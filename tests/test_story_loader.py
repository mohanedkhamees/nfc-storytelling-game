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
    with pytest.raises(StoryValidationError, match="'scenes' must be a non-empty list or object"):
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


def test_load_story_with_scenes_as_list(stories_dir: Path) -> None:
    list_story = {
        "id": "list_story",
        "title": "List Format Adventure",
        "start_scene": "start",
        "scenes": [
            {
                "id": "start",
                "title": "The Beginning",
                "text": "You are at the beginning.",
                "image": "start.png",
                "choices": {"Go North": "north"},
                "required_items": [],
                "gained_items": [],
                "lost_items": [],
                "ending": False,
            },
            {
                "id": "north",
                "title": "Northern Path",
                "text": "You head north.",
                "image": "north.png",
                "choices": {},
                "required_items": [],
                "gained_items": ["Map"],
                "lost_items": [],
                "ending": True,
            },
        ],
    }
    path = stories_dir / "list_story.json"
    path.write_text(json.dumps(list_story), encoding="utf-8")
    loader = StoryLoader(stories_dir)

    story = loader.load_story("list_story")
    assert story.id == "list_story"
    assert story.start_scene == "start"
    assert len(story.scenes) == 2

    start = story.get_scene("start")
    assert start is not None
    assert start.title == "The Beginning"
    assert start.choices == {"Go North": "north"}
    assert start.ending is False

    north = story.get_scene("north")
    assert north is not None
    assert north.title == "Northern Path"
    assert north.gained_items == ("Map",)
    assert north.is_ending is True
    assert north.ending_id == "default"


def test_load_story_with_scenes_as_dict_backward_compat(story_loader: StoryLoader) -> None:
    """Dict-format scenes (legacy schema) still load correctly."""
    story = story_loader.load_story("test_story")
    assert story.id == "test_story"
    assert isinstance(story.scenes, dict)
    assert story.get_scene("victory") is not None
    assert story.get_scene("victory").ending == "good"
    assert story.get_scene("victory").is_ending is True
    assert story.get_scene("victory").ending_id == "good"

    swamp_end = story.get_scene("swamp_end")
    assert swamp_end is not None
    assert swamp_end.ending == "bad"
    assert swamp_end.is_ending is True
    assert swamp_end.ending_id == "bad"


def test_load_production_stories() -> None:
    """Production story files load with list-format scenes and children titles."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")

    assert loader.list_available_stories() == ["benny", "mina", "nova"]

    benny = loader.load_story("benny")
    assert benny.id == "benny"
    assert benny.title == "Benny and the Lost Crystal"
    assert benny.start_scene == "bunny_home"
    assert benny.get_scene("bunny_home") is not None

    mina = loader.load_story("mina")
    assert mina.id == "mina"
    assert mina.title == "Mina and the Missing Moon Lantern"
    assert mina.start_scene == "school_yard"
    assert mina.get_scene("school_yard") is not None

    nova = loader.load_story("nova")
    assert nova.id == "nova"
    assert nova.title == "Nova and the Friendly Star"
    assert nova.start_scene == "bedroom"
    assert nova.get_scene("bedroom") is not None


def test_list_story_titles_discovers_production_stories() -> None:
    """Exactly three children story titles are discovered from stories/*.json."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    titles = loader.list_story_titles()
    assert titles == [
        "Benny and the Lost Crystal",
        "Mina and the Missing Moon Lantern",
        "Nova and the Friendly Star",
    ]


def test_choice_labels_loaded_from_production_stories() -> None:
    """Production scenes expose child-friendly choice_labels for every choice."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    benny = loader.load_story("benny")
    home = benny.get_scene("bunny_home")
    assert home is not None
    assert home.choice_labels == {
        "Talk": "💬 Talk — Ask Grandma Rabbit for help",
        "Run": "🏃 Run — Head into the whispering forest",
        "Key": "🗝️ Key — Open the little wooden box",
    }
    for scene in benny.scenes.values():
        if scene.choices:
            assert set(scene.choice_labels.keys()) == set(scene.choices.keys())


def test_choice_labels_backward_compat_missing_field(stories_dir: Path) -> None:
    """Scenes without choice_labels default to an empty dict."""
    loader = StoryLoader(stories_dir)
    story = loader.load_story("test_story")
    start = story.get_scene("start")
    assert start is not None
    assert start.choice_labels == {}


def test_invalid_choice_labels_type_raises_validation_error(stories_dir: Path) -> None:
    invalid = {
        "id": "bad_labels",
        "title": "Bad Labels",
        "start_scene": "start",
        "scenes": {
            "start": {
                "id": "start",
                "text": "Start here.",
                "image": "start.png",
                "choices": {"Go": "end"},
                "choice_labels": ["not", "a", "dict"],
            },
            "end": {
                "id": "end",
                "text": "The end.",
                "image": "end.png",
                "choices": {},
            },
        },
    }
    path = stories_dir / "bad_labels.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    loader = StoryLoader(stories_dir)
    with pytest.raises(StoryValidationError, match="'choice_labels' must be an object"):
        loader.load_story(path)
