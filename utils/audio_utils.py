import subprocess
import json
import sys
import os

def _find_binary(name):
    if hasattr(sys, '_MEIPASS'):
        path = os.path.join(sys._MEIPASS, 'bin', name)
        if os.path.exists(path):
            return path
    return name

def get_audio_duration(file_path: str) -> float | None:
    """
    Ottiene la durata di un file audio/video in secondi usando ffprobe.

    Args:
        file_path: Il percorso del file multimediale.

    Returns:
        La durata in secondi come float, o None se si verifica un errore.
    """
    command = [
        _find_binary('ffprobe'),
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]

    try:
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
        
        if 'format' in data and 'duration' in data['format']:
            return float(data['format']['duration'])
        
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
    """
    command = [
        _find_binary('ffmpeg'),
        '-y',
        '-i', input_file,
        '-ar', '16000',
        '-ac', '1',
        '-c:a', 'pcm_s16le',
        output_file
    ]

    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

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