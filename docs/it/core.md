# Componente `core/` — Logica di dominio

Tre moduli: esecuzione di whisper.cpp, download YouTube e gestione dei modelli.

## `core/whispercpp_manager.py` — Esecuzione di whisper.cpp

Gestisce il ciclo di vita del processo `whisper-cli` (l'engine nativo di trascrizione).

### Responsabilità

- **Localizzazione del binario**: in sviluppo `bin/whisper-cli` alla root del repo; nel bundle PyInstaller la cartella `bin` aggiunta con `--add-data` (via `resource_path`, vedi `utils/resource_path.py`). Su Windows il nome diventa `whisper-cli.exe` (`binary_name`).
- **Risoluzione del file modello**: `_find_model_file()` (whispercpp_manager.py:35) cerca `ggml-<model>.gguf` o `.bin` nella `models_dir` (la cache utente).
- **Build del comando**: `run_whisper()` (whispercpp_manager.py:53) costruisce gli argomenti CLI:
  - `-m <modello> -f <file> -of <prefisso_output> -t <thread>` + flag per lingua (`-l`, se diversa da `auto`), task `-tr` (translate), formato output (`-osrt/-ovtt/-otxt/-otsv/-ojson`);
  - GPU (default) o CPU: in modalità CPU aggiunge `-ng` e usa più thread (85% dei core vs 50% in GPU).
- **Env per-OS**: prima del lancio imposta la variabile di librerie sul `bin_dir` del bundle — `LD_LIBRARY_PATH` (Linux), `DYLD_LIBRARY_PATH` (macOS), `PATH` (Windows) — così il loader trova le librerie Vulkan/Metal accanto al binario (whispercpp_manager.py:108-122).
- **Progresso**: il progresso % è derivato dal parsing dei timestamp SRT stampati da whisper-cli su stdout (`_TIMESTAMP_RE`, whispercpp_manager.py:12) rapportati alla durata totale del file (`total_duration`).
- **Stop**: `stop_process()` (whispercpp_manager.py:164) termina il processo in modo cooperativo con `process_lock` (terminate → kill dopo 3s).

### Note

- `current_process` e il lock proteggono l'unico processo attivo per istanza.
- I return sono sempre coppie `(bool, messaggio)` usate dal service per gli esiti.
- `stop_process` gestisce i codici di uscita di interruzione (-15/9/130) come "interrotto dall'utente".

## `core/youtube_manager.py` — Download YouTube

Wrapper su **yt-dlp** (bundlato nel venv e nel bundle PyInstaller).

### Responsabilità

- `download_video()` (youtube_manager.py:29): scarica con formato selezionato:
  - modalità `audio` → formato audio scelto da yt-dlp (`format` implicito);
  - modalità `video` → `merge_output_format = 'mp4'` (video+audio uniti in MP4).
- **Progresso**: `_progress_hook` (youtube_manager.py:19) estrae `_percent_str` dallo stato `downloading` (pulito dagli escape ANSI) e lo inoltra al callback.
- **Risultato**: ritorna il path del file scaricato, con fallback per estensione reale (`.mp4`/`.mkv`/`.webm`) perché `filepath` di yt-dlp può indicare un file inesistente prima del merge.
- **Stop**: `stop()` interrompe `yt_dlp` attivo (`self._ydl`).
- `noplaylist: True`: un link di playlist scarica solo il singolo video.

## `core/model_manager.py` — Catalogo e download dei modelli

### Responsabilità

- **Catalogo**: `CATEGORIES` (model_manager.py:9) definisce 4 tier per hardware: `potato` (tiny/base q5_1), `laptop` (small/medium q5), `desktop` (medium q8_0, large-v2, large-v3-turbo), `highend` (large-v2/v3 fino a f16, 6 GB). Ogni modello: `id` (→ `ggml-<id>.bin`), label con dimensione, quantizzazione. `DEFAULT_CATEGORY = "desktop"`.
- **Risoluzione**: `get_category()`/`resolve_model_id(category, index)` usati dalla UI per mappare radio-button → id modello.
- **URL**: `MODEL_REPO = https://huggingface.co/ggerganov/whisper.cpp/resolve/main` — i modelli quantizzati ufficiali di whisper.cpp.
- **Download**: `ModelManager.download_model()` (model_manager.py:90):
  - se il file esiste già → OK senza rete ("Modello già presente in cache");
  - altrimenti `urllib.request.urlretrieve` con `reporthook` per il progresso, supporto cancellazione via `is_cancelled_cb` e pulizia del file parziale su annullamento/errore.
- **Path**: i modelli sono salvati in `models_dir` fornita da ConfigManager (cache utente, vedi [utils.md](utils.md)) — mai dentro il bundle.

### Note

- Il default di config `model = large-v3-turbo-q5_0` implica un primo download di ~2 GB; le categorie potato/laptop scaricano centinaia di MB.
- `download_model()` viene chiamato dal service a ogni elaborazione: se il modello c'è già, è un no-op immediato.
