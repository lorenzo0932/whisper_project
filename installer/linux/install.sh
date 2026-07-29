#!/bin/bash
set -e

APP_NAME="WhisperGUI"
APPIMAGE="${APP_NAME}-x86_64.AppImage"
DEST="$HOME/.local/bin/whisper-gui"
DESKTOP="$HOME/.local/share/applications/whisper-gui.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

if [ ! -f "$APPIMAGE" ]; then
    echo "Errore: $APPIMAGE non trovato nella directory corrente."
    echo "Scaricalo da: https://github.com/lorenzo0932/whisper_project/releases"
    exit 1
fi

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$ICON_DIR"

cp "$APPIMAGE" "$DEST"
chmod +x "$DEST"

cat > "$DESKTOP" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WhisperGUI
Comment=Trascrizione AI nativa (Vulkan/Metal)
Exec=$DEST
Icon=whisper-gui
Terminal=false
Categories=AudioVideo;Audio;
EOF

if [ -f "media/WhisperGUIImage.png" ]; then
    cp "media/WhisperGUIImage.png" "$ICON_DIR/whisper-gui.png"
fi

echo "✅ WhisperGUI installato in $DEST"
echo "✅ Collegamento .desktop creato in $DESKTOP"
echo ""
echo "Puoi avviare WhisperGUI dal menu applicazioni o con:"
echo "  $ whisper-gui"
echo ""
echo "Per la CLI:"
echo "  $ whisper-gui --cli -f file.wav"
