# Project Report — Tangible NFC Interactive Storytelling Game

**Course:** Natural User Interfaces (NUI)  
**Project:** Offline tangible-interaction storytelling game  
**Status:** Complete (Steps 1–13)

---

## What Was Built

This project delivers a fully functional **offline tangible storytelling game** where players advance branching narratives by scanning physical NFC cards. The system comprises:

1. **Arduino firmware** (`arduino/rc522_reader.ino`) — reads RC522 UIDs and transmits uppercase hex strings over USB serial at 115200 baud
2. **Python application** — eight modules wired through a composition root (`main.py`):
   - Serial listener with auto-reconnect and debounce
   - UID-to-card registry (`data/cards.json`)
   - JSON story loader with validation
   - Branching story engine with inventory gating
   - Tkinter dark-mode GUI (display-only, no gameplay buttons)
   - Asset manager with Pillow image caching and placeholders
3. **Three complete stories** — Fantasy, Mystery, and Space with multiple scenes, inventory mechanics, and endings
4. **42 scene images** across genre subfolders under `assets/images/`
5. **Interactive card registration CLI** (`register_cards.py`) with backup and validation
6. **35 automated unit tests** covering core modules
7. **Documentation** — README, module reference, diagrams, architecture design, and this report

The game runs in two modes: **hardware mode** (default, real NFC input) and **debug mode** (`--debug`, simulated card scans via keyboard/buttons).

---

## Why NFC Improves NUI

Traditional GUI-based games rely on mouse clicks and keyboard input — interactions mediated through abstract on-screen controls. This project inverts that model:

| Aspect | Conventional GUI | Tangible NFC (this project) |
|--------|------------------|----------------------------|
| Input modality | Abstract (click button) | Physical (place card on reader) |
| Cognitive mapping | Symbol → action via screen | Object → action via touch |
| Social presence | Individual screen interaction | Shared physical cards visible to group |
| Embodiment | Disembodied pointer | Card-as-prop, reader-as-altar |
| Accessibility of intent | Hidden in menus | Cards labeled with action names |

NFC cards function as **physical affordances** — each card is a tangible token representing a story choice, item, or system command. The player does not select from a dropdown; they **perform** the action by placing the corresponding card on the reader. This aligns with NUI principles: natural, direct manipulation of real-world objects to control digital content.

The GUI serves exclusively as a **display surface** — scene images, narrative text, inventory, and connection status — reinforcing that interaction happens through the physical world, not the screen.

---

## What Was Learned

### Technical skills

- **Embedded ↔ host communication:** Designing a minimal serial protocol (newline-terminated UIDs) and handling threading, debounce, and reconnect in Python
- **State machine design:** Building a data-driven story engine where JSON defines scenes, choices, inventory rules, and endings
- **Separation of concerns:** Keeping Arduino firmware UID-only; all game logic in Python; UI display-only
- **Thread-safe GUI updates:** Marshaling serial callbacks to the Tkinter main thread via `root.after()`
- **Test-driven validation:** Unit tests for loader validation, engine transitions, inventory gating, and asset fallbacks

### Design insights

- **Data-driven scalability:** Adding a fourth story requires only a new JSON file and images — no engine changes
- **Card registration workflow:** Physical UIDs must be mapped once; the registration CLI with backup prevents data loss
- **Graceful degradation:** Missing images show placeholders; missing serial port shows reconnect status; debug mode enables development without hardware
- **Debouncing is essential:** Both firmware and Python debounce duplicate reads to prevent accidental double-transitions

### Process lessons

- Architecture-first design (Step 2 document) guided consistent module boundaries through implementation
- Incremental steps (serial → cards → engine → UI → integration) reduced integration risk
- Documentation alongside code supports university presentation and future maintenance

---

## Future Improvements

| Area | Enhancement |
|------|-------------|
| **Voice** | Text-to-speech narration of scene text; audio cues on card scan |
| **Sound** | Background music per story genre; transition sound effects |
| **AI stories** | Procedural scene generation or LLM-authored branches |
| **Story packs** | Downloadable JSON + asset bundles; in-app story selector |
| **Multiplayer** | Turn-based shared reader; player-specific inventories |
| **Cloud save** | Resume progress across devices; sync inventory and scene |
| **Mobile** | Companion app for story authoring and card registration |
| **JSON Schema** | Validate story files at load time with formal schema |
| **Card enrollment UI** | In-game panel showing unknown UIDs for quick registration |

---

## Supervisor Review Section

### Constructive Feedback

**Strengths observed:**

- Clear tangible NUI concept executed consistently — GUI has no gameplay buttons
- Well-structured modular architecture with single-responsibility modules
- Comprehensive error handling: unknown cards, invalid actions, missing items, serial disconnect
- Three complete stories with inventory gating demonstrate non-trivial branching
- Debug mode enables reliable demonstration without hardware dependency
- 35 unit tests provide confidence in core logic
- Professional documentation suitable for handoff and presentation

**Areas for improvement:**

- No save/resume persistence — progress lost on application close
- Item cards (`CardType.ITEM`) are registered but have no gameplay effect (items come from scenes only)
- No automated integration test for the full serial → engine → UI pipeline
- Story JSON authoring lacks schema validation tooling
- Accessibility: no screen reader support or high-contrast mode
- Multiplayer and cloud features remain future work

### Estimated Grade: **A-**

**Justification:** The project demonstrates a complete, working tangible NUI system with hardware integration, three branching stories, inventory mechanics, a polished dark-mode GUI, interactive card registration, and thorough unit test coverage. Architecture is clean and documented. The tangible interaction model is authentic and well-motivated. Minor deductions for: no save persistence (planned but not implemented), item cards being cosmetic-only, and absence of end-to-end hardware integration tests. For a university NUI coursework project at this scope, the implementation quality, documentation, and demonstration readiness warrant a strong **A-** — bordering on **A** if the live hardware demo executes flawlessly during presentation.

**To reach A+:** Add save/resume, voice narration for one story, and a recorded demo video showing the full hardware flow.

---

*End of project report.*
