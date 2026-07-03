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

    inputs = iter(["Fantasy", "Sword", "quit"])
    output = StringIO()

    with patch("sys.stdout", output):
        run_cli(debug=False, input_fn=lambda _prompt: next(inputs))

    text = output.getvalue()
    assert "Fantasy Quest" in text or "Fantasy" in text
    assert "Inventory" in text
    assert "Goodbye." in text


def test_run_cli_unknown_card_shows_error():
    from main import run_cli

    inputs = iter(["Not A Real Card", "quit"])
    output = StringIO()

    with patch("sys.stdout", output):
        run_cli(debug=False, input_fn=lambda _prompt: next(inputs))

    assert "ERROR: Unknown card" in output.getvalue()
