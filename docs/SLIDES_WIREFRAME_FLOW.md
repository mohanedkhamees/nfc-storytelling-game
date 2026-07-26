# Slides — Wireframe & Interaction Flow

Slide-ready text. Short lines, no paragraphs — design is yours.

---

## Slide 1 — Architecture ≠ Wireframe

**Title:** Wireframe & Interaction Flow
**Subtitle:** How the child moves through the system, state by state

**Left column — System Architecture Diagram**
Shows:
• technical components
• and data flow

e.g.:
`NFC card → RC522 → Arduino → USB serial → CardManager → StoryEngine → Screen`

**Right column — Wireframe & Interaction Flow**
Shows:
• what the child sees and touches
• and how they move between states

e.g.:
`START → SCENE → (check card) → SCENE → ENDING → restart`

**Footer line**
> Our interface is not only the screen — it is the **table**: cards, reader and display.
> So our wireframe has two layers: the physical setup and the screen states.

---

## Slide 2 — Wireframe, layer 1: the physical setup

**Title:** Wireframe — the table
**Subtitle:** The interface a child actually touches

Top-down sketch, four zones:

```
            ┌─────────────────────────┐
            │         SCREEN          │   display only — no buttons
            └─────────────────────────┘
                 ┌───────────┐
                 │  READER   │             the one active spot
                 └───────────┘
   [🐰][🔍][🚀]   [💬][🏃][🗝️][✨][🛡️][⚔️][🙈][🚪]   [🔄]
    story cards          action cards               restart

            ┌─────────────────────────┐
            │      PLAYED CARDS       │   kept away from the reader
            └─────────────────────────┘
```

**Label each zone**
• **Screen** — reports state, never accepts input
• **Reader** — the single point of contact; ~2 cm range
• **Deck** — 12 printed cards; this is the input device
• **Played-cards area** — deliberately far from the reader

**Why the fourth zone exists**
> A card left near the reader is re-detected and re-triggers the story.
> The fix is physical, not software: give played cards somewhere to go.
> This came out of testing, not planning.

---

## Slide 3 — Wireframe, layer 2: the three screens

**Title:** Wireframe — the screen states
**Subtitle:** Three states, one persistent footer

```
   START                    SCENE                    ENDING
 ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
 │ pick a story │     │ title            │     │ 🎉 The End       │
 │              │     │ ┌────┐  story    │     │ ┌────┐  ending   │
 │ [🐰][🔍][🚀] │     │ │IMG │  text     │     │ │IMG │  text     │
 │              │     │ └────┘           │     │ └────┘           │
 │              │     │ ( o )( o )( o )  │     │  scan 🔄 to      │
 │              │     │ backpack: ...    │     │  play again      │
 ├──────────────┤     ├──────────────────┤     ├──────────────────┤
 │ status │ prompt │ last scan │  ← always visible, all three states
 └──────────────┴──────────────┴──────────┘
```

**Region labels**
• **Choice row** — mirrors the physical cards: same icon, same colour
• **Backpack** — shows held items so nothing must be remembered
• **Footer** — reader connected? · what to do now · what was just scanned

**One design rule**
> No screen has a gameplay control.
> If a button existed, the child would use it — and the cards would become decoration.

---

## Slide 4 — Interaction flow

**Title:** Interaction flow
**Subtitle:** Three states, and every refusal returns you to where you were

```
        ┌──────────────────┐
        │  START SCREEN    │ ← waiting for a story card
        └────────┬─────────┘
                 │ place 🐰 story card
                 ▼
        ┌──────────────────┐
        │  SCENE           │ ←──────────────┐
        │  waiting for a   │                │  place another
        │  choice card     │                │  action card
        └────────┬─────────┘                │
                 │ place an action card     │
                 ▼                          │
        ┌──────────────────┐                │
        │  CHECK           │                │
        │  valid here?     │                │
        │  item needed?    │                │
        └───┬─────────┬────┘                │
     refuse │         │ allow               │
            │         ▼                     │
            │   next scene ─────────────────┘
            │         │
            │         │ scene is an ending
            ▼         ▼
      stay put   ┌──────────────────┐
      + message  │  ENDING          │
                 │  scan 🔄 Restart │
                 └────────┬─────────┘
                          │ place 🔄
                          └──────► back to first scene
```

**The four refusals** — all keep the current scene, nothing is lost
• Card is not a choice here → "This card cannot be used here."
• Scene needs an item you do not have → names the missing item
• Card is not registered → "Unknown card scanned."
• Story already finished → "Scan Restart to play again."

---

## Slide 5 — The same flow as a swimlane

**Title:** One loop, lane by lane
*(Worksheet format: User · Action · Interface · Change of state · Function)*

| User | Action | Interface | Change of state | Function |
|---|---|---|---|---|
| Wants to start | Looks at the screen | START shows 3 story cards | idle → waiting | — |
| Chooses | Picks up 🐰 Benny | no change yet | — | — |
| Commits | **Places card on reader** | footer: "Last scan: Benny" | waiting → playing | UID read, story loaded |
| Listens | Adult reads the text | SCENE: image, text, 3 choices | — | scene rendered |
| Decides | Finds the matching card | choice row shows the options | — | — |
| Commits | Places 🗝️ Key | new scene, item in backpack | scene A → scene B | choice validated, item granted |
| Errs | Places a card not offered here | message for 4 s | **no change** | invalid action |
| Finishes | Places 🔄 Restart | back to the first scene | ended → playing | state reset |

**Read the "Change of state" column**
> Only three rows change state. Everything else is the child looking, deciding and reaching.
> That is the interaction we designed for — the scan is the smallest part of it.

---

## Slide 6 — What the flow tells us *(optional, if time)*

**Title:** What the flow made visible

• **One input, three states** — the whole system is smaller than it looks
• **Every refusal is a self-loop** — a wrong card costs nothing
• **The footer is the only constant** — it answers: is it alive, what now, did that work
• **No undo** — the flow has no backward arrow, and our evaluation flagged this
• **The physical layer matters** — the played-cards zone exists because of a real failure

---

## Speaker notes

**The line to say on slide 1**
> A system diagram answers "how did we build it". A wireframe answers "what does the
> child see and do". Same product, different question.

**If asked why there is no undo**
> The flow diagram has no backward arrow. We found that in the evaluation and rated it
> "should fix" — a ↩️ Go Back card is the fix, and it costs one card and one transition.

**If asked how the wireframe differs from the story map**
> The story map is content: 29 scenes of Benny. The wireframe is the interface: three
> screens that any of the three stories flow through.
