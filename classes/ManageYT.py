import sys
import yt_dlp

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
           