from __future__ import annotations

from typing import Protocol

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from scenario.categories import CATEGORIES
from scenario.config import GoogleAISettings
from scenario.models import PersonalityMention, ScenarioParagraph
from scenario.services.gemini_retry import call_with_retry

_INSTRUCTION = """You are analyzing paragraphs from a historical narrative scenario.
For each paragraph, return every subject that clears the bar for one of the
categories below — not just the most central one. A paragraph can hold
several subjects, of the same or different categories.

Categories:
{categories}

For each subject return:
- paragraph_number: the paragraph's number, exactly as given.
- category: one of {category_ids}.
- name and query: as described under that category.

Rules:
- Skip a paragraph entirely if nothing in it qualifies (generic groups,
  unnamed roles, fictional or narrating characters do not count; neither
  does a name mentioned only in a one-line comparison with nothing else said
  about it).
- Never invent a name that is not grounded in the paragraph's own text.
- Omit any paragraph with no qualifying subject from the output entirely.

Paragraphs:
{paragraphs}
"""


class _Mention(BaseModel):
    paragraph_number: int = 0
    name: str = ""
    query: str = ""
    category: str = "people"


class _DetectionResponse(BaseModel):
    personalities: list[_Mention] = Field(default_factory=list)


class PersonalityDetectorService(Protocol):
    def detect(
        self, paragraphs: list[ScenarioParagraph], categories: list[str]
    ) -> list[PersonalityMention]: ...


class GeminiPersonalityDetectorService:
    def __init__(self, settings: GoogleAISettings) -> None:
        self._client = genai.Client(api_key=settings.api_key)
        self._model = settings.model

    def detect(
        self, paragraphs: list[ScenarioParagraph], categories: list[str]
    ) -> list[PersonalityMention]:
        body = "\n".join(f'PARAGRAPH {p.number}: "{p.text}"' for p in paragraphs)
        category_block = "\n\n".join(
            f"[{CATEGORIES[c].id}]\n{CATEGORIES[c].detect_rules}" for c in categories
        )

        response = call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=_INSTRUCTION.format(
                    paragraphs=body,
                    categories=category_block,
                    category_ids=", ".join(f'"{c}"' for c in categories),
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_DetectionResponse,
                ),
            )
        )
        parsed = _DetectionResponse.model_validate_json(response.text)

        return [
            PersonalityMention(
                paragraph_number=m.paragraph_number,
                name=m.name,
                query=m.query or m.name,
                category=m.category,
            )
            for m in parsed.personalities
            if m.name and m.paragraph_number and m.category in categories
        ]
