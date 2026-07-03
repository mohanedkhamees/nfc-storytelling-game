"""UID-to-card mapping for the Tangible NFC Story Game.

Loads card definitions from ``data/cards.json`` and maps raw NFC UIDs
(from :mod:`serial_reader`) to structured :class:`Card` objects.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CardType(str, Enum):
    """Supported card categories used by the story engine and application."""

    STORY = "story"
    ACTION = "action"
    ITEM = "item"
    SYSTEM = "system"


_VALID_CARD_TYPES = {member.value for member in CardType}


@dataclass(frozen=True)
class Card:
    """A registered NFC card with a known UID, display name, and type."""

    uid: str
    name: str
    type: CardType


@dataclass(frozen=True)
class UnknownCard:
    """Placeholder returned when a scanned UID is not in the card registry."""

    uid: str
    name: str = "Unknown"
    type: str = "unknown"


def normalize_uid(uid: str) -> str:
    """Normalize a raw UID string for consistent lookup (uppercase, no spaces)."""
    return uid.strip().upper().replace(" ", "")


class CardManager:
    """Loads and queries the UID → card mapping from ``data/cards.json``."""

    def __init__(self, cards_path: Path | str = "data/cards.json") -> None:
        """Initialize the manager and load card definitions from disk.

        Args:
            cards_path: Path to the JSON card registry file.
        """
        self._cards_path = Path(cards_path)
        self._cards: dict[str, Card] = {}
        self.reload_cards()

    def reload_cards(self) -> None:
        """Re-read the card registry from disk (supports hot-reload during development)."""
        loaded = self._load_cards_from_file()
        if loaded is not None:
            self._cards = loaded

    def get_card_by_uid(self, uid: str) -> Card | UnknownCard:
        """Return the card for a UID, or :class:`UnknownCard` if not registered."""
        normalized = normalize_uid(uid)
        card = self._cards.get(normalized)
        if card is None:
            return UnknownCard(uid=normalized)
        return card

    def is_known_card(self, uid: str) -> bool:
        """Return whether the UID is present in the card registry."""
        return normalize_uid(uid) in self._cards

    def get_all_cards(self) -> dict[str, Card]:
        """Return a copy of the full UID → card mapping."""
        return dict(self._cards)

    def get_cards_by_type(self, card_type: CardType) -> list[Card]:
        """Return all registered cards matching the given type."""
        return [card for card in self._cards.values() if card.type == card_type]

    def _load_cards_from_file(self) -> dict[str, Card] | None:
        """Parse the JSON registry file. Returns ``None`` on unrecoverable errors."""
        if not self._cards_path.is_file():
            logger.error("Card registry not found: %s", self._cards_path)
            return {}

        try:
            raw_text = self._cards_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to read card registry %s: %s", self._cards_path, exc)
            return None

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in card registry %s: %s", self._cards_path, exc)
            return None

        if not isinstance(data, dict):
            logger.error(
                "Card registry %s must be a JSON object, got %s",
                self._cards_path,
                type(data).__name__,
            )
            return {}

        cards: dict[str, Card] = {}
        for raw_uid, entry in data.items():
            card = self._parse_card_entry(str(raw_uid), entry)
            if card is not None:
                cards[card.uid] = card

        logger.info("Loaded %d card(s) from %s", len(cards), self._cards_path)
        return cards

    def _parse_card_entry(self, raw_uid: str, entry: Any) -> Card | None:
        """Validate and parse a single card entry. Skips invalid entries with a warning."""
        normalized_uid = normalize_uid(raw_uid)
        if not normalized_uid:
            logger.warning("Skipping card entry with empty UID")
            return None

        if not isinstance(entry, dict):
            logger.warning(
                "Skipping UID %s: expected object with name and type, got %s",
                normalized_uid,
                type(entry).__name__,
            )
            return None

        name = entry.get("name")
        card_type_raw = entry.get("type")

        if not isinstance(name, str) or not name.strip():
            logger.warning("Skipping UID %s: missing or invalid 'name' field", normalized_uid)
            return None

        if not isinstance(card_type_raw, str):
            logger.warning("Skipping UID %s: missing or invalid 'type' field", normalized_uid)
            return None

        card_type_value = card_type_raw.strip().lower()
        if card_type_value not in _VALID_CARD_TYPES:
            logger.warning(
                "Skipping UID %s: unknown card type %r (expected one of %s)",
                normalized_uid,
                card_type_raw,
                ", ".join(sorted(_VALID_CARD_TYPES)),
            )
            return None

        return Card(
            uid=normalized_uid,
            name=name.strip(),
            type=CardType(card_type_value),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    manager = CardManager()

    print("=== CardManager demo ===\n")
    print(f"Loaded {len(manager.get_all_cards())} card(s) from data/cards.json\n")

    test_uids = [
        ("A1B2C3D4", "known story card (exact match)"),
        ("a1b2 c3d4", "known story card (lowercase + spaces)"),
        ("11223344", "known action card"),
        ("99AABBCC", "known item card"),
        ("DEADBEEF", "known story card (Mystery)"),
        ("FFFFFFFF", "unknown card"),
    ]

    for uid, description in test_uids:
        card = manager.get_card_by_uid(uid)
        known = manager.is_known_card(uid)
        print(f"UID {uid!r} ({description})")
        print(f"  is_known_card: {known}")
        print(f"  result: {card}")
        print()

    print("Cards by type:")
    for card_type in CardType:
        cards = manager.get_cards_by_type(card_type)
        names = [c.name for c in cards]
        print(f"  {card_type.value}: {names}")
