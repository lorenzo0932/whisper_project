import subprocess
import json
import re
import sys
import os

_OUT_TIME_MS_RE = re.compile(r'out_time_ms=(\d+)')

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

def _format_filter_path(path):
    """Escape un path per l'uso nel filtro subtitles di ffmpeg."""
    p = path.replace('\\', '/')
    p = p.replace(':', '\\:')
    p = p.replace("'", "\\'")
    return p

def _run_ffmpeg(command, total_duration=None, progress_callback=None,
                is_cancelled_cb=None, process_registry=None):
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    full_command = command[:1] + ["-nostats", "-progress", "pipe:1"] + command[1:]

    process = subprocess.Popen(
        full_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        startupinfo=startupinfo
    )

    if process_registry is not None:
        process_registry.append(process)

    last_pct = -1

    def _emit(pct):
        nonlocal last_pct
        if pct != last_pct:
            last_pct = pct
            progress_callback(pct)

    try:
        for line in iter(process.stdout.readline, ''):
            if is_cancelled_cb and is_cancelled_cb():
                process.terminate()
                try:
                    process.wait(3)
                except Exception:
                    process.kill()
                return False
            if progress_callback and total_duration and total_duration > 0:
                match = _OUT_TIME_MS_RE.match(line.strip())
                if match:
                    pct = int((int(match.group(1)) / (total_duration * 1000)) * 100)
                    _emit(min(pct, 100))

        process.wait()

        if process.returncode == 0:
            if progress_callback:
                _emit(100)
            return True

        tail = process.stderr.read() or ""
        print(f"Errore FFmpeg (Codice {process.returncode}): {tail.strip()[-500:]}")
        return False
    finally:
        if process_registry is not None and process in process_registry:
            process_registry.remove(process)

def embed_subtitles(video_path, srt_path, output_path, language="ita",
                    progress_callback=None, is_cancelled_cb=None,
                    process_registry=None, total_duration=None) -> bool:
    """
    Muxa un file SRT come traccia soft nel video (nessun re-encode).
    MP4/MOV -> mov_text, MKV -> srt, WebM -> webvtt.
    """
    ext = os.path.splitext(output_path)[1].lower()
    if ext in (".mp4", ".mov", ".m4v"):
        sub_args = ["-c:s", "mov_text", "-metadata:s:s:0", f"language={language}",
                    "-movflags", "+faststart"]
    elif ext == ".webm":
        sub_args = ["-c:s", "webvtt"]
    else:
        sub_args = ["-c:s", "srt"]

    command = [
        _find_binary('ffmpeg'), '-y',
        '-i', video_path,
        '-i', srt_path,
        '-map', '0:v',
        '-map', '0:a?',
        '-map', '1:0',
        '-c', 'copy',
    ] + sub_args + [output_path]

    return _run_ffmpeg(
        command,
        total_duration=total_duration,
        progress_callback=progress_callback,
        is_cancelled_cb=is_cancelled_cb,
        process_registry=process_registry
    )

def burn_subtitles(video_path, srt_path, output_path, progress_callback=None,
                   is_cancelled_cb=None, process_registry=None,
                   total_duration=None, audio_codec="copy") -> bool:
    """
    Incide i sottotitoli nell'immagine del video (re-encode libx264).
    Se l'audio non è compatibile con MP4, ritenta con re-encode AAC.
    """
    filter_path = _format_filter_path(srt_path)
    command = [
        _find_binary('ffmpeg'), '-y',
        '-i', video_path,
        '-vf', f"subtitles=filename={filter_path}",
        '-c:v', 'libx264', '-crf', '20', '-preset', 'medium',
        '-c:a', audio_codec,
        output_path
    ]

    ok = _run_ffmpeg(
        command,
        total_duration=total_duration,
        progress_callback=progress_callback,
        is_cancelled_cb=is_cancelled_cb,
        process_registry=process_registry
    )

    if ok or audio_codec != "copy":
        return ok

    print("Audio non compatibile con MP4, ritento con re-encode AAC...")
    return burn_subtitles(
        video_path, srt_path, output_path,
        progress_callback=progress_callback,
        is_cancelled_cb=is_cancelled_cb,
        process_registry=process_registry,
        total_duration=total_duration,
        audio_codec="aac"
    )