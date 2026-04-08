import subprocess
import os
import re
import threading
import sys
import urllib.request

class WhisperCppManager:
    def __init__(self, bin_path="bin/whisper-cli", models_dir="models"):
        self.bin_path = os.path.abspath(bin_path)
        self.models_dir = os.path.abspath(models_dir)
        self.current_process = None
        self.process_lock = threading.Lock()
        
        # Crea la cartella dei modelli se non esiste
        os.makedirs(self.models_dir, exist_ok=True)

    def download_model(self, model_name, progress_callback=None, log_callback=None, is_cancelled_cb=None):
        """
        Scarica il modello GGML da HuggingFace se non presente.
        Supporta l'interruzione immediata tramite is_cancelled_cb.
        """
        model_file = f"ggml-{model_name}.bin"
        model_path = os.path.join(self.models_dir, model_file)

        if os.path.exists(model_path):
            if log_callback:
                log_callback(f"Modello '{model_name}' già presente in cache.")
            return True

        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_file}"

        if log_callback:
            log_callback(f"Download del modello '{model_name}' iniziato...")

        try:
            def reporthook(block_num, block_size, total_size):
                # Controllo interruzione utente
                if is_cancelled_cb and is_cancelled_cb():
                    raise InterruptedError("Download annullato dall'utente.")
                
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(100, int((downloaded / total_size) * 100))
                    progress_callback(percent)

            urllib.request.urlretrieve(url, model_path, reporthook)
            
            if log_callback:
                log_callback(f"Download completato: {model_file}")
            return True
            
        except InterruptedError as e:
            if log_callback: log_callback(str(e))
            if os.path.exists(model_path): os.remove(model_path)
            return False
        except Exception as e:
            if log_callback: log_callback(f"Errore durante il download: {e}")
            if os.path.exists(model_path): os.remove(model_path)
            return False

    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Converte stringa [HH:MM:SS.mmm] in secondi float."""
        parts = timestamp_str.replace(',', '.').split(':')
        try:
            if len(parts) == 3:  # HH:MM:SS
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:  # MM:SS
                return float(parts[0]) * 60 + float(parts[1])
        except: pass
        return 0.0

    def run_whisper(self, model, language, task, output_format, output_dir, file_path, output_name=None, total_duration=None, log_callback=None, progress_callback=None, device_mode="gpu"):
        """
        Esegue il binario whisper-cli con i parametri scelti.
        """
        os.makedirs(output_dir, exist_ok=True)

        model_file = os.path.join(self.models_dir, f"ggml-{model}.bin")
        if not os.path.exists(model_file):
            return False, f"Modello non trovato: {model_file}"

        # Determina il prefisso del file di output (senza estensione)
        if output_name:
            out_file_prefix = os.path.join(output_dir, output_name)
        else:
            base = os.path.splitext(os.path.basename(file_path))[0]
            out_file_prefix = os.path.join(output_dir, base)

        # --- GESTIONE THREAD E DEVICE ---
        cpu_cores = os.cpu_count() or 4
        if device_mode == "cpu":
            # Target 85% per lasciare risorse al sistema
            threads = max(1, int(cpu_cores * 0.85))
            gpu_args = ["-ng"] # Flag "No GPU"
            mode_label = "CPU"
        else:
            # In GPU usiamo comunque 50% dei thread per supporto
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

        # Formati output
        if output_format == "srt": command.append("-osrt")
        elif output_format == "vtt": command.append("-ovtt")
        elif output_format == "txt": command.append("-otxt")
        else: command.append("-osrt")

        try:
            with self.process_lock:
                # Setup ambiente per librerie condivise (Vulkan .so)
                env = os.environ.copy()
                bin_dir = os.path.dirname(self.bin_path)
                env["LD_LIBRARY_PATH"] = f"{bin_dir}:{env.get('LD_LIBRARY_PATH', '')}"

                self.current_process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, bufsize=1, encoding='utf-8', env=env
                )
                process = self.current_process
            
            # Regex per estrarre il progresso dai timestamp [00:00:10.000 --> 00:00:15.000]
            timestamp_regex = re.compile(r'\[(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\s-->\s(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\]')

            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line: continue
                if log_callback: log_callback(line)
                
                # Calcolo percentuale basato sulla durata totale
                if progress_callback and total_duration and total_duration > 0:
                    match = timestamp_regex.search(line)
                    if match:
                        end_hour, end_min_sec = match.group(3), match.group(4)
                        full_ts = f"{end_hour}:{end_min_sec}" if end_hour else end_min_sec
                        current_sec = self._parse_timestamp(full_ts)
                        percentage = int((current_sec / total_duration) * 100)
                        progress_callback(min(percentage, 100))

            process.wait()

            if process.returncode == 0:
                if progress_callback: progress_callback(100)
                return True, "Trascrizione completata con successo."
            elif process.returncode in [-15, 9, 130]: 
                return False, "Processo interrotto dall'utente."
            else:
                return False, f"Errore durante l'esecuzione (Codice: {process.returncode})."

        except Exception as e:
            return False, f"Errore inatteso nel manager: {e}"
        finally:
            with self.process_lock:
                self.current_process = None

    def stop_process(self):
        """Interrompe il processo whisper-cli se attivo."""
        with self.process_lock:
            if self.current_process and self.current_process.poll() is None:
                self.current_process.terminate()
                try:
                    self.current_process.wait(3)
                except:
                    self.current_process.kill()
                return True
            return False