"""Tests for widget classes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.const import COLOR_CYAN
from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.chart import ChartWidget
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.media import MediaWidget
from custom_components.geekmagic.widgets.text import TextWidget


@pytest.fixture
def renderer():
    """Create a renderer instance."""
    return Renderer()


@pytest.fixture
def canvas(renderer):
    """Create a canvas for drawing."""
    return renderer.create_canvas()


@pytest.fixture
def rect():
    """Standard widget rectangle."""
    return (10, 10, 110, 110)


@pytest.fixture
def render_context(renderer, canvas, rect):
    """Create a RenderContext for widgets."""
    _, draw = canvas
    return RenderContext(draw, rect, renderer)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_entity_state():
    """Create a mock entity state."""
    state = MagicMock()
    state.state = "23.5"
    state.entity_id = "sensor.temperature"
    state.attributes = {
        "friendly_name": "Temperature",
        "unit_of_measurement": "°C",
    }
    return state


class TestWidgetConfig:
    """Tests for WidgetConfig."""

    def test_create_config(self):
        """Test creating widget config."""
        config = WidgetConfig(
            widget_type="clock",
            slot=0,
        )
        assert config.widget_type == "clock"
        assert config.slot == 0
        assert config.entity_id is None

    def test_create_config_with_options(self):
        """Test creating widget config with all options."""
        config = WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.temp",
            label="Temperature",
            color=COLOR_CYAN,
            options={"show_name": True},
        )
        assert config.entity_id == "sensor.temp"
        assert config.label == "Temperature"
        assert config.color == COLOR_CYAN
        assert config.options["show_name"] is True


class TestClockWidget:
    """Tests for ClockWidget."""

    def test_init(self):
        """Test clock widget initialization."""
        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        assert widget.show_date is True
        assert widget.show_seconds is False

    def test_init_with_options(self):
        """Test clock widget with custom options."""
        config = WidgetConfig(
            widget_type="clock",
            slot=0,
            options={"show_date": False, "show_seconds": True, "time_format": "12h"},
        )
        widget = ClockWidget(config)
        assert widget.show_date is False
        assert widget.show_seconds is True
        assert widget.time_format == "12h"

    def test_get_entities(self):
        """Test that clock has no entity dependencies."""
        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)
        assert widget.get_entities() == []

    def test_render(self, renderer, canvas, rect):
        """Test clock rendering."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(widget_type="clock", slot=0)
        widget = ClockWidget(config)

        # Should not raise exception
        widget.render(ctx)

        # Verify image is valid
        assert img.size == (480, 480)

    def test_render_24h(self, renderer, canvas, rect):
        """Test clock with 24-hour format."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(
            widget_type="clock",
            slot=0,
            options={"time_format": "24h"},
        )
        widget = ClockWidget(config)
        widget.render(ctx)
        assert img.size == (480, 480)

    def test_render_12h(self, renderer, canvas, rect):
        """Test clock with 12-hour format."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(
            widget_type="clock",
            slot=0,
            options={"time_format": "12h"},
        )
        widget = ClockWidget(config)
        widget.render(ctx)
        assert img.size == (480, 480)


class TestEntityWidget:
    """Tests for EntityWidget."""

    def test_init(self):
        """Test entity widget initialization."""
        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = EntityWidget(config)
        assert widget.show_name is True
        assert widget.show_unit is True

    def test_get_entities(self):
        """Test entity dependencies."""
        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = EntityWidget(config)
        assert widget.get_entities() == ["sensor.temperature"]

    def test_render_without_hass(self, renderer, canvas, rect):
        """Test rendering without Home Assistant (placeholder)."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = EntityWidget(config)
        widget.render(ctx)
        assert img.size == (480, 480)

    def test_render_with_entity(self, renderer, canvas, rect, mock_hass, mock_entity_state):
        """Test rendering with entity state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        mock_hass.states.get.return_value = mock_entity_state

        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = EntityWidget(config)
        widget.render(ctx, hass=mock_hass)
        assert img.size == (480, 480)


class TestMediaWidget:
    """Tests for MediaWidget."""

    def test_init(self):
        """Test media widget initialization."""
        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        assert widget.show_artist is True
        assert widget.show_progress is True

    def test_render_idle(self, renderer, canvas, rect, mock_hass):
        """Test rendering idle state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        state = MagicMock()
        state.state = "idle"
        mock_hass.states.get.return_value = state

        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        widget.render(ctx, hass=mock_hass)
        assert img.size == (480, 480)

    def test_render_playing(self, renderer, canvas, rect, mock_hass):
        """Test rendering playing state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        state = MagicMock()
        state.state = "playing"
        state.attributes = {
            "media_title": "Test Song",
            "media_artist": "Test Artist",
            "media_position": 60,
            "media_duration": 180,
        }
        mock_hass.states.get.return_value = state

        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        widget.render(ctx, hass=mock_hass)
        assert img.size == (480, 480)

    def test_format_time(self):
        """Test time formatting."""
        config = WidgetConfig(widget_type="media", slot=0)
        widget = MediaWidget(config)

        assert widget._format_time(0) == "0:00"
        assert widget._format_time(65) == "1:05"
        assert widget._format_time(3661) == "1:01:01"


class TestChartWidget:
    """Tests for ChartWidget."""

    def test_init(self):
        """Test chart widget initialization."""
        config = WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = ChartWidget(config)
        assert widget.hours == 24
        assert widget.show_value is True

    def test_set_history(self):
        """Test setting history data."""
        config = WidgetConfig(widget_type="chart", slot=0)
        widget = ChartWidget(config)

        data = [10, 15, 12, 18, 22]
        widget.set_history(data)
        assert widget._history_data == data

    def test_render_no_data(self, renderer, canvas, rect):
        """Test rendering without data."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(
            widget_type="chart",
            slot=0,
            label="Temperature",
        )
        widget = ChartWidget(config)
        widget.render(ctx)
        assert img.size == (480, 480)

    def test_render_with_data(self, renderer, canvas, rect, mock_hass, mock_entity_state):
        """Test rendering with history data."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        mock_hass.states.get.return_value = mock_entity_state

        config = WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = ChartWidget(config)
        widget.set_history([20.0, 21.5, 22.0, 21.0, 23.5, 24.0, 23.0])
        widget.render(ctx, hass=mock_hass)
        assert img.size == (480, 480)


class TestTextWidget:
    """Tests for TextWidget."""

    def test_init(self):
        """Test text widget initialization."""
        config = WidgetConfig(
            widget_type="text",
            slot=0,
            options={"text": "Hello World"},
        )
        widget = TextWidget(config)
        assert widget.text == "Hello World"
        assert widget.size == "regular"
        assert widget.align == "center"

    def test_render_static_text(self, renderer, canvas, rect):
        """Test rendering static text."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        config = WidgetConfig(
            widget_type="text",
            slot=0,
            options={"text": "Hello", "size": "large"},
        )
        widget = TextWidget(config)
        widget.render(ctx)
        assert img.size == (480, 480)

    def test_render_entity_text(self, renderer, canvas, rect, mock_hass, mock_entity_state):
        """Test rendering entity state as text."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        mock_hass.states.get.return_value = mock_entity_state

        config = WidgetConfig(
            widget_type="text",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = TextWidget(config)
        widget.render(ctx, hass=mock_hass)
        assert img.size == (480, 480)

    def test_different_alignments(self, renderer, rect):
        """Test different text alignments."""
        for align in ["left", "center", "right"]:
            img, draw = renderer.create_canvas()
            ctx = RenderContext(draw, rect, renderer)
            config = WidgetConfig(
                widget_type="text",
                slot=0,
                options={"text": "Test", "align": align},
            )
            widget = TextWidget(config)
            widget.render(ctx)
            assert img.size == (480, 480)

    def test_different_sizes(self, renderer, rect):
        """Test different text sizes."""
        for size in ["small", "regular", "large", "xlarge"]:
            img, draw = renderer.create_canvas()
            ctx = RenderContext(draw, rect, renderer)
            config = WidgetConfig(
                widget_type="text",
                slot=0,
                options={"text": "Test", "size": size},
            )
            widget = TextWidget(config)
            widget.render(ctx)
            assert img.size == (480, 480)
