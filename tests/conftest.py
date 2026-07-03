"""Shared pytest fixtures for the Tangible NFC Story Game."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from card_manager import CardManager
from story_engine import StoryEngine
from story_loader import StoryLoader


SAMPLE_CARDS = {
    "A1B2C3D4": {"name": "Test Story", "type": "story"},
    "11223344": {"name": "Go North", "type": "action"},
    "55667788": {"name": "Restart", "type": "system"},
    "99AABBCC": {"name": "Key", "type": "item"},
}

SAMPLE_STORY = {
    "id": "test_story",
    "title": "Test Adventure",
    "start_scene": "start",
    "scenes": {
        "start": {
            "id": "start",
            "text": "You are at the beginning.",
            "image": "start.png",
            "choices": {
                "Go North": "north",
                "Go South": "south",
                "Climb": "peak",
            },
        },
        "north": {
            "id": "north",
            "text": "You head north into the mountains.",
            "image": "north.png",
            "choices": {"Go North": "peak"},
            "gained_items": ["Map"],
        },
        "south": {
            "id": "south",
            "text": "You wander south through the swamp.",
            "image": "south.png",
            "choices": {"Go South": "swamp_end"},
        },
        "peak": {
            "id": "peak",
            "text": "The summit requires a map.",
            "image": "peak.png",
            "choices": {"Go North": "victory"},
            "required_items": ["Map"],
        },
        "swamp_end": {
            "id": "swamp_end",
            "text": "You are lost in the swamp forever.",
            "image": "swamp.png",
            "choices": {},
            "ending": "bad",
        },
        "victory": {
            "id": "victory",
            "text": "You reach the summit!",
            "image": "victory.png",
            "choices": {},
            "ending": "good",
        },
    },
}


@pytest.fixture
def cards_path(tmp_path: Path) -> Path:
    """Temporary cards.json for isolated CardManager tests."""
    path = tmp_path / "cards.json"
    path.write_text(json.dumps(SAMPLE_CARDS, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def card_manager(cards_path: Path) -> CardManager:
    """CardManager backed by a temporary card registry."""
    return CardManager(cards_path)


@pytest.fixture
def stories_dir(tmp_path: Path) -> Path:
    """Temporary stories directory with a valid sample story."""
    directory = tmp_path / "stories"
    directory.mkdir()
    (directory / "test_story.json").write_text(
        json.dumps(SAMPLE_STORY, indent=2),
        encoding="utf-8",
    )
    return directory


@pytest.fixture
def story_loader(stories_dir: Path) -> StoryLoader:
    """StoryLoader backed by a temporary stories directory."""
    return StoryLoader(stories_dir)


@pytest.fixture
def story_engine(story_loader: StoryLoader) -> StoryEngine:
    """StoryEngine wired to the temporary story loader."""
    return StoryEngine(story_loader)


@pytest.fixture
def sample_story(story_loader: StoryLoader):
    """Loaded sample Story instance."""
    return story_loader.load_story("test_story")
