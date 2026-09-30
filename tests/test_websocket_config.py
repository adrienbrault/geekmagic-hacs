"""Tests for the layout geometry the ``geekmagic/config`` command sends the panel."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import LAYOUT_NAMES, LAYOUT_SLOT_COUNTS
from custom_components.geekmagic.coordinator import LAYOUT_CLASSES
from custom_components.geekmagic.websocket import layout_slot_rects

EPS = 1e-3


def test_every_layout_class_has_a_slot_count() -> None:
    assert set(LAYOUT_CLASSES) == set(LAYOUT_SLOT_COUNTS)


def test_every_layout_has_a_display_name() -> None:
    assert set(LAYOUT_NAMES) == set(LAYOUT_SLOT_COUNTS)


@pytest.mark.parametrize("layout_type", sorted(LAYOUT_CLASSES))
def test_layout_rects_match_slot_count_and_fit_unit_square(layout_type: str) -> None:
    rects = layout_slot_rects()[layout_type]

    assert len(rects) == LAYOUT_SLOT_COUNTS[layout_type]
    for rect in rects:
        assert rect["x"] >= 0
        assert rect["y"] >= 0
        assert rect["w"] > 0
        assert rect["h"] > 0
        assert rect["x"] + rect["w"] <= 1 + EPS
        assert rect["y"] + rect["h"] <= 1 + EPS


@pytest.mark.parametrize("layout_type", sorted(LAYOUT_CLASSES))
def test_layout_rects_tile_the_square(layout_type: str) -> None:
    """Built without padding/gap, the slots cover the whole screen."""
    area = sum(r["w"] * r["h"] for r in layout_slot_rects()[layout_type])
    assert area == pytest.approx(1, abs=0.02)


def test_rects_follow_slot_index_order() -> None:
    """Rect i is slot i: the corner hero puts its hero at the slot it claims."""
    rects = layout_slot_rects()
    hero_slot = {
        "hero_corner_tl": 0,
        "hero_corner_tr": 1,
        "hero_corner_bl": 4,
        "hero_corner_br": 4,
    }
    for layout_type, slot in hero_slot.items():
        biggest = max(range(len(rects[layout_type])), key=lambda i: rects[layout_type][i]["w"])
        assert biggest == slot, layout_type
