from __future__ import annotations

import asyncio
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = PROJECT_ROOT / "jobs"

# Bot API caps a single uploaded document at 50 MB. Clips are stored, not
# compressed (mp4 doesn't shrink), so an archive's size is the sum of its
# files plus a few hundred bytes of zip headers.
MAX_ARCHIVE_BYTES = 49 * 1024 * 1024
_ZIP_ENTRY_OVERHEAD = 512


_PROGRESS = re.compile(r"PROGRESS (images|render) (\d+)/(\d+)(?: found=(\d+))?")


def read_progress(log_path: Path) -> str | None:
    """Human-readable status from the last PROGRESS line in a job log, or
    None before the first one. Reads only the tail, the log can get long."""
    try:
        with log_path.open("rb") as log:
            log.seek(0, 2)
            log.seek(max(0, log.tell() - 65536))
            tail = log.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    matches = _PROGRESS.findall(tail)
    if not matches:
        return None
    stage, done, total, found = matches[-1]
    if stage == "images":
        return f"Изображения: {done} из {total}, найдено {found}."
    # After a resume the renderer only counts clips made in this run; the
    # files on disk are the truth.
    on_disk = len(list((log_path.parent / "videos").glob("*.mp4")))
    return f"Рендер: {max(int(done), on_disk)} из {total}."


class StageError(RuntimeError):
    def __init__(self, stage: str, log_path: Path) -> None:
        super().__init__(f"{stage} failed, see {log_path}")
        self.stage = stage
        self.log_path = log_path


@dataclass
class JobResult:
    json_path: Path
    videos_dir: Path
    subjects: int
    with_images: int
    """subject count per category id, in scenario order of first appearance."""
    per_category: dict[str, int]
    clips: list[Path]


async def _run_stage(stage: str, args: list[str], log_path: Path) -> None:
    with log_path.open("ab") as log:
        log.write(f"=== {stage}: {' '.join(args)}\n".encode())
        log.flush()
        process = await asyncio.create_subprocess_exec(
            *args, cwd=PROJECT_ROOT, stdout=log, stderr=asyncio.subprocess.STDOUT
        )
        code = await process.wait()
    if code != 0:
        raise StageError(stage, log_path)


async def run_pipeline(docx_path: Path, categories: list[str], on_stage=None) -> JobResult:
    """docx -> scenario JSON + images -> one clip per subject mention.
    Everything lands next to the docx in its job directory; the log there
    holds both stages' output. Safe to call again for the same docx after an
    interruption: a finished scenario stage is not repeated and clips that
    already exist are not re-rendered."""
    job_dir = docx_path.parent
    scenario_dir = job_dir / "scenario"
    videos_dir = job_dir / "videos"
    log_path = job_dir / "log.txt"
    python = sys.executable
    json_path = scenario_dir / f"{docx_path.stem}.json"

    if not json_path.exists():
        await _run_stage(
            "scenario",
            [
                python, "-m", "scenario.main", str(docx_path),
                "--output-dir", str(scenario_dir),
                "--categories", ",".join(categories),
            ],
            log_path,
        )
    entries = json.loads(json_path.read_text(encoding="utf-8"))
    with_images = sum(1 for entry in entries if entry.get("images"))
    per_category: dict[str, int] = {}
    for entry in entries:
        category = entry.get("category", "people")
        per_category[category] = per_category.get(category, 0) + 1
    if on_stage:
        await on_stage(len(entries), with_images, per_category)

    await _run_stage(
        "render",
        [
            python, "-m", "scenario.render_cards", str(json_path),
            "--output-dir", str(videos_dir), "--skip-existing",
        ],
        log_path,
    )
    clips = sorted(videos_dir.glob("*.mp4"), key=lambda p: [float(x) for x in p.stem.split(".")])
    return JobResult(json_path, videos_dir, len(entries), with_images, per_category, clips)


def make_archives(result: JobResult, out_dir: Path, stem: str) -> list[Path]:
    """Packs the clips (and the scenario JSON, in the first part) into as few
    zip files as fit under the Bot API upload cap. Greedy, in scenario order,
    so each part holds a contiguous run of clips."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = [result.json_path, *result.clips]

    parts: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    for path in files:
        size = path.stat().st_size + _ZIP_ENTRY_OVERHEAD
        if current and current_size + size > MAX_ARCHIVE_BYTES:
            parts.append(current)
            current, current_size = [], 0
        current.append(path)
        current_size += size
    if current:
        parts.append(current)

    archives: list[Path] = []
    for index, part in enumerate(parts, start=1):
        suffix = f"-{index}of{len(parts)}" if len(parts) > 1 else ""
        archive = out_dir / f"{stem}{suffix}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
            for path in part:
                zf.write(path, arcname=path.name)
        archives.append(archive)
    return archives


# --- job records -----------------------------------------------------------
#
# Each job directory holds a job.json: who asked, for what, and how far it
# got. The queue itself lives in memory; these records are what lets a
# restarted bot pick the queue back up, including an archive delivery that
# was cut off halfway.

JOB_FILE = "job.json"
ACTIVE_STATUSES = ("queued", "running", "sending")


def save_job(job_dir: Path, record: dict) -> None:
    tmp = job_dir / (JOB_FILE + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(job_dir / JOB_FILE)


def load_active_jobs() -> list[tuple[Path, dict]]:
    """Unfinished jobs, oldest first."""
    found: list[tuple[float, Path, dict]] = []
    if not JOBS_DIR.exists():
        return []
    for path in JOBS_DIR.glob(f"*/{JOB_FILE}"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("status") in ACTIVE_STATUSES:
            found.append((record.get("created", path.stat().st_mtime), path.parent, record))
    found.sort(key=lambda item: item[0])
    return [(job_dir, record) for _, job_dir, record in found]
