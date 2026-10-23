from __future__ import annotations

from scenario.services.http_client import ResilientHttpClient

_WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
_WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


def extract_string_claim(claims: dict, prop: str) -> str | None:
    claim_list = claims.get(prop)
    if not claim_list:
        return None
    try:
        return claim_list[0]["mainsnak"]["datavalue"]["value"]
    except (KeyError, IndexError):
        return None


class WikidataResolver:
    """Resolves a name to its Wikipedia article and Wikidata entity, and
    caches both. Shared by biography lookup and image sourcing so a given
    person's QID (and its claims) are only fetched once per run, not once
    per concern.
    """

    def __init__(self) -> None:
        self._client = ResilientHttpClient()
        self._qid_cache: dict[str, str | None] = {}
        self._exact_cache: dict[str, str | None] = {}
        self._entity_cache: dict[str, dict] = {}

    def resolve_qid(self, name: str) -> str | None:
        """Exact article title (following redirects) first; free-text search
        only if no such article exists. Search ranks by popularity, which
        turns "House of Mortimer" into a surname page and "House of
        Mortimer, English noble family" into a comedian."""
        if name in self._qid_cache:
            return self._qid_cache[name]
        qid = self._resolve_exact(name)
        if not qid:
            title = self._resolve_title(name)
            qid = self._resolve_wikidata_id(title) if title else None
        self._qid_cache[name] = qid
        return qid

    def resolve_qid_any(self, *names: str | None, human: bool | None = None) -> str | None:
        """First entity any of the given spellings resolves to. Exact titles
        for every spelling are tried before any free-text search, so
        "Godwin, Earl of Wessex" (an article) beats a search for "Godwin";
        searches go shortest spelling first, since the qualifier in a long
        query ("House of Mortimer, English noble family") drags in namesakes.
        `human` = True/False rejects entities that are not / are a person."""
        spellings = [n for n in names if n]
        for name in spellings:
            qid = self._exact_cache.get(name)
            if qid is None and name not in self._exact_cache:
                qid = self._resolve_exact(name)
                self._exact_cache[name] = qid
            if qid and self._matches_kind(qid, human):
                self._qid_cache.setdefault(name, qid)
                return qid
        for name in sorted(spellings, key=len):
            qid = self.resolve_qid(name)
            if qid and self._matches_kind(qid, human):
                return qid
        return None

    def is_human(self, qid: str) -> bool:
        claims = self.get_entity(qid).get("claims", {})
        for claim in claims.get("P31", []):
            try:
                if claim["mainsnak"]["datavalue"]["value"]["id"] == "Q5":
                    return True
            except (KeyError, TypeError):
                continue
        return False

    def _matches_kind(self, qid: str, human: bool | None) -> bool:
        if human is None:
            return True
        return self.is_human(qid) == human

    def _resolve_exact(self, title: str) -> str | None:
        """QID of the article with exactly this title (redirects followed),
        or None if there is no such article or it is a disambiguation page."""
        data = self._client.get_json(
            _WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item|disambiguation",
                "titles": title,
                "redirects": 1,
                "format": "json",
            },
        )
        for page in data.get("query", {}).get("pages", {}).values():
            if "missing" in page:
                continue
            props = page.get("pageprops", {})
            if "disambiguation" in props:
                continue
            qid = props.get("wikibase_item")
            if qid:
                return qid
        return None

    def label(self, qid: str) -> str | None:
        """English label of an entity — the canonical name Commons files
        tend to be titled with ("William the Conqueror"), as opposed to
        whatever spelling the detector chose ("William I of England")."""
        try:
            return self.get_entity(qid)["labels"]["en"]["value"]
        except (KeyError, TypeError):
            return None

    def get_entity(self, qid: str) -> dict:
        entity = self._entity_cache.get(qid)
        if entity is None:
            data = self._client.get_json(_WIKIDATA_ENTITY_URL.format(qid=qid))
            entity = data["entities"][qid]
            self._entity_cache[qid] = entity
        return entity

    def _resolve_title(self, name: str) -> str | None:
        data = self._client.get_json(
            _WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "list": "search",
                "srsearch": name,
                "srlimit": 1,
                "format": "json",
            },
        )
        results = data.get("query", {}).get("search", [])
        return results[0]["title"] if results else None

    def _resolve_wikidata_id(self, title: str) -> str | None:
        data = self._client.get_json(
            _WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "prop": "pageprops",
                "titles": title,
                "format": "json",
            },
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
            if qid:
                return qid
        return None
