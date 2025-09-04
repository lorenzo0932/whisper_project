import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QPushButton, QTextEdit, QButtonGroup, QFileDialog, QMessageBox,
    QGroupBox, QComboBox, QProgressBar, QCheckBox, QToolButton, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

# Import corretti come da specifica
from utils.config_manager import ConfigManager
from services.processing_service import ProcessingService
from ui.settings_dialog import SettingsDialog

class MainWindow(QWidget):
    start_processing_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.is_process_active = False
        
        self.COMPACT_HEIGHT = 300
        self.PROGRESS_HEIGHT = 300
        self.LOG_HEIGHT = 580
        
        self.setup_processing_thread()
        self.init_ui()
        self.connect_signals()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Whisper GUI")
        self.setGeometry(100, 100, 800, self.COMPACT_HEIGHT)
        self.setMinimumSize(750, self.COMPACT_HEIGHT)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        source_group = QGroupBox("Input Sorgente")
        source_layout = QVBoxLayout(source_group)
        self.name_entry = QLineEdit(placeholderText="Nome file di output (es. audio_trascritto)")
        source_layout.addWidget(self.name_entry)
        input_type_layout = QHBoxLayout()
        self.input_type_group = QButtonGroup(self)
        self.radio_youtube = QRadioButton("YouTube"); self.radio_youtube.setChecked(True)
        self.radio_audio = QRadioButton("File Audio")
        self.radio_video = QRadioButton("File Video")
        for btn in [self.radio_youtube, self.radio_audio, self.radio_video]: self.input_type_group.addButton(btn); input_type_layout.addWidget(btn)
        input_type_layout.addStretch()
        source_layout.addLayout(input_type_layout)
        path_layout = QHBoxLayout()
        self.file_path_entry = QLineEdit(placeholderText="Incolla il link di YouTube o seleziona un file")
        self.browse_button = QPushButton(); self.browse_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_DirOpenIcon))
        path_layout.addWidget(self.file_path_entry); path_layout.addWidget(self.browse_button)
        source_layout.addLayout(path_layout)
        
        whisper_group = QGroupBox("Impostazioni Whisper")
        whisper_layout = QVBoxLayout(whisper_group)
        model_layout = QHBoxLayout(); model_layout.addWidget(QLabel("Modello:"))
        self.model_combo = QComboBox(); self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"]); self.model_combo.setCurrentText("medium")
        model_layout.addWidget(self.model_combo); whisper_layout.addLayout(model_layout)
        lang_layout = QHBoxLayout(); lang_layout.addWidget(QLabel("Lingua:"))
        self.language_combo = QComboBox(); self.language_combo.addItems(["auto", "en", "it", "es", "fr", "de", "ja", "zh", "ru"])
        lang_layout.addWidget(self.language_combo); whisper_layout.addLayout(lang_layout)
        task_layout = QHBoxLayout(); task_layout.addWidget(QLabel("Task:"))
        self.task_group = QButtonGroup(self); self.radio_task_transcribe = QRadioButton("Trascrivi"); self.radio_task_translate = QRadioButton("Traduci"); self.radio_task_transcribe.setChecked(True)
        for btn in [self.radio_task_transcribe, self.radio_task_translate]: self.task_group.addButton(btn); task_layout.addWidget(btn)
        task_layout.addStretch(); whisper_layout.addLayout(task_layout)

        top_layout.addWidget(source_group, 1)
        top_layout.addWidget(whisper_group, 1)
        main_layout.addLayout(top_layout)
        
        # --- MODIFICA: Spostata la progress bar per una migliore separazione visiva ---
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Lo spaziatore principale ora si trova qui, per spingere in basso il log e l'action bar
        main_layout.addStretch(1)
        
        self.log_container_widget = QWidget()
        output_group_layout = QVBoxLayout(self.log_container_widget)
        output_group_layout.setContentsMargins(0, 5, 0, 0); output_group_layout.setSpacing(5)
        self.output_text = QTextEdit(); self.output_text.setReadOnly(True)
        output_group_layout.addWidget(self.output_text)
        self.log_container_widget.setVisible(False)
        main_layout.addWidget(self.log_container_widget)
        main_layout.setStretchFactor(self.log_container_widget, 100)

        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        self.log_title_bar = QHBoxLayout()
        self.toggle_log_button = QToolButton(); self.toggle_log_button.setArrowType(Qt.ArrowType.RightArrow); self.toggle_log_button.setCheckable(True); self.toggle_log_button.setChecked(False)
        log_label = QLabel("Log di Output")
        self.log_title_bar.addWidget(self.toggle_log_button); self.log_title_bar.addWidget(log_label); self.log_title_bar.addStretch()
        bottom_layout.addLayout(self.log_title_bar)
        
        self.settings_button = QPushButton(); self.settings_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_FileDialogDetailedView)); self.settings_button.setIconSize(QSize(20, 20)); self.settings_button.setToolTip("Apri impostazioni di esecuzione")
        bottom_layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignRight)
        
        self.start_button = QPushButton(" Avvia Processo"); self.start_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_MediaPlay)); self.start_button.setObjectName("StartButton"); self.start_button.setMinimumHeight(35)
        bottom_layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(bottom_layout)

        self.apply_stylesheet()

    def apply_stylesheet(self):
        QApplication.setStyle("Fusion")
        self.setStyleSheet("""
            QWidget { font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
            QGroupBox {
                font-weight: bold; padding: 15px; margin-top: 10px;
                border: 1px solid #CDCDCD; border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 5px; margin-left: 10px;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #AAAAAA; border-radius: 5px;
                padding: 8px; background-color: palette(base); font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 2px solid palette(highlight); }
            QComboBox::drop-down { border: none; }
            QPushButton {
                background-color: palette(button); color: palette(button-text);
                border: 1px solid #AAAAAA; border-radius: 5px;
                padding: 8px 16px; font-size: 10pt;
            }
            QPushButton:hover { background-color: palette(light); }
            QPushButton#StartButton {
                font-weight: bold; font-size: 11pt;
                background-color: palette(highlight); color: palette(highlighted-text);
                border: 1px solid palette(highlight);
            }
            QPushButton#StartButton:hover { border: 2px solid palette(highlight); }
            QToolButton, QPushButton[icon] { border: none; background-color: transparent; }
            QProgressBar {
                border: 1px solid #AAAAAA;
                border-radius: 5px;
                text-align: center;
                color: palette(text);
                padding: 4px; /* MODIFICA: Aggiunge padding per renderla visivamente più alta */
                margin-top: 5px; /* Aggiunge un po' di spazio sopra */
            }
            QProgressBar::chunk {
                background-color: palette(highlight);
                border-radius: 4px;
            }
        """)

    def setup_processing_thread(self):
        self.processing_thread = QThread(); self.processing_service = ProcessingService(self.config_manager); self.processing_service.moveToThread(self.processing_thread)
        self.start_processing_signal.connect(self.processing_service.start_processing); self.processing_service.started_signal.connect(self.on_processing_started); self.processing_service.stage_changed_signal.connect(self.on_stage_changed); self.processing_service.log_signal.connect(self.log_output); self.processing_service.progress_signal.connect(self.update_progress_bar); self.processing_service.finished_signal.connect(self.on_processing_finished)
        self.processing_thread.start()

    def connect_signals(self):
        self.start_button.clicked.connect(self.run_process); self.settings_button.clicked.connect(self.open_settings_dialog); self.browse_button.clicked.connect(self.show_file_dialog); self.input_type_group.buttonClicked.connect(self.update_browse_button_state); self.toggle_log_button.clicked.connect(self.toggle_log_visibility); self.update_browse_button_state()

    def load_settings(self):
        self.model_combo.setCurrentText(self.config_manager.get("model", "medium")); self.language_combo.setCurrentText(self.config_manager.get("language", "auto")); task = self.config_manager.get("task", "transcribe");
        if task == "translate": self.radio_task_translate.setChecked(True)
        else: self.radio_task_transcribe.setChecked(True)

    def run_process(self):
        if self.radio_youtube.isChecked(): input_type = "youtube"
        elif self.radio_audio.isChecked(): input_type = "audio"
        else: input_type = "video"
        params = {"input_type": input_type, "name": self.name_entry.text() or "audio", "file_path": self.file_path_entry.text(), "model": self.model_combo.currentText(), "language": self.language_combo.currentText(), "task": "translate" if self.radio_task_translate.isChecked() else "transcribe", "output_format": "srt"}
        if not params["file_path"]: QMessageBox.warning(self, "Dati mancanti", "Per favore, inserisci un Path/Link."); return
        self.start_button.setEnabled(False); self.progress_bar.show()
        self._update_minimum_height()
        self.start_processing_signal.emit(params)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.config_manager, self); dialog.exec(); self.log_output("Impostazioni di esecuzione aggiornate.")

    def update_browse_button_state(self): self.browse_button.setEnabled(not self.radio_youtube.isChecked())

    def show_file_dialog(self):
        if self.radio_audio.isChecked(): file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio", "", "Audio Files (*.wav *.mp3 *.flac *.m4a *.webm)")
        elif self.radio_video.isChecked(): file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video Files (*.mp4 *.mkv *.avi *.mov)")
        else: return
        if file_path: self.file_path_entry.setText(file_path); self.log_output(f"File selezionato: {file_path}");
        if not self.name_entry.text(): base_name = os.path.splitext(os.path.basename(file_path))[0]; self.name_entry.setText(base_name)

    def toggle_log_visibility(self, checked):
        self.log_container_widget.setVisible(checked)
        self.toggle_log_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self._update_minimum_height()

    def on_processing_finished(self, success, message):
        self.is_process_active = False
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        self._update_minimum_height()
        
        # Only show message boxes for actual errors or successful completion, not for user-initiated stops
        if not success and "interrotto dall'utente" not in message:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore durante il processo.\n{message}")
        elif success and "interrotto dall'utente" not in message:
            QMessageBox.information(self, "Completato", f"Processo completato con successo.\n{message}")
        # If it was interrupted by the user, no message box is shown.

    def _update_minimum_height(self):
        target_height = 0
        if self.log_container_widget.isVisible():
            target_height = self.LOG_HEIGHT
        elif self.progress_bar.isVisible():
            target_height = self.PROGRESS_HEIGHT
        else:
            target_height = self.COMPACT_HEIGHT
        self.setMinimumHeight(target_height)
        if self.height() < target_height:
            self.resize(self.width(), target_height)

    def on_stage_changed(self, stage_text: str): self.progress_bar.setFormat(f"{stage_text} - %p%"); self.progress_bar.setValue(0)
    def on_processing_started(self): self.is_process_active = True; self.start_button.setEnabled(False)
    def update_progress_bar(self, value: int): self.progress_bar.setValue(value)
    def log_output(self, message: str): self.output_text.append(message); self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())
    def closeEvent(self, event):
        if self.is_process_active:
            reply = QMessageBox.question(self, 'Processo in Esecuzione', "Un processo è ancora attivo. Sei sicuro di voler chiudere?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.processing_service.stop() # Stop the processing service
                self.processing_thread.quit()
                self.processing_thread.wait(5000) # Give it a bit more time to clean up
                event.accept()
            else:
                event.ignore()
        else:
            self.processing_thread.quit()
            self.processing_thread.wait()
            event.accept()
