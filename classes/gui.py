import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
from classes import ManageYT
from classes import ManageDocker
import os
import threading
import queue

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader e Whisper")


        # Nome del file per audio e video
        tk.Label(root, text="Inserire il nome del file:").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(root, width=50)
        self.name_entry.grid(row=0, column=1, pady=5)
        
        # Modello
        tk.Label(root, text="Grandezza del modello (default: medium):").grid(row=1, column=0, sticky="w")
        self.model_entry = tk.Entry(root, width=50)
        self.model_entry.insert(0, "medium")
        self.model_entry.grid(row=1, column=1, pady=5)
                
        # Radio buttons per la selezione del tipo di input
        tk.Label(root, text="Seleziona il tipo di input:").grid(row=2, column=0, sticky="w")
        self.input_type = tk.StringVar(value="youtube")
        self.radio_youtube = tk.Radiobutton(root, text="YouTube link", variable=self.input_type, value="youtube")
        self.radio_audio = tk.Radiobutton(root, text="Audio file", variable=self.input_type, value="audio")
        self.radio_video = tk.Radiobutton(root, text="Video file", variable=self.input_type, value="video")
        self.radio_youtube.grid(row=2, column=1, padx=10, sticky="w")
        self.radio_audio.grid(row=2, column=1, sticky="n")
        self.radio_video.grid(row=2, column=1, padx=10, sticky="e")
        
        # Campo per mostrare il path del file selezionato
        tk.Label(root, text="Path del file selezionato:").grid(row=3, column=0, sticky="w")
        self.file_path_var = tk.StringVar()
        self.file_path_entry = tk.Entry(root, width=37, textvariable=self.file_path_var)
        self.file_path_entry.insert(0, "path/to/file" or "youtube link", )
        self.file_path_entry.grid(row=3, column=1, pady=5, sticky="w", padx= 10)
        
        # Bottone per navigare nel filesystem in caso di file audio o video
        self.browse_button = tk.Button(root, text="Sfoglia", command=self.show_file_dialog)
        self.browse_button.grid(row=3, column=1, columnspan=2, pady=5, padx=10, sticky="e") 

        # Formato
        tk.Label(root, text="ID formato YTDL da scaricare (default: 251):").grid(row=4, column=0, sticky="w")
        self.format_entry = tk.Entry(root, width=50)
        self.format_entry.insert(0, "251")
        self.format_entry.grid(row=4, column=1, pady=5, padx=10)

        # Bottone per iniziare il download e la trascrizione
        self.start_button = tk.Button(root, text="Avvia Download e Trascrizione", command=self.run_process)
        self.start_button.grid(row=8, column=0, columnspan=3,  pady=10, sticky="n")

        # Output
        self.output_text = tk.Text(root, height=10, width=80, state="disabled")
        self.output_text.grid(row=9, column=0, columnspan=3  ,pady=10, padx= 10, sticky="w")

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

    def show_file_dialog(self):
        """Mostra il file dialog per selezionare un file locale."""
        if self.input_type.get() in "youtube":
            messagebox.showwarning("Opzione 'Sfoglia' non disponibile con YTDL", "Per favore seleziona 'Audio file' o 'Video file' per usare questa opzione.")
            return

        if self.input_type.get() in "video":
            file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
            self.extract_audio_from_video(file_path)
            
        if self.input_type.get() in "audio":
            file_path = filedialog.askopenfilename(filetypes=[("Audio files", "*.wav *.mp3 *.flac *webM")])



    def convert_audio(input_path, output_path):
        """Converti l'audio in un formato specifico."""
        command = f"ffmpeg -i {input_path} -ar 16000 -ac 1 -c:a pcm_s16le  {output_path}"
        subprocess.run(command, shell=True)


    def extract_audio_from_video(self, video_path):
        """Estrae l'audio da un video."""
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        base_name = base_name+"_audio"
        if self.name_entry.get():
            base_name = self.name_entry.get()
        
        output_audio_path = f"{os.path.dirname(video_path)}/input/{base_name}.wav"

        # Aggiungi una stampa di debug per verificare il path del file audio
        print(f"Extracting audio to: {output_audio_path}")

        # Estrai l'audio dal video
        command = f"ffmpeg -i {video_path} -vn -map 0:a:0 -c copy {output_audio_path} -y"
        subprocess.run(command, shell=True)

        # # Converti il file estratto in MP3 (o qualsiasi altro formato desiderato)
        # self.convert_audio("{output_audio_path}.wav", "{output_audio_path}.wav")

        self.file_path_var.set(output_audio_path)

        # Aggiungi una stampa di debug per verificare se il file audio è stato creato
        if os.path.exists(output_audio_path):
            print(f"Audio extracted successfully: output_audio_path")
        else:
            print("Failed to extract audio.")
            
    def run_process(self):
        # Ottieni i dati dall'interfaccia
        input_type = self.input_type.get()
        name = self.name_entry.get() or "audio.mp3"
        model = self.model_entry.get() or "medium"
        format = self.format_entry.get() or "251"

        # Verifica se i campi sono compilati
        if not name:
            messagebox.showwarning("Dati mancanti", "Per favore, compila tutti i campi richiesti.")
            return

        # Ottieni il path del file selezionato
        file_path = self.file_path_var.get()

        if input_type == "youtube":
            link = name  # Il nome del campo di input è utilizzato per il link YouTube
            audio_manager = ManageYT.YTDLManager(link, "", name, format)
            audio_manager.run()
        # else:
        #     link = ""
        #     if not file_path:
        #         messagebox.showwarning("Dati mancanti", "Per favore, seleziona un file o inserisci un link.")
        #         return

        #     audio_manager = ManageYT.LocalFileManager(file_path, name)

        # Crea un thread per eseguire il processo senza bloccare la GUI
        # thread = threading.Thread(target=self.process_download, args=(audio_manager, model))
        # thread.start()
        docker_thread = threading.Thread(target=self.docker_process, args=(model,))
        docker_thread.start()

    # def process_download(self, audio_manager, model):
    #     # Configura le directory
    #     input_dir = "input"
    #     output_text_dir = "output_text"
    #     os.makedirs(input_dir, exist_ok=True)
    #     os.makedirs(output_text_dir, exist_ok=True)

    #     # Inizializza la classe di download e avvia il processo
    #     audio_manager.run()
    #     self.log_output("Download completato.")

    def docker_process(self, model):
        # Configura le directory
        input_dir = "input"
        output_text_dir = "output_text"
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_text_dir, exist_ok=True)
        
        
        # Esegui il reboot del container (se necessario)
        reboot_script = "aux/FreeMemoryFromLLMs.sh"
        self.log_output("Riavvio del server Docker per liberare la VRAM...")
        reboot = subprocess.Popen(reboot_script, shell=True)
        reboot.wait()
        self.log_output("Reboot completato.")

        # Inizializza il container Docker e copia i file
        docker_container_name = "rocm-terminal"
        docker_folder = "/home/rocm-user/whisper"
        whisper_docker = ManageDocker.Docker(docker_container_name)

        # Copia il file audio nel container
        whisper_docker.copy_to_container(input_dir, self.name_entry.get(), f"{docker_folder}/samples")
        self.log_output(f"File audio '{self.name_entry.get()}' copiato nel container Docker.")

        # Imposta parametri di trascrizione
        language = "ja"
        task = "translate"
        output_format = "srt"
        output_dir = f"{docker_folder}/output"
        file_path = f"{docker_folder}/samples/{self.name_entry.get()}.*"

        # Esegui la trascrizione
        self.log_output("Avvio trascrizione e traduzione del file audio...")
        whisper_docker.run(model, language, task, output_format, output_dir, file_path)
        self.log_output("Trascrizione completata.")

        # Copia il file trascritto dal container al sistema host
        whisper_docker.copy_from_container(f"{docker_folder}/output/{self.name_entry.get()}.{output_format}", output_text_dir)
        self.log_output(f"File di trascrizione copiato su '{output_text_dir}'.")

        messagebox.showinfo("Completato", "Il processo è stato completato con successo!")