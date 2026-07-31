# CI/CD — GitHub Actions and local simulation

## Workflow: `.github/workflows/release.yml`

### Triggers

- `workflow_dispatch` with the `os` input: `all | linux | macos | windows` (for manual tests, no tag required);
- `push` of `v*` tags → release (artifact upload to the GitHub Release).

### Structure

```
validate (Fail-Fast Validation, ubuntu-22.04, ~10s)
  ├─ python -m compileall -q .      → Python syntax errors
  └─ bash -n on scripts/*.sh        → Bash syntax errors
  │ (fail-fast: a syntax error no longer burns 3 parallel runs)
  ▼
build-linux (ubuntu-22.04)   build-windows (windows-latest)   build-macos (macos-14 arm64)
```

Every build job runs the same sequence:

1. `actions/checkout@v4`
2. **Install system dependencies** (per-OS, see below)
3. `setup-python` 3.13 with `cache: 'pip'` (pip cache keyed on `requirements.txt`)
4. **Downloads Cache**: `build/cache`, key `downloads-<os>-hashFiles('build.py')` — avoids re-downloading ffmpeg/appimagetool/NSIS
5. **Engine Cache**: `bin/`, key `engine-<os>-hashFiles('build.py')` — on cache-hit, `build-engine --skip-engine` (compiles only when build.py changes)
6. `build.py bootstrap` → `build-engine` (or `--skip-engine`) → `build` → `package`
7. **Upload Release Asset** (`softprops/action-gh-release`, only `if: github.event_name == 'push'` — fails without a tag)

### Per-OS system dependencies (paid gotchas)

**Linux (ubuntu-22.04)** — apt:
- `cmake build-essential spirv-headers` — `spirv-headers` (jammy-updates 1.4.341) provides `SPIRV-HeadersConfig.cmake` required by ggml-vulkan;
- Qt runtime for the PyInstaller packaging (icon_gen.py with PyQt6): `libgl1 libegl1 libglib2.0-0 libxkbcommon0 libfontconfig1 libfreetype6 libdbus-1-3`;
- `file` — required by appimagetool.
- **LunarG Vulkan trio 1.4.313.0~rc1 via direct debs** (NO LunarG apt repo): `libvulkan1` + `libvulkan-dev` + `vulkan-headers` + `shaderc` (provides `glslc`). The jammy headers (1.3.204) are too old for ggml-vulkan v1.9.1 (`layer_setting_info`, `eMesaDozen`, `PhysicalDeviceProperties2`); Ubuntu's `libvulkan-dev` declares `Breaks: vulkan-headers` → replace the whole trio, no mixing.
- `appimagetool` runs with `--appimage-extract-and-run` (build.py): no FUSE needed.

**Windows (windows-latest)** — `choco install vulkan-sdk` + export `VULKAN_SDK` and `Bin` via `$env:GITHUB_ENV`/`GITHUB_PATH` (the choco package doesn't set the env itself); NSIS 3.12 downloaded by build.py into `build/cache`.

**macOS (macos-14, arm64)** — Xcode CLT (Metal/CoreML); osxexperts arm64 ffmpeg binaries; no bundle codesign (useless without notarization, would fail silently in CI).

### Operational notes

- **Caching**: the keys depend only on `build.py` — app .py changes don't invalidate the engine. 3 free levels: pip, downloads, engine.
- **Runners**: ubuntu-22.04 (glibc 2.35 = compatibility baseline), macos-14, windows-latest; first cold-cache run ~12 min, iterations ~3 min.
- **422 on dispatch**: right after pushing to the workflow, `gh workflow run` may answer 422 "does not have workflow_dispatch trigger" (GitHub cache): retry with `--ref <branch>` after ~30s.
- **Debug**: `run()` in build.py prints stderr/stdout (tail) when a command fails → CI logs show the exact tool error (cmake/nsis/appimagetool).

## Local simulation: `scripts/ci-linux.sh`

Simulates the `build-linux` job **without pushing**:

- `engine` — fresh clone of whisper.cpp in `/tmp/ci-engine` + compilation with the same Vulkan flags (doesn't touch `bin/`);
- `full` — the whole pipeline bootstrap + engine + build + package on the host (handles both Fedora/dnf and Debian/apt);
- `docker` — **exact runner replica**: `ubuntu:22.04` container with the same apt packages and LunarG debs of the workflow (shaderc + Vulkan trio 1.4.313), `pip3 install 'cmake==3.31.*'`, isolated workspace in `/tmp/ci-docker-whispergui`, AppImage retrieved into `installer/linux/output/`.

### Docker mode — details

- **Incremental between runs** (fast local iterations): `build/cache`, `external/` and `.venv` persist; the startup cleanup only touches `build/pyinstaller`, `dist/`, `bin/`, `installer/linux/output` (`sudo rm -rf` fallback for root-owned leftovers of interrupted runs).
- `BUILD_JOBS=16` in the container (local host); the CI runner uses the default `-j` (4 vCPUs).
- The produced AppImage is copied into `installer/linux/output/` and ownership is restored (`chown`).
- **Golden rule**: the docker sim anticipated every Linux fix (Vulkan headers, Qt deps, `file` for appimagetool) — test it BEFORE committing changes to the Linux pipeline.

### Testing the CI without dirtying git

Local edit → `scripts/ci-linux.sh docker` until green → **a single commit** (e.g. `fix(ci): ...`) → push → `gh workflow run release.yml --ref <branch> -f os=all` → merge `--no-ff` into `dev`.
