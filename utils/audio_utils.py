import subprocess
import json
import sys
import os

def get_audio_duration(file_path: str) -> float | None:
    """
    Ottiene la durata di un file audio/video in secondi usando ffprobe.

    Args:
        file_path: Il percorso del file multimediale.

    Returns:
        La durata in secondi come float, o None se si verifica un errore.
    """
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]

    try:
        # Nasconde la finestra della console su Windows
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            startupinfo=startupinfo
        )
        
        data = json.loads(result.stdout)
        
        # Cerca la durata nel formato del contenitore
        if 'format' in data and 'duration' in data['format']:
            return float(data['format']['duration'])
        
        # Se non trovata, cerca nei singoli stream
        if 'streams' in data and data['streams']:
            for stream in data['streams']:
                if 'duration' in stream:
                    return float(stream['duration'])

        return None

    except Exception as e:
        print(f"Errore ffprobe su '{file_path}': {e}", file=sys.stderr)
        return None

def convert_to_wav_16khz(input_file: str, output_file: str) -> bool:
    """
    Converte un file multimediale nel formato richiesto da whisper.cpp:
    WAV, 16kHz, 16-bit, Mono (PCM).
    
    Args:
        input_file: Percorso del file sorgente (mp4, webm, mp3, ecc.)
        output_file: Percorso del file WAV di destinazione.
        
    Returns:
        True se la conversione ha successo, False altrimenti.
    """
    command = [
        'ffmpeg',
        '-y',               # Sovrascrivi file esistente
        '-i', input_file,   # Input
        '-ar', '16000',     # Campionamento a 16kHz (Obbligatorio per whisper.cpp)
        '-ac', '1',         # Canale Mono (Obbligatorio per whisper.cpp)
        '-c:a', 'pcm_s16le',# Codec PCM 16-bit little endian
        output_file         # Output
    ]

    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Esegue la conversione catturando eventuali errori
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )

        if process.returncode == 0:
            return True
        else:
            print(f"Errore FFmpeg (Codice {process.returncode}): {process.stderr.decode('utf-8')}")
            return False

    except FileNotFoundError:
        print("Errore: FFmpeg non trovato nel sistema. Assicurati che sia installato.")
        return False
    except Exception as e:
        print(f"Errore durante la conversione audio: {e}")
        return False