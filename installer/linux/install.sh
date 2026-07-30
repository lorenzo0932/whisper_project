#!/bin/bash
set -e

APP_NAME="WhisperGUI"
IMG_NAME="${APP_NAME}-x86_64.AppImage"
DEST="$HOME/.local/bin/whisper-gui"
DESKTOP="$HOME/.local/share/applications/whisper-gui.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_DEST="$ICON_DIR/whisper-gui.svg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    echo "Uso: $0 [-i AppImage] [--uninstall]"
    echo "  -i <file>    Installa l'AppImage specificata"
    echo "  --uninstall  Rimuove WhisperGUI dal sistema"
    exit 1
}

UNINSTALL=false
APPIMAGE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall) UNINSTALL=true; shift ;;
        -i) APPIMAGE="$2"; shift 2 ;;
        *) usage ;;
    esac
done

if $UNINSTALL; then
    echo "Rimozione WhisperGUI..."
    rm -f "$DEST" "$DESKTOP" "$ICON_DEST"
    rmdir "$(dirname "$ICON_DEST")" 2>/dev/null || true
    echo "✅ WhisperGUI rimosso."
    exit 0
fi

# Cerca l'AppImage
if [ -z "$APPIMAGE" ]; then
    for dir in "$ROOT_DIR" "$ROOT_DIR/dist" "$ROOT_DIR/installer/linux/output"; do
        candidate="$dir/$IMG_NAME"
        [ -f "$candidate" ] && APPIMAGE="$candidate" && break
    done
fi

if [ -z "$APPIMAGE" ] || [ ! -f "$APPIMAGE" ]; then
    echo "Errore: $IMG_NAME non trovato."
    echo "Scaricalo da: https://github.com/lorenzo0932/whisper_project/releases"
    echo "Oppure specifica il percorso con: $0 -i <file>"
    exit 1
fi

echo "Installa WhisperGUI da: $APPIMAGE"

mkdir -p "$HOME/.local/bin"
cp "$APPIMAGE" "$DEST"
chmod +x "$DEST"

# Icona
ICON_SRC="$ROOT_DIR/icon/ai_studio_code.svg"

mkdir -p "$ICON_DIR"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DEST"
fi

cat > "$DESKTOP" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WhisperGUI
Comment=Trascrizione AI nativa (Vulkan/Metal)
Exec=$DEST
Icon=$ICON_DEST
StartupWMClass=whisper-gui
Terminal=false
Categories=AudioVideo;Audio;
EOF

echo "✅ WhisperGUI installato in $DEST"
echo "✅ Collegamento .desktop creato in $DESKTOP"
echo ""
echo "Avvia dal menu applicazioni o con: whisper-gui"
echo "Per rimuovere: $0 --uninstall"
