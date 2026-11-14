"""The widget picker's previews: mapping, files and sizes agree.

``frontend/src/widget-previews.json`` maps widget types to the sample whose
cells the picker shows, and lists each size class's cell size, which the
panel uses to pick the preview closest to a slot. ``scripts/update_samples.py``
crops the files into ``frontend/previews/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from custom_components.geekmagic.panel import PREVIEWS_DIR, _get_dir_hash
from custom_components.geekmagic.widgets import WIDGET_CLASSES

SPEC = json.loads(
    (Path(PREVIEWS_DIR).parent / "src" / "widget-previews.json").read_text(encoding="utf-8")
)

# Widgets with no meaningful sample to show (their content is the user's
# own markup or a bare icon); the picker shows their icon instead.
WITHOUT_PREVIEW = {"html", "icon"}


def test_every_widget_type_has_a_preview_or_is_listed_without_one() -> None:
    types = set(WIDGET_CLASSES)
    mapped = set(SPEC["samples"])
    assert mapped <= types, f"unknown widget types: {sorted(mapped - types)}"
    missing = types - mapped - WITHOUT_PREVIEW
    assert not missing, (
        f"add {sorted(missing)} to frontend/src/widget-previews.json (or WITHOUT_PREVIEW)"
    )


@pytest.mark.parametrize("sample", sorted(set(SPEC["samples"].values())))
def test_each_size_of_each_preview_exists_at_its_cell_size(sample: str) -> None:
    for size, (width, height) in SPEC["sizes"].items():
        path = PREVIEWS_DIR / f"{sample}_{size}.png"
        assert path.is_file(), f"{path.name} missing: run scripts/update_samples.py"
        with Image.open(path) as image:
            assert image.size == (width, height), path.name


def test_the_preview_hash_changes_with_the_files(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"one")
    before = _get_dir_hash(tmp_path)
    (tmp_path / "a.png").write_bytes(b"two")
    assert _get_dir_hash(tmp_path) != before
