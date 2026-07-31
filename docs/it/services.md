# Componente `services/` — Orchestrazione della pipeline

## `services/processing_service.py` — Orchestratore + canale Qt

È il cuore del flusso: riceve i parametri (dict) dalla UI o dal CLI, orchestra le fasi e comunica lo stato tramite **segnali Qt** (funzionano anche headless, perché il CLI usa una `QCoreApplication`, vedi `main.py:36`).

### Segnali esposti (processing_service.py:20-24)

| Segnale | Tipo | Uso |
|---|---|---|
| `started_signal` | () | elaborazione avviata |
| `stage_changed_signal` | (str) | cambio fase ("Download YouTube...", "Controllo modello...", "Trascrizione in corso..." ecc.) |
| `log_signal` | (str) | righe di log (anche stdout di whisper-cli) |
| `progress_signal` | (int) | percentuale 0-100 |
| `finished_signal` | (bool, str) | esito finale |

### Architettura

- **`ProcessingService` è un `QObject`**: `main_window.py:291-303` lo sposta su un `QThread` (`moveToThread`) e collega `start_processing_signal` (emesso dalla UI) al suo `start_processing()` — tutta la pipeline gira fuori dal thread della GUI.
- **Stato**: due `threading.Event` — `_stop_event` (annullamento richiesto) e `_working_event` (elaborazione in corso, guardia anti doppio avvio, `_check_cancelled`).
- **Binari**: `_find_bin_path()` (processing_service.py:41) individua `bin/` (root del repo in dev, `resource_path("bin")` nel bundle) e costruisce `WhisperCppManager` con la `models_dir` di ConfigManager.

### Pipeline `start_processing(params)` (processing_service.py:56)

1. **Pre-condizioni**: se `subs_mode != none` e input YouTube con `yt_mode=audio` → forza `yt_mode=video` (serve il video per i sottotitoli).
2. **Input** (`_handle_input`, processing_service.py:177): YouTube → `YoutubeManager.run()` (il path scaricato finisce in `_generated_files` per il cleanup); file locale → verifica esistenza; per i video salva `_video_source`.
3. **Modello**: `whisper_manager.download_model()` — no-op se già in cache, altrimenti download con progresso e annullamento.
4. **Conversione**: `convert_to_wav_16khz()` → WAV PCM 16kHz mono nella stessa cartella del file (`<file>_16khz.wav`, tracciato per il cleanup).
5. **Trascrizione**: `run_whisper()` con `total_duration` ricavato con `get_audio_duration()` (ffprobe).
6. **Fallback GPU→CPU** (processing_service.py:144): se il primo tentativo fallisce e `device_mode == "gpu"`, logga `[!] Fallimento GPU rilevato` e rilancia in CPU (`-ng`).
7. **Sottotitoli** (`_apply_subtitles`, processing_service.py:201): se richiesti, legge `<nome>.srt` e chiama `embed_subtitles()` (soft: `_subs` + estensione sorgente) o `burn_subtitles()` (hard: `_burned.mp4`), con progresso e registry dei processi ffmpeg (`_ffmpeg_processes`).
8. **Cleanup** (`_cleanup_and_finish`, processing_service.py:250):
   - annullamento → rimuove tutti i `_generated_files` + output parziali (srt/vtt/txt/tsv/json del prefisso);
   - successo → rimuove solo il WAV temporaneo.

### Stop (`stop()`, processing_service.py:282)

Imposta `_stop_event`, poi interrompe in cascata: yt-dlp (`yt_manager.stop()`), whisper-cli (`whisper_manager.stop_process()`), ogni ffmpeg registrato (terminate → wait 3s → kill). Il cleanup cooperativo avviene al rientro nella pipeline (ogni fase controlla `_stop_event`).

### Note

- Ogni fase emette `stage_changed_signal` e azzera il progresso: la UI mostra la fase nel formato della progress bar (`"<fase> - %p%"`, vedi [ui.md](ui.md)).
- `params` non contiene `device_mode`: viene letto direttamente dalla config al momento della trascrizione (modificabile dalle impostazioni).
