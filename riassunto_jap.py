import sys
import os
import time
import subprocess
import classes


link = input("Inserire il link da usare con yt-dlp: ")
name = input("Inserire il nome del file che si vuole dare al file: ")
model = input ("Inserire la grandezza del modello da utilizzare (default: medium):")
#Formato di default che si cerca di scaricare (audio ad alta qualità)
format = input ("Inserire l'id del formato che si vuole scaricare (default: 251):")
format = format or "251"  # Imposta 251 solo se format corrisponde ad una stringa vuota
model = model or "medium" # Imposta medium solo se model corriponde alla stringa vuota


# Creo delle cartelle di preparazione per i file audio e testo
input = "input"
# output_audio = "output_ffmpeg"
output_text = "output_text"
# os.makedirs("output_ffmpeg", exist_ok=True)
os.makedirs("output_text", exist_ok=True)

# Verificare se il formato selezionato è disponibile
yt_dlp_verify = f'yt-dlp -F {link}'
result = subprocess.run(yt_dlp_verify.split(), capture_output=True, text=True)

if format not in result.stdout:
    print(f"Formato {format} non disponibile. Provare con un altro formato (ad esempio 234)")
    sys.exit(1)


#scarico usando yt-dlp e metto il file in una cartella di input
yt_dlp_download = f"yt-dlp -o '{input}/{name}.%(ext)s' --format {format} {link}"
download_audio = subprocess.Popen(yt_dlp_download, shell=True)
# Attendi fino a quando il processo non è terminato
download_audio.wait()

filename_wav= name + ".wav"
filename_txt = name + ".txt"
filename_srt = name +".srt"

#converto il file in ffmpeg usando python e lo salvo nella stessa directory dove si trova con il nome output.wav
# ffmpeg_conversion = f"ffmpeg -y -i {input}/{name_with_ext} -ar 16000 -ac 1 -c:a pcm_s16le output_ffmpeg/{filename_wav}"
# subprocess.run(ffmpeg_conversion, shell=True)


# Imposto il path per lo script che libera la vram
reboot_ollama_docker = 'aux/OllamaServer.sh'

# Avvio lo script per riavviare i docker usati per ollama
subprocess.run(reboot_ollama_docker, shell=True)
#os.system('bash ' + reboot_ollama_docker)

#Aspetto 2 secondi per assicurarmi che lo script sia stato eseguito
time.sleep(2)

#copio il file all'interno di un docker container usando python
# docker_copy = f"docker cp {output_audio}/{filename_wav} rocm-docker:/home/rocm-user/whisper/samples/{filename_wav}"
docker_copy = f"docker cp {input}/{name}* rocm-docker:/home/rocm-user/whisper/samples/{name}"
subprocess.run(docker_copy, shell = True)


#eseguo la trascrizione del file audio in un file di srt usando whisper
whisper = f'docker exec -it rocm-docker bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch &&  whisper --model {model}  --language ja --output_format srt --task translate  --output_dir output/ samples/{name}"'
subprocess.run(whisper, shell=True)

#eseguo la trascrizione del file audio in un file di txt usando whisper
# whisper = f'docker exec -it rocm-docker bash -c "source /home/rocm-user/.bashrc && cd /home/rocm-user/whisper && conda activate pytorch &&  whisper --model {model}  --language ja --output_format txt --task translate  --output_dir output/ samples/{filename_wav}"'
# subprocess.run(whisper, shell=True)

# #copio il file srt generato nella cartella di output
docker_copy2 = f"docker cp rocm-docker:/home/rocm-user/whisper/output/{filename_srt} {output_text}/{filename_srt}"
subprocess.run(docker_copy2, shell=True)


#copio il file txt generato nella cartella di output
# docker_copy2 = f"docker cp rocm-docker:/home/rocm-user/whisper/output/{filename_txt} {output_text}/{filename_txt}"
# subprocess.run(docker_copy2, shell=True)



    




# subprocess.run(docker_copy2, shell=True)
