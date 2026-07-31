#!/bin/bash
set -e
# WhisperGUI installer (developers): delega la pipeline a build.py
cd "$(dirname "$0")"

echo "-------------------------------------------------------"
echo "   WhisperGUI Installer (build.py pipeline)"
echo "-------------------------------------------------------"

python3 build.py bootstrap
python3 build.py build-engine --skip-engine
python3 build.py build
python3 build.py install

echo "-------------------------------------------------------"
echo "   INSTALLAZIONE COMPLETATA!"
echo "   Avvia con: whisper-gui"
echo "-------------------------------------------------------"
