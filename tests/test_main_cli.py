"""Tests for main.py CLI mode and argument parsing."""

from __future__ import annotations

import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_parse_args_accepts_cli_and_debug():
    from main import parse_args

    args = parse_args(["--cli", "--debug"])
    assert args.cli is True
    assert args.debug is True
    assert args.hardware is False


def test_parse_args_accepts_hardware():
    from main import parse_args

    args = parse_args(["--hardware"])
    assert args.cli is False
    assert args.hardware is True
    assert args.debug is False


def test_parse_args_default_mode():
    from main import parse_args

    args = parse_args([])
    assert args.cli is False
    assert args.debug is False
    assert args.hardware is False


def test_cli_mode_avoids_tkinter_import():
    """CLI dispatch must not load tkinter (subprocess isolation)."""
    code = """
import sys
sys.argv = ["main.py", "--cli", "--debug"]
import main
main.run_cli = lambda debug=False, input_fn=input: None
main.main()
assert "tkinter" not in sys.modules, sorted(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_find_card_by_name_case_insensitive():
    from card_manager import CardManager
    from main import find_card_by_name

    manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    card = find_card_by_name(manager, "open door")
    assert card is not None
    assert card.name == "Open Door"


def test_run_cli_with_mocked_input():
    from main import run_cli

    inputs = iter(["Benny", "Talk", "quit"])
    output = StringIO()

    with patch("sys.stdout", output):
        run_cli(debug=False, input_fn=lambda _prompt: next(inputs))

    text = output.getvalue()
    assert "Benny and the Lost Crystal" in text
    assert "Mina and the Missing Moon Lantern" in text
    assert "Nova and the Friendly Star" in text
    assert "Benny" in text or "rabbit" in text.lower()
    assert "Inventory" in text
    assert "Goodbye." in text


def test_run_cli_unknown_card_shows_error():
    from main import run_cli

    inputs = iter(["Not A Real Card", "quit"])
    output = StringIO()

    with patch("sys.stdout", output):
        run_cli(debug=False, input_fn=lambda _prompt: next(inputs))

    assert "ERROR: Unknown card" in output.getvalue()


def test_run_cli_rejects_legacy_demo_story_cards():
    from main import run_cli

    inputs = iter(["Fantasy", "Mystery", "Space", "quit"])
    output = StringIO()

    with patch("sys.stdout", output):
        run_cli(debug=False, input_fn=lambda _prompt: next(inputs))

    text = output.getvalue()
    assert text.count("ERROR: Unknown card") == 3


def test_collect_story_titles_shows_three_production_stories():
    from main import collect_story_titles, init_story_loader

    story_loader, loaded_count, error = init_story_loader()
    assert error is None
    assert loaded_count == 3

    titles = collect_story_titles(story_loader)
    assert titles == [
        "Benny and the Lost Crystal",
        "Mina and the Missing Moon Lantern",
        "Nova and the Friendly Star",
    ]


def test_production_story_cards_in_registry_are_unique():
    """Each production story card has a unique UID and correct name."""
    from card_manager import CardManager, CardType

    manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    story_cards = manager.get_cards_by_type(CardType.STORY)

    assert len(story_cards) == 3
    assert len({card.uid for card in story_cards}) == 3

    names = {card.name for card in story_cards}
    assert names == {"Benny", "Mina", "Nova"}


def test_cli_story_cards_start_correct_titles():
    """CLI path: Benny/Mina/Nova cards load matching story titles."""
    from card_manager import CardManager
    from main import find_card_by_name, init_story_loader
    from story_engine import EngineOutcome, StoryEngine

    card_manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    story_loader, _, _ = init_story_loader()

    for card_name, expected_title in (
        ("Benny", "Benny and the Lost Crystal"),
        ("Mina", "Mina and the Missing Moon Lantern"),
        ("Nova", "Nova and the Friendly Star"),
    ):
        engine = StoryEngine(story_loader)
        card = find_card_by_name(card_manager, card_name)
        assert card is not None
        result = engine.handle_card(card)
        assert result.outcome == EngineOutcome.STORY_STARTED
        assert story_loader.load_story(result.story_id).title == expected_title


def test_collect_story_entries_maps_titles_to_card_names():
    """Start screen entries must pair each title with its NFC story card name."""
    from card_manager import CardManager
    from main import collect_story_entries, init_story_loader

    card_manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    story_loader, _, _ = init_story_loader()

    entries = collect_story_entries(story_loader, card_manager)
    assert entries == [
        ("Benny and the Lost Crystal", "Benny"),
        ("Mina and the Missing Moon Lantern", "Mina"),
        ("Nova and the Friendly Star", "Nova"),
    ]


def test_registry_story_cards_on_shared_engine_switch_stories():
    """Regression: sequential Benny/Mina/Nova scans must not all stay on Benny."""
    from card_manager import CardManager
    from main import find_card_by_name, init_story_loader
    from story_engine import EngineOutcome, StoryEngine

    card_manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    story_loader, _, _ = init_story_loader()
    engine = StoryEngine(story_loader)

    expected = (
        ("Benny", "benny", "bunny_home"),
        ("Mina", "mina", "school_yard"),
        ("Nova", "nova", "bedroom"),
    )
    for card_name, story_id, start_scene in expected:
        card = find_card_by_name(card_manager, card_name)
        assert card is not None
        result = engine.handle_card(card)
        assert result.outcome == EngineOutcome.STORY_STARTED, card_name
        assert result.story_id == story_id, card_name
        assert result.story_id != "benny" or card_name == "Benny"
        assert engine.get_current_scene().id == start_scene


def test_simulate_path_mina_after_benny_does_not_stay_on_benny():
    """App simulate path: scanning Mina after Benny must switch to Mina's story."""
    from card_manager import CardManager
    from main import GameApplication, init_story_loader
    from story_engine import EngineOutcome, StoryEngine

    card_manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    story_loader, _, _ = init_story_loader()
    engine = StoryEngine(story_loader)

    app = object.__new__(GameApplication)
    app._card_manager = card_manager
    app._story_engine = engine
    app._story_loader = story_loader
    app._last_inventory = ()
    app._log_active_scene_choices = lambda **kwargs: None

    class _NoOpUI:
        def set_last_scanned(self, *_args: object, **_kwargs: object) -> None:
            return None

        def set_status(self, *_args: object, **_kwargs: object) -> None:
            return None

        def show_error(self, *_args: object, **_kwargs: object) -> None:
            return None

        def show_start_screen(self) -> None:
            return None

        def show_scene(self, **_kwargs: object) -> None:
            return None

        def show_ending(self, **_kwargs: object) -> None:
            return None

    app._ui = _NoOpUI()
    app._apply_engine_result = GameApplication._apply_engine_result.__get__(app, GameApplication)

    app._simulate_card_by_name("Benny")
    assert engine.get_state().story_id == "benny"

    app._simulate_card_by_name("Mina")
    assert engine.get_state().story_id == "mina"
    assert engine.get_state().story_id != "benny"
    assert engine.get_current_scene() is not None
    assert engine.get_current_scene().id == "school_yard"


def test_resolve_card_for_action_uses_registry_card_type():
    from card_manager import CardManager
    from main import GameApplication, find_card_by_name

    manager = CardManager(PROJECT_ROOT / "data" / "cards.json")
    key_card = find_card_by_name(manager, "Key")
    assert key_card is not None
    assert key_card.type.value == "item"

    app = object.__new__(GameApplication)
    app._card_manager = manager
    resolved = app._resolve_card_for_action("Key")
    assert resolved.name == "Key"
    assert resolved.type.value == "item"
