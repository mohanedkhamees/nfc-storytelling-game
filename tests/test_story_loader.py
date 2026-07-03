"""Tests for story_loader.StoryLoader validation and loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from story_loader import StoryLoadError, StoryLoader, StoryValidationError


def test_load_valid_story(story_loader: StoryLoader) -> None:
    story = story_loader.load_story("test_story")
    assert story.id == "test_story"
    assert story.title == "Test Adventure"
    assert story.start_scene == "start"
    assert len(story.scenes) == 6

    start = story.get_scene("start")
    assert start is not None
    assert start.choices == {"Go North": "north", "Go South": "south", "Climb": "peak"}


def test_missing_story_file_raises_story_load_error(tmp_path: Path) -> None:
    stories = tmp_path / "stories"
    stories.mkdir()
    loader = StoryLoader(stories)
    with pytest.raises(StoryLoadError, match="Story not found"):
        loader.load_story("missing")


def test_invalid_json_raises_story_load_error(stories_dir: Path) -> None:
    bad_path = stories_dir / "broken.json"
    bad_path.write_text("{ not valid json", encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryLoadError, match="Malformed JSON"):
        loader.load_story(bad_path)


def test_missing_required_top_level_field_raises_validation_error(
    stories_dir: Path,
) -> None:
    invalid = {
        "title": "No ID",
        "start_scene": "start",
        "scenes": {},
    }
    path = stories_dir / "no_id.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="'id' must be a non-empty string"):
        loader.load_story(path)


def test_empty_scenes_raises_validation_error(stories_dir: Path) -> None:
    invalid = {
        "id": "empty",
        "title": "Empty",
        "start_scene": "start",
        "scenes": {},
    }
    path = stories_dir / "empty_scenes.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="'scenes' must be a non-empty object"):
        loader.load_story(path)


def test_bad_start_scene_reference_raises_validation_error(stories_dir: Path) -> None:
    invalid = {
        "id": "bad_start",
        "title": "Bad Start",
        "start_scene": "missing_scene",
        "scenes": {
            "only": {
                "id": "only",
                "text": "Lonely scene.",
                "image": "only.png",
                "choices": {},
            }
        },
    }
    path = stories_dir / "bad_start.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="start_scene .* is not defined"):
        loader.load_story(path)


def test_bad_choice_target_raises_validation_error(stories_dir: Path) -> None:
    invalid = {
        "id": "bad_choice",
        "title": "Bad Choice",
        "start_scene": "start",
        "scenes": {
            "start": {
                "id": "start",
                "text": "Start here.",
                "image": "start.png",
                "choices": {"Go": "nowhere"},
            }
        },
    }
    path = stories_dir / "bad_choice.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="references unknown scene"):
        loader.load_story(path)


def test_missing_scene_required_field_raises_validation_error(stories_dir: Path) -> None:
    invalid = {
        "id": "bad_scene",
        "title": "Bad Scene",
        "start_scene": "start",
        "scenes": {
            "start": {
                "id": "start",
                "text": "No image field.",
                "choices": {},
            }
        },
    }
    path = stories_dir / "bad_scene.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="'image' must be a non-empty string"):
        loader.load_story(path)
