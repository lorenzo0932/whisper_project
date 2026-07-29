#!/bin/bash
set -e

APP_NAME="WhisperGUI"
EXEC_NAME="whisper-gui"
BIN_DEST="$HOME/.local/bin/$EXEC_NAME"
PROJECT_DIR=$(pwd)

echo "-------------------------------------------------------"
echo "   WhisperGUI Installer (PyInstaller)"
echo "-------------------------------------------------------"

# 1. Pulizia
echo "[1/5] Pulizia..."
pkill -f "$EXEC_NAME" 2>/dev/null || true
[ -f "$BIN_DEST" ] && rm -f "$BIN_DEST"
rm -rf dist build_venv

# 2. Ambiente Python
echo "[2/5] Creazione ambiente virtuale..."
python3 -m venv build_venv
source build_venv/bin/activate
pip install --upgrade pip --quiet
pip install pyinstaller PyQt6 yt-dlp platformdirs --quiet

# 3. Build
echo "[3/5] Build eseguibile (PyInstaller)..."
pyinstaller --onefile \
    --add-data "bin:bin" \
    --add-data "media:media" \
    --paths . \
    --name "$APP_NAME" \
    main.py

# 4. Installazione
echo "[4/5] Installazione in $BIN_DEST..."
mkdir -p "$HOME/.local/bin"
cp "dist/$APP_NAME" "$BIN_DEST"
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

# Pulizia
deactivate
rm -rf build_venv

echo "-------------------------------------------------------"
echo "   INSTALLAZIONE COMPLETATA!"
echo "-------------------------------------------------------"
echo "Eseguibile: $BIN_DEST"
echo "Avvia con: whisper-gui"
