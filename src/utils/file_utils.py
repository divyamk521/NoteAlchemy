
import tempfile
import uuid
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

from config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3", ".mp4", ".mpeg", ".mpga",
    ".m4a", ".wav", ".webm", ".ogg", ".flac",
}

class FileSizeError(ValueError):
    """Raised when an uploaded file exceeds the configured size limit."""

class UnsupportedFormatError(ValueError):
    """Raised when a file extension is not in the supported audio formats."""

def validate_audio_file(filename: str, size_bytes: int) -> None:
    
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported format '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
        )
    if size_bytes > settings.max_file_size_bytes:
        size_mb = size_bytes / (1024 * 1024)
        raise FileSizeError(
            f"File is {size_mb:.1f} MB — exceeds the {settings.max_file_size_mb} MB limit."
        )
    
@contextmanager
def temp_audio_file(
    data: bytes,
    filename: str,
    suffix: Optional[str] = None,
) -> Generator[Path, None, None]:
    """Write *data* to a private temp file and yield its path.

    The name is unique per call. Streamlit serves every concurrent
    session from a single process, so a name derived only from the PID
    would collide across users: two simultaneous uploads would share one
    path, and whichever finished first would delete the file the other
    was still reading.
    """
    ext = suffix or Path(filename).suffix or ".mp3"
    tmp_dir = Path(tempfile.gettempdir()) / "notealchemy"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # uuid4 per call — never reuse a name across sessions or threads
    tmp_path = tmp_dir / f"upload_{uuid.uuid4().hex}{ext}"
    try:
        tmp_path.write_bytes(data)
        logger.debug(f"Temp audio written: {tmp_path} ({len(data)/1024:.1f} kB)")
        yield tmp_path #we get file path bcz transcription apis want filepath not bytes
    finally:
        if tmp_path.exists():
            tmp_path.unlink()#delete the temporary file after use
            logger.debug(f"Temp audio removed: {tmp_path}")

#creates a directory if missing
def ensure_dir(path: Path) -> Path:
    """Create *path* (and parents) if it doesn't exist; return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path

#just making sure the filename is safe or else i ll convert that to _
def safe_stem(filename: str) -> str:
    stem = Path(filename).stem
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return safe or "audio"
