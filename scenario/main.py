from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from scenario.categories import CATEGORY_IDS, DEFAULT_CATEGORIES, parse_categories
from scenario.config import get_settings
from scenario.models import PersonalityEntry
from scenario.services.biography import WikipediaBiographyLookupService
from scenario.services.downloader import HttpImageDownloaderService
from scenario.services.image_relevance import GeminiImageRelevanceService, VerifiedWikimediaSearchService
from scenario.services.image_selection import GeminiImageSelectionService
from scenario.services.personality_detector import GeminiPersonalityDetectorService
from scenario.services.pipeline import ScenarioPipeline
from scenario.services.scenario_parser import DocxScenarioParserService
from scenario.services.wikidata import WikidataResolver
from scenario.services.wikidata_image_search import WikidataImageSearchService
from scenario.services.wikimedia import (
    CombinedWikimediaSearchService,
    CommonsSearchService,
    PersonalityImagePool,
    _search_subject,
)


def _build_pipeline() -> ScenarioPipeline:
    settings = get_settings()
    resolver = WikidataResolver()

    # Wikidata's curated portrait (P18) + dedicated Commons category (P373)
    # first — both are human-vetted, so they're far more precise than
    # free-text Commons search. Commons search results are appended after
    # them so a person mentioned many times has enough distinct pictures.
    def canonical_name(query: str) -> str | None:
        subject = _search_subject(query)
        qid = resolver.resolve_qid_any(query if query != subject else None, subject)
        return resolver.label(qid) if qid else None

    search = VerifiedWikimediaSearchService(
        search=CombinedWikimediaSearchService(
            primary=WikidataImageSearchService(resolver),
            fallback=CommonsSearchService(),
            canonical_name=canonical_name,
        ),
        relevance=GeminiImageRelevanceService(settings.google),
    )
    return ScenarioPipeline(
        parser=DocxScenarioParserService(),
        detector=GeminiPersonalityDetectorService(settings.google),
        biography=WikipediaBiographyLookupService(resolver),
        image_pool=PersonalityImagePool(search),
        downloader=HttpImageDownloaderService(),
        selector=GeminiImageSelectionService(settings.google),
    )


def _write_json(entries: list[PersonalityEntry], output_json: Path) -> None:
    output_json.write_text(
        json.dumps([entry.model_dump() for entry in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Extract historical subjects (people, places, artifacts) and their Wikimedia images from a scenario docx"
    )
    parser.add_argument("docx_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help=f"Comma-separated subject categories to extract: {', '.join(CATEGORY_IDS)} (default: people)",
    )
    parser.add_argument(
        "--one-per-person",
        action="store_true",
        help="Only the first mention of each personality gets a card (default: every mention, each with a different image).",
    )
    parser.add_argument(
        "--refresh-years",
        action="store_true",
        help="Recompute the years caption of every entry in an existing output JSON (after a date-lookup fix), leaving images untouched.",
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help=(
            "Top up images for an existing output JSON's entries that have "
            "fewer than 2 images (e.g. after Wikimedia rate limiting cut a "
            "run short), without re-running LLM detection."
        ),
    )
    args = parser.parse_args()

    output_dir = args.output_dir or args.docx_path.with_suffix("")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / f"{args.docx_path.stem}.json"

    pipeline = _build_pipeline()

    if args.fill_missing or args.refresh_years:
        entries = [
            PersonalityEntry.model_validate(item)
            for item in json.loads(output_json.read_text(encoding="utf-8"))
        ]
        if args.refresh_years:
            changed = pipeline.refresh_years(entries)
            print(f"Years changed for {changed} entries", file=sys.stderr)
        if args.fill_missing:
            pipeline.fill_missing_images(entries, output_dir)
    else:
        entries = pipeline.run(
            args.docx_path,
            output_dir,
            categories=parse_categories(args.categories),
            one_per_person=args.one_per_person,
        )

    _write_json(entries, output_json)

    print(f"Found {len(entries)} subjects. Output: {output_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
