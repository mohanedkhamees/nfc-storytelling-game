"""Graph validation and path simulation tests for production story JSON files."""

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest

from audit_stories import VALID_NFC_ACTIONS, _audit_story_graph
from card_manager import Card, CardType
from story_engine import EngineOutcome, StoryEngine
from story_loader import Story, StoryLoader

STORIES_DIR = Path(__file__).resolve().parent.parent / "stories"


@pytest.fixture(scope="module")
def production_loader() -> StoryLoader:
    """StoryLoader pointed at the real stories/ directory."""
    return StoryLoader(STORIES_DIR)


@pytest.fixture(scope="module")
def production_stories(production_loader: StoryLoader) -> dict[str, Story]:
    """All three children's stories loaded once for the module."""
    return production_loader.load_all_stories()


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_audit_passes_for_production_story(
    production_loader: StoryLoader,
    story_id: str,
) -> None:
    """Structural audit reports no broken links or inventory traps."""
    story = production_loader.load_story(story_id)
    report = _audit_story_graph(story)
    assert not report.has_errors, (
        report.broken_links
        + report.inventory_trap_states
        + report.dead_end_scenes
        + report.unreachable_endings
    )


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_no_duplicate_scene_ids(production_stories: dict[str, Story], story_id: str) -> None:
    story = production_stories[story_id]
    ids = [scene.id for scene in story.scenes.values()]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_all_choice_targets_exist(production_stories: dict[str, Story], story_id: str) -> None:
    story = production_stories[story_id]
    valid_ids = set(story.scenes)
    for scene in story.scenes.values():
        for action, target in scene.choices.items():
            assert action in VALID_NFC_ACTIONS
            assert target in valid_ids, f"{story_id}/{scene.id}/{action} -> {target}"


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_choice_labels_keys_exist_in_choices(
    production_stories: dict[str, Story],
    story_id: str,
) -> None:
    story = production_stories[story_id]
    for scene in story.scenes.values():
        for label_key in scene.choice_labels:
            assert label_key in scene.choices, f"{scene.id} label {label_key!r}"


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_non_ending_scenes_have_outgoing_edges(
    production_stories: dict[str, Story],
    story_id: str,
) -> None:
    story = production_stories[story_id]
    for scene in story.scenes.values():
        if not scene.is_ending:
            assert scene.choices, f"{story_id}/{scene.id} is a dead-end non-ending scene"


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_all_endings_reachable_from_start(
    production_stories: dict[str, Story],
    story_id: str,
) -> None:
    story = production_stories[story_id]
    reachable: set[str] = set()
    queue: deque[str] = deque([story.start_scene])
    while queue:
        scene_id = queue.popleft()
        if scene_id in reachable:
            continue
        reachable.add(scene_id)
        scene = story.get_scene(scene_id)
        if scene:
            queue.extend(scene.choices.values())

    endings = [sid for sid, scene in story.scenes.items() if scene.is_ending]
    assert endings, f"{story_id} has no endings"
    for ending_id in endings:
        assert ending_id in reachable, f"{story_id} ending {ending_id!r} unreachable"


def _reachable_states(story: Story) -> set[tuple[str, frozenset[str]]]:
    """BFS over (scene_id, inventory) honoring required_items gates."""
    start = (story.start_scene, frozenset())
    queue: deque[tuple[str, frozenset[str]]] = deque([start])
    visited: set[tuple[str, frozenset[str]]] = {start}

    while queue:
        scene_id, inventory = queue.popleft()
        scene = story.get_scene(scene_id)
        if scene is None or scene.is_ending:
            continue
        for _action, target_id in scene.choices.items():
            target = story.get_scene(target_id)
            if target is None:
                continue
            if any(item not in inventory for item in target.required_items):
                continue
            new_inventory = set(inventory)
            for item in target.gained_items:
                new_inventory.add(item)
            for item in target.lost_items:
                new_inventory.discard(item)
            state = (target_id, frozenset(new_inventory))
            if state not in visited:
                visited.add(state)
                queue.append(state)
    return visited


def _can_reach_any_ending(story: Story, scene_id: str, inventory: frozenset[str]) -> bool:
    queue: deque[tuple[str, frozenset[str]]] = deque([(scene_id, inventory)])
    visited: set[tuple[str, frozenset[str]]] = {(scene_id, inventory)}

    while queue:
        sid, inv = queue.popleft()
        scene = story.get_scene(sid)
        if scene is not None and scene.is_ending:
            return True
        if scene is None:
            continue
        for _action, target_id in scene.choices.items():
            target = story.get_scene(target_id)
            if target is None:
                continue
            if any(item not in inv for item in target.required_items):
                continue
            new_inv = set(inv)
            for item in target.gained_items:
                new_inv.add(item)
            for item in target.lost_items:
                new_inv.discard(item)
            state = (target_id, frozenset(new_inv))
            if state not in visited:
                visited.add(state)
                queue.append(state)
    return False


@pytest.mark.parametrize("story_id", ["benny", "mina", "nova"])
def test_every_reachable_state_can_reach_an_ending(
    production_stories: dict[str, Story],
    story_id: str,
) -> None:
    """Inventory-aware simulation: no soft-lock trap states."""
    story = production_stories[story_id]
    states = _reachable_states(story)
    stuck = [
        (sid, inv)
        for sid, inv in states
        if not story.get_scene(sid).is_ending
        and not _can_reach_any_ending(story, sid, inv)
    ]
    assert not stuck, f"{story_id} stuck states: {stuck[:3]}"


def test_benny_forest_path_all_choices_transition(production_loader: StoryLoader) -> None:
    """Regression: forest_path Talk, Sword, and Hide must all advance the story."""
    for action, expected in (
        ("Talk", "squirrel_help"),
        ("Sword", "cut_thorns"),
        ("Hide", "ignore_squirrel"),
    ):
        engine = StoryEngine(production_loader)
        engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
        engine.handle_card(Card(uid="R1", name="Run", type=CardType.ACTION))
        result = engine.handle_card(Card(uid="X1", name=action, type=CardType.ACTION))
        assert result.outcome == EngineOutcome.SUCCESS, result.message
        assert result.new_scene_id == expected


def test_benny_key_item_card_at_bunny_home(production_loader: StoryLoader) -> None:
    """Key is an ITEM card but must work when listed as a scene choice."""
    engine = StoryEngine(production_loader)
    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    result = engine.handle_card(Card(uid="55555555", name="Key", type=CardType.ITEM))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "locked_box"


def test_benny_locked_tower_fail_run_escapes_trap(production_loader: StoryLoader) -> None:
    """Run at locked_tower_fail returns to mountain_tower instead of soft-locking."""
    engine = StoryEngine(production_loader)
    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    for uid, action in (
        ("R1", "Run"),       # bunny_home -> forest_path
        ("T1", "Talk"),      # forest_path -> squirrel_help
        ("R2", "Run"),       # squirrel_help -> broken_bridge
        ("R3", "Run"),       # broken_bridge -> riverbank
        ("T2", "Talk"),      # riverbank -> fox_meeting
    ):
        engine.handle_card(Card(uid=uid, name=action, type=CardType.ACTION))
    engine.handle_card(Card(uid="K1", name="Key", type=CardType.ITEM))  # -> mountain_tower
    engine.handle_card(Card(uid="D1", name="Open Door", type=CardType.ACTION))  # -> locked_tower_fail

    assert engine.get_current_scene().id == "locked_tower_fail"
    result = engine.handle_card(Card(uid="R4", name="Run", type=CardType.ACTION))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "mountain_tower"


def test_benny_mountain_tower_run_reaches_bridge(production_loader: StoryLoader) -> None:
    """Run at mountain_tower retreats to broken_bridge so players can recover."""
    engine = StoryEngine(production_loader)
    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))
    for uid, action in (
        ("R1", "Run"),
        ("T1", "Talk"),
        ("R2", "Run"),
        ("R3", "Run"),
        ("T2", "Talk"),
    ):
        engine.handle_card(Card(uid=uid, name=action, type=CardType.ACTION))
    engine.handle_card(Card(uid="K1", name="Key", type=CardType.ITEM))

    result = engine.handle_card(Card(uid="R4", name="Run", type=CardType.ACTION))
    assert result.outcome == EngineOutcome.SUCCESS
    assert result.new_scene_id == "broken_bridge"


def _walk_actions(
    engine: StoryEngine,
    actions: list[tuple[str, CardType]],
) -> str:
    """Execute a fixed card sequence and return the final scene id."""
    for index, (name, card_type) in enumerate(actions):
        result = engine.handle_card(Card(uid=str(index), name=name, type=card_type))
        assert result.outcome in {
            EngineOutcome.SUCCESS,
            EngineOutcome.STORY_ENDED,
        }, f"{name} at {engine.get_current_scene().id}: {result.message}"
    scene = engine.get_current_scene()
    assert scene is not None
    return scene.id


def test_benny_full_path_reaches_golden_ending(production_loader: StoryLoader) -> None:
    """Engine walk-through along a kindness path reaches golden_ending."""
    engine = StoryEngine(production_loader)
    engine.handle_card(Card(uid="A1", name="Benny", type=CardType.STORY))

    ending = _walk_actions(
        engine,
        [
            ("Key", CardType.ITEM),
            ("Key", CardType.ITEM),
            ("Run", CardType.ACTION),
            ("Talk", CardType.ACTION),
            ("Run", CardType.ACTION),
            ("Magic", CardType.ACTION),
            ("Magic", CardType.ACTION),
            ("Run", CardType.ACTION),
            ("Magic", CardType.ACTION),
            ("Run", CardType.ACTION),
            ("Magic", CardType.ACTION),
            ("Open Door", CardType.ACTION),
            ("Magic", CardType.ACTION),
        ],
    )
    assert ending == "golden_ending"


@pytest.mark.parametrize(
    ("story_id", "card_name", "actions", "expected_ending"),
    [
        (
            "mina",
            "Mina",
            [
                ("Key", CardType.ITEM),
                ("Key", CardType.ITEM),
                ("Run", CardType.ACTION),
                ("Hide", CardType.ACTION),
                ("Talk", CardType.ACTION),
                ("Magic", CardType.ACTION),
                ("Open Door", CardType.ACTION),
            ],
            "festival_ending",
        ),
        (
            "nova",
            "Nova",
            [
                ("Talk", CardType.ACTION),
                ("Magic", CardType.ACTION),
                ("Run", CardType.ACTION),
                ("Key", CardType.ITEM),
                ("Talk", CardType.ACTION),
                ("Talk", CardType.ACTION),
                ("Talk", CardType.ACTION),
                ("Key", CardType.ITEM),
                ("Run", CardType.ACTION),
                ("Shield", CardType.ACTION),
                ("Run", CardType.ACTION),
                ("Talk", CardType.ACTION),
                ("Magic", CardType.ACTION),
                ("Open Door", CardType.ACTION),
                ("Open Door", CardType.ACTION),
            ],
            "golden_space_ending",
        ),
    ],
)
def test_full_path_reaches_ending(
    production_loader: StoryLoader,
    story_id: str,
    card_name: str,
    actions: list[tuple[str, CardType]],
    expected_ending: str,
) -> None:
    engine = StoryEngine(production_loader)
    engine.handle_card(Card(uid="S1", name=card_name, type=CardType.STORY))
    ending = _walk_actions(engine, actions)
    assert ending == expected_ending
    assert production_loader.load_story(story_id).get_scene(ending).is_ending
