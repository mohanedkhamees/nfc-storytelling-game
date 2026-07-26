#!/usr/bin/env python3
"""Generate a Mermaid flow map of a branching story from its JSON file.

Produces ``docs/story-map-<id>.md`` showing every scene, every card-driven
transition, the items each scene grants, and the item gates. Run it again after
editing a story so the diagram never drifts from the content.

Usage::

    python generate_story_map.py            # all stories
    python generate_story_map.py benny      # one story
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from story_loader import Scene, Story, StoryLoader

PROJECT_ROOT = Path(__file__).resolve().parent
STORIES_DIR = PROJECT_ROOT / "stories"
DOCS_DIR = PROJECT_ROOT / "docs"

# Narrative acts, used to group scenes into readable clusters. Stories without an
# entry here fall back to grouping by distance from the start scene.
ACTS: dict[str, list[tuple[str, list[str]]]] = {
    "benny": [
        ("1 · At Home", ["bunny_home", "grandma_rabbit", "locked_box", "golden_key", "take_leaf_shield"]),
        ("2 · The Forest", ["forest_path", "squirrel_help", "cut_thorns", "ignore_squirrel", "wise_tree", "glowing_mushrooms"]),
        ("3 · The River", ["broken_bridge", "cross_bridge", "river_turtle", "riverbank", "water_song"]),
        ("4 · Fina the Fox", ["fox_shadow", "scare_fox", "fox_meeting", "heal_sister", "crystal_promise"]),
        ("5 · The Tower", ["mountain_tower", "locked_tower_fail", "vine_lift", "tower_gate", "crystal_room"]),
        ("6 · Endings", ["golden_ending", "silver_ending", "lost_ending"]),
    ],
}

# Emoji per NFC card, so an edge label reads like the physical card.
CARD_EMOJI = {
    "Sword": "⚔️", "Magic": "✨", "Shield": "🛡️", "Run": "🏃",
    "Key": "🗝️", "Talk": "💬", "Hide": "🙈", "Open Door": "🚪",
}


def scene_depths(story: Story) -> dict[str, int]:
    """Return each scene's distance in card scans from the start scene."""
    depths = {story.start_scene: 0}
    queue = deque([story.start_scene])
    while queue:
        current = queue.popleft()
        scene = story.get_scene(current)
        if scene is None:
            continue
        for target in scene.choices.values():
            if target not in depths:
                depths[target] = depths[current] + 1
                queue.append(target)
    return depths


def act_groups(story: Story) -> list[tuple[str, list[str]]]:
    """Return ``(act title, scene ids)`` groups for this story."""
    configured = ACTS.get(story.id)
    if configured:
        grouped = {sid for _, ids in configured for sid in ids}
        leftover = [sid for sid in story.scenes if sid not in grouped]
        if leftover:
            return configured + [("Ungrouped", leftover)]
        return configured

    depths = scene_depths(story)
    by_depth: dict[int, list[str]] = {}
    for sid in story.scenes:
        by_depth.setdefault(depths.get(sid, -1), []).append(sid)
    return [(f"Step {d}", sorted(ids)) for d, ids in sorted(by_depth.items())]


def node_label(scene: Scene) -> str:
    """Build the box caption: title plus item gains and gates."""
    title = scene.title or scene.id.replace("_", " ").title()
    lines = [title]
    if scene.required_items:
        lines.append("🔒 needs " + ", ".join(scene.required_items))
    if scene.gained_items:
        lines.append("➕ " + ", ".join(scene.gained_items))
    if scene.lost_items:
        lines.append("➖ " + ", ".join(scene.lost_items))
    # <br/> keeps Mermaid labels multi-line; quotes are stripped to stay valid.
    return "<br/>".join(line.replace('"', "") for line in lines)


def build_mermaid(story: Story) -> str:
    """Render the story graph as a Mermaid flowchart."""
    # LR keeps the six acts flowing sideways, which lays out far more compactly
    # than TD once the back-edges are included — and fits a 16:9 slide.
    out: list[str] = ["flowchart LR"]
    endings: list[str] = []
    gated: list[str] = []
    givers: list[str] = []

    for index, (act_title, scene_ids) in enumerate(act_groups(story)):
        # Mermaid ids must not start with a digit, hence the "act" prefix.
        safe_act = f"act{index}"
        out.append(f'    subgraph {safe_act}["{act_title}"]')
        out.append("        direction TB")
        for sid in scene_ids:
            scene = story.get_scene(sid)
            if scene is None:
                continue
            label = node_label(scene)
            if scene.is_ending:
                out.append(f'        {sid}(["{label}"])')
                endings.append(sid)
            else:
                out.append(f'        {sid}["{label}"]')
            if scene.required_items:
                gated.append(sid)
            elif scene.gained_items:
                givers.append(sid)
        out.append("    end")

    out.append("")
    # Edges that lead deeper into the story are drawn solid so the forward flow
    # reads at a glance; edges that loop back or sideways are dotted so they
    # recede instead of competing with it.
    depths = scene_depths(story)
    for sid, scene in story.scenes.items():
        for card, target in sorted(scene.choices.items()):
            emoji = CARD_EMOJI.get(card, "")
            label = f"{emoji} {card}".strip()
            forward = depths.get(target, 0) > depths.get(sid, 0)
            arrow = "-->" if forward else "-.->"
            out.append(f'    {sid} {arrow}|"{label}"| {target}')

    out.append("")
    plain = [
        sid
        for sid in story.scenes
        if sid not in endings and sid not in gated and sid not in givers and sid != story.start_scene
    ]
    out.append("    classDef scene fill:#FFFFFF,stroke:#8496A6,stroke-width:1.5px,color:#1B2733")
    if plain:
        out.append(f"    class {','.join(plain)} scene")
    out.append("    classDef start fill:#FFE785,stroke:#C9A227,stroke-width:3px,color:#1A1A2E")
    out.append("    classDef ending fill:#8FE39A,stroke:#3C9A50,stroke-width:3px,color:#1A1A2E")
    out.append("    classDef gate fill:#FFA8A8,stroke:#C25454,stroke-width:2px,color:#1A1A2E")
    out.append("    classDef giver fill:#C6E86B,stroke:#7FA32E,stroke-width:2px,color:#1A1A2E")
    out.append(f"    class {story.start_scene} start")
    if endings:
        out.append(f"    class {','.join(endings)} ending")
    if gated:
        out.append(f"    class {','.join(gated)} gate")
    if givers:
        out.append(f"    class {','.join(givers)} giver")
    return "\n".join(out)


def build_act_mermaid(story: Story, act_title: str, scene_ids: list[str]) -> str:
    """Render one act as a flowchart with no subgraphs.

    Mermaid clips edges that cross a subgraph boundary, so a cross-act arrow ends
    on the cluster rectangle instead of on the scene it actually points at. Per-act
    diagrams avoid clusters entirely: every arrow attaches to a real box. Scenes in
    other acts appear as dashed "ghost" boxes marked with their act number.
    """
    act_index = {sid: i for i, (_t, ids) in enumerate(act_groups(story)) for sid in ids}
    inside = set(scene_ids)
    depths = scene_depths(story)

    ghosts: set[str] = set()
    edges: list[tuple[str, str, str, bool]] = []
    for sid, scene in story.scenes.items():
        for card, target in sorted(scene.choices.items()):
            if sid in inside or target in inside:
                if sid not in inside:
                    ghosts.add(sid)
                if target not in inside:
                    ghosts.add(target)
                forward = depths.get(target, 0) > depths.get(sid, 0)
                edges.append((sid, card, target, forward))

    out = ["flowchart LR"]
    endings, gated, givers, plain = [], [], [], []
    for sid in scene_ids:
        scene = story.get_scene(sid)
        if scene is None:
            continue
        label = node_label(scene)
        if scene.is_ending:
            out.append(f'    {sid}(["{label}"])')
            endings.append(sid)
        else:
            out.append(f'    {sid}["{label}"]')
        if scene.required_items:
            gated.append(sid)
        elif scene.gained_items:
            givers.append(sid)
        elif sid != story.start_scene:
            plain.append(sid)

    for sid in sorted(ghosts):
        scene = story.get_scene(sid)
        title = (scene.title if scene and scene.title else sid).replace('"', "")
        marker = "①②③④⑤⑥"[act_index.get(sid, 0)]
        out.append(f'    {sid}["{marker} {title}"]')

    out.append("")
    for src, card, target, forward in edges:
        emoji = CARD_EMOJI.get(card, "")
        arrow = "-->" if forward else "-.->"
        out.append(f'    {src} {arrow}|"{emoji} {card}".strip()| {target}'.replace('".strip()|', '"|'))

    out.append("")
    out.append("    classDef scene fill:#FFFFFF,stroke:#8496A6,stroke-width:1.5px,color:#1B2733")
    out.append("    classDef ghost fill:#EDF2F7,stroke:#A9BACB,stroke-width:1px,stroke-dasharray:4 3,color:#5D6E7E")
    out.append("    classDef start fill:#FFE785,stroke:#C9A227,stroke-width:3px,color:#1A1A2E")
    out.append("    classDef ending fill:#8FE39A,stroke:#3C9A50,stroke-width:3px,color:#1A1A2E")
    out.append("    classDef gate fill:#FFA8A8,stroke:#C25454,stroke-width:2px,color:#1A1A2E")
    out.append("    classDef giver fill:#C6E86B,stroke:#7FA32E,stroke-width:2px,color:#1A1A2E")
    if plain:
        out.append(f"    class {','.join(plain)} scene")
    if ghosts:
        out.append(f"    class {','.join(sorted(ghosts))} ghost")
    if story.start_scene in inside:
        out.append(f"    class {story.start_scene} start")
    if endings:
        out.append(f"    class {','.join(endings)} ending")
    if gated:
        out.append(f"    class {','.join(gated)} gate")
    if givers:
        out.append(f"    class {','.join(givers)} giver")
    return "\n".join(out)


def build_markdown(story: Story) -> str:
    """Wrap the flowchart in a documentation page with a legend and stats."""
    depths = scene_depths(story)
    edges = sum(len(s.choices) for s in story.scenes.values())
    endings = [s for s in story.scenes.values() if s.is_ending]
    gates = {
        item
        for scene in story.scenes.values()
        for item in scene.required_items
    }
    longest = max(depths.values()) if depths else 0

    lines = [
        f"# Story map — {story.title}",
        "",
        "*Generated by `generate_story_map.py`. Re-run it after editing the story.*",
        "",
        "| | |",
        "|---|---|",
        f"| Scenes | {len(story.scenes)} |",
        f"| Card transitions | {edges} |",
        f"| Endings | {len(endings)} |",
        f"| Item gates | {len(gates)} ({', '.join(sorted(gates))}) |",
        f"| Shortest route to an ending | {min((depths[s.id] for s in endings), default=0)} scans |",
        f"| Deepest scene | {longest} scans from the start |",
        "",
        "**Legend** — 🟡 start · 🟢 ending · 🔴 needs an item to enter · 🟩 gives an item.",
        "",
        "Arrow labels are the NFC card you place on the reader. **Solid arrows** carry the story "
        "forward; **dotted arrows** loop back or sideways to a scene the child could already reach, "
        "so the forward path stays readable.",
        "",
        "```mermaid",
        build_mermaid(story),
        "```",
        "",
        "> **Caveat on this whole-story view.** Mermaid clips edges where they cross an act",
        "> boundary, so a cross-act arrow visually ends on the act rectangle rather than on the",
        "> scene it points at. The per-act diagrams below have no act boxes, so every arrow",
        "> attaches to a real scene. Use those when the exact source and target matter.",
        "",
        "## Act by act",
        "",
        "Dashed grey boxes are scenes in another act, marked with that act's number.",
        "",
    ]

    for index, (act_title, scene_ids) in enumerate(act_groups(story), start=1):
        lines += [
            f"### {act_title}",
            "",
            "```mermaid",
            build_act_mermaid(story, act_title, scene_ids),
            "```",
            "",
        ]

    lines += [
        "## Re-rendering the image",
        "",
        "The PNG/SVG in `docs/img/` are produced with mermaid-cli. After editing the story,",
        "re-run this script, then:",
        "",
        "```powershell",
        f"cd docs/img",
        f"mmdc -i story-map-{story.id}.mmd -o story-map-{story.id}.png "
        "-c mermaid-config.json -p puppeteer-config.json -b \"#FFFFFF\" -w 3600 -s 2",
        "```",
        "",
        "`puppeteer-config.json` points at the installed Chrome, because the Chromium that",
        "ships with Puppeteer fails to launch on this machine (`0xC000007B`).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    loader = StoryLoader(STORIES_DIR)
    story_ids = args or loader.list_available_stories()

    DOCS_DIR.mkdir(exist_ok=True)
    for story_id in story_ids:
        try:
            story = loader.load_story(story_id)
        except Exception as exc:
            print(f"skipped {story_id!r}: {exc}")
            continue
        target = DOCS_DIR / f"story-map-{story.id}.md"
        target.write_text(build_markdown(story), encoding="utf-8")
        edges = sum(len(s.choices) for s in story.scenes.values())
        print(f"wrote {target.relative_to(PROJECT_ROOT)} ({len(story.scenes)} scenes, {edges} transitions)")

        # Per-act diagrams, where every arrow attaches to a real scene box.
        img_dir = DOCS_DIR / "img"
        img_dir.mkdir(exist_ok=True)
        for index, (act_title, scene_ids) in enumerate(act_groups(story), start=1):
            mmd = build_act_mermaid(story, act_title, scene_ids)
            path = img_dir / f"story-act{index}-{story.id}.mmd"
            path.write_text(mmd + "\n", encoding="utf-8")
            print(f"  act {index}: {act_title} ({len(scene_ids)} scenes) -> {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
