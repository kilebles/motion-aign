from __future__ import annotations

from pydantic import BaseModel, Field


class ScenarioParagraph(BaseModel):
    number: int
    text: str


class PersonalityMention(BaseModel):
    paragraph_number: int
    name: str
    query: str
    category: str = "people"


class PersonalityInfo(BaseModel):
    name: str
    years: str | None = None


class ImageCandidate(BaseModel):
    source_id: str
    title: str
    url: str


class PersonalityImage(BaseModel):
    file: str
    source_id: str
    url: str


class PersonalityEntry(BaseModel):
    paragraph_number: int
    paragraph: str
    personality: PersonalityInfo
    # Which niche this subject belongs to (see scenario/categories.py):
    # people, places (battles, institutions, landmarks) or artifacts
    # (families, arms, books, laws, monuments).
    category: str = "people"
    # The detector's disambiguated search query ("Godwin, Earl of Wessex"),
    # kept so a later --fill-missing pass searches for the right person
    # instead of the bare name.
    query: str | None = None
    images: list[PersonalityImage] = Field(default_factory=list)
