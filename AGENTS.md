# AGENTS.md

WhisperGUI: GUI PyQt6 + trascrizione whisper.cpp (backend CLI). Entry: `main.py` (GUI di default, `--cli` per modalità headless). Commenti, commit e UI in **italiano**. Nessuna suite di test: la verifica è uno smoke test CLI.

## Comandi

- Avvio dev (venv creato da `build.py bootstrap`): `.venv/bin/python main.py` oppure `--cli -f <file> -m tiny` (headless, usato per tutti gli smoke test; modelli in `models/`)
- Smoke test rapido: `.venv/bin/python main.py --cli -f input/test.webm -m tiny` — stampa `[FINISH] Successo: True`
- Build/packaging: `python3 build.py {bootstrap|build-engine|build|package|install}`; `install.sh` è un wrapper; dopo modifiche a build.py: `python3 -m py_compile build.py`
- Simulazione del job CI Linux **senza push**: `scripts/ci-linux.sh engine|full|docker` (gestisce sia Fedora/dnf che Debian/apt; `docker` = replica esatta del runner ubuntu:22.04)

## Architettura

- `core/whispercpp_manager.py` avvia `whisper-cli` impostando env per-OS (`LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`/`PATH`) sul `bin_dir`
- `utils/resource_path.py`: `resource_path()`/`binary_name()` — **tutti** i path a risorse/binarie nel bundle passano da qui (PyInstaller onedir mette tutto in `_internal`); icone via `resource_path("icon/ai_studio_code.svg")` (main.py:82, ui/main_window.py:35)
- `services/processing_service.py` espone segnali Qt (funzionano anche headless con `QCoreApplication`)
- Backend GPU: Vulkan su Linux/Windows, Metal+CoreML su macOS; **arm64-only** su macOS

## Build & CI — gotchas pagati in run CI (non ripetere gli errori)

- `external/whisper.cpp` viene clonato da `build.py build-engine` (tag `WHISPERCPP_TAG`, v1.9.x); `external/*`, `bin/`, `models/`, `dist/`, `build/` sono gitignored
- **Licenze**: progetto GPL-3.0 (`LICENSE`, copyright Madonna0932); `licenses/` contiene i testi integrali delle terze parti (aggiornarla quando cambia una dipendenza) e `THIRD_PARTY_NOTICES.md` la tabella riassuntiva; `build.py` la include nel bundle con `--add-data` (come bin/media/icon)
- `find_package(Vulkan COMPONENTS glslc REQUIRED)` richiede il binario **glslc**:
  - `glslang-tools` di Ubuntu **non** lo fornisce; il pacchetto `shaderc` del repo LunarG sì (nel workflow: download diretto del .deb, NO repo LunarG in apt)
  - **Headers Vulkan di jammy (libvulkan-dev 1.3.204) troppo vecchi per ggml-vulkan v1.9.1** (errori `layer_setting_info`, `eMesaDozen`, `PhysicalDeviceProperties2`): su Linux il workflow installa il **trio LunarG 1.4.313.0~rc1 via deb diretti** — `libvulkan1` + `libvulkan-dev` + `vulkan-headers` + `shaderc` — e NON il `libvulkan-dev` di Ubuntu (che dichiara `Breaks: vulkan-headers`: con `--force-overwrite` comunque dpkg rifiuta la config; si sostituisce l'intero trio, niente mix). Fedora ha vulkan-headers 1.4.341 (per questo i test locali non segnalavano nulla)
  - `ggml-vulkan` richiede anche `find_package(SPIRV-Headers CONFIG)`: su Ubuntu serve `apt install spirv-headers` (**jammy-updates** 1.4.341 — la versione base di jammy non ha `SPIRV-HeadersConfig.cmake`); su Fedora arriva da `spirv-headers-devel` (per questo i test locali non lo segnalavano)
  - Windows: `choco install vulkan-sdk` + export `VULKAN_SDK` e `Bin` via `$env:GITHUB_ENV`/`GITHUB_PATH` (il pacchetto choco non imposta env da solo)
- **Deps runtime Qt nel runner** (il packaging PyInstaller esegue `icon_gen.py` con PyQt6): `libgl1 libegl1 libglib2.0-0 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3` + `file` (richiesto da appimagetool, che gira con `--appimage-extract-and-run` in build.py: niente FUSE)
- **Simulazione docker incrementale**: `build/cache`, `external/` e `.venv` persistono tra i run (la pulizia all'avvio tocca solo `build/pyinstaller`, `dist/`, `bin/`, `installer/linux/output`); `BUILD_JOBS=16` nel container (il runner CI usa il default `-j` = 4 vCPU). La sim ha anticipato TUTTI i fix Linux: testarla PRIMA di committare modifiche alla pipeline Linux
- `gh workflow run` subito dopo un push al workflow può rispondere 422 "does not have workflow_dispatch trigger" (cache di GitHub): riprovare con `--ref <branch>` dopo ~30s
- **Caching CI** (gratis, actions/cache): 3 livelli per-OS — pip (`setup-python` con `cache: pip`), download (`build/cache`, chiave `downloads-<os>-hash(build.py)`) e engine (`bin/`, chiave `engine-<os>-hash(build.py)` → `build-engine --skip-engine` sul cache-hit). Le chiavi dipendono solo da build.py: modifiche ai .py dell'app non invalidano l'engine; `--skip-engine` chiama comunque `ensure_ffmpeg()` (difensivo)
- Il job `validate` (fail-fast, ~10s) esegue `compileall` + `bash -n` prima dei job pesanti: un errore di sintassi non brucia più 3 run parallele
- `requirements.txt` è **pinnato** (PyQt6/yt-dlp/platformdirs/pyinstaller): aggiornare SOLO dopo aver testato il venv e aggiornando anche la cache pip
- `aux/` è un path riservato su Windows (bloccava il checkout git) — non crearne uno alla root
- `--add-data` di PyInstaller richiede path **assoluti** (in build.py)
- Lo zip NSIS ha `nsis-3.12/` in root: `package_windows` cerca `makensis.exe` ricorsivamente
- NSIS: `HWND_BROADCAST` è già definito da NSIS 3.x — non ridefinirlo senza guardia `!ifndef` (errore hard in compilazione)
- macOS: niente `codesign` del bundle `.app` (senza notarizzazione non serve, in CI fallisce silenziosamente); ffmpeg/whisper-cli firmati ad-hoc in build-engine; ffmpeg da osxexperts (binari arm64), su Linux johnvansickle, su Windows BtbN
- `softprops/action-gh-release` fallisce senza tag: upload solo con `if: github.event_name == 'push'` (i dispatch validano la build fino al packaging)
- `run()` in build.py stampa stderr/stdout (tail) quando un comando fallisce: i log CI dicono l'errore ESATTO del tool (cmake/nsis/codesign)
- CI testabile con `gh workflow run release.yml --ref <branch> -f os=linux|macos|windows|all`; runner: ubuntu-22.04 (glibc 2.35 = baseline compatibilità), macos-14 (arm64), windows-latest; primo run a cache fredda ~12 min, iterazioni successive ~3 min

## Git workflow

- `dev` è il branch di integrazione; lavoro su `feat/<nome>` → merge `--no-ff` in `dev` → branch eliminato
- Commit piccoli e mirati (`fix(ci): ...`, `chore: ...`); squash dei fix iterativi prima del merge
- Macchina locale: **Fedora 43** (dnf, non apt); `glslc` locale = pacchetto dnf `glslc`
