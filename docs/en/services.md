# `services/` Component — Pipeline orchestration

## `services/processing_service.py` — Orchestrator + Qt channel

It is the heart of the flow: it receives the parameters (dict) from the UI or the CLI, orchestrates the stages and reports state through **Qt signals** (they also work headless, because the CLI uses a `QCoreApplication`, see `main.py:36`).

### Exposed signals (processing_service.py:20-24)

| Signal | Type | Usage |
|---|---|---|
| `started_signal` | () | processing started |
| `stage_changed_signal` | (str) | stage change ("Downloading YouTube...", "Checking model...", "Transcribing..." etc.) |
| `log_signal` | (str) | log lines (including whisper-cli stdout) |
| `progress_signal` | (int) | percentage 0-100 |
| `finished_signal` | (bool, str) | final outcome |

### Architecture

- **`ProcessingService` is a `QObject`**: `main_window.py:291-303` moves it to a `QThread` (`moveToThread`) and connects `start_processing_signal` (emitted by the UI) to its `start_processing()` — the whole pipeline runs off the GUI thread.
- **State**: two `threading.Event`s — `_stop_event` (cancellation requested) and `_working_event` (processing in progress, anti double-start guard, `_check_cancelled`).
- **Binaries**: `_find_bin_path()` (processing_service.py:41) locates `bin/` (project root in dev, `resource_path("bin")` in the bundle) and builds `WhisperCppManager` with ConfigManager's `models_dir`.

### Pipeline `start_processing(params)` (processing_service.py:56)

1. **Preconditions**: if `subs_mode != none` and YouTube input with `yt_mode=audio` → forces `yt_mode=video` (subtitles need the video).
2. **Input** (`_handle_input`, processing_service.py:177): YouTube → `YoutubeManager.run()` (the downloaded path goes into `_generated_files` for cleanup); local file → existence check; for videos it stores `_video_source`.
3. **Model**: `whisper_manager.download_model()` — no-op if already cached, otherwise download with progress and cancellation.
4. **Conversion**: `convert_to_wav_16khz()` → WAV PCM 16kHz mono in the same folder as the file (`<file>_16khz.wav`, tracked for cleanup).
5. **Transcription**: `run_whisper()` with `total_duration` obtained from `get_audio_duration()` (ffprobe).
6. **GPU→CPU fallback** (processing_service.py:144): if the first attempt fails and `device_mode == "gpu"`, it logs `[!] GPU failure detected` and retries in CPU mode (`-ng`).
7. **Subtitles** (`_apply_subtitles`, processing_service.py:201): if requested, reads `<name>.srt` and calls `embed_subtitles()` (soft: `_subs` + source extension) or `burn_subtitles()` (hard: `_burned.mp4`), with progress and the ffmpeg process registry (`_ffmpeg_processes`).
8. **Cleanup** (`_cleanup_and_finish`, processing_service.py:250):
   - cancellation → removes all `_generated_files` + partial outputs (srt/vtt/txt/tsv/json of the prefix);
   - success → removes only the temporary WAV.

### Stop (`stop()`, processing_service.py:282)

Sets `_stop_event`, then interrupts in cascade: yt-dlp (`yt_manager.stop()`), whisper-cli (`whisper_manager.stop_process()`), every registered ffmpeg process (terminate → wait 3s → kill). Cooperative cleanup happens when the pipeline resumes (every stage checks `_stop_event`).

### Notes

- Every stage emits `stage_changed_signal` and resets the progress: the UI shows the stage in the progress bar format (`"<stage> - %p%"`, see [ui.md](ui.md)).
- `params` does not contain `device_mode`: it is read directly from the config at transcription time (changeable from the settings).
