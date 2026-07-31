#!/bin/bash
# Simula localmente il job build-linux di release.yml (nessun push richiesto).
#
# Uso:
#   scripts/ci-linux.sh engine   compila whisper.cpp come in CI (clone fresco v1.9.1
#                                in /tmp/ci-engine, stessi flag Vulkan) - NON tocca bin/
#   scripts/ci-linux.sh full     intera pipeline: bootstrap + engine + build + package
set -e
cd "$(dirname "$0")/.."
MODE="${1:-engine}"

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
    echo "Uso: $0 [engine|full]"
    exit 1
    ;;
esac
