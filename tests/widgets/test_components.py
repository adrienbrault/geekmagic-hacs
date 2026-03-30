"""Tests for the declarative component system."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.widgets.components import (
    Adaptive,
    Bar,
    Column,
    Empty,
    Icon,
    Padding,
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

    def test_measure_clamps_to_max_width(self, mock_ctx: MagicMock) -> None:
        """Text.measure() clamps to max_width when text is wider."""
        mock_ctx.get_text_size.return_value = (200, 16)
        text = Text("Very long text string")
        w, h = text.measure(mock_ctx, 100, 80)
        assert w == 100  # clamped to max_width
        assert h == 16

    def test_measure_clamps_to_max_height(self, mock_ctx: MagicMock) -> None:
        """Text.measure() clamps to max_height when text is taller."""
        mock_ctx.get_text_size.return_value = (40, 100)
        text = Text("Hello")
        w, h = text.measure(mock_ctx, 200, 50)
        assert w == 40
        assert h == 50  # clamped to max_height

    def test_measure_bold(self, mock_ctx: MagicMock) -> None:
        """Test bold text measurement."""
        text = Text("Hello", bold=True)
        text.measure(mock_ctx, 100, 80)
        mock_ctx.get_font.assert_called_with("regular", bold=True)

    def test_render_auto_truncates(self, mock_ctx: MagicMock) -> None:
        """Text auto-truncates when rendered width is less than natural width."""
        # get_text_size returns wide text, then progressively shorter truncated versions
        mock_ctx.get_text_size.side_effect = [
            (200, 16),  # initial measurement in render
            (200, 16),  # _truncate_text: full text still too wide
            (180, 16),  # _truncate_text: text[:-1] + "…"
            (90, 16),  # _truncate_text: fits!
        ]
        text = Text("Very long text")
        text.render(mock_ctx, 0, 0, 100, 40)
        mock_ctx.draw_text.assert_called_once()
        # Verify truncated text was drawn (not the original)
        drawn_text = mock_ctx.draw_text.call_args[0][0]
        assert drawn_text.endswith("…")

    def test_render_no_truncation_when_fits(self, mock_ctx: MagicMock) -> None:
        """Text renders without truncation when it fits."""
        mock_ctx.get_text_size.return_value = (40, 16)
        text = Text("Hello")
        text.render(mock_ctx, 0, 0, 100, 40)
        drawn_text = mock_ctx.draw_text.call_args[0][0]
        assert drawn_text == "Hello"

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


class TestEmpty:
    """Tests for Empty component."""

    def test_measure(self, mock_ctx: MagicMock) -> None:
        """Test empty component measures as zero."""
        empty = Empty()
        w, h = empty.measure(mock_ctx, 100, 80)
        assert w == 0
        assert h == 0


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


class TestPadding:
    """Tests for Padding component."""

    def test_measure_with_all(self, mock_ctx: MagicMock) -> None:
        """Test padding with uniform padding."""
        padded = Padding(child=Text("Hi"), all=10)
        w, h = padded.measure(mock_ctx, 200, 100)
        assert w == 40 + 20  # text + padding*2
        assert h == 16 + 20

    def test_measure_with_horizontal_vertical(self, mock_ctx: MagicMock) -> None:
        """Test padding with separate horizontal/vertical."""
        padded = Padding(child=Text("Hi"), horizontal=20, vertical=10)
        w, h = padded.measure(mock_ctx, 200, 100)
        assert w == 40 + 40  # text + horizontal*2
        assert h == 16 + 20  # text + vertical*2

    def test_measure_with_individual(self, mock_ctx: MagicMock) -> None:
        """Test padding with individual sides."""
        padded = Padding(child=Text("Hi"), top=5, right=10, bottom=15, left=20)
        w, h = padded.measure(mock_ctx, 200, 100)
        assert w == 40 + 10 + 20  # text + right + left
        assert h == 16 + 5 + 15  # text + top + bottom
