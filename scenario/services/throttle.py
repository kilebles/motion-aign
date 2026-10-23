from __future__ import annotations

import time


class Throttle:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._last_call_at = 0.0

    def wait(self) -> None:
        remaining = self._min_interval - (time.monotonic() - self._last_call_at)
        if remaining > 0:
            time.sleep(remaining)
        self._last_call_at = time.monotonic()
