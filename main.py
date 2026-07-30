import sys
import argparse
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow
from utils.config_manager import ConfigManager
from services.processing_service import ProcessingService

def run_cli(args, config):
    # Setup dei parametri CLI con i default della nostra app
    params = {
        "input_type": "youtube" if args.file.startswith(("http", "www")) else "audio",
        "name": args.name or "output_cli",
        "file_path": args.file,
        "model": args.model or config.get("model"),
        "language": args.language or config.get("language"),
        "task": args.task or config.get("task"),
        "output_format": args.format or config.get("output_format"),
        "output_dir": args.output_dir or config.get("output_dir")
    }

    # Per far funzionare i segnali di ProcessingService serve un'istanza di QCoreApplication
    # anche se non c'è una finestra (GUI)
    app = QCoreApplication(sys.argv)
    
    service = ProcessingService(config)
    
    # Colleghiamo i segnali alla console invece che alla GUI
    service.log_signal.connect(lambda msg: print(f"[LOG] {msg}"))
    service.progress_signal.connect(lambda val: print(f"[PROGRESS] {val}%", end='\r'))
    service.stage_changed_signal.connect(lambda stage: print(f"\n[FASE] {stage}"))
    
    def on_finished(success, message):
        print(f"\n[FINISH] Successo: {success} - {message}")
        sys.exit(0 if success else 1)

    service.finished_signal.connect(on_finished)
    
    print(f"--- Avvio modalità CLI (Device: {config.get('device_mode')}) ---")
    service.start_processing(params)
    return app.exec()

if __name__ == '__main__':
    config = ConfigManager()
    
    parser = argparse.ArgumentParser(description="WhisperGUI - Trascrizione Nativa")
    parser.add_argument("--cli", action="store_true", help="Avvia in modalità riga di comando")
    parser.add_argument("-f", "--file", type=str, help="Percorso file locale o link YouTube")
    parser.add_argument("-m", "--model", type=str, help="Modello (tiny, base, medium, large-v3...)")
    parser.add_argument("-l", "--language", type=str, help="Lingua (auto, it, en...)")
    parser.add_argument("-t", "--task", type=str, choices=['transcribe', 'translate'], help="Task")
    parser.add_argument("-o", "--output-dir", type=str, help="Cartella di output")
    parser.add_argument("-n", "--name", type=str, help="Nome file di output")
    parser.add_argument("-format", "--format", type=str, choices=['srt', 'vtt', 'txt', 'json'], help="Formato")

    args = parser.parse_args()

    if args.cli:
        if not args.file:
            print("Errore: In modalità CLI devi specificare un file con -f o --file")
            sys.exit(1)
        run_cli(args, config)
    else:
        # Modalità GUI standard
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon("icon/ai_studio_code.svg"))
        app.setDesktopFileName("whisper-gui")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())