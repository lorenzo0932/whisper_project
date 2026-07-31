# `core/` Component — Domain logic

Three modules: whisper.cpp execution, YouTube downloads and model management.

## `core/whispercpp_manager.py` — whisper.cpp execution

Manages the lifecycle of the `whisper-cli` process (the native transcription engine).

### Responsibilities

- **Binary lookup**: in development `bin/whisper-cli` at the project root; in the PyInstaller bundle the `bin` directory added with `--add-data` (via `resource_path`, see `utils/resource_path.py`). On Windows the name becomes `whisper-cli.exe` (`binary_name`).
- **Model file resolution**: `_find_model_file()` (whispercpp_manager.py:35) looks for `ggml-<model>.gguf` or `.bin` in `models_dir` (the user cache).
- **Command building**: `run_whisper()` (whispercpp_manager.py:53) builds the CLI arguments:
  - `-m <model> -f <file> -of <output_prefix> -t <threads>` plus language (`-l`, unless `auto`), task `-tr` (translate), output format flags (`-osrt/-ovtt/-otxt/-otsv/-ojson`);
  - GPU (default) or CPU: in CPU mode it adds `-ng` and uses more threads (85% of cores vs 50% in GPU).
- **Per-OS env**: before launching it sets the library variable on the bundle `bin_dir` — `LD_LIBRARY_PATH` (Linux), `DYLD_LIBRARY_PATH` (macOS), `PATH` (Windows) — so the loader finds the Vulkan/Metal libraries next to the binary (whispercpp_manager.py:108-122).
- **Progress**: the % progress is derived by parsing the SRT timestamps printed by whisper-cli on stdout (`_TIMESTAMP_RE`, whispercpp_manager.py:12) compared against the file total duration (`total_duration`).
- **Stop**: `stop_process()` (whispercpp_manager.py:164) terminates the process cooperatively under `process_lock` (terminate → kill after 3s).

### Notes

- `current_process` and the lock protect the single active process per instance.
- Returns are always `(bool, message)` pairs consumed by the service for outcomes.
- `stop_process` handles interruption exit codes (-15/9/130) as "interrupted by user".

## `core/youtube_manager.py` — YouTube downloads

Wrapper around **yt-dlp** (bundled in the venv and in the PyInstaller bundle).

### Responsibilities

- `download_video()` (youtube_manager.py:29): downloads with the selected format:
  - `audio` mode → audio format chosen by yt-dlp (implicit `format`);
  - `video` mode → `merge_output_format = 'mp4'` (video+audio merged into MP4).
- **Progress**: `_progress_hook` (youtube_manager.py:19) extracts `_percent_str` from the `downloading` status (cleaned of ANSI escapes) and forwards it to the callback.
- **Result**: returns the path of the downloaded file, with a fallback for the real extension (`.mp4`/`.mkv`/`.webm`) because yt-dlp's `filepath` can point to a non-existent file before the merge.
- **Stop**: `stop()` interrupts the active `yt_dlp` (`self._ydl`).
- `noplaylist: True`: a playlist link downloads only the single video.

## `core/model_manager.py` — Model catalog and downloads

### Responsibilities

- **Catalog**: `CATEGORIES` (model_manager.py:9) defines 4 hardware tiers: `potato` (tiny/base q5_1), `laptop` (small/medium q5), `desktop` (medium q8_0, large-v2, large-v3-turbo), `highend` (large-v2/v3 up to f16, 6 GB). Each model: `id` (→ `ggml-<id>.bin`), label with size, quantization. `DEFAULT_CATEGORY = "desktop"`.
- **Resolution**: `get_category()`/`resolve_model_id(category, index)` used by the UI to map radio buttons → model id.
- **URL**: `MODEL_REPO = https://huggingface.co/ggerganov/whisper.cpp/resolve/main` — the official quantized whisper.cpp models.
- **Download**: `ModelManager.download_model()` (model_manager.py:90):
  - if the file already exists → OK with no network ("Model already in cache");
  - otherwise `urllib.request.urlretrieve` with a `reporthook` for progress, cancellation support via `is_cancelled_cb` and partial-file cleanup on cancel/error.
- **Path**: models are stored in the `models_dir` provided by ConfigManager (user cache, see [utils.md](utils.md)) — never inside the bundle.

### Notes

- The config default `model = large-v3-turbo-q5_0` implies a first download of ~2 GB; the potato/laptop tiers download hundreds of MB.
- `download_model()` is called by the service on every job: if the model is already present it's an immediate no-op.
