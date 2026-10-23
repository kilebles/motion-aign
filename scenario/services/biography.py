from __future__ import annotations

import logging
from typing import Protocol

from scenario.categories import CATEGORIES
from scenario.models import PersonalityInfo
from scenario.services.wikidata import WikidataResolver

logger = logging.getLogger(__name__)



class BiographyLookupService(Protocol):
    def lookup(
        self, name: str, query: str | None = None, category: str = "people"
    ) -> PersonalityInfo: ...


class WikipediaBiographyLookupService:
    """Reads dates from Wikidata's structured claims — more reliable than
    parsing years out of free-text summaries. Which claims depends on the
    category: birth/death for people, the event date or founding year for
    places, the inception for artifacts and families (see categories.py).
    """

    def __init__(self, resolver: WikidataResolver) -> None:
        self._resolver = resolver

    def lookup(
        self, name: str, query: str | None = None, category: str = "people"
    ) -> PersonalityInfo:
        qid = self._resolver.resolve_qid_any(query, name, human=(category == "people"))
        if not qid:
            logger.warning("Could not resolve a Wikidata item for %r", name)
            return PersonalityInfo(name=name, years=None)

        claims = self._resolver.get_entity(qid).get("claims", {})
        spec = CATEGORIES.get(category, CATEGORIES["people"])

        years: str | None = None
        for source in spec.date_props:
            if isinstance(source, tuple):
                start = self._extract_year(claims, source[0])
                end = self._extract_year(claims, source[1])
                years = f"{start} — {end}" if start and end else (start or end)
            else:
                years = self._extract_year(claims, source)
            if years:
                break
        return PersonalityInfo(name=name, years=years)

    @staticmethod
    def _extract_year(claims: dict, prop: str) -> str | None:
        """One year for a property that may hold several claims (a monastery
        founded in 960, refounded 1245, re-established 1540). A claim ranked
        "preferred" wins; otherwise the earliest date. Precision 9 is a year,
        8 a decade, 7 a century — century values are useless as captions and
        are skipped."""
        dated: list[tuple[int, str, str]] = []  # (year, rank, text)
        for claim in claims.get(prop, []):
            try:
                value = claim["mainsnak"]["datavalue"]["value"]
                time_value = value["time"]
            except (KeyError, TypeError):
                continue
            precision = value.get("precision", 9)
            if not time_value or precision < 8:
                continue
            sign, year = time_value[0], int(time_value[1:5])
            signed_year = -year if sign == "-" else year
            if precision == 8:
                year -= year % 10
                text = f"{year}s BCE" if sign == "-" else f"{year}s"
            else:
                text = f"{year} BCE" if sign == "-" else str(year)
            dated.append((signed_year, claim.get("rank", "normal"), text))
        if not dated:
            return None
        preferred = [d for d in dated if d[1] == "preferred"]
        return (preferred or sorted(dated))[0][2]
