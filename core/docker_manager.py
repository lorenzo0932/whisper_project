# --- whisper_gui/core/docker_manager.py ---
import docker
import tarfile
import os
import glob

class DockerManager:
    def __init__(self, container_name):
        try:
            self.client = docker.from_env()
            self.container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            raise ConnectionError(f"Container Docker '{container_name}' non trovato. Assicurati che sia in esecuzione.")
        except docker.errors.DockerException:
            raise ConnectionError("Errore di connessione al demone Docker. Assicurati che Docker sia installato e in esecuzione.")

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

    def run_whisper(self, model, language, task, output_format, output_dir, file_path, use_fast_whisper=False, batch_size=4, log_callback=None):
        if use_fast_whisper:
            command = (f'bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch && '
                       f'python3 insanely-fast-whisper.py --model-name {model} --language {language} --output_format {output_format} '
                       f'--task {task} --output_dir {output_dir} --batch_size {batch_size} --file_name {file_path}"')
        else:
            command = (f'bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch && '
                       f'whisper "{file_path}" --model {model} --language {language} --output_format {output_format} '
                       f'--task {task} --output_dir {output_dir}"')

        if log_callback:
            log_callback(f"Esecuzione comando nel container: {command}")

        try:
            exec_result = self.container.exec_run(command, stream=True, demux=True)
            
            full_output = []
            for stdout_chunk, stderr_chunk in exec_result.output:
                if stdout_chunk:
                    line = stdout_chunk.decode('utf-8').strip()
                    if log_callback:
                        log_callback(line)
                    full_output.append(line)
                if stderr_chunk:
                    line = stderr_chunk.decode('utf-8').strip()
                    if log_callback:
                        log_callback(f"ERR: {line}")
                    full_output.append(f"ERR: {line}")

            # exec_run non fornisce un exit_code in streaming, dobbiamo ispezionare dopo
            exit_code = self.client.api.exec_inspect(exec_result.exec_id)['ExitCode']

            if exit_code == 0:
                return True, "Comando Whisper eseguito con successo nel container."
            else:
                return False, f"Errore durante l'esecuzione di Whisper (Codice: {exit_code}):\n{' '.join(full_output)}"
        except Exception as e:
            return False, f"Errore inatteso durante l'esecuzione nel container: {e}"