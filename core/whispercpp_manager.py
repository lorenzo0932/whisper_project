import subprocess
import os
import re
import sys
import threading
import logging
from core.model_manager import ModelManager
from utils.resource_path import binary_name

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(
    r'\[(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\s-->\s(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\]'
)

class WhisperCppManager:
    def __init__(self, bin_path=None, models_dir="models"):
        if bin_path is None:
            bin_path = os.path.join("bin", binary_name("whisper-cli"))
        self.bin_path = os.path.abspath(bin_path)
        self.models_dir = os.path.abspath(models_dir)
        self.current_process = None
        self.process_lock = threading.Lock()
        self.model_manager = ModelManager(models_dir)
        os.makedirs(self.models_dir, exist_ok=True)

    def download_model(self, model_name, progress_callback=None, log_callback=None, is_cancelled_cb=None):
        return self.model_manager.download_model(
            model_name,
            progress_callback=progress_callback,
            log_callback=log_callback,
            is_cancelled_cb=is_cancelled_cb
        )

    def _find_model_file(self, model):
        for ext in [".gguf", ".bin"]:
            path = os.path.join(self.models_dir, f"ggml-{model}{ext}")
            if os.path.exists(path):
                return path
        return None

    def _parse_timestamp(self, timestamp_str: str) -> float:
        parts = timestamp_str.replace(',', '.').split(':')
        try:
            if len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
        except Exception:
            logger.debug("Failed to parse timestamp: %s", timestamp_str)
        return 0.0

    def run_whisper(self, model, language, task, output_format, output_dir, file_path, output_name=None, total_duration=None, log_callback=None, progress_callback=None, device_mode="gpu"):
        os.makedirs(output_dir, exist_ok=True)

        model_file = self._find_model_file(model)
        if not model_file:
            return False, f"Modello non trovato: ggml-{model} (.gguf o .bin)"

        if output_name:
            out_file_prefix = os.path.join(output_dir, output_name)
        else:
            base = os.path.splitext(os.path.basename(file_path))[0]
            out_file_prefix = os.path.join(output_dir, base)

        cpu_cores = os.cpu_count() or 4
        if device_mode == "cpu":
            threads = max(1, int(cpu_cores * 0.85))
            gpu_args = ["-ng"]
            mode_label = "CPU"
        else:
            threads = max(1, int(cpu_cores * 0.5))
            gpu_args = []
            mode_label = "GPU/Vulkan"

        if log_callback:
            log_callback(f"Modalità: {mode_label} | Thread allocati: {threads}")

        command = [
            self.bin_path,
            "-m", model_file,
            "-f", file_path,
            "-of", out_file_prefix,
            "-t", str(threads)
        ] + gpu_args

        if language and language.lower() != "auto":
            command.extend(["-l", language])

        if task == "translate":
            command.append("-tr")

        if output_format == "srt":
            command.append("-osrt")
        elif output_format == "vtt":
            command.append("-ovtt")
        elif output_format == "txt":
            command.append("-otxt")
        elif output_format == "tsv":
            command.append("-otsv")
        elif output_format == "json":
            command.append("-ojson")
        else:
            command.append("-osrt")

        try:
            with self.process_lock:
                env = os.environ.copy()
                bin_dir = os.path.dirname(self.bin_path)
                if sys.platform == "win32":
                    lib_env = "PATH"
                    existing = env.get("PATH", "")
                    sep = os.pathsep
                elif sys.platform == "darwin":
                    lib_env = "DYLD_LIBRARY_PATH"
                    existing = env.get("DYLD_LIBRARY_PATH", "")
                    sep = ":"
                else:
                    lib_env = "LD_LIBRARY_PATH"
                    existing = env.get("LD_LIBRARY_PATH", "")
                    sep = ":"
                env[lib_env] = f"{bin_dir}{sep}{existing}" if existing else bin_dir

                self.current_process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding='utf-8', env=env
                )
                process = self.current_process

            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                if log_callback:
                    log_callback(line)

                if progress_callback and total_duration and total_duration > 0:
                    match = _TIMESTAMP_RE.search(line)
                    if match:
                        end_hour, end_min_sec = match.group(3), match.group(4)
                        full_ts = f"{end_hour}:{end_min_sec}" if end_hour else end_min_sec
                        current_sec = self._parse_timestamp(full_ts)
                        percentage = int((current_sec / total_duration) * 100)
                        progress_callback(min(percentage, 100))

            process.wait()

            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100)
                return True, "Trascrizione completata con successo."
            elif process.returncode in [-15, 9, 130]:
                return False, "Processo interrotto dall'utente."
            else:
                return False, f"Errore durante l'esecuzione (Codice: {process.returncode})."

        except Exception as e:
            logger.error("Errore inatteso nel manager: %s", e)
            return False, f"Errore inatteso nel manager: {e}"
        finally:
            with self.process_lock:
                self.current_process = None

    def stop_process(self):
        with self.process_lock:
            if self.current_process and self.current_process.poll() is None:
                self.current_process.terminate()
                try:
                    self.current_process.wait(3)
                except Exception:
                    logger.debug("Force killing whisper process")
                    self.current_process.kill()
                return True
            return False
