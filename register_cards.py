#!/usr/bin/env python3
"""
Interactive CLI tool for registering physical NFC cards.

Reads UIDs from the Arduino RC522 reader over serial and writes the
UID → card mapping to ``data/cards.json``.
"""

from __future__ import annotations

import argparse
import json
import logging
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from serial_reader import SerialReader, find_arduino_port, is_valid_uid

logger = logging.getLogger(__name__)

DEFAULT_CARDS_PATH = Path("data/cards.json")
DEFAULT_BAUD = 115200

VALID_CARD_TYPES = frozenset({"story", "action", "item", "system"})

CARDS_TO_REGISTER: list[tuple[str, str]] = [
    ("Benny", "story"),
    ("Mina", "story"),
    ("Nova", "story"),
    ("Sword", "action"),
    ("Magic", "action"),
    ("Shield", "action"),
    ("Run", "action"),
    ("Key", "action"),
    ("Talk", "action"),
    ("Hide", "action"),
    ("Open Door", "action"),
    ("Restart", "system"),
]


def normalize_uid(raw: str) -> str:
    """
    Normalize a raw UID string for consistent storage and lookup.

    Strips whitespace, uppercases, and removes spaces and colons.
    """
    return raw.strip().upper().replace(" ", "").replace(":", "")


def load_cards(path: Path) -> dict[str, dict[str, str]]:
    """
    Load the card registry from *path*.

    Creates ``data/`` and an empty registry file when missing.

    Returns:
        Mapping of normalized UID → ``{"name": ..., "type": ...}``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.is_file():
        logger.info("Creating empty card registry at %s", path)
        path.write_text("{}\n", encoding="utf-8")
        return {}

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read %s: %s", path, exc)
        raise SystemExit(1) from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Malformed JSON in %s: %s", path, exc)
        raise SystemExit(1) from exc

    if not isinstance(data, dict):
        logger.error("Card registry must be a JSON object, got %s", type(data).__name__)
        raise SystemExit(1)

    cards: dict[str, dict[str, str]] = {}
    for raw_uid, entry in data.items():
        uid = normalize_uid(str(raw_uid))
        if not uid or not is_valid_uid(uid):
            logger.warning("Skipping invalid UID key: %r", raw_uid)
            continue
        if not isinstance(entry, dict):
            logger.warning("Skipping UID %s: expected object, got %s", uid, type(entry).__name__)
            continue
        name = entry.get("name")
        card_type = entry.get("type")
        if not isinstance(name, str) or not isinstance(card_type, str):
            logger.warning("Skipping UID %s: missing name or type", uid)
            continue
        cards[uid] = {"name": name.strip(), "type": card_type.strip().lower()}

    return cards


def validate_cards_structure(cards: dict[str, dict[str, str]]) -> None:
    """
    Validate the in-memory card registry before writing to disk.

    Raises:
        ValueError: If the structure is invalid.
    """
    if not isinstance(cards, dict):
        raise ValueError("Card registry must be a dict")

    seen_names: set[str] = set()
    for uid, entry in cards.items():
        if not is_valid_uid(uid):
            raise ValueError(f"Invalid UID key: {uid!r}")
        if not isinstance(entry, dict):
            raise ValueError(f"Entry for UID {uid} must be an object")
        name = entry.get("name")
        card_type = entry.get("type")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"UID {uid}: missing or invalid 'name'")
        if not isinstance(card_type, str) or card_type.strip().lower() not in VALID_CARD_TYPES:
            raise ValueError(f"UID {uid}: invalid 'type' {card_type!r}")
        normalized_name = name.strip()
        if normalized_name in seen_names:
            raise ValueError(f"Duplicate card name in registry: {normalized_name!r}")
        seen_names.add(normalized_name)


def save_cards(path: Path, cards: dict[str, dict[str, str]], *, backup: bool = True) -> None:
    """
    Persist the card registry to *path*, optionally backing up the previous file.

    Rebuilds the JSON object keyed by UID (one UID per card name).

    Args:
        path: Destination JSON file.
        cards: UID → ``{name, type}`` mapping.
        backup: When True and the file exists, copy it to a timestamped backup first.
    """
    validate_cards_structure(cards)

    path.parent.mkdir(parents=True, exist_ok=True)

    if backup and path.is_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.parent / f"cards_backup_{timestamp}.json"
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info("Backed up existing registry to %s", backup_path)
        print(f"Backup saved: {backup_path}")

    # Rebuild UID-keyed dict with stable ordering (sorted by card name for readability).
    output: dict[str, dict[str, str]] = {}
    for uid in sorted(cards.keys(), key=lambda u: cards[u]["name"].lower()):
        entry = cards[uid]
        output[uid] = {"name": entry["name"], "type": entry["type"]}

    serialized = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    # Round-trip validate before write.
    json.loads(serialized)

    path.write_text(serialized, encoding="utf-8")
    logger.info("Saved %d card(s) to %s", len(output), path)


def find_uid_for_name(cards: dict[str, dict[str, str]], name: str) -> str | None:
    """Return the UID currently mapped to *name*, or None if not registered."""
    target = name.strip().lower()
    for uid, entry in cards.items():
        if entry.get("name", "").strip().lower() == target:
            return uid
    return None


def find_name_for_uid(cards: dict[str, dict[str, str]], uid: str) -> str | None:
    """Return the card name mapped to *uid*, or None if unknown."""
    entry = cards.get(normalize_uid(uid))
    if entry is None:
        return None
    return entry.get("name")


def print_summary_table(cards: dict[str, dict[str, str]]) -> None:
    """Print a UID | Name | Type summary table."""
    if not cards:
        print("\nNo cards registered.")
        return

    rows = sorted(
        ((uid, entry["name"], entry["type"]) for uid, entry in cards.items()),
        key=lambda row: row[1].lower(),
    )

    uid_width = max(len("UID"), max(len(uid) for uid, _, _ in rows))
    name_width = max(len("Name"), max(len(name) for _, name, _ in rows))
    type_width = max(len("Type"), max(len(card_type) for _, _, card_type in rows))

    header = f"{'UID'.ljust(uid_width)} | {'Name'.ljust(name_width)} | {'Type'.ljust(type_width)}"
    separator = "-" * len(header)
    print(f"\n{header}")
    print(separator)
    for uid, name, card_type in rows:
        print(f"{uid.ljust(uid_width)} | {name.ljust(name_width)} | {card_type.ljust(type_width)}")


def _prompt_yes_no(message: str, *, default: bool = False) -> bool:
    """Read a yes/no answer from stdin."""
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        answer = input(f"{message}{suffix}: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def _remove_uid(cards: dict[str, dict[str, str]], uid: str) -> None:
    """Remove a UID entry after user confirmation elsewhere."""
    cards.pop(normalize_uid(uid), None)


def _register_uid_for_card(
    cards: dict[str, dict[str, str]],
    card_name: str,
    card_type: str,
    uid: str,
) -> None:
    """Assign *uid* to *card_name*, removing any previous UID for that name."""
    uid = normalize_uid(uid)
    existing_uid = find_uid_for_name(cards, card_name)
    if existing_uid and existing_uid != uid:
        _remove_uid(cards, existing_uid)
    # If this UID was mapped to another name, caller must have confirmed removal.
    if uid in cards and cards[uid]["name"] != card_name:
        _remove_uid(cards, uid)
    cards[uid] = {"name": card_name, "type": card_type}


class _UIDListener:
    """Collects UIDs from :class:`SerialReader` into a thread-safe queue."""

    def __init__(self) -> None:
        """Initialize an empty UID queue."""
        self._queue: queue.Queue[str] = queue.Queue()

    def on_uid(self, uid: str) -> None:
        """Enqueue a validated UID from the serial reader callback."""
        self._queue.put(uid)

    def wait_for_uid(self, timeout: float = 120.0) -> str | None:
        """Block until a UID arrives or *timeout* seconds elapse."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


def wait_for_card_scan(
    listener: _UIDListener,
    card_name: str,
    *,
    timeout: float = 120.0,
) -> str | None:
    """
    Prompt the user to scan a card and wait for a UID.

    Returns:
        Normalized UID string, or None if the user skips or times out.
    """
    print(f'Scan the [{card_name}] card now... (type "s" + Enter to skip)')

    skip_requested = threading.Event()
    result: list[str | None] = [None]
    done = threading.Event()

    def stdin_reader() -> None:
        try:
            line = sys.stdin.readline()
            if line.strip().lower() == "s":
                skip_requested.set()
                done.set()
        except (EOFError, OSError):
            pass

    def uid_waiter() -> None:
        deadline = threading.Timer(timeout, lambda: done.set())
        deadline.daemon = True
        deadline.start()
        while not skip_requested.is_set() and not done.is_set():
            try:
                uid = listener._queue.get(timeout=0.5)
                result[0] = uid
                done.set()
                deadline.cancel()
                return
            except queue.Empty:
                continue
        deadline.cancel()

    threading.Thread(target=stdin_reader, daemon=True).start()
    threading.Thread(target=uid_waiter, daemon=True).start()

    print("Waiting for NFC scan", end="", flush=True)
    while not done.is_set():
        done.wait(timeout=0.5)
        print(".", end="", flush=True)
    print()

    if skip_requested.is_set():
        return None

    uid = result[0]
    if uid is None:
        print("Timed out waiting for scan.")
        return None

    return normalize_uid(uid)


def process_scan(
    cards: dict[str, dict[str, str]],
    card_name: str,
    card_type: str,
    uid: str,
) -> str:
    """
    Validate a scanned UID against the registry and apply updates.

    Returns:
        ``"ok"`` when registered, ``"retry"`` to scan again, ``"skip"`` to skip.
    """
    uid = normalize_uid(uid)
    if not is_valid_uid(uid):
        print(f"Invalid UID format: {uid!r}. Try again.")
        return "retry"

    existing_name = find_name_for_uid(cards, uid)
    if existing_name is not None and existing_name != card_name:
        print(
            f"Warning: UID {uid} is already mapped to '{existing_name}', "
            f"not '{card_name}'."
        )
        print("Scan a different physical card, or register that card first.")
        return "retry"

    existing_uid = find_uid_for_name(cards, card_name)
    if existing_uid is not None and existing_uid != uid:
        print(f"'{card_name}' is currently registered as UID {existing_uid}.")
        if not _prompt_yes_no(f"Replace with new UID {uid}?"):
            return "retry"
        if not _prompt_yes_no(
            f"Confirm: remove old mapping {existing_uid} → {card_name}?"
        ):
            return "retry"
        _remove_uid(cards, existing_uid)

    if existing_name == card_name and existing_uid == uid:
        print(f"'{card_name}' already registered as {uid} (unchanged).")
        return "ok"

    _register_uid_for_card(cards, card_name, card_type, uid)
    print(f"Registered [{card_name}] → {uid} ({card_type})")
    return "ok"


def register_card_interactive(
    cards: dict[str, dict[str, str]],
    listener: _UIDListener,
    card_name: str,
    card_type: str,
) -> bool:
    """
    Guided registration loop for a single card.

    Returns:
        True if the card was registered (or already correct), False if skipped.
    """
    print(f"\n--- Register: {card_name} ({card_type}) ---")

    while True:
        uid = wait_for_card_scan(listener, card_name)
        if uid is None:
            return False

        outcome = process_scan(cards, card_name, card_type, uid)
        if outcome == "ok":
            return True
        if outcome == "skip":
            return False
        # retry: loop again


def run_registration(
    cards: dict[str, dict[str, str]],
    listener: _UIDListener,
    targets: list[tuple[str, str]],
) -> None:
    """Run guided registration for each card in *targets*."""
    total = len(targets)
    for index, (card_name, card_type) in enumerate(targets, start=1):
        print(f"\n[{index}/{total}] Next card: {card_name} ({card_type})")
        register_card_interactive(cards, listener, card_name, card_type)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Register physical NFC cards for the Tangible NFC Interactive Storybook.",
    )
    parser.add_argument(
        "--port",
        help="Serial port (e.g. /dev/ttyUSB0, COM3). Auto-detected when omitted.",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Serial baud rate (default: {DEFAULT_BAUD}).",
    )
    parser.add_argument(
        "--cards-path",
        type=Path,
        default=DEFAULT_CARDS_PATH,
        help=f"Path to cards.json (default: {DEFAULT_CARDS_PATH}).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show current card mappings and exit.",
    )
    parser.add_argument(
        "--card",
        metavar="NAME",
        help="Register a single card by name (e.g. Benny).",
    )
    return parser


def resolve_targets(card_name: str | None) -> list[tuple[str, str]]:
    """Return the list of cards to register based on CLI options."""
    if card_name is None:
        return list(CARDS_TO_REGISTER)

    target_lower = card_name.strip().lower()
    for name, card_type in CARDS_TO_REGISTER:
        if name.lower() == target_lower:
            return [(name, card_type)]

    known = ", ".join(name for name, _ in CARDS_TO_REGISTER)
    raise SystemExit(f"Unknown card {card_name!r}. Known cards: {known}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cards = load_cards(args.cards_path)

    if args.list:
        print(f"Card registry: {args.cards_path}")
        print_summary_table(cards)
        return 0

    targets = resolve_targets(args.card)

    port = args.port or find_arduino_port()
    if port is None:
        print(
            "No Arduino serial port found. Connect the board and try again,\n"
            "or pass --port explicitly (e.g. --port /dev/tty.usbmodem14101 or COM3)."
        )
        return 1

    print("=== NFC Card Registration ===")
    print(f"Serial port: {port} @ {args.baud} baud")
    print(f"Registry: {args.cards_path}")
    if len(targets) == 1:
        print(f"Mode: single card ({targets[0][0]})")
    else:
        print(f"Mode: guided registration ({len(targets)} cards)")

    listener = _UIDListener()
    reader = SerialReader(on_uid=listener.on_uid, port=port, baud_rate=args.baud)
    reader.start()

    if not reader.connect():
        print(f"Failed to open serial port {port}. Check wiring and permissions.")
        reader.stop()
        return 1

    print("Serial reader connected. Place cards on the RC522 reader when prompted.\n")

    try:
        run_registration(cards, listener, targets)
    except KeyboardInterrupt:
        print("\n\nRegistration interrupted.")
        if cards and _prompt_yes_no("Save progress so far?", default=True):
            save_cards(args.cards_path, cards)
        return 130
    finally:
        reader.stop()

    if not cards:
        print("\nNo cards were registered. Registry unchanged.")
        return 0

    print("\n=== Registration complete ===")
    print_summary_table(cards)

    save_cards(args.cards_path, cards)
    print(f"Card registry saved to {args.cards_path}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
