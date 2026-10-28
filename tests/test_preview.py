"""Tests for GeekMagic preview rendering."""

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
    LAYOUT_SPLIT_H,
)
from custom_components.geekmagic.preview import (
    MockHass,
    MockState,
    MockStates,
    render_preview,
    render_screen_preview,
)


class TestMockState:
    """Test MockState class."""

    def test_create_state(self):
        """Test creating a mock state."""
        state = MockState(
            entity_id="sensor.temp",
            state="23.5",
            attributes={"unit_of_measurement": "°C"},
        )
        assert state.entity_id == "sensor.temp"
        assert state.state == "23.5"
        assert state.attributes["unit_of_measurement"] == "°C"

    def test_default_attributes(self):
        """Test default empty attributes."""
        state = MockState(entity_id="sensor.test", state="on")
        assert state.attributes == {}


class TestMockStates:
    """Test MockStates registry."""

    def test_set_and_get(self):
        """Test setting and getting states."""
        states = MockStates()
        states.set("sensor.temp", "25", {"unit_of_measurement": "°C"})

        state = states.get("sensor.temp")
        assert state is not None
        assert state.state == "25"
        assert state.attributes["unit_of_measurement"] == "°C"

    def test_get_nonexistent(self):
        """Test getting nonexistent state returns None."""
        states = MockStates()
        assert states.get("sensor.nonexistent") is None


class TestMockHass:
    """Test MockHass class."""

    def test_has_states(self):
        """Test MockHass has states registry."""
        hass = MockHass()
        assert hasattr(hass, "states")
        assert isinstance(hass.states, MockStates)


class TestRenderPreview:
    """Test preview rendering."""

    def test_render_clock_widget(self):
        """Test rendering a clock widget."""
        widgets_config = [{"type": "clock", "slot": 0}]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_entity_widget(self):
        """Test rendering an entity widget."""
        widgets_config = [
            {"type": "entity", "slot": 0, "entity_id": "sensor.temp", "label": "Temp"}
        ]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_gauge_widget(self):
        """Test rendering a gauge widget."""
        widgets_config = [
            {
                "type": "gauge",
                "slot": 0,
                "entity_id": "sensor.cpu",
                "options": {"style": "bar", "min": 0, "max": 100},
            }
        ]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)

    def test_render_weather_widget(self):
        """Test rendering a weather widget."""
        widgets_config = [{"type": "weather", "slot": 0, "entity_id": "weather.home"}]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)

    def test_render_status_widget(self):
        """Test rendering a status widget."""
        widgets_config = [{"type": "status", "slot": 0, "entity_id": "binary_sensor.motion"}]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)

    def test_render_multiple_widgets(self):
        """Test rendering multiple widgets."""
        widgets_config = [
            {"type": "clock", "slot": 0},
            {"type": "entity", "slot": 1, "entity_id": "sensor.temp"},
            {"type": "gauge", "slot": 2, "entity_id": "sensor.cpu"},
            {"type": "status", "slot": 3, "entity_id": "binary_sensor.door"},
        ]
        result = render_preview(LAYOUT_GRID_2X2, widgets_config)

        assert isinstance(result, bytes)

    def test_render_different_layouts(self):
        """Test rendering with different layouts."""
        widgets_config = [{"type": "clock", "slot": 0}]

        # Test Grid 2x2
        result_grid = render_preview(LAYOUT_GRID_2X2, widgets_config)
        assert isinstance(result_grid, bytes)

        # Test Split
        result_split = render_preview(LAYOUT_SPLIT_H, widgets_config)
        assert isinstance(result_split, bytes)

    def test_render_empty_widgets(self):
        """Test rendering with no widgets."""
        result = render_preview(LAYOUT_GRID_2X2, [])
        assert isinstance(result, bytes)


class TestRenderScreenPreview:
    """Test screen preview rendering."""

    def test_render_screen_preview(self):
        """Test rendering a complete screen configuration."""
        screen_config = {
            CONF_LAYOUT: LAYOUT_GRID_2X2,
            CONF_WIDGETS: [
                {"type": "clock", "slot": 0},
                {"type": "entity", "slot": 1, "entity_id": "sensor.temp"},
            ],
        }
        result = render_screen_preview(screen_config)

        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_render_screen_preview_default_layout(self):
        """Test rendering with default layout."""
        screen_config = {
            CONF_WIDGETS: [{"type": "clock", "slot": 0}],
        }
        result = render_screen_preview(screen_config)

        assert isinstance(result, bytes)
