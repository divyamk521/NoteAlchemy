import sys
from loguru import logger as _logger
from config.settings import get_settings

def setup_logger() -> None:
    """Configure loguru with level from settings."""
    settings = get_settings()
    _logger.remove()
    _logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
        ),
        colorize=True,
    )
    _logger.add(
        "logs/notealchemy.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        serialize=False,
    )


def get_logger(name: str):
    """Return a loguru logger bound to *name*."""
    return _logger.bind(name=name)
