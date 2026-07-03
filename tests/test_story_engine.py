"""Tests for story_engine.StoryEngine card-driven state machine."""

from __future__ import annotations

from card_manager import Card, CardType, UnknownCard
from story_engine import EngineOutcome, StoryEngine


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
    assert "not available" in result.message


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
