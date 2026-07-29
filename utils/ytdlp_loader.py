import logging

logger = logging.getLogger(__name__)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None
    logger.error("yt-dlp not found")
