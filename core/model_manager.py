import os
import logging
import ssl
import urllib.request

import certifi

logger = logging.getLogger(__name__)

MODEL_REPO = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

CATEGORIES = [
    {
        "id": "potato",
        "emoji": "🥔",
        "label": "Potato",
        "description": "PC vecchi, Raspberry Pi, risorse minime",
        "models": [
            {"id": "tiny-q5_1",     "label": "Tiny (q5_1, 75 MB)",  "quant": "q5_1"},
            {"id": "base-q5_1",     "label": "Base (q5_1, 150 MB)", "quant": "q5_1"},
        ]
    },
    {
        "id": "laptop",
        "emoji": "💻",
        "label": "Laptop",
        "description": "Bilanciato qualità/velocità per portatili",
        "models": [
            {"id": "small-q5_1",    "label": "Small (q5_1, 460 MB)", "quant": "q5_1"},
            {"id": "medium-q5_0",   "label": "Medium (q5_0, 1.5 GB)", "quant": "q5_0"},
        ]
    },
    {
        "id": "desktop",
        "emoji": "🖥️",
        "label": "Desktop",
        "description": "Raccomandato per desktop moderni",
        "models": [
            {"id": "medium-q8_0",         "label": "Medium (q8_0, 2.5 GB)", "quant": "q8_0"},
            {"id": "large-v2-q5_0",       "label": "L-v2 (q5_0, 2.5 GB)", "quant": "q5_0"},
            {"id": "large-v3-turbo-q5_0", "label": "L-v3 Turbo (q5_0, 2 GB)", "quant": "q5_0"},
        ]
    },
    {
        "id": "highend",
        "emoji": "🚀",
        "label": "High-End",
        "description": "Massima accuratezza, tanta RAM/VRAM",
        "models": [
            {"id": "large-v2-q5_0", "label": "L-v2 (q5_0, 2.5 GB)", "quant": "q5_0"},
            {"id": "large-v2",      "label": "L-v2 (f16, 5.5 GB)", "quant": "f16"},
            {"id": "large-v3-q5_0", "label": "L-v3 (q5_0, 3.5 GB)", "quant": "q5_0"},
            {"id": "large-v3",      "label": "L-v3 (f16, 6 GB)", "quant": "f16"},
        ]
    },
]

DEFAULT_CATEGORY = "desktop"

def get_categories():
    return CATEGORIES

def get_category(category_id):
    for cat in CATEGORIES:
        if cat["id"] == category_id:
            return cat
    return get_category(DEFAULT_CATEGORY)

def get_model_filename(model_id):
    return f"ggml-{model_id}.bin"

def get_download_url(model_id):
    filename = get_model_filename(model_id)
    return f"{MODEL_REPO}/{filename}"

def resolve_model_id(category_id, model_index=0):
    cat = get_category(category_id)
    models = cat["models"]
    idx = min(model_index, len(models) - 1)
    return models[idx]["id"]

class ModelManager:
    def __init__(self, models_dir):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)

    def get_model_path(self, model_id):
        return os.path.join(self.models_dir, get_model_filename(model_id))

    def is_downloaded(self, model_id):
        return os.path.exists(self.get_model_path(model_id))

    def download_model(self, model_id, progress_callback=None, log_callback=None, is_cancelled_cb=None):
        model_path = self.get_model_path(model_id)

        if os.path.exists(model_path):
            if log_callback:
                log_callback(f"Modello già presente in cache.")
            return True

        url = get_download_url(model_id)

        if log_callback:
            log_callback(f"Download del modello in corso...")

        try:
            def reporthook(block_num, block_size, total_size):
                if is_cancelled_cb and is_cancelled_cb():
                    raise InterruptedError("Download annullato dall'utente.")
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(100, int((downloaded / total_size) * 100))
                    progress_callback(percent)

            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=context) as resp:
                total_size = int(resp.headers.get("Content-Length") or 0)
                block_size = 64 * 1024
                block_num = 0
                with open(model_path, "wb") as out:
                    while True:
                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        reporthook(block_num, block_size, total_size)
                        block_num += 1

            if log_callback:
                log_callback(f"Download completato.")
            return True

        except InterruptedError as e:
            if log_callback:
                log_callback(str(e))
            if os.path.exists(model_path):
                os.remove(model_path)
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"Errore durante il download: {e}")
            if os.path.exists(model_path):
                os.remove(model_path)
            return False
