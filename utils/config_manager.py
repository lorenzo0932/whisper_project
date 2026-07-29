import os
import json
import logging
from pathlib import Path
from platformdirs import user_config_dir, user_cache_dir

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, app_name="WhisperGUI"):
        self.config_dir = user_config_dir(app_name, ensure_exists=True)
        self.cache_dir = user_cache_dir(app_name, ensure_exists=True)
        self.models_dir = os.path.join(self.cache_dir, "models")

        os.makedirs(self.models_dir, exist_ok=True)

        self.config_path = os.path.join(self.config_dir, "config.json")
        self.config = self._load_config()

    def _get_default_config(self):
        return {
            "device_mode": "gpu",
            "language": "auto",
            "task": "transcribe",
            "output_format": "srt",
            "input_dir": str(Path.home() / "Downloads"),
            "output_dir": str(Path.home() / "Documents" / "WhisperGUI"),
            "model_category": "desktop",
            "model_index": 0,
            "model": "large-v3-turbo-q5_0"
        }

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    defaults = self._get_default_config()
                    defaults.update(data)
                    return defaults
            except Exception as e:
                logger.warning("Failed to load config, using defaults: %s", e)
        return self._get_default_config()

    def set(self, key, value):
        self.config[key] = value
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error("Failed to save config: %s", e)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_default(self, key, default=None):
        return self._get_default_config().get(key, default)
