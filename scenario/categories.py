from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    """Button label in the bot."""
    label: str
    """What the detector should pull out of a paragraph, and how to name it."""
    detect_rules: str
    """Noun used in prompts: "this person" / "this place" / "this artifact"."""
    subject_noun: str
    """What counts as a usable picture of it (image selection + relevance)."""
    image_rules: str
    """Wikidata date sources in order of preference: a property id gives a
    single year, a (start, end) pair gives a range. First one with a value wins."""
    date_props: tuple[str | tuple[str, str], ...]
    """Extra Commons free-text searches, formatted with {name} and {core}
    (the name without "House of" / "family" / "dynasty"). Free-text search
    for a family name alone returns buildings and streets; "X coat of arms"
    returns the heraldry."""
    extra_searches: tuple[str, ...] = ()


# Wikidata properties
_BIRTH, _DEATH = "P569", "P570"
_POINT_IN_TIME, _INCEPTION, _PUBLISHED = "P585", "P571", "P577"
_START, _END = "P580", "P582"

CATEGORIES: dict[str, Category] = {
    "people": Category(
        id="people",
        label="Люди",
        detect_rules="""Real, named historical figures the paragraph substantively
describes — their actions, appearance, or role is actually discussed, with
enough in the paragraph's own text to say something concrete about them, not
just their name dropped in passing or in a brief comparison.
name: the person's most search-friendly English name as used on Wikipedia
(e.g. "Lucius Aemilius Paullus"). query: that name plus a short
disambiguating role/era, comma-separated (e.g. "Lucius Aemilius Paullus,
Roman consul and general").""",
        subject_noun="this person",
        image_rules="""- It must genuinely be THIS specific person — verify the identity, don't
  just trust that the file was found under their name. Reject a different
  person who merely shares the name, or an unrelated object or place. Being
  modern is not itself a reason to reject: if they are a living or recent
  figure, a photograph of them is exactly right.
- Their face or figure must be the clear, prominent, easy-to-recognize
  subject of the image — not a small figure lost in a busy scene or crowd.
- Reject an image where TEXT is the actual content — a book cover, title
  page, manuscript/document page, or a diagram — even if the person is
  named or depicted somewhere in it. A small caption naming the sitter
  under a classical engraved portrait, bust, or painting does NOT
  disqualify it.""",
        date_props=((_BIRTH, _DEATH),),
    ),
    "places": Category(
        id="places",
        label="Битвы",
        detect_rules="""Named places and place-bound events the paragraph substantively
describes: battles and sieges (as events with a site), universities,
schools and monasteries as institutions, castles, cathedrals, palaces,
cities and landmark sites where the narrative's events happen. Skip generic
regions ("the north", "the coast"), unnamed places, whole countries,
civilizations ("Ancient Rome") and regions or cities that are only named as
a setting without anything concrete said about the place itself.
name: the English Wikipedia article title (e.g. "Battle of Hastings",
"University of Oxford", "Tower of London"). query: that title plus a short
qualifier (e.g. "Battle of Hastings, 1066 Norman conquest").""",
        subject_noun="this place or event",
        image_rules="""- It must genuinely show THIS place or event: a photograph of the site,
  building or landmark, an aerial view, a period painting, tapestry or
  engraving depicting the battle, or a historical map of the battle.
- Prefer a photograph or painting that reads at a glance over a map or
  plan; reject plain text pages, a coat of arms or seal of the place,
  unrelated buildings that share the name, and portraits of people merely
  associated with the place.""",
        # Wars and campaigns have a start/end; battles a point in time;
        # institutions and buildings an inception.
        date_props=((_START, _END), _POINT_IN_TIME, _INCEPTION),
    ),
    "artifacts": Category(
        id="artifacts",
        label="Гербы",
        detect_rules="""Named families, dynasties, noble houses and surnames; coats of arms;
specific books, manuscripts, charters, laws and treaties (e.g. Domesday
Book, Magna Carta); cultural monuments and artifacts such as tapestries,
crowns, regalia, relics, ships and named coins. Skip generic mentions
("a charter", "their arms") without a proper name.
name: the English Wikipedia article title (e.g. "House of Grosvenor",
"Domesday Book", "Bayeux Tapestry"). query: that title plus a short
qualifier (e.g. "Domesday Book, 1086 survey of England").""",
        subject_noun="this artifact, document or family",
        image_rules="""- It must genuinely show THIS subject: for a family, house or surname, its
  coat of arms or heraldic achievement; for a book, charter, law or treaty,
  a page, binding or facsimile of the document itself (text-heavy images
  are exactly right here); for a monument or artifact, the object itself.
- Reject unrelated same-named items, modern logos, and a portrait of a
  single family member unless nothing else depicts the family.""",
        date_props=(_PUBLISHED, _INCEPTION, _POINT_IN_TIME, (_START, _END)),
        extra_searches=("{core} coat of arms", "Arms of {core}"),
    ),
}

_FAMILY_WORDS = re.compile(r"^(?:house|dynasty|family) of\s+|\s+(?:family|dynasty|house)$", re.IGNORECASE)


def core_name(name: str) -> str:
    """"House of Percy" -> "Percy", "Despenser family" -> "Despenser"."""
    return _FAMILY_WORDS.sub("", name).strip() or name


DEFAULT_CATEGORIES = ("people",)
CATEGORY_IDS = tuple(CATEGORIES)


def parse_categories(raw: str | None) -> list[str]:
    """"people,places" -> ["people", "places"]; None/"" -> the default."""
    if not raw:
        return list(DEFAULT_CATEGORIES)
    ids = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [item for item in ids if item not in CATEGORIES]
    if unknown:
        raise ValueError(f"Unknown categories {unknown}; known: {', '.join(CATEGORY_IDS)}")
    return ids
