#!/bin/bash
set -e

APP_NAME="WhisperGUI"
IMG_NAME="${APP_NAME}-x86_64.AppImage"
DEST="$HOME/.local/bin/whisper-gui"
APP_DIR="$HOME/.local/lib/whisper-gui"
DESKTOP="$HOME/.local/share/applications/whisper-gui.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_DEST="$ICON_DIR/whisper-gui.png"
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
    rm -rf "$APP_DIR"
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
    echo "Download dell'ultima release da GitHub..."
    APPIMAGE_URL="https://github.com/lorenzo0932/whisper_project/releases/latest/download/$IMG_NAME"
    APPIMAGE="$(mktemp --suffix=.AppImage)"
    if ! curl -fSL "$APPIMAGE_URL" -o "$APPIMAGE"; then
        rm -f "$APPIMAGE"
        echo "Errore: download fallito da $APPIMAGE_URL"
        exit 1
    fi
    chmod +x "$APPIMAGE"
fi

# Path assoluto: dopo l'estrazione cambiamo directory di lavoro
APPIMAGE="$(realpath "$APPIMAGE")"

echo "Installa WhisperGUI da: $APPIMAGE"

# Estrai l'AppImage senza FUSE (--appimage-extract non richiede mount)
TMP_EXTRACT="$(mktemp -d)"
cd "$TMP_EXTRACT"
"$APPIMAGE" --appimage-extract >/dev/null 2>&1 || {
    echo "Errore: estrazione AppImage fallita. File non valido?"
    rm -rf "$TMP_EXTRACT"
    exit 1
}

mkdir -p "$HOME/.local/bin" "$(dirname "$DESKTOP")"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$TMP_EXTRACT/squashfs-root/." "$APP_DIR/"

# Icona: dall'AppImage estratta (funziona anche con curl | bash), fallback all'SVG dal repo
ICON_SRC="$TMP_EXTRACT/squashfs-root/whisper-gui.png"
ICON_FALLBACK="$ROOT_DIR/icon/ai_studio_code.svg"

mkdir -p "$ICON_DIR"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DEST"
elif [ -f "$ICON_FALLBACK" ]; then
    cp "$ICON_FALLBACK" "$ICON_DEST"
fi

rm -rf "$TMP_EXTRACT"

cat > "$DEST" <<EOF
#!/bin/bash
exec "$APP_DIR/$APP_NAME" "\$@"
EOF
chmod 755 "$DEST"

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

echo "✅ WhisperGUI installato in $APP_DIR"
echo "✅ Collegamento creato in $DEST"
echo "✅ Collegamento .desktop creato in $DESKTOP"
echo ""
echo "Avvia dal menu applicazioni o con: whisper-gui"
echo "Per rimuovere: $0 --uninstall (da un clone del repo), oppure riesegui lo stesso comando curl|bash usato per installare aggiungendo: bash -s -- --uninstall"
