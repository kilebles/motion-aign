from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx

from scenario.constants import USER_AGENT
from scenario.services.throttle import Throttle

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_DEFAULT_RETRY_AFTER = 10.0

# Every host in this family (Commons, Wikipedia, Wikidata) has been observed
# to escalate Retry-After well past what's practical to wait out (600s+
# under sustained load). Capping it means a stubborn 429 becomes a failure
# for the caller to handle gracefully, not a multi-minute stall.
_MAX_RETRY_AFTER = 20.0

# Never wait forever on a socket. Wikimedia's media host will happily accept
# the connection and then go silent under load — without a read timeout that
# hangs the whole run indefinitely and the retry loop below never even runs.
_JSON_TIMEOUT = httpx.Timeout(connect=15.0, read=30.0, write=15.0, pool=15.0)
_DOWNLOAD_TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)

# 4s was observed to still trigger escalating 429s under a full scenario's
# sustained request volume (many personalities x images + search + bio
# lookups in one session); 6s trades some run time for fewer rate-limit hits.
_MIN_REQUEST_INTERVAL = 6.0


class ResilientHttpClient:
    """Shared GET client for the Wikimedia/Wikipedia/Wikidata API family:
    one User-Agent, one throttle, one capped-retry-on-429 policy. Give each
    caller its own instance so unrelated hosts don't share throttle state.
    """

    def __init__(self, min_interval_seconds: float = _MIN_REQUEST_INTERVAL) -> None:
        self._throttle = Throttle(min_interval_seconds)

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict:
        for _ in range(_MAX_RETRIES):
            self._throttle.wait()
            try:
                response = httpx.get(
                    url, params=params, headers={"User-Agent": USER_AGENT}, timeout=_JSON_TIMEOUT
                )
            except (httpx.TimeoutException, httpx.ConnectError):
                # A dropped or stalled connection is usually transient — one
                # such blip shouldn't cost a subject its whole image search.
                logger.warning("Connection problem on %s, retrying", url)
                continue
            if response.status_code == 429:
                self._sleep_retry_after(response, url)
                continue
            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"GET {url} failed after {_MAX_RETRIES} attempts")

    def download(self, url: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        for _ in range(_MAX_RETRIES):
            self._throttle.wait()
            try:
                with httpx.stream(
                    "GET",
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=_DOWNLOAD_TIMEOUT,
                    follow_redirects=True,
                ) as response:
                    if response.status_code == 429:
                        self._sleep_retry_after(response, url)
                        continue
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    return
            except httpx.TimeoutException:
                # A stalled connection is usually transient — drop it and let
                # the loop open a fresh one rather than failing the candidate.
                logger.warning("Timed out downloading %s, retrying", url)
                continue

        raise RuntimeError(f"Download {url} failed after {_MAX_RETRIES} attempts (rate limited)")

    def _sleep_retry_after(self, response: httpx.Response, url: str) -> None:
        retry_after = self._parse_retry_after(response)
        logger.warning("Rate limited on %s, retrying in %.0fs", url, retry_after)
        time.sleep(retry_after)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float:
        value = response.headers.get("Retry-After")
        if not value:
            return _DEFAULT_RETRY_AFTER
        try:
            return min(float(value), _MAX_RETRY_AFTER)
        except ValueError:
            return _DEFAULT_RETRY_AFTER
