import subprocess
import json
import sys

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
        # Usa startupinfo su Windows per nascondere la finestra della console
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
        
        # Se non trovata, cerca nel primo stream (utile per alcuni formati)
        if 'streams' in data and data['streams']:
            for stream in data['streams']:
                if 'duration' in stream:
                    return float(stream['duration'])

        # Se ancora non trovata, lancia un errore
        raise ValueError("Durata non trovata nell'output di ffprobe.")

    except FileNotFoundError:
        print("ERRORE: ffprobe non trovato. Assicurati che FFmpeg sia installato e nel PATH.", file=sys.stderr)
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        print(f"ERRORE durante il recupero della durata del file '{file_path}': {e}", file=sys.stderr)
        return None