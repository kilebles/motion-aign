from __future__ import annotations

from pathlib import Path
from typing import Protocol

from google import genai
from google.genai import types
from pydantic import BaseModel

from scenario.categories import CATEGORIES
from scenario.config import GoogleAISettings
from scenario.models import ImageCandidate
from scenario.services.gemini_retry import call_with_retry

_INSTRUCTION = """You are choosing the single best image to represent {name} —
{subject_noun} from history — for a historical documentary/infographic video.

Below are {count} candidate images, numbered 0 to {last}. Pick the ONE that
best shows {name}:
{image_rules}
- Among candidates that clear all of the above, prefer the more visually
  appealing and informative one: sharp, well-preserved, well-composed over
  blurry, damaged, heavily cropped, or low quality. All else equal, a
  cleaner presentation (tighter crop, less surrounding clutter) wins.
- If NONE of the candidates clear the bar, say so instead of picking the
  least-bad option.
{context}"""

_CONTEXT = """
The script paragraph this image will illustrate is quoted below. Use it to
pin down WHICH {name} is meant — the era, role and setting — and reject
any candidate that shows a different subject of the same name (e.g. a modern
namesake when the paragraph is about a medieval one):
\"\"\"{paragraph}\"\"\"
"""


def _guess_mime_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "image/jpeg"


class _Selection(BaseModel):
    best_index: int | None = None


class ImageSelectionService(Protocol):
    def pick_best(
        self,
        name: str,
        candidates: list[tuple[ImageCandidate, Path]],
        context: str | None = None,
        category: str = "people",
    ) -> ImageCandidate | None: ...


class GeminiImageSelectionService:
    """Compares a small batch of already-downloaded candidates in one call
    and picks the single best one — not just "does this show the person"
    but "which of these shows them most clearly and attractively" — instead
    of settling for whichever candidate happened to be tried first.
    """

    def __init__(self, settings: GoogleAISettings) -> None:
        self._client = genai.Client(api_key=settings.api_key)
        self._model = settings.model

    def pick_best(
        self,
        name: str,
        candidates: list[tuple[ImageCandidate, Path]],
        context: str | None = None,
        category: str = "people",
    ) -> ImageCandidate | None:
        if not candidates:
            return None

        spec = CATEGORIES.get(category, CATEGORIES["people"])
        context_block = _CONTEXT.format(name=name, paragraph=context) if context else ""
        contents: list[object] = [
            _INSTRUCTION.format(
                name=name,
                subject_noun=spec.subject_noun,
                image_rules=spec.image_rules,
                count=len(candidates),
                last=len(candidates) - 1,
                context=context_block,
            )
        ]
        for index, (_, path) in enumerate(candidates):
            data = path.read_bytes()
            contents.append(f"Image {index}:")
            contents.append(types.Part.from_bytes(data=data, mime_type=_guess_mime_type(data)))

        response = call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    # Picking the best portrait is a judgment call, not
                    # creative generation — keep it deterministic across
                    # identical calls.
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=_Selection,
                ),
            )
        )
        parsed = _Selection.model_validate_json(response.text)
        if parsed.best_index is None or not (0 <= parsed.best_index < len(candidates)):
            return None
        return candidates[parsed.best_index][0]
