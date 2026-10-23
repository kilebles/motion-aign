from __future__ import annotations

from typing import Protocol

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from scenario.categories import CATEGORIES
from scenario.config import GoogleAISettings
from scenario.models import ImageCandidate
from scenario.services.gemini_retry import call_with_retry
from scenario.services.wikimedia import WikimediaSearchService

_INSTRUCTION = """A search for "{query}" — {subject_noun} from history — on
Wikimedia Commons returned the file titles below. Some titles only match
because they share a word with the query by coincidence: the same word can
also name a species, a lunar crater, an unrelated place, or something else
entirely (e.g. a query for "Polybius" can pull in the moth species "Phocides
polybius"; a query for "Galen" can pull in the lunar crater "Galen").

For each numbered title, decide whether the file plausibly pictures the
subject itself, judged by these rules:
{image_rules}

Reject anything merely associated with the subject without picturing it,
and anything that happens to share the word. Return the numbers of the
titles that plausibly show the subject.

Titles:
{titles}
"""


class _RelevantIndices(BaseModel):
    relevant_indices: list[int] = Field(default_factory=list)


class ImageRelevanceService(Protocol):
    def filter_relevant(
        self, query: str, candidates: list[ImageCandidate], category: str = "people"
    ) -> list[ImageCandidate]: ...


class GeminiImageRelevanceService:
    def __init__(self, settings: GoogleAISettings) -> None:
        self._client = genai.Client(api_key=settings.api_key)
        self._model = settings.model

    def filter_relevant(
        self, query: str, candidates: list[ImageCandidate], category: str = "people"
    ) -> list[ImageCandidate]:
        if not candidates:
            return []

        spec = CATEGORIES.get(category, CATEGORIES["people"])
        titles = "\n".join(f"{i}: {c.title}" for i, c in enumerate(candidates))
        response = call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=_INSTRUCTION.format(
                    query=query,
                    subject_noun=spec.subject_noun,
                    image_rules=spec.image_rules,
                    titles=titles,
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_RelevantIndices,
                ),
            )
        )
        parsed = _RelevantIndices.model_validate_json(response.text)

        return [candidates[i] for i in parsed.relevant_indices if 0 <= i < len(candidates)]


class VerifiedWikimediaSearchService:
    """Wraps a WikimediaSearchService with an LLM relevance check. Keyword
    matching alone (see CommonsSearchService) lets same-word-different-subject
    results through for names that double as scientific/astronomical terms —
    this catches what the cheap filter can't.
    """

    def __init__(self, search: WikimediaSearchService, relevance: ImageRelevanceService) -> None:
        self._search = search
        self._relevance = relevance

    def search(self, query: str, category: str = "people") -> list[ImageCandidate]:
        candidates = self._search.search(query, category)
        return self._relevance.filter_relevant(query, candidates, category)
