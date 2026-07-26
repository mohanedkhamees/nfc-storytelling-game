# User Stories — Tangible NFC Interactive Storybook

Presentation-ready text. Same structure as the Voice Control example, with
**Trigger phrase → Trigger action**, because our input is a physical card placed on
a reader rather than an utterance.

---

## Framing slide (answers the three worksheet questions)

**Target user** — Children aged 6–9, pre-readers and early readers, who cannot yet
navigate a menu and are not fluent with a mouse or keyboard.

**Goal the interface allows** — Choose a story, steer it by choosing what the
character does next, collect story items, reach one of several endings, and replay.

**Context of use** — A shared table: screen standing up, NFC reader in front of it,
a deck of twelve picture cards spread out within reach. Indoors, social, often with
an adult reading aloud. No mouse, no keyboard, no touchscreen.

**Core interaction principle** — The card *is* the input device. The screen reports
state; it has no gameplay controls at all.

---

## Story 1 — Starting a story

**Persona**
Lina, 7 (she/her), at the after-school club, has never used the system before.

**Scenario**
She sees a glowing screen and a box of picture cards, and wants to know what it does.

**Trigger action**
Places the 🐰 **Benny** card on the reader.

**Storyboard sequence**
1. At the table — screen shows three story cards and "Waiting for your NFC card"
2. Recognition — she matches the 🐰 rabbit on screen to the 🐰 card in the deck
3. Contact — places the card flat on the reader
4. System reads — Arduino sends the card's UID, Python maps it to "Benny"
5. Story opens — first scene appears: picture, text, three choices

**System behaviour**
The reader detects the card and sends its ID over USB. The application maps that ID
to a story card and loads the story. The start screen is replaced by the first scene,
and the footer confirms "Last scan: Benny". Total time under one second.

**Design value**
• No instructions needed — the screen shows the cards to look for
• Discoverable: the icon on screen matches the icon on the card
• One physical action replaces a menu
• Nothing to read before you can begin

---

## Story 2 — Making a choice (the core loop)

**Persona**
Lina, 7 (she/her), now two scenes into Benny's story.

**Scenario**
Benny finds a squirrel trapped in a thorn bush. She has to decide what he does.

**Trigger action**
Places the 💬 **Talk** card on the reader.

**Storyboard sequence**
1. Scene shown — picture of the trapped squirrel, three coloured options
2. Decision — she reads the icons: 💬 Talk, ⚔️ Sword, 🙈 Hide
3. Search — looks down at the deck and finds the matching card by colour and icon
4. Contact — places 💬 Talk on the reader
5. Consequence — new scene, and a red apple appears in her backpack strip

**System behaviour**
The engine checks the scanned card against the choices available in the current scene,
moves to the target scene, and applies whatever that scene grants. The backpack strip
updates so the item is visible, not remembered.

**Design value**
• The choice is made with the hand, not a pointer
• Consequence is immediate and visible
• Recognition over recall — held items stay on screen
• Same three cards mean different things in different scenes, so twelve cards
  cover sixty different decisions

---

## Story 3 — A card that does not fit here

**Persona**
Lina, 7 (she/her), mid-story, excited and grabbing cards quickly.

**Scenario**
She likes the ⚔️ Sword card and places it in a scene where it is not one of the options.

**Trigger action**
Places the ⚔️ **Sword** card on the reader in a scene offering only Talk, Run and Key.

**Storyboard sequence**
1. Scene shown — three options, Sword is not among them
2. Wrong card — she places Sword anyway
3. System checks — the card matches no choice in this scene
4. Refusal — the scene does not change; a message appears in the footer
5. Recovery — she looks back at the coloured options and picks a valid card

**System behaviour**
The engine returns an "invalid action" result. The current scene is preserved — nothing
is lost — and the status bar shows "This card cannot be used here." for four seconds
before restoring the normal prompt.

**Design value**
• A wrong card costs nothing; the story never breaks
• The system stays silent about *why*, which our heuristic evaluation flagged
  as the weakest point in the interaction
• Identified fix: name the valid cards in the message and add a sound, because a
  child looking down at the deck misses a four-second text change

*(This is our honest friction panel — it is where the heuristic evaluation findings
come from, so it is worth showing rather than hiding.)*

---

## Story 4 — A path that needs an item

**Persona**
Lina, 7 (she/her), at the broken bridge, has not visited Grandma Rabbit.

**Scenario**
She wants to cross the bridge with the shield, but Benny never collected one.

**Trigger action**
Places the 🛡️ **Shield** card on the reader.

**Storyboard sequence**
1. Scene shown — broken bridge, text hints that "a big strong shield could help"
2. Attempt — she places 🛡️ Shield
3. System checks — the target scene requires the Leaf Shield; the backpack is empty
4. Refusal — Benny stays at the bridge, and the missing item is named
5. Alternative — she takes the turtle instead and still reaches the tower

**System behaviour**
Items are never picked up by scanning a card — a scene grants them when the child
enters it. Gates are checked on the *target* scene before the move commits, so the
player stays where they are. Every gate has an ungated alternative, so no route can
dead-end.

**Design value**
• The physical card cannot cheat the rule — you must have been somewhere to hold something
• Failure redirects instead of blocking
• State lives in the story, not in the child's memory
• Appropriate: consequences without punishment, for a 7-year-old audience

---

## Story 5 — Playing it again differently

**Persona**
Lina, 7 (she/her), has just reached the Golden Ending.

**Scenario**
She wants to find out what happens if Benny hides from the squirrel instead of helping.

**Trigger action**
Places the 🔄 **Restart** card on the reader.

**Storyboard sequence**
1. Ending shown — celebration screen, picture, "Scan Restart to play again"
2. Curiosity — she wonders about the paths she did not take
3. Contact — places 🔄 Restart
4. System resets — story returns to the first scene, backpack emptied
5. New route — this time she chooses 🙈 Hide and reaches a different ending

**System behaviour**
The Restart card resets the story to its start scene and clears the inventory. Twenty-nine
scenes and three endings mean the second run genuinely differs from the first.

**Design value**
• Replay is one card, not a menu
• Playful: the branching invites experimentation
• Three endings, none of them a failure screen
• A five-minute session, sized for one sitting

---

## Story 6 — Two children at one table

**Persona**
Lina, 7 (she/her) and Omar, 8 (he/him), sharing the table with a parent nearby.

**Scenario**
They disagree about what Benny should do next.

**Trigger action**
They negotiate, then one of them places the agreed card.

**Storyboard sequence**
1. Scene shown — three options visible to both children at once
2. Disagreement — Omar wants Run, Lina wants Talk
3. Negotiation — they argue over the physical cards, holding them up
4. Agreement — Lina places 💬 Talk on the reader
5. Shared outcome — both watch the same screen react

**System behaviour**
The reader accepts one card at a time and ignores repeat reads of the same card for
2.5 seconds, so a contested handover cannot double-trigger the story.

**Design value**
• The interface is the table, not a personal screen
• Cards are visible to everyone, so the choice is a shared, negotiable object
• Turn-taking is enforced by physics, not by software
• A mouse would have given one child control; the deck does not

---

## Which to show in a 10-minute talk

Show **Story 1** and **Story 2** — they establish the persona, the context and the core
loop. If time allows, add **Story 3**, because it sets up the heuristic-evaluation
section later and shows you tested honestly.

Keep 4–6 in the written documentation. Story 6 is the strongest argument for *why*
this had to be a tangible interface, so it is worth mentioning verbally even if the
slide is skipped.
