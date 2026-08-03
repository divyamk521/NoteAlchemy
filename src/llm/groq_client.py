from __future__ import annotations

from functools import lru_cache
from groq import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    Groq,
)

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


def verify_client(client: Groq) -> None:
    """Confirm the key actually works, raising GroqClientError if not.

    ``Groq(api_key=...)`` performs no I/O, so :func:`build_client` cannot
    detect a bad key — the `except AuthenticationError` there was
    unreachable. A wrong key therefore surfaced much later as a confusing
    mid-pipeline failure, after the user had already waited through
    transcription.

    ``models.list()`` is the cheapest authenticated call available, so we
    use it as a pre-flight probe. Callers should do this once per key and
    cache the result rather than probing on every run.
    """
    try:
        client.models.list()
    except AuthenticationError as exc:
        raise GroqClientError(
            "Groq rejected this API key. Check it at console.groq.com."
        ) from exc
    except (APIConnectionError, APITimeoutError) as exc:
        raise GroqClientError(
            f"Could not reach Groq to verify the key: {exc}"
        ) from exc
    except Exception as exc:
        raise GroqClientError(f"Could not verify Groq API key: {exc}") from exc
    logger.debug("Groq API key verified.")
