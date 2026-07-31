# Third-Party Notices

WhisperGUI is licensed under the GNU General Public License v3.0 — see the
`LICENSE` file. This document lists the third-party components bundled with,
or used to build, WhisperGUI, together with their licenses and copyright
holders. The full license texts are in the `licenses/` directory.

## Bundled components (distributed with the application)

| Component | Version | Source | License | Copyright |
|---|---|---|---|---|
| whisper.cpp (whisper-cli engine) | v1.9.1 | https://github.com/ggml-org/whisper.cpp | MIT | 2023-2026 The ggml authors |
| Whisper ggml models (downloaded at runtime from Hugging Face) | latest | https://huggingface.co/ggerganov/whisper.cpp | MIT | 2022 OpenAI |
| PyQt6 | 6.11.0 | https://www.riverbankcomputing.com | GPL v3 (or commercial) | Riverbank Computing Limited |
| Qt (bundled with PyQt6) | 6.11.0 | https://www.qt.io | LGPL v3 | The Qt Company Ltd. and contributors |
| FFmpeg / ffprobe (static builds) | n7.1 (Windows), release (Linux), 8.1 (macOS) | https://github.com/BtbN/FFmpeg-Builds · https://johnvansickle.com/ffmpeg · https://www.osxexperts.net | GPL v3 (BtbN, johnvansickle), GPL v2+ (osxexperts); FFmpeg base: LGPL v2.1+ | FFmpeg developers |
| yt-dlp | 2026.7.4 | https://github.com/yt-dlp/yt-dlp | Unlicense | yt-dlp contributors |
| platformdirs | 4.11.0 | https://github.com/platformdirs/platformdirs | MIT | platformdirs developers |

## Build-time components (not distributed, listed for completeness)

| Component | Version | Source | License | Copyright |
|---|---|---|---|---|
| PyInstaller | 6.21.0 | https://github.com/pyinstaller/pyinstaller | GPL v2 + bootloader exception | PyInstaller project |
| Vulkan-Headers | 1.4.313.0 | https://github.com/KhronosGroup/Vulkan-Headers | Apache-2.0 | Khronos Group |
| shaderc (glslc) | LunarG 1.4.313.0 | https://github.com/google/shaderc | Apache-2.0 | Google LLC |
| spirv-headers | 1.4.341 | https://github.com/KhronosGroup/SPIRV-Headers | MIT (multi-license file) | Khronos Group |
| NSIS | 3.12 | https://nsis.sourceforge.io | zlib/libpng (+ bzip2, CPL-1.0 for LZMA) | NSIS contributors |

License texts for all components above are available in the `licenses/`
directory of this repository and inside every distributed bundle.
