# --- whisper_gui/core/docker_manager.py ---
import docker
import tarfile
import os
import glob
import re
import threading # Import threading for process lock

class DockerManager:
    def __init__(self, container_name):
        self.current_process_exec_id = None # To store the exec_id for the running command
        self.process_lock = threading.Lock() # For thread-safe process management
        self.container_name = container_name
        try:
            self.client = docker.from_env()
            self.container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            self.container = None
            # Don't raise an error here, allow the check_container_status to handle it
        except docker.errors.DockerException:
            self.container = None
            # Don't raise an error here, allow the check_container_status to handle it

    def check_container_status(self):
        try:
            self.container = self.client.containers.get(self.container_name)
            if self.container.status == 'running':
                return True, f"Container '{self.container_name}' è in esecuzione."
            else:
                return False, f"Container '{self.container_name}' non è in esecuzione (stato: {self.container.status})."
        except docker.errors.NotFound:
            return False, f"Container Docker '{self.container_name}' non trovato."
        except docker.errors.DockerException:
            return False, "Errore di connessione al demone Docker. Assicurati che Docker sia installato e in esecuzione."

    def _find_file_by_name(self, src_path, file_name):
        search_pattern = os.path.join(src_path, f"{file_name}.*")
        files = glob.glob(search_pattern)
        if files:
            return files[0]
        else:
            raise FileNotFoundError(f"Nessun file trovato con nome '{file_name}' in '{src_path}'.")

    def copy_to_container(self, src_path, file_name, container_dest_path):
        local_file_path = self._find_file_by_name(src_path, file_name)
        
        # Usa un nome temporaneo univoco per evitare conflitti
        temp_tar_name = f'temp_{os.getpid()}.tar'
        with tarfile.open(temp_tar_name, mode='w') as tar:
            tar.add(local_file_path, arcname=os.path.basename(local_file_path))
        
        with open(temp_tar_name, 'rb') as tar_file:
            self.container.put_archive(container_dest_path, tar_file.read())
        
        os.remove(temp_tar_name)
        print(f"File '{local_file_path}' copiato nel container a '{container_dest_path}'.")

    def copy_from_container(self, container_src_path, local_dest_path, log_callback=None):
        """
        Copia file o directory dal container al percorso locale.
        container_src_path: percorso del file/directory all'interno del container.
        local_dest_path: percorso della directory locale dove salvare i file.
        """
        try:
            # Crea un archivio tar dei contenuti nel container
            strm, stat = self.container.get_archive(container_src_path)
            
            # Salva l'archivio tar temporaneamente
            temp_tar_path = f'temp_from_container_{os.getpid()}.tar'
            with open(temp_tar_path, 'wb') as f:
                for chunk in strm:
                    f.write(chunk)
            
            # Estrai l'archivio tar nella destinazione locale
            with tarfile.open(temp_tar_path, 'r') as tar:
                # Docker get_archive include la directory radice nel tar.
                # Dobbiamo estrarre i contenuti direttamente nella destinazione.
                for member in tar.getmembers():
                    if member.isfile():
                        # Costruisci il percorso di destinazione, ignorando la directory radice del tar
                        # Esempio: se container_src_path è /app/output e tar contiene /output/file.txt
                        # vogliamo estrarre direttamente in local_dest_path/file.txt
                        arcname_parts = member.name.split(os.sep)
                        # Se il primo elemento è vuoto (es. /output/file.txt -> ['', 'output', 'file.txt'])
                        # o se è il nome della directory sorgente nel container
                        if not arcname_parts[0] or arcname_parts[0] == os.path.basename(container_src_path):
                            # Rimuovi la parte della directory radice del tar
                            relative_path = os.path.join(*arcname_parts[1:])
                        else:
                            relative_path = member.name # Se non corrisponde, usa il nome completo

                        dest_file_path = os.path.join(local_dest_path, relative_path)
                        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                        
                        # Estrai il file
                        source = tar.extractfile(member)
                        if source:
                            with open(dest_file_path, 'wb') as dest_f:
                                dest_f.write(source.read())
                            if log_callback:
                                log_callback(f"File '{member.name}' copiato dal container a '{dest_file_path}'.")
            
            os.remove(temp_tar_path)
            return True, "File copiati con successo dal container."
        except docker.errors.NotFound:
            return False, f"Percorso '{container_src_path}' non trovato nel container."
        except Exception as e:
            return False, f"Errore durante la copia dal container: {e}"

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

    def run_whisper(self, model, language, task, output_format, output_dir, file_path, total_duration=None, use_fast_whisper=False, batch_size=4, log_callback=None, progress_callback=None):
        # Ensure output_dir exists locally before passing to container (for mounting)
        os.makedirs(output_dir, exist_ok=True)

        # Docker container paths based on user feedback
        container_whisper_home = "/home/rocm-user/whisper"
        container_input_dir = os.path.join(container_whisper_home, "input")
        container_output_dir = os.path.join(container_whisper_home, "output_text")
        
        # Get the base name of the file to process
        base_file_name = os.path.basename(file_path)
        container_file_path = os.path.join(container_input_dir, base_file_name)

        # Create the input and output directories in the container if they don't exist
        try:
            create_input_dir_command = f"mkdir -p {container_input_dir}"
            self.container.exec_run(create_input_dir_command)
            create_output_dir_command = f"mkdir -p {container_output_dir}"
            self.container.exec_run(create_output_dir_command)
            if log_callback:
                log_callback(f"Directories '{container_input_dir}' and '{container_output_dir}' created in the container.")
        except Exception as e:
            return False, f"Errore durante la creazione delle directory nel container: {e}"

        # Copy file to container's input directory
        try:
            self.copy_to_container(os.path.dirname(file_path), os.path.splitext(base_file_name)[0], container_input_dir)
            if log_callback:
                log_callback(f"File '{base_file_name}' copiato nel container.")
        except Exception as e:
            return False, f"Errore durante la copia del file nel container: {e}"

        # Construct the command to run inside the container
        if use_fast_whisper:
            command = (f'bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch && '
                       f'python3 -u insanely-fast-whisper.py --model-name {model} --language {language} --output_format {output_format} '
                       f'--task {task} --output_dir {container_output_dir} --batch_size {batch_size} --file_name {container_file_path}"')
        else:
            command = (f'bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch && '
                       f'python3 -u -m whisper "{container_file_path}" --model {model} --language {language} --output_format {output_format} '
                       f'--task {task} --output_dir {container_output_dir} --verbose True"')

        if log_callback:
            log_callback(f"Esecuzione comando nel container: {command}")

        # --- REGEX CORRETTO E FLESSIBILE ---
        # Rende il gruppo delle ore (HH:) opzionale
        timestamp_regex = re.compile(r'\[(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\s-->\s(?:(\d{2}):)?(\d{2}:\d{2}[,.]\d{3})\]')

        try:
            # Create an exec instance using the low-level API and store its ID
            exec_instance = self.client.api.exec_create(self.container.id, command, tty=True) # Abilita TTY
            with self.process_lock:
                self.current_process_exec_id = exec_instance['Id']

            # Start the exec instance (senza demux=True quando tty=True)
            exec_stream = self.client.api.exec_start(self.current_process_exec_id, stream=True)
            
            full_output = []
            _buffer = "" # Buffer per accumulare l'output parziale
            for chunk in exec_stream:
                # Quando tty=True, lo stream non è demultiplexato, è un unico flusso di dati
                _buffer += chunk.decode('utf-8')
                while '\n' in _buffer:
                    line, _buffer = _buffer.split('\n', 1)
                    line = line.strip()
                    if not line: continue

                    if log_callback:
                        log_callback(line)
                    full_output.append(line)

                    # --- LOGICA DI PROGRESSIONE CORRETTA E ROBUSTA ---
                    if progress_callback and total_duration and total_duration > 0:
                        match = timestamp_regex.search(line)
                        if match:
                            end_hour = match.group(3)
                            end_min_sec = match.group(4)
                            
                            full_timestamp_str = f"{end_hour}:{end_min_sec}" if end_hour else end_min_sec
                            
                            current_seconds = self._parse_timestamp(full_timestamp_str)
                            percentage = int((current_seconds / total_duration) * 100)
                            progress_callback(min(percentage, 100))
            
            # Process any remaining data in the buffer after the stream ends
            if _buffer:
                line = _buffer.strip()
                if line:
                    if log_callback:
                        log_callback(line)
                    full_output.append(line)
                    if progress_callback and total_duration and total_duration > 0:
                        match = timestamp_regex.search(line)
                        if match:
                            end_hour = match.group(3)
                            end_min_sec = match.group(4)
                            
                            full_timestamp_str = f"{end_hour}:{end_min_sec}" if end_hour else end_min_sec
                            
                            current_seconds = self._parse_timestamp(full_timestamp_str)
                            percentage = int((current_seconds / total_duration) * 100)
                            progress_callback(min(percentage, 100))
                
            # Get the exit code after the command finishes
            exec_info = self.client.api.exec_inspect(self.current_process_exec_id)
            exit_code = exec_info['ExitCode']

            with self.process_lock:
                self.current_process_exec_id = None # Clear the exec_id after completion

            if exit_code == 0:
                if progress_callback: progress_callback(100) # Ensure 100% on completion
                
                # Copia i file di output dal container al percorso locale
                copy_success, copy_message = self.copy_from_container(container_output_dir, output_dir, log_callback)
                if not copy_success:
                    return False, f"Comando Whisper eseguito con successo, ma errore durante la copia dei file di output: {copy_message}"
                
                return True, "Comando Whisper eseguito con successo nel container e file di output copiati."
            elif exit_code == 130: # Typically SIGINT (Ctrl+C), can be used for graceful termination
                if progress_callback: progress_callback(0) # Reset progress bar
                return True, "Processo Whisper nel container interrotto dall'utente."
            else:
                return False, f"Errore durante l'esecuzione di Whisper (Codice: {exit_code}):\n{' '.join(full_output)}"
        except Exception as e:
            with self.process_lock:
                self.current_process_exec_id = None # Clear the exec_id on error
            return False, f"Errore inatteso durante l'esecuzione nel container: {e}"

    def stop_process(self, log_callback=None):
        with self.process_lock:
            if self.current_process_exec_id:
                try:
                    # Docker doesn't have a direct way to "kill" an exec_run command by its ID.
                    # The most reliable way to stop a process inside a container is to find its PID
                    # and send a signal. This requires running another exec command.
                    # First, find the PID of the 'whisper' or 'python3 insanely-fast-whisper.py' process
                    # This assumes only one such process is running from our exec command.
                    pid_command = f"ps aux | grep -E 'whisper|insanely-fast-whisper.py' | grep -v grep | awk '{{print $2}}'"
                    _res = self.container.exec_run(pid_command, stream=False, demux=False)
                    pids = _res.output.decode('utf-8').strip().split('\n')
                    pids = [p for p in pids if p] # Filter out empty strings

                    if pids:
                        for pid in pids:
                            kill_command = f"kill -TERM {pid}" # Send SIGTERM
                            self.container.exec_run(kill_command)
                            if log_callback:
                                log_callback(f"Inviato SIGTERM a PID {pid} nel container.")
                        self.current_process_exec_id = None
                        return True
                    else:
                        if log_callback:
                            log_callback("Nessun processo Whisper/insanely-fast-whisper trovato nel container per terminazione.")
                        return False
                except Exception as e:
                    if log_callback:
                        log_callback(f"Errore durante la terminazione del processo nel container: {e}")
                    return False
            return False
