# CI/CD — GitHub Actions e simulazione locale

## Workflow: `.github/workflows/release.yml`

### Trigger

- `workflow_dispatch` con input `os`: `all | linux | macos | windows` (per test manuali, nessun tag richiesto);
- `push` di tag `v*` → rilascio (upload artefatti su GitHub Release).

### Struttura

```
validate (Fail-Fast Validation, ubuntu-22.04, ~10s)
  ├─ python -m compileall -q .      → errori di sintassi Python
  └─ bash -n su scripts/*.sh        → errori di sintassi Bash
  │ (fail-fast: un errore di sintassi non brucia più 3 run parallele)
  ▼
build-linux (ubuntu-22.04)   build-windows (windows-latest)   build-macos (macos-14 arm64)
```

Ogni job di build esegue la stessa sequenza:

1. `actions/checkout@v4`
2. **Install system dependencies** (per-OS, vedi sotto)
3. `setup-python` 3.13 con `cache: 'pip'` (cache pip via `requirements.txt`)
4. **Cache Downloads**: `build/cache`, chiave `downloads-<os>-hashFiles('build.py')` — evita di riscaricare ffmpeg/appimagetool/NSIS
5. **Cache Engine**: `bin/`, chiave `engine-<os>-hashFiles('build.py')` — se il cache-hit c'è, `build-engine --skip-engine` (compila solo se build.py cambia)
6. `build.py bootstrap` → `build-engine` (o `--skip-engine`) → `build` → `package`
7. **Upload Release Asset** (`softprops/action-gh-release`, solo `if: github.event_name == 'push'` — senza tag fallisce)

### Dipendenze di sistema per-OS (gotcha pagati)

**Linux (ubuntu-22.04)** — apt:
- `cmake build-essential spirv-headers` — `spirv-headers` (jammy-updates 1.4.341) fornisce `SPIRV-HeadersConfig.cmake` richiesto da ggml-vulkan;
- runtime Qt per il packaging PyInstaller (icon_gen.py con PyQt6): `libgl1 libegl1 libglib2.0-0 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3`;
- `file` — richiesto da appimagetool.
- **Trio Vulkan LunarG 1.4.313.0~rc1 via deb diretti** (NO repo LunarG in apt): `libvulkan1` + `libvulkan-dev` + `vulkan-headers` + `shaderc` (fornisce `glslc`). Gli header di jammy (1.3.204) sono troppo vecchi per ggml-vulkan v1.9.1 (`layer_setting_info`, `eMesaDozen`, `PhysicalDeviceProperties2`); il `libvulkan-dev` di Ubuntu dichiara `Breaks: vulkan-headers` → si sostituisce l'intero trio, niente mix.
- `appimagetool` gira con `--appimage-extract-and-run` (build.py): niente FUSE.

**Windows (windows-latest)** — `choco install vulkan-sdk` + export `VULKAN_SDK` e `Bin` via `$env:GITHUB_ENV`/`GITHUB_PATH` (il pacchetto choco non imposta le env da solo); NSIS 3.12 scaricato da build.py in `build/cache`.

**macOS (macos-14, arm64)** — Xcode CLT (Metal/CoreML); ffmpeg binari osxexperts arm64; niente codesign del bundle (senza notarizzazione non serve, in CI fallirebbe silenziosamente).

### Note operative

- **Caching**: le chiavi dipendono solo da `build.py` — modifiche ai .py dell'app non invalidano l'engine. 3 livelli gratis: pip, download, engine.
- **Runner**: ubuntu-22.04 (glibc 2.35 = baseline compatibilità), macos-14, windows-latest; primo run a cache fredda ~12 min, iterazioni ~3 min.
- **422 su dispatch**: subito dopo un push al workflow, `gh workflow run` può rispondere 422 "does not have workflow_dispatch trigger" (cache GitHub): riprovare con `--ref <branch>` dopo ~30s.
- **Debug**: `run()` di build.py stampa stderr/stdout (tail) quando un comando fallisce → i log CI mostrano l'errore esatto del tool (cmake/nsis/appimagetool).

## Simulazione locale: `scripts/ci-linux.sh`

Simula il job `build-linux` **senza push**:

- `engine` — clone fresco di whisper.cpp in `/tmp/ci-engine` + compilazione con gli stessi flag Vulkan (non tocca `bin/`);
- `full` — intera pipeline bootstrap + engine + build + package sull'host (gestisce Fedora/dnf e Debian/apt);
- `docker` — **replica esatta del runner**: container `ubuntu:22.04` con gli stessi pacchetti apt e deb LunarG del workflow (shaderc + trio Vulkan 1.4.313), `pip3 install 'cmake==3.31.*'`, workspace isolato in `/tmp/ci-docker-whispergui`, recupero dell'AppImage in `installer/linux/output/`.

### Modalità docker — dettagli

- **Incrementale tra i run** (iterazioni locali veloci): `build/cache`, `external/` e `.venv` persistono; la pulizia all'avvio tocca solo `build/pyinstaller`, `dist/`, `bin/`, `installer/linux/output` (fallback `sudo rm -rf` per residui di root di run interrotte).
- `BUILD_JOBS=16` nel container (host locale); il runner CI usa il default `-j` (4 vCPU).
- L'AppImage prodotta viene copiata in `installer/linux/output/` e l'ownership ripristinata (`chown`).
- **Regola d'oro**: la sim docker ha anticipato tutti i fix Linux (headers Vulkan, deps Qt, `file` per appimagetool) — testarla PRIMA di committare modifiche alla pipeline Linux.

### Test CI senza sporcare git

Modifica locale → `scripts/ci-linux.sh docker` fino a verde → **un singolo commit** (es. `fix(ci): ...`) → push → `gh workflow run release.yml --ref <branch> -f os=all` → merge `--no-ff` in `dev`.
