import os
import json
from pathlib import Path

class ConfigManager:
    def __init__(self, app_name="WhisperGUI"):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", app_name)
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", app_name)
        self.models_dir = os.path.join(self.cache_dir, "models")
        
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.config = self._load_config()

    def _get_default_config(self):
        return {
            "device_mode": "gpu",
            "model": "medium",
            "language": "auto",
            "task": "transcribe",
            "output_format": "srt",
            "input_dir": str(Path.home() / "Downloads"),
            "output_dir": str(Path.home() / "Documents" / "WhisperGUI")
        }

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    defaults = self._get_default_config()
                    defaults.update(data)
                    return defaults
            except: pass
        return self._get_default_config()

    def set(self, key, value):
        self.config[key] = value
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def get_default(self, key, default=None):
        return self._get_default_config().get(key, default)