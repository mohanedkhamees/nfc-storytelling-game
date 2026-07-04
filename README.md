# Tangible NFC Interactive Storybook for Children

A university Natural User Interfaces (NUI) project that combines **physical NFC cards**, **Arduino hardware**, and **interactive branching storytelling**. Players advance offline stories by scanning tangible cards — not by clicking GUI buttons.

---

## Project Overview

This game lets players explore three children’s branching narratives — *Benny and the Lost Crystal*, *Mina and the Missing Moon Lantern*, and *Nova and the Friendly Star* — by placing NFC tags on an RC522 reader connected to an Arduino Uno. The microcontroller sends card UIDs over USB serial; a Python application maps each UID to a symbolic card name, drives a story state machine, and updates a bright, child-friendly Tkinter display.

The GUI is **display-only** in production mode. Every story choice is made by scanning the corresponding physical card — preserving an authentic tangible interaction model suitable for NUI coursework and live demonstration.

---

## Features

- **Tangible NFC input** — story, action, item, and system cards as physical artifacts
- **Three complete children’s stories** — Benny and the Lost Crystal, Mina and the Missing Moon Lantern, and Nova and the Friendly Star
- **Bright child-friendly Tkinter GUI** — pastel story cards, scene images, narrative text, colorful choice pills, backpack inventory panel
- **Arduino RC522 integration** — auto-detected serial port, debounced scans, auto-reconnect
- **Debug mode** — simulate all 12 cards without hardware (keyboard shortcuts + panel)
- **Card registration CLI** — guided enrollment of physical tags into `data/cards.json`
- **Asset management** — image load/resize/cache with themed placeholders for missing files
- **CLI fallback mode** — terminal REPL when Tkinter/GUI is unavailable (macOS crashes, headless)
- **Unit tests** — pytest suite covering card manager, story loader, inventory, engine, assets, and CLI
- **Offline operation** — no network, cloud, or AI dependencies

---

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| **Microcontroller** | Arduino Uno (or compatible) |
| **NFC reader** | RC522 RFID module |
| **NFC tags** | 12+ ISO14443A cards/tags (MIFARE Classic, NTAG, etc.) |
| **Power** | USB cable for Arduino (5 V from host or adapter) |
| **Wiring** | Jumper wires; RC522 powered from **3.3 V** only |

---

## Software Requirements

| Software | Purpose |
|----------|---------|
| **Python 3.9+** | Application runtime |
| **pip** | Install Python dependencies |
| **Arduino IDE** | Upload RC522 firmware |
| **MFRC522 library** | Arduino library for RC522 (via Library Manager) |

Python packages (see `requirements.txt`):

- `pyserial>=3.5` — USB serial communication
- `Pillow>=10.0` — scene image loading and resizing
- `pytest>=7.0` — unit test runner

---

## Folder Structure

```
tangible-nfc-story-game/
├── arduino/
│   └── rc522_reader.ino          # RC522 firmware (UID → serial)
├── assets/
│   └── images/
│       ├── fantasy/              # Benny story scene PNGs
│       ├── mystery/              # Mina story scene PNGs
│       ├── space/                # Nova story scene PNGs
│       └── placeholders/
├── data/
│   └── cards.json                # UID → card name/type registry
├── docs/
│   ├── ARCHITECTURE.md           # Step 2 design document
│   ├── DIAGRAMS.md               # Architecture & game flow diagrams
│   ├── FINAL_CHECKLIST.md        # Step 13 verification checklist
│   ├── MODULES.md                # Module reference
│   └── PROJECT_REPORT.md         # University project conclusion
├── stories/
│   ├── benny.json
│   ├── mina.json
│   └── nova.json
├── tests/                        # pytest unit tests
├── main.py                       # Application entry point
├── ui.py                         # Tkinter GUI
├── serial_reader.py              # Arduino serial I/O
├── card_manager.py               # UID → card mapping
├── register_cards.py             # Interactive card enrollment
├── story_loader.py               # Story JSON ingestion
├── story_engine.py               # Game state machine
├── asset_manager.py              # Image loading & placeholders
├── generate_placeholders.py      # Create missing image PNGs
├── requirements.txt
└── README.md
```

---

## Installation

1. **Clone or download** the project:

   ```bash
   cd ~/Projects/tangible-nfc-story-game
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   # .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Python modules compile**:

   ```bash
   python3 -m py_compile *.py
   ```

---

## Arduino Setup

### Install the MFRC522 library

1. Open the Arduino IDE.
2. Go to **Sketch → Include Library → Manage Libraries**.
3. Search for **MFRC522** (by Miguel Balboa) and install it.

### Upload firmware

1. Connect the Arduino Uno via USB.
2. Open `arduino/rc522_reader.ino` in the Arduino IDE.
3. Select **Tools → Board → Arduino Uno**.
4. Select the correct serial port under **Tools → Port**.
5. Click **Upload**.
6. Open **Tools → Serial Monitor**, set baud to **115200**.
7. Tap an NFC card on the reader — you should see one uppercase hex UID per line (e.g. `A1B2C3D4`).

The Python application uses the same baud rate and expects newline-terminated UID lines.

---

## Wiring Diagram

Wire the RC522 module to Arduino Uno as specified in the firmware:

| RC522 Pin | Arduino Uno Pin |
|-----------|-----------------|
| SDA (SS)  | Digital **10**  |
| SCK       | Digital **13**  |
| MOSI      | Digital **11**  |
| MISO      | Digital **12**  |
| IRQ       | *(not connected)* |
| GND       | **GND**         |
| RST       | Digital **9**   |
| 3.3V      | **3.3V**        |

> **Important:** Connect RC522 VCC to **3.3 V only**. Do not use 5 V — it can damage the module.

---

## Python Setup

After installing dependencies (see [Installation](#installation)):

| Task | Command |
|------|---------|
| Run tests | `python3 -m pytest tests/ -v` |
| List registered cards | `python3 register_cards.py --list` |
| Generate missing images | `python3 generate_placeholders.py` |
| Demo card manager | `python3 card_manager.py` |
| Demo story loader | `python3 story_loader.py` |
| Demo story engine | `python3 story_engine.py` |

### Find the serial port

| OS | Typical paths |
|----|---------------|
| **macOS** | `/dev/tty.usbmodem*`, `/dev/tty.usbserial*`, `/dev/cu.usbmodem*` |
| **Linux** | `/dev/ttyUSB0`, `/dev/ttyACM0` |
| **Windows** | `COM3`, `COM4`, … (Device Manager or Arduino IDE) |

List ports from Python:

```bash
python3 -c "from serial.tools.list_ports import comports; print([p.device for p in comports()])"
```

---

## Running in Debug Mode (GUI)

Debug mode disables serial I/O and shows a developer panel for simulating card scans — no Arduino required.

```bash
python3 main.py --debug
```

**Keyboard shortcuts** (matching debug panel buttons):

| Key | Card |
|-----|------|
| 1 | Benny |
| 2 | Mina |
| 3 | Nova |
| 4 | Sword |
| 5 | Magic |
| 6 | Shield |
| 7 | Run |
| 8 | Key |
| 9 | Talk |
| 0 | Hide |
| - | Open Door |
| = | Restart |

You can also type a card name in the debug entry field and press Enter.

> **macOS Tkinter crash?** If `python3 main.py --debug` quits unexpectedly, use [CLI debug mode](#running-in-debug-cli-mode) instead — it never loads Tkinter.

---

## Running in Debug CLI Mode

CLI mode runs the same story engine in the terminal — type card names instead of scanning NFC tags. **Tkinter is never imported**, so this works when the GUI crashes on macOS or in headless environments.

```bash
python3 main.py --debug --cli
# or without verbose logging:
python3 main.py --cli
```

At the `Card>` prompt, enter a registered card name (case-insensitive). Names with spaces work, e.g. `Open Door`. Type `quit` to exit.

**Supported cards:** Benny, Mina, Nova, Sword, Magic, Shield, Run, Key, Talk, Hide, Open Door, Restart

Example session:

```bash
echo -e "Benny\nTalk\nquit" | python3 main.py --debug --cli
```

CLI mode does not use Arduino serial I/O. Combine `--debug` for verbose log output on stdout.

---

## Running with Real Hardware

Hardware mode is the **default** when `--debug` is not passed:

```bash
python3 main.py
# or explicitly:
python3 main.py --hardware
```

1. Upload Arduino firmware and wire the RC522 (see above).
2. Register physical cards (see [Registering RFID Cards](#registering-rfid-cards)).
3. Launch the game — the app auto-detects the Arduino serial port at **115200 baud**.
4. Scan a **story card** (Benny, Mina, or Nova) to begin.
5. Scan **action cards** (tangible NFC decision cards) matching the highlighted choices on screen.
6. At an ending, scan the **Restart** card to play again.

If no serial port is found at startup, the UI shows a reconnect message and the reader keeps retrying in the background.

> **Tip:** Close the Arduino Serial Monitor before running the game — only one program can open the port at a time.

---

## Registering RFID Cards

Physical NFC tags must be enrolled in `data/cards.json` before the game recognizes them.

### Registry format

```json
{
  "A1B2C3D4": { "name": "Benny", "type": "story" }
}
```

Keys are uppercase UID strings. Each value has `name` (matches story choices or story identifiers) and `type` (`story`, `action`, `item`, or `system`).

### Guided registration

With Arduino connected and firmware uploaded:

```bash
python3 register_cards.py
```

The tool walks through all 12 cards in order. For each card, place the matching physical tag on the reader. Type **`s`** + Enter to skip a card.

### Options

```bash
python3 register_cards.py --port /dev/ttyUSB0   # explicit serial port
python3 register_cards.py --baud 115200         # default baud rate
python3 register_cards.py --list                # show current mappings
python3 register_cards.py --card Benny        # register one card only
```

Before saving, the tool backs up the existing registry to `data/cards_backup_YYYYMMDD_HHMMSS.json`, validates JSON structure, and prints a summary table (UID | Name | Type).

---

## Story System

Stories live in `stories/` as JSON files and are discovered automatically at startup (`benny.json`, `mina.json`, `nova.json`). Each file defines:

- `id`, `title`, `start_scene`
- `scenes` — a graph of scene nodes with `text`, `image`, `choices`, and optional `required_items`, `gained_items`, `lost_items`, and `ending`

**Story cards** start a story when no story is active. The card name must match the story `id` or `title` (case-insensitive).

**Action cards** advance the story when their name matches a choice key on the current scene.

**Item cards** are registered for completeness but do not directly modify inventory — items are granted or removed when entering scenes via JSON fields.

**System cards** (Restart) reset the active story.

See `docs/MODULES.md` for module details and `docs/DIAGRAMS.md` for the game flow diagram.

---

## Project Architecture

```
Arduino RC522  →  serial_reader.py  →  main.py  →  card_manager.py
                                              ↓
                                        story_engine.py  ←  story_loader.py
                                              ↓
                                           ui.py  ←  asset_manager.py
                                              ↓
                                           Player
```

| Module | Role |
|--------|------|
| `main.py` | Composition root: CLI, logging, callback wiring, lifecycle |
| `serial_reader.py` | Background USB serial listener, auto-reconnect |
| `card_manager.py` | UID → card name/type from `data/cards.json` |
| `register_cards.py` | Interactive CLI to enroll physical NFC UIDs |
| `story_loader.py` | Load and validate branching story JSON |
| `story_engine.py` | Scene transitions, inventory, card-driven state machine |
| `ui.py` | Tkinter presentation (start, scene, ending screens) |
| `asset_manager.py` | Image load/resize/cache with missing-image placeholders |

Detailed diagrams: [docs/DIAGRAMS.md](docs/DIAGRAMS.md)  
Design document: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)  
Module reference: [docs/MODULES.md](docs/MODULES.md)

---

## Future Improvements

- Voice narration and sound effects for immersion
- AI-generated or downloadable story packs
- Multiplayer with shared card pools
- Cloud save and mobile companion app
- JSON Schema validation for story authoring
- Automated hardware integration tests

See [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) for the full university project conclusion and supervisor review.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| **Arduino not detected** | Check USB cable and power LED. Install CH340/CP210/FTDI drivers. Try a different port or cable. |
| **Wrong serial port** | List ports (see [Find the serial port](#find-the-serial-port)). Pass `--port` to `register_cards.py`. Close Serial Monitor — only one program can use the port. |
| **UID not appearing** | Confirm RC522 wiring (3.3 V, SS pin 10, RST pin 9). Re-upload firmware. Open Serial Monitor at 115200 baud and hold the card flat for 1–2 seconds. |
| **Duplicate UID scans** | Normal — firmware debounces reads. Lift the card and re-tap to scan again. |
| **`cards.json` invalid** | Fix JSON syntax or restore from `data/cards_backup_*.json`. Run `python3 register_cards.py --list`. |
| **Card not recognized** | UID missing from registry. Run `python3 register_cards.py --card <Name>`. UIDs are normalized (case/spaces). |
| **Serial port not found (game)** | Use `--debug` or `--debug --cli` to play without hardware while troubleshooting. |
| **GUI crashes on macOS** | Use `python3 main.py --debug --cli` for terminal mode (no Tkinter). |
| **Invalid action** | Card is registered but not a valid choice in the current scene. Check highlighted choices on screen. |
| **Story not found** | Story card name must match story `id` or `title` in `stories/*.json`. |
| **Missing images** | Run `python3 generate_placeholders.py` or add artwork at the path in story JSON. |

Console logs include timestamps. Use `--debug` for verbose output.

---

## Demo Checklist (University Presentation)

Use this sequence for a live or recorded demonstration:

### Before the demo

- [ ] Arduino wired, firmware uploaded, RC522 reading UIDs in Serial Monitor
- [ ] All 12 cards registered (`python3 register_cards.py --list`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Tests passing (`python3 -m pytest tests/ -v`)
- [ ] Close Arduino Serial Monitor before launching the game

### Demo script (~5 minutes)

1. **Introduce tangible NUI concept** — cards as physical input, GUI as display only
2. **Show start screen** — `python3 main.py --hardware` (or `--debug` as fallback)
3. **Scan Benny story card** — first scene appears with image and choices
4. **Scan Talk action card** — scene transition; note inventory change if applicable
5. **Scan an invalid card** — show error feedback in status bar
6. **Play through to an ending** — highlight branching and inventory gating
7. **Scan Restart card** — story resets to start scene
8. **Briefly show Mina or Nova** — demonstrate story switching
9. **Mention debug mode and tests** — `python3 main.py --debug`, pytest count

### Backup plan

If hardware fails during presentation, switch immediately to debug mode:

```bash
python3 main.py --debug
```

Or CLI mode if the GUI is unavailable:

```bash
python3 main.py --debug --cli
```

Use keyboard shortcuts (1 = Benny, 4 = Sword, = = Restart) to complete the same demo flow.

If the GUI crashes (common on some macOS setups), use CLI mode instead:

```bash
python3 main.py --debug --cli
```

Type card names at the prompt (`Benny`, `Talk`, `Restart`, etc.) to complete the same demo flow.

---

## Running Tests

Unit tests cover the card manager, story loader, inventory, story engine, and asset manager:

```bash
python3 -m py_compile *.py
python3 -m pytest tests/ -v
```

Expected result: **all tests passed** (including CLI mode tests in `tests/test_main_cli.py`).

Individual module demos:

```bash
python3 card_manager.py
python3 story_loader.py
python3 story_engine.py
python3 register_cards.py --help
```

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file — setup, usage, troubleshooting |
| [docs/MODULES.md](docs/MODULES.md) | Module responsibilities and dependencies |
| [docs/DIAGRAMS.md](docs/DIAGRAMS.md) | Architecture, game flow, folder tree |
| [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | University conclusion and supervisor review |
| [docs/FINAL_CHECKLIST.md](docs/FINAL_CHECKLIST.md) | Step 13 component verification |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Original Step 2 architecture design |

---

*Natural User Interfaces — Tangible NFC Interactive Storybook for Children*
