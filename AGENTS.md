# AGENTS.md

WhisperGUI: GUI PyQt6 + trascrizione whisper.cpp (backend CLI). Entry: `main.py` (GUI di default, `--cli` per modalità headless). Commenti, commit e UI in **italiano**. Nessuna suite di test: la verifica è uno smoke test CLI.

## Comandi

- Avvio dev (venv creato da `build.py bootstrap`): `.venv/bin/python main.py` oppure `--cli -f <file> -m tiny` (headless, usato per tutti gli smoke test; modelli in `models/`)
- Smoke test rapido: `.venv/bin/python main.py --cli -f input/test.webm -m tiny` — stampa `[FINISH] Successo: True`
- Build/packaging: `python3 build.py {bootstrap|build-engine|build|package|install}`; `install.sh` è un wrapper; dopo modifiche a build.py: `python3 -m py_compile build.py`
- Simulazione del job CI Linux **senza push**: `scripts/ci-linux.sh engine|full` (gestisce sia Fedora/dnf che Debian/apt)

## Architettura

- `core/whispercpp_manager.py` avvia `whisper-cli` impostando env per-OS (`LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`/`PATH`) sul `bin_dir`
- `utils/resource_path.py`: `resource_path()`/`binary_name()` — **tutti** i path a risorse/binarie nel bundle passano da qui (PyInstaller onedir mette tutto in `_internal`); icone via `resource_path("icon/ai_studio_code.svg")` (main.py:82, ui/main_window.py:35)
- `services/processing_service.py` espone segnali Qt (funzionano anche headless con `QCoreApplication`)
- Backend GPU: Vulkan su Linux/Windows, Metal+CoreML su macOS; **arm64-only** su macOS

## Build & CI — gotchas pagati in run CI (non ripetere gli errori)

- `external/whisper.cpp` viene clonato da `build.py build-engine` (tag `WHISPERCPP_TAG`, v1.9.x); `external/*`, `bin/`, `models/`, `dist/`, `build/` sono gitignored
- `find_package(Vulkan COMPONENTS glslc REQUIRED)` richiede il binario **glslc**:
  - `glslang-tools` di Ubuntu **non** lo fornisce; il pacchetto `shaderc` del repo LunarG sì (nel workflow: download diretto del .deb, NO repo LunarG in apt — il suo `libvulkan-dev` 1.4.313~rc1 è rotto: senza header, sovrascrive quello buono di Ubuntu)
  - Windows: `choco install vulkan-sdk` + export `VULKAN_SDK` e `Bin` via `$env:GITHUB_ENV`/`GITHUB_PATH` (il pacchetto choco non imposta env da solo)
- `aux/` è un path riservato su Windows (bloccava il checkout git) — non crearne uno alla root
- `--add-data` di PyInstaller richiede path **assoluti** (in build.py)
- Lo zip NSIS ha `nsis-3.12/` in root: `package_windows` cerca `makensis.exe` ricorsivamente
- macOS: niente `codesign` del bundle `.app` (senza notarizzazione non serve, in CI fallisce silenziosamente); ffmpeg/whisper-cli firmati ad-hoc in build-engine; ffmpeg da osxexperts (binari arm64), su Linux johnvansickle, su Windows BtbN
- `softprops/action-gh-release` fallisce senza tag: upload solo con `if: github.event_name == 'push'` (i dispatch validano la build fino al packaging)
- CI testabile con `gh workflow run release.yml --ref <branch> -f os=linux|macos|windows|all`; runner: ubuntu-22.04 (glibc 2.35 = baseline compatibilità), macos-14 (arm64), windows-latest

## Git workflow

- `dev` è il branch di integrazione; lavoro su `feat/<nome>` → merge `--no-ff` in `dev` → branch eliminato
- Commit piccoli e mirati (`fix(ci): ...`, `chore: ...`); squash dei fix iterativi prima del merge
- Macchina locale: **Fedora 43** (dnf, non apt); `glslc` locale = pacchetto dnf `glslc`
