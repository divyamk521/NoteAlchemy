from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from groq import Groq

from config.settings import get_settings
from src.utils.logger import get_logger
from src.utils.retry import groq_retry
from src.utils.file_utils import validate_audio_file, temp_audio_file

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TranscriptionResult:
    """Value object holding a completed transcription."""

    text: str
    filename: str
    duration_seconds: float
    model: str = field(default_factory=lambda: settings.whisper_model)
    word_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.word_count = len(self.text.split())

    def __repr__(self) -> str:
        return (
            f"<TranscriptionResult filename={self.filename!r} "
            f"words={self.word_count} duration={self.duration_seconds:.1f}s>"
        )
    
class WhisperClient:
    """
    Thin wrapper around the Groq audio transcription endpoint.

    """

    def __init__(self, client: Groq) -> None:
        self._client = client
#this is for the file or link uploads from streamlit 
    def transcribe_upload(
        self,
        file_bytes: bytes,
        filename: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from an in-memory upload i.e streamlit.
        streamlit->bytes->temp file->whisper transcription bcz groq compatible
        Returns
        -------
        TranscriptionResult
        """
        validate_audio_file(filename, len(file_bytes))
        logger.info(f"Transcribing upload: {filename} ({len(file_bytes)/1024:.1f} kB)")

        with temp_audio_file(file_bytes, filename) as tmp_path:
            return self._run_transcription(tmp_path, filename, language)

    def transcribe_file(
        self,
        path: Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio from a file already on disk (e.g. downloaded via yt-dlp).
        takes path->whisper transcription bcz groq compatible

        Returns
        -------
        TranscriptionResult
        """
        size = path.stat().st_size
        validate_audio_file(path.name, size)
        logger.info(f"Transcribing file: {path} ({size/1024:.1f} kB)")
        return self._run_transcription(path, path.name, language)

  

    @groq_retry
    def _run_transcription(
        self,
        path: Path,
        display_name: str,
        language: Optional[str],
    ) -> TranscriptionResult:
        t0 = time.perf_counter()#timer starts
        kwargs: dict = {
            "model": settings.whisper_model,
            "response_format": "text",
        }
        if language:
            kwargs["language"] = language

        with open(path, "rb") as fh:
            raw: str = self._client.audio.transcriptions.create(
                file=(display_name, fh),
                **kwargs,
            )

        elapsed = time.perf_counter() - t0#timer ends
        logger.success(
            f"Transcription done in {elapsed:.1f}s — "
            f"{len(raw.split())} words"
        )
        return TranscriptionResult(
            text=raw.strip(),
            filename=display_name,
            duration_seconds=elapsed,
        )
