"""Tests for story_engine.StoryEngine card-driven state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from card_manager import Card, CardType, UnknownCard
from story_engine import EngineOutcome, StoryEngine
from story_loader import StoryLoader


def _story_card(name: str = "Test Adventure", uid: str = "A1B2C3D4") -> Card:
    return Card(uid=uid, name=name, type=CardType.STORY)


def _action_card(name: str, uid: str = "11223344") -> Card:
    return Card(uid=uid, name=name, type=CardType.ACTION)


def _system_card(name: str = "Restart", uid: str = "55667788") -> Card:
    return Card(uid=uid, name=name, type=CardType.SYSTEM)


def test_story_start_via_story_card(story_engine: StoryEngine) -> None:
    result = story_engine.handle_card(_story_card())
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.story_id == "test_story"
    assert result.new_scene_id == "start"
    assert story_engine.is_story_active()

    scene = story_engine.get_current_scene()
    assert scene is not None
    assert scene.id == "start"


def test_scene_transition_via_action_card(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    result = story_engine.handle_card(_action_card("Go North"))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.previous_scene_id == "start"
    assert result.new_scene_id == "north"
    assert story_engine.get_current_scene().id == "north"


def test_invalid_action_returns_invalid_action(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    result = story_engine.handle_card(_action_card("Teleport"))
    assert result.outcome == EngineOutcome.INVALID_ACTION
    assert result.new_scene_id == "start"
    assert result.message == "This card cannot be used here."


def test_benny_run_from_morning_to_forest_path() -> None:
    """Run from Benny's Morning (bunny_home) reaches the whispering forest."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    assert engine.get_current_scene().id == "bunny_home"

    result = engine.handle_card(_action_card("Run", uid="run1"))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.previous_scene_id == "bunny_home"
    assert result.new_scene_id == "forest_path"


def test_item_key_card_works_when_key_is_scene_choice() -> None:
    """Key is registered as item type but may still be a valid scene choice."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    result = engine.handle_card(Card(uid="55555555", name="Key", type=CardType.ITEM))

    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "locked_box"


def test_benny_whispering_forest_choice_transitions() -> None:
    """Benny forest_path choices resolve to the correct target scenes."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    run_result = engine.handle_card(_action_card("Run", uid="run1"))
    assert run_result.new_scene_id == "forest_path"
    assert engine.get_current_scene().id == "forest_path"

    for action, expected_scene in (
        ("Talk", "squirrel_help"),
        ("Sword", "cut_thorns"),
        ("Hide", "ignore_squirrel"),
    ):
        branch = StoryEngine(loader)
        branch.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
        branch.handle_card(_action_card("Run", uid="run1"))
        result = branch.handle_card(_action_card(action))
        assert result.outcome == EngineOutcome.SUCCESS, result.message
        assert result.previous_scene_id == "forest_path"
        assert result.new_scene_id == expected_scene


def test_benny_choice_lookup_is_case_insensitive() -> None:
    """Action names match scene choice keys regardless of casing."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    engine.handle_card(_action_card("Run", uid="run1"))

    result = engine.handle_card(_action_card("sword"))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "cut_thorns"


def test_resolve_choice_key_never_uses_choice_labels() -> None:
    """Display labels must not be treated as engine action keys."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    story = loader.load_story("benny")
    scene = story.get_scene("forest_path")

    assert StoryEngine._resolve_choice_key(scene, "💬 Talk — Help the crying squirrel") is None
    assert StoryEngine._resolve_choice_key(scene, "Talk") == "Talk"


def test_branching_different_choices_lead_to_different_scenes(
    story_engine: StoryEngine,
) -> None:
    story_engine.handle_card(_story_card())

    north_result = story_engine.handle_card(_action_card("Go North"))
    assert north_result.new_scene_id == "north"

    story_engine.handle_card(_system_card())
    story_engine.handle_card(_story_card())

    south_result = story_engine.handle_card(_action_card("Go South"))
    assert south_result.new_scene_id == "south"
    assert south_result.new_scene_id != north_result.new_scene_id


def test_ending_scene_returns_story_ended(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    story_engine.handle_card(_action_card("Go South"))
    result = story_engine.handle_card(_action_card("Go South"))
    assert result.outcome == EngineOutcome.STORY_ENDED
    assert result.ending_id == "bad"
    assert result.new_scene_id == "swamp_end"
    assert story_engine.get_state().is_ended


def test_restart_via_system_card(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    story_engine.handle_card(_action_card("Go North"))
    assert story_engine.get_current_scene().id == "north"

    result = story_engine.handle_card(_system_card())
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.new_scene_id == "start"
    assert story_engine.get_state().inventory.items == []
    assert not story_engine.get_state().is_ended


def test_missing_required_items_blocks_transition(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    result = story_engine.handle_card(_action_card("Climb"))
    assert result.outcome == EngineOutcome.MISSING_ITEMS
    assert "Map" in result.message
    assert story_engine.get_current_scene().id == "start"


def test_gained_items_on_scene_entry(story_engine: StoryEngine) -> None:
    story_engine.handle_card(_story_card())
    story_engine.handle_card(_action_card("Go North"))
    assert "Map" in story_engine.get_state().inventory.items

    result = story_engine.handle_card(_action_card("Go North"))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "peak"


def test_unknown_card_returns_unknown_card(story_engine: StoryEngine) -> None:
    result = story_engine.handle_card(UnknownCard(uid="DEADBEEF"))
    assert result.outcome == EngineOutcome.UNKNOWN_CARD


@pytest.mark.parametrize(
    "card_name,story_id,title,start_scene",
    [
        ("Benny", "benny", "Benny and the Lost Crystal", "bunny_home"),
        ("Mina", "mina", "Mina and the Missing Moon Lantern", "school_yard"),
        ("Nova", "nova", "Nova and the Friendly Star", "bedroom"),
    ],
)
def test_production_story_cards_start_matching_stories(
    card_name: str,
    story_id: str,
    title: str,
    start_scene: str,
) -> None:
    """Benny, Mina, and Nova story cards start the correct children's stories."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    result = engine.handle_card(
        Card(uid="TEST", name=card_name, type=CardType.STORY)
    )
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.story_id == story_id
    assert result.new_scene_id == start_scene

    active_story = loader.load_story(result.story_id)
    assert active_story.title == title
    assert title in result.message


@pytest.mark.parametrize(
    "card_name,story_id,title",
    [
        ("benny and the lost crystal", "benny", "Benny and the Lost Crystal"),
        ("MINA AND THE MISSING MOON LANTERN", "mina", "Mina and the Missing Moon Lantern"),
        ("Nova and the Friendly Star", "nova", "Nova and the Friendly Star"),
    ],
)
def test_story_card_matches_full_title_case_insensitive(
    card_name: str,
    story_id: str,
    title: str,
) -> None:
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    result = engine.handle_card(
        Card(uid="TITLE", name=card_name, type=CardType.STORY)
    )
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.story_id == story_id
    assert loader.load_story(story_id).title == title


@pytest.mark.parametrize("legacy_name", ["Fantasy", "Mystery", "Space"])
def test_legacy_genre_story_cards_do_not_start_stories(legacy_name: str) -> None:
    """Legacy demo card names must not match or default to any production story."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    result = engine.handle_card(
        Card(uid="LEGACY", name=legacy_name, type=CardType.STORY)
    )
    assert result.outcome == EngineOutcome.STORY_NOT_FOUND
    assert not engine.is_story_active()


def test_story_card_ignored_when_story_already_active() -> None:
    """Rescanning a story card mid-game must not reset to the start scene."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    engine.handle_card(_action_card("Run", uid="run1"))
    assert engine.get_current_scene().id == "forest_path"

    result = engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    assert result.outcome == EngineOutcome.STORY_ALREADY_ACTIVE
    assert engine.get_current_scene().id == "forest_path"


@pytest.mark.parametrize(
    "first_card,second_card,expected_story_id,expected_start_scene",
    [
        ("Benny", "Mina", "mina", "school_yard"),
        ("Benny", "Nova", "nova", "bedroom"),
        ("Mina", "Benny", "benny", "bunny_home"),
        ("Mina", "Nova", "nova", "bedroom"),
        ("Nova", "Mina", "mina", "school_yard"),
    ],
)
def test_different_story_card_switches_active_story(
    first_card: str,
    second_card: str,
    expected_story_id: str,
    expected_start_scene: str,
) -> None:
    """Scanning a different story card must start that story, not keep the first."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    engine.handle_card(Card(uid="S1", name=first_card, type=CardType.STORY))
    assert engine.get_state().story_id is not None

    result = engine.handle_card(Card(uid="S2", name=second_card, type=CardType.STORY))
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.story_id == expected_story_id
    assert result.story_id != first_card.casefold()
    assert engine.get_state().story_id == expected_story_id
    assert engine.get_current_scene() is not None
    assert engine.get_current_scene().id == expected_start_scene


def test_mina_card_never_starts_benny_story() -> None:
    """Regression: Mina must never resolve to Benny's story."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")
    engine = StoryEngine(loader)

    result = engine.handle_card(Card(uid="B1C2D3E4", name="Mina", type=CardType.STORY))
    assert result.outcome == EngineOutcome.STORY_STARTED
    assert result.story_id == "mina"
    assert result.story_id != "benny"
    assert engine.get_current_scene().id == "school_yard"


def test_benny_forest_path_actions_do_not_reset_story() -> None:
    """Action cards at forest_path advance the story instead of returning home."""
    loader = StoryLoader(Path(__file__).resolve().parent.parent / "stories")

    for action, expected_scene in (
        ("Hide", "ignore_squirrel"),
        ("Sword", "cut_thorns"),
        ("Talk", "squirrel_help"),
    ):
        engine = StoryEngine(loader)
        engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
        engine.handle_card(_action_card("Run", uid="run1"))
        assert engine.get_current_scene().id == "forest_path"

        result = engine.handle_card(_action_card(action))
        assert result.outcome == EngineOutcome.SUCCESS, result.message
        assert result.new_scene_id == expected_scene
        assert engine.get_current_scene().id != "bunny_home"
