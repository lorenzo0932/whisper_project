# Whisper GUI

<p align="center">
  <strong>A user-friendly graphical interface for OpenAI's Whisper, simplifying the transcription and translation of audio from files or YouTube links.</strong>
<!-- </p>
<p align="center">
  You can replace this with a real screenshot of your application 
  <img src="image/WhisperGUIImage.png" alt="Whisper GUI Screenshot" width="700">
</p> -->

<!-- GIF 1: Main workflow from local 'media' folder -->
<p align="center">
  <img src="media/workflow.gif" alt="Whisper GUI Main Workflow Demo">
</p>

---

## 🎯 Why WhisperGUI?

WhisperGUI exists to make AI transcription **simple, private and truly local**.

Most transcription tools send your audio to a cloud service: convenient, but you lose control over your data and you depend on a connection. WhisperGUI takes the opposite approach — it is a **standalone desktop application** that runs the entire pipeline on your own machine:

*   **100% local and private** — audio never leaves your computer, no accounts, no cloud, no quotas.
*   **Native inference with whisper.cpp** — a highly optimized C++ port of OpenAI's Whisper that runs directly on your hardware, accelerated by **Vulkan** (Linux/Windows) or **Metal + CoreML** (macOS), with automatic CPU fallback when no GPU is available.
*   **Zero runtime dependencies** — no Python, no Docker, no ffmpeg installation needed. The app ships as a self-contained bundle (AppImage / DMG / NSIS installer) with the engine and static FFmpeg included.
*   **One-click installation** — download the artifact for your platform, run it, done.
*   **Flexible input** — local audio/video files or YouTube links (via yt-dlp), with optional subtitle integration into the video (soft track or burned).

The project started as a thin GUI over an API and evolved into a fully self-contained, cross-platform desktop app — the goal is simply: **paste a link or pick a file, and get your transcription without leaving your machine**.

---

## ✨ Key Features

*   **Flexible Input**: Process local audio/video files or simply paste a YouTube link.
*   **Native Local Execution**: Transcription powered by whisper.cpp (Vulkan/Metal + CPU fallback), fully offline after the first model download.
*   **Whisper Integration**: Leverages OpenAI's powerful models for accurate transcriptions and translations.
*   **Intuitive User Interface**: A clean and easy-to-use interface built with PyQt6.
*   **Customizable Output**: Choose between SRT, VTT, TXT, TSV, JSON or "all" formats.
*   **Subtitle Integration**: Embed the generated subtitles directly into the video as a soft track (`*_subs.mp4`) or burned into the image (`*_burned.mp4`).
*   **Flexible YouTube Downloads**: Choose between audio-only or full audio+video download.
*   **Model Categories**: Pre-configured model tiers (Potato → High-End) matched to your hardware, auto-downloaded from HuggingFace on first use.
*   **Configurability**: Adjust settings like the output directory and hardware acceleration via a configuration file.

---

## 🚀 Getting Started

This guide will walk you through setting up and running the project on your local system.

### 📋 Prerequisites

Before you begin, ensure you have the following dependencies installed on your system.

*   **Python 3.13** or higher (only for developers; end users need no Python at all)
*   **CMake + C/C++ toolchain** (only to compile the whisper.cpp engine)
*   **Vulkan SDK / headers** (Linux/Windows) or **Xcode Command Line Tools** (macOS) — only to compile the engine
*   **Docker** (Optional, only required for the local CI simulation: `scripts/ci-linux.sh docker`)

### 🛠️ Installation

#### End user

Download the artifact for your platform from the latest GitHub release:

*   **Windows** — `WhisperGUI-x86_64-setup.exe`: double-click and follow the wizard (installs into `%LOCALAPPDATA%\WhisperGUI`, no admin required).
*   **macOS (Apple Silicon)** — `WhisperGUI-macOS-arm64.dmg`: open the DMG and drag `WhisperGUI.app` into the Applications folder.
*   **Linux** — `WhisperGUI-x86_64.AppImage`:
    ```bash
    # Double-click, or "managed" installation (extraction + application menu):
    curl -sL https://raw.githubusercontent.com/lorenzo0932/whisper_project/main/installer/linux/install.sh | bash
    # Launch with: whisper-gui
    ```

No Python or FFmpeg installation is required: the app bundles its own static binaries. Models are downloaded automatically on first use into the per-user cache directory (`~/.cache/WhisperGUI/models` on Linux, `~/Library/Caches/WhisperGUI/models` on macOS, `%LOCALAPPDATA%\WhisperGUI\cache\models` on Windows).

#### Developers

The build pipeline is unified in `build.py` (same commands on every OS, also used by the CI):

```bash
python3 build.py bootstrap      # creates .venv and installs dependencies
python3 build.py build-engine   # compiles whisper.cpp (Vulkan on Linux/Windows, Metal+CoreML on macOS) and downloads static ffmpeg/ffprobe
python3 build.py build          # packages the app (PyInstaller onedir)
python3 build.py package        # produces the OS artifact: AppImage / .dmg / NSIS setup.exe
python3 build.py install        # installs locally (Linux/macOS: ~/.local or ~/Applications; Windows: setup.exe)
```

*   `--skip-engine` to reuse the binaries already present in `bin/` (no recompilation).
*   Quick install from source: `./install.sh` (wrapper around `build.py`).
*   Per-OS install scripts (also for removal): `installer/linux/install.sh`, `installer/macos/install.sh`, NSIS setup on Windows.
*   Full component documentation: [`docs/en/`](docs/en/) (English) / [`docs/it/`](docs/it/) (Italian).

## ⚙️ Configuration

The project uses a `config.json` file to manage settings. This file is automatically created in `~/.config/WhisperGUI/` on the first run.

<!-- GIF 3: Advanced settings from local 'media' folder -->
<img src="media/settings.gif" alt="Configuration Settings" width="400" align="right">

Here are the key configuration options:

*   `device_mode`: `"gpu"` (Vulkan/Metal, default) or `"cpu"` (forces CPU, with automatic GPU→CPU fallback on GPU failure).
*   `language` / `task`: default language (`auto` for detection) and task (`transcribe` or `translate`).
*   `output_format`: `srt`, `vtt`, `txt`, `tsv`, `json` or `all`.
*   `input_dir` / `output_dir`: default directories for input files and results.
*   `model_category` / `model_index`: last selected model tier and position.
*   `yt_mode`: YouTube download mode (`audio` or `video`).
*   `subs_mode`: subtitle integration (`none`, `soft`, `burn`).

<br clear="right"/>

## ▶️ Usage

You can run the project via the graphical user interface or the command line.

### 🖥️ Graphical User Interface (GUI)

This is the easiest way to use the tool.

1.  **Launch the application:**
    ```bash
    python main.py
    ```
2.  **Choose your input source**:
    *   **YouTube**: Paste the link.
    *   **Audio/Video File**: Click the browse button to select a file.

    <!-- GIF 2: Input flexibility from local 'media' folder -->
    <img src="media/input_flexibility.gif" alt="Input Flexibility" >

3.  **Provide an output file name.** If left blank, a default name will be used.
4.  **Adjust Whisper settings**: Select the model category and model, language, and task (transcribe or translate).
5.  **Open the settings (gear icon)** to choose the hardware acceleration mode (GPU/Vulkan default, or CPU-only).
6.  **Optional - Integrate subtitles into the video**: Use the "Sottotitoli nel video" dropdown to embed the generated SRT as a soft track (MP4/MKV, toggleable in the player) or burned into the image (MP4). This requires the SRT format and a video source (local video file or YouTube in "Audio + Video" mode).
7.  **Optional - YouTube download mode**: Choose "Solo Audio" (default, audio-only download) or "Audio + Video" (full video download, required for subtitle integration).
8.  **Click "Start Process"** to begin! Progress will be displayed in the GUI.

### ⌨️ Command-Line Interface (CLI)

For automation or headless environments, the same pipeline is available via CLI:

```bash
python main.py --cli -f <file_or_youtube_link> [-m <model>] [-l <language>] [-t transcribe|translate] \
               [-o <output_dir>] [-n <name>] [-format srt|vtt|txt|tsv|json] \
               [--subs none|soft|burn] [--yt-mode audio|video]
```

*   **CLI with subtitle integration:**
    ```bash
    python main.py --cli -f video.mp4 --subs soft   # soft track (MP4/MKV)
    python main.py --cli -f video.mp4 --subs burn   # burned-in subtitles (MP4)
    python main.py --cli -f https://youtube.com/... --subs soft --yt-mode video
    ```

## 📂 Project Structure

```
.
├── main.py               # Entry point: GUI (default) or --cli (headless)
├── build.py              # Cross-platform build pipeline (bootstrap/engine/build/package/install)
├── core/                 # Core logic: whisper.cpp manager, YouTube manager, model manager
├── services/             # Processing service: orchestration + Qt signals
├── ui/                   # PyQt6 UI components (main window, settings dialog)
├── utils/                # Helper modules (config, resource paths, audio tools)
├── scripts/              # Icon generation, local CI simulation (ci-linux.sh)
├── installer/            # Per-OS installers (linux, macos, windows)
├── media/                # Contains GIFs and other media for the README
├── licenses/             # Third-party license texts (shipped in the bundle)
├── docs/                 # Component documentation: en/ (English), it/ (Italian)
└── README.md             # This file
```

Detailed documentation for each component is available in [`docs/en/`](docs/en/) (English) and [`docs/it/`](docs/it/) (Italian): [Architecture](docs/en/ARCHITETTURA.md), [core](docs/en/core.md), [services](docs/en/services.md), [ui](docs/en/ui.md), [utils](docs/en/utils.md), [build pipeline](docs/en/build-pipeline.md), [CI](docs/en/ci.md).

## 💡 Future Developments

*   Improve error handling and logging.
*   Expand the model catalog (GGUF variants, faster quantizations).
*   Optional packaged GPU drivers / vulkan ICD detection to improve first-run experience on systems without a driver.

## 📜 License

WhisperGUI is free software, released under the **GNU General Public License v3.0** — see the [`LICENSE`](LICENSE) file. You can use, modify and redistribute it freely, provided modified versions are distributed under the same license.

The application bundles third-party components (whisper.cpp, FFmpeg, PyQt6/Qt, yt-dlp, ...): their licenses and attributions are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), with the full license texts in [`licenses/`](licenses/). The license texts are also shipped inside every distributed bundle.
