#!/usr/bin/env python3
"""Generate placeholder PNGs for story image paths that do not yet exist on disk."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from asset_manager import create_placeholder_pil_image, infer_story_type

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
STORIES_DIR = PROJECT_ROOT / "stories"
DEFAULT_SIZE = (800, 600)


def collect_image_paths(stories_dir: Path) -> set[str]:
    """Scan story JSON files and return all unique ``image`` field values.

    Args:
        stories_dir: Directory containing ``*.json`` story files.

    Returns:
        Set of image path strings referenced by scene ``image`` fields.
        Malformed files are skipped with a warning.
    """
    paths: set[str] = set()
    for story_file in sorted(stories_dir.glob("*.json")):
        try:
            with story_file.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping unreadable story file %s: %s", story_file, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("Skipping story file %s: expected JSON object", story_file)
            continue
        for scene in data.get("scenes", {}).values():
            if not isinstance(scene, dict):
                continue
            image = scene.get("image")
            if isinstance(image, str) and image:
                paths.add(image)
    return paths


def generate_missing_placeholders(
    project_root: Path = PROJECT_ROOT,
    *,
    size: tuple[int, int] = DEFAULT_SIZE,
) -> int:
    """Create placeholder PNGs for missing story images without overwriting files.

    Returns:
        Number of placeholder files created.
    """
    image_paths = collect_image_paths(project_root / "stories")
    created = 0

    for relative_path in sorted(image_paths):
        target = project_root / relative_path
        if target.exists():
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        scene_hint = infer_story_type(relative_path)
        placeholder = create_placeholder_pil_image(
            size,
            label="Missing Image",
            scene_hint=scene_hint,
        )
        placeholder.save(target, format="PNG")
        logger.info("Created placeholder: %s", target)
        created += 1

    return created


def main() -> None:
    """Entry point for ``python3 generate_placeholders.py``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    created = generate_missing_placeholders()
    print(f"Generated {created} placeholder image(s).")


if __name__ == "__main__":
    main()
