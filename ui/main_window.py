import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QPushButton, QTextEdit, QButtonGroup, QFileDialog, QMessageBox,
    QGroupBox, QComboBox, QProgressBar, QToolButton, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

from utils.config_manager import ConfigManager
from services.processing_service import ProcessingService
from ui.settings_dialog import SettingsDialog
from core.model_manager import get_categories, get_category, DEFAULT_CATEGORY, resolve_model_id

class MainWindow(QWidget):
    start_processing_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.is_process_active = False

        self.COMPACT_HEIGHT = 350
        self.PROGRESS_HEIGHT = 400
        self.LOG_HEIGHT = 580

        self.init_ui()
        self.setup_processing_thread()
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
        self.radio_youtube = QRadioButton("YouTube")
        self.radio_youtube.setChecked(True)
        self.radio_audio = QRadioButton("File Audio")
        self.radio_video = QRadioButton("File Video")
        
        for btn in[self.radio_youtube, self.radio_audio, self.radio_video]: 
            self.input_type_group.addButton(btn)
            input_type_layout.addWidget(btn)
            
        input_type_layout.addStretch()
        source_layout.addLayout(input_type_layout)
        
        source_layout.addWidget(QLabel("Link YouTube o Percorso File:"))
        path_layout = QHBoxLayout()
        self.file_path_entry = QLineEdit(placeholderText="Incolla il link di YouTube o seleziona un file")
        self.browse_button = QPushButton()
        self.browse_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_DirOpenIcon))
        path_layout.addWidget(self.file_path_entry)
        path_layout.addWidget(self.browse_button)
        source_layout.addLayout(path_layout)

        source_layout.addWidget(QLabel("Cartella di Output:"))
        output_dir_layout = QHBoxLayout()
        self.output_dir_entry = QLineEdit() 
        self.browse_output_dir_button = QPushButton()
        self.browse_output_dir_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_DirOpenIcon))
        output_dir_layout.addWidget(self.output_dir_entry)
        output_dir_layout.addWidget(self.browse_output_dir_button)
        source_layout.addLayout(output_dir_layout)
        
        whisper_group = QGroupBox("Impostazioni Whisper")
        whisper_layout = QVBoxLayout(whisper_group)

        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Categoria:"))
        self.category_combo = QComboBox()
        self.category_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.category_combo.setMinimumWidth(180)
        for cat in get_categories():
            self.category_combo.addItem(cat["label"], cat["id"])
        self._set_combo_dropdown_width(self.category_combo)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        cat_layout.addWidget(self.category_combo)
        whisper_layout.addLayout(cat_layout)

        self.model_group = QButtonGroup(self)
        self.model_radio_a = QRadioButton()
        self.model_radio_b = QRadioButton()
        self.model_group.addButton(self.model_radio_a, 0)
        self.model_group.addButton(self.model_radio_b, 1)
        self.model_radio_a.setChecked(True)
        whisper_layout.addWidget(self.model_radio_a)
        whisper_layout.addWidget(self.model_radio_b)

        self.model_info_label = QLabel()
        self.model_info_label.setStyleSheet("color: gray; font-size: 9pt;")
        whisper_layout.addWidget(self.model_info_label)

        self._on_category_changed(0)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Lingua:"))
        self.language_combo = QComboBox()
        self.language_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.language_combo.addItems(["auto", "en", "it", "es", "fr", "de", "ja", "zh", "ru"])
        self._set_combo_dropdown_width(self.language_combo)
        lang_layout.addWidget(self.language_combo)
        whisper_layout.addLayout(lang_layout)
        
        output_format_layout = QHBoxLayout()
        output_format_layout.addWidget(QLabel("Formato:"))
        self.output_format_combo = QComboBox()
        self.output_format_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.output_format_combo.addItems(["srt", "vtt", "txt", "tsv", "json", "all"])
        self._set_combo_dropdown_width(self.output_format_combo)
        self.output_format_combo.setCurrentText("srt") 
        output_format_layout.addWidget(self.output_format_combo)
        whisper_layout.addLayout(output_format_layout)

        task_layout = QHBoxLayout()
        task_layout.addWidget(QLabel("Task:"))
        self.task_group = QButtonGroup(self)
        self.radio_task_transcribe = QRadioButton("Trascrivi")
        self.radio_task_translate = QRadioButton("Traduci")
        self.radio_task_transcribe.setChecked(True)
        
        for btn in[self.radio_task_transcribe, self.radio_task_translate]: 
            self.task_group.addButton(btn)
            task_layout.addWidget(btn)
            
        task_layout.addStretch()
        whisper_layout.addLayout(task_layout)

        top_layout.addWidget(source_group, 1)
        top_layout.addWidget(whisper_group, 1)
        main_layout.addLayout(top_layout)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        main_layout.addStretch(1)
        
        self.log_container_widget = QWidget()
        output_group_layout = QVBoxLayout(self.log_container_widget)
        output_group_layout.setContentsMargins(0, 5, 0, 0)
        output_group_layout.setSpacing(5)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_group_layout.addWidget(self.output_text)
        self.log_container_widget.setVisible(False)
        main_layout.addWidget(self.log_container_widget)
        main_layout.setStretchFactor(self.log_container_widget, 100)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        self.log_title_bar = QHBoxLayout()
        self.toggle_log_button = QToolButton()
        self.toggle_log_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_log_button.setCheckable(True)
        self.toggle_log_button.setChecked(False)
        log_label = QLabel("Log di Output")
        self.log_title_bar.addWidget(self.toggle_log_button)
        self.log_title_bar.addWidget(log_label)
        self.log_title_bar.addStretch()
        bottom_layout.addLayout(self.log_title_bar)
        
        self.settings_button = QPushButton()
        self.settings_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_FileDialogDetailedView))
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setToolTip("Apri impostazioni")
        bottom_layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignRight)
        
        # PULSANTE STOP (Nuovo)
        self.stop_button = QPushButton(" Ferma")
        self.stop_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_MediaStop))
        self.stop_button.setObjectName("StopButton")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False) # Inizialmente disabilitato
        bottom_layout.addWidget(self.stop_button, 0, Qt.AlignmentFlag.AlignRight)

        # PULSANTE START
        self.start_button = QPushButton(" Avvia Processo")
        self.start_button.setIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_MediaPlay))
        self.start_button.setObjectName("StartButton")
        self.start_button.setMinimumHeight(35)
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
            QPushButton#StartButton:disabled { background-color: #cccccc; border: 1px solid #aaaaaa; }
            
            QPushButton#StopButton {
                font-weight: bold; font-size: 11pt;
                background-color: #d9534f; color: white; border: 1px solid #d43f3a;
            }
            QPushButton#StopButton:hover { background-color: #c9302c; border: 2px solid #c9302c; }
            QPushButton#StopButton:disabled { background-color: #f1b0b0; border: 1px solid #ebccd1; }

            QToolButton, QPushButton[icon] { border: none; background-color: transparent; }
            QProgressBar {
                border: 1px solid #AAAAAA; border-radius: 5px; text-align: center;
                color: palette(text); padding: 4px; margin-top: 5px;
            }
            QProgressBar::chunk { background-color: palette(highlight); border-radius: 4px; }
        """)

    def setup_processing_thread(self):
        self.processing_thread = QThread()
        self.processing_service = ProcessingService(self.config_manager)
        self.processing_service.moveToThread(self.processing_thread)
        
        self.start_processing_signal.connect(self.processing_service.start_processing)
        self.processing_service.started_signal.connect(self.on_processing_started)
        self.processing_service.stage_changed_signal.connect(self.on_stage_changed)
        self.processing_service.log_signal.connect(self.log_output)
        self.processing_service.progress_signal.connect(self.update_progress_bar)
        self.processing_service.finished_signal.connect(self.on_processing_finished)
        
        self.processing_thread.start()

    def connect_signals(self):
        self.start_button.clicked.connect(self.run_process)
        self.stop_button.clicked.connect(self.stop_process)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.browse_button.clicked.connect(self.show_file_dialog)
        self.browse_output_dir_button.clicked.connect(self.show_output_dir_dialog)
        self.input_type_group.buttonClicked.connect(self.update_browse_button_state)
        self.toggle_log_button.clicked.connect(self.toggle_log_visibility)
        self.model_group.buttonClicked.connect(self._update_model_info)
        self.update_browse_button_state()

    def load_settings(self):
        cat_id = self.config_manager.get("model_category", DEFAULT_CATEGORY)
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == cat_id:
                self.category_combo.setCurrentIndex(i)
                break
        model_index = self.config_manager.get("model_index", 0)
        rb = self.model_radio_a if model_index == 0 else self.model_radio_b
        rb.setChecked(True)
        self._update_model_info()

        self.language_combo.setCurrentText(self.config_manager.get("language", "auto"))
        self.output_format_combo.setCurrentText(self.config_manager.get("output_format", "srt"))

        task = self.config_manager.get("task", "transcribe")
        if task == "translate":
            self.radio_task_translate.setChecked(True)
        else:
            self.radio_task_transcribe.setChecked(True)

        default_output_dir = self.config_manager.get_default("output_dir")
        current_output_dir = self.config_manager.get("output_dir")

        self.output_dir_entry.setPlaceholderText(f"Default: {default_output_dir}")
        self.output_dir_entry.setText(current_output_dir if current_output_dir != default_output_dir else "")

    def run_process(self):
        if self.radio_youtube.isChecked():
            input_type = "youtube"
        elif self.radio_audio.isChecked():
            input_type = "audio"
        else:
            input_type = "video"

        cat_id = self.category_combo.currentData()
        model_index = self.model_group.checkedId()
        if model_index < 0:
            model_index = 0
        model_id = resolve_model_id(cat_id, model_index)

        self.config_manager.set("model_category", cat_id)
        self.config_manager.set("model_index", model_index)
        self.config_manager.set("output_format", self.output_format_combo.currentText())
        self.config_manager.set("output_dir", self.output_dir_entry.text())

        params = {
            "input_type": input_type,
            "name": self.name_entry.text() or "audio",
            "file_path": self.file_path_entry.text(),
            "model": model_id,
            "language": self.language_combo.currentText(),
            "task": "translate" if self.radio_task_translate.isChecked() else "transcribe",
            "output_format": self.output_format_combo.currentText(),
            "output_dir": self.output_dir_entry.text()
        }
        
        if not params["file_path"]:
            QMessageBox.warning(self, "Dati mancanti", "Per favore, inserisci un Path o Link.")
            return
        if not params["output_dir"]:
            QMessageBox.warning(self, "Dati mancanti", "Per favore, seleziona una cartella di output.")
            return
            
        self.progress_bar.show()
        self._update_minimum_height()
        self.start_processing_signal.emit(params)

    def stop_process(self):
        if self.is_process_active:
            reply = QMessageBox.question(
                self, 'Interrompi Esecuzione', 
                "Vuoi davvero interrompere? I file in corso di elaborazione verranno eliminati.", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_button.setEnabled(False)
                self.log_output("\n[!] Richiesta di interruzione... Attendere la pulizia del sistema.")
                self.processing_service.stop()

    def _set_combo_dropdown_width(self, combo):
        fm = combo.fontMetrics()
        max_w = max(fm.horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
        combo.view().setMinimumWidth(max_w + 30)

    def _on_category_changed(self, index):
        cat = get_categories()[index]
        m = cat["models"]
        self.model_radio_a.setText(m[0]["label"])
        self.model_radio_b.setText(m[1]["label"])
        self._update_model_info()

    def _update_model_info(self):
        cat_id = self.category_combo.currentData()
        cat = get_category(cat_id)
        idx = self.model_group.checkedId()
        if idx < 0:
            idx = 0
        model = cat["models"][idx]
        self.model_info_label.setText(
            f"ID: {model['id']}  |  Quantizzazione: {model['quant']}"
        )

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.config_manager, self)
        dialog.exec()
        self.load_settings() 

    def update_browse_button_state(self): 
        self.browse_button.setEnabled(not self.radio_youtube.isChecked())

    def show_file_dialog(self):
        if self.radio_audio.isChecked(): 
            file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Audio", "", "Audio Files (*.wav *.mp3 *.flac *.m4a *.webm)")
        elif self.radio_video.isChecked(): 
            file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona Video", "", "Video Files (*.mp4 *.mkv *.avi *.mov)")
        else: return
            
        if file_path: 
            self.file_path_entry.setText(file_path)
            self.log_output(f"File selezionato: {file_path}")
            if not self.name_entry.text(): 
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                self.name_entry.setText(base_name)

    def show_output_dir_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Seleziona Cartella di Output", self.output_dir_entry.text())
        if dir_path:
            self.output_dir_entry.setText(dir_path)
            self.log_output(f"Cartella di output selezionata: {dir_path}")

    def toggle_log_visibility(self, checked):
        self.log_container_widget.setVisible(checked)
        self.toggle_log_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self._update_minimum_height()

    def on_processing_started(self): 
        self.is_process_active = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def on_processing_finished(self, success, message):
        self.is_process_active = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.hide()
        self._update_minimum_height()
        
        if "interrotto" in message.lower():
            QMessageBox.information(self, "Annullato", message)
        elif not success:
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore:\n{message}")
        else:
            QMessageBox.information(self, "Completato", f"Processo completato con successo.\n{message}")

    def _update_minimum_height(self):
        target_height = self.LOG_HEIGHT if self.log_container_widget.isVisible() else (self.PROGRESS_HEIGHT if self.progress_bar.isVisible() else self.COMPACT_HEIGHT)
        self.setMinimumHeight(target_height)
        if self.height() < target_height: self.resize(self.width(), target_height)

    def on_stage_changed(self, stage_text: str): 
        self.progress_bar.setFormat(f"{stage_text} - %p%")
        self.progress_bar.setValue(0)
        
    def update_progress_bar(self, value: int): 
        self.progress_bar.setValue(value)
        
    def log_output(self, message: str): 
        self.output_text.append(message)
        self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.is_process_active:
            reply = QMessageBox.question(self, 'Uscita', "Elaborazione in corso. Vuoi davvero chiudere e annullare tutto?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.processing_service.stop() 
                self.processing_thread.quit()
                self.processing_thread.wait(3000) 
                event.accept()
            else:
                event.ignore()
        else:
            self.processing_thread.quit()
            self.processing_thread.wait()
            event.accept()