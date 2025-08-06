# --- whisper_gui/utils/config_manager.py ---
import os
import json

class ConfigManager:
    def __init__(self, app_name="WhisperGUI", config_file_name="config.json"):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", app_name)
        self.config_path = os.path.join(self.config_dir, config_file_name)
        self.config = self._load_config()

    def _get_default_config(self):
        return {
            "execution_mode": "docker",
            "model": "medium",
            "language": "ja",
            "task": "translate",
            "output_format": "srt",
            "input_dir": "input",
            "output_text_dir": "output_text",
            "docker_container_name": "rocm-terminal",
            "docker_folder": "/home/rocm-user/whisper",
            "use_insanely_fast_whisper": False, # Aggiunto per gestire la versione "fast"
            "batch_size": 4 # Per insanely-fast-whisper
        }

    def _load_config(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                try:
                    loaded_config = json.load(f)
                    default_config = self._get_default_config()
                    default_config.update(loaded_config)
                    return default_config
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {self.config_path}. Using default configuration.")
                    return self._get_default_config()
        else:
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

    def _save_config(self, config_data):
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self._save_config(self.config)