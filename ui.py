"""Tkinter presentation layer for the Tangible NFC Interactive Storybook.

Display-only GUI with a bright, child-friendly theme. Gameplay input comes
exclusively from NFC card scans handled by :mod:`main`; this module never
contains story logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import font as tkfont

from asset_manager import AssetManager
from story_loader import Scene

# Bright child-friendly palette
COLOR_BG = "#E8F4FC"
COLOR_BG_ALT = "#FFF8E7"
COLOR_SURFACE = "#FFFFFF"
COLOR_TEXT = "#2D3436"
COLOR_TEXT_DARK = "#1A1A2E"
COLOR_MUTED = "#636E72"
COLOR_ACCENT = "#FF6B9D"
COLOR_PLACEHOLDER = "#D6EAF8"
COLOR_CONNECTED = "#00B894"
COLOR_DISCONNECTED = "#E17055"
COLOR_FOOTER = "#FFF8E7"
COLOR_FOOTER_BORDER = "#FFD6E8"

PASTEL_PINK = "#FFD6E8"
PASTEL_YELLOW = "#FFF4B8"
PASTEL_GREEN = "#C8F7C5"
PASTEL_BLUE = "#B8E0FF"
PASTEL_LAVENDER = "#E8D6FF"
PASTEL_PEACH = "#FFE0CC"

PASTEL_CARD_COLORS = (PASTEL_PINK, PASTEL_YELLOW, PASTEL_GREEN, PASTEL_BLUE)
CHOICE_PILL_COLORS = (PASTEL_PINK, PASTEL_YELLOW, PASTEL_GREEN, PASTEL_BLUE, PASTEL_LAVENDER, PASTEL_PEACH)

MIN_WIDTH = 900
MIN_HEIGHT = 600
IMAGE_MAX_WIDTH = 420
IMAGE_MAX_HEIGHT = 320
ERROR_DISPLAY_MS = 4000

STORY_CARD_STYLES: dict[str, tuple[str, str]] = {
    "benny": ("🐰", PASTEL_PINK),
    "mina": ("🔍", PASTEL_YELLOW),
    "nova": ("🚀", PASTEL_BLUE),
}

DEBUG_CARD_STYLES: dict[str, tuple[str, str]] = {
    "Benny": ("🐰", PASTEL_PINK),
    "Mina": ("🔍", PASTEL_YELLOW),
    "Nova": ("🚀", PASTEL_BLUE),
    "Sword": ("⚔️", PASTEL_PEACH),
    "Magic": ("✨", PASTEL_LAVENDER),
    "Shield": ("🛡️", PASTEL_GREEN),
    "Run": ("🏃", PASTEL_YELLOW),
    "Key": ("🗝️", PASTEL_BLUE),
    "Talk": ("💬", PASTEL_PINK),
    "Hide": ("🙈", PASTEL_GREEN),
    "Open Door": ("🚪", PASTEL_PEACH),
    "Restart": ("🔄", PASTEL_LAVENDER),
}


def _resolve_font_family() -> str:
    """Pick the first available playful font on this system."""
    families = set(tkfont.families())
    for candidate in ("Comic Sans MS", "Chalkboard SE", "Segoe UI", "Trebuchet MS", "Helvetica"):
        if candidate in families:
            return candidate
    return "TkDefaultFont"


def _make_fonts(family: str) -> dict[str, tuple[str, int, str] | tuple[str, int]]:
    """Build the font tuple set used across screens."""
    return {
        "title": (family, 30, "bold"),
        "subtitle": (family, 18),
        "heading": (family, 24, "bold"),
        "progress_story": (family, 16, "bold"),
        "progress_scene": (family, 15),
        "scene_title": (family, 22, "bold"),
        "story": (family, 21),
        "body": (family, 17),
        "small": (family, 14),
        "status": (family, 15),
        "card_title": (family, 20, "bold"),
        "card_emoji": (family, 36),
        "choice_heading": (family, 18, "bold"),
        "choice_card": (family, 16, "bold"),
        "pill": (family, 15, "bold"),
        "debug": (family, 11),
        "debug_label": (family, 10),
        "celebration": (family, 36, "bold"),
    }


def _story_card_look(title: str, index: int) -> tuple[str, str]:
    """Return emoji and pastel background for a story title."""
    lowered = title.casefold()
    for key, (emoji, color) in STORY_CARD_STYLES.items():
        if key in lowered:
            return emoji, color
    return "📖", PASTEL_CARD_COLORS[index % len(PASTEL_CARD_COLORS)]


def _rounded_frame(
    master: tk.Widget,
    *,
    bg: str,
    padx: int = 16,
    pady: int = 16,
    border_color: str | None = None,
) -> tk.Frame:
    """Create a soft card-like frame using highlight borders."""
    border = border_color or bg
    frame = tk.Frame(
        master,
        bg=bg,
        highlightbackground=border,
        highlightthickness=2,
        bd=0,
        padx=padx,
        pady=pady,
    )
    return frame


class _StartScreen(tk.Frame):
    """Welcome screen with large colorful story cards."""

    def __init__(
        self,
        master: tk.Widget,
        *,
        story_entries: list[tuple[str, str]],
        fonts: dict[str, tuple],
        on_story_click: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        """Build the start screen listing available stories.

        Args:
            master: Parent Tkinter widget.
            story_entries: ``(title, story_card_name)`` pairs for each adventure.
            fonts: Resolved font tuples for this screen.
            on_story_click: When set, story cards invoke this with the NFC card name.
        """
        super().__init__(master, bg=COLOR_BG, **kwargs)
        self._fonts = fonts
        self._on_story_click = on_story_click
        self._build(story_entries)

    def _bind_story_click(self, widget: tk.Widget, card_name: str) -> None:
        """Make a widget simulate *card_name* when clicked (debug mode only)."""
        if self._on_story_click is None:
            return
        widget.bind(
            "<Button-1>",
            lambda _event, name=card_name: self._on_story_click(name),
        )
        widget.config(cursor="hand2")

    def _build(self, story_entries: list[tuple[str, str]]) -> None:
        header = tk.Frame(self, bg=COLOR_BG)
        header.pack(fill=tk.X, padx=32, pady=(28, 12))

        tk.Label(
            header,
            text="Tangible NFC Interactive Storybook",
            font=self._fonts["title"],
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG,
            justify=tk.CENTER,
        ).pack()

        tk.Label(
            header,
            text="Scan a story card and choose the adventure with NFC cards!",
            font=self._fonts["subtitle"],
            fg=COLOR_MUTED,
            bg=COLOR_BG,
            justify=tk.CENTER,
            wraplength=720,
        ).pack(pady=(8, 0))

        cards_row = tk.Frame(self, bg=COLOR_BG)
        cards_row.pack(expand=True, fill=tk.BOTH, padx=32, pady=(8, 24))

        display_entries = story_entries or [
            ("Benny and the Lost Crystal", "Benny"),
            ("Mina and the Missing Moon Lantern", "Mina"),
            ("Nova and the Friendly Star", "Nova"),
        ]

        for index, (title, card_name) in enumerate(display_entries):
            emoji, card_color = _story_card_look(title, index)
            card = _rounded_frame(
                cards_row,
                bg=card_color,
                padx=20,
                pady=24,
                border_color=COLOR_SURFACE,
            )
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=8)
            self._bind_story_click(card, card_name)

            emoji_label = tk.Label(
                card,
                text=emoji,
                font=self._fonts["card_emoji"],
                fg=COLOR_TEXT_DARK,
                bg=card_color,
            )
            emoji_label.pack(pady=(0, 8))
            self._bind_story_click(emoji_label, card_name)

            title_label = tk.Label(
                card,
                text=title,
                font=self._fonts["card_title"],
                fg=COLOR_TEXT_DARK,
                bg=card_color,
                justify=tk.CENTER,
                wraplength=220,
            )
            title_label.pack()
            self._bind_story_click(title_label, card_name)

        hint_text = (
            "✨ Click a story card or scan NFC to begin! ✨"
            if self._on_story_click is not None
            else "✨ Scan a story card to begin your adventure! ✨"
        )
        hint = tk.Label(
            self,
            text=hint_text,
            font=self._fonts["subtitle"],
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
        )
        hint.pack(pady=(0, 20))


class _StorySceneScreen(tk.Frame):
    """Active story scene with image, text, choices, and inventory."""

    def __init__(
        self,
        master: tk.Widget,
        *,
        fonts: dict[str, tuple],
        choice_clicks_enabled: bool = False,
        **kwargs: object,
    ) -> None:
        """Build the scene layout widgets.

        Args:
            master: Parent Tkinter widget.
            fonts: Resolved font tuples for this screen.
            choice_clicks_enabled: When True, choice cards invoke the click callback.
        """
        super().__init__(master, bg=COLOR_BG, **kwargs)
        self._fonts = fonts
        self._photo: object | None = None
        self._choice_clicks_enabled = choice_clicks_enabled
        self._choice_click_callback: Callable[[str], None] | None = None
        self._build()

    def set_choice_click_callback(self, callback: Callable[[str], None] | None) -> None:
        """Register a callback invoked with the exact choice key when a card is clicked."""
        self._choice_click_callback = callback

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        progress = _rounded_frame(
            self,
            bg=COLOR_SURFACE,
            padx=20,
            pady=12,
            border_color=PASTEL_LAVENDER,
        )
        progress.grid(row=0, column=0, sticky="ew", padx=28, pady=(16, 8))
        progress.columnconfigure(0, weight=1)

        self._progress_story_label = tk.Label(
            progress,
            text="",
            font=self._fonts["progress_story"],
            fg=COLOR_TEXT_DARK,
            bg=COLOR_SURFACE,
            anchor=tk.W,
        )
        self._progress_story_label.grid(row=0, column=0, sticky="ew")

        self._progress_scene_label = tk.Label(
            progress,
            text="",
            font=self._fonts["progress_scene"],
            fg=COLOR_MUTED,
            bg=COLOR_SURFACE,
            anchor=tk.W,
        )
        self._progress_scene_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        content = tk.Frame(self, bg=COLOR_BG)
        content.grid(row=1, column=0, sticky="nsew", padx=28, pady=8)
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        self._image_frame = _rounded_frame(
            content,
            bg=COLOR_PLACEHOLDER,
            padx=8,
            pady=8,
            border_color=COLOR_SURFACE,
        )
        self._image_frame.configure(width=IMAGE_MAX_WIDTH, height=IMAGE_MAX_HEIGHT)
        self._image_frame.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self._image_frame.grid_propagate(False)

        self._image_label = tk.Label(
            self._image_frame,
            bg=COLOR_PLACEHOLDER,
            fg=COLOR_MUTED,
            text="🖼️",
            font=self._fonts["card_emoji"],
        )
        self._image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        right = tk.Frame(content, bg=COLOR_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=0)
        right.rowconfigure(3, weight=0)

        self._scene_title_label = tk.Label(
            right,
            text="",
            font=self._fonts["scene_title"],
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG,
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=520,
        )
        self._scene_title_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        text_frame = _rounded_frame(
            right,
            bg=COLOR_SURFACE,
            padx=20,
            pady=16,
            border_color=PASTEL_BLUE,
        )
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text_scroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL)
        text_scroll.grid(row=0, column=1, sticky="ns")

        self._text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=self._fonts["story"],
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            relief=tk.FLAT,
            highlightthickness=0,
            padx=6,
            pady=6,
            height=10,
            state=tk.DISABLED,
            cursor="arrow",
            yscrollcommand=text_scroll.set,
        )
        self._text_widget.grid(row=0, column=0, sticky="nsew")
        text_scroll.config(command=self._text_widget.yview)

        choices_frame = tk.Frame(right, bg=COLOR_BG)
        choices_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        tk.Label(
            choices_frame,
            text="What should we do next?",
            font=self._fonts["choice_heading"],
            fg=COLOR_ACCENT,
            bg=COLOR_BG,
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(0, 10))

        self._choices_frame = tk.Frame(choices_frame, bg=COLOR_BG)
        self._choices_frame.pack(fill=tk.X)

        inventory_outer = _rounded_frame(
            right,
            bg=PASTEL_YELLOW,
            padx=16,
            pady=14,
            border_color=COLOR_SURFACE,
        )
        inventory_outer.grid(row=3, column=0, sticky="ew")

        tk.Label(
            inventory_outer,
            text="My Backpack 🎒",
            font=self._fonts["small"],
            fg=COLOR_TEXT_DARK,
            bg=PASTEL_YELLOW,
            anchor=tk.W,
        ).pack(anchor=tk.W, pady=(0, 6))

        self._inventory_label = tk.Label(
            inventory_outer,
            text="(empty)",
            font=self._fonts["body"],
            fg=COLOR_MUTED,
            bg=PASTEL_YELLOW,
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
            story_title: Active story title shown in the progress header.
            scene: Current scene data (text and image path).
            inventory: Item names held by the player.
            available_choices: Action card names valid in this scene.
            asset_manager: Loader for scene images and placeholders.
        """
        self._progress_story_label.config(text=story_title)

        scene_heading = scene.title.strip() if scene.title else scene.id.replace("_", " ").title()
        self._progress_scene_label.config(text=f"Scene: {scene_heading}")
        self._scene_title_label.config(text=scene_heading)

        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.insert(tk.END, scene.text)
        self._text_widget.config(state=tk.DISABLED)
        self._text_widget.yview_moveto(0.0)

        """self._render_choices(available_choices, scene.choice_labels)
        self._render_inventory(inventory)
        self._render_image(scene.image, asset_manager)"""
        self._render_image(scene.image, asset_manager)
        self._render_choices(available_choices, scene.choice_labels)
        self._render_inventory(inventory)

    def _render_choices(
        self,
        choices: list[str],
        choice_labels: dict[str, str],
    ) -> None:
        """Render choice cards using engine keys; labels are display-only."""
        for widget in self._choices_frame.winfo_children():
            widget.destroy()

        if not choices:
            tk.Label(
                self._choices_frame,
                text="No choices right now",
                font=self._fonts["small"],
                fg=COLOR_MUTED,
                bg=COLOR_BG,
            ).pack(anchor=tk.W)
            return

        cards_row = tk.Frame(self._choices_frame, bg=COLOR_BG)
        cards_row.pack(fill=tk.X)

        for index, choice_key in enumerate(choices):
            card_color = CHOICE_PILL_COLORS[index % len(CHOICE_PILL_COLORS)]
            label_text = choice_labels.get(choice_key, choice_key)
            card = _rounded_frame(
                cards_row,
                bg=card_color,
                padx=16,
                pady=12,
                border_color=COLOR_SURFACE,
            )
            card.pack(side=tk.LEFT, padx=(0, 12), pady=4)

            if self._choice_clicks_enabled and self._choice_click_callback is not None:
                tk.Button(
                    card,
                    text=label_text,
                    font=self._fonts["choice_card"],
                    fg=COLOR_TEXT_DARK,
                    bg=card_color,
                    activebackground=card_color,
                    activeforeground=COLOR_TEXT_DARK,
                    relief=tk.FLAT,
                    highlightthickness=0,
                    bd=0,
                    justify=tk.CENTER,
                    wraplength=180,
                    cursor="hand2",
                    command=lambda key=choice_key: self._choice_click_callback(key),
                ).pack()
            else:
                tk.Label(
                    card,
                    text=label_text,
                    font=self._fonts["choice_card"],
                    fg=COLOR_TEXT_DARK,
                    bg=card_color,
                    justify=tk.CENTER,
                    wraplength=180,
                ).pack()

    def _render_inventory(self, inventory: list[str]) -> None:
        if inventory:
            self._inventory_label.config(text=", ".join(inventory), fg=COLOR_TEXT)
        else:
            self._inventory_label.config(text="(empty)", fg=COLOR_MUTED)

    def _render_image(self, image_path: str, asset_manager: AssetManager) -> None:
        if not image_path:
            self._photo = None
            self._image_label.config(image="", text="🖼️")
            return
        self._image_label.config(image="", text="Loading…")

        self._image_label.update_idletasks()
        self._photo = asset_manager.load_image(
            image_path,
            (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT),
        )
        self._image_label.config(image=self._photo, text="")


class _EndingScreen(tk.Frame):
    """Terminal story screen with celebration styling."""

    def __init__(self, master: tk.Widget, *, fonts: dict[str, tuple], **kwargs: object) -> None:
        """Build the ending layout widgets.

        Args:
            master: Parent Tkinter widget.
            fonts: Resolved font tuples for this screen.
        """
        super().__init__(master, bg=COLOR_BG_ALT, **kwargs)
        self._fonts = fonts
        self._photo: object | None = None
        self._build()

    def _build(self) -> None:
        container = tk.Frame(self, bg=COLOR_BG_ALT)
        container.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        tk.Label(
            container,
            text="🎉",
            font=(self._fonts["card_emoji"][0], 48),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_ALT,
        ).pack(pady=(0, 4))

        self._celebration_label = tk.Label(
            container,
            text="The End 🌟",
            font=self._fonts["celebration"],
            fg=COLOR_ACCENT,
            bg=COLOR_BG_ALT,
        )
        self._celebration_label.pack(pady=(0, 8))

        self._title_label = tk.Label(
            container,
            text="",
            font=self._fonts["heading"],
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_ALT,
        )
        self._title_label.pack(pady=(0, 8))

        self._ending_label = tk.Label(
            container,
            text="",
            font=self._fonts["subtitle"],
            fg=COLOR_MUTED,
            bg=COLOR_BG_ALT,
        )
        self._ending_label.pack(pady=(0, 16))

        image_wrap = _rounded_frame(
            container,
            bg=COLOR_PLACEHOLDER,
            padx=8,
            pady=8,
            border_color=COLOR_SURFACE,
        )
        image_wrap.pack(pady=(0, 16))

        self._image_label = tk.Label(
            image_wrap,
            bg=COLOR_PLACEHOLDER,
            fg=COLOR_MUTED,
            text="🖼️",
            font=self._fonts["card_emoji"],
            width=IMAGE_MAX_WIDTH // 10,
            height=IMAGE_MAX_HEIGHT // 20,
        )
        self._image_label.pack()

        text_frame = _rounded_frame(
            container,
            bg=COLOR_SURFACE,
            padx=20,
            pady=16,
            border_color=PASTEL_PINK,
        )
        text_frame.pack(pady=(0, 20))

        self._text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=self._fonts["body"],
            fg=COLOR_TEXT,
            bg=COLOR_SURFACE,
            relief=tk.FLAT,
            highlightthickness=0,
            width=58,
            height=5,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self._text_widget.pack()

        tk.Label(
            container,
            text="Scan Restart to play again! 🔄",
            font=self._fonts["subtitle"],
            fg=COLOR_ACCENT,
            bg=COLOR_BG_ALT,
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
            self._ending_label.config(text="What a wonderful adventure!")

        self._text_widget.config(state=tk.NORMAL)
        self._text_widget.delete("1.0", tk.END)
        self._text_widget.insert(tk.END, scene.text)
        self._text_widget.config(state=tk.DISABLED)

        if not scene.image:
            self._photo = None
            self._image_label.config(image="", text="🖼️")
            return

        self._photo = asset_manager.load_image(
            scene.image,
            (IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT),
        )
        self._image_label.config(image=self._photo, text="")


class GameUI:
    """Bright, child-friendly Tkinter UI for the NFC storytelling game.

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
        story_entries: list[tuple[str, str]] | None = None,
        story_titles: list[str] | None = None,
        story_names: list[str] | None = None,
        asset_manager: AssetManager | None = None,
    ) -> None:
        """Build the widget tree and apply the bright child-friendly theme.

        Args:
            root: Tkinter root window.
            assets_dir: Directory containing scene images.
            debug_mode: When True, show a developer card-simulation panel.
            story_entries: ``(title, story_card_name)`` pairs for the start screen.
            story_titles: Deprecated; used only when ``story_entries`` is omitted.
            story_names: Deprecated alias for ``story_titles``.
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
        if story_entries is not None:
            self._story_entries = story_entries
        else:
            legacy_titles = story_titles or story_names or []
            self._story_entries = [(title, title) for title in legacy_titles]
        self._simulate_callback: Callable[[str], None] | None = None
        self._choice_click_callback: Callable[[str], None] | None = None
        self._error_after_id: str | None = None
        self._current_screen: str = "start"
        self._font_family = _resolve_font_family()
        self._fonts = _make_fonts(self._font_family)

        self._configure_root()
        self._build_layout()
        self.show_start_screen()

    def register_simulate_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when debug mode simulates a card scan.

        Args:
            callback: Called with the card name when a debug scan is triggered.
        """
        self._simulate_callback = callback

    def register_choice_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when a scene choice card is clicked.

        Args:
            callback: Called with the exact choice key from ``scene.choices``.
        """
        self._choice_click_callback = callback
        self._scene_screen.set_choice_click_callback(callback)

    def show_start_screen(self) -> None:
        """Show the welcome screen listing available story cards."""
        self._current_screen = "start"
        self._show_frame(self._start_screen)
        self.set_status("Waiting for your NFC card…")

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
        self._show_frame(self._scene_screen)

        self._scene_screen.update_content(
            story_title=story_title,
            scene=scene,
            inventory=inventory,
            available_choices=available_choices,
            asset_manager=self._asset_manager,
        )
        self.set_status("Waiting for your NFC card…")

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
        self.set_status("Story complete. Scan Restart to play again!")

    def set_status(self, message: str) -> None:
        """Update the persistent status bar message."""
        self._status_label.config(text=message, fg=COLOR_MUTED)

    def set_connection_status(self, connected: bool) -> None:
        """Show whether the NFC serial reader is connected."""
        if connected:
            self._connection_label.config(
                text="🟢 Reader connected",
                fg=COLOR_CONNECTED,
            )
        else:
            self._connection_label.config(
                text="🔴 Reader disconnected",
                fg=COLOR_DISCONNECTED,
            )

    def set_debug_mode(self, enabled: bool) -> None:
        """Show debug-mode status when serial I/O is disabled."""
        if enabled:
            self._connection_label.config(
                text="🎮 Debug mode (simulated scans)",
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
        self._status_label.config(text=message, fg=COLOR_DISCONNECTED)

        def restore() -> None:
            self._status_label.config(text=original, fg=COLOR_MUTED)
            self._error_after_id = None

        self._error_after_id = self._root.after(ERROR_DISPLAY_MS, restore)

    def _configure_root(self) -> None:
        self._root.title("Tangible NFC Interactive Storybook")
        self._root.configure(bg=COLOR_BG)
        """self._root.minsize(MIN_WIDTH, MIN_HEIGHT)"""
        self._root.attributes("-fullscreen", True)
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=self._font_family, size=14)
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
            story_entries=self._story_entries,
            fonts=self._fonts,
            on_story_click=self._trigger_simulate if self._debug_mode else None,
        )
        self._scene_screen = _StorySceneScreen(
            self._screen_container,
            fonts=self._fonts,
            choice_clicks_enabled=self._debug_mode,
        )
        self._ending_screen = _EndingScreen(self._screen_container, fonts=self._fonts)

        for screen in (self._start_screen, self._scene_screen, self._ending_screen):
            screen.grid(row=0, column=0, sticky="nsew")

        footer = tk.Frame(
            self._root,
            bg=COLOR_FOOTER,
            highlightbackground=COLOR_FOOTER_BORDER,
            highlightthickness=2,
            padx=16,
            pady=10,
        )
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)

        self._connection_label = tk.Label(
            footer,
            text="⏳ Reader connecting…",
            font=self._fonts["small"],
            fg=COLOR_MUTED,
            bg=COLOR_FOOTER,
            anchor=tk.W,
        )
        self._connection_label.grid(row=0, column=0, sticky="w")

        self._status_label = tk.Label(
            footer,
            text="Waiting for your NFC card…",
            font=self._fonts["status"],
            fg=COLOR_MUTED,
            bg=COLOR_FOOTER,
            anchor=tk.CENTER,
        )
        self._status_label.grid(row=0, column=1, sticky="ew", padx=12)

        self._last_scan_label = tk.Label(
            footer,
            text="Last scan: —",
            font=self._fonts["small"],
            fg=COLOR_MUTED,
            bg=COLOR_FOOTER,
            anchor=tk.E,
        )
        self._last_scan_label.grid(row=0, column=2, sticky="e")

        if self._debug_mode:
            self._build_debug_panel()

    def _build_debug_panel(self) -> None:
        """Build compact developer tools for simulated card scans."""
        panel = tk.LabelFrame(
            self._root,
            text="Debug — simulate scan (keys 1–9, 0, -, =)",
            font=self._fonts["debug_label"],
            fg=COLOR_MUTED,
            bg=COLOR_BG,
            labelanchor=tk.N,
        )
        panel.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

        debug_cards = [
            "Benny",
            "Mina",
            "Nova",
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

        buttons_frame = tk.Frame(panel, bg=COLOR_BG)
        buttons_frame.pack(fill=tk.X, padx=6, pady=(4, 2))

        for index, name in enumerate(debug_cards):
            emoji, card_color = DEBUG_CARD_STYLES.get(name, ("🃏", PASTEL_LAVENDER))
            label = f"{key_labels[index]}{emoji}"
            tk.Button(
                buttons_frame,
                text=label,
                font=self._fonts["debug"],
                fg=COLOR_MUTED,
                bg=card_color,
                activebackground=card_color,
                activeforeground=COLOR_TEXT_DARK,
                relief=tk.FLAT,
                highlightbackground=COLOR_SURFACE,
                highlightthickness=1,
                padx=4,
                pady=1,
                cursor="hand2",
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

        entry_frame = tk.Frame(panel, bg=COLOR_BG)
        entry_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        tk.Label(
            entry_frame,
            text="Card:",
            font=self._fonts["debug_label"],
            fg=COLOR_MUTED,
            bg=COLOR_BG,
        ).pack(side=tk.LEFT)

        self._debug_entry = tk.Entry(
            entry_frame,
            font=self._fonts["debug"],
            width=16,
            relief=tk.FLAT,
            highlightbackground=PASTEL_BLUE,
            highlightthickness=1,
        )
        self._debug_entry.pack(side=tk.LEFT, padx=6)
        self._debug_entry.bind("<Return>", self._on_debug_entry)

        tk.Button(
            entry_frame,
            text="Go",
            font=self._fonts["debug"],
            fg=COLOR_MUTED,
            bg=PASTEL_GREEN,
            activebackground=PASTEL_GREEN,
            relief=tk.FLAT,
            highlightbackground=COLOR_SURFACE,
            highlightthickness=1,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._on_debug_entry,
        ).pack(side=tk.LEFT)

    def _trigger_simulate(self, card_name: str) -> None:
        """Simulate an NFC scan using the registered card action key."""
        action_key = card_name.strip()
        if action_key and self._simulate_callback is not None:
            self._simulate_callback(action_key)

    def _on_debug_entry(self, _event: object = None) -> None:
        name = self._debug_entry.get().strip()
        if name:
            self._trigger_simulate(name)
            self._debug_entry.delete(0, tk.END)

    def _show_frame(self, frame: tk.Frame) -> None:
        frame.tkraise()
