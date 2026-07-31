# Componente `ui/` — Interfaccia PyQt6

Due moduli: la finestra principale e il dialogo impostazioni.

## `ui/main_window.py` — Finestra principale

`MainWindow(QWidget)` costruisce tutta la GUI e collega i segnali al `ProcessingService` (che gira su un `QThread`).

### Struttura della UI (`init_ui`, main_window.py:34)

- **Input Sorgente** (`QGroupBox`):
  - nome output (`name_entry`), radio YouTube / File Audio / File Video (`input_type_group`);
  - campo path/link + pulsante browse (disabilitato in modalità YouTube);
  - cartella di output con browse;
  - combo "Download YouTube": Solo Audio (`audio`) / Audio + Video (`video`).
- **Impostazioni Whisper**:
  - combo **Categoria** (`category_combo`, main_window.py:100) popolata da `core/model_manager.get_categories()` con icone colorate per tier (potato/laptop/desktop/highend);
  - 4 radio modello (`model_radio_a..d`) riempite da `_on_category_changed()` (main_window.py:441) con i modelli della categoria selezionata;
  - label info modello (ID + quantizzazione, `_update_model_info`, main_window.py:455);
  - combo lingua (auto/en/it/es/fr/de/ja/zh/ru), formato output (srt/vtt/txt/tsv/json/**all**), sottotitoli (Nessuno/Traccia soft/Incisi hard), task (Trascrivi/Traduci).
- **Area log**: `QTextEdit` read-only collassabile (pulsante `toggle_log_button`, arrow), con resize dinamico della finestra (`_update_minimum_height`, main_window.py:521).
- **Barra inferiore**: pulsante impostazioni, STOP (rosso, disabilitato a riposo), START (evidenziato, disabilitato durante l'elaborazione).
- Stile: `apply_stylesheet()` (main_window.py:249) — style Fusion + stylesheet con bordi arrotondati, pulsanti colorati.

### Thread e segnali (`setup_processing_thread`, main_window.py:291)

```
QThread ── moveToThread ──> ProcessingService
UI ── start_processing_signal(params) ──> service.start_processing
service.started_signal        ──> on_processing_started      (blocca START, abilita STOP)
service.stage_changed_signal  ──> on_stage_changed           (formato progress "fase - %p%")
service.log_signal            ──> log_output                 (append + autoscroll)
service.progress_signal       ──> update_progress_bar
service.finished_signal       ──> on_processing_finished     (QMessageBox esito)
```

### Comportamento

- **`run_process()`** (main_window.py:353): valida input/output, applica i vincoli dei sottotitoli (formato SRT o "all" + sorgente video, forzatura `yt_mode=video`), salva le scelte correnti nella config (`model_category`, `model_index`, `output_format`, `output_dir`, `yt_mode`, `subs_mode`) ed emette `start_processing_signal(params)`.
- **`stop_process()`** (main_window.py:412): conferma con `QMessageBox`, disabilita STOP e chiama `processing_service.stop()`.
- **`closeEvent()`** (main_window.py:542): con elaborazione attiva chiede conferma; sempre: `processing_thread.quit() + wait()`.
- **`load_settings()`** (main_window.py:316): ripristina categoria/modello/lingua/formato/task/yt_mode/subs_mode dalla config; la cartella di output è mostrata solo se diversa dal default (placeholder col default).
- I dialoghi file sono filtrati per tipo (audio/video) e il nome output viene autocompilato dal nome file (`show_file_dialog`, main_window.py:477).
- `changeEvent` riapplica lo stile Fusion al cambio palette (tema scuro del sistema).

## `ui/settings_dialog.py` — Dialogo impostazioni

`SettingsDialog(QDialog)` (settings_dialog.py:8) — minimale e autoesplicativo:

- **Motore di Trascrizione**: riquadro informativo ("il software ora esegue la trascrizione interamente in modalità nativa tramite whisper.cpp; i modelli mancanti verranno scaricati in automatico").
- **Accelerazione Hardware**: radio GPU (Vulkan, predefinita) / Solo CPU — all'`accept()` salva `device_mode` nella config (`settings_dialog.py:56-59`).
- Alla chiusura, `main_window.py:466-469` ricarica le impostazioni (`open_settings_dialog` → `dialog.exec()` → `load_settings()`).
