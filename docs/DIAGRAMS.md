# Architecture & Flow Diagrams

Text diagrams for the Tangible NFC Interactive Storytelling Game.

---

## 1. Project Architecture

End-to-end data flow from physical card to player display:

```
┌──────────┐    SPI     ┌──────────┐   USB Serial   ┌─────────────────┐
│ NFC Card │ ─────────► │  RC522   │ ─────────────► │  Arduino Uno    │
│ (tag)    │            │  Reader  │  UID + newline │  rc522_reader   │
└──────────┘            └──────────┘                └────────┬────────┘
                                                             │
                                                    115200 baud
                                                             │
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │  serial_reader.py   │
                                                  │  (background thread)│
                                                  │  debounce + reconnect│
                                                  └──────────┬──────────┘
                                                             │ on_uid(uid)
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │      main.py        │
                                                  │  GameApplication    │
                                                  │  root.after() → UI  │
                                                  └──────────┬──────────┘
                                                             │
                              ┌──────────────────────────────┼──────────────────────────────┐
                              │                              │                              │
                              ▼                              ▼                              ▼
                   ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
                   │ card_manager.py  │           │ story_engine.py  │           │      ui.py       │
                   │  UID → Card      │           │  state machine   │           │  Tkinter GUI     │
                   │  data/cards.json │           │  inventory       │           │  (display only)  │
                   └──────────────────┘           └────────┬─────────┘           └────────┬─────────┘
                                                           │                              │
                                                           ▼                              │
                                                  ┌──────────────────┐                    │
                                                  │ story_loader.py  │                    │
                                                  │  stories/*.json  │                    │
                                                  └──────────────────┘                    │
                                                                                          │
                                                                                          ▼
                                                                                 ┌──────────────────┐
                                                                                 │ asset_manager.py │
                                                                                 │ assets/images/   │
                                                                                 └──────────────────┘
                                                                                          │
                                                                                          ▼
                                                                                    ┌──────────┐
                                                                                    │  Player  │
                                                                                    │ (viewer) │
                                                                                    └──────────┘
```

### Module dependency graph

```
main.py
 ├── serial_reader.py  → pyserial
 ├── card_manager.py   → (stdlib)
 ├── story_loader.py   → (stdlib)
 ├── story_engine.py
 │    ├── card_manager.py
 │    └── story_loader.py
 ├── asset_manager.py  → Pillow
 └── ui.py
      ├── asset_manager.py
      └── story_loader.py (Scene type)

register_cards.py → serial_reader.py
generate_placeholders.py → asset_manager.py
```

---

## 2. Game Flow

Player journey from start to ending:

```
                    ┌─────────────────┐
                    │   START SCREEN  │
                    │ "Scan Story Card│
                    │   to begin"     │
                    └────────┬────────┘
                             │
                    Scan STORY card
                    (Fantasy / Mystery / Space)
                             │
                             ▼
                    ┌─────────────────┐
                    │  STORY STARTED  │
                    │  Load story JSON│
                    │  Enter start    │
                    │  scene          │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │         SCENE VIEW           │
              │  • Scene image               │
              │  • Story text                │
              │  • Available action choices  │
              │  • Inventory panel           │
              └──────────────┬───────────────┘
                             │
                    Scan ACTION card
                    (matches a choice key)
                             │
              ┌──────────────┴───────────────┐
              │                              │
        Valid choice                   Invalid choice
        + required items met           or missing items
              │                              │
              ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │ SCENE TRANSITION│            │  ERROR MESSAGE  │
    │ Apply gained/   │            │  Stay on current│
    │ lost items      │            │  scene          │
    └────────┬────────┘            └─────────────────┘
             │
             ├── Not ending ──► back to SCENE VIEW
             │
             └── Is ending ──► ┌─────────────────┐
                               │  ENDING SCREEN  │
                               │  Final text +   │
                               │  ending ID      │
                               └────────┬────────┘
                                        │
                               Scan RESTART card
                               (or new STORY card)
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ STORY RESTARTED │
                               │ or new story    │
                               └─────────────────┘
```

### Card type routing (story_engine)

```
Scan received
     │
     ▼
Unknown UID? ──yes──► UNKNOWN_CARD
     │no
     ▼
Card type?
     │
     ├── STORY ──► Match story id/title → STORY_STARTED
     │
     ├── ACTION ──► Match scene choice → SUCCESS / MISSING_ITEMS / INVALID_ACTION
     │
     ├── SYSTEM ──► "Restart" → STORY_STARTED (reset)
     │
     └── ITEM ──► ITEM_CARD_IGNORED (items come from scenes)
```

---

## 3. Final Folder Tree

Generated from project root (excluding `.git` and `.pytest_cache`):

```
tangible-nfc-story-game/
├── README.md
├── requirements.txt
├── main.py
├── ui.py
├── serial_reader.py
├── card_manager.py
├── register_cards.py
├── story_loader.py
├── story_engine.py
├── asset_manager.py
├── generate_placeholders.py
├── arduino/
│   └── rc522_reader.ino
├── assets/
│   └── images/
│       ├── fantasy/
│       │   ├── armory.png
│       │   ├── castle.png
│       │   ├── caught.png
│       │   ├── dragon.png
│       │   ├── escape.png
│       │   ├── forest.png
│       │   ├── gate.png
│       │   ├── hermit.png
│       │   ├── standoff.png
│       │   ├── throne.png
│       │   ├── tower.png
│       │   ├── vault.png
│       │   ├── victory.png
│       │   └── wizard.png
│       ├── mystery/
│       │   ├── accusation.png
│       │   ├── cellar.png
│       │   ├── fled.png
│       │   ├── foyer.png
│       │   ├── garden.png
│       │   ├── kitchen.png
│       │   ├── library.png
│       │   ├── parlor.png
│       │   ├── study.png
│       │   └── wrong_accuse.png
│       ├── space/
│       │   ├── airlock.png
│       │   ├── alien_vessel.png
│       │   ├── boarding.png
│       │   ├── bridge.png
│       │   ├── crew_quarters.png
│       │   ├── debris.png
│       │   ├── engineering.png
│       │   ├── escape_pod.png
│       │   ├── hull_exterior.png
│       │   ├── peace_treaty.png
│       │   └── rescue.png
│       └── placeholders/
├── data/
│   └── cards.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── MODULES.md
│   ├── DIAGRAMS.md
│   ├── PROJECT_REPORT.md
│   └── FINAL_CHECKLIST.md
├── stories/
│   ├── fantasy.json
│   ├── mystery.json
│   └── space.json
└── tests/
    ├── conftest.py
    ├── test_asset_manager.py
    ├── test_card_manager.py
    ├── test_inventory.py
    ├── test_story_engine.py
    └── test_story_loader.py
```

**Image counts:** Fantasy 14, Mystery 10, Space 11 (42 scene images total).
