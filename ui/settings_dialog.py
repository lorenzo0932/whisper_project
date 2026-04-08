from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QDialogButtonBox, QLabel, QGroupBox, QRadioButton, QHBoxLayout
)
from PyQt6.QtCore import Qt

from utils.config_manager import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        self.setWindowTitle("Impostazioni di Esecuzione")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Riquadro informativo
        info_group = QGroupBox("Motore di Trascrizione")
        info_layout = QVBoxLayout(info_group)
        
        info_label = QLabel(
            "Il software ora esegue la trascrizione interamente "
            "in modalità nativa tramite <b>whisper.cpp</b>.\n\n"
            "• I modelli mancanti verranno scaricati in automatico."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)

        # Riquadro Accelerazione Hardware
        hw_group = QGroupBox("Accelerazione Hardware")
        hw_layout = QHBoxLayout(hw_group)
        
        self.radio_gpu = QRadioButton("GPU (Vulkan / Predefinita)")
        self.radio_cpu = QRadioButton("Solo CPU")
        
        # Carica la scelta attuale (default è GPU)
        if self.config_manager.get("device_mode", "gpu") == "cpu":
            self.radio_cpu.setChecked(True)
        else:
            self.radio_gpu.setChecked(True)
            
        hw_layout.addWidget(self.radio_gpu)
        hw_layout.addWidget(self.radio_cpu)
        hw_layout.addStretch()
        layout.addWidget(hw_group)

        # Pulsanti OK e Annulla
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        # Salva la scelta al click su "OK"
        mode = "cpu" if self.radio_cpu.isChecked() else "gpu"
        self.config_manager.set("device_mode", mode)
        super().accept()