#!/bin/bash
set -e

APP_NAME="WhisperGUI"
DMG="${APP_NAME}-macOS-universal.dmg"
VOLUME="/Volumes/$APP_NAME"

if [ ! -f "$DMG" ]; then
    echo "Errore: $DMG non trovato."
    echo "Scaricalo da: https://github.com/lorenzo0932/whisper_project/releases"
    exit 1
fi

hdiutil attach "$DMG" -nobrowse
cp -R "$VOLUME/$APP_NAME.app" /Applications/
hdiutil detach "$VOLUME"

echo "✅ WhisperGUI installato in /Applications/"
echo "Puoi avviarlo da Launchpad o con: open /Applications/WhisperGUI.app"
