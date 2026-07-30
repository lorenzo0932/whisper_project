#!/bin/bash
set -e

APP_NAME="WhisperGUI"
APP_BUNDLE="${APP_NAME}.app"
DMG_NAME="${APP_NAME}-macOS-universal.dmg"
DEST="/Applications/${APP_BUNDLE}"
CLI_SYMLINK="/usr/local/bin/whisper-gui"
MOUNT="/Volumes/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
    echo "Uso: $0 [-i <path.dmg>] [--uninstall]"
    echo "  -i <file>    Installa dal DMG specificato"
    echo "  --uninstall  Rimuove WhisperGUI dal sistema"
    exit 1
}

cleanup() {
    hdiutil detach "$MOUNT" 2>/dev/null || true
}

UNINSTALL=false
DMG_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall) UNINSTALL=true; shift ;;
        -i) DMG_PATH="$2"; shift 2 ;;
        *) usage ;;
    esac
done

if $UNINSTALL; then
    echo "Rimozione WhisperGUI..."
    rm -rf "$DEST"
    rm -f "$CLI_SYMLINK"
    echo "WhisperGUI rimosso."
    exit 0
fi

if [ -z "$DMG_PATH" ]; then
    for dir in "$ROOT_DIR" "$ROOT_DIR/installer/macos/output"; do
        candidate="$dir/$DMG_NAME"
        [ -f "$candidate" ] && DMG_PATH="$candidate" && break
    done
fi

if [ -z "$DMG_PATH" ] || [ ! -f "$DMG_PATH" ]; then
    echo "Errore: $DMG_NAME non trovato."
    echo "Scaricalo da: https://github.com/lorenzo0932/whisper_project/releases"
    echo "Oppure specifica il percorso con: $0 -i <file>"
    exit 1
fi

trap cleanup EXIT

echo "Montaggio DMG..."
hdiutil attach "$DMG_PATH" -nobrowse -mountpoint "$MOUNT"

APP_SRC=""
for f in "$MOUNT"/*; do
    if [ -d "$f" ] && [[ "$f" == *.app ]]; then
        APP_SRC="$f"
        break
    fi
done

if [ -z "$APP_SRC" ]; then
    echo "Errore: $APP_BUNDLE non trovato nel DMG."
    exit 1
fi

echo "Installazione di ${APP_NAME} in /Applications/..."
rm -rf "$DEST"
cp -R "$APP_SRC" "$DEST"

echo "Creazione collegamento CLI in ${CLI_SYMLINK}..."
mkdir -p "$(dirname "$CLI_SYMLINK")"
ln -sf "$DEST/Contents/MacOS/$APP_NAME" "$CLI_SYMLINK"

echo "WhisperGUI installato in $DEST"
echo "Avvia dal Launchpad o con: whisper-gui"
echo "Per rimuovere: $0 --uninstall"
