"""Tests for the declarative component system."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.widgets.components import (
    Adaptive,
    Bar,
    Column,
    Flex,
    Icon,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
)


@pytest.fixture
def mock_ctx() -> MagicMock:
    """Create a mock RenderContext."""
    ctx = MagicMock()
    ctx.width = 100
    ctx.height = 80
    ctx.get_font.return_value = MagicMock()
    ctx.get_text_size.return_value = (40, 16)
    # Theme colors for theme-aware components
    ctx.theme.text_primary = (255, 255, 255)
    ctx.theme.text_secondary = (150, 150, 150)
    return ctx


class TestText:
    """Tests for Text component."""

    def test_measure(self, mock_ctx: MagicMock) -> None:
        """Test text measurement."""
        text = Text("Hello")
        w, h = text.measure(mock_ctx, 100, 80)
        assert w == 40
        assert h == 16
        mock_ctx.get_font.assert_called_with("regular", bold=False)

    def test_measure_bold(self, mock_ctx: MagicMock) -> None:
        """Test bold text measurement."""
        text = Text("Hello", bold=True)
        text.measure(mock_ctx, 100, 80)
        mock_ctx.get_font.assert_called_with("regular", bold=True)

    def test_render_center(self, mock_ctx: MagicMock) -> None:
        """Test centered text rendering."""
        text = Text("Hello", align="center")
        text.render(mock_ctx, 10, 20, 100, 40)
        mock_ctx.draw_text.assert_called_once()
        args = mock_ctx.draw_text.call_args
        assert args[0][1] == (60, 40)  # x=10+50, y=20+20
        assert args[0][3] == (255, 255, 255)  # theme.text_primary (default)

    def test_render_start(self, mock_ctx: MagicMock) -> None:
        """Test left-aligned text rendering."""
        text = Text("Hello", align="start")
        text.render(mock_ctx, 10, 20, 100, 40)
        args = mock_ctx.draw_text.call_args
        assert args[0][1] == (10, 40)  # x=10, y=20+20


class TestIcon:
    """Tests for Icon component."""

    def test_measure_auto_size(self, mock_ctx: MagicMock) -> None:
        """Test icon auto-sizing to container with max_size constraint."""
        icon = Icon("cpu")  # default max_size=32
        w, h = icon.measure(mock_ctx, 100, 80)
        assert w == 32  # capped at max_size
        assert h == 32

    def test_measure_auto_size_custom_max(self, mock_ctx: MagicMock) -> None:
        """Test icon auto-sizing with custom max_size."""
        icon = Icon("cpu", max_size=80)
        w, h = icon.measure(mock_ctx, 100, 80)
        assert w == 80  # min(100, 80, max_size=80)
        assert h == 80

    def test_measure_fixed_size(self, mock_ctx: MagicMock) -> None:
        """Test icon with fixed size."""
        icon = Icon("cpu", size=24)
        w, h = icon.measure(mock_ctx, 100, 80)
        assert w == 24
        assert h == 24

    def test_render(self, mock_ctx: MagicMock) -> None:
        """Test icon rendering."""
        icon = Icon("cpu", size=20, color=(255, 0, 0))
        icon.render(mock_ctx, 10, 10, 40, 40)
        mock_ctx.draw_icon.assert_called_once()
        args = mock_ctx.draw_icon.call_args[0]
        assert args[0] == "cpu"
        assert args[1] == (20, 20)  # centered: 10 + (40-20)//2
        assert args[2] == 20
        assert args[3] == (255, 0, 0)


class TestBar:
    """Tests for Bar component."""

    def test_measure_default_height(self, mock_ctx: MagicMock) -> None:
        """Test bar default height calculation."""
        bar = Bar(percent=50)
        w, h = bar.measure(mock_ctx, 100, 80)
        assert w == 100  # full width
        assert h == 12  # max(6, 80*0.15)

    def test_measure_fixed_height(self, mock_ctx: MagicMock) -> None:
        """Test bar with fixed height."""
        bar = Bar(percent=50, height=8)
        w, h = bar.measure(mock_ctx, 100, 80)
        assert w == 100
        assert h == 8

    def test_render(self, mock_ctx: MagicMock) -> None:
        """Test bar rendering."""
        bar = Bar(percent=75, color=(0, 255, 0))
        bar.render(mock_ctx, 10, 20, 80, 10)
        mock_ctx.draw_bar.assert_called_once()
        args = mock_ctx.draw_bar.call_args[0]
        assert args[0] == (10, 20, 90, 30)  # rect
        assert args[1] == 75  # percent
        assert args[2] == (0, 255, 0)  # color


class TestRing:
    """Tests for Ring component."""

    def test_measure(self, mock_ctx: MagicMock) -> None:
        """Test ring measures as square."""
        ring = Ring(percent=50)
        w, h = ring.measure(mock_ctx, 100, 80)
        assert w == 80  # min(100, 80)
        assert h == 80

    def test_render(self, mock_ctx: MagicMock) -> None:
        """Test ring rendering."""
        ring = Ring(percent=75)
        ring.render(mock_ctx, 0, 0, 80, 80)
        mock_ctx.draw_ring_gauge.assert_called_once()


class TestSpacer:
    """Tests for Spacer component."""

    def test_measure_default(self, mock_ctx: MagicMock) -> None:
        """Test spacer default measurement."""
        spacer = Spacer()
        w, h = spacer.measure(mock_ctx, 100, 80)
        assert w == 0
        assert h == 0

    def test_measure_min_size(self, mock_ctx: MagicMock) -> None:
        """Test spacer with minimum size."""
        spacer = Spacer(min_size=10)
        w, h = spacer.measure(mock_ctx, 100, 80)
        assert w == 10
        assert h == 10

    def test_render_does_nothing(self, mock_ctx: MagicMock) -> None:
        """Test spacer renders nothing."""
        spacer = Spacer()
        spacer.render(mock_ctx, 0, 0, 50, 50)
        # No draw calls should be made
        mock_ctx.draw_text.assert_not_called()
        mock_ctx.draw_icon.assert_not_called()


class TestRow:
    """Tests for Row layout component."""

    def test_measure_single_child(self, mock_ctx: MagicMock) -> None:
        """Test row with single child."""
        row = Row(children=[Text("Hi")])
        w, h = row.measure(mock_ctx, 200, 100)
        assert w == 40  # text width
        assert h == 16  # text height

    def test_measure_with_gap(self, mock_ctx: MagicMock) -> None:
        """Test row measurement includes gap."""
        row = Row(children=[Text("A"), Text("B")], gap=10)
        w, _h = row.measure(mock_ctx, 200, 100)
        assert w == 40 + 10 + 40  # two texts + gap

    def test_measure_with_padding(self, mock_ctx: MagicMock) -> None:
        """Test row measurement includes padding."""
        row = Row(children=[Text("Hi")], padding=10)
        w, h = row.measure(mock_ctx, 200, 100)
        assert w == 40 + 20  # text + padding*2
        assert h == 16 + 20

    def test_empty_row(self, mock_ctx: MagicMock) -> None:
        """Test that empty row handles gracefully."""
        row = Row(children=[])
        w, h = row.measure(mock_ctx, 200, 100)
        assert w == 0
        assert h == 0


class TestColumn:
    """Tests for Column layout component."""

    def test_measure_single_child(self, mock_ctx: MagicMock) -> None:
        """Test column with single child."""
        col = Column(children=[Text("Hi")])
        w, h = col.measure(mock_ctx, 200, 100)
        assert w == 40  # text width
        assert h == 16  # text height

    def test_measure_with_gap(self, mock_ctx: MagicMock) -> None:
        """Test column measurement includes gap."""
        col = Column(children=[Text("A"), Text("B")], gap=10)
        _w, h = col.measure(mock_ctx, 200, 100)
        assert h == 16 + 10 + 16  # two texts + gap

    def test_measure_with_padding(self, mock_ctx: MagicMock) -> None:
        """Test column measurement includes padding."""
        col = Column(children=[Text("Hi")], padding=10)
        w, h = col.measure(mock_ctx, 200, 100)
        assert w == 40 + 20
        assert h == 16 + 20


class TestStack:
    """Tests for Stack layout component."""

    def test_measure_takes_max(self, mock_ctx: MagicMock) -> None:
        """Test stack takes max dimensions of children."""
        mock_ctx.get_text_size.side_effect = [(40, 16), (60, 20)]
        stack = Stack(children=[Text("short"), Text("longer")])
        w, h = stack.measure(mock_ctx, 200, 100)
        assert w == 60  # max width
        assert h == 20  # max height


class TestAdaptive:
    """Tests for Adaptive layout component."""

    def test_uses_row_when_fits(self, mock_ctx: MagicMock) -> None:
        """Test adaptive uses row layout when children fit horizontally."""
        mock_ctx.get_text_size.return_value = (20, 16)
        adaptive = Adaptive(children=[Text("A"), Text("B")], gap=4, padding=0)
        # Total width = 20 + 4 + 20 = 44, fits in 100
        # This should use Row layout
        adaptive.render(mock_ctx, 0, 0, 100, 50)
        # Can't easily verify which layout was used, but no errors means success

    def test_uses_column_when_narrow(self, mock_ctx: MagicMock) -> None:
        """Test adaptive uses column layout when too narrow."""
        mock_ctx.get_text_size.return_value = (40, 16)
        adaptive = Adaptive(children=[Text("A"), Text("B")], gap=4, padding=0)
        # Total width = 40 + 4 + 40 = 84, doesn't fit in 50
        adaptive.render(mock_ctx, 0, 0, 50, 100)


class _SizedComponent(Bar):
    """A Bar subclass that records what render coordinates it received.

    Bar already returns (max_width, h) from measure, which is exactly the
    behaviour Flex relies on, so we reuse it as a probe for the layout.
    """

    def __post_init__(self) -> None:
        self.rendered_at: tuple[int, int, int, int] | None = None

    def render(self, ctx: object, x: int, y: int, width: int, height: int) -> None:
        self.rendered_at = (x, y, width, height)


class TestFlexInRow:
    """Flex children should consume the remaining main-axis space in Row."""

    @pytest.fixture
    def real_ctx(self) -> MagicMock:
        ctx = MagicMock()
        ctx.width = 200
        ctx.height = 50
        ctx.theme.bar_background = (40, 40, 40)
        ctx.theme.text_primary = (255, 255, 255)
        ctx.theme.text_secondary = (150, 150, 150)
        ctx.get_font.return_value = MagicMock()
        # Fixed-size text so the math is predictable.
        ctx.get_text_size.return_value = (20, 10)
        return ctx

    def test_flex_gets_remaining_width(self, real_ctx: MagicMock) -> None:
        """Row with [Icon(20), Flex(Bar), Text(20)] gives Flex what's left."""
        bar_probe = _SizedComponent(percent=50)
        row = Row(
            children=[
                Icon("temp", size=20),
                Flex(bar_probe),
                Text("85%", font="tiny"),
            ],
            gap=4,
        )
        row.render(real_ctx, 0, 0, 200, 30)
        # 200 - 20(icon) - 20(text) - 4*2(gaps) = 152
        assert bar_probe.rendered_at is not None
        assert bar_probe.rendered_at[2] == 152

    def test_flex_with_no_room_collapses_to_zero(self, real_ctx: MagicMock) -> None:
        """When fixed siblings already overflow, Flex shrinks to 0."""
        bar_probe = _SizedComponent(percent=50)
        row = Row(
            children=[
                Icon("a", size=80),
                Flex(bar_probe),
                Icon("b", size=80),
            ],
            gap=4,
        )
        row.render(real_ctx, 0, 0, 100, 30)
        # 80 + 80 + 8(gaps) = 168 > 100; Flex (AUTO base) stays at 0.
        assert bar_probe.rendered_at is not None
        assert bar_probe.rendered_at[2] == 0


class TestFlexInColumn:
    @pytest.fixture
    def real_ctx(self) -> MagicMock:
        ctx = MagicMock()
        ctx.width = 100
        ctx.height = 200
        ctx.theme.bar_background = (40, 40, 40)
        ctx.theme.text_primary = (255, 255, 255)
        ctx.theme.text_secondary = (150, 150, 150)
        ctx.get_font.return_value = MagicMock()
        ctx.get_text_size.return_value = (20, 10)
        return ctx

    def test_flex_gets_remaining_height(self, real_ctx: MagicMock) -> None:
        bar_probe = _SizedComponent(percent=50, height=20)
        col = Column(
            children=[
                Icon("a", size=30),
                Flex(bar_probe),
                Icon("b", size=30),
            ],
            gap=5,
        )
        col.render(real_ctx, 0, 0, 100, 200)
        # 200 - 30 - 30 - 5*2 = 130
        assert bar_probe.rendered_at is not None
        assert bar_probe.rendered_at[3] == 130


class TestTextAutoFit:
    """auto_fit should walk the shrink chain before giving up to truncation."""

    def _ctx_with_widths(self, widths: dict[str, int]) -> MagicMock:
        ctx = MagicMock()
        ctx.theme.text_primary = (255, 255, 255)
        ctx.theme.text_secondary = (150, 150, 150)
        # Each font-name lookup returns a sentinel object so we can route
        # get_text_size by which font it was given.
        font_objs: dict[str, MagicMock] = {}

        def get_font(name: str, bold: bool = False, adjust: int = 0) -> MagicMock:
            return font_objs.setdefault(name, MagicMock(name=f"font:{name}"))

        def get_text_size(text: str, font: MagicMock) -> tuple[int, int]:
            for name, obj in font_objs.items():
                if obj is font:
                    return (widths.get(name, 0), 10)
            return (0, 10)

        ctx.get_font.side_effect = get_font
        ctx.get_text_size.side_effect = get_text_size

        def fit_text(text: str, max_width: int | None = None, bold: bool = False) -> MagicMock:
            return font_objs.setdefault("fitted", MagicMock(name="font:fitted"))

        ctx.fit_text.side_effect = fit_text
        return ctx

    def test_picks_largest_font_that_fits(self) -> None:
        # "regular" too wide, "small" fits — should pick "small".
        ctx = self._ctx_with_widths(
            {"regular": 100, "secondary": 90, "small": 60, "tertiary": 50, "tiny": 40}
        )
        text = Text(text="x", font="regular", auto_fit=True)
        font = text._pick_font(ctx, max_width=70)
        assert font is ctx.get_font("small")

    def test_scales_continuously_when_chain_bottoms_out(self) -> None:
        # Regression: "10:30:00 AM" missing the "tiny" bucket by one pixel
        # rendered as "10:30:00 A…". The chain must hand off to
        # ctx.fit_text() before resorting to truncation.
        ctx = self._ctx_with_widths(
            {"regular": 100, "secondary": 90, "small": 80, "tertiary": 70, "tiny": 60, "fitted": 50}
        )
        text = Text(text="x", font="regular", auto_fit=True)
        font = text._pick_font(ctx, max_width=55)
        assert font is ctx.fit_text("x")

    def test_falls_back_to_smallest_font_when_nothing_fits(self) -> None:
        ctx = self._ctx_with_widths(
            {"regular": 100, "secondary": 90, "small": 80, "tertiary": 70, "tiny": 60, "fitted": 60}
        )
        text = Text(text="x", font="regular", auto_fit=True)
        # Even fit_text can't go below its floor (60 wide) for 30px; should
        # still return tiny so the truncation pass at render-time can
        # ellipsize a short string.
        font = text._pick_font(ctx, max_width=30)
        assert font is ctx.get_font("tiny")

    def test_unknown_font_uses_fallback_chain(self) -> None:
        ctx = self._ctx_with_widths({"weird-font": 200, "small": 50, "tiny": 40})
        text = Text(text="x", font="weird-font", auto_fit=True)
        # weird-font (200) doesn't fit, small (50) does → picks small.
        font = text._pick_font(ctx, max_width=80)
        assert font is ctx.get_font("small")


class TestAdaptiveMeasure:
    """Adaptive.measure must report the same dimensions it will render at.

    Otherwise the outer container under-budgets height when Adaptive falls
    back to Column, and the contents overflow into siblings.
    """

    @pytest.fixture
    def ctx(self) -> MagicMock:
        ctx = MagicMock()
        ctx.theme.text_primary = (255, 255, 255)
        ctx.theme.text_secondary = (150, 150, 150)
        ctx.get_font.return_value = MagicMock()
        # Each Text("X") is 30 wide, 10 tall.
        ctx.get_text_size.return_value = (30, 10)
        return ctx

    def test_measure_returns_row_size_when_fits(self, ctx: MagicMock) -> None:
        # Two 30-wide texts + 6 gap = 66; container width 100 → fits as Row.
        adaptive = Adaptive(children=[Text("a"), Text("b")], gap=6)
        w, h = adaptive.measure(ctx, max_width=100, max_height=50)
        # Row.measure returns total_w (66) and max child h (10).
        assert (w, h) == (66, 10)

    def test_measure_returns_column_size_when_doesnt_fit(self, ctx: MagicMock) -> None:
        # Same children but a 50px container — total width 66 > 50, so
        # Adaptive should fall back to Column and report the COLUMN size.
        adaptive = Adaptive(children=[Text("a"), Text("b")], gap=6)
        w, h = adaptive.measure(ctx, max_width=50, max_height=100)
        # Column.measure returns max child width (30) and total height
        # (10 + 6 + 10 = 26).
        assert (w, h) == (30, 26)
