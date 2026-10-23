from __future__ import annotations

import logging
from pathlib import Path

from scenario.categories import DEFAULT_CATEGORIES
from scenario.models import (
    ImageCandidate,
    PersonalityEntry,
    PersonalityImage,
    PersonalityInfo,
    PersonalityMention,
)
from scenario.services.biography import BiographyLookupService
from scenario.services.downloader import ImageDownloaderService
from scenario.services.image_selection import ImageSelectionService
from scenario.services.personality_detector import PersonalityDetectorService
from scenario.services.scenario_parser import ScenarioParserService
from scenario.services.wikimedia import PersonalityImagePool

logger = logging.getLogger(__name__)

IMAGES_PER_PERSONALITY = 1
# How many candidates are downloaded and compared at once per image slot.
SELECTION_BATCH_SIZE = 3
# A batch can come back with no winner (none of the 3 qualify) — cap how
# many batches we'll try per personality so a name with mostly unusable
# Commons results still terminates instead of draining the whole pool.
MAX_BATCHES_PER_PERSONALITY = 4


def _first_mention_per_personality(
    mentions: list[PersonalityMention],
) -> list[PersonalityMention]:
    """Optional mode: one card per personality, taken from where they first
    come up. The default is every mention, each with a *different* picture
    (see ScenarioPipeline); a mention is left without an image once the
    person's distinct candidates run out, never given a repeat.
    """
    seen: set[tuple[str, str]] = set()
    first: list[PersonalityMention] = []
    for mention in sorted(mentions, key=lambda m: m.paragraph_number):
        key = (mention.category, mention.name)
        if key in seen:
            continue
        seen.add(key)
        first.append(mention)
    return first


def _pool_key(category: str, name: str) -> str:
    # Used-image bookkeeping and the search pool are per subject; the same
    # word can name a person and a place ("Hastings"), so key by both.
    return f"{category}:{name}"


class ScenarioPipeline:
    def __init__(
        self,
        parser: ScenarioParserService,
        detector: PersonalityDetectorService,
        biography: BiographyLookupService,
        image_pool: PersonalityImagePool,
        downloader: ImageDownloaderService,
        selector: ImageSelectionService,
    ) -> None:
        self._parser = parser
        self._detector = detector
        self._biography = biography
        self._image_pool = image_pool
        self._downloader = downloader
        self._selector = selector
        self._bio_cache: dict[str, PersonalityInfo] = {}
        # Same person can appear in many paragraphs — this must be shared
        # across all of them (keyed by name, a stable identity), not local
        # to one paragraph's collection call. Otherwise, once the pool
        # cycles back around, a later paragraph has no memory that an
        # earlier paragraph already claimed or ruled out a given candidate.
        self._used_ids: dict[str, set[str]] = {}
        # Candidates already shown to the selector (per name). Fresh ones are
        # offered before runners-up, so a person's later mentions keep
        # seeing new pictures instead of re-judging the same three.
        self._offered_ids: dict[str, set[str]] = {}

    def run(
        self,
        docx_path: Path,
        output_dir: Path,
        categories: list[str] | None = None,
        one_per_person: bool = False,
    ) -> list[PersonalityEntry]:
        paragraphs = self._parser.parse(docx_path)
        text_by_number = {p.number: p.text for p in paragraphs}
        detected = self._detector.detect(paragraphs, categories or list(DEFAULT_CATEGORIES))
        if one_per_person:
            mentions = _first_mention_per_personality(detected)
        else:
            mentions = sorted(detected, key=lambda m: m.paragraph_number)

        entries: list[PersonalityEntry] = []
        # A paragraph can feature more than one personality — image numbers
        # run on continuously within a paragraph (102.1/102.2 for the first
        # personality, 102.3/102.4 for the second) so two entries sharing a
        # paragraph never write over each other's files.
        next_index_by_paragraph: dict[int, int] = {}

        total = len(mentions)
        for position, mention in enumerate(mentions, start=1):
            info = self._get_biography(mention.name, mention.query, mention.category)
            entry = PersonalityEntry(
                paragraph_number=mention.paragraph_number,
                paragraph=text_by_number[mention.paragraph_number],
                personality=info,
                category=mention.category,
                query=mention.query,
            )
            entries.append(entry)

            start_index = next_index_by_paragraph.get(mention.paragraph_number, 1)
            next_index_by_paragraph[mention.paragraph_number] = self._collect_images(
                entry, output_dir, start_index
            )
            # Machine-readable progress for whoever tails the log (the bot).
            found = sum(1 for e in entries if e.images)
            logger.info("PROGRESS images %d/%d found=%d", position, total, found)

        for entry in entries:
            entry.images.sort(key=lambda image: image.file)
        return entries

    def fill_missing_images(self, entries: list[PersonalityEntry], output_dir: Path) -> None:
        """Tops up any entry with fewer than IMAGES_PER_PERSONALITY images —
        for a JSON left incomplete by transient Wikimedia rate limiting or
        an exhausted candidate pool, without re-running LLM detection.
        """
        next_index_by_paragraph: dict[int, int] = {}

        for entry in entries:
            self._used_ids.setdefault(_pool_key(entry.category, entry.personality.name), set()).update(
                image.source_id for image in entry.images
            )
            if entry.images:
                # file names are "<paragraph>.<index>.jpg" — recover the
                # highest index already claimed for this paragraph so a
                # sibling personality's top-up can't collide with it either.
                used_index = max(int(image.file.split(".")[1]) for image in entry.images)
                next_index_by_paragraph[entry.paragraph_number] = max(
                    next_index_by_paragraph.get(entry.paragraph_number, 1), used_index + 1
                )

        for entry in entries:
            if len(entry.images) >= IMAGES_PER_PERSONALITY:
                continue
            start_index = next_index_by_paragraph.get(
                entry.paragraph_number, len(entry.images) + 1
            )
            next_index_by_paragraph[entry.paragraph_number] = self._collect_images(
                entry, output_dir, start_index
            )

        for entry in entries:
            entry.images.sort(key=lambda image: image.file)

    def refresh_years(self, entries: list[PersonalityEntry]) -> int:
        """Re-runs the date lookup for every entry (one lookup per distinct
        subject, cached) and returns how many captions changed."""
        changed = 0
        for entry in entries:
            info = self._get_biography(entry.personality.name, entry.query, entry.category)
            if info.years != entry.personality.years:
                logger.info(
                    "Years for %r: %r -> %r", entry.personality.name, entry.personality.years, info.years
                )
                entry.personality.years = info.years
                changed += 1
        return changed

    def _get_biography(
        self, name: str, query: str | None = None, category: str = "people"
    ) -> PersonalityInfo:
        cache_key = _pool_key(category, name)
        info = self._bio_cache.get(cache_key)
        if info is None:
            try:
                info = self._biography.lookup(name, query, category)
            except Exception:
                logger.warning(
                    "Biography lookup failed for %r, leaving years empty", name, exc_info=True
                )
                info = PersonalityInfo(name=name, years=None)
            self._bio_cache[cache_key] = info
        return info

    def _collect_images(self, entry: PersonalityEntry, output_dir: Path, start_index: int) -> int:
        """Pulls candidates in small batches, downloads each batch, and asks
        the selector to pick the single best one out of it — until the entry
        has IMAGES_PER_PERSONALITY images or the batch budget runs out.
        Returns the next unused image-number slot for this paragraph, so a
        second personality in the same paragraph can continue after it.
        """
        name = entry.personality.name
        query = entry.query or name
        category = entry.category
        key = _pool_key(category, name)
        used_ids = self._used_ids.setdefault(key, set())
        next_index = start_index
        batches_tried = 0

        while len(entry.images) < IMAGES_PER_PERSONALITY and batches_tried < MAX_BATCHES_PER_PERSONALITY:
            batches_tried += 1
            batch = self._next_unused_batch(key, query, category, used_ids)
            if not batch:
                break

            downloaded: list[tuple[ImageCandidate, Path]] = []
            for position, candidate in enumerate(batch):
                temp_path = output_dir / f".candidate-{entry.paragraph_number}-{next_index}-{position}.jpg"
                try:
                    self._downloader.download(candidate, temp_path)
                except Exception:
                    logger.warning(
                        "Download failed for a candidate of %r, skipping it", name, exc_info=True
                    )
                    used_ids.add(candidate.source_id)
                    continue
                downloaded.append((candidate, temp_path))

            if not downloaded:
                continue

            try:
                winner = self._selector.pick_best(
                    name, downloaded, context=entry.paragraph, category=category
                )
            except Exception:
                logger.warning(
                    "Selection call failed for a batch of %r, discarding this batch",
                    name,
                    exc_info=True,
                )
                winner = None
            if winner is None:
                logger.info("No candidate in this batch clearly shows %r", name)

            for candidate, temp_path in downloaded:
                if winner is not None and candidate.source_id == winner.source_id:
                    final_path = output_dir / f"{entry.paragraph_number}.{next_index}.jpg"
                    temp_path.rename(final_path)
                    entry.images.append(
                        PersonalityImage(file=final_path.name, source_id=candidate.source_id, url=candidate.url)
                    )
                    used_ids.add(candidate.source_id)
                    next_index += 1
                else:
                    temp_path.unlink(missing_ok=True)
                    # A runner-up lost a comparison, it wasn't rejected — leave
                    # it in circulation for the next paragraph. Only retire the
                    # whole batch when nothing in it cleared the bar.
                    if winner is None:
                        used_ids.add(candidate.source_id)

        return next_index

    def _next_unused_batch(
        self, key: str, query: str, category: str, used_ids: set[str]
    ) -> list[ImageCandidate]:
        """Next SELECTION_BATCH_SIZE candidates for this person that are not
        used (picked for an earlier mention, or retired). Never-offered
        candidates come first, in search order; if there are fewer than a
        batch, runners-up from earlier comparisons top it up. Empty once the
        person's distinct candidates are exhausted — the caller then leaves
        the mention without an image rather than repeating one.
        """
        try:
            pool = self._image_pool.candidates(key, query, category)
        except Exception:
            logger.warning("Wikimedia search failed for %r", query, exc_info=True)
            return []

        offered = self._offered_ids.setdefault(key, set())
        available = [c for c in pool if c.source_id not in used_ids]
        fresh = [c for c in available if c.source_id not in offered]
        runners_up = [c for c in available if c.source_id in offered]

        batch = (fresh + runners_up)[:SELECTION_BATCH_SIZE]
        offered.update(c.source_id for c in batch)
        if not batch:
            logger.info("No distinct image candidates left for %r", key)
        return batch
