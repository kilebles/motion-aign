from __future__ import annotations

from pathlib import Path
from typing import Protocol

from scenario.models import ImageCandidate
from scenario.services.http_client import ResilientHttpClient


class ImageDownloaderService(Protocol):
    def download(self, candidate: ImageCandidate, output_path: Path) -> None: ...


class HttpImageDownloaderService:
    def __init__(self) -> None:
        self._client = ResilientHttpClient()

    def download(self, candidate: ImageCandidate, output_path: Path) -> None:
        self._client.download(candidate.url, output_path)
