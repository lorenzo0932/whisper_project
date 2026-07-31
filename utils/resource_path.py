import os
import sys


def resource_path(relative_path: str) -> str:
    """Risolve un path verso le risorse dell'app.

    Funziona sia in esecuzione da sorgente (root del progetto) sia da
    bundle PyInstaller (onedir/onefile, dove sys._MEIPASS punta ai dati).
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)


def binary_name(name: str) -> str:
    """Aggiunge l'estensione .exe su Windows."""
    if sys.platform == "win32" and not name.lower().endswith(".exe"):
        return name + ".exe"
    return name
