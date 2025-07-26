import sys
import yt_dlp

class YTDLManager:
    def __init__(self, link, input_folder, name, format_id):
        self._link = link
        self._input_folder = input_folder
        self._name = name
        self._format_id = format_id # Renamed from _format to _format_id

    def get_audio_only_formats(self):
        """
        Ottiene una lista di ID di formati audio-only disponibili per il video,
        ordinati in ordine decrescente a partire da 251.
        """
        ydl_opts = {'quiet': True, 'simulate': True, 'skip_download': True}
        audio_formats = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self._link, download=False)
                for f in info.get('formats', []):
                    # Check if it's an audio-only format and has a format_id
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('format_id'):
                        try:
                            format_id_int = int(f['format_id'])
                            if format_id_int >= 251: # Start from 251 as requested
                                audio_formats.append(format_id_int)
                        except ValueError:
                            # Ignore format_ids that are not purely numeric
                            pass
            # Sort in descending order
            audio_formats.sort(reverse=True)
            return audio_formats
        except Exception as e:
            print(f"Errore durante il recupero dei formati audio: {e}")
            return []

    def verify_format(self, format_to_verify):
        """
        Verifica se il formato selezionato è disponibile per il video specificato.

        Args:
            format_to_verify (str): ID del formato desiderato (ad esempio "234").

        Returns:
            tuple: (bool, str) - True if format is available, False otherwise, and an error message if applicable.
        """
        ydl_opts = {'quiet': False}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self._link, download=False)
                for f in info['formats']:
                    format_id = f.get('format_id')
                    if format_to_verify in format_id:
                        return True, None
                else:
                    return False, f"Il formato {format_to_verify} non è disponibile per il video specificato."
        except Exception as e:
            error_str = str(e)
            if "HTTP Error 403: Forbidden" in error_str:
                return False, "Errore: Il video è protetto o non disponibile per la verifica del formato (HTTP 403 Forbidden)."
            else:
                return False, f"Errore durante la verifica del formato: {error_str}"
            
    def download_video(self, format_to_download):
        """
        Scarica il video YouTube specificato utilizzando yt-dlp.
        """
        ydl_opts = {
            'format': format_to_download,
            'outtmpl': f"{self._input_folder}/{self._name}.%(ext)s",
            'quiet': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([self._link])
                print(f"Operazione di download Avvenuta con successo con formato {format_to_download}\n")
                return True, None # Success, no error message
            except Exception as e:
                error_str = str(e)
                if "HTTP Error 403: Forbidden" in error_str:
                    error_message = "Errore: Il video è protetto o non disponibile per il download (HTTP 403 Forbidden).\n"
                else:
                    error_message = f"Errore durante il download con formato {format_to_download}: {error_str}\n"
                print(error_message)
                return False, error_message # Failure, with error message
                
    def run (self):
        if self._format_id == "auto":
            print("Modalità automatica: ricerca e download del miglior formato audio disponibile.")
            audio_formats = self.get_audio_only_formats()
            if not audio_formats:
                return False, "Nessun formato audio-only disponibile trovato o errore nel recupero."

            for fmt_id in audio_formats:
                print(f"Tentativo di download con formato ID: {fmt_id}")
                success_download, error_message_download = self.download_video(str(fmt_id))
                if success_download:
                    return True, None # Successfully downloaded with this format
                else:
                    print(f"Fallito con formato {fmt_id}: {error_message_download}")
            return False, "Tutti i tentativi di download automatico sono falliti."
        else:
            # Existing manual format logic
            success_verify, error_message_verify = self.verify_format(self._format_id)
            if success_verify:
                success_download, error_message_download = self.download_video(self._format_id)
                return success_download, error_message_download
            else:
                print(error_message_verify + "\n")
                return False, error_message_verify
