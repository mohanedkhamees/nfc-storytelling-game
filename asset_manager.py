"""Centralized image loading, resizing, and caching for scene assets."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageTk

logger = logging.getLogger(__name__)

COLOR_BG = "#1a1a2e"
COLOR_SURFACE = "#16213e"
COLOR_TEXT = "#eaeaea"
COLOR_MUTED = "#a0a0a0"

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

_STORY_TYPES = ("fantasy", "mystery", "space")


def infer_story_type(path: str) -> str | None:
    """Return a capitalized story genre hint from an image path, if detectable."""
    lower = path.replace("\\", "/").lower()
    for story in _STORY_TYPES:
        if f"/{story}/" in lower:
            return story.capitalize()
    return None


def create_placeholder_pil_image(
    size: tuple[int, int],
    label: str = "Missing Image",
    scene_hint: str | None = None,
) -> Image.Image:
    """Build a dark-themed placeholder PIL image with readable centered text.

    Args:
        size: Target width and height in pixels.
        label: Primary message (e.g. ``"Missing Image"``).
        scene_hint: Optional genre hint (Fantasy, Mystery, Space).

    Returns:
        A new RGB ``Image`` filled with the UI background color and label text.
    """
    width, height = size
    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle(
        [4, 4, width - 5, height - 5],
        outline=COLOR_SURFACE,
        width=2,
    )

    lines = [label]
    if scene_hint:
        lines.append(scene_hint)

    font_size = max(12, min(width, height) // 12)
    try:
        font = ImageFont.truetype("Helvetica", font_size)
        hint_font = ImageFont.truetype("Helvetica", max(10, font_size - 4))
    except OSError:
        font = ImageFont.load_default()
        hint_font = font

    y = height // 2 - (len(lines) * font_size) // 2
    for index, line in enumerate(lines):
        current_font = font if index == 0 else hint_font
        color = COLOR_TEXT if index == 0 else COLOR_MUTED
        bbox = draw.textbbox((0, 0), line, font=current_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        draw.text((x, y), line, fill=color, font=current_font)
        y += text_height + 6

    return img


class AssetManager:
    """Load, resize, and cache scene images relative to the project root.

    Missing or invalid assets resolve to themed placeholder images so the UI
    never crashes on a bad path.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the manager.

        Args:
            project_root: Directory used to resolve relative image paths.
                Defaults to the directory containing this module.
        """
        self._project_root = (
            Path(project_root) if project_root is not None else Path(__file__).resolve().parent
        )
        self._cache: dict[tuple, ImageTk.PhotoImage] = {}

    def _resolve_path(self, path: str) -> Path:
        """Resolve *path* against the project root (or return absolute paths as-is)."""
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return self._project_root / path

    def image_exists(self, path: str) -> bool:
        """Return True when *path* points to a supported image file on disk."""
        resolved = self._resolve_path(path)
        return resolved.is_file() and resolved.suffix.lower() in SUPPORTED_EXTENSIONS

    def clear_cache(self) -> None:
        """Drop all cached ``PhotoImage`` instances."""
        self._cache.clear()

    def get_placeholder(
        self,
        size: tuple[int, int],
        label: str = "Missing Image",
        path: str = "",
    ) -> ImageTk.PhotoImage:
        """Return a cached placeholder ``PhotoImage`` for the given size.

        Args:
            size: Target display dimensions.
            label: Primary placeholder text.
            path: Optional image path used to infer a story-genre hint.
        """
        scene_hint = infer_story_type(path) if path else None
        cache_key = ("__placeholder__", size, label, scene_hint)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pil_image = create_placeholder_pil_image(size, label=label, scene_hint=scene_hint)
        photo = ImageTk.PhotoImage(pil_image)
        self._cache[cache_key] = photo
        return photo

    def load_image(self, path: str, size: tuple[int, int]) -> ImageTk.PhotoImage:
        """Load and resize an image, returning a placeholder when missing.

        Args:
            path: Project-root-relative path (e.g. ``assets/images/fantasy/castle.png``).
            size: Maximum width and height; image is scaled with aspect ratio preserved.

        Returns:
            A ``PhotoImage`` suitable for Tkinter widgets. Results are cached by
            ``(path, size)``.
        """
        cache_key = (path, size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not path:
            photo = self.get_placeholder(size, path="")
            self._cache[cache_key] = photo
            return photo

        resolved = self._resolve_path(path)
        if resolved.is_file() and resolved.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                with Image.open(resolved) as img:
                    loaded = img.convert("RGBA")
                    loaded.thumbnail(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(loaded)
                    self._cache[cache_key] = photo
                    return photo
            except OSError as exc:
                logger.warning("Failed to load image %s: %s", resolved, exc)
        else:
            logger.warning("Image not found: %s", resolved)

        photo = self.get_placeholder(size, path=path)
        self._cache[cache_key] = photo
        return photo
