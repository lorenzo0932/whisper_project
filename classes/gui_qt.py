import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QPushButton, QTextEdit, QButtonGroup, QFileDialog, QMessageBox,
    QGroupBox, # Added QGroupBox for better layout
    QComboBox # Added QComboBox for model selection
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess
import os
import threading
import queue
from . import ManageYT
from . import ManageDocker

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    # Change signal to emit a tuple: (success_status, error_message)
    process_finished_signal = pyqtSignal(bool, str) 

    def __init__(self, target_function, *args, **kwargs):
        super().__init__()
        self.target_function = target_function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        success = False
        error_message = "An unknown error occurred."
        try:
            # Ensure target_function always returns (bool, str)
            result = self.target_function(*self.args, **self.kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                success, error_message = result
            else:
                error_message = f"Worker function returned unexpected type: {type(result)}"
        except Exception as e:
            error_message = f"Error in worker thread: {e}"
        finally:
            self.log_signal.emit(error_message)
            self.process_finished_signal.emit(success, error_message)

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader e Whisper")
        self.setGeometry(100, 100, 750, 600) # Adjusted size for better balance and readability

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20) # Adjusted margins
        main_layout.setSpacing(12) # Adjusted spacing between major sections

        # --- Input Section ---
        input_group = QGroupBox("Input e Opzioni")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(8) # Adjusted spacing within group box

        # File Name
        name_layout = QHBoxLayout()
        # File Name
        name_layout = QHBoxLayout()
        # File Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome del file:"))
        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText("Nome del file (es. audio.mp3)")
        name_layout.addWidget(self.name_entry, 1) # Re-added stretch
        input_layout.addLayout(name_layout)

        # Model Size Selector
        model_selection_layout = QHBoxLayout()
        model_selection_layout.addWidget(QLabel("Modello Whisper:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3", "Custom"])
        self.model_combo.setCurrentText("medium") # Default selection
        model_selection_layout.addWidget(self.model_combo, 1) # Re-added stretch
        input_layout.addLayout(model_selection_layout)

        # Custom Model Entry (initially hidden)
        self.custom_model_layout = QHBoxLayout()
        self.custom_model_label = QLabel("Nome modello custom:")
        self.custom_model_entry = QLineEdit()
        self.custom_model_entry.setPlaceholderText("es. custom_model_name")
        self.custom_model_layout.addWidget(self.custom_model_label)
        self.custom_model_layout.addWidget(self.custom_model_entry, 1) # Re-added stretch
        input_layout.addLayout(self.custom_model_layout)

        # Input Type Radio Buttons
        input_type_group_box = QHBoxLayout()
        input_type_group_box.addWidget(QLabel("Tipo di input:"))
        
        self.input_type_group = QButtonGroup(self)
        self.radio_youtube = QRadioButton("YouTube link")
        self.radio_audio = QRadioButton("File audio")
        self.radio_video = QRadioButton("File video")

        self.radio_youtube.setChecked(True) # Default selection
        self.input_type_group.addButton(self.radio_youtube)
        self.input_type_group.addButton(self.radio_audio)
        self.input_type_group.addButton(self.radio_video)

        input_type_group_box.addWidget(self.radio_youtube)
        input_type_group_box.addWidget(self.radio_audio)
        input_type_group_box.addWidget(self.radio_video)
        input_type_group_box.addStretch(1) # Keep stretch for radio buttons
        input_layout.addLayout(input_type_group_box)

        # File Path / YouTube Link
        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(QLabel("Path/Link:"))
        self.file_path_entry = QLineEdit()
        self.file_path_entry.setPlaceholderText("path/to/file or youtube link")
        file_path_layout.addWidget(self.file_path_entry, 1) # Keep stretch for file path
        
        self.browse_button = QPushButton("Sfoglia")
        self.browse_button.clicked.connect(self.show_file_dialog)
        file_path_layout.addWidget(self.browse_button)
        input_layout.addLayout(file_path_layout)

        # Format Selection (Automatico/Manuale)
        format_selection_layout = QHBoxLayout()
        format_selection_layout.addWidget(QLabel("Formato YTDL:"))
        
        self.format_mode_group = QButtonGroup(self)
        self.radio_format_auto = QRadioButton("Automatico")
        self.radio_format_manual = QRadioButton("Manuale")

        self.radio_format_auto.setChecked(True) # Default selection
        self.format_mode_group.addButton(self.radio_format_auto)
        self.format_mode_group.addButton(self.radio_format_manual)

        format_selection_layout.addWidget(self.radio_format_auto)
        format_selection_layout.addWidget(self.radio_format_manual)
        format_selection_layout.addStretch(1) # Keep stretch for format radio buttons
        input_layout.addLayout(format_selection_layout)

        # Manual Format ID Entry (initially hidden)
        self.manual_format_layout = QHBoxLayout()
        self.manual_format_label = QLabel("ID formato:")
        self.manual_format_entry = QLineEdit()
        self.manual_format_entry.setPlaceholderText("es. 251")
        self.manual_format_layout.addWidget(self.manual_format_label)
        self.manual_format_layout.addWidget(self.manual_format_entry, 1) # Re-added stretch
        input_layout.addLayout(self.manual_format_layout)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # --- Start Button ---
        self.start_button = QPushButton("Avvia Download e Trascrizione")
        self.start_button.clicked.connect(self.run_process)
        main_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Output Section ---
        output_group = QGroupBox("Log di Output")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        self.setLayout(main_layout)
        
        # Apply a modern style
        QApplication.setStyle("Fusion")
        # Apply some basic QSS for a cleaner look
        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 10pt;
                color: palette(window-text); /* Ensure all text inherits system text color */
            }
            QGroupBox {
                font-weight: bold;
                margin-top: 20px; /* Increased margin-top for title */
                border: 1px solid #AAAAAA; /* Changed border to a lighter gray for better contrast */
                border-radius: 5px;
                padding-top: 15px; /* Adjusted padding-top */
                padding-bottom: 5px;
                background-color: palette(window); /* Use system window background color */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Centered the title */
                padding: 0 10px; /* Adjusted padding for better spacing */
                background-color: transparent;
                border-radius: 0px;
                color: palette(window-text); /* Use system text color for dark mode compatibility */
                font-size: 10pt;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #444444; /* Apply the same dark gray border as QGroupBox */
                border-radius: 4px;
                padding: 5px;
                background-color: palette(base); /* Use system base color for dark mode compatibility */
                color: palette(window-text); /* Use system text color */
            }
            QComboBox {
                border: 1px solid #444444; /* Apply the same dark gray border as QGroupBox */
                border-radius: 4px;
                padding: 5px;
                background-color: palette(base); /* Ensure the main combo box has a consistent background */
                color: palette(window-text); /* Use system text color */
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                /* image: url(no_image.png); */ /* Re-enable if default arrow interferes */
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 10pt;
                margin-top: 10px;
                box-shadow: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2); /* Add a subtle shadow on hover */
            }
            QRadioButton {
                padding: 3px 0;
                color: palette(window-text);
            }
            QLabel {
                font-weight: normal;
                color: palette(window-text);
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #444444; /* Same border as other inputs */
                border-radius: 4px;
                background-color: palette(window); /* Use window background for the dropdown list */
                selection-background-color: #0056b3; /* Explicitly set selection background */
                selection-color: white; /* Ensure text is white on selection */
            }
            QComboBox QAbstractItemView::item {
                padding: 3px 5px;
                background-color: palette(window); /* Explicitly set item background to window color */
                color: palette(window-text);
                background-clip: padding-box;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #0056b3; /* Match button hover color */
                color: white;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #003f80; /* Darker blue for selected item */
                color: white;
                border: none;
            }
        """)

        # Connect radio buttons to update browse button state
        self.input_type_group.buttonClicked.connect(self.update_browse_button_state)
        self.update_browse_button_state() # Set initial state

        # Connect format mode radio buttons to update manual format entry visibility
        self.format_mode_group.buttonClicked.connect(self.update_format_entry_state)
        self.update_format_entry_state() # Set initial state

        # Connect model combo box to update custom model entry visibility
        self.model_combo.currentIndexChanged.connect(self.update_custom_model_state)
        self.update_custom_model_state() # Set initial state

    def update_browse_button_state(self):
        if self.radio_youtube.isChecked():
            self.browse_button.setEnabled(False)
        else:
            self.browse_button.setEnabled(True)

    def update_format_entry_state(self):
        if self.radio_format_manual.isChecked():
            self.manual_format_label.show()
            self.manual_format_entry.show()
            self.manual_format_entry.setEnabled(True)
        else:
            self.manual_format_label.hide()
            self.manual_format_entry.hide()
            self.manual_format_entry.setEnabled(False)

    def update_custom_model_state(self):
        if self.model_combo.currentText() == "Custom":
            self.custom_model_label.show()
            self.custom_model_entry.show()
            self.custom_model_entry.setEnabled(True)
        else:
            self.custom_model_label.hide()
            self.custom_model_entry.hide()
            self.custom_model_entry.setEnabled(False)

    def log_output(self, message):
        self.output_text.append(message)

    def show_file_dialog(self):
        if self.radio_youtube.isChecked():
            QMessageBox.warning(self, "Opzione 'Sfoglia' non disponibile con YTDL", "Per favore seleziona 'Audio file' o 'Video file' per usare questa opzione.")
            return

        if self.radio_video.isChecked():
            file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video Files (*.mp4 *.avi *.mkv)")
            if file_path:
                self.log_output(f"Selected video: {file_path}")
                self.extract_audio_from_video(file_path)
            
        elif self.radio_audio.isChecked():
            file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio", "", "Audio Files (*.wav *.mp3 *.flac *.webM)")
            if file_path:
                self.file_path_entry.setText(file_path)
                self.log_output(f"Selected audio: {file_path}")

    def extract_audio_from_video(self, video_path):
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        base_name = base_name + "_audio"
        if self.name_entry.text():
            base_name = self.name_entry.text()
        
        output_audio_path = os.path.join(os.path.dirname(video_path), "input", f"{base_name}.wav")
        os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)

        self.log_output(f"Extracting audio to: {output_audio_path}")

        command = ["ffmpeg", "-i", video_path, "-vn", "-map", "0:a:0", "-c", "copy", output_audio_path, "-y"]
        try:
            subprocess.run(command, check=True)
            self.log_output(f"Audio extracted successfully to: {output_audio_path}")
            self.file_path_entry.setText(output_audio_path)
        except subprocess.CalledProcessError as e:
            self.log_output(f"Error extracting audio: {e}")
            QMessageBox.critical(self, "Errore Estrazione Audio", f"Si è verificato un errore durante l'estrazione dell'audio: {e}")

    def run_process(self):
        input_type = ""
        if self.radio_youtube.isChecked():
            input_type = "youtube"
        elif self.radio_audio.isChecked():
            input_type = "audio"
        elif self.radio_video.isChecked():
            input_type = "video"

        name = self.name_entry.text() or "audio.mp3"
        
        model = self.model_combo.currentText()
        if model == "Custom":
            model = self.custom_model_entry.text()
            if not model:
                QMessageBox.warning(self, "Dati mancanti", "Per favore, inserisci un nome per il modello custom.")
                return
        
        format_id = ""
        if self.radio_format_auto.isChecked():
            format_id = "auto"
        else:
            format_id = self.manual_format_entry.text()
            if not format_id:
                QMessageBox.warning(self, "Dati mancanti", "Per favore, inserisci un ID formato manuale.")
                return

        file_path = self.file_path_entry.text()

        if not name:
            QMessageBox.warning(self, "Dati mancanti", "Per favore, compila il campo 'Nome del file'.")
            return
        
        if not file_path and input_type != "youtube":
            QMessageBox.warning(self, "Dati mancanti", "Per favore, seleziona un file o inserisci un link.")
            return
        
        if input_type == "youtube" and not file_path:
            QMessageBox.warning(self, "Dati mancanti", "Per favore, inserisci un link YouTube.")
            return

        # Disable start button to prevent multiple clicks
        self.start_button.setEnabled(False)

        # Start the download/file management process in a worker thread
        if input_type == "youtube":
            audio_manager = ManageYT.YTDLManager(file_path, "input", name, format_id)
            self.download_thread = WorkerThread(audio_manager.run)
            self.download_thread.log_signal.connect(self.log_output)
            # Connect to the new signal signature
            self.download_thread.process_finished_signal.connect(lambda success, error_msg: self.handle_download_completion(success, error_msg, model))
            self.log_output("Avvio download YouTube...")
            self.download_thread.start()
        else:
            # For local files, we directly proceed to docker process
            self.start_docker_process(model)

    def handle_download_completion(self, success, error_message, model):
        if success:
            self.log_output("Download completato.")
            self.start_docker_process(model)
        else:
            self.log_output(f"Download fallito: {error_message}")
            QMessageBox.critical(self, "Errore Download", f"Il download del video YouTube è fallito.\n{error_message}\nControllare il link o il formato.")
            self.start_button.setEnabled(True) # Re-enable button

    def start_docker_process(self, model):
        self.docker_thread = WorkerThread(self._docker_process_task, model)
        self.docker_thread.log_signal.connect(self.log_output)
        self.docker_thread.process_finished_signal.connect(self.on_docker_process_finished)
        self.docker_thread.start()

    def _docker_process_task(self, model):
        input_dir = "input"
        output_text_dir = "output_text"
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_text_dir, exist_ok=True)
        
        self.log_output("Riavvio del server Docker per liberare la VRAM...")
        reboot_script = "aux/FreeMemoryFromLLMs.sh"
        reboot = subprocess.Popen(reboot_script, shell=True)
        reboot.wait()
        self.log_output("Reboot completato.")

        docker_container_name = "rocm-terminal"
        docker_folder = "/home/rocm-user/whisper"
        whisper_docker = ManageDocker.Docker(docker_container_name)

        file_to_copy = None
        base_name_for_copy = self.name_entry.text()
        for f in os.listdir(input_dir):
            if f.startswith(base_name_for_copy):
                file_to_copy = f
                break
        
        if not file_to_copy:
            self.log_output(f"Error: Could not find file '{base_name_for_copy}' in '{input_dir}' to copy to Docker.")
            return 1 # Indicate error

        self.log_output(f"Copia del file audio '{file_to_copy}' nel container Docker...")
        whisper_docker.copy_to_container(input_dir, file_to_copy, f"{docker_folder}/samples")
        self.log_output(f"File audio '{file_to_copy}' copiato nel container Docker.")

        language = "ja"
        task = "translate"
        output_format = "srt"
        output_dir = f"{docker_folder}/output"
        file_path_in_docker = f"{docker_folder}/samples/{file_to_copy}"

        self.log_output("Avvio trascrizione e traduzione del file audio...")
        whispercheck = whisper_docker.run(model, language, task, output_format, output_dir, file_path_in_docker) 
        if whispercheck == 0:
            self.log_output("Trascrizione completata.")
        else:
            self.log_output(f"Errore durante l'esecuzione della trascrizione.\n {whispercheck}")
            return 1 # Indicate error

        output_file_name = f"{os.path.splitext(file_to_copy)[0]}.{output_format}"
        self.log_output(f"Copia del file trascritto da '{docker_folder}/output/{output_file_name}' a '{output_text_dir}'...")
        whisper_docker.copy_from_container(f"{docker_folder}/output/{output_file_name}", output_text_dir)
        self.log_output(f"File di trascrizione copiato su '{output_text_dir}'.")
        return 0 # Indicate success

    def on_docker_process_finished(self, result):
        self.start_button.setEnabled(True) # Re-enable button
        if result == 0:
            QMessageBox.information(self, "Completato", "Il processo è stato completato con successo!")
        else:
            QMessageBox.critical(self, "Errore", "C'è stato un problema durante l'esecuzione della trascrizione. Per maggiori informazioni al riguardo consultare la console di log.")



