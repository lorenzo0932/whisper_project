# Usa whisper di openai per eseguire la trascrizione

import os
import subprocess
from classes import ManageDocker
from classes import ManageYT
import time

link = input("Inserire il link da usare con yt-dlp: ")
name = input("Inserire il nome del file che si vuole dare al file: ")
model = input ("Inserire la grandezza del modello da utilizzare (default: medium):")
#Formato di default che si cerca di scaricare (audio ad alta qualità)
format = input ("Inserire l'id del formato che si vuole scaricare (default: 251):")
format = format or "251"  # Imposta 251 solo se format corrisponde ad una stringa vuota
model = model or "medium" # Imposta medium solo se model corriponde alla stringa vuota

# Inizia il conteggio del tempo
start_time = time.time()

# Inserisco un commento divertente
print("Ecco un commento divertente: 'Ciao! Come possoi aiutarti oggi?'")

# Creo delle cartelle di preparazione per i file audio e testo
input = "input"
output_text = "output_text"
os.makedirs("output_text", exist_ok=True)

#Definisco tutte le informazioni riguardanti il container docker
docker_container_name= f"rocm-docker"
docker_folder= f"/home/rocm-user/whisper"

#Creo un oggetto per la gestione del download di audio
audio = ManageYT.YTDLManager(link, input, name, format)
audio.run()

# Imposto il path per lo script che libera la vram
reboot_ollama_docker = f"aux/FreeMemoryFromLLMs.sh"

# Avvio lo script per riavviare i docker usati per ollama
reboot = subprocess.Popen(reboot_ollama_docker, shell=True)
reboot.wait()
print("Dopo il reboot della vram, è possibile ripartire l'esecuzione del programma.\n")

#Creo un oggetto per la gestione dei docker
whisper_docker = ManageDocker.Docker(docker_container_name)

#Copio il file audio dentro il docker
whisper_docker.copy_to_container(input, name, f"{docker_folder}/samples")

# Imposto paramentri necessari all'esecuzione del modello Whisper
language = "ja"
task = "translate"
output_format = "srt"
output_dir = f"{docker_folder}/output"
file_path = f"{docker_folder}/samples/{name}.*"

#Eseguo la traduzione e trascrizione del file audio con whisper
whisper_docker.run(model, language, task, output_format, output_dir, file_path)

# Copio il file trascrizione dentro la cartella di destinazione
whisper_docker.copy_from_container(f"{docker_folder}/output/{name}.{output_format}", output_text)

#Finisce il conteggio del tempo
end_time = time.time()
print("Il processo è stato completato in {:.2f} secondi.".format(end_time - start_time))



