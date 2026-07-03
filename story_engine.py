"""Core story state machine for the Tangible NFC Story Game.

Manages active story, scene transitions, inventory, and card-driven actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from card_manager import Card, CardType, UnknownCard
from story_loader import Scene, Story, StoryLoader


class EngineOutcome(str, Enum):
    """Possible outcomes from story engine operations.

    Each value indicates how :meth:`StoryEngine.handle_card` resolved a scan.
    """

    SUCCESS = "success"
    STORY_STARTED = "story_started"
    STORY_ENDED = "story_ended"
    UNKNOWN_CARD = "unknown_card"
    INVALID_ACTION = "invalid_action"
    MISSING_ITEMS = "missing_items"
    NO_STORY_LOADED = "no_story_loaded"
    STORY_NOT_FOUND = "story_not_found"
    STORY_ALREADY_ENDED = "story_already_ended"
    ITEM_CARD_IGNORED = "item_card_ignored"


@dataclass(frozen=True)
class EngineResult:
    """Outcome of a story engine operation.

    Attributes:
        outcome: Typed result category for the caller to branch on.
        message: Human-readable description for logging or UI display.
        previous_scene_id: Scene before a transition, if applicable.
        new_scene_id: Scene after a transition, if applicable.
        story_id: Active story identifier, if a story is loaded.
        ending_id: Ending identifier when a terminal scene is reached.
        inventory: Snapshot of held items after the operation.
    """

    outcome: EngineOutcome
    message: str
    previous_scene_id: str | None = None
    new_scene_id: str | None = None
    story_id: str | None = None
    ending_id: str | None = None
    inventory: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        """Return whether the operation completed successfully."""
        return self.outcome in {
            EngineOutcome.SUCCESS,
            EngineOutcome.STORY_STARTED,
            EngineOutcome.STORY_ENDED,
        }


class Inventory:
    """Player inventory with duplicate prevention."""

    def __init__(self, items: list[str] | None = None) -> None:
        """Initialize inventory, optionally from an existing item list."""
        self._items: set[str] = set()
        if items:
            for item in items:
                self.add_item(item)

    def add_item(self, item: str) -> bool:
        """Add an item if not already held. Returns True if added."""
        name = item.strip()
        if not name or name in self._items:
            return False
        self._items.add(name)
        return True

    def remove_item(self, item: str) -> bool:
        """Remove an item from inventory. Returns True if it was present."""
        name = item.strip()
        if name not in self._items:
            return False
        self._items.remove(name)
        return True

    def has_item(self, item: str) -> bool:
        """Return whether the player holds the given item."""
        return item.strip() in self._items

    def has_all(self, items: list[str] | tuple[str, ...]) -> bool:
        """Return whether the player holds every listed item."""
        return all(self.has_item(item) for item in items)

    @property
    def items(self) -> list[str]:
        """Return a sorted copy of held items."""
        return sorted(self._items)

    def reset(self) -> None:
        """Clear all items."""
        self._items.clear()

    def copy(self) -> Inventory:
        """Return a deep copy of this inventory."""
        return Inventory(self.items)


@dataclass
class GameState:
    """Mutable snapshot of the current game session."""

    story_id: str | None = None
    scene_id: str | None = None
    inventory: Inventory = field(default_factory=Inventory)
    flags: dict[str, Any] = field(default_factory=dict)
    is_ended: bool = False
    ending_id: str | None = None

    def copy(self) -> GameState:
        """Return a shallow copy with duplicated inventory."""
        return GameState(
            story_id=self.story_id,
            scene_id=self.scene_id,
            inventory=self.inventory.copy(),
            flags=dict(self.flags),
            is_ended=self.is_ended,
            ending_id=self.ending_id,
        )


class StoryEngine:
    """Branching story state machine driven by NFC card actions.

    Story card mapping
    ------------------
    When no story is active, a ``CardType.STORY`` card starts a story whose
    ``Story.title`` or ``Story.id`` matches the card ``name`` (case-insensitive).
    For example, card name ``"Fantasy"`` matches story id ``"fantasy"`` or title
    ``"Fantasy Quest"``.

    Item cards
    ----------
    ``CardType.ITEM`` cards do not directly modify inventory. Items are granted
    or removed when entering scenes via ``gained_items`` and ``lost_items``.

    Required items
    --------------
    When transitioning **to** a scene, ``required_items`` on the target scene
    must be satisfied. If not, the player remains on the current scene.
    """

    def __init__(self, story_loader: StoryLoader | None = None) -> None:
        """Initialize the engine with an optional story loader.

        Args:
            story_loader: Loader used to resolve story IDs. Defaults to
                ``StoryLoader()`` with project-relative ``stories/`` path.
        """
        self._loader = story_loader or StoryLoader()
        self._story: Story | None = None
        self._state = GameState()

    def start_story(self, story_id: str) -> EngineResult:
        """Start a story by ID, resetting inventory and scene to the start.

        Args:
            story_id: Story identifier matching a JSON file in ``stories/``.

        Returns:
            :class:`EngineResult` describing the outcome.
        """
        try:
            story = self._loader.load_story(story_id)
        except Exception as exc:
            return EngineResult(
                outcome=EngineOutcome.STORY_NOT_FOUND,
                message=str(exc),
            )

        return self._activate_story(story)

    def handle_card(self, card: Card | UnknownCard) -> EngineResult:
        """Process a scanned card and update game state accordingly.

        Args:
            card: Resolved card from :class:`CardManager`, or :class:`UnknownCard`.

        Returns:
            :class:`EngineResult` describing the outcome.
        """
        if isinstance(card, UnknownCard):
            return EngineResult(
                outcome=EngineOutcome.UNKNOWN_CARD,
                message=f"Unknown card scanned: {card.uid}",
            )

        if card.type == CardType.STORY:
            return self._handle_story_card(card)

        if not self.is_story_active():
            return EngineResult(
                outcome=EngineOutcome.NO_STORY_LOADED,
                message="Scan a story card to begin.",
            )

        if self._state.is_ended:
            return EngineResult(
                outcome=EngineOutcome.STORY_ALREADY_ENDED,
                message="Story has ended. Scan Restart or a story card.",
                story_id=self._state.story_id,
                new_scene_id=self._state.scene_id,
                ending_id=self._state.ending_id,
                inventory=tuple(self._state.inventory.items),
            )

        if card.type == CardType.ACTION:
            return self._handle_action_card(card)

        if card.type == CardType.SYSTEM:
            return self._handle_system_card(card)

        if card.type == CardType.ITEM:
            return EngineResult(
                outcome=EngineOutcome.ITEM_CARD_IGNORED,
                message=(
                    f"Item card {card.name!r} has no effect here. "
                    "Items are gained by entering scenes."
                ),
                story_id=self._state.story_id,
                new_scene_id=self._state.scene_id,
                inventory=tuple(self._state.inventory.items),
            )

        return EngineResult(
            outcome=EngineOutcome.INVALID_ACTION,
            message=f"Unsupported card type: {card.type!r}",
            story_id=self._state.story_id,
            new_scene_id=self._state.scene_id,
            inventory=tuple(self._state.inventory.items),
        )

    def get_current_scene(self) -> Scene | None:
        """Return the active scene, or ``None`` if no story is loaded."""
        if self._story is None or self._state.scene_id is None:
            return None
        return self._story.get_scene(self._state.scene_id)

    def get_state(self) -> GameState:
        """Return a copy of the current game state."""
        return self._state.copy()

    def restart(self) -> EngineResult:
        """Restart the current story from its start scene with empty inventory.

        Returns:
            :class:`EngineResult` describing the outcome.
        """
        if self._story is None:
            return EngineResult(
                outcome=EngineOutcome.NO_STORY_LOADED,
                message="No story is active to restart.",
            )
        return self._activate_story(self._story)

    def is_story_active(self) -> bool:
        """Return whether a story is currently loaded."""
        return self._story is not None and self._state.story_id is not None

    def _handle_story_card(self, card: Card) -> EngineResult:
        """Start a story matching the story card name."""
        story = self._find_story_for_card(card.name)
        if story is None:
            return EngineResult(
                outcome=EngineOutcome.STORY_NOT_FOUND,
                message=f"No story matches card name {card.name!r}.",
            )
        return self._activate_story(story)

    def _handle_action_card(self, card: Card) -> EngineResult:
        """Transition when the action card matches a choice on the current scene."""
        scene = self.get_current_scene()
        if scene is None:
            return EngineResult(
                outcome=EngineOutcome.NO_STORY_LOADED,
                message="No active scene.",
            )

        next_scene_id = scene.choices.get(card.name)
        if next_scene_id is None:
            return EngineResult(
                outcome=EngineOutcome.INVALID_ACTION,
                message=f"{card.name!r} is not available in the current scene.",
                story_id=self._state.story_id,
                new_scene_id=self._state.scene_id,
                inventory=tuple(self._state.inventory.items),
            )

        return self._transition_to_scene(next_scene_id, previous_scene_id=scene.id)

    def _handle_system_card(self, card: Card) -> EngineResult:
        """Handle system cards such as Restart."""
        if card.name.lower() == "restart":
            return self.restart()

        return EngineResult(
            outcome=EngineOutcome.INVALID_ACTION,
            message=f"Unknown system card: {card.name!r}.",
            story_id=self._state.story_id,
            new_scene_id=self._state.scene_id,
            inventory=tuple(self._state.inventory.items),
        )

    def _activate_story(self, story: Story) -> EngineResult:
        """Reset state and enter a story's start scene."""
        self._story = story
        self._state = GameState(story_id=story.id)
        result = self._enter_scene(story.start_scene, previous_scene_id=None)
        if result.outcome == EngineOutcome.SUCCESS:
            return EngineResult(
                outcome=EngineOutcome.STORY_STARTED,
                message=f"Started story: {story.title}",
                previous_scene_id=None,
                new_scene_id=story.start_scene,
                story_id=story.id,
                inventory=tuple(self._state.inventory.items),
            )
        return result

    def _transition_to_scene(
        self,
        next_scene_id: str,
        *,
        previous_scene_id: str | None,
    ) -> EngineResult:
        """Validate and move to the target scene."""
        if self._story is None:
            return EngineResult(
                outcome=EngineOutcome.NO_STORY_LOADED,
                message="No story is active.",
            )

        target = self._story.get_scene(next_scene_id)
        if target is None:
            return EngineResult(
                outcome=EngineOutcome.INVALID_ACTION,
                message=f"Scene {next_scene_id!r} does not exist.",
                story_id=self._state.story_id,
                new_scene_id=self._state.scene_id,
                inventory=tuple(self._state.inventory.items),
            )

        missing = [
            item for item in target.required_items if not self._state.inventory.has_item(item)
        ]
        if missing:
            missing_list = ", ".join(missing)
            return EngineResult(
                outcome=EngineOutcome.MISSING_ITEMS,
                message=f"Missing required items: {missing_list}",
                previous_scene_id=previous_scene_id,
                new_scene_id=self._state.scene_id,
                story_id=self._state.story_id,
                inventory=tuple(self._state.inventory.items),
            )

        return self._enter_scene(next_scene_id, previous_scene_id=previous_scene_id)

    def _enter_scene(
        self,
        scene_id: str,
        *,
        previous_scene_id: str | None,
    ) -> EngineResult:
        """Apply scene entry effects and update state."""
        if self._story is None:
            return EngineResult(
                outcome=EngineOutcome.NO_STORY_LOADED,
                message="No story is active.",
            )

        scene = self._story.get_scene(scene_id)
        if scene is None:
            return EngineResult(
                outcome=EngineOutcome.INVALID_ACTION,
                message=f"Scene {scene_id!r} does not exist.",
                story_id=self._state.story_id,
                new_scene_id=self._state.scene_id,
                inventory=tuple(self._state.inventory.items),
            )

        for item in scene.gained_items:
            self._state.inventory.add_item(item)
        for item in scene.lost_items:
            self._state.inventory.remove_item(item)

        self._state.scene_id = scene_id
        self._state.is_ended = scene.is_ending
        self._state.ending_id = scene.ending_id

        if scene.is_ending:
            return EngineResult(
                outcome=EngineOutcome.STORY_ENDED,
                message=f"Story ended: {scene.ending_id or 'default'}",
                previous_scene_id=previous_scene_id,
                new_scene_id=scene_id,
                story_id=self._state.story_id,
                ending_id=scene.ending_id,
                inventory=tuple(self._state.inventory.items),
            )

        return EngineResult(
            outcome=EngineOutcome.SUCCESS,
            message=f"Entered scene: {scene_id}",
            previous_scene_id=previous_scene_id,
            new_scene_id=scene_id,
            story_id=self._state.story_id,
            inventory=tuple(self._state.inventory.items),
        )

    def _find_story_for_card(self, card_name: str) -> Story | None:
        """Find a story whose id or title matches the card name (case-insensitive)."""
        normalized = card_name.strip().casefold()
        for story_id in self._loader.list_available_stories():
            story = self._loader.load_story(story_id)
            if story.id.casefold() == normalized:
                return story
            if story.title.casefold() == normalized:
                return story
        return None


def _print_result(label: str, result: EngineResult, scene: Scene | None) -> None:
    """Print a formatted engine result for demo output."""
    print(f"\n--- {label} ---")
    print(f"Outcome: {result.outcome.value}")
    print(f"Message: {result.message}")
    if result.story_id:
        print(f"Story:   {result.story_id}")
    if result.new_scene_id:
        print(f"Scene:   {result.new_scene_id}")
    if result.ending_id:
        print(f"Ending:  {result.ending_id}")
    print(f"Inventory: {list(result.inventory)}")
    if scene:
        print(f"Scene text: {scene.text}")


if __name__ == "__main__":
    from card_manager import Card

    print("=== StoryEngine demo ===\n")

    loader = StoryLoader()
    engine = StoryEngine(loader)

    print(f"Available stories: {loader.list_available_stories()}")

    fantasy_card = Card(uid="A1B2C3D4", name="Fantasy", type=CardType.STORY)
    result = engine.handle_card(fantasy_card)
    scene = engine.get_current_scene()
    _print_result("1. Story card scan (Fantasy)", result, scene)

    sword_card = Card(uid="11223344", name="Sword", type=CardType.ACTION)
    result = engine.handle_card(sword_card)
    scene = engine.get_current_scene()
    _print_result("2. Action card (Sword -> armory)", result, scene)

    result = engine.handle_card(sword_card)
    scene = engine.get_current_scene()
    _print_result("3. Action card (Sword -> dragon, needs Sword item)", result, scene)

    key_card = Card(uid="99AABBCC", name="Key", type=CardType.ITEM)
    result = engine.handle_card(key_card)
    _print_result("4. Item card (ignored — items come from scenes)", result, scene)

    restart_card = Card(uid="55667788", name="Restart", type=CardType.SYSTEM)
    result = engine.handle_card(restart_card)
    scene = engine.get_current_scene()
    _print_result("5. System card (Restart)", result, scene)
