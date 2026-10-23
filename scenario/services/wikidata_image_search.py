from __future__ import annotations

import logging

from scenario.models import ImageCandidate
from scenario.services.http_client import ResilientHttpClient
from scenario.services.wikidata import WikidataResolver, extract_string_claim
from scenario.services.wikimedia import IMAGEINFO_PROPS, _search_subject, extract_candidates

logger = logging.getLogger(__name__)

_COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
_CATEGORY_LIMIT = 100

_MAIN_IMAGE_PROPERTY = "P18"
_COMMONS_CATEGORY_PROPERTY = "P373"


class WikidataImageSearchService:
    """Sources candidates from a person's Wikidata entity instead of
    free-text Commons search: P18 is the single image Wikipedia editors
    curated as *the* portrait for that person's infobox, and P373 is their
    dedicated Commons category — both far more precise than keyword search,
    which can't tell a genuine portrait from a same-named crater, species,
    or a passing appearance in someone else's photo.
    """

    def __init__(self, resolver: WikidataResolver) -> None:
        self._resolver = resolver
        self._client = ResilientHttpClient()

    def search(self, query: str, category: str = "people") -> list[ImageCandidate]:
        name = _search_subject(query)
        # Full query first: the role/era qualifier is what separates this
        # person from namesakes when the bare name is ambiguous.
        qid = self._resolver.resolve_qid_any(
            query if query != name else None, name, human=(category == "people")
        )
        if not qid:
            logger.info("No Wikidata entity for %r", name)
            return []

        claims = self._resolver.get_entity(qid).get("claims", {})
        candidates: list[ImageCandidate] = []
        seen_filenames: set[str] = set()

        main_image = extract_string_claim(claims, _MAIN_IMAGE_PROPERTY)
        if main_image:
            candidate = self._lookup_file(main_image)
            if candidate:
                candidates.append(candidate)
                seen_filenames.add(main_image)

        category = extract_string_claim(claims, _COMMONS_CATEGORY_PROPERTY)
        if category:
            candidates.extend(self._category_members(category, exclude=seen_filenames))

        if not candidates:
            logger.info("Wikidata entity for %r (qid=%s) has no usable image/category", name, qid)
        return candidates

    def _lookup_file(self, filename: str) -> ImageCandidate | None:
        data = self._client.get_json(
            _COMMONS_API_URL,
            params={
                "action": "query",
                "format": "json",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": IMAGEINFO_PROPS,
            },
        )
        candidates = extract_candidates(data.get("query", {}).get("pages", {}))
        return candidates[0] if candidates else None

    def _category_members(self, category: str, exclude: set[str]) -> list[ImageCandidate]:
        data = self._client.get_json(
            _COMMONS_API_URL,
            params={
                "action": "query",
                "format": "json",
                "generator": "categorymembers",
                "gcmtitle": f"Category:{category}",
                "gcmtype": "file",
                "gcmlimit": _CATEGORY_LIMIT,
                "prop": "imageinfo",
                "iiprop": IMAGEINFO_PROPS,
            },
        )
        candidates = extract_candidates(data.get("query", {}).get("pages", {}))
        return [c for c in candidates if c.title.removeprefix("File:") not in exclude]
