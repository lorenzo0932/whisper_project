#!/bin/bash
# Simula localmente il job build-linux di release.yml (nessun push richiesto).
#
# Uso:
#   scripts/ci-linux.sh engine   compila whisper.cpp come in CI (clone fresco v1.9.1
#                                in /tmp/ci-engine, stessi flag Vulkan) - NON tocca bin/
#   scripts/ci-linux.sh full     intera pipeline: bootstrap + engine + build + package
#   scripts/ci-linux.sh docker   replica ESATTA del runner CI (container ubuntu:22.04,
#                                stessi pacchetti apt e deb shaderc) - richiede docker
set -e
cd "$(dirname "$0")/.."
MODE="${1:-engine}"

if [ "$MODE" == "docker" ]; then
    if ! command -v docker >/dev/null; then
        echo "Docker non installato: la modalita' docker richiede il demone docker."
        exit 1
    fi
    echo "=========================================================="
    echo " Avvio simulazione GitHub Actions (Ubuntu 22.04) ..."
    echo "=========================================================="

    WORK_DIR="/tmp/ci-docker-whispergui"
    echo "[0/5] Preparazione workspace isolato in $WORK_DIR..."
    # Pulizia dei soli artefatti volatili; build/cache, external/ e .venv persistono
    # tra i run per velocizzare le iterazioni locali (niente re-download/re-clone/pip)
    # Fallback sudo: una run precedente interrotta lascia file di root
    rm -rf "$WORK_DIR/build/pyinstaller" "$WORK_DIR/dist" "$WORK_DIR/bin" "$WORK_DIR/installer/linux/output" 2>/dev/null \
        || sudo rm -rf "$WORK_DIR/build/pyinstaller" "$WORK_DIR/dist" "$WORK_DIR/bin" "$WORK_DIR/installer/linux/output"
    mkdir -p "$WORK_DIR/build/cache" "$WORK_DIR"

    # Replica fedele di actions/checkout ignorando i file generati localmente dall'host
    # (senza esclusioni il container userebbe il .venv del Fedora host: binari ELF
    # incompatibili + CMakeCache sporca -> errore immediato)
    rsync -a --exclude='.venv' \
             --exclude='bin' \
             --exclude='build' \
             --exclude='dist' \
             --exclude='external' \
             --exclude='installer/*/output' \
             --exclude='.git' \
             --exclude='input' \
             --exclude='models' \
             --exclude='__pycache__' \
             ./ "$WORK_DIR/"

    HOST_UID=$(id -u)
    HOST_GID=$(id -g)

    docker run --rm -i -e BUILD_JOBS=16 -v "$WORK_DIR:/workspace" -w /workspace ubuntu:22.04 bash -e << EOF
        echo "[1/5] Installazione dipendenze di sistema (apt)..."
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            cmake build-essential spirv-headers \
            libgl1 libegl1 libglib2.0-0 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3 \
            file \
            wget git python3 python3-venv python3-pip xz-utils curl

        echo "[2/5] Vulkan SDK 1.4.313 (deb LunarG) e CMake (3.31.*)..."
        echo "   (gli header 1.3.204 di jammy sono troppo vecchi per ggml-vulkan v1.9.1)"
        wget -q https://packages.lunarg.com/vulkan/pool/main/v/vulkan-loader/libvulkan1_1.4.313.0~rc1-1lunarg22.04-1_amd64.deb -O /tmp/libvulkan1.deb
        wget -q https://packages.lunarg.com/vulkan/pool/main/v/vulkan-loader/libvulkan-dev_1.4.313.0~rc1-1lunarg22.04-1_amd64.deb -O /tmp/libvulkan-dev.deb
        wget -q https://packages.lunarg.com/vulkan/pool/main/v/vulkan-headers/vulkan-headers_1.4.313.0~rc1-1lunarg22.04-1_all.deb -O /tmp/vulkan-headers.deb
        wget -q https://packages.lunarg.com/vulkan/pool/main/s/shaderc/shaderc_2025.2~rc1-1lunarg22.04-1_amd64.deb -O /tmp/shaderc.deb
        dpkg -i /tmp/libvulkan1.deb /tmp/libvulkan-dev.deb /tmp/vulkan-headers.deb /tmp/shaderc.deb
        pip3 install --quiet 'cmake==3.31.*'

        echo "[3/5] Esecuzione pipeline build.py..."
        python3 build.py bootstrap
        python3 build.py build-engine
        python3 build.py build
        python3 build.py package

        echo "[4/5] Ripristino permessi per recupero artefatti..."
        chown -R $HOST_UID:$HOST_GID /workspace
EOF

    echo "[5/5] Recupero artefatto e pulizia..."
    mkdir -p installer/linux/output
    cp "$WORK_DIR/installer/linux/output/"*.AppImage installer/linux/output/
    rm -rf "$WORK_DIR"

    echo "OK: simulazione completata! AppImage in installer/linux/output/"
    exit 0
fi

install_deps() {
  if command -v dnf >/dev/null; then
    sudo dnf install -y cmake gcc-c++ glslc vulkan-headers
  elif command -v apt-get >/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq cmake build-essential libvulkan-dev shaderc
  else
    echo "Pacchetto manager non supportato: installa cmake, un compilatore C/C++, glslc e i header Vulkan"
    exit 1
  fi
}

case "$MODE" in
  engine)
    echo "=== Simulazione job build-linux (engine) ==="
    echo "[1/3] Dipendenze di sistema (come in CI)..."
    install_deps
    echo "[2/3] Clone fresco whisper.cpp v1.9.1..."
    rm -rf /tmp/ci-engine
    git clone --depth 1 --branch v1.9.1 https://github.com/ggml-org/whisper.cpp.git /tmp/ci-engine
    echo "[3/3] Compilazione (stessi flag della CI)..."
    cmake -B /tmp/ci-engine/build -S /tmp/ci-engine -DGGML_VULKAN=ON -DGGML_AVX512=OFF
    cmake --build /tmp/ci-engine/build -j
    echo "OK: engine compila esattamente come nel runner."
    ;;
  full)
    echo "=== Simulazione job build-linux (pipeline completa) ==="
    python3 build.py bootstrap
    python3 build.py build-engine
    python3 build.py build
    python3 build.py package
    echo "OK: pipeline completa come in CI."
    ;;
  *)
    echo "Uso: $0 [engine|full|docker]"
    exit 1
    ;;
esac
