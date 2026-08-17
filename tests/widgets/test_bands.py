"""The band policy, tested once instead of once per widget.

``_bands.plan_bands`` is the seam four card widgets used to hold their
own copy of: does this cell still show its name, and which optional
bands survive? These tests pin the rule itself — the truth table across
real slot sizes, the hide strings that keep the kit from re-hiding a
band Python decided to keep, and the two seams the callers reach for
(their own content box, their own identity floor).

The widgets' own tests assert that their fragments reflect the plan;
that is the interface. This file asserts the rule.
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets._bands import IDENTITY_MIN_H, BandPlan, plan_bands
from custom_components.geekmagic.widgets._cellkit import HIDE_SHORT_H, HIDE_SMALL, cell_box
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME, get_theme


def cell(width: int, height: int, theme=DEFAULT_THEME) -> CellContext:
    """Cell context of an arbitrary size."""
    return CellContext(width=width, height=height, slot_index=0, theme=theme)


# Real slot geometry, from the smallest 3x3 tile to a fullscreen panel.
# (width, height, caption, compact_identity, small)
SIZES = [
    (40, 40, False, False, False),  # below the identity floor: nothing survives
    (60, 60, False, True, False),  # 3x3 tile: shrunk identity row
    (69, 65, False, True, False),  # 3x3 grid slot as laid out today
    (74, 228, True, False, False),  # sidebar strip: tall, far too narrow for chips
    (100, 100, True, False, False),  # exactly the .hide-short breakpoint
    (116, 116, True, False, False),  # 3x3 cell of a fullscreen grid
    (130, 130, True, False, True),  # exactly the .hide-small breakpoint
    (240, 74, False, True, False),  # hero-layout footer
    (240, 240, True, False, True),  # fullscreen
]


class TestBandTruthTable:
    """One rule, every slot the layouts actually produce."""

    @pytest.mark.parametrize(("width", "height", "caption", "compact", "small"), SIZES)
    def test_bands_across_real_slots(self, width, height, caption, compact, small):
        plan = plan_bands(cell(width, height), has_name=True)
        assert (plan.caption, plan.compact_identity, plan.small) == (caption, compact, small)

    @pytest.mark.parametrize(("width", "height", "caption", "compact", "small"), SIZES)
    def test_hide_classes_follow_the_kit(self, width, height, caption, compact, small):
        # A band kept below the kit's breakpoint must NOT carry the class
        # whose media rule would hide it again.
        plan = plan_bands(cell(width, height), has_name=True)
        # The feature-icon band above the caption takes the same class.
        assert plan.caption_hide == ("hide-short" if caption else "")
        assert plan.chips_hide == ("hide-small" if small else "")

    @pytest.mark.parametrize(("width", "height", "caption", "compact", "small"), SIZES)
    def test_a_nameless_cell_shows_no_caption(self, width, height, caption, compact, small):
        named = plan_bands(cell(width, height), has_name=True)
        nameless = plan_bands(cell(width, height), has_name=False)
        assert named.show_caption is (caption or compact)
        assert nameless.show_caption is False
        # Only the name gate differs — the geometry is the same cell.
        assert replace(nameless, show_caption=named.show_caption) == named

    @pytest.mark.parametrize(("width", "height", "caption", "compact", "small"), SIZES)
    def test_the_two_caption_modes_are_exclusive(self, width, height, caption, compact, small):
        # compact_identity exists *because* the band was shed; a cell
        # never has both, or the widget would budget the row twice.
        plan = plan_bands(cell(width, height), has_name=True)
        assert not (plan.caption and plan.compact_identity)


class TestBreakpointEdges:
    """The rule sits exactly on the kit's mirrored breakpoints."""

    def test_caption_band_turns_on_at_hide_short(self):
        assert plan_bands(cell(120, HIDE_SHORT_H - 1), has_name=True).caption is False
        assert plan_bands(cell(120, HIDE_SHORT_H), has_name=True).caption is True

    def test_chip_strip_turns_on_at_hide_small(self):
        assert plan_bands(cell(HIDE_SMALL - 1, 200), has_name=True).small is False
        assert plan_bands(cell(HIDE_SMALL, 200), has_name=True).small is True
        assert plan_bands(cell(200, HIDE_SMALL - 1), has_name=True).small is False

    def test_identity_floor_is_measured_on_the_content_box(self):
        # 44px of cell is under the 40px floor once the box is taken:
        # the chrome inset and .cell's percentage padding come off first.
        assert plan_bands(cell(120, 44), has_name=True).compact_identity is False
        assert plan_bands(cell(120, 60), has_name=True).compact_identity is True

    def test_default_box_is_the_card_family_box(self):
        ctx = cell(69, 65)
        assert plan_bands(ctx, has_name=True) == plan_bands(
            ctx, has_name=True, box_h=cell_box(ctx)[1]
        )


class TestCallerSeams:
    """What a caller may bring of its own, and what it may not."""

    def test_a_caller_budgeting_in_px_passes_its_own_box(self):
        # status budgets against cell_box_px, not the card family's
        # percentages — the floor has to mean the same thing there.
        ctx = cell(69, 65)
        assert plan_bands(ctx, has_name=True, box_h=39.0).compact_identity is False
        assert plan_bands(ctx, has_name=True, box_h=41.0).compact_identity is True

    def test_a_shallower_identity_row_may_lower_the_floor(self):
        # status's compact layout: a bare 10px caption beside a 10px icon
        # survives cells a card's caption+feature band would crowd.
        ctx = cell(69, 65)
        assert plan_bands(ctx, has_name=True, box_h=36.0).show_caption is False
        assert plan_bands(ctx, has_name=True, box_h=36.0, identity_min_h=34.0).show_caption is True

    def test_the_floor_lives_here_once(self):
        assert IDENTITY_MIN_H == 40.0

    def test_a_widget_overrides_one_field_not_the_rule(self):
        # clock's date band follows the caption breakpoint, not the chip
        # strip's; ``replace`` keeps the exception visible.
        plan = plan_bands(cell(114, 228), has_name=True)
        overridden = replace(plan, chips_hide="hide-short")
        assert overridden.chips_hide == "hide-short"
        assert overridden.caption_hide == plan.caption_hide
        assert plan.chips_hide == ""

    def test_the_plan_is_frozen(self):
        # A widget passes its plan on to card_html; a mutable one would
        # let markup and height budget drift apart mid-render.
        plan = plan_bands(cell(240, 240), has_name=True)
        with pytest.raises(AttributeError):
            setattr(plan, "caption", False)  # noqa: B010 (frozen dataclass under test)

    @pytest.mark.parametrize("theme_name", ["watchos", "light", "brutal", "neon"])
    def test_chromed_themes_shrink_the_box_not_the_breakpoints(self, theme_name):
        # The kit's media queries answer to the CELL, so caption/small are
        # theme-independent; only the identity floor sees the chrome.
        ctx = cell(240, 74, theme=get_theme(theme_name))
        plan = plan_bands(ctx, has_name=True)
        assert (plan.caption, plan.small) == (False, False)
        assert plan.compact_identity is True


def test_plan_is_a_value_not_a_computation():
    """Equal cells plan equally — the widget can compare and cache it."""
    a = plan_bands(cell(116, 116), has_name=True)
    b = plan_bands(cell(116, 116), has_name=True)
    assert a == b
    assert isinstance(a, BandPlan)
