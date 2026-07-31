import os
import logging
import threading
from PyQt6.QtCore import QObject, pyqtSignal

from utils.config_manager import ConfigManager
from core.whispercpp_manager import WhisperCppManager
from core.youtube_manager import YoutubeManager
from utils.resource_path import resource_path, binary_name
from utils.audio_utils import (
    get_audio_duration,
    convert_to_wav_16khz,
    embed_subtitles,
    burn_subtitles
)

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

        self._stop_event = threading.Event()
        self._working_event = threading.Event()

        self._find_bin_path()

        self._generated_files = []
        self._output_prefix = None
        self.yt_manager = None
        self._video_source = None
        self._ffmpeg_processes = []

    def _find_bin_path(self):
        models_dir = self.config_manager.models_dir
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
        if not os.path.isdir(bin_dir):
            bin_dir = resource_path("bin")
        self._bin_dir = bin_dir
        self._models_dir = models_dir
        self.whisper_manager = WhisperCppManager(
            bin_path=os.path.join(bin_dir, binary_name("whisper-cli")),
            models_dir=models_dir
        )

    def _check_cancelled(self):
        return self._stop_event.is_set()

    def start_processing(self, params: dict):
        if self._working_event.is_set():
            return

        self._working_event.set()
        self._stop_event.clear()
        self._generated_files.clear()
        self._output_prefix = None
        self._video_source = None
        self.started_signal.emit()

        subs_mode = params.get("subs_mode", "none")
        if (subs_mode != "none" and params['input_type'] == "youtube"
                and params.get('yt_mode', 'audio') != 'video'):
            params['yt_mode'] = 'video'
            self.log_signal.emit("[!] Sottotitoli richiesti: download YouTube passato a Audio+Video.")

        file_to_process = None
        temp_wav_file = None

        try:
            file_to_process = self._handle_input(params)

            if self._stop_event.is_set():
                self._cleanup_and_finish(False, "Operazione annullata.")
                return
            if not file_to_process:
                self._cleanup_and_finish(False, "Recupero del file fallito.")
                return

            if params['input_type'] == "youtube":
                self._generated_files.append(file_to_process)

            self.stage_changed_signal.emit(f"Controllo modello {params['model']}...")
            self.progress_signal.emit(0)

            model_ready = self.whisper_manager.download_model(
                model_name=params['model'],
                progress_callback=self.progress_signal.emit,
                log_callback=self.log_signal.emit,
                is_cancelled_cb=self._check_cancelled
            )

            if self._stop_event.is_set():
                self._cleanup_and_finish(False, "Download modello annullato.")
                return
            if not model_ready:
                self._cleanup_and_finish(False, "Impossibile scaricare il modello.")
                return

            self.stage_changed_signal.emit("Conversione audio...")
            self.log_signal.emit("Generazione file WAV 16kHz (PCM)...")

            temp_wav_file = os.path.splitext(file_to_process)[0] + "_16khz.wav"
            self._generated_files.append(temp_wav_file)

            conversion_ok = convert_to_wav_16khz(file_to_process, temp_wav_file)

            if self._stop_event.is_set():
                self._cleanup_and_finish(False, "Conversione interrotta.")
                return
            if not conversion_ok:
                self._cleanup_and_finish(False, "Errore nella conversione con FFmpeg.")
                return

            self.stage_changed_signal.emit("Trascrizione in corso...")
            total_duration = get_audio_duration(temp_wav_file)

            output_dir = params['output_dir']
            output_name = params['name']
            self._output_prefix = os.path.join(output_dir, output_name)

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

            if not success and not self._stop_event.is_set() and device_mode == "gpu":
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
                    device_mode="cpu"
                )

            if self._stop_event.is_set():
                self._cleanup_and_finish(False, "Interrotto dall'utente.")
            elif success:
                success, message = self._apply_subtitles(params)
                self._cleanup_and_finish(success, message)
            else:
                self._cleanup_and_finish(success, message)

        except Exception as e:
            if not self._stop_event.is_set():
                msg = f"Errore critico servizio: {e}"
                self.log_signal.emit(msg)
                self._cleanup_and_finish(False, msg)

    def _handle_input(self, params: dict) -> str | None:
        input_type = params['input_type']
        if input_type == "youtube":
            self.stage_changed_signal.emit("Download YouTube...")
            self.yt_manager = YoutubeManager(
                link=params['file_path'],
                input_folder=self.config_manager.get("input_dir"),
                name=params['name'],
                mode=params.get('yt_mode', 'audio'),
            )
            success, result = self.yt_manager.run(progress_callback=self.progress_signal.emit)
            if success and params.get('yt_mode') == 'video':
                self._video_source = result
            return result if success else None
        else:
            p = params['file_path']
            if not os.path.exists(p):
                self.log_signal.emit(f"File non trovato: {p}")
                return None
            if input_type == "video":
                self._video_source = p
            self.progress_signal.emit(0)
            return p

    def _apply_subtitles(self, params: dict):
        subs_mode = params.get("subs_mode", "none")
        if subs_mode == "none" or not self._video_source:
            return True, "Trascrizione completata con successo."

        srt_path = os.path.join(params['output_dir'], params['name'] + ".srt")
        if not os.path.exists(srt_path):
            self.log_signal.emit("[!] Sottotitoli saltati: file SRT non trovato.")
            return True, "Trascrizione completata (sottotitoli non integrati)."

        self.stage_changed_signal.emit("Integrazione sottotitoli...")
        self.log_signal.emit(f"Video sorgente: {self._video_source}")
        self.progress_signal.emit(0)
        total_duration = get_audio_duration(self._video_source) or 0

        if subs_mode == "soft":
            ext = os.path.splitext(self._video_source)[1].lower() or ".mp4"
            output_path = self._output_prefix + "_subs" + ext
            ok = embed_subtitles(
                self._video_source, srt_path, output_path,
                total_duration=total_duration,
                progress_callback=self.progress_signal.emit,
                is_cancelled_cb=self._check_cancelled,
                process_registry=self._ffmpeg_processes
            )
            label = "traccia soft"
        else:
            output_path = self._output_prefix + "_burned.mp4"
            ok = burn_subtitles(
                self._video_source, srt_path, output_path,
                total_duration=total_duration,
                progress_callback=self.progress_signal.emit,
                is_cancelled_cb=self._check_cancelled,
                process_registry=self._ffmpeg_processes
            )
            label = "sottotitoli incisi"

        if not ok:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    logger.debug("Failed to remove partial subtitle output: %s", output_path)
            return False, f"Errore nell'integrazione dei sottotitoli ({label})."

        self._generated_files.append(output_path)
        self.log_signal.emit(f"Video con {label}: {output_path}")
        return True, f"Trascrizione completata. Video con {label}: {output_path}"

    def _cleanup_and_finish(self, success: bool, message: str):
        if self._stop_event.is_set():
            self.log_signal.emit("Pulizia file residui in corso...")
            for f in self._generated_files:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        logger.debug("Failed to remove temp file: %s", f)

            if self._output_prefix:
                for ext in [".srt", ".vtt", ".txt", ".tsv", ".json"]:
                    out = self._output_prefix + ext
                    if os.path.exists(out):
                        try:
                            os.remove(out)
                        except Exception:
                            logger.debug("Failed to remove output file: %s", out)

            message = "Processo annullato. Sistema ripulito."
            success = False
        else:
            temp_wav = next((f for f in self._generated_files if f.endswith("_16khz.wav")), None)
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception as e:
                    logger.warning("Failed to remove temp wav: %s", e)

        self._working_event.clear()
        self.finished_signal.emit(success, message)

    def stop(self):
        if self._working_event.is_set():
            self._stop_event.set()
            self.log_signal.emit("\n[!] Richiesta STOP ricevuta.")

            if self.yt_manager:
                try:
                    self.yt_manager.stop()
                except Exception as e:
                    logger.warning("Errore nello stop di yt-dlp: %s", e)

            self.whisper_manager.stop_process()

            for proc in list(self._ffmpeg_processes):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(3)
                    except Exception:
                        proc.kill()