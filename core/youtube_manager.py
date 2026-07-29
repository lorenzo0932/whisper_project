import logging
import yt_dlp
import re

logger = logging.getLogger(__name__)

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

class YoutubeManager:
    def __init__(self, link, input_folder, name):
        self._link = link
        self._input_folder = input_folder
        self._name = name
        self.progress_callback = None
        self._ydl = None

    def _progress_hook(self, d):
        if d['status'] == 'downloading' and self.progress_callback:
            percent_str = d.get('_percent_str', '0.0%')
            cleaned = _ANSI_RE.sub('', percent_str).strip()
            try:
                percentage = float(cleaned.replace('%', ''))
                self.progress_callback(int(percentage))
            except (ValueError, TypeError):
                pass

    def download_video(self, format_to_download):
        ydl_opts = {
            'format': format_to_download,
            'outtmpl': f"{self._input_folder}/{self._name}.%(ext)s",
            'quiet': True,
            'noplaylist': True,
            'progress_hooks': [self._progress_hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self._ydl = ydl
            try:
                info = ydl.extract_info(self._link, download=True)
                filepath = info.get('filepath') or ydl.prepare_filename(info)
                return True, filepath
            except Exception as e:
                return False, f"Errore durante il download: {e}"
            finally:
                self._ydl = None

    def run(self, progress_callback=None):
        self.progress_callback = progress_callback
        logger.info("Download del miglior audio disponibile.")
        success_download, result = self.download_video('bestaudio/best')
        if success_download:
            return True, result
        return False, f"Download fallito: {result}"

    def stop(self):
        if self._ydl is not None:
            try:
                self._ydl.params['quiet'] = True
            except Exception:
                pass
