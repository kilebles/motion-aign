from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_PERSONALITIES_DIR = PROJECT_ROOT / "public" / "personalities"
# Extra flags for `remotion render`, e.g. "--concurrency=1 --offthreadvideo-cache-size-in-bytes=157286400"
# on a small server where the default settings run out of memory.
EXTRA_RENDER_ARGS = shlex.split(os.environ.get("REMOTION_RENDER_ARGS", ""))


def _pick_list(raw: str | None) -> list[str] | None:
    """"a" -> ["a"], "a,b" -> ["a", "b"], None -> None (let the composition pick)."""
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def render_cards(
    json_path: Path,
    output_dir: Path,
    theme: str | None = None,
    choreography: str | None = None,
    card_accent: str | None = None,
    skip_existing: bool = False,
) -> None:
    entries = json.loads(json_path.read_text(encoding="utf-8"))
    source_dir = json_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    PUBLIC_PERSONALITIES_DIR.mkdir(parents=True, exist_ok=True)

    renderable = [entry for entry in entries if entry.get("images")]
    rendered = 0
    for entry in entries:
        name = entry["personality"]["name"]
        images = entry.get("images", [])
        if not images:
            print(f"Skipping {name!r} (paragraph {entry['paragraph_number']}): no image", file=sys.stderr)
            continue

        # Image file names are already unique per entry ("<paragraph>.<index>.jpg"),
        # even when two personalities share a paragraph — reuse the stem for the
        # output file so two entries never collide.
        image_file = images[0]["file"]
        clip_name = Path(image_file).stem

        source_image = source_dir / image_file
        dest_image = PUBLIC_PERSONALITIES_DIR / image_file
        shutil.copy(source_image, dest_image)

        props: dict = {
            "image": f"personalities/{image_file}",
            "name": name,
        }
        # Always set: Remotion merges --props over the composition's
        # defaultProps, so an omitted key would show the Studio sample years.
        props["years"] = entry["personality"].get("years") or ""
        # Variant pins. Omitted = the composition picks per seed (image + name),
        # so every clip gets its own theme / entrance / card accent combination.
        for key, raw in (("theme", theme), ("choreography", choreography), ("cardAccent", card_accent)):
            pool = _pick_list(raw)
            if pool:
                props[key] = pool[0] if len(pool) == 1 else pool

        output_file = output_dir / f"{clip_name}.mp4"
        if skip_existing and output_file.exists():
            print(f"Skipping {output_file}: already rendered", file=sys.stderr)
            continue
        print(f"Rendering {output_file} for {name!r}...", file=sys.stderr)
        try:
            subprocess.run(
                [
                    "npx",
                    "remotion",
                    "render",
                    "src/index.ts",
                    "PersonalityCard",
                    str(output_file),
                    f"--props={json.dumps(props)}",
                    *EXTRA_RENDER_ARGS,
                ],
                cwd=PROJECT_ROOT,
                check=True,
            )
        except subprocess.CalledProcessError:
            print(f"Render failed for {name!r}, skipping", file=sys.stderr)
            continue
        rendered += 1
        print(f"PROGRESS render {rendered}/{len(renderable)}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a 10s PersonalityCard video for every personality found in a scenario JSON"
    )
    parser.add_argument("json_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--theme",
        help="Pin a theme id, or a comma-separated pool to pick from (see src/library/themes.ts)",
    )
    parser.add_argument(
        "--choreography",
        help="Pin a choreography id or pool (see src/library/choreographies.ts)",
    )
    parser.add_argument(
        "--card-accent",
        help="Pin a card accent: sweep, flash, none — or a comma-separated pool",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Leave clips that already exist in the output dir alone (e.g. after --fill-missing added new entries)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or (args.json_path.parent / "videos")
    render_cards(
        args.json_path,
        output_dir,
        theme=args.theme,
        choreography=args.choreography,
        card_accent=args.card_accent,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    main()
