"""Tests for asset_manager."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from asset_manager import (
    AssetManager,
    create_placeholder_pil_image,
    infer_story_type,
)


def test_infer_story_type_from_path() -> None:
    assert infer_story_type("assets/images/fantasy/castle.png") == "Benny"
    assert infer_story_type("assets/images/mystery/foyer.png") == "Mina"
    assert infer_story_type("assets/images/space/bridge.png") == "Nova"
    assert infer_story_type("other/path.png") is None


def test_create_placeholder_pil_image_size() -> None:
    image = create_placeholder_pil_image((200, 150), scene_hint="Benny")
    assert image.size == (200, 150)


def test_image_exists_false_for_missing(tmp_path: Path) -> None:
    manager = AssetManager(tmp_path)
    assert manager.image_exists("assets/images/fantasy/missing.png") is False


def test_image_exists_true_for_png(tmp_path: Path) -> None:
    image_path = tmp_path / "assets/images/fantasy/castle.png"
    image_path.parent.mkdir(parents=True)
    create_placeholder_pil_image((64, 48)).save(image_path)

    manager = AssetManager(tmp_path)
    assert manager.image_exists("assets/images/fantasy/castle.png") is True


class _FakePhotoImage:
    """Stand-in for ImageTk.PhotoImage that avoids requiring a Tk display."""

    _instances: list["_FakePhotoImage"] = []

    def __init__(self, image: Image.Image) -> None:
        self._image = image
        self.__class__._instances.append(self)

    def width(self) -> int:
        return self._image.width

    def height(self) -> int:
        return self._image.height


@pytest.fixture(autouse=True)
def fake_photo_image(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakePhotoImage._instances.clear()
    monkeypatch.setattr("asset_manager.ImageTk.PhotoImage", _FakePhotoImage)


def test_load_image_returns_placeholder_for_missing(tmp_path: Path) -> None:
    manager = AssetManager(tmp_path)
    photo = manager.load_image("assets/images/space/bridge.png", (100, 80))
    assert photo.width() == 100
    assert photo.height() == 80


def test_load_image_caches_result(tmp_path: Path) -> None:
    manager = AssetManager(tmp_path)
    first = manager.load_image("assets/images/mystery/foyer.png", (120, 90))
    second = manager.load_image("assets/images/mystery/foyer.png", (120, 90))
    assert first is second
    assert len(_FakePhotoImage._instances) == 1


def test_clear_cache(tmp_path: Path) -> None:
    manager = AssetManager(tmp_path)
    first = manager.load_image("assets/images/fantasy/castle.png", (120, 90))
    manager.clear_cache()
    second = manager.load_image("assets/images/fantasy/castle.png", (120, 90))
    assert first is not second
    assert len(_FakePhotoImage._instances) == 2
