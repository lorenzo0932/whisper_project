#!/bin/bash
set -e

# --- CONFIGURAZIONE ---
APP_NAME="WhisperGUI"
EXEC_NAME="whisper-gui"
BIN_DEST="$HOME/.local/bin/$EXEC_NAME"
PROJECT_DIR=$(pwd)
CORES=$(nproc 2>/dev/null || echo 4)

echo "-------------------------------------------------------"
echo "   WhisperGUI Turbo Installer (Target: $CORES Core)"
echo "-------------------------------------------------------"

# 1. Pulizia processi attivi (Risolve errore I/O)
echo "[1/5] Sblocco file e pulizia processi..."
pkill -f "whisper-gui" || true
[ -f "$BIN_DEST" ] && rm -f "$BIN_DEST"

# 2. Setup ambiente di build isolato (Per evitare bug Anaconda/Nuitka)
echo "[2/5] Creazione ambiente di build isolato..."
python3 -m venv build_venv
source build_venv/bin/activate
pip install --upgrade pip --quiet
pip install nuitka ordered-set zstandard PyQt6 yt-dlp --quiet

# 3. Compilazione MULTICORE
echo "[3/5] Compilazione C++ in corso (Uso di $CORES core)..."
# Usiamo --no-metadata per evitare il bug di Anaconda che hai riscontrato
python -m nuitka --standalone --onefile \
    --enable-plugin=pyqt6 \
    --include-data-dir="$PROJECT_DIR/bin=bin" \
    --include-data-dir="$PROJECT_DIR/media=media" \
    --jobs="$CORES" \
    --static-libpython=no \
    --output-filename="whisper-gui-bin" \
    --output-dir="dist" \
    --no-deployment-flag=self-execution \
    main.py

# 4. Installazione Atomica (Risolve errore I/O di 'clonazione fallita')
echo "[4/5] Installazione in $BIN_DEST..."
mkdir -p "$HOME/.local/bin"
# Usiamo 'cat' per scrivere il file, è il metodo più sicuro contro i lock del filesystem
cat "dist/whisper-gui-bin" > "$BIN_DEST"
chmod 755 "$BIN_DEST"

# 5. Integrazione Sistema
echo "[5/5] Creazione collegamenti..."
mkdir -p "$HOME/.config/WhisperGUI"
mkdir -p "$HOME/.cache/WhisperGUI/models"
mkdir -p "$HOME/.local/share/applications"

ICON_PATH="$PROJECT_DIR/media/WhisperGUIImage.png"
[ ! -f "$ICON_PATH" ] && ICON_PATH="audio-x-generic"

cat <<EOF > "$HOME/.local/share/applications/whisper-gui.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Whisper GUI
Comment=Trascrizione AI nativa (Vulkan)
Exec=$BIN_DEST
Icon=$ICON_PATH
Terminal=false
Categories=AudioVideo;Audio;
EOF

# Pulizia ambiente temporaneo
deactivate
rm -rf build_venv

echo "-------------------------------------------------------"
echo "   INSTALLAZIONE COMPLETATA IN MODALITÀ TURBO!"
echo "-------------------------------------------------------"
echo "• Eseguibile: $BIN_DEST"
echo "• Prova la CLI: whisper-gui --cli -f file.wav"