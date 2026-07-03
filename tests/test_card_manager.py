"""Tests for card_manager.CardManager and UID normalization."""

from __future__ import annotations

import json

import pytest

from card_manager import CardManager, CardType, UnknownCard, normalize_uid


def test_valid_uid_lookup(card_manager: CardManager) -> None:
    card = card_manager.get_card_by_uid("A1B2C3D4")
    assert card.name == "Test Story"
    assert card.type == CardType.STORY
    assert card_manager.is_known_card("A1B2C3D4")


def test_unknown_uid_returns_unknown_card(card_manager: CardManager) -> None:
    card = card_manager.get_card_by_uid("FFFFFFFF")
    assert isinstance(card, UnknownCard)
    assert card.name == "Unknown"
    assert card.type == "unknown"
    assert not card_manager.is_known_card("FFFFFFFF")


def test_uid_normalization_lowercase_and_spaces(card_manager: CardManager) -> None:
    assert normalize_uid("a1b2 c3d4") == "A1B2C3D4"
    card = card_manager.get_card_by_uid("a1b2 c3d4")
    assert card.name == "Test Story"
    assert card.uid == "A1B2C3D4"


def test_reload_cards_picks_up_file_changes(cards_path, card_manager: CardManager) -> None:
    updated = {
        "A1B2C3D4": {"name": "Updated Story", "type": "story"},
        "AABBCCDD": {"name": "New Action", "type": "action"},
    }
    cards_path.write_text(json.dumps(updated), encoding="utf-8")
    card_manager.reload_cards()

    card = card_manager.get_card_by_uid("A1B2C3D4")
    assert card.name == "Updated Story"

    new_card = card_manager.get_card_by_uid("AABBCCDD")
    assert new_card.name == "New Action"
    assert new_card.type == CardType.ACTION

    assert card_manager.get_card_by_uid("11223344").name == "Unknown"
