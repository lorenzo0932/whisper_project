# Pipeline di build e packaging

Tutto ruota attorno a `build.py`: gli **stessi 5 comandi** su Linux, macOS e Windows, usati sia dagli sviluppatori sia dalla CI (`.github/workflows/release.yml`).

```
python build.py bootstrap      crea il venv e installa le dipendenze (requirements.txt pinnati)
python build.py build-engine   compila whisper.cpp (backend per-OS) e scarica ffmpeg/ffprobe statici
python build.py build          impacchetta l'app con PyInstaller (onedir) in dist/WhisperGUI
python build.py package        produce l'artefatto dell'OS: AppImage / .dmg / setup.exe NSIS
python build.py install        installa localmente l'app appena buildata
```

Flag: `--skip-engine` (usa i binari già in `bin/`, con `ensure_ffmpeg()` comunque difensivo), `--no-bootstrap` (usa l'interprete corrente invece del venv).

## Costanti e piattaforma (build.py:26-42)

- `APP_NAME = "WhisperGUI"`, `EXEC_NAME = "whisper-gui"`, `VERSION = "1.0.0"`, `WHISPERCPP_TAG = "v1.9.1"`, repo `ggml-org/whisper.cpp`.
- Path root: `bin/` (binari engine+ffmpeg), `dist/` (bundle PyInstaller), `build/cache/` (download: ffmpeg, appimagetool, NSIS).
- `IS_WINDOWS / IS_MACOS / IS_LINUX` determinano backend, nomi binari e separatori.

## `bootstrap` (build.py:82)

Crea `.venv` se assente (`python -m venv`) e installa `requirements.txt` pinnato (PyQt6 6.11.0, yt-dlp, platformdirs 4.11.0, pyinstaller 6.21.0). In CI il venv è ricreato a ogni run (le cache pip di setup-python velocizzano).

## `build-engine` (build.py:103)

1. `ensure_whispercpp_source()` (build.py:93): clona `external/whisper.cpp` (tag v1.9.1, depth 1) **solo se assente** — in CI questo path è cache-ato via `--skip-engine`.
2. Configurazione CMake con backend per-OS (build.py:113-120):
   - Linux/Windows: `-DGGML_VULKAN=ON -DGGML_AVX512=OFF` (su Linux Windows AVX512 off; su Windows il backend vulkan);
   - macOS: `-DGGML_METAL=ON -DWHISPER_COREML=ON` (arm64-only).
3. `cmake --build build -j N` con `BUILD_JOBS` opzionale dall'env (default: tutti i core; sul runner CI = 4 vCPU).
4. Copia `whisper-cli` in `bin/`.
5. `ensure_ffmpeg()` (build.py:138): scarica ffmpeg/ffprobe statici in `build/cache` (`download()` non ridiscarica se presente) e li estrae in `bin/` — johnvansickle (Linux), osxexperts arm64 (macOS), BtbN (Windows).

## `build` (build.py:~190)

PyInstaller `--onedir --noconfirm` con:
- `--add-data <path assoluto>:<dest>` per `bin`, `media`, `icon` (i path assoluti sono obbligatori: in CI è un gotcha già pagato);
- `--workpath`/`--specpath` in `build/pyinstaller/`;
- output in `dist/WhisperGUI`.

## `package` (build.py:346)

| OS | Funzione | Artefatto | Dettagli |
|---|---|---|---|
| Linux | `package_linux` (build.py:224) | `installer/linux/output/WhisperGUI-x86_64.AppImage` | copia `dist` in `build/AppDir`, genera icona PNG via `scripts/icon_gen.py` (PyQt6.QtSvg, niente dipendenze esterne), crea `AppRun`/`.desktop`, esegue `appimagetool --appimage-extract-and-run` (niente FUSE: funziona in container e runner). |
| macOS | `package_macos` (build.py:266) | `installer/macos/output/WhisperGUI-macOS-arm64.dmg` | costruisce `build/WhisperGUI.app` (Contents/MacOS+Resources), genera iconset ICNS con icon_gen, firma ad-hoc, `hdiutil create` (UDZO). Niente codesign del bundle (senza notarizzazione non serve). |
| Windows | `package_windows` (build.py:320) | `installer/windows/output/WhisperGUI-x86_64-setup.exe` | cerca `makensis.exe` (PATH o scarica NSIS 3.12 in `build/cache` — lo zip ha `nsis-3.12/` in root: ricerca ricorsiva), compila `installer/windows/whispergui.nsi` con `-DVERSION -DAPP_PATH -DOUT_FILE`. |

## `install` (build.py:355)

| OS | Destinazione |
|---|---|
| Linux | `~/.local/lib/whisper-gui` (bundle) + launcher `~/.local/bin/whisper-gui` + icona SVG e `.desktop` in `~/.local/share` (voce nel menu applicazioni) |
| macOS | `~/Applications/WhisperGUI.app` |
| Windows | generato dal setup NSIS (in `%LOCALAPPDATA%`, senza admin) |

## Wrapper e script correlati

- `install.sh` (root): bootstrap + build-engine `--skip-engine` + build + install — installazione rapida per sviluppatori.
- `installer/linux/install.sh` / `installer/macos/install.sh`: installazione "curata" per l'utente finale (anche disinstallazione).
- `scripts/icon_gen.py`: `png <svg> <out> <size>` e `iconset <svg> <dir>` (icone 16→512 + @2x) via `QSvgRenderer`, senza creare QApplication (quindi senza plugin di piattaforma).
- Vedi [ci.md](ci.md) per come la CI usa questa pipeline con caching.
