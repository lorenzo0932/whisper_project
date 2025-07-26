import sys
from PyQt6.QtWidgets import QApplication
from classes import gui_qt


# Crea la finestra principale e avvia la GUI
app = QApplication(sys.argv)
window = gui_qt.AppView()
window.show()
sys.exit(app.exec())
