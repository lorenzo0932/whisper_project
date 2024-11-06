import docker
import tarfile
import os
import glob

class Docker:
    def __init__(self,  container_name):
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name)
    
    def _find_file_by_name(self, src_path, file_name):
        """
        Trova un file che inizia con `file_name` in una src_path specificata.
        :param src_path: src_path in cui cercare.
        :param file_name: Nome del file senza estensione.
        :return: Il percorso completo del file trovato.
        """
        search_pattern = os.path.join(src_path, f"{file_name}.*")
        files = glob.glob(search_pattern)
        if files:
            return files[0]  # Restituisce il primo file che corrisponde al pattern
        else:
            raise FileNotFoundError(f"Nessun file trovato con nome '{file_name}' in '{src_path}'.")

    
    def copy_to_container(self, src_path, file_name, container_dest_path):
        """
        Copies a file from the local machine to the Docker container.

        :param src_path: Path where the file is located on the local machine
        :type src_path: str
        :param file_name: Name of the file without extension
        :type file_name: str
        :param container_dest_path: Path inside the Docker container where the file will be copied
        :type container_dest_path: str
        """
        
        # Operazioni per trovare il file passato senza estensione
        local_file_path = self._find_file_by_name(src_path, file_name)
        file_name = os.path.basename(local_file_path)
        
        # Aggiunge il file a un archivio temporaneo
        with tarfile.open('temp.tar', mode='w') as tar:
            tar.add(local_file_path, arcname=os.path.basename(local_file_path))
        # Copia l'archivio temporaneo nel contenitore Docker
        with open('temp.tar', 'rb') as tar_file:
            self.container.put_archive(container_dest_path, tar_file.read())
        
        # Rimuove il file temporaneo appena creato
        os.remove('temp.tar')
        print(f"File '{local_file_path}' copiato nel container con successo a '{container_dest_path}'.")
        
        
    def copy_from_container(self, container_file_path, dest_path):
        """
        Copia un file dal container al sistema host.
        
        :param container_file_path: Percorso completo del file all'interno del container.
        :param dest_path: Cartella di destinazione sul sistema host.
        """
        file_name = os.path.basename(container_file_path)

        # Ottieni il file come archivio tar
        bits, _ = self.container.get_archive(container_file_path)
        with open('temp.tar', 'wb') as tar_file:
            for chunk in bits:
                tar_file.write(chunk)

        # Estrai il file dall'archivio tar nella cartella di destinazione
        with tarfile.open('temp.tar') as tar:
            tar.extractall(path=dest_path)

        os.remove('temp.tar')
        print(f"File '{container_file_path}' copiato dal container al sistema host con successo a '{dest_path}/{file_name}'.")

    def run(self, model, language, task, output_format, output_dir, file_path):
        """
        Esegue un comando nel contenitore Docker.
        """
        command = f'bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch && whisper --model {model} --language {language} --output_format {output_format} --task {task} --output_dir {output_dir} {file_path}"'
        print("Esecuzione del comando whisper...")
        result = self.container.exec_run(command)
        if result.exit_code == 0:
            print("Comando eseguito con successo.")
        else:
            print(f"Errore durante l'esecuzione del comando: {result.output.decode()}")

