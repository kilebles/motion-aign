from __future__ import annotations

import logging
import re
from typing import Callable, Protocol

from scenario.categories import CATEGORIES, core_name
from scenario.models import ImageCandidate
from scenario.services.http_client import ResilientHttpClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://commons.wikimedia.org/w/api.php"
# Strict downstream filtering (relevance + "is the person clearly the
# subject") rejects a lot of raw results — a bigger pool means less chance
# of running out of fresh candidates and wrapping into repeats.
_SEARCH_LIMIT = 50
# SVG is included because Commons heraldry (coats of arms) is almost all
# SVG; it is fetched as a rasterised PNG thumbnail, never as the SVG itself.
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".svg")
_SVG_THUMB_WIDTH = 1280

# Wikimedia rejects hotlinked originals and non-standard thumbnail sizes
# (429 "use thumbnail images in sizes listed on https://w.wiki/GHai"), so
# every candidate URL is a pre-rendered thumbnail at one of these widths,
# strictly smaller than the original so the server never falls back to
# serving the original. Anything narrower than the smallest bucket is too
# small for a 1080p card anyway and is dropped.
# 1920 is deliberately left out: rendering it on demand for a huge original
# is what Commons throttles with 429, and 1280 is plenty for a 1080p card.
_THUMB_WIDTHS = (1280, 960, 500, 330, 250)
# imageinfo props every Commons query below must ask for.
IMAGEINFO_PROPS = "url|size"

# Descriptive tails like "X holding a sceptre" are cut before searching.
# "of" and "for" are deliberately NOT in this list: they are part of proper
# names ("House of Percy", "Battle of Hastings", "University of Oxford").
_TRAILING_CLAUSE = re.compile(
    r"\s+(?:with|depicting|showing|bearing|holding)\s+", re.IGNORECASE
)


def _core_phrase(subject: str) -> str:
    return _TRAILING_CLAUSE.split(subject, maxsplit=1)[0].strip()


def _search_subject(query: str) -> str:
    # Queries arrive as "<subject>, <era/role qualifier>" — full-text search
    # ranks far worse against the whole qualified string than against just
    # the subject.
    subject = query.split(",", 1)[0].strip()
    return _core_phrase(subject)


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") else word


# Words that say nothing about WHICH subject a title is about — regnal
# numbers, titles, places-as-qualifiers, connectives. "William I of England"
# must match "William the Conqueror.jpg" on "william", not on "england".
_GENERIC_WORDS = {
    "the", "of", "and", "de", "da", "von", "van", "la", "le", "du", "des",
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "king", "queen", "earl", "duke", "count", "lord", "lady", "sir", "saint", "st",
    "house", "family", "dynasty", "battle", "siege", "castle", "abbey", "university",
    "england", "english", "britain", "british", "france", "french", "normandy", "norman",
    "rome", "roman", "greek", "greece",
}


def _name_words(core: str) -> set[str]:
    """Distinctive words of a subject name: anything not in the generic list."""
    words = {w for w in re.findall(r"[a-zA-Z]+", core.lower()) if w not in _GENERIC_WORDS}
    return {_stem(w) for w in words} or {_stem(w) for w in re.findall(r"[a-zA-Z]+", core.lower())}


def _head_noun(core: str) -> str:
    """Kept for callers that want a single anchor word: the last distinctive word."""
    words = [w for w in re.findall(r"[a-zA-Z]+", core.lower()) if w not in _GENERIC_WORDS]
    return words[-1] if words else ""


def _candidate_words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-zA-Z]+", text.lower())}


def _is_relevant(name_words: set[str], words: set[str]) -> bool:
    # At least one distinctive word of the subject's name must appear in the
    # candidate title. Generic words (regnal numbers, "England", "House") are
    # excluded on both sides of the test, so they can neither anchor a match
    # nor produce a false positive on a shared era or civilization.
    return bool(name_words & words)


def _thumbnail_url(original_url: str, width: int) -> str | None:
    """Canonical pre-rendered thumbnail for a Commons original:
    .../commons/a/ab/File.jpg -> .../commons/thumb/a/ab/File.jpg/960px-File.jpg
    """
    base = original_url.split("?", 1)[0]
    marker = "/wikipedia/commons/"
    if marker not in base:
        return None
    prefix, rest = base.split(marker, 1)
    filename = rest.rsplit("/", 1)[-1]
    if filename.lower().endswith(".svg"):
        # Vector: any size can be rasterised, the nominal width is irrelevant.
        return f"{prefix}{marker}thumb/{rest}/{_SVG_THUMB_WIDTH}px-{filename}.png"
    thumb_width = next((w for w in _THUMB_WIDTHS if w < width), None)
    if thumb_width is None:
        return None
    return f"{prefix}{marker}thumb/{rest}/{thumb_width}px-{filename}"


def extract_candidates(pages: dict) -> list[ImageCandidate]:
    """Shared imageinfo-pages -> ImageCandidate parsing, used by any Commons
    API call shaped as action=query + prop=imageinfo (full-text search,
    category members, or a single File: lookup). Requires IMAGEINFO_PROPS."""
    candidates: list[ImageCandidate] = []
    for page in pages.values():
        title = page.get("title", "")
        if not title.lower().endswith(_IMAGE_EXTENSIONS):
            continue
        info = page.get("imageinfo")
        if not info:
            continue
        original = info[0].get("url")
        width = info[0].get("width") or 0
        if not original:
            continue
        url = _thumbnail_url(original, width)
        if url is None:
            logger.debug("Skipping %r: no standard thumbnail below %dpx", title, width)
            continue
        candidates.append(ImageCandidate(source_id=f"commons:{page['pageid']}", title=title, url=url))
    return candidates


class WikimediaSearchService(Protocol):
    def search(self, query: str, category: str = "people") -> list[ImageCandidate]: ...


class FallbackWikimediaSearchService:
    """Tries `primary` first, only calling `fallback` if it found nothing —
    e.g. a Wikidata-sourced search backed by free-text Commons search for
    the rare person with no Wikidata entity at all."""

    def __init__(self, primary: WikimediaSearchService, fallback: WikimediaSearchService) -> None:
        self._primary = primary
        self._fallback = fallback

    def search(self, query: str, category: str = "people") -> list[ImageCandidate]:
        candidates = self._primary.search(query, category)
        if candidates:
            return candidates
        logger.info("No primary-source candidates for %r, falling back to Commons search", query)
        return self._fallback.search(query, category)


class CombinedWikimediaSearchService:
    """Returns `primary` results first, then whatever `fallback` adds on top
    (deduplicated by source id). A person mentioned in twenty paragraphs
    needs twenty *different* pictures — the curated Wikidata portrait and
    category alone rarely hold that many, so free-text Commons search is
    appended as a second tier rather than used only when the first is empty.
    Curated candidates keep their place at the front, so early mentions still
    get the best portraits."""

    def __init__(
        self,
        primary: WikimediaSearchService,
        fallback: WikimediaSearchService,
        canonical_name: Callable[[str], str | None] | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        # Maps a query to the subject's canonical name (its Wikidata label),
        # searched in addition to the query when the two differ.
        self._canonical_name = canonical_name

    def search(self, query: str, category: str = "people") -> list[ImageCandidate]:
        candidates = list(self._primary.search(query, category))
        seen = {c.source_id for c in candidates}
        if not candidates:
            logger.info("No primary-source candidates for %r, using Commons search only", query)

        phrasings = [query]
        canonical = self._canonical_name(query) if self._canonical_name else None
        if canonical and canonical.lower() != _search_subject(query).lower():
            phrasings.append(canonical)

        for phrasing in phrasings:
            try:
                extra = self._fallback.search(phrasing, category)
            except Exception:
                logger.warning("Commons search failed for %r, skipping it", phrasing, exc_info=True)
                continue
            for candidate in extra:
                if candidate.source_id not in seen:
                    seen.add(candidate.source_id)
                    candidates.append(candidate)
        return candidates


class CommonsSearchService:
    def __init__(self) -> None:
        self._client = ResilientHttpClient()

    def search(self, query: str, category: str = "people") -> list[ImageCandidate]:
        subject = _search_subject(query)
        name_words = _name_words(subject)
        spec = CATEGORIES.get(category, CATEGORIES["people"])
        # Category-specific phrasings go first: they are the precise ones
        # ("Percy coat of arms"), the bare subject is the broad fallback and
        # its results land at the back of the pool.
        phrasings = [
            template.format(name=subject, core=core_name(subject)) for template in spec.extra_searches
        ] + [subject]

        candidates: list[ImageCandidate] = []
        seen: set[str] = set()
        for phrasing in phrasings:
            for candidate in self._search_once(phrasing):
                if candidate.source_id in seen:
                    continue
                if not _is_relevant(name_words, _candidate_words(candidate.title)):
                    continue
                seen.add(candidate.source_id)
                candidates.append(candidate)

        if not candidates:
            logger.warning("No relevant Commons results for %r (searched %r)", query, phrasings)
        return candidates

    def _search_once(self, text: str) -> list[ImageCandidate]:
        data = self._client.get_json(
            _SEARCH_URL,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": text,
                "gsrnamespace": 6,
                "gsrlimit": _SEARCH_LIMIT,
                "prop": "imageinfo",
                "iiprop": IMAGEINFO_PROPS,
            },
        )
        return extract_candidates(data.get("query", {}).get("pages", {}))


class PersonalityImagePool:
    """Searches Wikimedia once per personality and caches the full ordered
    candidate list. Which candidates have been used, offered or rejected is
    the pipeline's business (it has to be shared across every paragraph the
    person appears in) — the pool only guarantees one search per person.

    Pools are keyed by `key` (the personality's name), never by the search
    text: the detector re-words the query per paragraph ("X, King of England"
    vs "X, Duke of Normandy"), and keying on that would split one person
    across several lists.
    """

    def __init__(self, search: WikimediaSearchService) -> None:
        self._search = search
        self._pools: dict[str, list[ImageCandidate]] = {}

    def candidates(self, key: str, query: str, category: str = "people") -> list[ImageCandidate]:
        pool = self._pools.get(key)
        if pool is None:
            pool = self._search.search(query, category)
            self._pools[key] = pool
            logger.info("%d image candidates for %r", len(pool), key)
        return pool
