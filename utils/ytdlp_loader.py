import os
import sys
import json
import logging
import tarfile
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

from utils.config_manager import ConfigManager

GITHUB_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
DOWNLOAD_BASE = "https://api.github.com/repos/yt-dlp/yt-dlp/tarball"

_cfg = ConfigManager()
YTDLP_CACHE = os.path.join(_cfg.cache_dir, "yt-dlp", "current")

_loaded = False

def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    if os.path.isdir(YTDLP_CACHE):
        sys.path.insert(0, YTDLP_CACHE)
    _loaded = True

def _get_local_version():
    _ensure_loaded()
    try:
        import yt_dlp.version
        return yt_dlp.version.__version__
    except ImportError:
        return None

def _get_remote_version():
    try:
        req = urllib.request.Request(GITHUB_API, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "WhisperGUI"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["tag_name"].lstrip("v")
    except Exception as e:
        logger.warning("Failed to check yt-dlp remote version: %s", e)
        return None

def check_for_update():
    current = _get_local_version()
    latest = _get_remote_version()
    if current is None or latest is None:
        return None
    if current != latest:
        return (current, latest)
    return None

def perform_update(version):
    url = f"{DOWNLOAD_BASE}/v{version}"
    dest_dir = os.path.dirname(YTDLP_CACHE)
    temp_dir = os.path.join(dest_dir, f".ytdlp-{version}")
    os.makedirs(temp_dir, exist_ok=True)

    tarball_path = os.path.join(temp_dir, f"yt-dlp-{version}.tar.gz")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WhisperGUI"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(tarball_path, "wb") as f:
                f.write(resp.read())

        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(tarball_path, "r:gz") as tar:
            top_dir = tar.getnames()[0].split("/")[0]
            tar.extractall(extract_dir)

        src = os.path.join(extract_dir, top_dir, "yt_dlp")
        dst = os.path.join(dest_dir, f"yt-dlp-{version}")
        if os.path.isdir(dst):
            import shutil
            shutil.rmtree(dst)
        os.rename(src, dst)

        current_link = YTDLP_CACHE
        if os.path.islink(current_link) or os.path.isdir(current_link):
            import shutil
            if os.path.islink(current_link) or os.path.isfile(current_link):
                os.remove(current_link)
            else:
                shutil.rmtree(current_link)
        os.symlink(dst, current_link)

        import shutil
        shutil.rmtree(temp_dir)
        return True
    except Exception as e:
        logger.error("Failed to update yt-dlp: %s", e)
        import shutil
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

_ensure_loaded()
try:
    import yt_dlp
except ImportError:
    yt_dlp = None
