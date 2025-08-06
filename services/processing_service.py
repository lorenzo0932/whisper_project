import os
from PyQt6.QtCore import QObject, pyqtSignal

# Import corretti come da specifica
from utils.config_manager import ConfigManager
from core.docker_manager import DockerManager
from core.native_manager import NativeWhisper
from core.youtube_manager import Youtube_manager
from utils.audio_utils import get_audio_duration

class ProcessingService(QObject):
    started_signal = pyqtSignal()
    # NUOVO: Segnale per notificare il cambio di fase (es. da download a trascrizione)
    stage_changed_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self._is_working = False

    def start_processing(self, params: dict):
        if self._is_working:
            self.log_signal.emit("Un processo è già in esecuzione.")
            return

        self._is_working = True
        self.started_signal.emit()
        
        try:
            # 1. Gestione dell'input
            file_to_process = self._handle_input(params)
            if not file_to_process:
                self._cleanup_and_finish(False, "Gestione dell'input fallita.")
                return

            self.stage_changed_signal.emit("Trascrizione in corso...")
            
            total_duration = get_audio_duration(file_to_process)
            if total_duration:
                self.log_signal.emit(f"Durata totale per la trascrizione: {total_duration:.2f} secondi.")
            else:
                self.log_signal.emit("ATTENZIONE: Impossibile determinare la durata. La barra di progresso per Whisper non sarà disponibile.")

            # 2. Esecuzione di Whisper
            execution_mode = self.config_manager.get("execution_mode")
            if execution_mode == "docker":
                # La logica per il progresso di Docker va implementata in modo simile.
                self.log_signal.emit("La barra di progresso per Docker non è ancora implementata.")
                docker_manager = DockerManager(self.config_manager.get("docker_container_name"))
                # ... (chiamata a docker_manager)
                success, message = True, "Simulazione Docker completata."
            else:
                native_manager = NativeWhisper()
                success, message = native_manager.run_whisper(
                    model=params['model'],
                    language=params['language'],
                    task=params['task'],
                    output_format=params['output_format'],
                    output_dir=self.config_manager.get("output_text_dir"),
                    file_path=file_to_process,
                    total_duration=total_duration,
                    log_callback=self.log_signal.emit,
                    progress_callback=self.progress_signal.emit
                )
            
            self._cleanup_and_finish(success, message)

        except Exception as e:
            error_msg = f"Errore critico nel servizio di elaborazione: {e}"
            self.log_signal.emit(error_msg)
            self._cleanup_and_finish(False, error_msg)

    def _handle_input(self, params: dict) -> str | None:
        input_type = params['input_type']
        
        if input_type == "youtube":
            self.stage_changed_signal.emit("Download in corso...")
            yt_manager = Youtube_manager(
                link=params['file_path'],
                input_folder=self.config_manager.get("input_dir"),
                name=params['name'],
                format_id="auto"
            )
            success, result = yt_manager.run(progress_callback=self.progress_signal.emit)
            if success:
                return result
            else:
                return None
        else:
            file_path = params['file_path']
            if not os.path.exists(file_path):
                self.log_signal.emit(f"File di input non trovato: {file_path}")
                return None
            self.progress_signal.emit(0)
            return file_path

    def _cleanup_and_finish(self, success: bool, message: str):
        self._is_working = False
        self.finished_signal.emit(success, message)