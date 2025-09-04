import subprocess
import os
import sys
import re
import threading

class NativeWhisper:
    def __init__(self):
        self.current_process = None
        self.process_lock = threading.Lock()

    def _check_command(self, command):
        # Questa funzione può essere migliorata per funzionare meglio su Windows
        # ma per Linux/macOS 'which' è adeguato.
        return subprocess.run(['which', command], capture_output=True, text=True).returncode == 0

    def check_dependencies(self):
        # Questo metodo è un placeholder, l'implementazione completa può essere complessa.
        # Per ora, assumiamo che le dipendenze siano soddisfatte.
        if not self._check_command(sys.executable):
            return False, "Interprete Python non trovato."
        # Potremmo aggiungere un controllo per 'pip show openai-whisper'
        return True, "Dipendenze verificate (simulazione)."

    def _parse_timestamp(self, timestamp_str: str) -> float:
        """
        Converte un timestamp flessibile (con o senza ore) in secondi.
        Esempi di input: '01:23:45.678' o '23:45.678'
        """
        parts = timestamp_str.replace(',', '.').split(':')
        seconds = 0.0
        try:
            # Elabora le parti in ordine inverso per gestire entrambi i formati
            if len(parts) == 3:  # HH:MM:SS.mmm
                seconds += float(parts[0]) * 3600
                seconds += float(parts[1]) * 60
                seconds += float(parts[2])
            elif len(parts) == 2:  # MM:SS.mmm
                seconds += float(parts[0]) * 60
                seconds += float(parts[1])
            else:
                return 0.0 # Formato non riconosciuto
        except (ValueError, IndexError):
            return 0.0 # Ritorna 0 in caso di errore di parsing
        return seconds

    def run_whisper(self, model, language, task, output_format, output_dir, file_path, total_duration=None, log_callback=None, progress_callback=None):
        os.makedirs(output_dir, exist_ok=True)

        command = [
            sys.executable,
            "-u",
            "-m", "whisper",
            file_path,
            "--model", model,
            "--task", task,
            "--output_format", output_format,
            "--output_dir", output_dir,
            "--verbose", "True" # Assicura che l'output dei timestamp sia sempre presente
        ]
        if language and language.lower() != "auto":
            command.extend(["--language", language])

        if log_callback:
            log_callback(f"Esecuzione comando Whisper: {' '.join(command)}")

        try:
            with self.process_lock:
                self.current_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8')
                process = self.current_process
            
            # --- REGEX CORRETTO E FLESSIBILE ---
            # Rende il gruppo delle ore (HH:) opzionale
            timestamp_regex = re.compile(r'\[(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\s-->\s(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\]')

            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line: continue

                if log_callback:
                    log_callback(line)
                
                # --- LOGICA DI PROGRESSIONE CORRETTA E ROBUSTA ---
                if progress_callback and total_duration and total_duration > 0:
                    match = timestamp_regex.search(line)
                    if match:
                        # Estrae il timestamp di fine, che può avere o meno le ore
                        end_hour = match.group(3)
                        end_min_sec = match.group(4)
                        
                        full_timestamp_str = f"{end_hour}:{end_min_sec}" if end_hour else end_min_sec
                        
                        current_seconds = self._parse_timestamp(full_timestamp_str)
                        percentage = int((current_seconds / total_duration) * 100)
                        progress_callback(min(percentage, 100))

            process.wait()

            if process.returncode == 0:
                if progress_callback: progress_callback(100) # Assicura il completamento al 100%
                return True, "Comando Whisper eseguito con successo."
            elif process.returncode == -15: # SIGTERM, process was terminated
                if progress_callback: progress_callback(0) # Reset progress bar
                return True, "Processo Whisper interrotto dall'utente."
            else:
                return False, f"Errore durante l'esecuzione di Whisper (Codice: {process.returncode}). Controlla il log per i dettagli."
        except FileNotFoundError:
            return False, f"Comando non trovato: '{sys.executable}'. Assicurati che Python e Whisper siano installati correttamente."
        except Exception as e:
            return False, f"Errore inatteso durante l'esecuzione di Whisper: {e}"
        finally:
            with self.process_lock:
                self.current_process = None

    def stop_process(self):
        with self.process_lock:
            process_to_stop = self.current_process
            if process_to_stop and process_to_stop.poll() is None:
                process_to_stop.terminate()
                process_to_stop.wait(5) # Wait for a few seconds for the process to terminate
                if process_to_stop.poll() is None: # If it's still running, kill it
                    process_to_stop.kill()
                # Only set self.current_process to None if it's the same process we just stopped
                if self.current_process == process_to_stop:
                    self.current_process = None
                return True
            return False
