"""Tkinter presentation layer for the Tangible NFC Story Game.

Display-only GUI with dark theme. Gameplay input comes exclusively from NFC
card scans handled by :mod:`main`; this module never contains story logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import font as tkfont

from asset_manager import AssetManager
from story_loader import Scene

# Dark theme palette
COLOR_BG = "#1a1a2e"
COLOR_SURFACE = "#16213e"
COLOR_ACCENT = "#e94560"
COLOR_TEXT = "#eaeaea"
COLOR_MUTED = "#a0a0a0"
COLOR_PLACEHOLDER = "#2a2a4a"
COLOR_CONNECTED = "#4ecca3"
COLOR_DISCONNECTED = "#e94560"
COLOR_CHOICE_HIGHLIGHT = "#0f3460"

FONT_TITLE = ("Helvetica", 26, "bold")
FONT_SUBTITLE = ("Helvetica", 16)
FONT_BODY = ("Helvetica", 15)
FONT_SMALL = ("Helvetica", 12)
FONT_STATUS = ("Helvetica", 13)

MIN_WIDTH = 900
MIN_HEIGHT = 600
IMAGE_MAX_WIDTH = 420
IMAGE_MAX_HEIGHT = 320
ERROR_DISPLAY_MS = 4000


class _StartScreen(tk.Frame):
    """Welcome screen shown when no story is active."""

    def __init__(
        self,
        master: tk.Widget,
        *,
        story_names: list[str],
        **kwargs: object,
    ) -> None:
        """Build the start screen listing available story cards.

        Args:
            master: Parent Tkinter widget.
            story_names: Story card names displayed on the welcome screen.
        """
        super().__init__(master, bg=COLOR_BG, **kwargs)
        self._build(story_names)

    def _build(self, story_names: list[str]) -> None:
        container = tk.Frame(self, bg=COLOR_BG)
        container.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        tk.Label(
            container,
            text="Tangible NFC Interactive\nStorytelling Game",
            font=FONT_TITLE,
            fg=COLOR_TEXT,
            bg=COLOR_BG,
            justify=tk.CENTER,
        ).pack(pady=(0, 24))

        tk.Label(
            container,
            text="Scan a Story Card to begin",
            font=FONT_SUBTITLE,
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
        ).pack(pady=(0, 32))

        stories_frame = tk.Frame(container, bg=COLOR_SURFACE, padx=24, pady=20)
        stories_frame.pack()

        tk.Label(
            stories_frame,
            text="Available Stories",
            font=("Helvetica", 14, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
        ).pack(anchor=tk.W, pady=(0, 12))

        display_names = story_names or ["Fantasy", "Mystery", "Space"]
        for name in display_names:
            tk.Label(
                stories_frame,
                text=f"•  {name}",
                font=FONT_BODY,
                fg=COLOR_MUTED,
                bg=COLOR_SURFACE,
                anchor=tk.W,
            ).pack(fill=tk.X, pady=2)


class _StorySceneScreen(tk.Frame):
    """Active story scene with image, text, choices, and inventory."""

    def __init__(self, master: tk.Widget, **kwargs: object) -> None:
        """Build the scene layout widgets.

        Args:
            master: Parent Tkinter widget.
        """
        super().__init__(master, bg=COLOR_BG, **kwargs)
        self._photo: object | None = None
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._title_label = tk.Label(
            self,
            text="",
            font=("Helvetica", 22, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_BG,
            anchor=tk.W,
        )
        self._title_label.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        content = tk.Frame(self, bg=COLOR_BG)
        content.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        self._image_frame = tk.Frame(
            content,
            bg=COLOR_PLACEHOLDER,
            width=IMAGE_MAX_WIDTH,
            height=IMAGE_MAX_HEIGHT,
        )
        self._image_frame.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self._image_frame.grid_propagate(False)

        self._image_label = tk.Label(
            self._image_frame,
            bg=COLOR_PLACEHOLDER,
            fg=COLOR_MUTED,
            text="No image",
            font=FONT_BODY,
        )
        self._image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        right = tk.Frame(content, bg=COLOR_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=0)
        right.rowconfigure(2, weight=0)

        text_frame = tk.Frame(right, bg=COLOR_SURFACE, padx=16, pady=16)
        text_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=FONT_BODY,
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            relief=tk.FLAT,
            highlightthickness=0,
            padx=4,
            pady=4,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self._text_widget.grid(row=0, column=0, sticky="nsew")

        choices_frame = tk.Frame(right, bg=COLOR_BG)
        choices_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        tk.Label(
            choices_frame,
            text="Scan an NFC card to choose:",
            font=("Helvetica", 13, "bold"),
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(0, 6))

        self._choices_frame = tk.Frame(choices_frame, bg=COLOR_BG)
        self._choices_frame.pack(fill=tk.X)

        inventory_outer = tk.Frame(right, bg=COLOR_SURFACE, padx=16, pady=12)
        inventory_outer.grid(row=2, column=0, sticky="ew")

        tk.Label(
            inventory_outer,
            text="Inventory",
            font=("Helvetica", 13, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(0, 6))

        self._inventory_label = tk.Label(
            inventory_outer,
            text="(empty)",
            font=FONT_BODY,
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=480,
        )
        self._inventory_label.pack(anchor=tk.W)

    def update_content(
        self,
        *,
        story_title: str,
        scene: Scene,
        inventory: list[str],
        available_choices: list[str],
        asset_manager: AssetManager,
    ) -> None:
        """Refresh scene image, text, choices, and inventory display.

        Args:
            story_title: Active story title shown in the header.
            scene: Current scene data (text and image path).
            inventory: Item names held by the player.
            available_choices: Action card names valid in this scene.
            asset_manager: Loader for scene images and placeholders.
        """
        self._title_label.config(text=story_title)

        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.insert(tk.END, scene.text)
        self._text_widget.config(state=tk.DISABLED)

        self._render_choices(available_choices)
        self._render_inventory(inventory)
        self._render_image(scene.image, asset_manager)

    def _render_choices(self, choices: list[str]) -> None:
        for widget in self._choices_frame.winfo_children():
            widget.destroy()

        if not choices:
            tk.Label(
                self._choices_frame,
                text="No choices available",
                font=FONT_SMALL,
                fg=COLOR_MUTED,
                bg=COLOR_BG,
            ).pack(anchor=tk.W)
            return

        for choice in choices:
            chip = tk.Label(
                self._choices_frame,
                text=f"  {choice}  ",
                font=("Helvetica", 14, "bold"),
                fg=COLOR_TEXT,
                bg=COLOR_CHOICE_HIGHLIGHT,
                padx=8,
                pady=4,
            )
            chip.pack(side=tk.LEFT, padx=(0, 8), pady=4)

    def _render_inventory(self, inventory: list[str]) -> None:
        if inventory:
            self._inventory_label.config(text=", ".join(inventory), fg=COLOR_TEXT)
        else:
            self._inventory_label.config(text="(empty)", fg=COLOR_MUTED)

    def _render_image(self, image_path: str, asset_manager: AssetManager) -> None:
        if not image_path:
            self._photo = None
            self._image_label.config(image="", text="No image")
            return

        self._photo = asset_manager.load_image(
            image_path,
            (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT),
        )
        self._image_label.config(image=self._photo, text="")


class _EndingScreen(tk.Frame):
    """Terminal story screen prompting a restart scan."""

    def __init__(self, master: tk.Widget, **kwargs: object) -> None:
        """Build the ending layout widgets.

        Args:
            master: Parent Tkinter widget.
        """
        super().__init__(master, bg=COLOR_BG, **kwargs)
        self._photo: object | None = None
        self._build()

    def _build(self) -> None:
        container = tk.Frame(self, bg=COLOR_BG)
        container.place(relx=0.5, rely=0.42, anchor=tk.CENTER)

        self._title_label = tk.Label(
            container,
            text="",
            font=("Helvetica", 22, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_BG,
        )
        self._title_label.pack(pady=(0, 8))

        self._ending_label = tk.Label(
            container,
            text="",
            font=("Helvetica", 14),
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
        )
        self._ending_label.pack(pady=(0, 20))

        self._image_label = tk.Label(
            container,
            bg=COLOR_PLACEHOLDER,
            fg=COLOR_MUTED,
            text="No image",
            font=FONT_BODY,
            width=IMAGE_MAX_WIDTH // 10,
            height=IMAGE_MAX_HEIGHT // 20,
        )
        self._image_label.pack(pady=(0, 20))

        self._text_widget = tk.Text(
            container,
            wrap=tk.WORD,
            font=FONT_BODY,
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            relief=tk.FLAT,
            highlightthickness=0,
            width=60,
            height=6,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self._text_widget.pack(pady=(0, 24))

        tk.Label(
            container,
            text="Scan Restart Card to play again",
            font=FONT_SUBTITLE,
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
        ).pack()

    def update_content(
        self,
        *,
        story_title: str,
        scene: Scene,
        ending_id: str | None,
        asset_manager: AssetManager,
    ) -> None:
        """Refresh ending title, text, and optional image.

        Args:
            story_title: Active story title shown in the header.
            scene: Terminal scene data (text and image path).
            ending_id: Identifier for the ending reached, if any.
            asset_manager: Loader for scene images and placeholders.
        """
        self._title_label.config(text=story_title)

        if ending_id:
            self._ending_label.config(text=f"Ending: {ending_id}")
        else:
            self._ending_label.config(text="The End")

        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.insert(tk.END, scene.text)
        self._text_widget.config(state=tk.DISABLED)

        if not scene.image:
            self._photo = None
            self._image_label.config(image="", text="No image")
            return

        self._photo = asset_manager.load_image(
            scene.image,
            (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT),
        )
        self._image_label.config(image=self._photo, text="")


class GameUI:
    """Dark-mode Tkinter UI for the NFC storytelling game.

    The UI is display-only: it renders story state and scan feedback but
    never processes gameplay decisions. All input arrives via NFC scans
    handled in :mod:`main`.
    """

    def __init__(
        self,
        root: tk.Tk,
        assets_dir: Path | str = "assets",
        *,
        debug_mode: bool = False,
        story_names: list[str] | None = None,
        asset_manager: AssetManager | None = None,
    ) -> None:
        """Build the widget tree and apply the dark theme.

        Args:
            root: Tkinter root window.
            assets_dir: Directory containing scene images.
            debug_mode: When True, show a developer card-simulation panel.
            story_names: Story card names listed on the start screen.
            asset_manager: Optional pre-built asset manager from the app root.
        """
        self._root = root
        self._assets_dir = Path(assets_dir)
        if asset_manager is not None:
            self._asset_manager = asset_manager
        else:
            project_root = (
                self._assets_dir.parent if self._assets_dir.name == "assets" else self._assets_dir
            )
            self._asset_manager = AssetManager(project_root=project_root)
        self._debug_mode = debug_mode
        self._story_names = story_names or ["Fantasy", "Mystery", "Space"]
        self._simulate_callback: Callable[[str], None] | None = None
        self._error_after_id: str | None = None
        self._current_screen: str = "start"

        self._configure_root()
        self._build_layout()
        self.show_start_screen()

    def register_simulate_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when debug mode simulates a card scan.

        Args:
            callback: Called with the card name when a debug scan is triggered.
        """
        self._simulate_callback = callback

    def show_start_screen(self) -> None:
        """Show the welcome screen listing available story cards."""
        self._current_screen = "start"
        self._show_frame(self._start_screen)
        self.set_status("Waiting for NFC card...")

    def show_scene(
        self,
        story_title: str,
        scene: Scene,
        inventory: list[str],
        available_choices: list[str],
    ) -> None:
        """Render an active story scene with highlighted NFC choices.

        Args:
            story_title: Title shown in the scene header.
            scene: Current scene data from the story loader.
            inventory: Item names held by the player.
            available_choices: Action card names valid in this scene.
        """
        self._current_screen = "scene"
        self._scene_screen.update_content(
            story_title=story_title,
            scene=scene,
            inventory=inventory,
            available_choices=available_choices,
            asset_manager=self._asset_manager,
        )
        self._show_frame(self._scene_screen)
        self.set_status("Waiting for NFC card...")

    def show_ending(
        self,
        story_title: str,
        scene: Scene,
        ending_id: str | None,
    ) -> None:
        """Render the story ending and prompt for a restart scan.

        Args:
            story_title: Title shown in the ending header.
            scene: Terminal scene data from the story loader.
            ending_id: Identifier for the ending reached, if any.
        """
        self._current_screen = "ending"
        self._ending_screen.update_content(
            story_title=story_title,
            scene=scene,
            ending_id=ending_id,
            asset_manager=self._asset_manager,
        )
        self._show_frame(self._ending_screen)
        self.set_status("Story complete. Scan Restart Card to play again.")

    def set_status(self, message: str) -> None:
        """Update the persistent status bar message."""
        self._status_label.config(text=message)

    def set_connection_status(self, connected: bool) -> None:
        """Show whether the NFC serial reader is connected."""
        if connected:
            self._connection_label.config(
                text="● Reader connected",
                fg=COLOR_CONNECTED,
            )
        else:
            self._connection_label.config(
                text="● Reader disconnected",
                fg=COLOR_DISCONNECTED,
            )

    def set_debug_mode(self, enabled: bool) -> None:
        """Show debug-mode status when serial I/O is disabled."""
        if enabled:
            self._connection_label.config(
                text="● Debug mode (simulated scans)",
                fg=COLOR_MUTED,
            )

    def set_last_scanned(self, card_name: str, uid: str) -> None:
        """Display the most recently scanned card name and UID."""
        self._last_scan_label.config(text=f"Last scan: {card_name} ({uid})")

    def show_error(self, message: str) -> None:
        """Show a temporary error message in the status bar."""
        if self._error_after_id is not None:
            self._root.after_cancel(self._error_after_id)
            self._error_after_id = None

        original = self._status_label.cget("text")
        self._status_label.config(text=message, fg=COLOR_ACCENT)

        def restore() -> None:
            self._status_label.config(text=original, fg=COLOR_MUTED)
            self._error_after_id = None

        self._error_after_id = self._root.after(ERROR_DISPLAY_MS, restore)

    def _configure_root(self) -> None:
        self._root.title("Tangible NFC Story Game")
        self._root.configure(bg=COLOR_BG)
        self._root.minsize(MIN_WIDTH, MIN_HEIGHT)

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=12)
        self._root.option_add("*Font", default_font)

    def _build_layout(self) -> None:
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)
        if self._debug_mode:
            self._root.rowconfigure(1, weight=0)
            self._root.rowconfigure(2, weight=0)

        self._screen_container = tk.Frame(self._root, bg=COLOR_BG)
        self._screen_container.grid(row=0, column=0, sticky="nsew")
        self._screen_container.rowconfigure(0, weight=1)
        self._screen_container.columnconfigure(0, weight=1)

        self._start_screen = _StartScreen(
            self._screen_container,
            story_names=self._story_names,
        )
        self._scene_screen = _StorySceneScreen(self._screen_container)
        self._ending_screen = _EndingScreen(self._screen_container)

        for screen in (self._start_screen, self._scene_screen, self._ending_screen):
            screen.grid(row=0, column=0, sticky="nsew")

        footer = tk.Frame(self._root, bg=COLOR_SURFACE, padx=16, pady=10)
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)

        self._connection_label = tk.Label(
            footer,
            text="● Reader connecting…",
            font=FONT_SMALL,
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
            anchor=tk.W,
        )
        self._connection_label.grid(row=0, column=0, sticky="w")

        self._status_label = tk.Label(
            footer,
            text="Waiting for NFC card...",
            font=FONT_STATUS,
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
            anchor=tk.CENTER,
        )
        self._status_label.grid(row=0, column=1, sticky="ew", padx=12)

        self._last_scan_label = tk.Label(
            footer,
            text="Last scan: —",
            font=FONT_SMALL,
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
            anchor=tk.E,
        )
        self._last_scan_label.grid(row=0, column=2, sticky="e")

        if self._debug_mode:
            self._build_debug_panel()

    def _build_debug_panel(self) -> None:
        """Build hidden developer tools for simulating card scans."""
        panel = tk.LabelFrame(
            self._root,
            text="Debug — Simulate Card Scan (keys 1–9, 0, -, =)",
            font=FONT_SMALL,
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            labelanchor=tk.N,
        )
        panel.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        debug_cards = [
            "Fantasy",
            "Mystery",
            "Space",
            "Sword",
            "Magic",
            "Shield",
            "Run",
            "Key",
            "Talk",
            "Hide",
            "Open Door",
            "Restart",
        ]
        self._debug_cards = debug_cards
        key_labels = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="]

        buttons_frame = tk.Frame(panel, bg=COLOR_SURFACE)
        buttons_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        for index, name in enumerate(debug_cards):
            label = f"{key_labels[index]} {name}"
            tk.Button(
                buttons_frame,
                text=label,
                font=FONT_SMALL,
                command=lambda n=name: self._trigger_simulate(n),
            ).pack(side=tk.LEFT, padx=2, pady=2)

        key_bindings = {
            "1": 0,
            "2": 1,
            "3": 2,
            "4": 3,
            "5": 4,
            "6": 5,
            "7": 6,
            "8": 7,
            "9": 8,
            "0": 9,
            "minus": 10,
            "equal": 11,
        }
        for key, card_index in key_bindings.items():
            self._root.bind(
                f"<{key}>",
                lambda _event, idx=card_index: self._trigger_simulate(debug_cards[idx]),
            )

        entry_frame = tk.Frame(panel, bg=COLOR_SURFACE)
        entry_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        tk.Label(
            entry_frame,
            text="Card name:",
            font=FONT_SMALL,
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
        ).pack(side=tk.LEFT)

        self._debug_entry = tk.Entry(entry_frame, font=FONT_SMALL, width=24)
        self._debug_entry.pack(side=tk.LEFT, padx=8)
        self._debug_entry.bind("<Return>", self._on_debug_entry)

        tk.Button(
            entry_frame,
            text="Simulate",
            font=FONT_SMALL,
            command=self._on_debug_entry,
        ).pack(side=tk.LEFT)

    def _trigger_simulate(self, card_name: str) -> None:
        if self._simulate_callback is not None:
            self._simulate_callback(card_name)

    def _on_debug_entry(self, _event: object = None) -> None:
        name = self._debug_entry.get().strip()
        if name:
            self._trigger_simulate(name)
            self._debug_entry.delete(0, tk.END)

    def _show_frame(self, frame: tk.Frame) -> None:
        frame.tkraise()
