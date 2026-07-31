# `ui/` Component — PyQt6 Interface

Two modules: the main window and the settings dialog.

## `ui/main_window.py` — Main window

`MainWindow(QWidget)` builds the whole GUI and connects the signals to the `ProcessingService` (which runs on a `QThread`).

### UI structure (`init_ui`, main_window.py:34)

- **Input Source** (`QGroupBox`):
  - output name (`name_entry`), YouTube / Audio File / Video File radios (`input_type_group`);
  - path/link field + browse button (disabled in YouTube mode);
  - output folder with browse;
  - "Download YouTube" combo: Audio only (`audio`) / Audio + Video (`video`).
- **Whisper Settings**:
  - **Category** combo (`category_combo`, main_window.py:100) populated from `core/model_manager.get_categories()` with colored tier icons (potato/laptop/desktop/highend);
  - 4 model radios (`model_radio_a..d`) filled by `_on_category_changed()` (main_window.py:441) with the models of the selected category;
  - model info label (ID + quantization, `_update_model_info`, main_window.py:455);
  - language combo (auto/en/it/es/fr/de/ja/zh/ru), output format (srt/vtt/txt/tsv/json/**all**), subtitles (None/soft track/burned-in), task (Transcribe/Translate).
- **Log area**: read-only collapsible `QTextEdit` (`toggle_log_button` arrow), with dynamic window resizing (`_update_minimum_height`, main_window.py:521).
- **Bottom bar**: settings button, STOP (red, disabled at rest), START (highlighted, disabled during processing).
- Style: `apply_stylesheet()` (main_window.py:249) — Fusion style + stylesheet with rounded borders and colored buttons.

### Thread and signals (`setup_processing_thread`, main_window.py:291)

```
QThread ── moveToThread ──> ProcessingService
UI ── start_processing_signal(params) ──> service.start_processing
service.started_signal        ──> on_processing_started      (disables START, enables STOP)
service.stage_changed_signal  ──> on_stage_changed           (progress format "stage - %p%")
service.log_signal            ──> log_output                 (append + autoscroll)
service.progress_signal       ──> update_progress_bar
service.finished_signal       ──> on_processing_finished     (QMessageBox outcome)
```

### Behavior

- **`run_process()`** (main_window.py:353): validates input/output, applies the subtitle constraints (SRT or "all" format + video source, forces `yt_mode=video`), saves the current choices into the config (`model_category`, `model_index`, `output_format`, `output_dir`, `yt_mode`, `subs_mode`) and emits `start_processing_signal(params)`.
- **`stop_process()`** (main_window.py:412): confirms with `QMessageBox`, disables STOP and calls `processing_service.stop()`.
- **`closeEvent()`** (main_window.py:542): with an active job asks for confirmation; always: `processing_thread.quit() + wait()`.
- **`load_settings()`** (main_window.py:316): restores category/model/language/format/task/yt_mode/subs_mode from the config; the output folder is shown only if different from the default (placeholder with the default).
- File dialogs are filtered by type (audio/video) and the output name is auto-filled from the file name (`show_file_dialog`, main_window.py:477).
- `changeEvent` reapplies the Fusion style on palette change (system dark theme).

## `ui/settings_dialog.py` — Settings dialog

`SettingsDialog(QDialog)` (settings_dialog.py:8) — minimal and self-explanatory:

- **Transcription Engine**: info box ("the software now performs transcription entirely in native mode via whisper.cpp; missing models will be downloaded automatically").
- **Hardware Acceleration**: GPU radio (Vulkan, default) / CPU only — on `accept()` it saves `device_mode` into the config (`settings_dialog.py:56-59`).
- On close, `main_window.py:466-469` reloads the settings (`open_settings_dialog` → `dialog.exec()` → `load_settings()`).
