# WhisperGUI Architecture

> Component documentation. Index: [core](core.md) · [services](services.md) · [ui](ui.md) · [utils](utils.md) · [build pipeline](build-pipeline.md) · [CI](ci.md) — Italian version: [`docs/it/`](../it/)

## Overview

WhisperGUI is a **standalone, cross-platform** desktop application (Linux, macOS arm64, Windows) for local transcription and translation of audio/video using OpenAI Whisper via **whisper.cpp**.

The app is a **self-contained bundle** (PyInstaller onedir): it ships the Python interpreter, the PyQt6 GUI, the `whisper-cli` binary (a native engine compiled with the per-OS GPU backend) and static `ffmpeg`/`ffprobe`. End users install nothing: no Python, no FFmpeg, no explicit Vulkan drivers (system ones are used).

```
┌────────────────────────────────────────────────────────────┐
│  UI (PyQt6) — ui/main_window.py                            │
│  emits param dict on start_processing_signal (QThread)      │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│  services/processing_service.py  (orchestrator, in QThread) │
│  Qt signals: started / stage_changed / log / progress /      │
│              finished                                        │
└──┬──────────────┬──────────────────┬───────────────────────┘
   ▼              ▼                  ▼
┌──────────┐  ┌─────────────┐   ┌──────────────────┐
│youtube_  │  │model_       │   │whispercpp_       │
│manager   │  │manager      │   │manager           │
│(yt-dlp)  │  │(HF download)│   │(subprocess       │
│          │  │             │   │ whisper-cli)     │
└────┬─────┘  └──────┬──────┘   └───────┬──────────┘
     │               │                 │
     ▼               ▼                 ▼
 input file / YouTube ──► ffmpeg ──► WAV 16kHz mono ──► whisper-cli ──► SRT/VTT/TXT/TSV/JSON
                                                                    │
                                            (optional) ffmpeg ──► video with soft/burned subs
```

## End-to-end data flow

1. **Input**: a local audio/video file or a YouTube link.
   - YouTube → `core/youtube_manager.py` (yt-dlp), in `audio` mode (audio track only) or `video` mode (MP4 merge).
   - Local file → used directly.
2. **Model**: `core/model_manager.py` checks the model in the user cache; if missing, downloads it from HuggingFace (`ggml-<id>.bin` from the `ggerganov/whisper.cpp` repo) with progress/cancel callbacks. Models live **outside the bundle** in `user_cache_dir("WhisperGUI")/models` (see [utils.md](utils.md)).
3. **Audio conversion**: `utils/audio_utils.convert_to_wav_16khz()` — ffmpeg → WAV PCM 16kHz mono (the format required by whisper.cpp).
4. **Transcription**: `core/whispercpp_manager.run_whisper()` spawns `whisper-cli` as a subprocess with:
   - per-OS env to locate shared libraries (`LD_LIBRARY_PATH` Linux, `DYLD_LIBRARY_PATH` macOS, `PATH` Windows) pointing to the bundle `bin_dir`;
   - progress derived by parsing SRT timestamps on stdout (`_TIMESTAMP_RE`, `whispercpp_manager.py:12`) against the total duration;
   - GPU mode (default) or CPU (`-ng`), with threads allocated proportionally to `os.cpu_count()`.
5. **Output**: `srt|vtt|txt|tsv|json` file in the chosen output directory.
6. **(Optional) Subtitles in video**: if `subs_mode != none` and a video source exists, `utils/audio_utils.embed_subtitles()` (soft track `*_subs.mp4`) or `burn_subtitles()` (burned-in `*_burned.mp4`), with progress via ffmpeg `-progress`.
7. **Cleanup**: temporary files (`*_16khz.wav`, YouTube downloads when the input is YouTube) are removed; on cancellation partial output is cleaned too.

## Key decisions

- **Native backend, no Docker**: the project evolution replaced the Docker mode (and `insanely-fast-whisper`) with native whisper.cpp transcription: zero runtime dependencies for the user, no containers to manage.
- **All resource/binary paths go through `utils/resource_path.py`**: in development it points to the project root; in the PyInstaller onedir bundle it points to `_internal` (see [utils.md](utils.md)).
- **Automatic GPU → CPU fallback**: if `whisper-cli` fails in GPU mode, `processing_service` retries transcription with `-ng` (`processing_service.py:144`).
- **Responsive UI**: `ProcessingService` is a `QObject` moved to a `QThread` (`main_window.py:291-303`); Qt signals are the only communication channel (they also work headless with `QCoreApplication`, used by `main.py --cli`).
- **Cooperative cancellation**: a `threading.Event` stop flag is checked at every stage (model download, conversion, transcription, subtitles); processes (whisper-cli, yt-dlp, ffmpeg) are terminated and partial files deleted.
- **Model categories**: `core/model_manager.py` organizes models in tiers (potato → highend) with quantizations suited to the hardware; the config default is `large-v3-turbo-q5_0` (~1.6-2 GB) — the first download can be large.

## Module dependencies

```
main.py
 ├─ ui/main_window.py ── services/processing_service.py
 │      └─ ui/settings_dialog.py     ├─ core/whispercpp_manager.py ── core/model_manager.py
 │      └─ utils/config_manager.py   ├─ core/youtube_manager.py
 │      └─ core/model_manager.py     └─ utils/audio_utils.py
 │                                   └─ utils/resource_path.py
 └─ utils/config_manager.py
```
