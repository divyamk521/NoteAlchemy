from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import yt_dlp #youtube downloader library

from config.settings import get_settings
from src.utils.logger import get_logger
from src.utils.file_utils import ensure_dir

logger = get_logger(__name__)
settings = get_settings()

@dataclass
class DownloadResult:
    """Value object for a completed YouTube audio download."""

    path: Path
    title: str
    duration_seconds: int
    url: str

class YouTubeDownloader:
    """
    Downloads the audio track of a YouTube video as an M4A file.

    Uses yt-dlp's Python API so there is no subprocess / shell dependency.
    
    """

    def __init__(self) -> None:
        self._tmp_dir = Path(tempfile.gettempdir()) / "notealchemy" / "yt_downloads"
        ensure_dir(self._tmp_dir)

    

    @contextmanager
    def download(self, url: str) -> Generator[DownloadResult, None, None]:
       
       
        output_template = str(self._tmp_dir / "%(id)s.%(ext)s")
        info: dict = {}

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            # Store info so we can retrieve title / duration
            "postprocessors": [],
        }

        logger.info(f"Starting YouTube download: {url}")
        downloaded_path: Path | None = None

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                meta = ydl.extract_info(url, download=True)
                info = meta or {}
                video_id = info.get("id", "unknown")
                ext = info.get("ext", settings.ytdlp_audio_format)
                downloaded_path = self._tmp_dir / f"{video_id}.{ext}"

                logger.success(
                    f"Downloaded '{info.get('title', 'unknown')}' "
                    f"({info.get('duration', 0)}s) → {downloaded_path}"
                )

            result = DownloadResult(
                path=downloaded_path,
                title=info.get("title", "Unknown Title"),
                duration_seconds=int(info.get("duration", 0)),
                url=url,
            )
            yield result

        finally:
            if downloaded_path and downloaded_path.exists():
                downloaded_path.unlink()
                logger.debug(f"Removed downloaded audio: {downloaded_path}")

    
    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """Return True if *url* looks like a valid YouTube link."""
        return any(
            domain in url
            for domain in ("youtube.com/watch", "youtu.be/", "youtube.com/shorts/")
        )





