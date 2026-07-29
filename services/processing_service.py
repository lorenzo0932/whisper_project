import os
import sys
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from utils.config_manager import ConfigManager
from core.whispercpp_manager import WhisperCppManager
from core.youtube_manager import YoutubeManager
from utils.audio_utils import get_audio_duration, convert_to_wav_16khz

logger = logging.getLogger(__name__)

class ProcessingService(QObject):
    started_signal = pyqtSignal()
    stage_changed_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self._is_working = False
        self._is_cancelled = False

        self._find_bin_path()

        self._generated_files = []
        self._output_prefix = None
        self.yt_manager = None

    def _find_bin_path(self):
        models_dir = self.config_manager.models_dir
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        if not os.path.isdir(bin_dir):
            bin_dir = os.path.join(sys._MEIPASS, "bin") if hasattr(sys, '_MEIPASS') else bin_dir
        self._bin_dir = bin_dir
        self._models_dir = models_dir
        self.whisper_manager = WhisperCppManager(
            bin_path=os.path.join(bin_dir, "whisper-cli"),
            models_dir=models_dir
        )

    def _check_cancelled(self):
        """Metodo di callback per il downloader dei modelli."""
        return self._is_cancelled

    def start_processing(self, params: dict):
        if self._is_working:
            return

        self._is_working = True
        self._is_cancelled = False
        self._generated_files.clear()
        self._output_prefix = None
        self.started_signal.emit()
        
        file_to_process = None
        temp_wav_file = None

        try:
            # --- 1. GESTIONE INPUT (Download o File Locale) ---
            file_to_process = self._handle_input(params)
            
            if self._is_cancelled:
                self._cleanup_and_finish(False, "Operazione annullata.")
                return
            if not file_to_process:
                self._cleanup_and_finish(False, "Recupero del file fallito.")
                return

            # Se è un download da YT, tracciamolo per pulizia in caso di Stop
            if params['input_type'] == "youtube":
                self._generated_files.append(file_to_process)

            # --- 2. VERIFICA E DOWNLOAD DEL MODELLO ---
            self.stage_changed_signal.emit(f"Controllo modello {params['model']}...")
            self.progress_signal.emit(0)
            
            model_ready = self.whisper_manager.download_model(
                model_name=params['model'],
                progress_callback=self.progress_signal.emit,
                log_callback=self.log_signal.emit,
                is_cancelled_cb=self._check_cancelled
            )
            
            if self._is_cancelled:
                self._cleanup_and_finish(False, "Download modello annullato.")
                return
            if not model_ready:
                self._cleanup_and_finish(False, "Impossibile scaricare il modello.")
                return

            # --- 3. CONVERSIONE AUDIO (Obbligatoria per whisper.cpp) ---
            self.stage_changed_signal.emit("Conversione audio...")
            self.log_signal.emit("Generazione file WAV 16kHz (PCM)...")
            
            temp_wav_file = os.path.splitext(file_to_process)[0] + "_16khz.wav"
            self._generated_files.append(temp_wav_file)
            
            conversion_ok = convert_to_wav_16khz(file_to_process, temp_wav_file)
            
            if self._is_cancelled:
                self._cleanup_and_finish(False, "Conversione interrotta.")
                return
            if not conversion_ok:
                self._cleanup_and_finish(False, "Errore nella conversione con FFmpeg.")
                return

            # --- 4. TRASCRIZIONE ---
            self.stage_changed_signal.emit("Trascrizione in corso...")
            total_duration = get_audio_duration(temp_wav_file)
            
            output_dir = params['output_dir']
            output_name = params['name']
            self._output_prefix = os.path.join(output_dir, output_name)
            
            # Recupera scelta GPU/CPU dalle impostazioni
            device_mode = self.config_manager.get("device_mode", "gpu")
            
            success, message = self.whisper_manager.run_whisper(
                model=params['model'],
                language=params['language'],
                task=params['task'],
                output_format=params['output_format'],
                output_dir=output_dir,
                file_path=temp_wav_file,
                output_name=output_name,
                total_duration=total_duration,
                log_callback=self.log_signal.emit,
                progress_callback=self.progress_signal.emit,
                device_mode=device_mode
            )

            # --- FALLBACK AUTOMATICO SU CPU SE GPU FALLISCE ---
            if not success and not self._is_cancelled and device_mode == "gpu":
                self.log_signal.emit("\n[!] Fallimento GPU rilevato. Avvio fallback su CPU...")
                self.stage_changed_signal.emit("Fallback: Trascrizione CPU...")
                self.progress_signal.emit(0)
                
                success, message = self.whisper_manager.run_whisper(
                    model=params['model'],
                    language=params['language'],
                    task=params['task'],
                    output_format=params['output_format'],
                    output_dir=output_dir,
                    file_path=temp_wav_file,
                    output_name=output_name,
                    total_duration=total_duration,
                    log_callback=self.log_signal.emit,
                    progress_callback=self.progress_signal.emit,
                    device_mode="cpu" # Forza CPU
                )
            
            if self._is_cancelled:
                self._cleanup_and_finish(False, "Interrotto dall'utente.")
            else:
                self._cleanup_and_finish(success, message)

        except Exception as e:
            if not self._is_cancelled:
                msg = f"Errore critico servizio: {e}"
                self.log_signal.emit(msg)
                self._cleanup_and_finish(False, msg)

    def _handle_input(self, params: dict) -> str | None:
        """Scarica da YT o verifica file locale."""
        input_type = params['input_type']
        if input_type == "youtube":
            self.stage_changed_signal.emit("Download YouTube...")
            self.yt_manager = YoutubeManager(
                link=params['file_path'],
                input_folder=self.config_manager.get("input_dir"),
                name=params['name'],
            )
            success, result = self.yt_manager.run(progress_callback=self.progress_signal.emit)
            return result if success else None
        else:
            p = params['file_path']
            if not os.path.exists(p):
                self.log_signal.emit(f"File non trovato: {p}")
                return None
            self.progress_signal.emit(0)
            return p

    def _cleanup_and_finish(self, success: bool, message: str):
        """Gestisce la pulizia dei file generati."""
        # Se interrotto: cancella tutto (download YT, WAV convertiti, trascrizioni incomplete)
        if self._is_cancelled:
            self.log_signal.emit("Pulizia file residui in corso...")
            for f in self._generated_files:
                if f and os.path.exists(f):
                    try: os.remove(f)
                    except: pass

            if self._output_prefix:
                for ext in [".srt", ".vtt", ".txt", ".tsv", ".json"]:
                    out = self._output_prefix + ext
                    if os.path.exists(out):
                        try: os.remove(out)
                        except: pass
            
            message = "Processo annullato. Sistema ripulito."
            success = False

        # Se completato: cancella solo il WAV a 16kHz temporaneo, lascia l'input e l'output
        else:
            temp_wav = next((f for f in self._generated_files if f.endswith("_16khz.wav")), None)
            if temp_wav and os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except: pass

        self._is_working = False
        self.finished_signal.emit(success, message)

    def stop(self):
        """Richiesta di interruzione immediata."""
        if self._is_working:
            self._is_cancelled = True
            self.log_signal.emit("\n[!] Richiesta STOP ricevuta.")
            
            if self.yt_manager:
                try:
                    self.yt_manager.stop()
                except Exception as e:
                    logger.warning("Errore nello stop di yt-dlp: %s", e)
                
            # Ferma il binario C++
            self.whisper_manager.stop_process()