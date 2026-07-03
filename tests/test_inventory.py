"""Tests for story_engine.Inventory."""

from __future__ import annotations

from story_engine import Inventory


def test_add_item() -> None:
    inv = Inventory()
    assert inv.add_item("Sword") is True
    assert inv.has_item("Sword")
    assert "Sword" in inv.items


def test_remove_item() -> None:
    inv = Inventory(["Sword", "Key"])
    assert inv.remove_item("Sword") is True
    assert not inv.has_item("Sword")
    assert inv.has_item("Key")


def test_remove_missing_item_returns_false() -> None:
    inv = Inventory()
    assert inv.remove_item("Shield") is False


def test_duplicate_add_prevention() -> None:
    inv = Inventory()
    assert inv.add_item("Key") is True
    assert inv.add_item("Key") is False
    assert inv.items == ["Key"]


def test_has_item() -> None:
    inv = Inventory(["Map"])
    assert inv.has_item("Map")
    assert inv.has_item("  Map  ")
    assert not inv.has_item("Compass")


def test_has_all() -> None:
    inv = Inventory(["Sword", "Key", "Map"])
    assert inv.has_all(["Sword", "Key"])
    assert not inv.has_all(["Sword", "Shield"])


def test_reset() -> None:
    inv = Inventory(["Sword", "Key"])
    inv.reset()
    assert inv.items == []
    assert not inv.has_item("Sword")
