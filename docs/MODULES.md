# Module Reference

Brief reference for every Python module in the Tangible NFC Interactive Storybook.

---

## main.py

**Purpose:** Application composition root. Wires serial I/O, card mapping, story engine, and Tkinter UI. Marshals background-thread serial events onto the Tkinter main thread via `root.after()`.

**Key classes:**
- `GameApplication` — constructs all subsystems, handles UID callbacks, maps engine outcomes to UI transitions
- `configure_logging()` — sets up console logging with timestamps
- `parse_args()` / `main()` — CLI entry point (`--debug`, `--hardware`)

**Dependencies:** `tkinter`, `asset_manager`, `card_manager`, `serial_reader`, `story_engine`, `story_loader`, `ui`

---

## ui.py

**Purpose:** Display-only Tkinter presentation layer with dark theme. Renders start screen, active scene (image + text + choices + inventory), and ending screen. Never contains story logic.

**Key classes:**
- `GameUI` — public facade: `show_start_screen()`, `show_scene()`, `show_ending()`, status/error/connection display, debug panel
- `_StartScreen` — welcome screen listing available stories
- `_StorySceneScreen` — active scene layout with image, text, choice chips, inventory
- `_EndingScreen` — terminal scene with restart prompt

**Dependencies:** `tkinter`, `asset_manager`, `story_loader.Scene`

---

## serial_reader.py

**Purpose:** Hardware I/O boundary. Opens Arduino serial port on a background thread, reads newline-terminated UID lines, debounces duplicates, and invokes callbacks. Auto-detects port and reconnects on disconnect.

**Key classes / functions:**
- `SerialReader` — `start()`, `stop()`, `connect()`, `is_connected()`
- `find_arduino_port()` — heuristic port auto-detection
- `is_valid_uid()` / `_normalize_uid()` — UID validation (4/7/10 byte hex)

**Dependencies:** `pyserial` (`serial`, `serial.tools.list_ports`), `threading`

---

## story_engine.py

**Purpose:** Core branching story state machine. Tracks active story, current scene, inventory, and ending state. Processes scanned cards and returns structured outcomes.

**Key classes:**
- `StoryEngine` — `handle_card()`, `start_story()`, `restart()`, `get_current_scene()`, `get_state()`
- `Inventory` — add/remove/query items with duplicate prevention
- `GameState` — mutable session snapshot (story ID, scene ID, inventory, flags, ending)
- `EngineOutcome` / `EngineResult` — typed operation outcomes

**Dependencies:** `card_manager`, `story_loader`

---

## story_loader.py

**Purpose:** Story JSON ingestion. Loads, validates, and caches branching story files from `stories/` into immutable domain objects.

**Key classes:**
- `StoryLoader` — `load_story()`, `list_available_stories()`, `get_cached_story()`, `reload_story()`
- `Story` — immutable story graph with `get_scene()`, `is_ending()`
- `Scene` — immutable scene node (text, image, choices, items, ending marker)
- `StoryLoadError` / `StoryValidationError` — structured load failures

**Dependencies:** `json`, `pathlib` (stdlib only)

---

## card_manager.py

**Purpose:** UID-to-card mapping. Loads `data/cards.json` and resolves raw NFC UIDs to structured card objects.

**Key classes / functions:**
- `CardManager` — `get_card_by_uid()`, `get_cards_by_type()`, `reload_cards()`
- `Card` — registered card (uid, name, type)
- `UnknownCard` — placeholder for unregistered UIDs
- `CardType` — enum: `story`, `action`, `item`, `system`
- `normalize_uid()` — uppercase, strip spaces

**Dependencies:** `json`, `pathlib`, `logging` (stdlib only)

---

## asset_manager.py

**Purpose:** Centralized image loading, resizing, and caching for scene artwork. Returns themed placeholders when files are missing.

**Key classes / functions:**
- `AssetManager` — `load_image()`, `get_placeholder()`, `image_exists()`, `clear_cache()`
- `create_placeholder_pil_image()` — dark-themed PIL placeholder generator
- `infer_story_type()` — story character hint from image path (Benny/Mina/Nova)

**Dependencies:** `Pillow` (`PIL.Image`, `PIL.ImageTk`), `pathlib`

---

## register_cards.py

**Purpose:** Interactive CLI tool for registering physical NFC cards. Reads UIDs from Arduino over serial and writes the UID → card mapping to `data/cards.json`.

**Key functions:**
- `load_cards()` / `save_cards()` — read/write registry with validation and backup
- `register_card_interactive()` — guided scan loop for one card
- `run_registration()` — walk through all 12 predefined cards
- `_UIDListener` — thread-safe UID queue from `SerialReader`

**Dependencies:** `serial_reader`, `json`, `argparse`, `threading`, `queue`

**CLI:** `--port`, `--baud`, `--cards-path`, `--list`, `--card NAME`

---

## generate_placeholders.py

**Purpose:** Utility script that scans story JSON files for referenced image paths and creates dark-themed placeholder PNGs for any missing files. Existing files are never overwritten.

**Key functions:**
- `collect_image_paths()` — extract unique `image` fields from story JSON
- `generate_missing_placeholders()` — create PNGs under `assets/images/`

**Dependencies:** `asset_manager`, `json`, `pathlib`

**Not imported by the runtime application** — run manually: `python3 generate_placeholders.py`
