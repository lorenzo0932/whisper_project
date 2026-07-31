# Componente `utils/` — Moduli di supporto

Tre moduli: configurazione utente, risoluzione path e utility audio (ffmpeg/ffprobe).

## `utils/config_manager.py` — Configurazione e percorsi utente

`ConfigManager` (config_manager.py:9) centralizza config, cache e modelli usando **platformdirs** (unica dipendenza "di servizio" del progetto, pinnata in requirements.txt).

### Percorsi per-OS

| Cosa | API platformdirs | Linux | macOS | Windows |
|---|---|---|---|---|
| config (`config.json`) | `user_config_dir("WhisperGUI")` | `~/.config/WhisperGUI/` | `~/Library/Application Support/WhisperGUI/` | `%APPDATA%\WhisperGUI\` |
| cache (`cache_dir`) | `user_cache_dir("WhisperGUI")` | `~/.cache/WhisperGUI/` | `~/Library/Caches/WhisperGUI/` | `%LOCALAPPDATA%\WhisperGUI\cache\` |
| **modelli** | `cache_dir/models` (config_manager.py:13) | `~/.cache/WhisperGUI/models/` | `~/Library/Caches/WhisperGUI/models/` | `%LOCALAPPDATA%\WhisperGUI\cache\models\` |

### Responsabilità

- **Default**: `_get_default_config()` (config_manager.py:20) definisce `device_mode=gpu`, `language=auto`, `task=transcribe`, `output_format=srt`, `model_category=desktop`, `model=large-v3-turbo-q5_0`, `yt_mode=audio`, `subs_mode=none`, cartelle input (`~/Downloads`) e output (`~/Documents/WhisperGUI`).
- **Caricamento**: `_load_config()` (config_manager.py:35) fa merge dei default con il file esistente (i default coprono le chiavi mancanti; file corrotto → default con warning).
- **Salvataggio**: `set()` (config_manager.py:47) scrive JSON indentato; `get(key, default)` e `get_default()` (usato dalla UI per il placeholder della cartella di output).
- `ensure_exists=True` crea le directory all'istanziazione.

### Note

- I modelli **non** vivono mai nel bundle: vengono scaricati nella cache utente (vedi [ARCHITETTURA.md](ARCHITETTURA.md)).
- `ConfigManager()` è istanziato una volta in `main.py:56` e passato a UI, dialoghi e service.

## `utils/resource_path.py` — Path nel bundle PyInstaller

Due funzioni, usate **ovunque** per i path a risorse/binarie (regola: mai path hardcoded, altrimenti il bundle onedir si rompe — PyInstaller sposta tutto in `_internal`):

- `resource_path(relative)` (resource_path.py:5): in esecuzione da sorgente → root del progetto; nel bundle (presenza di `sys._MEIPASS`) → `_MEIPASS/relative`.
- `binary_name(name)` (resource_path.py:16): aggiunge `.exe` su Windows.

Esempi d'uso: icona `resource_path("icon/ai_studio_code.svg")` (main.py:82, main_window.py:36), cartella binari `resource_path("bin")` (processing_service.py:45), ffmpeg/ffprobe in `utils/audio_utils.py:12`.

## `utils/audio_utils.py` — Utility audio/video (ffmpeg/ffprobe)

Tutte le funzioni risolvono i binari con `_find_binary()` (audio_utils.py:11): prima `bin/` del bundle (via `resource_path`), poi fallback sul PATH di sistema.

### Funzioni

| Funzione | Righe | Descrizione |
|---|---|---|
| `get_audio_duration()` | audio_utils.py:17 | durata in secondi via `ffprobe -show_format -show_streams` (JSON); ritorna `None` su errore. Usata per il progresso della trascrizione. |
| `convert_to_wav_16khz()` | audio_utils.py:67 | `ffmpeg -ar 16000 -ac 1 -c:a pcm_s16le` → WAV PCM 16kHz mono, il formato richiesto da whisper.cpp. |
| `embed_subtitles()` | audio_utils.py:172 | aggiunge il file SRT come **traccia soft** nel video di output (copia il container originale e muxa i sottotitoli), con mappatura durata e `-progress` per il callback. |
| `burn_subtitles()` | audio_utils.py:206 | **incide** i sottotitoli nel frame video (`subtitles` filter), output `*_burned.mp4`, con progresso e annullamento. |

### Note

- Su Windows i subprocess usano `STARTUPINFO` con `STARTF_USESHOWWINDOW` (niente finestre a terminale lampeggianti).
- Il progresso di embed/burn deriva da `out_time_ms=...` dello stderr di ffmpeg (`_OUT_TIME_MS_RE`, audio_utils.py:9) rapportato alla durata totale.
- I processi ffmpeg vengono registrati nel `process_registry` del service per poter essere terminati su STOP.
