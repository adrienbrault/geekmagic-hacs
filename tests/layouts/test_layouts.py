"""Tests for layout classes."""

import re
import sys
from datetime import UTC, datetime
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
from custom_components.geekmagic.widgets.state import WidgetState


@pytest.fixture
def renderer():
    """Create a renderer instance."""
    return Renderer()


@pytest.fixture
def canvas(renderer):
    """Create a canvas for drawing."""
    return renderer.create_canvas()


def render_with_clock(renderer, canvas, layout):
    """Place a clock in slot 0, render, and return (img, changed).

    ``changed`` is True when the render modified the blank canvas.
    """
    img, draw = canvas
    before = img.tobytes()

    config = WidgetConfig(widget_type="clock", slot=0)
    layout.set_widget(0, ClockWidget(config))

    states = {0: WidgetState(now=datetime.now(tz=UTC))}
    layout.render(renderer, draw, states)
    return img, before != img.tobytes()


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
        img, changed = render_with_clock(renderer, canvas, GridLayout(rows=2, cols=2))
        assert img.size == (480, 480)
        assert changed


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
        img, changed = render_with_clock(renderer, canvas, HeroLayout())
        assert img.size == (480, 480)
        assert changed


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
        img, changed = render_with_clock(renderer, canvas, SplitHorizontal())
        assert img.size == (480, 480)
        assert changed


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
        img, changed = render_with_clock(renderer, canvas, ThreeColumnLayout())
        assert img.size == (480, 480)
        assert changed


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
        img, changed = render_with_clock(renderer, canvas, FullscreenLayout())
        assert img.size == (480, 480)
        assert changed


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


class TestHeroHarmony:
    """Equal-sized sibling cells agree on one hero size (Layout._hero_caps)."""

    @staticmethod
    def _grid(values: list[str]):
        from custom_components.geekmagic.layouts.grid import Grid2x2
        from custom_components.geekmagic.widgets.base import WidgetConfig
        from custom_components.geekmagic.widgets.entity import EntityWidget
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState

        layout = Grid2x2()
        states = {}
        for i, value in enumerate(values):
            layout.set_widget(
                i,
                EntityWidget(
                    WidgetConfig(widget_type="entity", slot=i, entity_id=f"sensor.s{i}", label="X")
                ),
            )
            states[i] = WidgetState(entity=EntityState(entity_id=f"sensor.s{i}", state=value))
        return layout, states

    @staticmethod
    def _fits(layout, states) -> dict[int, float]:
        from custom_components.geekmagic.htmldoc import CellContext

        fits = {}
        for slot in layout.slots:
            if slot.widget is None:
                continue
            x1, y1, x2, y2 = slot.rect
            ctx = CellContext(
                width=x2 - x1, height=y2 - y1, slot_index=slot.index, theme=layout.theme
            )
            hint = slot.widget.hero_hint(ctx, states[slot.index])
            assert hint is not None
            fits[slot.index] = hint[1]
        return fits

    def test_numbers_share_the_smallest_fit(self):
        layout, states = self._grid(["23.5", "58", "1013456", "12"])
        fits = self._fits(layout, states)
        caps = layout._hero_caps(states)
        # Four members: the seven-digit value is the outlier (well under
        # the next fit) and keeps its own size; the other three agree on
        # the next-smallest.
        common = sorted(fits.values())[1]
        assert 2 not in caps
        assert caps[0] == caps[1] == caps[3] == pytest.approx(common)

    def test_words_and_numbers_are_separate_groups(self):
        layout, states = self._grid(["On", "Off", "23.5", "58"])
        caps = layout._hero_caps(states)
        fits = self._fits(layout, states)
        assert caps[0] == caps[1] == pytest.approx(min(fits[0], fits[1]))
        assert caps[2] == caps[3] == pytest.approx(min(fits[2], fits[3]))

    def test_a_cell_never_gives_up_more_than_half_its_size(self):
        layout, states = self._grid(["8", "100000000"])
        caps = layout._hero_caps(states)
        fits = self._fits(layout, states)
        # A pair has no outlier exemption; the floor bounds the loss.
        assert caps[0] == pytest.approx(max(fits[1], 0.5 * fits[0]))

    def test_render_applies_the_cap(self):
        layout, states = self._grid(["On", "Off", "Locked", "Open"])
        cells = layout._cell_documents(states)
        sizes = set()
        for _slot, document, _animated in cells:
            match = re.search(r't-hero"><div style="font-size: ([\d.]+)px', document)
            assert match is not None
            sizes.add(float(match.group(1)))
        # Three of the four words agree ("Locked" may be the outlier).
        assert len(sizes) <= 2


class TestMonochromeThemes:
    """A monochrome theme (night) owns every colour on screen."""

    def test_widget_colours_are_dropped_on_monochrome_themes(self):
        from custom_components.geekmagic.widgets.gauge import GaugeWidget
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState
        from custom_components.geekmagic.widgets.theme import THEMES

        layout = Grid2x2()
        layout.theme = THEMES["night"]
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                color=(50, 215, 75),
                options={"style": "ring"},
            )
        )
        layout.set_widget(0, widget)
        entity = EntityState(entity_id="sensor.cpu", state="73", attributes={})
        cells = layout._cell_documents({0: WidgetState(entity=entity)})
        assert "rgb(50, 215, 75)" not in cells[0][1]
        # The widget's own configuration is untouched afterwards.
        assert widget.config.color == (50, 215, 75)

    def test_colours_survive_on_ordinary_themes(self):
        from custom_components.geekmagic.widgets.gauge import GaugeWidget
        from custom_components.geekmagic.widgets.state import EntityState, WidgetState

        layout = Grid2x2()
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                color=(50, 215, 75),
                options={"style": "ring"},
            )
        )
        layout.set_widget(0, widget)
        entity = EntityState(entity_id="sensor.cpu", state="73", attributes={})
        cells = layout._cell_documents({0: WidgetState(entity=entity)})
        assert "rgb(50, 215, 75)" in cells[0][1]
