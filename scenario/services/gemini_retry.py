from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 5.0


def call_with_retry(fn: Callable[[], T]) -> T:
    """Retries a Gemini API call a few times with a short delay. This
    session has seen intermittent `FAILED_PRECONDITION: User location is
    not supported for the API use` errors that clear up on retry — nothing
    about the request itself is wrong, so retrying is the right response
    rather than treating it as a permanent failure.
    """
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt + 1 < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS)
    assert last_error is not None
    raise last_error
