#!/usr/bin/env python3
"""Audit branching story JSON files for structural integrity and completability.

Loads all stories via :class:`StoryLoader`, validates scene graphs, simulates
reachable paths, and prints a per-story report. Exits with code 1 when broken
links or other structural errors are found.
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from story_loader import Scene, Story, StoryLoadError, StoryLoader

VALID_NFC_ACTIONS = frozenset(
    {"Sword", "Magic", "Shield", "Run", "Key", "Talk", "Hide", "Open Door", "Restart"}
)
VALID_ACTION_KEYS = VALID_NFC_ACTIONS

PROJECT_ROOT = Path(__file__).resolve().parent
STORIES_DIR = PROJECT_ROOT / "stories"


@dataclass
class SceneReport:
    """Validation results for a single scene."""

    scene_id: str
    ok: bool = True
    issues: list[str] = field(default_factory=list)


@dataclass
class StoryReport:
    """Aggregated audit results for one story."""

    story: Story
    source: Path
    scene_reports: dict[str, SceneReport] = field(default_factory=dict)
    broken_links: list[str] = field(default_factory=list)
    dead_end_scenes: list[str] = field(default_factory=list)
    orphan_scenes: list[str] = field(default_factory=list)
    unreachable_endings: list[str] = field(default_factory=list)
    invalid_action_keys: list[str] = field(default_factory=list)
    label_issues: list[str] = field(default_factory=list)
    paths_not_reaching_ending: list[str] = field(default_factory=list)
    inventory_trap_states: list[str] = field(default_factory=list)

    @property
    def total_scenes(self) -> int:
        return len(self.story.scenes)

    @property
    def total_endings(self) -> int:
        return sum(1 for scene in self.story.scenes.values() if scene.is_ending)

    @property
    def total_branches(self) -> int:
        return sum(len(scene.choices) for scene in self.story.scenes.values())

    @property
    def has_errors(self) -> bool:
        return bool(
            self.broken_links
            or self.dead_end_scenes
            or self.unreachable_endings
            or self.invalid_action_keys
            or self.label_issues
            or self.paths_not_reaching_ending
            or self.inventory_trap_states
            or any(not report.ok for report in self.scene_reports.values())
        )

    @property
    def ok(self) -> bool:
        """True when the story has no structural or inventory-trap errors."""
        return not self.has_errors


def _validate_choice_labels(scene: Scene) -> list[str]:
    """Return errors when choice_labels keys are not present in choices."""
    issues: list[str] = []
    choice_keys = set(scene.choices)
    for label_key in scene.choice_labels:
        if label_key not in choice_keys:
            issues.append(
                f"choice_labels key {label_key!r} is not in choices {sorted(choice_keys)!r}"
            )
    return issues


def audit_story(story: Story) -> StoryReport:
    """Validate one loaded story and return an audit report."""
    return _audit_story_graph(story)


def _audit_story_graph(story: Story) -> StoryReport:
    """Build the directed graph and validate structural rules."""
    report = StoryReport(story=story, source=STORIES_DIR / f"{story.id}.json")
    scene_ids = set(story.scenes)

    for scene in story.scenes.values():
        scene_report = SceneReport(scene_id=scene.id)
        label_issues = _validate_choice_labels(scene)
        if label_issues:
            scene_report.ok = False
            scene_report.issues.extend(label_issues)
            report.label_issues.extend(
                f"{scene.id}: {issue}" for issue in label_issues
            )

        if scene.is_ending and scene.choices:
            scene_report.ok = False
            msg = "ending scene must not have choices"
            scene_report.issues.append(msg)
            report.broken_links.append(f"{scene.id}: {msg}")

        if not scene.is_ending and not scene.choices:
            scene_report.ok = False
            msg = "non-ending scene has no outgoing choices"
            scene_report.issues.append(msg)
            report.dead_end_scenes.append(scene.id)

        for action, target in scene.choices.items():
            if action not in VALID_NFC_ACTIONS:
                scene_report.ok = False
                msg = f"choice key {action!r} is not a valid NFC card name"
                scene_report.issues.append(msg)
                report.invalid_action_keys.append(f"{scene.id}: {msg}")

            if target not in scene_ids:
                scene_report.ok = False
                msg = f"choice {action!r} -> {target!r} (unknown scene)"
                scene_report.issues.append(msg)
                report.broken_links.append(f"{scene.id}: {msg}")

        report.scene_reports[scene.id] = scene_report

    reachable = _reachable_from_start(story)
    report.orphan_scenes = sorted(scene_ids - reachable)

    endings = [sid for sid, scene in story.scenes.items() if scene.is_ending]
    report.unreachable_endings = sorted(e for e in endings if e not in reachable)

    report.paths_not_reaching_ending = _find_dead_branch_states(story)
    report.inventory_trap_states = _find_inventory_trap_states(story)

    return report


def _reachable_from_start(story: Story) -> set[str]:
    """Return scene ids reachable from start_scene via any choice edge."""
    reachable: set[str] = set()
    queue: deque[str] = deque([story.start_scene])

    while queue:
        scene_id = queue.popleft()
        if scene_id in reachable:
            continue
        reachable.add(scene_id)
        scene = story.scenes.get(scene_id)
        if scene is None:
            continue
        for target in scene.choices.values():
            if target not in reachable:
                queue.append(target)

    return reachable


def _find_dead_branch_states(story: Story) -> list[str]:
    """Find non-ending scenes from which no path can reach any ending.

    Uses iterative deepening over choice edges (ignoring inventory gates).
    Cycles are handled by tracking visited scene ids on each DFS branch.
    """
    endings = {sid for sid, scene in story.scenes.items() if scene.is_ending}
    dead_states: list[str] = []

    def can_reach_ending(scene_id: str, visited: frozenset[str]) -> bool:
        if scene_id in endings:
            return True
        scene = story.scenes.get(scene_id)
        if scene is None or not scene.choices:
            return False
        for target in scene.choices.values():
            if target in visited:
                continue
            if can_reach_ending(target, visited | {target}):
                return True
        return False

    for scene_id, scene in story.scenes.items():
        if scene.is_ending:
            continue
        if not can_reach_ending(scene_id, frozenset({scene_id})):
            dead_states.append(scene_id)

    return dead_states


def _find_inventory_trap_states(story: Story) -> list[str]:
    """Return non-ending states where every choice is blocked by missing items."""
    start = (story.start_scene, frozenset())
    queue: deque[tuple[str, frozenset[str]]] = deque([start])
    visited: set[tuple[str, frozenset[str]]] = {start}
    traps: list[str] = []

    while queue:
        scene_id, inventory = queue.popleft()
        scene = story.scenes.get(scene_id)
        if scene is None or scene.is_ending:
            continue

        workable = 0
        for _action, target_id in scene.choices.items():
            target = story.scenes.get(target_id)
            if target is None:
                continue
            if any(item not in inventory for item in target.required_items):
                continue
            workable += 1
            new_inventory = set(inventory)
            for item in target.gained_items:
                new_inventory.add(item)
            for item in target.lost_items:
                new_inventory.discard(item)
            state = (target_id, frozenset(new_inventory))
            if state not in visited:
                visited.add(state)
                queue.append(state)

        if scene.choices and workable == 0:
            inv_text = ", ".join(sorted(inventory)) or "(empty)"
            traps.append(f"{scene_id} with inventory [{inv_text}]")

    return traps


def _print_story_report(report: StoryReport) -> None:
    """Print a human-readable audit report for one story."""
    story = report.story
    status = "❌ FAIL" if report.has_errors else "✅ PASS"
    print(f"\n{'=' * 72}")
    print(f"Story: {story.title!r} ({story.id}) — {status}")
    print(f"{'=' * 72}")
    print(f"  Scenes:    {report.total_scenes}")
    print(f"  Endings:   {report.total_endings}")
    print(f"  Branches:  {report.total_branches} choice edges")
    print(f"  Start:     {story.start_scene}")

    if report.broken_links:
        print("\n  Broken links:")
        for item in report.broken_links:
            print(f"    ❌ {item}")
    else:
        print("\n  Broken links: none ✅")

    if report.dead_end_scenes:
        print("\n  Dead-end non-ending scenes:")
        for scene_id in report.dead_end_scenes:
            print(f"    ❌ {scene_id}")
    else:
        print("\n  Dead-end non-ending scenes: none ✅")

    if report.orphan_scenes:
        print("\n  Orphan scenes (unreachable from start):")
        for scene_id in report.orphan_scenes:
            print(f"    ❌ {scene_id}")
    else:
        print("\n  Orphan scenes: none ✅")

    if report.unreachable_endings:
        print("\n  Unreachable endings:")
        for scene_id in report.unreachable_endings:
            print(f"    ❌ {scene_id}")
    else:
        print("\n  Unreachable endings: none ✅")

    if report.invalid_action_keys:
        print("\n  Invalid NFC action keys:")
        for item in report.invalid_action_keys:
            print(f"    ❌ {item}")
    else:
        print("\n  NFC action keys: all valid ✅")

    if report.label_issues:
        print("\n  choice_labels issues:")
        for item in report.label_issues:
            print(f"    ❌ {item}")
    else:
        print("\n  choice_labels: all keys match choices ✅")

    if report.paths_not_reaching_ending:
        print("\n  Scenes with no path to any ending:")
        for scene_id in report.paths_not_reaching_ending:
            print(f"    ❌ {scene_id}")
    else:
        print("\n  All non-ending scenes reach an ending ✅")

    if report.inventory_trap_states:
        print("\n  Inventory trap states (all choices blocked):")
        for item in report.inventory_trap_states[:10]:
            print(f"    ❌ {item}")
        if len(report.inventory_trap_states) > 10:
            print(f"    ... and {len(report.inventory_trap_states) - 10} more")
    else:
        print("\n  Inventory traps: none ✅")

    print("\n  Per-scene choices:")
    for scene_id in sorted(report.scene_reports):
        scene = story.scenes[scene_id]
        scene_report = report.scene_reports[scene_id]
        marker = "✅" if scene_report.ok else "❌"
        ending_tag = " [ENDING]" if scene.is_ending else ""
        print(f"    {marker} {scene_id}{ending_tag}")
        if not scene.choices:
            print("        (no choices)")
            continue
        for action, target in sorted(scene.choices.items()):
            target_ok = target in story.scenes
            edge_marker = "✅" if target_ok else "❌"
            label = scene.choice_labels.get(action, action)
            print(f"        {edge_marker} {action!r} -> {target!r}  ({label})")


def audit_all_stories(stories_dir: Path = STORIES_DIR) -> list[StoryReport]:
    """Load and audit every story JSON in *stories_dir*."""
    loader = StoryLoader(stories_dir)
    reports: list[StoryReport] = []

    for story_id in loader.list_available_stories():
        try:
            story = loader.load_story(story_id)
        except StoryLoadError as exc:
            print(f"\n❌ Failed to load {story_id!r}: {exc}")
            reports.append(
                StoryReport(
                    story=Story(id=story_id, title=story_id, start_scene="", scenes={}),
                    source=stories_dir / f"{story_id}.json",
                    broken_links=[str(exc)],
                )
            )
            continue
        reports.append(_audit_story_graph(story))

    return reports


def main(argv: list[str] | None = None) -> int:
    """Run the audit and return a process exit code."""
    _ = argv
    print("Tangible NFC Story Audit")
    print(f"Stories directory: {STORIES_DIR}")

    if not STORIES_DIR.is_dir():
        print(f"❌ Stories directory not found: {STORIES_DIR}")
        return 1

    reports = audit_all_stories()
    if not reports:
        print("❌ No story files found.")
        return 1

    for report in reports:
        _print_story_report(report)

    failed = [report for report in reports if report.has_errors]
    print(f"\n{'=' * 72}")
    if failed:
        print(f"Summary: ❌ {len(failed)} of {len(reports)} stories have issues")
        return 1

    print(f"Summary: ✅ All {len(reports)} stories passed structural audit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
