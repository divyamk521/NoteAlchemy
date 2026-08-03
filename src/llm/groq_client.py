from __future__ import annotations

from functools import lru_cache
from groq import Groq, AuthenticationError

from config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GroqClientError(RuntimeError):
    """Raised when the Groq client cannot be initialised."""

def build_client(api_key: str) -> Groq:
    
    if not api_key or not api_key.strip():
        raise GroqClientError(
            "Groq API key is empty. "
            "Set GROQ_API_KEY in .env or enter it in the sidebar."
        )
    try:
        client = Groq(api_key=api_key.strip())
        logger.debug("Groq client created successfully.")
        return client
    except AuthenticationError as exc:
        raise GroqClientError(f"Groq authentication failed: {exc}") from exc
    except Exception as exc:
        raise GroqClientError(f"Could not create Groq client: {exc}") from exc


@lru_cache(maxsize=8)
def get_cached_client(api_key: str) -> Groq:
    """
    Return a cached :class:`groq.Groq` client for *api_key*.

    Caches up to 8 distinct keys (sufficient for any real-world usage).
    """
    return build_client(api_key)
