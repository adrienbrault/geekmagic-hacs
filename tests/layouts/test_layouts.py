"""Tests for layout classes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import pytest

from custom_components.geekmagic.layouts.base import Slot
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid2x3, Grid3x3, GridLayout
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.split import (
    SplitHorizontal,
    SplitVertical,
    ThreeColumnLayout,
)
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.clock import ClockWidget


@pytest.fixture
def renderer():
    """Create a renderer instance."""
    return Renderer()


@pytest.fixture
def canvas(renderer):
    """Create a canvas for drawing."""
    return renderer.create_canvas()


class TestSlot:
    """Tests for Slot dataclass."""

    def test_create_slot(self):
        """Test creating a slot."""
        slot = Slot(index=0, rect=(10, 10, 100, 100))
        assert slot.index == 0
        assert slot.rect == (10, 10, 100, 100)
        assert slot.widget is None

    def test_slot_with_widget(self):
        """Test creating a slot with a widget."""
        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        slot = Slot(index=0, rect=(10, 10, 100, 100), widget=widget)
        assert slot.widget is not None


class TestGridLayout:
    """Tests for GridLayout."""

    def test_init_2x2(self):
        """Test 2x2 grid initialization."""
        layout = GridLayout(rows=2, cols=2)
        assert layout.rows == 2
        assert layout.cols == 2
        assert layout.get_slot_count() == 4

    def test_init_2x3(self):
        """Test 2x3 grid initialization."""
        layout = GridLayout(rows=2, cols=3)
        assert layout.get_slot_count() == 6

    def test_init_3x3(self):
        """Test 3x3 grid initialization."""
        layout = GridLayout(rows=3, cols=3)
        assert layout.get_slot_count() == 9

    def test_slot_rectangles_valid(self):
        """Test that slot rectangles are valid (x2 > x1, y2 > y1)."""
        layout = GridLayout(rows=2, cols=2)
        for slot in layout.slots:
            x1, y1, x2, y2 = slot.rect
            assert x2 > x1, f"Slot {slot.index}: x2 ({x2}) should be > x1 ({x1})"
            assert y2 > y1, f"Slot {slot.index}: y2 ({y2}) should be > y1 ({y1})"

    def test_slots_within_display(self):
        """Test that all slots are within display bounds."""
        layout = GridLayout(rows=2, cols=2)
        for slot in layout.slots:
            x1, y1, x2, y2 = slot.rect
            assert x1 >= 0 and y1 >= 0
            assert x2 <= 240 and y2 <= 240

    def test_get_slot(self):
        """Test getting a slot by index."""
        layout = GridLayout(rows=2, cols=2)
        slot = layout.get_slot(0)
        assert slot is not None
        assert slot.index == 0

    def test_get_slot_invalid(self):
        """Test getting invalid slot index."""
        layout = GridLayout(rows=2, cols=2)
        assert layout.get_slot(-1) is None
        assert layout.get_slot(10) is None

    def test_set_widget(self):
        """Test setting a widget in a slot."""
        layout = GridLayout(rows=2, cols=2)
        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)

        layout.set_widget(0, widget)
        assert layout.slots[0].widget is widget

    def test_render(self, renderer, canvas):
        """Test rendering layout with widgets."""
        img, draw = canvas
        layout = GridLayout(rows=2, cols=2)

        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        layout.set_widget(0, widget)

        layout.render(renderer, draw)
        assert img.size == (480, 480)


class TestGrid2x2:
    """Tests for Grid2x2 convenience class."""

    def test_init(self):
        """Test 2x2 grid initialization."""
        layout = Grid2x2()
        assert layout.get_slot_count() == 4


class TestGrid2x3:
    """Tests for Grid2x3 convenience class."""

    def test_init(self):
        """Test 2x3 grid initialization."""
        layout = Grid2x3()
        assert layout.get_slot_count() == 6


class TestGrid3x3:
    """Tests for Grid3x3 convenience class."""

    def test_init(self):
        """Test 3x3 grid initialization."""
        layout = Grid3x3()
        assert layout.get_slot_count() == 9


class TestHeroLayout:
    """Tests for HeroLayout."""

    def test_init_default(self):
        """Test hero layout with defaults."""
        layout = HeroLayout()
        assert layout.get_slot_count() == 4  # 1 hero + 3 footer
        assert layout.footer_slots == 3

    def test_init_custom(self):
        """Test hero layout with custom options."""
        layout = HeroLayout(footer_slots=4, hero_ratio=0.6)
        assert layout.get_slot_count() == 5
        assert layout.hero_ratio == 0.6

    def test_hero_slot_is_larger(self):
        """Test that hero slot is larger than footer slots."""
        layout = HeroLayout()
        hero = layout.slots[0]
        footer = layout.slots[1]

        hero_height = hero.rect[3] - hero.rect[1]
        footer_height = footer.rect[3] - footer.rect[1]

        assert hero_height > footer_height

    def test_slots_within_display(self):
        """Test all slots within display bounds."""
        layout = HeroLayout()
        for slot in layout.slots:
            x1, y1, x2, y2 = slot.rect
            assert x1 >= 0 and y1 >= 0
            assert x2 <= 240 and y2 <= 240

    def test_render(self, renderer, canvas):
        """Test rendering hero layout."""
        img, draw = canvas
        layout = HeroLayout()

        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        layout.set_widget(0, widget)

        layout.render(renderer, draw)
        assert img.size == (480, 480)


class TestSplitLayout:
    """Tests for SplitHorizontal and SplitVertical."""

    def test_horizontal_split(self):
        """Test horizontal split (side by side)."""
        layout = SplitHorizontal()
        assert layout.get_slot_count() == 2
        # Left and right slots should have same height but different x positions
        left = layout.slots[0].rect
        right = layout.slots[1].rect
        assert left[1] == right[1]  # Same top
        assert left[3] == right[3]  # Same bottom

    def test_vertical_split(self):
        """Test vertical split (stacked)."""
        layout = SplitVertical()
        assert layout.get_slot_count() == 2
        # Top and bottom slots should have same width but different y positions
        top = layout.slots[0].rect
        bottom = layout.slots[1].rect
        assert top[0] == bottom[0]  # Same left
        assert top[2] == bottom[2]  # Same right

    def test_ratio_50_50(self):
        """Test 50/50 split."""
        layout = SplitHorizontal(ratio=0.5)
        left = layout.slots[0].rect
        right = layout.slots[1].rect

        left_width = left[2] - left[0]
        right_width = right[2] - right[0]

        # Should be approximately equal
        assert abs(left_width - right_width) < 20

    def test_ratio_clamped(self):
        """Test that ratio is clamped to reasonable values."""
        layout = SplitHorizontal(ratio=0.1)  # Too small
        assert layout.ratio == 0.2

        layout = SplitHorizontal(ratio=0.95)  # Too large
        assert layout.ratio == 0.8

    def test_slots_within_display(self):
        """Test all slots within display bounds."""
        layout = SplitHorizontal()
        for slot in layout.slots:
            x1, y1, x2, y2 = slot.rect
            assert x1 >= 0 and y1 >= 0
            assert x2 <= 240 and y2 <= 240

    def test_render(self, renderer, canvas):
        """Test rendering split layout."""
        img, draw = canvas
        layout = SplitHorizontal()

        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        layout.set_widget(0, widget)

        layout.render(renderer, draw)
        assert img.size == (480, 480)


class TestThreeColumnLayout:
    """Tests for ThreeColumnLayout."""

    def test_init(self):
        """Test three column initialization."""
        layout = ThreeColumnLayout()
        assert layout.get_slot_count() == 3

    def test_custom_ratios(self):
        """Test custom column ratios."""
        layout = ThreeColumnLayout(ratios=(0.25, 0.5, 0.25))
        assert len(layout.slots) == 3

        # Middle column should be wider
        left = layout.slots[0].rect
        middle = layout.slots[1].rect
        right = layout.slots[2].rect

        left_width = left[2] - left[0]
        middle_width = middle[2] - middle[0]
        right_width = right[2] - right[0]

        assert middle_width > left_width
        assert middle_width > right_width

    def test_render(self, renderer, canvas):
        """Test rendering three column layout."""
        img, draw = canvas
        layout = ThreeColumnLayout()

        layout.render(renderer, draw)
        assert img.size == (480, 480)


class TestFullscreenLayout:
    """Tests for FullscreenLayout."""

    def test_init(self):
        """Test fullscreen layout initialization."""
        layout = FullscreenLayout()
        assert layout.get_slot_count() == 1

    def test_slot_is_fullscreen(self):
        """Test that the single slot covers the entire display."""
        layout = FullscreenLayout()
        slot = layout.slots[0]
        x1, y1, x2, y2 = slot.rect
        assert (x1, y1) == (0, 0)
        assert (x2, y2) == (240, 240)

    def test_no_padding(self):
        """Test that padding is always 0."""
        layout = FullscreenLayout()
        assert layout.padding == 0

    def test_padding_ignored(self):
        """Test that padding parameter is ignored."""
        layout = FullscreenLayout(padding=8)  # Should be ignored
        assert layout.padding == 0
        slot = layout.slots[0]
        x1, y1, x2, y2 = slot.rect
        assert (x1, y1) == (0, 0)
        assert (x2, y2) == (240, 240)

    def test_render(self, renderer, canvas):
        """Test rendering fullscreen layout."""
        img, draw = canvas
        layout = FullscreenLayout()

        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        layout.set_widget(0, widget)

        layout.render(renderer, draw)
        assert img.size == (480, 480)


class TestLayoutEntityTracking:
    """Tests for layout entity tracking."""

    def test_get_all_entities_empty(self):
        """Test getting entities from empty layout."""
        layout = Grid2x2()
        assert layout.get_all_entities() == []

    def test_get_all_entities_with_widgets(self):
        """Test getting entities from layout with widgets."""
        from custom_components.geekmagic.widgets.entity import EntityWidget

        layout = Grid2x2()

        config1 = WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")
        config2 = WidgetConfig(widget_type="entity", slot=1, entity_id="sensor.humidity")

        layout.set_widget(0, EntityWidget(config1))
        layout.set_widget(1, EntityWidget(config2))

        entities = layout.get_all_entities()
        assert "sensor.temp" in entities
        assert "sensor.humidity" in entities
        assert len(entities) == 2


class TestSizeAdjustRendering:
    """End-to-end tests for the per-widget text size option (issue #31)."""

    @staticmethod
    def _render_text_widget(renderer, options):
        from custom_components.geekmagic.widgets.text import TextWidget

        img, draw = renderer.create_canvas()
        layout = GridLayout(rows=2, cols=2)
        config = WidgetConfig(widget_type="text", slot=0, options=options)
        layout.set_widget(0, TextWidget(config))
        layout.render(renderer, draw)
        return img.tobytes()

    def test_size_adjust_changes_rendering(self, renderer):
        """A non-zero size_adjust produces a visibly different render."""
        base = self._render_text_widget(renderer, {"text": "Hi"})
        smaller = self._render_text_widget(renderer, {"text": "Hi", "size_adjust": -2})
        assert base != smaller

    def test_size_adjust_zero_is_byte_identical(self):
        """size_adjust=0 (explicit or absent) renders byte-identical output —
        the samples regression gate for issue #31."""
        renderer = Renderer()
        base = self._render_text_widget(renderer, {"text": "Hi"})
        explicit_zero = self._render_text_widget(renderer, {"text": "Hi", "size_adjust": 0})
        assert base == explicit_zero
