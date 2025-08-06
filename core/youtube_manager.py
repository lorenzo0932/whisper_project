import sys
import yt_dlp
import re

class Youtube_manager:
    def __init__(self, link, input_folder, name, format_id):
        self._link = link
        self._input_folder = input_folder
        self._name = name
        self._format_id = format_id
        self.progress_callback = None

    def _progress_hook(self, d):
        """
        Questa funzione viene chiamata da yt-dlp durante il download.
        """
        if d['status'] == 'downloading' and self.progress_callback:
            # L'output di yt-dlp può contenere codici di colore ANSI, li rimuoviamo
            percent_str = d.get('_percent_str', '0.0%')
            cleaned_percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).strip()
            
            try:
                # Estrae il valore numerico della percentuale
                percentage = float(cleaned_percent_str.replace('%', ''))
                self.progress_callback(int(percentage))
            except (ValueError, TypeError):
                pass # Ignora errori di parsing, il prossimo hook correggerà

    def download_video(self, format_to_download):
        """
        Scarica il video YouTube specificato utilizzando yt-dlp.
        """
        ydl_opts = {
            'format': format_to_download,
            'outtmpl': f"{self._input_folder}/{self._name}.%(ext)s",
            'quiet': True, # Mettiamo a True per gestire noi l'output
            'noplaylist': True,
            'progress_hooks': [self._progress_hook], # <-- Ecco la magia!
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self._link, download=True)
                filepath = info.get('filepath') or ydl.prepare_filename(info)
                return True, filepath
            except Exception as e:
                return False, f"Errore durante il download: {e}"

    def run(self, progress_callback=None):
        """
        Esegue il processo di download.
        Accetta un callback per gli aggiornamenti di progresso.
        """
        self.progress_callback = progress_callback
        
        # Per semplicità, usiamo la modalità automatica. Puoi ripristinare la logica
        # di verifica del formato se necessario.
        print("Modalità automatica: ricerca e download del miglior formato audio disponibile.")
        
        # Scegliamo un formato audio di alta qualità (es. m4a o webm)
        success_download, result = self.download_video('bestaudio/best')
        
        if success_download:
            return True, result
        else:
            return False, f"Tutti i tentativi di download sono falliti. Errore: {result}"