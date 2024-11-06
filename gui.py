import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import subprocess
import classes
import os
import threading
import queue

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader e Whisper")

        # Link input
        tk.Label(root, text="Inserire il link da usare con yt-dlp:").grid(row=0, column=0, sticky="w")
        self.link_entry = tk.Entry(root, width=50)
        self.link_entry.grid(row=0, column=1, pady=5)

        # Nome file
        tk.Label(root, text="Inserire il nome del file:").grid(row=1, column=0, sticky="w")
        self.name_entry = tk.Entry(root, width=50)
        self.name_entry.grid(row=1, column=1, pady=5)

        # Modello
        tk.Label(root, text="Grandezza del modello (default: medium):").grid(row=2, column=0, sticky="w")
        self.model_entry = tk.Entry(root, width=50)
        self.model_entry.insert(0, "medium")
        self.model_entry.grid(row=2, column=1, pady=5)

        # Formato
        tk.Label(root, text="ID formato da scaricare (default: 251):").grid(row=3, column=0, sticky="w")
        self.format_entry = tk.Entry(root, width=50)
        self.format_entry.insert(0, "251")
        self.format_entry.grid(row=3, column=1, pady=5)

        # Bottone per iniziare
        self.start_button = tk.Button(root, text="Avvia Download e Trascrizione", command=self.run_process)
        self.start_button.grid(row=4, column=0, columnspan=2, pady=10)

        # Output
        self.output_text = tk.Text(root, height=10, width=70, state="disabled")
        self.output_text.grid(row=5, column=0, columnspan=2, pady=10)

        # Coda per passare i messaggi dal thread di lavoro alla GUI
        self.log_queue = queue.Queue()

        # Aggiornamento della Text Box
        self.update_log()

    def log_output(self, message):
        """Invia messaggi alla coda per essere letti e visualizzati."""
        self.log_queue.put(message)

    def update_log(self):
        """Aggiorna la Text Box con i messaggi dalla coda."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.output_text.configure(state="normal")
                self.output_text.insert("end", message + "\n")
                self.output_text.configure(state="disabled")
                self.output_text.see("end")
        except queue.Empty:
            pass

        # Chiamata ricorsiva per aggiornare continuamente la GUI
        self.root.after(100, self.update_log)

    def run_process(self):
        # Ottieni i dati dall'interfaccia
        link = self.link_entry.get()
        name = self.name_entry.get()
        model = self.model_entry.get() or "medium"
        format = self.format_entry.get() or "251"

        # Verifica se i campi sono compilati
        if not link or not name:
            messagebox.showwarning("Dati mancanti", "Per favore, compila tutti i campi richiesti.")
            return

        # Crea un thread per eseguire il processo senza bloccare la GUI
        thread = threading.Thread(target=self.process_download, args=(link, name, model, format))
        thread.start()

    def process_download(self, link, name, model, format):
        # Configura le directory
        input_dir = "input"
        output_text_dir = "output_text"
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_text_dir, exist_ok=True)

        # Inizializza la classe di download e avvia il processo
        audio_manager = classes.YTDLManager(link, input_dir, name, format)
        audio_manager.run()
        self.log_output("Download completato.")

        # Esegui il reboot del container (se necessario)
        reboot_script = "aux/OllamaServer.sh"
        self.log_output("Riavvio del server Docker per liberare la VRAM...")
        reboot = subprocess.Popen(reboot_script, shell=True)
        reboot.wait()
        self.log_output("Reboot completato.")

        # Inizializza il container Docker e copia i file
        docker_container_name = "rocm-docker"
        docker_folder = "/home/rocm-user/whisper"
        whisper_docker = classes.Docker(docker_container_name)

        # Copia il file audio nel container
        whisper_docker.copy_to_container(input_dir, name, f"{docker_folder}/samples")
        self.log_output(f"File audio '{name}' copiato nel container Docker.")

        # Imposta parametri di trascrizione
        language = "ja"
        task = "translate"
        output_format = "srt"
        output_dir = f"{docker_folder}/output"
        file_path = f"{docker_folder}/samples/{name}.*"

        # Esegui la trascrizione
        self.log_output("Avvio trascrizione e traduzione del file audio...")
        whisper_docker.run(model, language, task, output_format, output_dir, file_path)
        self.log_output("Trascrizione completata.")

        # Copia il file trascritto dal container al sistema host
        whisper_docker.copy_from_container(f"{docker_folder}/output/{name}.{output_format}", output_text_dir)
        self.log_output(f"File di trascrizione copiato su '{output_text_dir}'.")

        messagebox.showinfo("Completato", "Il processo è stato completato con successo!")

# Crea la finestra principale e avvia la GUI
root = tk.Tk()
app = App(root)
root.mainloop()
