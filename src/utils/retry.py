"""Retry policy for Groq API calls.

Only *transient* failures are retried. Retrying a permanent error (bad
API key, malformed request, unparseable model output) cannot succeed: it
just multiplies latency and burns quota. With N sections generated per
run, a blanket retry turns one systematic failure into 3xN doomed calls.
"""

import logging

from groq import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)

from config.settings import get_settings

settings = get_settings()

_log = logging.getLogger("notealchemy.retry")

#: Failures worth a second attempt. Everything else fails fast.
#:   RateLimitError      — 429, we are ahead of our quota
#:   APIConnectionError  — network dropped mid-flight
#:   APITimeoutError     — request exceeded the client deadline
#:   InternalServerError — 5xx on Groq's side
TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


def groq_retry(func=None):
    """Retry *func* on transient Groq errors with exponential back-off.

    Usable bare (``@groq_retry``) or called (``@groq_retry()``).
    """
    decorator = retry(
        stop=stop_after_attempt(settings.max_retries),
        # Jitter matters once sections run concurrently: without it a
        # shared 429 makes every worker retry on the same schedule.
        wait=wait_exponential_jitter(
            initial=settings.retry_delay_seconds,
            max=30,
            jitter=settings.retry_delay_seconds,
        ),
        retry=retry_if_exception_type(TRANSIENT_ERRORS),
        before_sleep=before_sleep_log(_log, logging.WARNING),
        reraise=True,
    )
    if func is not None:
        return decorator(func)
    return decorator
