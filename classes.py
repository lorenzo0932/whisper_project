import sys
import yt_dlp
import docker
import tarfile
import os
import glob

class YTDLManager:
    def __init__(self, link, input_folder, name, format):
        self._link = link
        self._input_folder = input_folder
        self._name = name
        self._format = format       

    def verify_format(self):
        """
        Verifica se il formato selezionato è disponibile per il video specificato.

        Args:
            link (str): URL del video YouTube.
            format (str): ID del formato desiderato (ad esempio "234").

        Returns:
            bool: True se il formato è disponibile, False altrimenti.
        """
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self._link, download=False)
            #cerca tra i --list-format di yt-dlp il nostro self.format solo cercando fra gli id
            #print(json.dumps(ydl.sanitize_info(info), indent=4))
            if any(f['format_id'] == self._format for f in info.get('formats', [])):
                return True
            else:
                return False
            
    def download_video(self):
        """
        Scarica il video YouTube specificato utilizzando yt-dlp.
        """
        ydl_opts = {
            'format': self._format,
            'outtmpl': f"{self._input_folder}/{self._name}.%(ext)s",
            'quiet': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([self._link])
                print(f"Operazione di download Avvenuta con successo\n")
            except Exception as e:
                print(f"Errore durante la download: {e}\n")
                
    def run (self):
        if self.verify_format():
            self.download_video()
        else:
            print("Il formato selezionato non è disponibile per il video specificato.\n")
            sys.exit(1)
                        
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


