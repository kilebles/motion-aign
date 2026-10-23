from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from docx import Document

from scenario.models import ScenarioParagraph

# Standalone-line check only (anchored ^...$), same approach as hdoc-prompts:
# a heading phrase embedded mid-sentence in real narrative text is not filtered.
# Scenarios arrive in both Russian and English, so both vocabularies are matched.
_HEADING_LINE = re.compile(
    r"^(вступление|введение|заключение|пролог|эпилог|глава\s+\d+\b.*"
    r"|introduction|conclusion|prologue|epilogue|chapter\s+\d+\b.*)$",
    re.IGNORECASE,
)


def _is_heading(line: str) -> bool:
    return bool(_HEADING_LINE.match(line))


class ScenarioParserService(Protocol):
    def parse(self, path: Path) -> list[ScenarioParagraph]: ...


class DocxScenarioParserService:
    def parse(self, path: Path) -> list[ScenarioParagraph]:
        document = Document(path)
        paragraphs: list[ScenarioParagraph] = []
        number = 0
        for para in document.paragraphs:
            for line in para.text.split("\n"):
                line = line.strip()
                if not line or _is_heading(line):
                    continue
                number += 1
                paragraphs.append(ScenarioParagraph(number=number, text=line))
        return paragraphs
