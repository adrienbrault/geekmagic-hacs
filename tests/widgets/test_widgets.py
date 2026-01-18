"""Tests for widget classes."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.helpers import (
    get_binary_sensor_icon,
    get_domain_state_icon,
    parse_color,
    translate_binary_state,
)
from custom_components.geekmagic.widgets.media import MediaWidget
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget, StatusWidget
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.weather import WeatherWidget


def _build_entity_state(hass: Any, entity_id: str) -> EntityState | None:
    """Build EntityState from hass for a given entity_id."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    return EntityState(
        entity_id=entity_id,
        state=state.state,
        attributes=dict(state.attributes),
    )


def _build_widget_state(
    hass: Any | None = None,
    entity_id: str | None = None,
    extra_entities: list[str] | None = None,
    history: list[float] | None = None,
    forecast: list[dict[str, Any]] | None = None,
) -> WidgetState:
    """Build a WidgetState for testing.

    Args:
        hass: HomeAssistant instance (optional)
        entity_id: Primary entity ID
        extra_entities: List of additional entity IDs
        history: Chart history data
        forecast: Weather forecast data

    Returns:
        WidgetState instance
    """
    entity = None
    entities: dict[str, EntityState] = {}

    if hass and entity_id:
        entity = _build_entity_state(hass, entity_id)

    if hass and extra_entities:
        for eid in extra_entities:
            ent_state = _build_entity_state(hass, eid)
            if ent_state:
                entities[eid] = ent_state

    return WidgetState(
        entity=entity,
        entities=entities,
        history=history or [],
        forecast=forecast or [],
        image=None,
        now=datetime.now(tz=UTC),
    )


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


class TestTranslateBinaryState:
    """Tests for translate_binary_state helper."""

    def test_door_sensor_on(self):
        """Test door sensor 'on' translates to 'Open'."""
        assert translate_binary_state("on", "door") == "Open"

    def test_door_sensor_off(self):
        """Test door sensor 'off' translates to 'Closed'."""
        assert translate_binary_state("off", "door") == "Closed"

    def test_motion_sensor_on(self):
        """Test motion sensor 'on' translates to 'Detected'."""
        assert translate_binary_state("on", "motion") == "Detected"

    def test_motion_sensor_off(self):
        """Test motion sensor 'off' translates to 'Clear'."""
        assert translate_binary_state("off", "motion") == "Clear"

    def test_window_sensor(self):
        """Test window sensor translations."""
        assert translate_binary_state("on", "window") == "Open"
        assert translate_binary_state("off", "window") == "Closed"

    def test_lock_sensor(self):
        """Test lock sensor translations (on = unlocked)."""
        assert translate_binary_state("on", "lock") == "Unlocked"
        assert translate_binary_state("off", "lock") == "Locked"

    def test_connectivity_sensor(self):
        """Test connectivity sensor translations."""
        assert translate_binary_state("on", "connectivity") == "Connected"
        assert translate_binary_state("off", "connectivity") == "Disconnected"

    def test_no_device_class(self):
        """Test that no device_class returns original state."""
        assert translate_binary_state("on", None) == "on"
        assert translate_binary_state("off", None) == "off"

    def test_unknown_device_class(self):
        """Test that unknown device_class returns original state."""
        assert translate_binary_state("on", "unknown_class") == "on"
        assert translate_binary_state("off", "unknown_class") == "off"

    def test_case_insensitive(self):
        """Test that state matching is case insensitive."""
        assert translate_binary_state("ON", "door") == "Open"
        assert translate_binary_state("Off", "door") == "Closed"

    def test_other_states_unchanged(self):
        """Test that non-on/off states are returned unchanged."""
        assert translate_binary_state("unavailable", "door") == "unavailable"
        assert translate_binary_state("unknown", "motion") == "unknown"


class TestBinarySensorIcons:
    """Tests for get_binary_sensor_icon helper - reads from HA JSON files."""

    def test_door_sensor_on_icon(self):
        """Test door sensor 'on' returns open door icon."""
        icon = get_binary_sensor_icon("on", "door")
        assert icon == "mdi:door-open"

    def test_door_sensor_off_icon(self):
        """Test door sensor 'off' returns closed door icon."""
        icon = get_binary_sensor_icon("off", "door")
        assert icon == "mdi:door-closed"

    def test_motion_sensor_icons(self):
        """Test motion sensor icons for on/off states."""
        assert get_binary_sensor_icon("on", "motion") == "mdi:motion-sensor"
        assert get_binary_sensor_icon("off", "motion") == "mdi:motion-sensor-off"

    def test_window_sensor_icons(self):
        """Test window sensor icons."""
        assert get_binary_sensor_icon("on", "window") == "mdi:window-open"
        assert get_binary_sensor_icon("off", "window") == "mdi:window-closed"

    def test_lock_sensor_icons(self):
        """Test lock sensor icons (on = unlocked)."""
        assert get_binary_sensor_icon("on", "lock") == "mdi:lock-open"
        assert get_binary_sensor_icon("off", "lock") == "mdi:lock"

    def test_connectivity_icons(self):
        """Test connectivity sensor icons."""
        assert get_binary_sensor_icon("on", "connectivity") == "mdi:check-network-outline"
        assert get_binary_sensor_icon("off", "connectivity") == "mdi:close-network-outline"

    def test_no_device_class_returns_none(self):
        """Test that no device_class returns None."""
        assert get_binary_sensor_icon("on", None) is None
        assert get_binary_sensor_icon("off", None) is None

    def test_unknown_device_class_returns_none(self):
        """Test that unknown device_class returns None."""
        assert get_binary_sensor_icon("on", "nonexistent_class") is None

    def test_case_insensitive(self):
        """Test that state matching is case insensitive."""
        assert get_binary_sensor_icon("ON", "door") == "mdi:door-open"
        assert get_binary_sensor_icon("Off", "door") == "mdi:door-closed"


class TestParseColor:
    """Tests for parse_color helper function."""

    def test_parse_tuple(self):
        """Test that tuples are returned as-is."""
        result = parse_color((255, 128, 0), (0, 0, 0))
        assert result == (255, 128, 0)

    def test_parse_list(self):
        """Test that lists are converted to tuples."""
        result = parse_color([255, 128, 0], (0, 0, 0))
        assert result == (255, 128, 0)
        assert isinstance(result, tuple)

    def test_parse_list_with_strings(self):
        """Test that lists with string numbers are converted."""
        result = parse_color(["255", "128", "0"], (0, 0, 0))
        assert result == (255, 128, 0)

    def test_parse_none_returns_default(self):
        """Test that None returns the default color."""
        default = (100, 100, 100)
        result = parse_color(None, default)
        assert result == default

    def test_parse_invalid_list_returns_default(self):
        """Test that invalid list returns default."""
        default = (100, 100, 100)
        # Too few elements
        assert parse_color([255, 128], default) == default
        # Too many elements
        assert parse_color([255, 128, 0, 255], default) == default
        # Invalid values
        assert parse_color(["invalid", "values", "here"], default) == default

    def test_parse_invalid_type_returns_default(self):
        """Test that invalid types return default."""
        default = (100, 100, 100)
        assert parse_color("red", default) == default
        assert parse_color(12345, default) == default
        assert parse_color({"r": 255, "g": 128, "b": 0}, default) == default


class TestDomainStateIcons:
    """Tests for get_domain_state_icon helper - reads from HA JSON files."""

    def test_light_on_off_icons(self):
        """Test light domain icons for on/off states."""
        # Light on state returns default icon (lightbulb)
        assert get_domain_state_icon("light", "on") == "mdi:lightbulb"
        assert get_domain_state_icon("light", "off") == "mdi:lightbulb-off"

    def test_switch_on_off_icons(self):
        """Test switch domain icons for on/off states."""
        assert get_domain_state_icon("switch", "on") == "mdi:toggle-switch-variant"
        assert get_domain_state_icon("switch", "off") == "mdi:toggle-switch-variant-off"

    def test_fan_on_off_icons(self):
        """Test fan domain icons for on/off states."""
        assert get_domain_state_icon("fan", "on") == "mdi:fan"
        assert get_domain_state_icon("fan", "off") == "mdi:fan-off"

    def test_lock_state_icons(self):
        """Test lock domain icons for various states."""
        assert get_domain_state_icon("lock", "locked") == "mdi:lock"
        assert get_domain_state_icon("lock", "unlocked") == "mdi:lock-open-variant"

    def test_unknown_domain_returns_none(self):
        """Test that unknown domain returns None."""
        assert get_domain_state_icon("nonexistent_domain", "on") is None

    def test_case_insensitive(self):
        """Test that state matching is case insensitive."""
        assert get_domain_state_icon("light", "OFF") == "mdi:lightbulb-off"
        assert get_domain_state_icon("switch", "On") == "mdi:toggle-switch-variant"


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
        state = _build_widget_state()
        widget.render(ctx, state)

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
        state = _build_widget_state()
        widget.render(ctx, state)
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
        state = _build_widget_state()
        widget.render(ctx, state)
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
        state = _build_widget_state()  # No entity
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_with_entity(self, renderer, canvas, rect, hass, mock_entity_state):
        """Test rendering with entity state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        # Set up the entity state in hass
        hass.states.async_set(
            "sensor.temperature",
            "23.5",
            {"friendly_name": "Temperature", "unit_of_measurement": "°C"},
        )

        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = EntityWidget(config)
        state = _build_widget_state(hass, "sensor.temperature")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_door_sensor_shows_open(self, renderer, canvas, rect, hass):
        """Test that door sensor 'on' displays as 'Open' instead of 'on'."""
        _img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "binary_sensor.front_door",
            "on",
            {"friendly_name": "Front Door", "device_class": "door"},
        )

        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="binary_sensor.front_door",
        )
        widget = EntityWidget(config)
        state = _build_widget_state(hass, "binary_sensor.front_door")
        component = widget.render(ctx, state)

        # Check that the component tree contains "Open" text
        # The component is either a Column (CenteredValue) or IconValueDisplay
        from custom_components.geekmagic.widgets.components import (
            Column,
            IconValueDisplay,
            Panel,
            Text,
        )

        def find_value_text(comp) -> str | None:
            """Recursively find the value text in the component tree."""
            if isinstance(comp, IconValueDisplay):
                return comp.value
            if isinstance(comp, Text):
                return comp.text
            if isinstance(comp, Panel) and comp.child:
                return find_value_text(comp.child)
            if isinstance(comp, Column) and comp.children:
                # First child is typically the value
                for child in comp.children:
                    if isinstance(child, Text):
                        return child.text
            return None

        value = find_value_text(component)
        assert value == "Open", f"Expected 'Open' but got '{value}'"

    def test_render_door_sensor_shows_closed(self, renderer, canvas, rect, hass):
        """Test that door sensor 'off' displays as 'Closed' instead of 'off'."""
        _img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "binary_sensor.front_door",
            "off",
            {"friendly_name": "Front Door", "device_class": "door"},
        )

        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="binary_sensor.front_door",
        )
        widget = EntityWidget(config)
        state = _build_widget_state(hass, "binary_sensor.front_door")
        component = widget.render(ctx, state)

        from custom_components.geekmagic.widgets.components import (
            Column,
            IconValueDisplay,
            Panel,
            Text,
        )

        def find_value_text(comp) -> str | None:
            """Recursively find the value text in the component tree."""
            if isinstance(comp, IconValueDisplay):
                return comp.value
            if isinstance(comp, Text):
                return comp.text
            if isinstance(comp, Panel) and comp.child:
                return find_value_text(comp.child)
            if isinstance(comp, Column) and comp.children:
                for child in comp.children:
                    if isinstance(child, Text):
                        return child.text
            return None

        value = find_value_text(component)
        assert value == "Closed", f"Expected 'Closed' but got '{value}'"

    def test_render_motion_sensor_shows_detected(self, renderer, canvas, rect, hass):
        """Test that motion sensor 'on' displays as 'Detected'."""
        _img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "binary_sensor.motion",
            "on",
            {"friendly_name": "Motion", "device_class": "motion"},
        )

        config = WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="binary_sensor.motion",
        )
        widget = EntityWidget(config)
        state = _build_widget_state(hass, "binary_sensor.motion")
        component = widget.render(ctx, state)

        from custom_components.geekmagic.widgets.components import (
            Column,
            IconValueDisplay,
            Panel,
            Text,
        )

        def find_value_text(comp) -> str | None:
            """Recursively find the value text in the component tree."""
            if isinstance(comp, IconValueDisplay):
                return comp.value
            if isinstance(comp, Text):
                return comp.text
            if isinstance(comp, Panel) and comp.child:
                return find_value_text(comp.child)
            if isinstance(comp, Column) and comp.children:
                for child in comp.children:
                    if isinstance(child, Text):
                        return child.text
            return None

        value = find_value_text(component)
        assert value == "Detected", f"Expected 'Detected' but got '{value}'"


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

    def test_render_idle(self, renderer, canvas, rect, hass):
        """Test rendering idle state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        # Set up media player state in hass
        hass.states.async_set("media_player.living_room", "idle", {})

        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        state = _build_widget_state(hass, "media_player.living_room")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_paused(self, renderer, canvas, rect, hass):
        """Test rendering paused state shows MediaIdle (centered pause icon)."""
        _img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        # Set up media player in paused state
        hass.states.async_set(
            "media_player.living_room",
            "paused",
            {
                "media_title": "Test Song",
                "media_artist": "Test Artist",
            },
        )

        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        state = _build_widget_state(hass, "media_player.living_room")
        component = widget.render(ctx, state)

        # Verify it returns MediaIdle component (not AlbumArt or NowPlaying)
        from custom_components.geekmagic.widgets.media import MediaIdle

        assert isinstance(component, MediaIdle)

    def test_render_playing(self, renderer, canvas, rect, hass):
        """Test rendering playing state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        # Set up media player state in hass
        hass.states.async_set(
            "media_player.living_room",
            "playing",
            {
                "media_title": "Test Song",
                "media_artist": "Test Artist",
                "media_position": 60,
                "media_duration": 180,
            },
        )

        config = WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
        )
        widget = MediaWidget(config)
        state = _build_widget_state(hass, "media_player.living_room")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_format_time(self, renderer, canvas, rect):
        """Test time formatting."""
        from custom_components.geekmagic.widgets.media import _format_time

        assert _format_time(0) == "0:00"
        assert _format_time(65) == "1:05"
        assert _format_time(3661) == "1:01:01"


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
        state = _build_widget_state()  # No history
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_with_data(self, renderer, canvas, rect, hass, mock_entity_state):
        """Test rendering with history data."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        # Set up the entity state in hass
        hass.states.async_set(
            "sensor.temperature",
            "23.5",
            {"friendly_name": "Temperature", "unit_of_measurement": "°C"},
        )

        config = WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = ChartWidget(config)
        state = _build_widget_state(
            hass,
            "sensor.temperature",
            history=[20.0, 21.5, 22.0, 21.0, 23.5, 24.0, 23.0],
        )
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_is_binary_data_true(self):
        """Test binary data detection returns true for 0/1 data."""
        from custom_components.geekmagic.widgets.chart import ChartDisplay

        display = ChartDisplay(data=[0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0])
        assert display._is_binary_data() is True

    def test_is_binary_data_false(self):
        """Test binary data detection returns false for numeric data."""
        from custom_components.geekmagic.widgets.chart import ChartDisplay

        display = ChartDisplay(data=[20.0, 21.5, 22.0, 21.0, 23.5])
        assert display._is_binary_data() is False

    def test_is_binary_data_empty(self):
        """Test binary data detection returns false for empty data."""
        from custom_components.geekmagic.widgets.chart import ChartDisplay

        display = ChartDisplay(data=[])
        assert display._is_binary_data() is False

    def test_render_binary_data(self, renderer, canvas, rect, hass):
        """Test rendering with binary sensor data uses timeline bar."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "binary_sensor.door",
            "off",
            {"friendly_name": "Door"},
        )

        config = WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="binary_sensor.door",
            label="Door",
        )
        widget = ChartWidget(config)
        # Binary data: 0=closed, 1=open
        state = _build_widget_state(
            hass,
            "binary_sensor.door",
            history=[0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0],
        )
        widget.render(ctx, state)
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
        state = _build_widget_state()
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_entity_text(self, renderer, canvas, rect, hass, mock_entity_state):
        """Test rendering entity state as text."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        # Set up the entity state in hass
        hass.states.async_set(
            "sensor.temperature",
            "23.5",
            {"friendly_name": "Temperature", "unit_of_measurement": "°C"},
        )

        config = WidgetConfig(
            widget_type="text",
            slot=0,
            entity_id="sensor.temperature",
        )
        widget = TextWidget(config)
        state = _build_widget_state(hass, "sensor.temperature")
        widget.render(ctx, state)
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
            state = _build_widget_state()
            widget.render(ctx, state)
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
            state = _build_widget_state()
            widget.render(ctx, state)
            assert img.size == (480, 480)


class TestGaugeWidget:
    """Tests for GaugeWidget."""

    def test_init(self):
        """Test gauge widget initialization."""
        config = WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
        )
        widget = GaugeWidget(config)
        assert widget.style == "bar"
        assert widget.min_value == 0
        assert widget.max_value == 100
        assert widget.show_value is True

    def test_init_with_options(self):
        """Test gauge widget with custom options."""
        config = WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            options={"style": "ring", "min": 10, "max": 50, "unit": "%"},
        )
        widget = GaugeWidget(config)
        assert widget.style == "ring"
        assert widget.min_value == 10
        assert widget.max_value == 50
        assert widget.unit == "%"

    def test_render_bar_style(self, renderer, canvas, rect, hass):
        """Test rendering bar gauge."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("sensor.cpu", "75", {"friendly_name": "CPU"})

        config = WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            options={"style": "bar"},
        )
        widget = GaugeWidget(config)
        state = _build_widget_state(hass, "sensor.cpu")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_ring_style(self, renderer, canvas, rect, hass):
        """Test rendering ring gauge."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("sensor.cpu", "50", {"friendly_name": "CPU"})

        config = WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            options={"style": "ring"},
        )
        widget = GaugeWidget(config)
        state = _build_widget_state(hass, "sensor.cpu")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_arc_style(self, renderer, canvas, rect, hass):
        """Test rendering arc gauge."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("sensor.cpu", "25", {"friendly_name": "CPU"})

        config = WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu",
            options={"style": "arc"},
        )
        widget = GaugeWidget(config)
        state = _build_widget_state(hass, "sensor.cpu")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_without_entity(self, renderer, canvas, rect):
        """Test rendering without entity shows placeholder."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        config = WidgetConfig(widget_type="gauge", slot=0)
        widget = GaugeWidget(config)
        state = _build_widget_state()
        widget.render(ctx, state)
        assert img.size == (480, 480)


class TestProgressWidget:
    """Tests for ProgressWidget."""

    def test_init(self):
        """Test progress widget initialization."""
        config = WidgetConfig(
            widget_type="progress",
            slot=0,
            entity_id="sensor.steps",
        )
        widget = ProgressWidget(config)
        assert widget.target == 100
        assert widget.show_target is True

    def test_init_with_options(self):
        """Test progress widget with custom options."""
        config = WidgetConfig(
            widget_type="progress",
            slot=0,
            entity_id="sensor.steps",
            options={"target": 10000, "unit": "steps", "show_target": False},
        )
        widget = ProgressWidget(config)
        assert widget.target == 10000
        assert widget.unit == "steps"
        assert widget.show_target is False

    def test_render_with_entity(self, renderer, canvas, rect, hass):
        """Test rendering with entity state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "sensor.steps", "5000", {"friendly_name": "Steps", "unit_of_measurement": "steps"}
        )

        config = WidgetConfig(
            widget_type="progress",
            slot=0,
            entity_id="sensor.steps",
            options={"target": 10000},
        )
        widget = ProgressWidget(config)
        state = _build_widget_state(hass, "sensor.steps")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_without_entity(self, renderer, canvas, rect):
        """Test rendering without entity."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        config = WidgetConfig(widget_type="progress", slot=0)
        widget = ProgressWidget(config)
        state = _build_widget_state()
        widget.render(ctx, state)
        assert img.size == (480, 480)


class TestMultiProgressWidget:
    """Tests for MultiProgressWidget."""

    def test_init(self):
        """Test multi-progress widget initialization."""
        config = WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={"items": [], "title": "Fitness"},
        )
        widget = MultiProgressWidget(config)
        assert widget.items == []
        assert widget.title == "Fitness"

    def test_get_entities(self):
        """Test entity dependencies."""
        config = WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={
                "items": [
                    {"entity_id": "sensor.steps", "target": 10000},
                    {"entity_id": "sensor.calories", "target": 500},
                ]
            },
        )
        widget = MultiProgressWidget(config)
        assert "sensor.steps" in widget.get_entities()
        assert "sensor.calories" in widget.get_entities()

    def test_render_with_items(self, renderer, canvas, rect, hass):
        """Test rendering with multiple items."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("sensor.steps", "5000", {"friendly_name": "Steps"})
        hass.states.async_set("sensor.calories", "300", {"friendly_name": "Calories"})

        config = WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={
                "title": "Fitness",
                "items": [
                    {"entity_id": "sensor.steps", "target": 10000, "label": "Steps"},
                    {"entity_id": "sensor.calories", "target": 500, "label": "Cal"},
                ],
            },
        )
        widget = MultiProgressWidget(config)
        state = _build_widget_state(hass, extra_entities=["sensor.steps", "sensor.calories"])
        widget.render(ctx, state)
        assert img.size == (480, 480)


class TestStatusWidget:
    """Tests for StatusWidget."""

    def test_init(self):
        """Test status widget initialization."""
        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
        )
        widget = StatusWidget(config)
        assert widget.on_text == "ON"
        assert widget.off_text == "OFF"
        assert widget.show_status_text is True

    def test_init_with_options(self):
        """Test status widget with custom options."""
        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
            options={"on_text": "Open", "off_text": "Closed"},
        )
        widget = StatusWidget(config)
        assert widget.on_text == "Open"
        assert widget.off_text == "Closed"

    def test_init_with_list_colors(self):
        """Test status widget with colors as lists (from JSON)."""
        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
            options={
                "on_color": [0, 255, 0],  # List from JSON
                "off_color": [255, 0, 0],  # List from JSON
            },
        )
        widget = StatusWidget(config)
        # Colors should be converted to tuples
        assert widget.on_color == (0, 255, 0)
        assert widget.off_color == (255, 0, 0)
        assert isinstance(widget.on_color, tuple)
        assert isinstance(widget.off_color, tuple)

    def test_init_with_tuple_colors(self):
        """Test status widget with colors as tuples (native Python)."""
        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
            options={
                "on_color": (0, 255, 0),
                "off_color": (255, 0, 0),
            },
        )
        widget = StatusWidget(config)
        assert widget.on_color == (0, 255, 0)
        assert widget.off_color == (255, 0, 0)

    def test_render_with_custom_colors(self, renderer, canvas, rect, hass):
        """Test rendering with custom colors from JSON (issue #48 regression test)."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("binary_sensor.door", "on", {"friendly_name": "Front Door"})

        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
            options={
                "on_color": [0, 255, 0],  # List from JSON (like from frontend)
                "off_color": [255, 0, 0],
            },
        )
        widget = StatusWidget(config)
        state = _build_widget_state(hass, "binary_sensor.door")
        # This should not raise "TypeError: color must be int or tuple"
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_on_state(self, renderer, canvas, rect, hass):
        """Test rendering on state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("binary_sensor.door", "on", {"friendly_name": "Front Door"})

        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
        )
        widget = StatusWidget(config)
        state = _build_widget_state(hass, "binary_sensor.door")
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_off_state(self, renderer, canvas, rect, hass):
        """Test rendering off state."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("binary_sensor.door", "off", {"friendly_name": "Front Door"})

        config = WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="binary_sensor.door",
        )
        widget = StatusWidget(config)
        state = _build_widget_state(hass, "binary_sensor.door")
        widget.render(ctx, state)
        assert img.size == (480, 480)


class TestStatusListWidget:
    """Tests for StatusListWidget."""

    def test_init(self):
        """Test status list widget initialization."""
        config = WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={"entities": [], "title": "Doors"},
        )
        widget = StatusListWidget(config)
        assert widget.entities == []
        assert widget.title == "Doors"

    def test_init_with_list_colors(self):
        """Test status list widget with colors as lists (from JSON)."""
        config = WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "entities": [],
                "on_color": [0, 255, 0],  # List from JSON
                "off_color": [255, 0, 0],  # List from JSON
            },
        )
        widget = StatusListWidget(config)
        # Colors should be converted to tuples
        assert widget.on_color == (0, 255, 0)
        assert widget.off_color == (255, 0, 0)
        assert isinstance(widget.on_color, tuple)
        assert isinstance(widget.off_color, tuple)

    def test_get_entities(self):
        """Test entity dependencies."""
        config = WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={"entities": ["binary_sensor.front_door", ["binary_sensor.back_door", "Back"]]},
        )
        widget = StatusListWidget(config)
        entities = widget.get_entities()
        assert "binary_sensor.front_door" in entities
        assert "binary_sensor.back_door" in entities

    def test_render_with_custom_colors(self, renderer, canvas, rect, hass):
        """Test rendering with custom colors from JSON (issue #48 regression test)."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("binary_sensor.front_door", "on", {"friendly_name": "Front"})
        hass.states.async_set("binary_sensor.back_door", "off", {"friendly_name": "Back"})

        config = WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Doors",
                "entities": ["binary_sensor.front_door", "binary_sensor.back_door"],
                "on_color": [0, 255, 0],  # List from JSON
                "off_color": [255, 0, 0],  # List from JSON
            },
        )
        widget = StatusListWidget(config)
        state = _build_widget_state(
            hass, extra_entities=["binary_sensor.front_door", "binary_sensor.back_door"]
        )
        # This should not raise "TypeError: color must be int or tuple"
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_with_entities(self, renderer, canvas, rect, hass):
        """Test rendering with multiple entities."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set("binary_sensor.front_door", "on", {"friendly_name": "Front"})
        hass.states.async_set("binary_sensor.back_door", "off", {"friendly_name": "Back"})

        config = WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Doors",
                "entities": ["binary_sensor.front_door", "binary_sensor.back_door"],
            },
        )
        widget = StatusListWidget(config)
        state = _build_widget_state(
            hass, extra_entities=["binary_sensor.front_door", "binary_sensor.back_door"]
        )
        widget.render(ctx, state)
        assert img.size == (480, 480)


class TestWeatherWidget:
    """Tests for WeatherWidget."""

    def test_init(self):
        """Test weather widget initialization."""
        config = WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
        )
        widget = WeatherWidget(config)
        assert widget.show_forecast is True
        assert widget.forecast_days == 3
        assert widget.show_humidity is True

    def test_init_with_options(self):
        """Test weather widget with custom options."""
        config = WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
            options={"show_forecast": False, "forecast_days": 5, "show_humidity": False},
        )
        widget = WeatherWidget(config)
        assert widget.show_forecast is False
        assert widget.forecast_days == 5
        assert widget.show_humidity is False

    def test_render_without_entity(self, renderer, canvas, rect):
        """Test rendering without entity shows placeholder."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)

        config = WidgetConfig(widget_type="weather", slot=0)
        widget = WeatherWidget(config)
        state = _build_widget_state()
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_with_entity(self, renderer, canvas, rect, hass):
        """Test rendering with weather entity."""
        img, draw = canvas
        ctx = RenderContext(draw, rect, renderer)
        hass.states.async_set(
            "weather.home",
            "sunny",
            {
                "friendly_name": "Home",
                "temperature": 22,
                "humidity": 45,
                # Note: forecast is no longer in attributes since HA 2024.3+
                # It's now fetched via weather.get_forecasts service
            },
        )

        # Forecast is now provided via WidgetState, not entity attributes
        # Use realistic ISO datetime format like Home Assistant returns
        forecast = [
            {"datetime": "2025-12-29T00:00:00+00:00", "condition": "sunny", "temperature": 24},
            {"datetime": "2025-12-30T00:00:00+00:00", "condition": "cloudy", "temperature": 20},
        ]

        config = WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
        )
        widget = WeatherWidget(config)
        state = _build_widget_state(hass, "weather.home", forecast=forecast)
        widget.render(ctx, state)
        assert img.size == (480, 480)

    def test_render_compact_mode(self, renderer, hass):
        """Test rendering in compact mode (small container)."""
        img, draw = renderer.create_canvas()
        # Small rect to trigger compact mode
        small_rect = (10, 10, 70, 70)
        ctx = RenderContext(draw, small_rect, renderer)
        hass.states.async_set(
            "weather.home",
            "rainy",
            {"temperature": 15, "humidity": 80},
        )

        config = WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
        )
        widget = WeatherWidget(config)
        state = _build_widget_state(hass, "weather.home")
        widget.render(ctx, state)
        assert img.size == (480, 480)
