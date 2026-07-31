# WhisperGUI Next-Gen — Roadmap

Obiettivo: trasformare WhisperGUI in un'applicazione desktop cross-platform standalone
(no Python, no Docker) con trascrizione via whisper.cpp (Vulkan/Metal + CPU fallback),
download YouTube resiliente e installazione one-click per Linux/macOS/Windows.

## Branch Strategy

```
dev (base)
├── feat/platformdirs-config   → config_manager.py: platformdirs
├── feat/model-manager         → core/model_manager.py: categorie + GGUF
├── feat/youtube-manager-rename → core/youtube_manager.py: rename + stop()
├── feat/ytdlp-autoupdate      → utils/ytdlp_loader.py: (RIMOSSO — yt-dlp bundlato)
├── fix/whispercpp-manager     → core/whispercpp_manager.py: GGUF, fix
├── fix/processing-service     → services/processing_service.py: thread safety
├── feat/gui-model-selector    → ui/main_window.py: combo box categorie
├── feat/ci-cd-release         → .github/workflows/release.yml + installer
└── feat/installer-standardization → build.py + installers per-OS (in corso)
```

Ogni branch parte da `dev`, merge in `dev` via PR dopo implementazione.

---

## Architettura Finale

```
whisper_project/
├── main.py                       # Entry point GUI + CLI
├── build.py                      # Pipeline build cross-platform (bootstrap/engine/build/package/install)
├── requirements.txt              # PyQt6, yt-dlp, platformdirs, pyinstaller
├── ROADMAP.md
├── core/
│   ├── __init__.py
│   ├── whispercpp_manager.py     # whisper.cpp subprocess (Vulkan/Metal/CPU)
│   ├── youtube_manager.py        # yt-dlp download YouTube (audio o audio+video)
│   └── model_manager.py          # Download/gestione modelli GGUF
├── services/
│   ├── __init__.py
│   └── processing_service.py     # Orchestratore (input → audio → whisper → sottotitoli)
├── ui/
│   ├── __init__.py
│   ├── main_window.py            # Finestra principale PyQt6
│   └── settings_dialog.py        # Impostazioni
├── utils/
│   ├── __init__.py
│   ├── config_manager.py         # Path OS-standard (platformdirs)
│   ├── resource_path.py          # Path risorse bundle (PyInstaller) + .exe suffix
│   ├── audio_utils.py            # ffprobe/ffmpeg + embed/burn sottotitoli
│   └── ytdlp_loader.py           # Import wrapper per yt_dlp
├── bin/                          # whisper-cli + ffmpeg/ffprobe (per piattaforma)
├── media/                        # GIF, icone
├── installer/
│   ├── linux/
│   │   └── install.sh            # AppImage → ~/.local/lib + wrapper + .desktop
│   ├── macos/
│   │   └── install.sh            # DMG → /Applications + symlink CLI
│   └── windows/
│       └── whispergui.nsi        # Setup NSIS (per-user, PATH opzionale)
└── .github/
    └── workflows/
        └── release.yml           # CI/CD multi-piattaforma (delega a build.py)
```

---

## Fasi Implementazione

### Fase 0 — Pulizia Repo

Branch: diretto su `dev` (commit singolo)

Azioni:
1. Eliminare file morti: `DA_VERIFICARE`, `temp_689944.tar`, `launch.sh`
2. Eliminare directory: `build_venv/`, `dist/` (se versionata), `.vscode/`
3. Sostituire `requirements-*.txt` con unico `requirements.txt`:
   ```
   PyQt6
   yt-dlp
   platformdirs
   ```
4. Aggiornare `.gitignore`: aggiungere `build_venv/`, `dist/`, `*.egg-info/`, `build/`, `ROADMAP.md`
   (questo è già stato parzialmente fatto nei commit locali)

File modificati:
- `DA_VERIFICARE` → eliminato
- `temp_689944.tar` → eliminato
- `launch.sh` → eliminato (già fatto)
- `.gitignore` → già modificato
- `requirements-*.txt` → sostituito da `requirements.txt`
- `whisper-gui-bin.spec` → eliminato (PyInstaller, non più usato)
- `nuitka-crash-report.xml` → eliminato

Commit: `chore: cleanup repository - remove dead files, consolidate requirements`

---

### Fase 1 — Path OS-standard (config_manager.py)

Branch: `feat/platformdirs-config`
Base: `dev`

Modifiche a `utils/config_manager.py`:

Prima (hardcoded):
```python
self.config_dir = os.path.join(os.path.expanduser("~"), ".config", app_name)
self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", app_name)
self.models_dir = os.path.join(self.cache_dir, "models")
```

Dopo (platformdirs):
```python
from platformdirs import user_config_dir, user_cache_dir

self.config_dir = user_config_dir(app_name, ensure_exists=True)
self.cache_dir = user_cache_dir(app_name, ensure_exists=True)
self.models_dir = os.path.join(self.cache_dir, "models")
```

Risultato per ogni OS:
| OS | Config | Cache |
|----|--------|-------|
| Linux | `~/.config/WhisperGUI` | `~/.cache/WhisperGUI` |
| macOS | `~/Library/Application Support/WhisperGUI` | `~/Library/Caches/WhisperGUI` |
| Windows | `%APPDATA%/WhisperGUI` | `%LOCALAPPDATA%/WhisperGUI` |

Aggiungere dipendenza `platformdirs` a `requirements.txt`.

Rimuovere logica `base_path` da `ProcessingService` (processing_service.py righe 25-27) —
era un workaround per path relativi da .desktop, non serve più con path OS-standard.

Commit: `feat: use platformdirs for OS-standard config/cache paths`

---

### Fase 2 — ModelManager (core/model_manager.py)

Branch: `feat/model-manager`
Base: `dev`

Nuovo file `core/model_manager.py`.

Struttura categorie:

| Categoria | Modello 1 | Modello 2 | Uso |
|-----------|-----------|-----------|-----|
| Potato | tiny (q5_k_m, ~200MB) | base (q5_k_m, ~400MB) | PC vecchi, Raspberry Pi |
| Laptop | small (q5_k_m, ~1GB) | medium (q5_k_m, ~1.5GB) | Bilanciato qualità/velocità |
| Desktop | medium (q8_0, ~2.5GB) | large-v3-turbo (q5_k_m, ~2GB) | Consigliato per desktop |
| High-End | large-v3 (q5_k_m, ~3.5GB) | large-v3 (f16, ~6GB) | Massima accuratezza |

Download URL (aggiornato): `https://huggingface.co/ggml-org/whisper.cpp/resolve/main/ggml-{model}-{quant}.gguf`

Formato file modello: `ggml-{model}-{quant}.gguf`

Metodi principali:
- `get_categories()` → lista categorie
- `get_models_for_category(category)` → lista modelli per categoria
- `get_model_filename(model_id, quant)` → nome file
- `get_download_url(model_id, quant)` → URL
- `download_model(model_id, quant, progress_callback, log_callback, is_cancelled_cb)` → download
- `get_model_path(model_id, quant)` → path locale
- `is_model_downloaded(model_id, quant)` → check cache

Se un modello `.bin` (GGML vecchio) esiste già in cache, supportarlo lo stesso
(backward compatibility). Il download di nuovi modelli usa sempre `.gguf`.

Commit: `feat: add ModelManager with human-friendly categories and GGUF support`

---

### Fase 3 — YoutubeManager rename + fix

Branch: `feat/youtube-manager-rename`
Base: `dev`

1. Rinominare `core/youtube_manager.py` → `core/youtube_manager.py` (stesso nome file,
   ma classe `Youtube_manager` → `YoutubeManager`)

2. Aggiungere metodo `stop()`:
```python
def stop(self):
    """Interrompe il download yt-dlp in corso."""
    if hasattr(self, '_ydl') and self._ydl:
        self._ydl.params['quiet'] = True  # evita noise in stderr
```

   Aggiornare processing_service.py per salvare riferimento a `self._ydl` nel `_progress_hook`.

3. Rimuovere `format_id` dal costruttore (non usato). Sostituire con logica `bestaudio/best`
   automatica.

4. Fix parsing percentuale ANSI: regex invece di strip semplice.

Commit: `refactor: rename Youtube_manager to YoutubeManager, add stop() method`

---

#~~## Fase 4 — yt-dlp Auto-Update Bloccante (RIMOSSA)~~

~~Branch: `feat/ytdlp-autoupdate`~~
Base: `dev`

~~RIMOSSA. yt-dlp viene bundlato dentro l'eseguibile standalone al momento della build
(PyInstaller). L'auto-update non funziona in bundle perché il modulo yt_dlp è congelato.~~
~~Per avere una versione più recente di yt-dlp, l'utente scarica una nuova release di
WhisperGUI.~~

---

### Fase 5 — Fix whispercpp_manager.py

Branch: `fix/whispercpp-manager`
Base: `dev`

Modifiche a `core/whispercpp_manager.py`:

1. **Supporto GGUF**: in `run_whisper()` e `download_model()`, cercare anche `.gguf`
   oltre a `.bin`. Se il modello richiesto è `.gguf`, usare nome appropriato.

2. **`except: pass`** (righe 70, 186, 193): sostituire con `logging.warning()` o
   `logging.error()`.

3. **Regex timestamp**: da locale in `run_whisper()` a costante di classe:
   ```python
   class WhisperCppManager:
       _TIMESTAMP_RE = re.compile(...)
   ```

4. **Path injection** (riga 109): aggiungere `'--', file_path` prima di `file_path`
   per evitare che un path con `-` venga interpretato come flag.

5. **`LD_LIBRARY_PATH`** (riga 131): loggare la modifica. Documentare nel README
   che Vulkan richiede `libvulkan.so.1` nel sistema.

6. **Download modello** (riga 31): URL aggiornato a `ggml-org/whisper.cpp`.

Commit: `fix: add GGUF support, fix race conditions and error handling in whispercpp_manager`

---

### Fase 6 — Fix processing_service.py

Branch: `fix/processing-service`
Base: `dev`

1. **Race condition** (righe 20-21): `_is_working` e `_is_cancelled` → `threading.Event`:
   ```python
   self._stop_event = threading.Event()  # al posto di _is_cancelled
   self._working_event = threading.Event()  # al posto di _is_working
   ```

2. **`yt_manager.stop()`** (riga 215): dopo rename, funziona. Aggiornare controllo
   `hasattr(self.yt_manager, 'stop')` a chiamata diretta.

3. **Rimuovere `base_path`** (righe 25-27): non più necessario con `platformdirs`.

4. **Cleanup più robusto**: `_cleanup_and_finish` resettare eventi con `clear()`.

5. **`_handle_input`**: se input_type è "youtube", estrarre info senza scaricare
   (usare `ydl.extract_info(..., download=False)`) per validare il link prima del
   download vero.

Commit: `fix: use threading.Event for thread safety, remove legacy base_path workaround`

---

### Fase 7 — GUI: Combo Box Modelli Categorici

Branch: `feat/gui-model-selector`
Base: `dev`

Modifiche a `ui/main_window.py`:

Sostituire combo box piatto con:

1. **Combo box categoria**: `QComboBox` con items:
   - 🥔 Potato
   - 💻 Laptop
   - 🖥️ Desktop (default)
   - 🚀 High-End

2. **Radio button modello**: quando cambia categoria, aggiornare 2 `QRadioButton`
   con i modelli disponibili per quella categoria.

3. **Label informativa**: sotto i radio button, mostra:
   - Nome modello (es. `large-v3-turbo`)
   - Dimensione stimata (es. `~2GB`)
   - Quantizzazione (es. `q5_k_m`)

4. **Logica backend**: quando l'utente clicca "Avvia", tradurre la selezione in
   `model_id` + `quant` da passare a `ModelManager`.

Struttura layout:
```
┌──────────────────────────────────┐
│ Categoria:   [▾ Desktop       ] │
│                                   │
│ Modello:     ○ medium (q8_0)     │
│              ○ large-v3-turbo    │
│                                   │
│ Info: large-v3-turbo q5_k_m ~2GB │
└──────────────────────────────────┘
```

Commit: `feat: replace flat model list with category-based model selector in GUI`

---

### Fase 8 — CI/CD + Installer

### Pacchettizzazione: PyInstaller (non Nuitka)

Usiamo **PyInstaller** invece di Nuitka perché:
- Build molto più veloce (~1 min vs ~15 min)
- Nessun crash di compilazione o bug di compatibilità
- Stesso risultato: singolo eseguibile standalone
- Flag: `pyinstaller --onefile --add-data "bin:bin" --add-data "media:media" --name WhisperGUI main.py`

Branch: `feat/ci-cd-release`
Base: `dev`

Creare `.github/workflows/release.yml`:

```yaml
name: Build & Release
on:
  push:
    tags: ['v*']

jobs:
  build-linux:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Build whisper.cpp (Vulkan)
        run: |
          cmake -B build -DGGML_VULKAN=ON
          cmake --build build -j
          cp build/bin/whisper-cli bin/
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Build executable (PyInstaller)
        run: |
          pip install pyinstaller PyQt6 yt-dlp platformdirs
          pyinstaller --onefile \
            --add-data "bin:bin" --add-data "media:media" \
            --name WhisperGUI main.py
          mv dist/WhisperGUI dist/WhisperGUI-x86_64.AppImage
      - name: Upload Release Asset
        uses: softprops/action-gh-release@v2
        with:
          files: dist/WhisperGUI-x86_64.AppImage

  build-macos:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - name: Build whisper.cpp (Metal + CoreML)
        run: |
          cmake -B build -DGGML_METAL=ON -DWHISPER_COREML=ON
          cmake --build build -j
          cp build/bin/whisper-cli bin/
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Build executable (PyInstaller)
        run: |
          pip install pyinstaller PyQt6 yt-dlp platformdirs
          pyinstaller --onefile \
            --add-data "bin:bin" --add-data "media:media" \
            --name WhisperGUI main.py
          mv dist/WhisperGUI dist/WhisperGUI-macOS
      - name: Create .dmg
        run: |
          hdiutil create -volname "WhisperGUI" \
            -srcfolder dist/WhisperGUI-macOS \
            -ov -format UDZO \
            dist/WhisperGUI-macOS-universal.dmg
      - name: Upload Release Asset
        uses: softprops/action-gh-release@v2
        with:
          files: dist/WhisperGUI-macOS-universal.dmg

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build whisper.cpp (Vulkan)
        run: |
          cmake -B build -DGGML_VULKAN=ON
          cmake --build build --config Release -j
          copy build\bin\Release\whisper-cli.exe bin\
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Build executable (PyInstaller)
        run: |
          pip install pyinstaller PyQt6 yt-dlp platformdirs
          pyinstaller --onefile `
            --add-data "bin;bin" --add-data "media;media" `
            --name WhisperGUI main.py
          move dist\WhisperGUI.exe dist\WhisperGUI-x86_64.exe
      - name: Upload Release Asset
        uses: softprops/action-gh-release@v2
        with:
          files: dist\WhisperGUI-x86_64.exe
```

Installer script:

**Linux** (`installer/linux/install.sh`):
```bash
#!/bin/bash
# Installa WhisperGUI AppImage in userspace
set -e

APPIMAGE="WhisperGUI-x86_64.AppImage"
DEST="$HOME/.local/bin/whisper-gui"
DESKTOP="$HOME/.local/share/applications/whisper-gui.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$ICON_DIR"

cp "$APPIMAGE" "$DEST"
chmod +x "$DEST"

cat > "$DESKTOP" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WhisperGUI
Comment=Trascrizione AI nativa (Vulkan/Metal)
Exec=$DEST
Icon=whisper-gui
Terminal=false
Categories=AudioVideo;Audio;
EOF

# Usa icona dal bundle se presente
if [ -f "media/WhisperGUIImage.png" ]; then
    cp "media/WhisperGUIImage.png" "$ICON_DIR/whisper-gui.png"
fi

echo "WhisperGUI installato in $DEST"
```

**macOS** (`installer/macos/install.sh`): monta .dmg e copia in /Applications.

**Windows** (`installer/windows/install.ps1`): copia .exe e aggiorna PATH utente.

Commit: `feat: add GitHub Actions CI/CD with multi-platform builds and installers`

---

## Versioning

Formato: `v{major}.{minor}.{patch}` (es. `v1.0.0`)

Prima release: `v1.0.0`

Ogni push di un tag `v*` triggera la pipeline CI/CD.

---

## Dipendenze

```
# requirements.txt (runtime)
PyQt6
yt-dlp
platformdirs

# build (aggiunto solo per compilare l'eseguibile standalone)
pyinstaller
```

Non serve `torch`, `torchaudio`, `torchvision`, `openai-whisper`, `requests`, `nuitka`.

---

## Note Tecniche

- whisper.cpp: `github.com/ggml-org/whisper.cpp`, tag `v1.9.1` (Jun 2026)
- Modelli: `huggingface.co/ggml-org/whisper.cpp`
- yt-dlp: bundlato nell'eseguibile via PyInstaller, nessun auto-update runtime
- Python: 3.13+ (usare 3.13 per compatibilità Nuitka)
- Formato modelli: GGUF (`.gguf`), con backward compatibility per `.bin` (GGML)
- Vulkan: richiede `libvulkan.so.1` sul sistema (tipicamente preinstallato)
- macOS: Metal + CoreML via `-DGGML_METAL=ON -DWHISPER_COREML=ON`
- Build PyInstaller: `pyinstaller --onefile --add-data "bin:bin" --add-data "media:media" --name WhisperGUI main.py`

---

## Stati di Avanzamento

| # | Fase | Branch | Stato |
|---|------|--------|-------|
| 0 | Pulizia repo | `dev` (direct) | [x] |
| 1 | Path OS-standard (platformdirs) | `feat/platformdirs-config` | [x] |
| 2 | ModelManager (categorie + GGUF) | `feat/model-manager` | [x] |
| 3 | YoutubeManager rename + stop() | `feat/youtube-manager-rename` | [x] |
| 4 | yt-dlp auto-update bloccante | `feat/ytdlp-autoupdate` | [x] (RIMOSSO — yt-dlp bundlato nella release) |
| 5 | Fix whispercpp_manager.py | `fix/whispercpp-manager` | [x] |
| 6 | Fix processing_service.py | `fix/processing-service` | [x] |
| 7 | GUI: combo box modelli categorici | `feat/gui-model-selector` | [x] |
| 8 | CI/CD + installer | `feat/ci-cd-release` | [x] |
| — | Ricompilare whisper.cpp v1.9.1 | `dev` | [x] |
| — | Release v1.0.0 | tag `v1.0.0` | [ ] |
