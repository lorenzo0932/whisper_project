# Architettura di WhisperGUI

> Documentazione dei componenti (in italiano). Indice: [core](core.md) · [services](services.md) · [ui](ui.md) · [utils](utils.md) · [build pipeline](build-pipeline.md) · [CI](ci.md)

## Panoramica

WhisperGUI è un'applicazione desktop **standalone e cross-platform** (Linux, macOS arm64, Windows) per la trascrizione e traduzione locale di audio/video con OpenAI Whisper via **whisper.cpp**.

L'app è un **bundle self-contained** (PyInstaller onedir): al suo interno viaggiano l'interprete Python, la GUI PyQt6, il binario `whisper-cli` (engine nativo compilato con backend GPU per-OS) e `ffmpeg`/`ffprobe` statici. L'utente finale non installa nulla: niente Python, niente FFmpeg, niente driver Vulkan espliciti (usa quelli di sistema).

```
┌────────────────────────────────────────────────────────────┐
│  UI (PyQt6) — ui/main_window.py                            │
│  emette param dict su start_processing_signal (QThread)     │
└──────────────────────────┬─────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────┐
│  services/processing_service.py  (orchestratore, in QThread)│
│  segnali Qt: started / stage_changed / log / progress /     │
│              finished                                       │
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
                                            (opz.) ffmpeg ──► video con sottotitoli soft/burn
```

## Flusso dati end-to-end

1. **Input**: un file audio/video locale oppure un link YouTube.
   - YouTube → `core/youtube_manager.py` (yt-dlp), modalità `audio` (solo traccia audio) o `video` (merge MP4).
   - File locale → usato direttamente.
2. **Modello**: `core/model_manager.py` verifica la presenza del modello nella cache utente; se manca lo scarica da HuggingFace (`ggml-<id>.bin` dal repo `ggerganov/whisper.cpp`) con callback di progresso e annullamento. I modelli vivono **fuori dal bundle** in `user_cache_dir("WhisperGUI")/models` (vedi [utils.md](utils.md)).
3. **Conversione audio**: `utils/audio_utils.convert_to_wav_16khz()` — ffmpeg → WAV PCM 16kHz mono (formato richiesto da whisper.cpp).
4. **Trascrizione**: `core/whispercpp_manager.run_whisper()` lancia `whisper-cli` in subprocess con:
   - env per-OS per trovare le librerie (`LD_LIBRARY_PATH` Linux, `DYLD_LIBRARY_PATH` macOS, `PATH` Windows) puntando al `bin_dir` del bundle;
   - progresso derivato dal parsing dei timestamp SRT nello stdout (`_TIMESTAMP_RE`, `whispercpp_manager.py:12`);
   - modalità GPU (default) o CPU (`-ng`), con thread allocati proporzionalmente a `os.cpu_count()`.
5. **Output**: file `srt|vtt|txt|tsv|json` nella cartella di output scelta.
6. **(Opzionale) Sottotitoli nel video**: se `subs_mode != none` e c'è una sorgente video, `utils/audio_utils.embed_subtitles()` (traccia soft `*_subs.mp4`) o `burn_subtitles()` (incisi `*_burned.mp4`), con progresso via `-progress` di ffmpeg.
7. **Cleanup**: i file temporanei (`*_16khz.wav`, download YouTube se input YouTube) vengono rimossi; in caso di annullamento viene ripulito anche l'output parziale.

## Decisioni chiave

- **Backend nativo, niente Docker**: l'evoluzione del progetto ha sostituito la modalità Docker (e `insanely-fast-whisper`) con la trascrizione nativa whisper.cpp: zero dipendenze runtime per l'utente, niente container da gestire.
- **Tutti i path a risorse/binarie passano da `utils/resource_path.py`**: in sviluppo punta alla root del repo, nel bundle PyInstaller onedir punta a `_internal` (vedi [utils.md](utils.md)).
- **Fallback GPU → CPU automatico**: se `whisper-cli` fallisce in modalità GPU, `processing_service` ripete la trascrizione con `-ng` (`processing_service.py:144`).
- **UI reattiva**: `ProcessingService` è un `QObject` spostato su un `QThread` (`main_window.py:291-303`); i segnali Qt sono l'unico canale di comunicazione (funzionano anche headless con `QCoreApplication`, usato da `main.py --cli`).
- **Annullamento cooperativo**: un `threading.Event` di stop viene controllato in ogni fase (download modello, conversione, trascrizione, sottotitoli); i processi (whisper-cli, yt-dlp, ffmpeg) vengono terminati e i file parziali eliminati.
- **Modelli per categorie**: `core/model_manager.py` organizza i modelli in tier (potato → highend) con quantizzazioni adatte all'hardware; il default di config è `large-v3-turbo-q5_0` (~1.6-2 GB) — il primo download può essere corposo.

## Dipendenze tra moduli

```
main.py
 ├─ ui/main_window.py ── services/processing_service.py
 │      └─ ui/settings_dialog.py     ├─ core/whispercpp_manager.py ── core/model_manager.py
 │      └─ utils/config_manager.py   ├─ core/youtube_manager.py
 │      └─ core/model_manager.py     └─ utils/audio_utils.py
 │                                   └─ utils/resource_path.py
 └─ utils/config_manager.py
```
