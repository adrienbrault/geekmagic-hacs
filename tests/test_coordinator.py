"""Tests for GeekMagic coordinator multi-screen support."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
    LAYOUT_SPLIT_H,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator


@pytest.fixture
def coordinator_device():
    """Create mock GeekMagic device for coordinator tests."""
    device = MagicMock()
    device.upload_and_display = AsyncMock()
    device.set_brightness = AsyncMock()
    return device


@pytest.fixture
def old_format_options():
    """Create old single-screen format options."""
    return {
        CONF_REFRESH_INTERVAL: 15,
        CONF_LAYOUT: LAYOUT_GRID_2X2,
        CONF_WIDGETS: [{"type": "clock", "slot": 0}],
    }


@pytest.fixture
def new_format_options():
    """Create new multi-screen format options."""
    return {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREEN_CYCLE_INTERVAL: 30,
        CONF_SCREENS: [
            {
                "name": "Dashboard",
                CONF_LAYOUT: LAYOUT_GRID_2X2,
                CONF_WIDGETS: [{"type": "clock", "slot": 0}],
            },
            {
                "name": "Media",
                CONF_LAYOUT: LAYOUT_SPLIT_H,
                CONF_WIDGETS: [{"type": "clock", "slot": 0}],
            },
        ],
    }


class TestCoordinatorMigration:
    """Test options migration."""

    def test_migrate_old_format(self, hass, coordinator_device, old_format_options):
        """Test migrating old single-screen format."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, old_format_options)

        assert CONF_SCREENS in coordinator.options
        assert len(coordinator.options[CONF_SCREENS]) == 1
        assert coordinator.options[CONF_SCREENS][0][CONF_LAYOUT] == LAYOUT_GRID_2X2
        assert coordinator.options[CONF_REFRESH_INTERVAL] == 15

    def test_already_migrated(self, hass, coordinator_device, new_format_options):
        """Test that already-migrated options are unchanged."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)

        assert coordinator.options[CONF_SCREEN_CYCLE_INTERVAL] == 30
        assert len(coordinator.options[CONF_SCREENS]) == 2


class TestCoordinatorMultiScreen:
    """Test multi-screen functionality."""

    def test_screen_count(self, hass, coordinator_device, new_format_options):
        """Test screen count property."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        assert coordinator.screen_count == 2

    def test_current_screen_initial(self, hass, coordinator_device, new_format_options):
        """Test initial current screen is 0."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        assert coordinator.current_screen == 0

    def test_current_screen_name(self, hass, coordinator_device, new_format_options):
        """Test current screen name property."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        assert coordinator.current_screen_name == "Dashboard"

    @pytest.mark.asyncio
    async def test_set_screen(self, hass, coordinator_device, new_format_options):
        """Test setting screen by index."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]

        await coordinator.async_set_screen(1)
        assert coordinator.current_screen == 1
        assert coordinator.current_screen_name == "Media"

    @pytest.mark.asyncio
    async def test_set_screen_invalid_index(self, hass, coordinator_device, new_format_options):
        """Test setting invalid screen index is ignored."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]

        await coordinator.async_set_screen(10)  # Invalid index
        assert coordinator.current_screen == 0  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_next_screen(self, hass, coordinator_device, new_format_options):
        """Test cycling to next screen."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]

        assert coordinator.current_screen == 0
        await coordinator.async_next_screen()
        assert coordinator.current_screen == 1
        await coordinator.async_next_screen()
        assert coordinator.current_screen == 0  # Wraps around

    @pytest.mark.asyncio
    async def test_previous_screen(self, hass, coordinator_device, new_format_options):
        """Test cycling to previous screen."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, new_format_options)
        coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]

        assert coordinator.current_screen == 0
        await coordinator.async_previous_screen()
        assert coordinator.current_screen == 1  # Wraps around


class TestCoordinatorUpdateOptions:
    """Test options update functionality."""

    def test_update_options_rebuilds_screens(self, hass, coordinator_device, old_format_options):
        """Test that updating options rebuilds screens."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, old_format_options)
        assert coordinator.screen_count == 1

        # Update to multi-screen
        new_options = {
            CONF_REFRESH_INTERVAL: 10,
            CONF_SCREEN_CYCLE_INTERVAL: 0,
            CONF_SCREENS: [
                {"name": "Screen 1", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []},
                {"name": "Screen 2", CONF_LAYOUT: LAYOUT_SPLIT_H, CONF_WIDGETS: []},
                {"name": "Screen 3", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []},
            ],
        }
        coordinator.update_options(new_options)

        assert coordinator.screen_count == 3


class TestCoordinatorWidgetRegistration:
    """Test that all widget types are registered."""

    def test_all_widgets_registered(self):
        """Test that all 13 widget types are registered."""
        from custom_components.geekmagic.coordinator import WIDGET_CLASSES

        expected_widgets = [
            "camera",
            "clock",
            "entity",
            "fullscreen",
            "media",
            "chart",
            "text",
            "gauge",
            "progress",
            "multi_progress",
            "status",
            "status_list",
            "weather",
        ]

        for widget_type in expected_widgets:
            assert widget_type in WIDGET_CLASSES, f"Widget {widget_type} not registered"

        assert len(WIDGET_CLASSES) == 13


class MockState:
    """Mock State object with .state attribute for testing."""

    def __init__(self, state_value: str) -> None:
        """Initialize with state value."""
        self.state = state_value


class TestExtractNumericValues:
    """Tests for extract_numeric_values helper function.

    This function handles the minimal_response=True format from Home Assistant's
    recorder, which returns a mix of State objects and dictionaries.
    """

    def test_parse_state_objects(self):
        """Test parsing works with full State objects."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("20.0"),
            MockState("21.5"),
            MockState("22.0"),
        ]

        values = extract_numeric_values(history)

        assert values == [20.0, 21.5, 22.0]

    def test_parse_dict_objects(self):
        """Test parsing works with dictionary objects."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            {"state": "20.0", "last_changed": "2024-01-01T00:00:00Z"},
            {"state": "21.5", "last_changed": "2024-01-01T01:00:00Z"},
            {"state": "22.0", "last_changed": "2024-01-01T02:00:00Z"},
        ]

        values = extract_numeric_values(history)

        assert values == [20.0, 21.5, 22.0]

    def test_parse_mixed_format(self):
        """Test parsing the actual minimal_response=True format.

        This is the critical regression test. When minimal_response=True,
        HA returns State objects for first/last and dicts for intermediate.
        """
        from custom_components.geekmagic.coordinator import extract_numeric_values

        # Simulating exactly what minimal_response=True returns
        history = [
            MockState("20.0"),  # State object (first)
            {"state": "21.5"},  # Dict (middle)
            {"state": "22.0"},  # Dict (middle)
            {"state": "23.0"},  # Dict (middle)
            MockState("24.0"),  # State object (last)
        ]

        values = extract_numeric_values(history)

        # All 5 values should be extracted, not just first/last
        assert values == [20.0, 21.5, 22.0, 23.0, 24.0]
        assert len(values) == 5

    def test_parse_non_numeric_states_skipped(self):
        """Test that unrecognized non-numeric states are silently skipped."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("20.0"),
            MockState("unavailable"),  # Skipped - not numeric or binary
            {"state": "unknown"},  # Skipped - not numeric or binary
            {"state": "22.0"},
            MockState("on"),  # Converted to 1.0 (binary)
            {"state": "23.5"},
        ]

        values = extract_numeric_values(history)

        # Numeric + binary states extracted, unavailable/unknown skipped
        assert values == [20.0, 22.0, 1.0, 23.5]

    def test_parse_empty_list(self):
        """Test that empty list returns empty result."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        values = extract_numeric_values([])

        assert values == []

    def test_parse_none_state_values(self):
        """Test that None state values are skipped."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("20.0"),
            {"state": None},
            MockState("22.0"),
        ]

        values = extract_numeric_values(history)

        assert values == [20.0, 22.0]

    def test_parse_dict_missing_state_key(self):
        """Test that dicts without 'state' key are skipped."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("20.0"),
            {"last_changed": "2024-01-01T00:00:00Z"},  # Missing 'state'
            {"state": "22.0"},
        ]

        values = extract_numeric_values(history)

        assert values == [20.0, 22.0]

    def test_parse_integer_values(self):
        """Test that integer values are converted to floats."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("20"),
            {"state": "21"},
            MockState("22"),
        ]

        values = extract_numeric_values(history)

        assert values == [20.0, 21.0, 22.0]
        assert all(isinstance(v, float) for v in values)

    def test_parse_binary_on_off_states(self):
        """Test that binary on/off states are converted to 1.0/0.0."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("off"),
            MockState("on"),
            {"state": "off"},
            {"state": "on"},
            MockState("on"),
        ]

        values = extract_numeric_values(history)

        assert values == [0.0, 1.0, 0.0, 1.0, 1.0]

    def test_parse_binary_open_closed_states(self):
        """Test that open/closed states are converted to 1.0/0.0."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("closed"),
            MockState("open"),
            {"state": "closed"},
        ]

        values = extract_numeric_values(history)

        assert values == [0.0, 1.0, 0.0]

    def test_parse_binary_home_states(self):
        """Test that home/not_home states are converted to 1.0/0.0."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("not_home"),
            MockState("home"),
            {"state": "home"},
        ]

        values = extract_numeric_values(history)

        assert values == [0.0, 1.0, 1.0]

    def test_parse_binary_mixed_with_numeric(self):
        """Test that mixed binary and numeric states work together."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        # This could happen if someone charts a sensor that changed type
        history = [
            MockState("23.5"),
            MockState("on"),
            {"state": "off"},
            {"state": "42.0"},
        ]

        values = extract_numeric_values(history)

        assert values == [23.5, 1.0, 0.0, 42.0]

    def test_parse_binary_case_insensitive(self):
        """Test that binary state matching is case-insensitive."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("ON"),
            MockState("Off"),
            {"state": "OPEN"},
            {"state": "Closed"},
        ]

        values = extract_numeric_values(history)

        assert values == [1.0, 0.0, 1.0, 0.0]

    def test_parse_other_binary_states(self):
        """Test other binary states like locked/unlocked, playing/paused."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("locked"),
            MockState("unlocked"),
            {"state": "playing"},
            {"state": "paused"},
            MockState("active"),
            MockState("idle"),
        ]

        values = extract_numeric_values(history)

        assert values == [0.0, 1.0, 1.0, 0.0, 1.0, 0.0]

    def test_parse_binary_with_unavailable_unknown(self):
        """Test binary states with unavailable/unknown interspersed.

        Real-world scenario: device goes offline, comes back online.
        """
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("locked"),
            MockState("unknown"),  # Device briefly unknown
            MockState("unlocked"),
            {"state": "unavailable"},  # Device went offline
            {"state": "locked"},  # Device came back
            MockState("unavailable"),
            MockState("unlocked"),
        ]

        values = extract_numeric_values(history)

        # unknown/unavailable should be skipped, only valid states kept
        assert values == [0.0, 1.0, 0.0, 1.0]

    def test_parse_all_unavailable(self):
        """Test that all unavailable/unknown returns empty list."""
        from custom_components.geekmagic.coordinator import extract_numeric_values

        history = [
            MockState("unavailable"),
            {"state": "unknown"},
            MockState("unavailable"),
        ]

        values = extract_numeric_values(history)

        assert values == []
