#!/bin/bash
set -e

APP_NAME="WhisperGUI"
EXEC_NAME="whisper-gui"
BIN_DEST="$HOME/.local/bin/$EXEC_NAME"
PROJECT_DIR=$(pwd)
ICON_SRC="$PROJECT_DIR/icon/ai_studio_code.svg"
ICON_DEST="$HOME/.local/share/icons/hicolor/scalable/apps/whisper-gui.svg"

echo "-------------------------------------------------------"
echo "   WhisperGUI Installer (PyInstaller)"
echo "-------------------------------------------------------"

# 1. Pulizia
echo "[1/6] Pulizia..."
pkill -f "$EXEC_NAME" 2>/dev/null || true
[ -f "$BIN_DEST" ] && rm -f "$BIN_DEST"
rm -rf dist build_venv

# 2. Ambiente Python
echo "[2/6] Creazione ambiente virtuale..."
python3 -m venv build_venv
source build_venv/bin/activate
pip install --upgrade pip --quiet
pip install pyinstaller PyQt6 yt-dlp platformdirs --quiet

# 3. ffmpeg statico
echo "[3/6] Download ffmpeg statico..."
mkdir -p bin
if [ ! -f "bin/ffmpeg" ] || [ ! -f "bin/ffprobe" ]; then
    curl -sL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz?accept=yes" -o /tmp/ffmpeg.tar.xz
    tar -xJf /tmp/ffmpeg.tar.xz -C /tmp/
    cp /tmp/ffmpeg-*-static/ffmpeg /tmp/ffmpeg-*-static/ffprobe bin/
    chmod +x bin/ffmpeg bin/ffprobe
    rm -rf /tmp/ffmpeg.tar.xz /tmp/ffmpeg-*-static
fi

# 4. Build
echo "[4/6] Build eseguibile (PyInstaller)..."
pyinstaller --onefile \
    --add-data "bin:bin" \
    --add-data "media:media" \
    --add-data "icon:icon" \
    --paths . \
    --name "$APP_NAME" \
    main.py

# 5. Installazione
echo "[5/6] Installazione in $BIN_DEST..."
mkdir -p "$HOME/.local/bin"
cp "dist/$APP_NAME" "$BIN_DEST"
chmod 755 "$BIN_DEST"

# 6. Integrazione Sistema
echo "[6/6] Creazione collegamenti..."
mkdir -p "$HOME/.config/WhisperGUI"
mkdir -p "$HOME/.cache/WhisperGUI/models"
mkdir -p "$HOME/.local/share/applications"

mkdir -p "$(dirname "$ICON_DEST")"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DEST"
fi

cat <<EOF > "$HOME/.local/share/applications/whisper-gui.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Whisper GUI
Comment=Trascrizione AI nativa (Vulkan)
Exec=$BIN_DEST
Icon=$ICON_DEST
StartupWMClass=whisper-gui
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
