"""Application composition root for the Tangible NFC Story Game.

Wires serial I/O, card mapping, story engine, and Tkinter UI. All gameplay
logic stays in :mod:`story_engine`; this module only orchestrates callbacks
and marshals background-thread serial events onto the Tkinter main thread.

Use ``--cli`` to run a terminal REPL without importing Tkinter (macOS-safe).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from card_manager import Card, CardManager, CardType
from story_engine import EngineOutcome, EngineResult, StoryEngine
from story_loader import StoryLoadError, StoryLoader

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CARDS_PATH = PROJECT_ROOT / "data" / "cards.json"
DEFAULT_STORIES_DIR = PROJECT_ROOT / "stories"
DEFAULT_ASSETS_DIR = PROJECT_ROOT / "assets"

CLI_SUPPORTED_CARDS = [
    "Fantasy",
    "Mystery",
    "Space",
    "Sword",
    "Magic",
    "Shield",
    "Run",
    "Key",
    "Talk",
    "Hide",
    "Open Door",
    "Restart",
]

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def configure_logging(*, debug: bool = False) -> None:
    """Configure console logging with timestamps."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )


def init_card_manager() -> tuple[CardManager, str | None]:
    """Load card registry; return manager and optional user-facing error."""
    manager = CardManager(DEFAULT_CARDS_PATH)
    card_count = len(manager.get_all_cards())

    if not DEFAULT_CARDS_PATH.is_file():
        error = (
            f"Card registry not found: {DEFAULT_CARDS_PATH.name}. "
            "Add data/cards.json to register NFC cards."
        )
        logger.error("Card registry missing: %s", DEFAULT_CARDS_PATH)
        return manager, error

    if card_count == 0:
        error = (
            "No valid cards loaded from data/cards.json. "
            "Check the file format and try again."
        )
        logger.error("Card registry empty or invalid: %s", DEFAULT_CARDS_PATH)
        return manager, error

    logger.info("Loaded %d card(s) from %s", card_count, DEFAULT_CARDS_PATH)
    return manager, None


def init_story_loader() -> tuple[StoryLoader, int, str | None]:
    """Preload stories on startup and return loader, count, and optional error."""
    loader = StoryLoader(DEFAULT_STORIES_DIR)

    if not DEFAULT_STORIES_DIR.is_dir():
        error = f"Stories directory not found: {DEFAULT_STORIES_DIR.name}"
        logger.error("Stories directory missing: %s", DEFAULT_STORIES_DIR)
        return loader, 0, error

    available_ids = loader.list_available_stories()
    logger.info("Found %d story file(s) in %s", len(available_ids), DEFAULT_STORIES_DIR)

    loaded_count = 0
    for story_id in available_ids:
        try:
            loader.load_story(story_id)
            loaded_count += 1
        except (StoryLoadError, Exception) as exc:
            logger.error("Failed to load story %r: %s", story_id, exc)

    error: str | None = None
    if available_ids and loaded_count == 0:
        error = "Story files found but none could be loaded. Check stories/*.json."
    elif loaded_count:
        logger.info("Preloaded %d story/stories", loaded_count)

    return loader, loaded_count, error


def find_card_by_name(card_manager: CardManager, card_name: str) -> Card | None:
    """Return a registered card matching *card_name* (case-insensitive)."""
    normalized = card_name.strip().casefold()
    for card in card_manager.get_all_cards().values():
        if card.name.casefold() == normalized:
            return card
    return None


def collect_story_names(card_manager: CardManager, story_loader: StoryLoader) -> list[str]:
    """Return story card names for the start screen."""
    story_cards = card_manager.get_cards_by_type(CardType.STORY)
    names = sorted({card.name for card in story_cards})

    for story_id in story_loader.list_available_stories():
        try:
            story = story_loader.load_story(story_id)
            if story.title not in names:
                names.append(story.title)
        except Exception:
            logger.debug("Could not load story %s for start screen", story_id)

    if not names:
        names = ["Fantasy", "Mystery", "Space"]
    return names


def _get_active_story_title(story_loader: StoryLoader, story_engine: StoryEngine) -> str:
    """Return the display title of the active story, or a fallback string."""
    state = story_engine.get_state()
    if state.story_id is None:
        return "Story"

    cached = story_loader.get_cached_story(state.story_id)
    if cached is not None:
        return cached.title

    try:
        return story_loader.load_story(state.story_id).title
    except Exception:
        return state.story_id


def _log_engine_result(result: EngineResult, last_inventory: tuple[str, ...]) -> tuple[str, ...]:
    """Emit structured log lines for notable engine events; return updated inventory snapshot."""
    outcome = result.outcome

    if outcome == EngineOutcome.STORY_STARTED:
        logger.info(
            "Story started: %s (scene=%s)",
            result.story_id,
            result.new_scene_id,
        )
    elif outcome == EngineOutcome.STORY_ENDED:
        logger.info(
            "Story ended: %s (ending=%s)",
            result.story_id,
            result.ending_id,
        )
    elif outcome == EngineOutcome.SUCCESS and result.previous_scene_id is not None:
        logger.info(
            "Scene changed: %s → %s",
            result.previous_scene_id,
            result.new_scene_id,
        )
    elif outcome == EngineOutcome.INVALID_ACTION:
        logger.info("Invalid action: %s", result.message)
    elif outcome == EngineOutcome.UNKNOWN_CARD:
        logger.info("Unknown card: %s", result.message)
    elif outcome == EngineOutcome.MISSING_ITEMS:
        logger.info("Missing items: %s", result.message)
    elif outcome == EngineOutcome.STORY_NOT_FOUND:
        logger.error("Story not found: %s", result.message)

    inventory = result.inventory
    if inventory != last_inventory:
        logger.info("Inventory changed: %s", list(inventory) if inventory else "(empty)")
        return inventory
    return last_inventory


def _print_cli_start_screen(story_names: list[str]) -> None:
    print("\n=== Tangible NFC Story Game (CLI) ===")
    print("Scan a Story Card to begin.\n")
    print("Available stories:")
    for name in story_names:
        print(f"  • {name}")
    print("\nType a card name to simulate a scan (or 'quit' to exit).")
    print("Supported cards:", ", ".join(CLI_SUPPORTED_CARDS))


def _print_cli_scene(
    *,
    story_title: str,
    scene,
    inventory: list[str],
    choices: list[str],
) -> None:
    print(f"\n--- {story_title} ---")
    print(scene.text)
    if choices:
        print("\nChoices:")
        for choice in choices:
            print(f"  • {choice}")
    else:
        print("\nChoices: (none)")
    if inventory:
        print(f"\nInventory: {', '.join(inventory)}")
    else:
        print("\nInventory: (empty)")


def _print_cli_ending(*, story_title: str, scene, ending_id: str | None) -> None:
    print(f"\n--- {story_title} — ENDING ---")
    if ending_id:
        print(f"Ending: {ending_id}")
    else:
        print("The End")
    print(scene.text)
    print("\nScan Restart Card to play again.")


def _print_cli_error(message: str) -> None:
    print(f"\nERROR: {message}")


def _print_cli_status(message: str) -> None:
    print(f"\nStatus: {message}")


def _apply_cli_engine_result(
    result: EngineResult,
    *,
    card_manager: CardManager,
    story_loader: StoryLoader,
    story_engine: StoryEngine,
    last_inventory: tuple[str, ...],
) -> tuple[str, ...]:
    """Map engine outcomes to terminal output."""
    outcome = result.outcome
    updated_inventory = _log_engine_result(result, last_inventory)

    if outcome == EngineOutcome.UNKNOWN_CARD:
        _print_cli_error("Unknown card scanned.")
        return updated_inventory

    if outcome == EngineOutcome.INVALID_ACTION:
        _print_cli_error("This card cannot be used in the current scene.")
        return updated_inventory

    if outcome == EngineOutcome.MISSING_ITEMS:
        _print_cli_error(result.message)
        return updated_inventory

    if outcome == EngineOutcome.NO_STORY_LOADED:
        _print_cli_start_screen(collect_story_names(card_manager, story_loader))
        _print_cli_status(result.message)
        return updated_inventory

    if outcome == EngineOutcome.STORY_NOT_FOUND:
        _print_cli_error(result.message)
        return updated_inventory

    if outcome == EngineOutcome.STORY_ALREADY_ENDED:
        _print_cli_status(result.message)
        return updated_inventory

    if outcome == EngineOutcome.ITEM_CARD_IGNORED:
        _print_cli_status(result.message)
        if story_engine.is_story_active():
            scene = story_engine.get_current_scene()
            if scene is not None:
                state = story_engine.get_state()
                _print_cli_scene(
                    story_title=_get_active_story_title(story_loader, story_engine),
                    scene=scene,
                    inventory=list(state.inventory.items),
                    choices=sorted(scene.choices.keys()),
                )
        return updated_inventory

    if outcome in {EngineOutcome.STORY_STARTED, EngineOutcome.SUCCESS}:
        scene = story_engine.get_current_scene()
        if scene is None:
            return updated_inventory
        state = story_engine.get_state()
        if state.is_ended:
            _print_cli_ending(
                story_title=_get_active_story_title(story_loader, story_engine),
                scene=scene,
                ending_id=state.ending_id,
            )
        else:
            _print_cli_scene(
                story_title=_get_active_story_title(story_loader, story_engine),
                scene=scene,
                inventory=list(state.inventory.items),
                choices=sorted(scene.choices.keys()),
            )
        return updated_inventory

    if outcome == EngineOutcome.STORY_ENDED:
        scene = story_engine.get_current_scene()
        if scene is not None:
            state = story_engine.get_state()
            _print_cli_ending(
                story_title=_get_active_story_title(story_loader, story_engine),
                scene=scene,
                ending_id=state.ending_id,
            )
        return updated_inventory

    logger.error("Unhandled engine outcome: %s — %s", outcome.value, result.message)
    _print_cli_error(result.message)
    return updated_inventory


def run_cli(*, debug: bool = False, input_fn=input) -> None:
    """Run the game in terminal mode without Tkinter or Arduino."""
    configure_logging(debug=debug)
    logger.info("Starting Tangible NFC Story Game (CLI mode, debug=%s)", debug)

    card_manager, cards_error = init_card_manager()
    story_loader, _, story_error = init_story_loader()
    story_engine = StoryEngine(story_loader)

    if cards_error:
        _print_cli_error(cards_error)
    if story_error:
        _print_cli_error(story_error)

    story_names = collect_story_names(card_manager, story_loader)
    _print_cli_start_screen(story_names)

    last_inventory: tuple[str, ...] = ()

    while True:
        try:
            line = input_fn("\nCard> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        card_name = line.strip()
        if not card_name:
            continue
        if card_name.casefold() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break

        card = find_card_by_name(card_manager, card_name)
        if card is None:
            _print_cli_error(
                f"Unknown card {card_name!r}. Type a supported card name "
                f"(e.g. Open Door)."
            )
            continue

        logger.info("CLI simulate: %s (uid=%s)", card.name, card.uid)
        result = story_engine.handle_card(card)
        last_inventory = _apply_cli_engine_result(
            result,
            card_manager=card_manager,
            story_loader=story_loader,
            story_engine=story_engine,
            last_inventory=last_inventory,
        )


class GameApplication:
    """Composition root: constructs modules, wires callbacks, runs the GUI app."""

    def __init__(
        self,
        *,
        hardware_mode: bool = True,
        debug: bool = False,
    ) -> None:
        """Initialize all subsystems and wire event callbacks.

        Args:
            hardware_mode: When True, start :class:`SerialReader` for NFC input.
            debug: When True, enable the UI debug panel for simulated scans.
        """
        import tkinter as tk

        from asset_manager import AssetManager
        from serial_reader import SerialReader
        from ui import GameUI

        self._hardware_mode = hardware_mode and not debug
        self._debug = debug
        self._serial_reader: SerialReader | None = None
        self._last_inventory: tuple[str, ...] = ()

        logger.info("Creating Tkinter root window...")
        self._root = tk.Tk()
        logger.info("Tkinter root window created successfully")

        logger.info(
            "Starting Tangible NFC Story Game (hardware=%s, debug=%s)",
            self._hardware_mode,
            debug,
        )

        self._card_manager, self._cards_load_error = init_card_manager()
        self._story_loader, _, self._story_load_error = init_story_loader()
        self._asset_manager = AssetManager(project_root=PROJECT_ROOT)
        logger.info("Asset manager ready (project root: %s)", PROJECT_ROOT)

        self._story_engine = StoryEngine(self._story_loader)

        story_names = collect_story_names(self._card_manager, self._story_loader)

        self._ui = GameUI(
            self._root,
            DEFAULT_ASSETS_DIR,
            debug_mode=debug,
            story_names=story_names,
            asset_manager=self._asset_manager,
        )
        if debug:
            self._ui.register_simulate_callback(self._simulate_card_by_name)

        if self._cards_load_error:
            self._ui.show_error(self._cards_load_error)

        if self._story_load_error:
            self._ui.show_error(self._story_load_error)

        if self._hardware_mode:
            self._serial_reader = SerialReader(
                on_uid=self._on_uid,
                on_connection_change=self._on_connection_change,
            )
        else:
            self._ui.set_debug_mode(True)

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        """Start serial listening (if hardware mode) and enter the Tkinter event loop."""
        if self._hardware_mode and self._serial_reader is not None:
            self._serial_reader.start()
            connected = self._serial_reader.is_connected()
            self._ui.set_connection_status(connected)
            if not connected:
                logger.warning(
                    "No Arduino serial port detected — background reconnect active. "
                    "Use --debug to simulate cards without hardware."
                )
                self._ui.set_status(
                    "No NFC reader detected. Connect Arduino or restart with --debug."
                )
        else:
            logger.info("Debug mode: serial reader disabled; use the debug panel to simulate scans")

        self._ui.show_start_screen()
        logger.info("Application ready — showing start screen")
        logger.info("Entering Tkinter mainloop")
        self._root.mainloop()
        logger.info("Tkinter mainloop exited")

    def _on_uid(self, uid: str) -> None:
        """Serial callback (background thread) — marshal to Tkinter main thread."""
        self._root.after(0, lambda: self._handle_uid(uid))

    def _on_connection_change(self, connected: bool) -> None:
        """Serial connection callback — marshal to Tkinter main thread."""
        self._root.after(0, lambda: self._handle_connection_change(connected))

    def _handle_connection_change(self, connected: bool) -> None:
        """Update UI when the serial reader connects or disconnects."""
        if connected:
            logger.info("Serial reader connected")
        else:
            logger.warning("Serial reader disconnected")

        self._ui.set_connection_status(connected)
        if not connected:
            self._ui.set_status("NFC reader disconnected. Reconnect Arduino or wait for auto-reconnect.")
        elif self._story_engine.is_story_active() and not self._story_engine.get_state().is_ended:
            self._ui.set_status("Waiting for NFC card...")
        elif not self._story_engine.is_story_active():
            self._ui.set_status("Waiting for NFC card...")

    def _handle_uid(self, uid: str) -> None:
        """Process a scanned UID on the main thread."""
        logger.info("UID received: %s", uid)

        card = self._card_manager.get_card_by_uid(uid)
        if isinstance(card, Card):
            logger.info("Card mapped: %s (type=%s)", card.name, card.type.value)
            display_uid = card.uid
        else:
            logger.warning("Unknown UID: %s", uid)
            display_uid = uid

        self._ui.set_last_scanned(card.name, display_uid)

        result = self._story_engine.handle_card(card)
        self._apply_engine_result(result)

    def _simulate_card_by_name(self, card_name: str) -> None:
        """Debug helper: simulate a scan by card name."""
        card = find_card_by_name(self._card_manager, card_name)
        if card is None:
            logger.warning("Debug simulate: unknown card name %r", card_name)
            self._ui.show_error(f"No registered card named {card_name!r}.")
            return

        logger.info("Debug simulate: %s (uid=%s)", card.name, card.uid)
        self._ui.set_last_scanned(card.name, card.uid)
        result = self._story_engine.handle_card(card)
        self._apply_engine_result(result)

    def _apply_engine_result(self, result: EngineResult) -> None:
        """Map engine outcomes to UI screen transitions, logging, and status messages."""
        outcome = result.outcome
        self._last_inventory = _log_engine_result(result, self._last_inventory)

        if outcome == EngineOutcome.UNKNOWN_CARD:
            self._ui.show_error("Unknown card scanned.")
            return

        if outcome == EngineOutcome.INVALID_ACTION:
            self._ui.show_error("This card cannot be used in the current scene.")
            return

        if outcome == EngineOutcome.MISSING_ITEMS:
            self._ui.show_error(result.message)
            return

        if outcome == EngineOutcome.NO_STORY_LOADED:
            self._ui.show_start_screen()
            self._ui.set_status(result.message)
            return

        if outcome == EngineOutcome.STORY_NOT_FOUND:
            self._ui.show_error(result.message)
            return

        if outcome == EngineOutcome.STORY_ALREADY_ENDED:
            self._ui.set_status(result.message)
            return

        if outcome == EngineOutcome.ITEM_CARD_IGNORED:
            self._ui.set_status(result.message)
            if self._story_engine.is_story_active():
                self._show_current_scene()
            return

        if outcome in {EngineOutcome.STORY_STARTED, EngineOutcome.SUCCESS}:
            if self._story_engine.get_state().is_ended:
                self._show_current_ending()
            else:
                self._show_current_scene()
            return

        if outcome == EngineOutcome.STORY_ENDED:
            self._show_current_ending()
            return

        logger.error("Unhandled engine outcome: %s — %s", outcome.value, result.message)
        self._ui.show_error(result.message)

    def _show_current_scene(self) -> None:
        """Render the engine's current scene on the story screen."""
        scene = self._story_engine.get_current_scene()
        if scene is None:
            self._ui.show_start_screen()
            return

        story_title = _get_active_story_title(self._story_loader, self._story_engine)
        state = self._story_engine.get_state()
        choices = sorted(scene.choices.keys())

        self._ui.show_scene(
            story_title=story_title,
            scene=scene,
            inventory=list(state.inventory.items),
            available_choices=choices,
        )

    def _show_current_ending(self) -> None:
        """Render the ending screen for the current terminal scene."""
        scene = self._story_engine.get_current_scene()
        if scene is None:
            self._ui.show_start_screen()
            return

        state = self._story_engine.get_state()
        self._ui.show_ending(
            story_title=_get_active_story_title(self._story_loader, self._story_engine),
            scene=scene,
            ending_id=state.ending_id,
        )

    def _on_close(self) -> None:
        """Clean shutdown: stop serial thread and destroy the window."""
        if self._serial_reader is not None:
            self._serial_reader.stop()
        self._root.destroy()


def run_gui(*, hardware_mode: bool, debug: bool) -> None:
    """Launch the Tkinter GUI with safe initialization on macOS."""
    configure_logging(debug=debug)

    try:
        import tkinter as tk  # noqa: F401 — verify Tkinter is available
    except ImportError as exc:
        print(f"\nGUI failed to start: Tkinter is not available ({exc}).")
        print("Try: python3 main.py --debug --cli")
        sys.exit(1)

    try:
        logger.info("Initializing GUI application...")
        app = GameApplication(hardware_mode=hardware_mode, debug=debug)
        app.run()
    except Exception as exc:
        logger.exception("GUI failed to start")
        print(f"\nGUI failed to start: {exc}")
        print("Try: python3 main.py --debug --cli")
        sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for hardware vs debug vs terminal operation."""
    parser = argparse.ArgumentParser(
        description="Tangible NFC Interactive Storytelling Game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 main.py              # hardware mode (default)\n"
            "  python3 main.py --hardware   # explicit hardware mode\n"
            "  python3 main.py --debug      # simulate cards without Arduino\n"
            "  python3 main.py --debug --cli  # terminal mode (no Tkinter)\n"
        ),
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in terminal mode without Tkinter (no GUI, no Arduino)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--debug",
        action="store_true",
        help="Disable serial I/O and enable the debug panel for simulated card scans",
    )
    mode.add_argument(
        "--hardware",
        action="store_true",
        help="Enable SerialReader for Arduino NFC input (default when --debug is not set)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and launch the game application."""
    args = parse_args(argv)
    debug = args.debug
    hardware_mode = not debug

    if args.cli:
        run_cli(debug=debug)
    else:
        run_gui(hardware_mode=hardware_mode, debug=debug)


if __name__ == "__main__":
    main()
