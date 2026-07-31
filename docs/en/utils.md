# `utils/` Component — Helper modules

Three modules: user configuration, path resolution and audio utilities (ffmpeg/ffprobe).

## `utils/config_manager.py` — Configuration and user paths

`ConfigManager` (config_manager.py:9) centralizes config, cache and models using **platformdirs** (the only "service" dependency of the project, pinned in requirements.txt).

### Per-OS paths

| Item | platformdirs API | Linux | macOS | Windows |
|---|---|---|---|---|
| config (`config.json`) | `user_config_dir("WhisperGUI")` | `~/.config/WhisperGUI/` | `~/Library/Application Support/WhisperGUI/` | `%APPDATA%\WhisperGUI\` |
| cache (`cache_dir`) | `user_cache_dir("WhisperGUI")` | `~/.cache/WhisperGUI/` | `~/Library/Caches/WhisperGUI/` | `%LOCALAPPDATA%\WhisperGUI\cache\` |
| **models** | `cache_dir/models` (config_manager.py:13) | `~/.cache/WhisperGUI/models/` | `~/Library/Caches/WhisperGUI/models/` | `%LOCALAPPDATA%\WhisperGUI\cache\models\` |

### Responsibilities

- **Defaults**: `_get_default_config()` (config_manager.py:20) defines `device_mode=gpu`, `language=auto`, `task=transcribe`, `output_format=srt`, `model_category=desktop`, `model=large-v3-turbo-q5_0`, `yt_mode=audio`, `subs_mode=none`, input folder (`~/Downloads`) and output folder (`~/Documents/WhisperGUI`).
- **Loading**: `_load_config()` (config_manager.py:35) merges the defaults with the existing file (defaults cover missing keys; corrupted file → defaults with warning).
- **Saving**: `set()` (config_manager.py:47) writes indented JSON; `get(key, default)` and `get_default()` (used by the UI for the output-folder placeholder).
- `ensure_exists=True` creates the directories at instantiation.

### Notes

- Models **never** live in the bundle: they are downloaded to the user cache (see [ARCHITETTURA.md](ARCHITETTURA.md)).
- `ConfigManager()` is instantiated once in `main.py:56` and passed to UI, dialogs and service.

## `utils/resource_path.py` — Paths in the PyInstaller bundle

Two functions, used **everywhere** for resource/binary paths (rule: never hardcode paths, otherwise the onedir bundle breaks — PyInstaller moves everything to `_internal`):

- `resource_path(relative)` (resource_path.py:5): when running from source → project root; in the bundle (`sys._MEIPASS` present) → `_MEIPASS/relative`.
- `binary_name(name)` (resource_path.py:16): appends `.exe` on Windows.

Usage examples: icon `resource_path("icon/ai_studio_code.svg")` (main.py:82, main_window.py:36), binaries folder `resource_path("bin")` (processing_service.py:45), ffmpeg/ffprobe in `utils/audio_utils.py:12`.

## `utils/audio_utils.py` — Audio/video utilities (ffmpeg/ffprobe)

All functions resolve the binaries with `_find_binary()` (audio_utils.py:11): first `bin/` of the bundle (via `resource_path`), then fallback to the system PATH.

### Functions

| Function | Lines | Description |
|---|---|---|
| `get_audio_duration()` | audio_utils.py:17 | duration in seconds via `ffprobe -show_format -show_streams` (JSON); returns `None` on error. Used for the transcription progress. |
| `convert_to_wav_16khz()` | audio_utils.py:67 | `ffmpeg -ar 16000 -ac 1 -c:a pcm_s16le` → WAV PCM 16kHz mono, the format required by whisper.cpp. |
| `embed_subtitles()` | audio_utils.py:172 | adds the SRT file as a **soft track** in the output video (copies the original container and muxes the subtitles), with duration mapping and `-progress` for the callback. |
| `burn_subtitles()` | audio_utils.py:206 | **burns** the subtitles into the video frames (`subtitles` filter), output `*_burned.mp4`, with progress and cancellation. |

### Notes

- On Windows the subprocesses use `STARTUPINFO` with `STARTF_USESHOWWINDOW` (no flashing terminal windows).
- The embed/burn progress comes from `out_time_ms=...` on ffmpeg's stderr (`_OUT_TIME_MS_RE`, audio_utils.py:9) compared against the total duration.
- The ffmpeg processes are registered in the service's `process_registry` so they can be terminated on STOP.
