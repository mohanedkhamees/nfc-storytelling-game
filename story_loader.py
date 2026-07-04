"""Story JSON ingestion for the Tangible NFC Interactive Storybook.

Loads and validates branching story files from ``stories/`` and exposes
immutable domain objects (:class:`Story`, :class:`Scene`).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StoryLoadError(Exception):
    """Raised when a story file cannot be read or parsed."""


class StoryValidationError(StoryLoadError):
    """Raised when story JSON is syntactically valid but fails structural checks."""


@dataclass(frozen=True)
class Scene:
    """Immutable single scene node in a branching story graph."""

    id: str
    text: str
    image: str
    choices: dict[str, str]
    title: str = ""
    choice_labels: dict[str, str] = field(default_factory=dict)
    required_items: tuple[str, ...] = ()
    gained_items: tuple[str, ...] = ()
    lost_items: tuple[str, ...] = ()
    ending: bool | str | None = None

    @property
    def is_ending(self) -> bool:
        """Return whether this scene marks a story ending."""
        if self.ending is None:
            return False
        if isinstance(self.ending, bool):
            return self.ending
        return bool(self.ending)

    @property
    def ending_id(self) -> str | None:
        """Return a string ending identifier, or ``None`` for non-endings."""
        if self.ending is None or self.ending is False:
            return None
        if isinstance(self.ending, str):
            return self.ending
        return "default"


@dataclass(frozen=True)
class Story:
    """Immutable in-memory representation of a complete story graph."""

    id: str
    title: str
    start_scene: str
    scenes: dict[str, Scene]

    def get_scene(self, scene_id: str) -> Scene | None:
        """Retrieve a scene by ID, or ``None`` if it does not exist."""
        return self.scenes.get(scene_id)

    def is_ending(self, scene_id: str) -> bool:
        """Return whether the given scene is a terminal ending."""
        scene = self.get_scene(scene_id)
        return scene.is_ending if scene is not None else False


class StoryLoader:
    """Load, validate, and cache story JSON files from a directory."""

    def __init__(self, stories_dir: Path | str = "stories") -> None:
        """Initialize the loader with the directory containing story JSON files.

        Args:
            stories_dir: Path to the folder of ``*.json`` story files.
        """
        self._stories_dir = Path(stories_dir)
        self._cache: dict[str, Story] = {}

    @property
    def stories_dir(self) -> Path:
        """Return the configured stories directory path."""
        return self._stories_dir

    def load_story(self, name_or_path: str | Path) -> Story:
        """Load a story by ID, filename, or absolute/relative path.

        Accepts ``"benny"``, ``"benny.json"``, or a full path to a JSON file.
        Results are cached by story ID.

        Args:
            name_or_path: Story identifier or path to a JSON file.

        Returns:
            Parsed :class:`Story` instance.

        Raises:
            StoryLoadError: If the file cannot be read.
            StoryValidationError: If the JSON structure is invalid.
        """
        path = self._resolve_story_path(name_or_path)
        raw = self._read_json_file(path)
        story = self._parse_story(raw, source=path)

        if story.id in self._cache:
            cached = self._cache[story.id]
            if cached is not story:
                self._cache[story.id] = story
        else:
            self._cache[story.id] = story

        return story

    def load_all_stories(self) -> dict[str, Story]:
        """Load every ``*.json`` story file in the stories directory.

        Returns:
            Mapping of story ID to :class:`Story`. Files that fail to load are
            skipped; callers may inspect logs or load individually for errors.

        Raises:
            StoryLoadError: If the stories directory does not exist.
        """
        if not self._stories_dir.is_dir():
            raise StoryLoadError(f"Stories directory not found: {self._stories_dir}")

        stories: dict[str, Story] = {}
        for path in sorted(self._stories_dir.glob("*.json")):
            try:
                story = self.load_story(path)
            except StoryLoadError:
                continue
            stories[story.id] = story
        return stories

    def reload_story(self, name_or_path: str | Path) -> Story:
        """Force reload a story from disk, invalidating its cache entry.

        Args:
            name_or_path: Story identifier or path to a JSON file.

        Returns:
            Freshly parsed :class:`Story` instance.
        """
        path = self._resolve_story_path(name_or_path)
        raw = self._read_json_file(path)
        story = self._parse_story(raw, source=path)
        self._cache[story.id] = story
        return story

    def get_cached_story(self, story_id: str) -> Story | None:
        """Return a cached story by ID without reading from disk.

        Args:
            story_id: Story identifier.

        Returns:
            Cached :class:`Story`, or ``None`` if not yet loaded.
        """
        return self._cache.get(story_id)

    def list_available_stories(self) -> list[str]:
        """Return story IDs available as ``*.json`` files in the stories directory.

        Story IDs are read from each file's ``id`` field when possible; otherwise
        the filename stem is used as a fallback without loading the full story.
        """
        if not self._stories_dir.is_dir():
            return []

        story_ids: list[str] = []
        for path in sorted(self._stories_dir.glob("*.json")):
            try:
                raw = self._read_json_file(path)
                story_id = raw.get("id")
                if isinstance(story_id, str) and story_id.strip():
                    story_ids.append(story_id.strip())
                else:
                    story_ids.append(path.stem)
            except StoryLoadError:
                story_ids.append(path.stem)
        return story_ids

    def list_story_titles(self) -> list[str]:
        """Return display titles for every loadable ``*.json`` story in the directory.

        Titles come from each file's ``title`` field. Files that fail to load are
        skipped. Results are sorted alphabetically by title.
        """
        titles: list[str] = []
        for story_id in self.list_available_stories():
            try:
                story = self.load_story(story_id)
            except StoryLoadError:
                continue
            titles.append(story.title)
        return sorted(titles)

    def clear_cache(self) -> None:
        """Remove all cached stories."""
        self._cache.clear()

    def _resolve_story_path(self, name_or_path: str | Path) -> Path:
        """Resolve a story name or path to an existing JSON file."""
        candidate = Path(name_or_path)
        if candidate.is_file():
            return candidate

        stem = Path(name_or_path).stem
        direct = self._stories_dir / f"{stem}.json"
        if direct.is_file():
            return direct

        if not self._stories_dir.is_dir():
            raise StoryLoadError(f"Stories directory not found: {self._stories_dir}")

        for path in self._stories_dir.glob("*.json"):
            try:
                raw = self._read_json_file(path)
            except StoryLoadError:
                continue
            story_id = raw.get("id")
            if isinstance(story_id, str) and story_id.strip() == stem:
                return path

        raise StoryLoadError(
            f"Story not found for {name_or_path!r} in {self._stories_dir}"
        )

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        """Read and parse a JSON object from disk."""
        if not path.is_file():
            raise StoryLoadError(f"Story file not found: {path}")

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StoryLoadError(f"Failed to read story file {path}: {exc}") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise StoryLoadError(f"Malformed JSON in {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise StoryValidationError(
                f"Story file {path} must contain a JSON object, got {type(data).__name__}"
            )
        return data

    def _parse_story(self, data: dict[str, Any], *, source: Path) -> Story:
        """Validate top-level story fields and build a :class:`Story`."""
        story_id = self._require_non_empty_str(data, "id", source)
        title = self._require_non_empty_str(data, "title", source)
        start_scene = self._require_non_empty_str(data, "start_scene", source)

        raw_scenes = data.get("scenes")
        scenes_dict = self._normalize_scenes(raw_scenes, source)

        scenes: dict[str, Scene] = {}
        for scene_key, scene_data in scenes_dict.items():
            if not isinstance(scene_data, dict):
                raise StoryValidationError(
                    f"Story {source}: scene {scene_key!r} must be an object"
                )
            scene = self._parse_scene(scene_data, source=source, scene_key=str(scene_key))
            if scene.id in scenes and scene.id != str(scene_key):
                raise StoryValidationError(
                    f"Story {source}: duplicate scene id {scene.id!r}"
                )
            scenes[scene.id] = scene

        if start_scene not in scenes:
            raise StoryValidationError(
                f"Story {source}: start_scene {start_scene!r} is not defined in scenes"
            )

        self._validate_choice_targets(scenes, source)

        return Story(id=story_id, title=title, start_scene=start_scene, scenes=scenes)

    def _parse_scene(
        self,
        data: dict[str, Any],
        *,
        source: Path,
        scene_key: str,
    ) -> Scene:
        """Validate and parse a single scene object."""
        scene_id = self._require_non_empty_str(data, "id", source, context=scene_key)
        raw_title = data.get("title", "")
        if raw_title is None:
            raw_title = ""
        if not isinstance(raw_title, str):
            raise StoryValidationError(
                f"Story {source}, scene {scene_id!r}: 'title' must be a string"
            )
        title = raw_title.strip()
        text = self._require_non_empty_str(data, "text", source, context=scene_key)
        image = self._require_non_empty_str(data, "image", source, context=scene_key)

        raw_choices = data.get("choices", {})
        if raw_choices is None:
            raw_choices = {}
        if not isinstance(raw_choices, dict):
            raise StoryValidationError(
                f"Story {source}, scene {scene_id!r}: 'choices' must be an object"
            )

        choices: dict[str, str] = {}
        for action_name, next_scene in raw_choices.items():
            if not isinstance(action_name, str) or not action_name.strip():
                raise StoryValidationError(
                    f"Story {source}, scene {scene_id!r}: choice keys must be non-empty strings"
                )
            if not isinstance(next_scene, str) or not next_scene.strip():
                raise StoryValidationError(
                    f"Story {source}, scene {scene_id!r}: choice {action_name!r} "
                    "must map to a non-empty scene id"
                )
            choices[action_name.strip()] = next_scene.strip()

        choice_labels = self._parse_choice_labels(
            data.get("choice_labels"),
            source=source,
            scene_id=scene_id,
            choices=choices,
        )

        required_items = self._parse_string_list(
            data.get("required_items"), source, scene_id, "required_items"
        )
        gained_items = self._parse_string_list(
            data.get("gained_items"), source, scene_id, "gained_items"
        )
        lost_items = self._parse_string_list(
            data.get("lost_items"), source, scene_id, "lost_items"
        )
        ending = self._parse_ending(data.get("ending"), source, scene_id)

        return Scene(
            id=scene_id,
            text=text,
            image=image,
            choices=choices,
            title=title,
            choice_labels=choice_labels,
            required_items=tuple(required_items),
            gained_items=tuple(gained_items),
            lost_items=tuple(lost_items),
            ending=ending,
        )

    def _normalize_scenes(
        self,
        raw_scenes: Any,
        source: Path,
    ) -> dict[str, dict[str, Any]]:
        """Convert scenes from list or dict format into a dict keyed by scene id."""
        if isinstance(raw_scenes, list):
            if not raw_scenes:
                raise StoryValidationError(
                    f"Story {source}: 'scenes' must be a non-empty list or object"
                )
            scenes_dict: dict[str, dict[str, Any]] = {}
            for index, scene_data in enumerate(raw_scenes):
                if not isinstance(scene_data, dict):
                    raise StoryValidationError(
                        f"Story {source}: scenes[{index}] must be an object"
                    )
                scene_id = scene_data.get("id")
                if not isinstance(scene_id, str) or not scene_id.strip():
                    raise StoryValidationError(
                        f"Story {source}: scenes[{index}] must have a non-empty 'id'"
                    )
                scene_id = scene_id.strip()
                if scene_id in scenes_dict:
                    raise StoryValidationError(
                        f"Story {source}: duplicate scene id {scene_id!r}"
                    )
                scenes_dict[scene_id] = scene_data
            return scenes_dict

        if isinstance(raw_scenes, dict):
            if not raw_scenes:
                raise StoryValidationError(
                    f"Story {source}: 'scenes' must be a non-empty list or object"
                )
            return dict(raw_scenes)

        raise StoryValidationError(
            f"Story {source}: 'scenes' must be a list or object, "
            f"got {type(raw_scenes).__name__}"
        )

    def _validate_choice_targets(self, scenes: dict[str, Scene], source: Path) -> None:
        """Ensure every choice references an existing scene ID."""
        valid_ids = set(scenes)
        for scene in scenes.values():
            for action_name, target_id in scene.choices.items():
                if target_id not in valid_ids:
                    raise StoryValidationError(
                        f"Story {source}, scene {scene.id!r}: choice {action_name!r} "
                        f"references unknown scene {target_id!r}"
                    )

    def _parse_choice_labels(
        self,
        value: Any,
        *,
        source: Path,
        scene_id: str,
        choices: dict[str, str],
    ) -> dict[str, str]:
        """Parse optional human-friendly labels for NFC choice cards."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise StoryValidationError(
                f"Story {source}, scene {scene_id!r}: 'choice_labels' must be an object"
            )

        labels: dict[str, str] = {}
        for key, label in value.items():
            if not isinstance(key, str) or not key.strip():
                raise StoryValidationError(
                    f"Story {source}, scene {scene_id!r}: "
                    "choice_labels keys must be non-empty strings"
                )
            if not isinstance(label, str) or not label.strip():
                raise StoryValidationError(
                    f"Story {source}, scene {scene_id!r}: "
                    f"choice_labels[{key!r}] must be a non-empty string"
                )
            labels[key.strip()] = label.strip()

        choice_keys = set(choices)
        label_keys = set(labels)
        extra = label_keys - choice_keys
        missing = choice_keys - label_keys
        if extra:
            logger.warning(
                "Story %s, scene %r: choice_labels has keys not in choices: %s",
                source,
                scene_id,
                sorted(extra),
            )
        if missing:
            logger.warning(
                "Story %s, scene %r: choices missing choice_labels for: %s",
                source,
                scene_id,
                sorted(missing),
            )

        return labels

    def _parse_string_list(
        self,
        value: Any,
        source: Path,
        scene_id: str,
        field_name: str,
    ) -> list[str]:
        """Parse an optional list of non-empty strings."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise StoryValidationError(
                f"Story {source}, scene {scene_id!r}: '{field_name}' must be a list"
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise StoryValidationError(
                    f"Story {source}, scene {scene_id!r}: "
                    f"'{field_name}[{index}]' must be a non-empty string"
                )
            items.append(item.strip())
        return items

    def _parse_ending(
        self,
        value: Any,
        source: Path,
        scene_id: str,
    ) -> bool | str | None:
        """Parse the optional ending marker."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise StoryValidationError(
            f"Story {source}, scene {scene_id!r}: 'ending' must be bool, string, or omitted"
        )

    def _require_non_empty_str(
        self,
        data: dict[str, Any],
        field: str,
        source: Path,
        *,
        context: str | None = None,
    ) -> str:
        """Require a non-empty string field."""
        value = data.get(field)
        prefix = f"Story {source}"
        if context is not None:
            prefix += f", scene {context!r}"
        if not isinstance(value, str) or not value.strip():
            raise StoryValidationError(f"{prefix}: '{field}' must be a non-empty string")
        return value.strip()


if __name__ == "__main__":
    loader = StoryLoader()
    print("=== StoryLoader demo ===\n")
    print(f"Available stories: {loader.list_available_stories()}\n")

    for story_id in loader.list_available_stories():
        story = loader.load_story(story_id)
        print(f"Loaded {story.id!r}: {story.title!r} ({len(story.scenes)} scenes)")
        start = story.get_scene(story.start_scene)
        if start:
            print(f"  start: {start.id!r} — choices: {list(start.choices.keys())}")
