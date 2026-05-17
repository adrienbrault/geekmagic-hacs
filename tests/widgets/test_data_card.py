"""Unit tests for the ``DataCard`` declarative widget primitive.

We test the *layout policy* — that ``pick_card_mode`` returns the right
mode for each cell shape, and that ``DataCard`` builds the expected
component tree for each mode. Pixel-rendered behaviour is exercised
through the per-widget sample regressions, not here.
"""

from __future__ import annotations

from typing import cast

import pytest

from custom_components.geekmagic.widgets.colors import (
    THEME_INFO,
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
)
from custom_components.geekmagic.widgets.components import (
    Adaptive,
    Bar,
    Column,
    Icon,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
    VerticalBar,
)
from custom_components.geekmagic.widgets.data_card import (
    Chip,
    DataCard,
    cell_metrics,
    pick_card_mode,
)


class TestPickCardMode:
    """Threshold contract for ``pick_card_mode``.

    Mirrors ``component_helpers._pick_bar_mode`` (already validated
    against the gauges sample images) plus the indicator-aware
    overrides for Ring/Arc/VerticalBar.
    """

    def test_stacked_for_square_roomy_cells(self) -> None:
        # 110x110 is a 2x2 grid cell with default padding.
        assert pick_card_mode(110, 110) == "stacked"
        assert pick_card_mode(150, 150) == "stacked"

    def test_stacked_floor_is_65(self) -> None:
        # Just below the 65 px floor → compact.
        assert pick_card_mode(64, 64) == "compact"
        # At the floor → stacked (band-aware icon sizing keeps it readable).
        assert pick_card_mode(65, 65) == "stacked"

    def test_compact_only_for_very_short_cells(self) -> None:
        # short_side < 80 — too tight even for a band-aware stacked card.
        assert pick_card_mode(160, 60) == "compact"
        assert pick_card_mode(60, 60) == "compact"

    def test_wide_short_cells_with_short_side_at_floor(self) -> None:
        # 240x80 / 240x120 cells now go stacked: band-aware icon sizing
        # keeps the icon proportional and the chip strip gets its own
        # band instead of being squeezed into compact mode.
        assert pick_card_mode(240, 80) == "stacked"
        assert pick_card_mode(240, 120) == "stacked"

    def test_vertical_only_with_vertical_bar(self) -> None:
        # 80x240 has short_side=80 and height > width x 1.8 - without a
        # VerticalBar it falls back to stacked (the ``short_side >= 80``
        # rule wins); with a VerticalBar, vertical mode kicks in.
        assert pick_card_mode(80, 240) == "stacked"
        bar = VerticalBar(percent=50, color=THEME_PRIMARY)
        assert pick_card_mode(80, 240, bar) == "vertical"

    def test_ring_indicator_forces_ring_mode(self) -> None:
        ring = Ring(percent=50, color=THEME_PRIMARY)
        # Ring mode wins over stacked / compact, regardless of cell shape.
        assert pick_card_mode(70, 70, ring) == "ring"
        assert pick_card_mode(150, 150, ring) == "ring"
        assert pick_card_mode(240, 80, ring) == "ring"


class TestCellMetrics:
    """Sizing rules — replaces the scattered ``int(width * 0.0X)`` calls."""

    def test_padding_scales_with_short_side(self) -> None:
        m = cell_metrics(240, 240)
        assert m.padding == 12  # 5% of 240

    def test_padding_floor_is_two(self) -> None:
        # On a 30-px short side, 5% rounds to 1 → clamped to 2.
        m = cell_metrics(30, 30)
        assert m.padding >= 2

    def test_icon_size_clamps_to_80(self) -> None:
        # Big cell — 55% of 240 = 132, clamped down to 80.
        m = cell_metrics(240, 240)
        assert m.icon_size == 80

    def test_icon_size_floor_is_16(self) -> None:
        # Tiny cell — 55% of 28 = 15, clamped up to 16.
        m = cell_metrics(28, 28)
        assert m.icon_size == 16


class TestDataCardStacked:
    """Stacked mode — three watchOS bands, ``space-evenly``."""

    def _stacked(self, **kwargs: object) -> Column:
        card = DataCard(mode="stacked", **kwargs)  # type: ignore[arg-type]
        return cast("Column", card._build_stacked(cell_metrics(120, 120), 6))

    def test_outer_is_space_evenly_column(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        assert isinstance(col, Column)
        assert col.justify == "space-evenly"
        assert col.align == "stretch"

    def test_caption_band_uses_secondary_text(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        # First band is the caption row.
        caption_row = col.children[0]
        assert isinstance(caption_row, Row)
        text = caption_row.children[0]
        assert isinstance(text, Text)
        assert text.text == "CPU"
        assert text.color == THEME_TEXT_SECONDARY

    def test_caption_band_drops_when_no_caption_or_icon(self) -> None:
        col = self._stacked(hero="73%")
        # No caption band — first band should be the hero.
        assert isinstance(col.children[0], Row)
        text = col.children[0].children[0]
        assert isinstance(text, Text)
        assert text.text == "73%"

    def test_caption_band_includes_icon_when_set(self) -> None:
        col = self._stacked(caption="CPU", icon="mdi:cpu", hero="73%")
        caption_row = col.children[0]
        assert isinstance(caption_row, Row)
        # Two children: icon + caption text.
        assert isinstance(caption_row.children[0], Icon)
        assert isinstance(caption_row.children[1], Text)

    def test_hero_uses_text_primary_by_default(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        hero_row = col.children[1]
        assert isinstance(hero_row, Row)
        assert hero_row.children[0].color == THEME_TEXT_PRIMARY  # type: ignore[union-attr]

    def test_supporting_strip_present_when_chips_given(self) -> None:
        col = self._stacked(caption="HEATING", hero="21°", supporting=[Chip("22°")])
        assert len(col.children) == 3
        support = col.children[2]
        assert isinstance(support, Row)
        assert support.justify == "center"

    def test_multi_chip_supporting_strip_centred(self) -> None:
        # Two chips centred together rather than pushed to opposite
        # edges (Adaptive's space-between default).
        chips = [Chip("22°"), Chip("58%", icon="mdi:water-percent")]
        col = self._stacked(caption="HEATING", hero="21°", supporting=chips)
        support = col.children[2]
        assert isinstance(support, Row)
        assert support.justify == "center"

    def test_indicator_appended_at_the_end(self) -> None:
        bar = Bar(percent=73, color=THEME_PRIMARY)
        col = self._stacked(caption="CPU", hero="73%", indicator=bar)
        assert col.children[-1] is bar

    def test_empty_string_icon_treated_as_no_icon_chip_role(self) -> None:
        """ha-icon-picker writes ``""`` when cleared; without truthy
        guard the chip-role caption band would render ``Icon("")`` →
        ``help-circle`` fallback (issue #125)."""
        col = self._stacked(caption="CPU", icon="", hero="73%")
        caption_row = col.children[0]
        assert isinstance(caption_row, Row)
        assert all(not isinstance(c, Icon) for c in caption_row.children)

    def test_empty_string_icon_treated_as_no_icon_feature_role(self) -> None:
        """In feature-icon mode the empty-string icon used to be promoted
        to its own band as ``help-circle`` (issue #125)."""
        col = self._stacked(caption="CPU", icon="", icon_role="feature", hero="73%")
        # No band should contain an Icon — feature_icon must be False.
        for band in col.children:
            if isinstance(band, Row):
                assert all(not isinstance(c, Icon) for c in band.children)


class TestDataCardCompact:
    """Compact mode — header pinned top via Adaptive, indicator pinned bottom."""

    def _compact(self, **kwargs: object) -> Column:
        card = DataCard(mode="compact", **kwargs)  # type: ignore[arg-type]
        return cast("Column", card._build_compact(cell_metrics(240, 80), 6))

    def test_outer_is_space_evenly_column(self) -> None:
        col = self._compact(caption="CPU", hero="73%")
        assert isinstance(col, Column)
        assert col.justify == "space-evenly"

    def test_header_uses_adaptive_when_multiple_children(self) -> None:
        from custom_components.geekmagic.widgets.components import Flex

        col = self._compact(caption="CPU", hero="73%")
        # Single-band cards Flex-wrap so the header fills the cell.
        flex = col.children[0]
        assert isinstance(flex, Flex)
        assert isinstance(flex.child, Adaptive)

    def test_compact_header_has_spacer_between_caption_and_hero(self) -> None:
        from custom_components.geekmagic.widgets.components import Flex

        col = self._compact(caption="CPU", hero="73%")
        flex = cast("Flex", col.children[0])
        header = cast("Adaptive", flex.child)
        # Children: caption text, Spacer, hero text.
        assert isinstance(header.children[0], Text)
        assert isinstance(header.children[1], Spacer)
        assert isinstance(header.children[2], Text)

    def test_compact_lone_hero_uses_centered_row(self) -> None:
        # Bare hero (clock case) wraps in a centred Row, then the whole
        # single-band header gets Flex-wrapped to fill the cell.
        from custom_components.geekmagic.widgets.components import Flex

        col = self._compact(hero="10:30")
        flex = col.children[0]
        assert isinstance(flex, Flex)
        row = flex.child
        assert isinstance(row, Row)
        assert row.justify == "center"
        assert len(row.children) == 1
        assert isinstance(row.children[0], Text)

    def test_compact_indicator_appended(self) -> None:
        bar = Bar(percent=73, color=THEME_PRIMARY)
        col = self._compact(caption="CPU", hero="73%", indicator=bar)
        assert col.children[-1] is bar

    def test_empty_string_icon_treated_as_no_icon_feature_role(self) -> None:
        """Compact mode's feature-icon branch must also reject ``""``
        (issue #125)."""
        col = self._compact(caption="CPU", icon="", icon_role="feature", hero="73%")

        # Walk the tree; no Icon component should appear anywhere.
        def _has_icon(comp: object) -> bool:
            if isinstance(comp, Icon):
                return True
            children = getattr(comp, "children", None)
            if children:
                return any(_has_icon(c) for c in children)
            child = getattr(comp, "child", None)
            if child is not None:
                return _has_icon(child)
            return False

        assert not _has_icon(col)


class TestDataCardRing:
    """Ring mode — hero centred inside the indicator ring."""

    def test_roomy_cell_keeps_caption_above(self) -> None:
        ring = Ring(percent=70, color=THEME_PRIMARY)
        card = DataCard(mode="ring", caption="CPU", hero="70%", indicator=ring)
        col = cast("Column", card._build_ring(cell_metrics(150, 150), 6, 150, 150))
        # Bands: caption row, Flex(Stack).
        assert len(col.children) == 2
        assert isinstance(col.children[0], Row)
        # Hero is wrapped inside the Stack.
        flex = col.children[1]
        stack = flex.child  # type: ignore[attr-defined]
        assert isinstance(stack, Stack)

    def test_tight_cell_drops_caption(self) -> None:
        ring = Ring(percent=70, color=THEME_PRIMARY)
        card = DataCard(mode="ring", caption="CPU", hero="70%", indicator=ring)
        # Below the 65-px short-side floor, ring drops the caption.
        col = cast("Column", card._build_ring(cell_metrics(60, 60), 6, 60, 60))
        assert len(col.children) == 1


class TestChip:
    """Chip — small icon+text supporting metric."""

    def test_no_icon_renders_text_only(self) -> None:
        chip = Chip("22°")
        row = cast("Row", chip._build(20))
        assert isinstance(row, Row)
        assert len(row.children) == 1
        assert isinstance(row.children[0], Text)

    def test_with_icon_renders_two_children(self) -> None:
        chip = Chip("58%", icon="mdi:water-percent", color=THEME_INFO)
        row = cast("Row", chip._build(20))
        assert len(row.children) == 2
        assert isinstance(row.children[0], Icon)
        assert isinstance(row.children[1], Text)

    def test_chip_color_propagates_to_text_and_icon(self) -> None:
        chip = Chip("58%", icon="mdi:water-percent", color=THEME_INFO)
        row = cast("Row", chip._build(20))
        icon, text = row.children[0], row.children[1]
        assert isinstance(icon, Icon)
        assert isinstance(text, Text)
        assert icon.color == THEME_INFO
        assert text.color == THEME_INFO


class TestDataCardAutoMode:
    """Auto mode resolves through ``pick_card_mode`` at render time."""

    @pytest.mark.parametrize(
        ("width", "height", "indicator", "expected"),
        [
            (110, 110, None, "stacked"),
            (240, 80, None, "stacked"),  # short_side=80 → stacked (band-aware)
            (65, 65, None, "stacked"),  # at the new 65-px floor
            (60, 60, None, "compact"),  # below the floor → compact
            (80, 240, None, "stacked"),  # No VerticalBar → stacked at floor
            (80, 240, VerticalBar(percent=50, color=THEME_PRIMARY), "vertical"),
            (110, 110, Ring(percent=50, color=THEME_PRIMARY), "ring"),
        ],
    )
    def test_resolves_expected_mode(
        self, width: int, height: int, indicator: object, expected: str
    ) -> None:
        assert pick_card_mode(width, height, indicator) == expected  # type: ignore[arg-type]
