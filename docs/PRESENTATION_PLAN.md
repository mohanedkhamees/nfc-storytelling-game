# One-Day Plan — Final Presentation

**Format:** 10 min presentation + 5 min Q&A · 4 presenters
**Goal:** demo works, every point in the professor's list is covered, and every question lands on someone who owns that area.

---

## 0. Do first — demo blockers (one person, ~30 min)

### ✅ Already fixed (verify, don't redo)

| Was broken | Fix | Why it mattered |
|---|---|---|
| `main.py` hardcoded `port="/dev/cu.usbmodem145101"` (a macOS path) and bypassed auto-detection | now `--port` CLI flag, defaults to auto-detect | **Hardware mode could not connect on Windows at all.** |
| `usbmodem` missing from the port keyword list | added | Auto-detect failed on macOS — the reason someone hardcoded the port. |
| Fullscreen with no way out | `Escape` exits fullscreen, `F11` restores | If the demo misbehaves you can get to the desktop. |

**Run the app with the venv Python, not the system one** — the system Python has no `pyserial`:

```powershell
.\.venv\Scripts\python.exe main.py                 # auto-detect the reader
.\.venv\Scripts\python.exe main.py --port COM7     # force a port if auto-detect fails
.\.venv\Scripts\python.exe main.py --debug         # no hardware, GUI with debug panel
```

Find the port with the Arduino plugged in:

```powershell
.\.venv\Scripts\python.exe -c "from serial.tools import list_ports; [print(p.device, '|', p.description) for p in list_ports.comports()]"
```

> When I checked, only Bluetooth COM ports were present — **no Arduino was connected.** Plug it in and confirm you see it *today*, not an hour before the presentation.

### ⚠️ Decision needed — you cannot switch stories mid-session

`main.py:574` blocks *every* story card once a story is running:

```python
if card.type == CardType.STORY and self._story_engine.is_story_active():
    self._ui.show_error("Story cards can only be used at the start.")
    return
```

`is_story_active()` stays `True` even after an ending. So **once you start Benny, you cannot start Mina — even after finishing — without restarting the app.** The Restart card only replays the current story.

This contradicts `StoryEngine`, which was designed to switch stories and already handles re-scanning the same card gracefully. It's also why `test_main_cli.py::test_simulate_path_mina_after_benny_does_not_stay_on_benny` fails (pre-existing, not caused by today's edits).

**Two options:**
- **Delete those 4 lines** → story switching works, the failing test passes, demo can show two stories. Recommended.
- **Keep it** → plan the demo around one story, and *never* scan a second story card on stage.

Decide before you build the demo script. If you keep it, own it in Q&A as a deliberate choice ("we lock the story so a child can't wipe their progress by grabbing the wrong card") — that's a defensible answer, but then the failing test should be updated to match.

---

## 1. The day — 4 people in parallel

| Time | A — Hardware | B — Engine/Content | C — UI/Demo | D — UX & Slides |
|---|---|---|---|---|
| **Block 1** (~2 h) | Apply §0 fixes, confirm Arduino connects, test all 12 cards read | Read `story_engine.py` + `story_loader.py`, run the audit tool | Read `ui.py` + `main.py` wiring, run all three modes | Storyboard sketches + wireframe (from `UX_LAB_PHASE2.md`) |
| **Block 2** (~2 h) | Record a **backup demo video** — insurance | Rewrite Benny text (see §6), re-run audit | Build the architecture slide picture | Heuristic evaluation with one friend/family member — 1 h is enough |
| **Block 3** (~1.5 h) | Rehearse card handling | Write dev-course + milestones slides | Write demo script, rehearse | Assemble the deck, write intro slides |
| **Block 4** (~1.5 h) | **Full run-through together, twice, on the clock.** Then Q&A drill: each person answers 5 questions from their cheat sheet out loud. |

**Non-negotiable:** finish Block 4. A rehearsed 10-minute talk with a modest demo beats an unrehearsed one with a great demo.

---

## 2. Slide-by-slide (10:00)

Every required point from the email is covered, and every person speaks on the area they own for Q&A.

| # | Slide | Time | Speaker | Content |
|---|---|---|---|---|
| 1 | Title + team + **task distribution** | 0:45 | **D** | Names + the 4 ownership areas. Gets a required point out of the way in 20 s and tells the professor who to aim questions at. |
| 2 | **Project task + use case** | 1:15 | **D** | One persona, one scenario: Lina, 7, at the after-school table. Physical cards, no mouse, pre-reader. Use a storyboard panel, not bullet points. |
| 3 | **Prototyping methods & frameworks** | 0:45 | **C** | Paper prototype + bodystorming → wireframe → working prototype. Python 3.12, Tkinter, Pillow, pyserial, Arduino/MFRC522, pytest. |
| 4 | **Course of development + milestones** | 1:15 | **B** | 4 phases + the turning points (§5). |
| 5 | **System architecture** (the picture) | 1:30 | **B** | The layer diagram from `ARCHITECTURE_AS_BUILT.md` §2. **This is a required slide — have an actual image.** |
| 6 | **Technical design decisions, justified** | 1:00 | **A** | Three decisions, each with the alternative you rejected (§4). |
| 7 | **LIVE DEMO** | 2:30 | **A** places cards, **C** narrates | See §3. |
| 8 | **UX evaluation + what we'd fix next** | 1:00 | **D** | 3 findings from the heuristic evaluation, prioritized critical/important/nice-to-have. Mention the full documentation is in the separate submission. |

**The one sentence everyone must be able to say:**
> "A child places a physical NFC card on a reader; an Arduino sends the card's UID over USB serial; Python maps it to a story action and shows the next scene — the card is the only input, there are no buttons."

---

## 3. Demo script (2:30) + fallbacks

Rehearse this exact sequence. Do **not** improvise on stage.

1. App is **already running** on the start screen before you begin. Never launch it live.
2. C: "The screen invites the child to place a card." A places **🐰 Benny** → first scene appears.
3. C narrates the scene, points at the three choice options. A places **💬 Talk** → new scene, **point out the item appearing in the inventory strip**.
4. A places a card that is *not* valid here → C: "The system tells the child instead of doing nothing." *(This shows error handling on purpose — turn a weakness into a designed moment.)*
5. A places 2–3 more cards to reach an ending.
6. A places **🔄 Restart** → back to the start.

**Fallbacks, in order:**
- Reader not detected → quit, relaunch with `--port COMx`. 10 seconds.
- Still failing → `--debug` mode, drive it from the debug panel. Say plainly: "the reader isn't being detected on this machine, so we'll simulate the scans — the software path is identical from the UID onward." This is honest and costs you little.
- Total failure → play the **backup video** (A records it in Block 2). *Record it. It costs 15 minutes and it is the difference between a bad grade and a fine one.*

Physical checklist: Arduino + cable, all 12 cards, laptop **charger**, adapter for the projector, laptop sleep/notifications **off**.

---

## 4. The 4-way split & Q&A ownership

Each person owns one layer of the system. If a question isn't yours, say *"that's B's area"* — that's not weakness, it's what "distribution of tasks" means.

### A — Hardware & signal chain
**Files:** `arduino/rc522_reader.ino`, `serial_reader.py`, `register_cards.py`

Must know: RC522 talks SPI to the Arduino; firmware sends **one uppercase hex UID per line at 115200 baud** and contains **no game logic** (119 lines); Python auto-detects the port and reconnects every 3 s; UIDs validated as 4/7/10-byte hex; **double-scan protection is two-stage** — firmware suppresses repeats while the card sits on the reader, Python debounces 2500 ms per UID.

| Likely question | Answer |
|---|---|
| Why NFC instead of QR codes or a camera? | QR needs a camera, good lighting, and aiming — hard for a 7-year-old. NFC just needs the card *placed near* the reader, no line of sight, and the cards are cheap, durable and printable. |
| Why doesn't the Arduino run the game? | Deliberate separation. The microcontroller does one job: read a UID, send a line. Game logic needs a filesystem, images and tests. It also means we could swap the reader for a different sensor without touching the game. |
| What if two cards are read at once / a card bounces? | Two-stage debounce (above). In practice the reader reports one card; repeats while the card rests on the reader are suppressed in firmware. |
| What happens if you unplug it mid-game? | The reader thread detects the read error, the footer turns red, and it retries every 3 seconds. **Game state is preserved** — you carry on where you were. |
| How do you register a new card? | `register_cards.py` — scan the physical card, type its name and type, it writes `data/cards.json`. That's how our 12 cards were enrolled. |
| Why 115200 baud? | Fast enough that the UID arrives faster than the child can look up, and it's a standard rate. The bottleneck is the RC522, not the serial line. |

### B — Story engine & content
**Files:** `story_engine.py`, `story_loader.py`, `stories/*.json`, `audit_stories.py`

Must know: the engine is a **state machine**; `handle_card()` is the single entry point and returns a typed `EngineResult` with one of **11 `EngineOutcome` values**; **items are granted by entering scenes, never by scanning an item card**; gates (`required_items`) are checked on the *target* scene before the move commits; content is **75 scenes / 8 endings across 3 stories**.

| Likely question | Answer |
|---|---|
| How do you add a new story? | Drop one JSON file in `stories/`, register a story card, add one line to the ID map. **No engine code changes.** That was the point of separating content from logic. |
| How do you know a story isn't broken? | Two layers. `StoryLoader` rejects at load time any choice pointing to a scene that doesn't exist. `audit_stories.py` then walks every graph and reports unreachable scenes, dead ends, inventory traps and endings you can't reach. All three stories currently pass. |
| Why JSON and not a database? | Fully offline, human-editable by a non-programmer, and version-controlled in git. A database would add a dependency and buy us nothing at this scale. |
| Why 11 outcome values instead of true/false? | So the application layer maps each outcome to exactly one UI reaction. The engine never formats a screen and the UI never re-derives a rule — which is why the same engine drives both the GUI and the terminal version. |
| Can the child get stuck? | No. The audit checks that every non-ending scene can still reach an ending, and an invalid card leaves you where you are rather than moving you somewhere broken. |
| Is there a save feature? | No — deliberate. A session is 5–10 minutes and designed for one sitting. Adding persistence was scoped out. |

### C — UI & interaction
**Files:** `ui.py`, `asset_manager.py`, `main.py` (wiring)

Must know: **three screens** (start / scene / ending) stacked and raised, never rebuilt; **the UI is display-only** — no gameplay buttons; the serial thread never touches Tkinter, everything is marshalled with `root.after(0, …)`; missing images fall back to generated placeholders; three run modes (hardware / `--debug` / `--debug --cli`).

| Likely question | Answer |
|---|---|
| Why Tkinter? | It's in the standard library — zero extra install on the demo machine — and cross-platform. We don't need animation-heavy rendering; we need a reliable full-screen display. Pillow handles image scaling. |
| Why no buttons on screen? | That's the core NUI decision. If there were buttons, the child would use them — they're faster than finding a card — and the tangible interaction would be decoration. The screen reports state; the cards are the input device. |
| How do you handle the threading? | Serial runs on a background daemon thread. Tkinter is not thread-safe, so the callback does `root.after(0, ...)` to hand the UID to the main thread. Every state change happens on one thread. |
| What if an image file is missing? | `AssetManager` generates a themed placeholder with the story name. The UI never crashes on a bad asset path — important when content and artwork are produced separately. |
| How did you develop without the hardware? | Two hardware-free modes: `--debug` gives the full GUI with simulated scans, `--debug --cli` runs in the terminal. The core engine imports neither `serial` nor `tkinter`, which is also why the tests need no hardware. |
| How is it tested? | 107 tests, no hardware required — engine, loader, card mapping, inventory, asset fallback, the CLI, and a walk over the real story files. |

### D — UX process & evaluation
**Files:** `docs/UX_LAB_PHASE2.md`, your storyboard/wireframe/workbook

Must know: the method chain **storyboard → paper prototype → bodystorming → wireframe → heuristic evaluation → prioritized fixes**; Nielsen's 10 heuristics; what you actually found with your tester; that the interface is **cards + reader + screen + table**, not just the window.

| Likely question | Answer |
|---|---|
| Which usability method did you use and why? | Heuristic evaluation with the Nielsen-Norman workbook — it's fast, needs one non-expert evaluator, and finds the majority of issues at wireframe stage before they're expensive to fix. |
| Did you test with real children? | **Be honest.** If you didn't: "We tested with an adult acting the persona and did bodystorming to simulate the physical context. Testing with children in the target age group is the clear next step and our main validity limitation." Do not claim testing you didn't do. |
| What was your biggest finding? | Pick one real one from your session. A strong candidate: on-screen choice colours are assigned by *position*, so the same card appears in a different colour in each scene — breaking the link to the physical card the child is hunting for. |
| What would you fix first? | Whatever you graded 🔴 critical, with the reason. |
| What is bodystorming and why did you do it? | Physically acting out the scenario with paper props to surface assumptions you can't see on screen — for a tangible interface, how the card is *held and placed* is part of the design. |

---

## 5. Course of development & milestones (for slide 4)

Confirm these from your own memory — I inferred them from the git history and the code:

| Phase | What happened |
|---|---|
| 1. Concept & architecture | Defined the tangible concept, chose the layered architecture, wrote the design doc |
| 2. Core software | Story loader + engine + card manager, developed **without hardware** using the CLI/debug modes |
| 3. Hardware integration | Arduino RC522 firmware, serial reader, card enrolment (`feature/nfc-integration`, merged in PR #1) |
| 4. Content & UI polish | Three stories (75 scenes), the child-friendly UI, the story audit tool |

**Turning points worth naming explicitly** — professors like these, because they show reasoning rather than just work:

1. **Keeping the Arduino "dumb."** Firmware transmits UIDs only. Made the game testable on a laptop and the hardware replaceable.
2. **Building hardware-free run modes early.** Meant three of us could work while one had the Arduino — this shaped the whole architecture and is why the core has no GUI or serial imports.
3. **Refusing to add on-screen buttons.** The tempting shortcut; rejected because it would have made the tangible interaction optional.
4. **Writing the story audit tool.** Once content passed ~50 scenes, hand-checking branches stopped working. Automating it caught real broken links.

---

## 6. Benny rewrite brief (B, Block 2)

The flow problem you sensed is real and I can name it precisely: **most collected items do nothing.**

| Story | Items gained | Items ever required | Decorative |
|---|---|---|---|
| Benny | 10 | 4 | **6** |
| Mina | 9 | 2 | 7 |
| Nova | 12 | 2 | **10** |

Benny's inventory fills with *Map, Feather Charm, Tower Mark, River Stone, Fox Trust, Crystal Promise* — none of which ever unlock anything. The child learns that collecting is meaningless, and the inventory strip becomes noise. (Nova is worse: items like "Safety Check" and "Navigation Fixed" aren't objects at all, they're internal flags shown to the player.)

**Rewrite rules for Benny:**
1. **Cut the decorative items.** Keep only what a gate actually needs: Apple, Golden Key, Leaf Shield, River Song. Every item the child sees should open something.
2. **Language for ages 6–9.** Max ~10 words per sentence, one idea per sentence, concrete nouns, present tense. Replace abstract morals ("Bravery does not mean you are never afraid") with something a child *sees* happen.
3. **Make gates visible.** When a scene needs an item, the previous scene should hint at it. "Missing required items: River Song" is meaningless to a child who has no idea what that is or where to get it.
4. **Keep all 29 scene IDs, choice keys and image paths unchanged** — the card names and artwork must keep working.
5. **Re-run the audit afterwards:** `$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe audit_stories.py`

> The audit tool crashes on Windows without `PYTHONIOENCODING=utf-8` — it prints emoji the default console encoding can't handle. Minor, but it'll waste your time at midnight if you don't know.

**Offer:** I can do this rewrite in one pass and you review it — likely faster and more consistent than doing it by hand tonight. Say the word.

---

## 7. Q&A ground rules

- **Answer from your area. Hand off the rest.** "That's A's area" is a correct answer, and it demonstrates the task distribution you claimed on slide 1.
- **Never invent a number.** You know these: 3 stories, 75 scenes, 8 endings, 12 cards, 115200 baud, 107 tests, ~4,400 lines.
- **Own the gaps.** "We didn't implement save/resume — sessions are short and it was scoped out." "We haven't tested with children yet; that's the next step." A known limitation stated confidently reads as engineering judgment. A bluff that unravels does not.
- **The trap question is "why is this a *natural* user interface?"** Answer: the input is a physical object a child already knows how to handle — pick it up, put it down. No syntax to learn, no pointer, no reading required. The interface is the table, not the screen.
