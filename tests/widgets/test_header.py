"""Tests for the chart/candlestick label-value header logic.

The four-way mode decision (inline / stacked / value_only / label_only)
is pure data — driven by text widths and container size — so it's easy
to pin down without a real renderer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.widgets._header import LabelValueHeader


def _ctx_with_text_widths(label_w: int, value_w: int, text_h: int = 10) -> MagicMock:
    """Build a mock RenderContext that returns deterministic text widths."""
    ctx = MagicMock()
    label_font = MagicMock(name="font:small")
    value_font = MagicMock(name="font:regular")

    def get_font(name: str, bold: bool = False, adjust: int = 0) -> MagicMock:
        if name == "small":
            return label_font
        if name == "regular":
            return value_font
        return MagicMock(name=f"font:{name}")

    def get_text_size(text: str, font: MagicMock) -> tuple[int, int]:
        if font is label_font:
            return (label_w, text_h)
        if font is value_font:
            return (value_w, text_h)
        return (0, text_h)

    ctx.get_font.side_effect = get_font
    ctx.get_text_size.side_effect = get_text_size
    return ctx


def _mode(ctx: MagicMock, label: str | None, value: str, inner_w: int, height: int) -> str:
    h = LabelValueHeader(label=label, value=value, value_color=(0, 0, 0))
    return h._mode(ctx, inner_w, height)


class TestHeaderMode:
    def test_empty_when_neither_present(self) -> None:
        ctx = _ctx_with_text_widths(0, 0)
        assert _mode(ctx, label=None, value="", inner_w=200, height=120) == "empty"

    def test_label_only_when_no_value(self) -> None:
        ctx = _ctx_with_text_widths(40, 0)
        assert _mode(ctx, label="Temp", value="", inner_w=200, height=120) == "label_only"

    def test_value_only_when_no_label(self) -> None:
        ctx = _ctx_with_text_widths(0, 30)
        assert _mode(ctx, label=None, value="23.5°C", inner_w=200, height=120) == "value_only"

    def test_inline_when_both_fit(self) -> None:
        # 40 + 30 + 4 gap = 74 ≤ 200 → inline.
        ctx = _ctx_with_text_widths(40, 30)
        assert _mode(ctx, label="Temp", value="23.5°C", inner_w=200, height=120) == "inline"

    def test_stacked_when_doesnt_fit_inline_but_tall_enough(self) -> None:
        # 80 + 50 + 4 = 134 > 100 → not inline. Height 120, stacked needs
        # 10+10+4 = 24 ≤ 32% of 120 = 38, and 120 ≥ 90 → stacked.
        ctx = _ctx_with_text_widths(80, 50)
        assert _mode(ctx, label="Temp", value="23.5°C", inner_w=100, height=120) == "stacked"

    def test_value_only_when_too_short_to_stack(self) -> None:
        # Doesn't fit inline (80+50+4 > 100), and height 60 < 90 → drop label.
        ctx = _ctx_with_text_widths(80, 50)
        assert _mode(ctx, label="Temp", value="23.5°C", inner_w=100, height=60) == "value_only"

    def test_value_only_when_stacked_too_tall(self) -> None:
        # Doesn't fit inline; tall text means stacked > 32% of height.
        ctx = _ctx_with_text_widths(80, 50, text_h=40)
        assert _mode(ctx, label="T", value="V", inner_w=100, height=200) == "value_only"


class TestMeasureHeight:
    @pytest.mark.parametrize(
        ("label_w", "value_w", "inner_w", "height", "expected_min"),
        [
            # Stacked: label_h(10) + value_h(10) + 8 = 28
            (80, 50, 100, 120, 28),
            # Inline: max(0.18*200=36, max(10,10)+4=14) = 36
            (40, 30, 200, 200, 36),
            # Empty: 0.08*200 = 16
            (0, 0, 200, 200, 16),
        ],
    )
    def test_measured(
        self, label_w: int, value_w: int, inner_w: int, height: int, expected_min: int
    ) -> None:
        ctx = _ctx_with_text_widths(label_w, value_w)
        label = "L" if label_w else None
        value = "V" if value_w else ""
        h = LabelValueHeader(label=label, value=value, value_color=(0, 0, 0))
        assert h.measure_height(ctx, inner_w, height) == expected_min

    def test_caches_mode(self) -> None:
        ctx = _ctx_with_text_widths(40, 30)
        h = LabelValueHeader(label="T", value="V", value_color=(0, 0, 0))
        h.measure_height(ctx, 200, 120)
        assert h._cached_mode == "inline"
