from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QRadioButton, QCheckBox,
    QDialogButtonBox, QHBoxLayout, QButtonGroup
)
from PyQt6.QtCore import Qt

# Import corretti come da specifica
from utils.config_manager import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None, docker_available: bool = True, docker_status_message: str = ""):
        super().__init__(parent)
        self.config_manager = config_manager
        self.docker_available = docker_available
        self.docker_status_message = docker_status_message

        self.setWindowTitle("Impostazioni di Esecuzione")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Gruppo Modalità di Esecuzione
        exec_group = QGroupBox("Modalità di Esecuzione")
        exec_layout = QHBoxLayout(exec_group)
        self.execution_mode_group = QButtonGroup(self)
        self.radio_mode_docker = QRadioButton("Docker")
        self.radio_mode_native = QRadioButton("Nativo")
        self.execution_mode_group.addButton(self.radio_mode_docker)
        self.execution_mode_group.addButton(self.radio_mode_native)
        exec_layout.addWidget(self.radio_mode_docker)
        exec_layout.addWidget(self.radio_mode_native)
        exec_layout.addStretch()
        layout.addWidget(exec_group)

        # Disable Docker option if not available
        if not self.docker_available:
            self.radio_mode_docker.setEnabled(False)
            # If Docker was the selected mode but is now unavailable, switch to native
            if self.config_manager.get("execution_mode", "docker") == "docker":
                self.radio_mode_native.setChecked(True)
                self.config_manager.set("execution_mode", "native")
            # Add a tooltip to explain why it's disabled
            self.radio_mode_docker.setToolTip(f"Docker non disponibile: {self.docker_status_message}")
        
        # Gruppo Opzioni Avanzate
        advanced_group = QGroupBox("Opzioni Avanzate (Docker)")
        advanced_layout = QVBoxLayout(advanced_group)
        self.use_fast_whisper_checkbox = QCheckBox("Usa 'insanely-fast-whisper'")
        advanced_layout.addWidget(self.use_fast_whisper_checkbox)
        layout.addWidget(advanced_group)

        # Pulsanti OK e Annulla
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept) # accept() salverà le impostazioni
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.load_settings()

    def load_settings(self):
        mode = self.config_manager.get("execution_mode", "docker")
        if mode == "native":
            self.radio_mode_native.setChecked(True)
        else:
            self.radio_mode_docker.setChecked(True)
        
        self.use_fast_whisper_checkbox.setChecked(self.config_manager.get("use_insanely_fast_whisper", False))

    def accept(self):
        """Sovrascrive il metodo accept per salvare prima di chiudere."""
        self.config_manager.set("execution_mode", "native" if self.radio_mode_native.isChecked() else "docker")
        self.config_manager.set("use_insanely_fast_whisper", self.use_fast_whisper_checkbox.isChecked())
        super().accept()
