from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
from config.settings import get_settings

settings = get_settings()


_log = logging.getLogger("notealchemy.retry")

def groq_retry(func=None):
    
    decorator = retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(
            multiplier=settings.retry_delay_seconds,
            min=settings.retry_delay_seconds,
            max=30,
        ),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(_log, logging.WARNING),
        reraise=True,
    )
    if func is not None:
        return decorator(func)
    return decorator
