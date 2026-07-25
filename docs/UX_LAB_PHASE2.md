# UX Lab — Phase 2 working plan

Deliverables for the second phase of the NUI UX Lab, mapped to our project (Tangible NFC Interactive Storybook).

**Our group is a tangible/touch group** → per the professor's email we **must** do bodystorming with paper prototypes. (The Conversational-UI extra heuristics do *not* apply to us.)

---

## 0. What has to be handed in

| # | Deliverable | Format | Source exercise |
|---|---|---|---|
| 1 | Sketched lo-fi prototype + paper prototype | **Photos** | Worksheets Ex. A + C |
| 2 | Wireframe + User Story | **Pictures** (sketch/Figma/Miro export) | Worksheets Ex. A + B |
| 3 | Heuristic Evaluation + Bodystorming | **Annotations & comments** (filled NN/g workbook + annotated photos) | Worksheets Ex. C + D |
| 4 | Results and comments | Written analysis | HE slides p.12 |
| 5 | Final design with fixed issues | Revised wireframe + changelog, grouped Critical / Important / Nice-to-have | HE slides p.14 |

Suggested repo layout for the evidence:

```
docs/ux-lab/
  01-storyboard/      photos of the sketched panels
  02-wireframe/       wireframe screens + interaction flowchart
  03-paper-prototype/ photos of the paper cards, reader mock, paper screens
  04-bodystorming/    session photos/video stills + annotations
  05-evaluation/      filled NN/g workbook (PDF/scan) + notes
  06-results/         findings table + final revised wireframe
```

---

## 1. The three artefacts people mix up

This is the part the professor flagged ("wireframe with interaction flow — **differs from a system diagram**"). Three different documents, three different questions:

| Artefact | Question it answers | Audience | Our file |
|---|---|---|---|
| **System / architecture diagram** | How is the software built? | Developers | `docs/ARCHITECTURE_AS_BUILT.md` — **already done, not part of this hand-in** |
| **User story + storyboard** | *Who* uses it, *where*, and what happens to them from motivation to goal? | Designers, stakeholders | Ex. A below |
| **Wireframe + interaction flow** | What does the person *see* and *do*, screen by screen, step by step? | Designers, developers | Ex. B below |

> Rule of thumb: if a box in your drawing contains a **module name** (`StoryEngine`, `SerialReader`), it belongs in the architecture doc. If it contains a **thing the user sees or touches** ("scene picture", "Benny card", "green light"), it belongs in the wireframe.

---

## 2. Exercise A — User story + storyboard

**User story** = one or two sentences fixing target user, context of use, and goal. Classic form:

> *As a* 6–9-year-old child playing at the after-school club table, *I want to* choose what the character does by putting a picture card on the reader, *so that* I can steer the story myself without being able to read long menus or use a mouse.

Add the three worksheet questions (p.4) explicitly — they will be graded:

| Question | Our answer |
|---|---|
| **Who is the target user?** | Children ~6–9, pre-/early readers; a parent or educator co-present as facilitator. |
| **What functions/goal does the interface allow?** | Pick a story, make narrative choices, collect story items, reach one of several endings, replay. |
| **Where is the action performed?** | A shared table — screen standing up, reader in front of it, deck of ~12 physical cards spread out. Indoors, shared/social, no keyboard or mouse. |

**Storyboard** = 6–8 hand-drawn panels (NN/g style, worksheets p.8–10). Draw the *person and the room*, not just the screen. Suggested panel sequence — one panel per key interaction/event leading to the goal:

1. **Motivation** — Lina sits at the table, bored; the box of story cards and the glowing screen invite her ("Scan a card to begin").
2. **Discovery** — she picks up the 🐰 Benny card; the start screen shows the same rabbit icon.
3. **First contact** — she places the card on the reader; *click* — screen changes to the first scene.
4. **Choice** — the screen shows three coloured options (💬 Talk / 🏃 Run / 🗝️ Key); she looks down at the deck to find the matching card.
5. **Consequence** — she places 🗝️ Key; a new picture and an item appears in her inventory strip.
6. **Friction (be honest!)** — she places a card that isn't valid here; the screen flashes a message she doesn't notice. *This panel is the seed of your heuristic findings.*
7. **Goal** — she reaches an ending; screen celebrates.
8. **Replay** — she places 🔄 Restart and starts a different branch.

Sketch on paper, photograph, that's deliverable 1 + 2.

---

## 3. Exercise B — Wireframe + interaction flowchart

### 3a. Wireframe

Grey boxes and labels only — **no colour, no artwork, no final copy**. For a tangible interface you need **two layers**, and including the physical one is what separates a NUI wireframe from a normal app wireframe:

**Layer 1 — physical setup (top-down view of the table):**

```
        ┌───────────────────────┐
        │       SCREEN          │   ← display, standing, ~50 cm from child
        └───────────────────────┘
             ┌───────────┐
             │  READER   │           ← the only "active" spot
             └───────────┘
   [🐰][🔍][🚀]   [⚔️][✨][🛡️][🏃][🗝️][💬][🙈][🚪]   [🔄]
    story cards          action cards                system
```

**Layer 2 — screen states (3 screens):**

```
START                          SCENE                          ENDING
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  title               │  │ story title          │  │  ✨ ending title      │
│                      │  │ ┌──────┐  scene text │  │  ┌──────┐            │
│  [card][card][card]  │  │ │ IMG  │  ......     │  │  │ IMG  │  text      │
│   pick one to start  │  │ └──────┘  ......     │  │  └──────┘            │
│                      │  │ ( o )( o )( o ) ←choices│  place 🔄 to replay  │
│                      │  │ inventory: ....      │  │                      │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ status │ prompt │ last│  │ status │ prompt │ last│  │ status │ prompt │last│  ← persistent footer
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

Annotate each region with *what it is for*, e.g. "choice row — mirrors the physical cards the child should look for".

### 3b. Interaction flowchart

Use the swimlane structure given on worksheets p.13 — **User / Action / Interface / Change of state / Functions**. Example for one loop:

| User | Action | Interface | Change of state | Function |
|---|---|---|---|---|
| Wants to know what to do | Looks at screen | Start screen lists 3 story cards | idle → waiting | — |
| Decides on a story | Picks up 🐰 card | (no system change yet) | — | — |
| Commits | **Places card on reader** | Footer: "Last scan: Benny" | waiting → story running | UID read → story starts |
| Reads/looks | Listens to adult read text | Scene screen: image + text + 3 choices | — | scene rendered |
| Decides | Finds matching card in the deck | choice row highlights options | — | — |
| Commits | Places 🗝️ Key card | new scene, item added to strip | scene A → scene B | choice validated, item granted |
| Errs | Places a card not valid here | footer message for 4 s | *no change* | invalid action |
| Finishes | Places 🔄 Restart | ending → start scene | story → reset | restart |

Then draw it as a proper flowchart with a decision diamond ("is this card valid in this scene?") and the error loop-back. **Include the failure branches** — that's where the evaluation findings will hang.

---

## 4. Exercise C — Paper prototype + bodystorming (mandatory for us)

### Props to build (an hour of cutting)

- ~12 **paper cards**, index-card size, drawn with the emoji + name exactly as on screen.
- A **cardboard "reader"** — a box or a marked square on the table. It does nothing; a human plays the sensor.
- **Paper screens** — A4 sheets, one per scene you want to test (5–6 is enough: start, 2 scenes, an error state, an ending).
- Optional: a paper "footer strip" the facilitator swaps to show status messages.

### Roles (worksheets/bodystorming p.18: teams of 3–7)

| Role | Job |
|---|---|
| **Child** (tester) | Actually plays. Ideally a real child or a friend/family member instructed to behave like one. Think aloud. |
| **The Computer** | Sits behind the paper screens, swaps the sheet when a card is placed on the box. **Must not help or explain.** |
| **Facilitator** | Gives the task ("get Benny to the end of his story"), calls freeze, does not solve problems. |
| **Observer(s)** | Photograph, time, and write down every hesitation, wrong card, and question. |

### Run it

1. Set the table up as in your physical wireframe. Photograph the setup **before** anyone touches it.
2. Give the task, then stay quiet. Record where hands go and where eyes go — the bodystorming slides (p.8) ask you to analyse **hand / palm / finger / arm / upper body** against **distance, direction, movement, angle**. For us the interesting measures are: does the child *place*, *tap*, *wave*, or *hold* the card? How long do they hold it? Do they lift it again?
3. Use **"Freeze" / "What-if"** triggers (p.20–21) when it stalls. Ones that fit our project:
   - *What if the child can't read yet?*
   - *What if two children want to place a card at the same time?*
   - *What if the card is placed upside-down / only half on the reader?*
   - *What if the reader is unplugged mid-story?*
   - *What if the child walks away and comes back five minutes later?*
4. Debrief immediately, write the insight list while it's fresh.

**Output:** photos + video stills, annotated with arrows and comments ("she tapped instead of placing — expected phone-style tap"), and a list of ideas/insights/problems.

---

## 5. Exercise D — Heuristic evaluation

Fill the **NN/g workbook** (one Issues + Recommendations box per heuristic) with a friend or family member as evaluator, on the **wireframe/paper prototype** — not on the finished code.

Workbook header: *Evaluator · Date · Product: Tangible NFC Interactive Storybook · Task: "Play Benny's story from start to an ending, then start Mina's story."*

### Candidate findings (from a code read — treat as hypotheses, confirm or refute with your tester)

I went through the implementation; these are the places most likely to produce real findings. **Do not paste these in as results** — the professor wants a real evaluation. Use them to know where to look.

| # | Heuristic | Candidate issue | Where | Suggested fix |
|---|---|---|---|---|
| 1 | Visibility of system status | A rejected scan is shown only as small footer text for 4 s. A child looking down at the deck will miss it entirely. No sound, no animation, no colour flash on the main area. | `ui.py` `show_error`, `ERROR_DISPLAY_MS = 4000` | Central, persistent feedback + sound; clear it on the next successful scan instead of on a timer. |
| 2 | Match between system and real world | Footer prints the raw hex UID: `Last scan: Run (A3531C34)`. That's developer jargon on a children's screen. | `ui.py` `set_last_scanned` | Show the card name and icon only; keep the UID behind debug mode. |
| 3 | User control and freedom | **No undo.** Once a card is placed the branch is committed; the only exit is Restart, which wipes the whole story and the inventory. There is no "go back one scene". | `story_engine.py` — no back transition | Add a ↩️ "Go back" card, or at least "Undo last choice". |
| 3 | User control and freedom | The window opens **fullscreen with no way out** — no Escape binding, no close button, `minsize` commented out. The adult has to Alt+F4 or kill the process. | `ui.py:879` `attributes("-fullscreen", True)` | Bind `<Escape>` to exit fullscreen. One line, clear win. |
| 4 | Consistency and standards | Choice colours are assigned **by position** (`CHOICE_PILL_COLORS[index % 6]`), so the *same* card is pink in one scene and green in the next — while the debug panel gives each card a *fixed* colour. The on-screen colour therefore does not match the physical card. | `ui.py` `_render_choices` vs `DEBUG_CARD_STYLES` | One fixed colour + icon per card, everywhere, matching the printed card. This is probably our single highest-value fix. |
| 5 | Error prevention | Nothing stops the child from reaching for a card that isn't valid in this scene — the design lets the error happen and then reports it. | engine validates after the fact | Show the valid cards more prominently; consider dimming/greying the rest on a "your cards" strip. |
| 6 | Recognition rather than recall | The child must map an on-screen label to one of 12 physical cards spread on the table. Made harder by the colour inconsistency above. | scene screen | Show the card's exact icon **and** colour in the choice pill, at card size. |
| 7 | Flexibility and efficiency | No accelerators for a returning player (no skip, no "jump to the branch I haven't seen"). Keyboard shortcuts exist but only in debug mode. | `_build_debug_panel` | Low priority for our audience — probably "nice to have". |
| 8 | Aesthetic and minimalist design | Footer carries three things at once, including the UID (see #2). | footer | Drop the UID; keep status + prompt. |
| 9 | Recognize/diagnose/recover | Error text says *what* went wrong but not *what to do*: "This card cannot be used here." Disconnect message is written for a developer: "Reconnect Arduino or wait for auto-reconnect." | `main.py` `_apply_engine_result`, `_handle_connection_change` | "That card doesn't work here — try 💬 Talk, 🏃 Run or 🗝️ Key." / "The reader is asleep. Ask a grown-up to check the cable." |
| 10 | Help and documentation | No in-app explanation of *how* to play — the start screen lists stories but never says "place a card on the reader". Nothing teaches that cards are placed, not tapped or waved. | start screen | A permanent illustrated hint on the start screen + a printed instruction card in the box. |

Also worth testing explicitly, because the code has a rule that is invisible to the player: **item cards do nothing when scanned** — items are granted by entering scenes. A child who finds a 🗝️ Key card and tries to "use" it gets an ignore message. Is that understandable? (Heuristics 2, 5, 9.)

> Alternative to the workbook: the **Cognitive Walkthrough** (HE slides p.7–10) — the four questions per step. If you'd rather do that, run it over the flowchart from Ex. B, step by step. The professor allows either; the workbook is faster with a non-expert tester.

---

## 6. Deliverable 4 & 5 — results and final design

Write up findings in this shape (HE slides p.14):

**Specific issues identified** — grouped as heuristic violations / usability concerns / accessibility issues / consistency problems / UX gaps.

**Prioritized recommendations:**

| Priority | Criterion | Likely candidates from the list above |
|---|---|---|
| 🔴 **Critical (must fix)** | Blocks the goal or breaks the interaction model | Card↔screen colour mismatch (#4/#6); invisible error feedback (#1); no way to exit fullscreen (#3) |
| 🟡 **Important (should fix)** | Causes hesitation or needs an adult to rescue | No undo (#3); unhelpful error wording (#9); no "how to play" (#10) |
| 🟢 **Nice-to-have (consider)** | Polish | Hide the UID (#2/#8); accelerators for repeat players (#7); sound design |

Then produce the **final wireframe** with the critical and important issues fixed, side by side with the original, and a short changelog: *issue → evidence (which test, which heuristic) → change made*.

That "evidence" column is what turns this from an opinion into an evaluation, and it's the bit that gets marked.

---

## 7. Suggested order of work

1. Storyboard sketches (paper, 1–2 h) → photos.
2. Wireframe + flowchart from the storyboard (2 h).
3. Cut the paper prototype (1 h).
4. Bodystorming session with a tester, 90 min per the slides — photograph everything.
5. Heuristic evaluation with the same or a second tester, on the paper prototype (1 h).
6. Consolidate findings, prioritize, redraw the final wireframe (2 h).
7. *Optional but strong:* implement the 🔴 critical fixes in the actual code and show before/after screenshots. We already know exactly where each one lives.
