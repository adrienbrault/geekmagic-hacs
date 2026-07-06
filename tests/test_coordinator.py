"""Tests for GeekMagic coordinator multi-screen support."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.const import (
    BACKOFF_LOG_INTERVAL,
    CONF_LAYOUT,
    CONF_MANAGE_PRO_ALBUM,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    LAYOUT_GRID_2X2,
    LAYOUT_SPLIT_H,
    MAX_BACKOFF_MULTIPLIER,
    MODEL_PRO,
)
from custom_components.geekmagic.coordinator import CONF_ASSIGNED_VIEWS, GeekMagicCoordinator
from custom_components.geekmagic.device import (
    ConnectionResult,
    DeviceState,
    RenderedDashboardRequest,
)


@pytest.fixture
def coordinator_device():
    """Create mock GeekMagic device for coordinator tests."""
    device = MagicMock()
    device.display_rendered_dashboard = AsyncMock()
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
        """Test that all widget types are registered."""
        from custom_components.geekmagic.coordinator import WIDGET_CLASSES

        expected_widgets = [
            "attribute_list",
            "camera",
            "candlestick",
            "climate",
            "clock",
            "entity",
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

        assert len(WIDGET_CLASSES) == 16


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


class MockTimedState:
    """Mock State object with .state and .last_changed for testing."""

    def __init__(self, state_value: str, last_changed: datetime) -> None:
        """Initialize with a state value and its last_changed timestamp."""
        self.state = state_value
        self.last_changed = last_changed


class TestExtractTimestampedNumericValues:
    """Tests for the extract_timestamped_numeric_values helper."""

    def test_keeps_timestamps_and_values(self):
        """State objects yield (timestamp, value) pairs."""
        from custom_components.geekmagic.coordinator import (
            extract_timestamped_numeric_values,
        )

        base = datetime(2024, 1, 1, tzinfo=UTC)
        history = [
            MockTimedState("20.0", base),
            MockTimedState("21.5", base + timedelta(hours=1)),
        ]

        result = extract_timestamped_numeric_values(history)

        assert result == [
            (base.timestamp(), 20.0),
            ((base + timedelta(hours=1)).timestamp(), 21.5),
        ]

    def test_converts_binary_states(self):
        """on/off states are converted to 1.0/0.0."""
        from custom_components.geekmagic.coordinator import (
            extract_timestamped_numeric_values,
        )

        base = datetime(2024, 1, 1, tzinfo=UTC)
        history = [
            MockTimedState("off", base),
            MockTimedState("on", base + timedelta(hours=1)),
        ]

        result = extract_timestamped_numeric_values(history)

        assert [value for _, value in result] == [0.0, 1.0]

    def test_sorts_by_timestamp(self):
        """Out-of-order states are sorted by timestamp."""
        from custom_components.geekmagic.coordinator import (
            extract_timestamped_numeric_values,
        )

        base = datetime(2024, 1, 1, tzinfo=UTC)
        history = [
            MockTimedState("2.0", base + timedelta(hours=2)),
            MockTimedState("0.0", base),
            MockTimedState("1.0", base + timedelta(hours=1)),
        ]

        result = extract_timestamped_numeric_values(history)

        assert [value for _, value in result] == [0.0, 1.0, 2.0]

    def test_skips_states_without_timestamp(self):
        """States lacking last_changed are skipped."""
        from custom_components.geekmagic.coordinator import (
            extract_timestamped_numeric_values,
        )

        result = extract_timestamped_numeric_values([MockState("20.0")])

        assert result == []


class TestResampleHistory:
    """Tests for resample_history.

    Regression coverage for issue #133: the recorder stores state *changes*,
    not periodic samples, so plotting raw points at even horizontal spacing
    distorts time. resample_history puts history back on an even time axis.
    """

    def test_empty_history(self):
        """No history returns an empty list."""
        from custom_components.geekmagic.coordinator import resample_history

        base = datetime(2024, 1, 1, tzinfo=UTC)
        assert resample_history([], base, base + timedelta(hours=24)) == []

    def test_constant_value_is_flat(self):
        """A single steady value resamples to a flat line."""
        from custom_components.geekmagic.coordinator import resample_history

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=24)
        history = [MockTimedState("42.0", start)]

        result = resample_history(history, start, end, buckets=24)

        assert result == [42.0] * 24

    def test_long_flat_period_is_not_collapsed(self):
        """A value held at 0 for most of the window stays flat at 0.

        This is the core of issue #133: power sits at 0 W for hours (one
        recorded point) with a brief spike. The 0 W stretch must occupy
        most of the resampled series, not collapse to a sliver.
        """
        from custom_components.geekmagic.coordinator import resample_history

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=24)
        history = [
            MockTimedState("0", start),
            MockTimedState("3000", start + timedelta(hours=12)),
            MockTimedState("0", start + timedelta(hours=12, minutes=15)),
        ]

        result = resample_history(history, start, end, buckets=96)

        assert len(result) == 96
        # The spike lasts 15 min out of a 24 h window; the vast majority of
        # the resampled points must still read 0.
        assert result.count(0.0) >= 94
        # The spike is preserved somewhere in the series.
        assert max(result) > 0

    def test_time_weighted_average_within_bucket(self):
        """A change mid-bucket yields a time-weighted average."""
        from custom_components.geekmagic.coordinator import resample_history

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=1)
        # Value 0 for the first 45 min, then 100 for the last 15 min.
        history = [
            MockTimedState("0", start),
            MockTimedState("100", start + timedelta(minutes=45)),
        ]

        result = resample_history(history, start, end, buckets=1)

        assert result == [pytest.approx(25.0)]

    def test_binary_history_thresholded(self):
        """Binary history resamples to 0.0/1.0 values only."""
        from custom_components.geekmagic.coordinator import resample_history

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=24)
        history = [
            MockTimedState("off", start),
            MockTimedState("on", start + timedelta(hours=12)),
        ]

        result = resample_history(history, start, end, buckets=96)

        assert set(result) <= {0.0, 1.0}
        assert result.count(0.0) == 48
        assert result.count(1.0) == 48

    def test_leading_gap_is_dropped(self):
        """Buckets before the first data point are dropped."""
        from custom_components.geekmagic.coordinator import resample_history

        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = start + timedelta(hours=24)
        # First (and only) data point arrives 6 h into the window.
        history = [MockTimedState("50", start + timedelta(hours=6))]

        result = resample_history(history, start, end, buckets=96)

        # 24 of 96 buckets precede the data point and are dropped.
        assert result == [50.0] * 72


class TestCoordinatorBackoff:
    """Test exponential backoff for offline device handling.

    Issue #36: Excessive logging when device goes offline.
    These tests verify the backoff mechanism reduces retry frequency
    and log spam when a device is unreachable.
    """

    @pytest.fixture
    def backoff_device(self):
        """Create mock device with test_connection support."""
        device = MagicMock()
        device.host = "192.168.1.100"
        device.model = "unknown"
        device.display_rendered_dashboard = AsyncMock()
        device.set_brightness = AsyncMock()
        device.get_brightness = AsyncMock(return_value=50)
        device.get_state = AsyncMock(return_value=None)
        device.get_space = AsyncMock(return_value=None)
        device.test_connection = AsyncMock(
            return_value=ConnectionResult(success=True, error="none", message="OK")
        )
        device.is_builtin_theme = MagicMock(return_value=False)
        device.set_theme_custom = AsyncMock()
        return device

    @pytest.fixture
    def simple_options(self):
        """Create simple single-screen options."""
        return {
            CONF_REFRESH_INTERVAL: 10,
            CONF_SCREENS: [
                {
                    "name": "Test",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                }
            ],
        }

    def test_initial_state_no_backoff(self, hass, backoff_device, simple_options):
        """Test that coordinator starts with no backoff state."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        assert coordinator._consecutive_failures == 0
        assert coordinator._device_offline is False
        assert coordinator._base_update_interval == 10
        assert coordinator.update_interval == timedelta(seconds=10)

    def test_apply_backoff_exponential(self, hass, backoff_device, simple_options):
        """Test that backoff increases exponentially."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Simulate failures and check backoff progression
        # Failure 1: multiplier = 2^1 = 2
        coordinator._consecutive_failures = 1
        coordinator._apply_backoff()
        assert coordinator.update_interval == timedelta(seconds=20)

        # Failure 2: multiplier = 2^2 = 4
        coordinator._consecutive_failures = 2
        coordinator._apply_backoff()
        assert coordinator.update_interval == timedelta(seconds=40)

        # Failure 3: multiplier = 2^3 = 8
        coordinator._consecutive_failures = 3
        coordinator._apply_backoff()
        assert coordinator.update_interval == timedelta(seconds=80)

        # Failure 4: multiplier = 2^4 = 16
        coordinator._consecutive_failures = 4
        coordinator._apply_backoff()
        assert coordinator.update_interval == timedelta(seconds=160)

    def test_apply_backoff_capped_at_max(self, hass, backoff_device, simple_options):
        """Test that backoff is capped at MAX_BACKOFF_MULTIPLIER."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Simulate many failures - should be capped at max
        coordinator._consecutive_failures = 100
        coordinator._apply_backoff()

        expected_interval = DEFAULT_REFRESH_INTERVAL * MAX_BACKOFF_MULTIPLIER
        assert coordinator.update_interval == timedelta(seconds=expected_interval)

    def test_reset_backoff(self, hass, backoff_device, simple_options):
        """Test that reset_backoff restores normal state."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Set up backoff state
        coordinator._consecutive_failures = 5
        coordinator._device_offline = True
        coordinator._apply_backoff()
        assert coordinator.update_interval != timedelta(seconds=10)

        # Reset backoff
        coordinator._reset_backoff()

        assert coordinator._consecutive_failures == 0
        assert coordinator._device_offline is False
        assert coordinator.update_interval == timedelta(seconds=10)

    @patch("custom_components.geekmagic.coordinator._LOGGER")
    def test_log_offline_status_first_failure(
        self, mock_logger, hass, backoff_device, simple_options
    ):
        """Test that first failure logs at warning level."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        coordinator._consecutive_failures = 1
        coordinator._log_offline_status("Connection refused")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "is offline" in call_args
        assert "exponential backoff" in call_args

    @patch("custom_components.geekmagic.coordinator._LOGGER")
    def test_log_offline_status_subsequent_debug(
        self, mock_logger, hass, backoff_device, simple_options
    ):
        """Test that subsequent failures log at debug level."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Reset mock to ignore constructor calls
        mock_logger.reset_mock()

        coordinator._consecutive_failures = 2
        coordinator._log_offline_status("Connection refused")

        # Check the specific debug call was made
        mock_logger.debug.assert_called_with(
            "GeekMagic device %s offline (attempt %d): %s",
            "192.168.1.100",
            2,
            "Connection refused",
        )
        mock_logger.warning.assert_not_called()

    @patch("custom_components.geekmagic.coordinator._LOGGER")
    def test_log_offline_status_periodic_summary(
        self, mock_logger, hass, backoff_device, simple_options
    ):
        """Test that periodic summary logs at warning level."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)
        coordinator.update_interval = timedelta(seconds=180)

        # At BACKOFF_LOG_INTERVAL failures, should log summary
        coordinator._consecutive_failures = BACKOFF_LOG_INTERVAL
        coordinator._log_offline_status("Connection refused")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "still offline" in call_args
        assert "attempts" in call_args

    @patch("custom_components.geekmagic.coordinator._LOGGER")
    def test_log_connection_error_first_failure(
        self, mock_logger, hass, backoff_device, simple_options
    ):
        """Test that first connection error logs at warning level."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        coordinator._consecutive_failures = 1
        coordinator._log_connection_error(Exception("Connection refused"))

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "connection failed" in call_args

    @patch("custom_components.geekmagic.coordinator._LOGGER")
    def test_log_connection_error_subsequent_debug(
        self, mock_logger, hass, backoff_device, simple_options
    ):
        """Test that subsequent errors log at debug level."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Reset mock to ignore constructor calls
        mock_logger.reset_mock()

        coordinator._consecutive_failures = 5
        test_exception = Exception("Connection refused")
        coordinator._log_connection_error(test_exception)

        # Check the specific debug call was made
        mock_logger.debug.assert_called_with(
            "GeekMagic update failed (attempt %d): %s",
            5,
            test_exception,
        )
        mock_logger.warning.assert_not_called()

    def test_update_options_preserves_base_interval(self, hass, backoff_device, simple_options):
        """Test that update_options updates base interval for backoff."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)
        assert coordinator._base_update_interval == 10

        # Update with new interval
        new_options = simple_options.copy()
        new_options[CONF_REFRESH_INTERVAL] = 30
        coordinator.update_options(new_options)

        assert coordinator._base_update_interval == 30
        assert coordinator.update_interval == timedelta(seconds=30)

    @pytest.mark.asyncio
    async def test_device_offline_skips_rendering(self, hass, backoff_device, simple_options):
        """Test that offline device skips expensive rendering.

        When device is marked offline, coordinator should only do
        a lightweight connectivity check instead of full render cycle.
        """
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Mark device as offline
        coordinator._device_offline = True
        coordinator._consecutive_failures = 5

        # Set up failed connection test
        backoff_device.test_connection = AsyncMock(
            return_value=ConnectionResult(
                success=False, error="connection_refused", message="Connection refused"
            )
        )

        # Update should fail without rendering
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Device offline" in str(exc_info.value)

        # Verify expensive operations were NOT called
        backoff_device.display_rendered_dashboard.assert_not_called()

        # Verify connectivity check WAS called
        backoff_device.test_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_device_comes_back_online(self, hass, backoff_device, simple_options):
        """Test that device recovery resets backoff and resumes updates."""
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Mark device as offline with significant backoff
        coordinator._device_offline = True
        coordinator._consecutive_failures = 10
        coordinator._apply_backoff()

        # Set up successful connection test
        backoff_device.test_connection = AsyncMock(
            return_value=ConnectionResult(success=True, error="none", message="OK")
        )

        # Mock the rendering to succeed
        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            result = await coordinator._async_update_data()

        # Verify backoff was reset
        assert coordinator._consecutive_failures == 0
        assert coordinator._device_offline is False
        assert coordinator.update_interval == timedelta(seconds=10)

        # Verify update succeeded
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_managed_pro_album_option_passed_to_device(
        self, hass, backoff_device, simple_options
    ):
        """Test coordinator asks the device to keep only the managed Pro image."""
        backoff_device.model = MODEL_PRO
        coordinator = GeekMagicCoordinator(
            hass,
            backoff_device,
            {**simple_options, CONF_MANAGE_PRO_ALBUM: True},
        )

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            result = await coordinator._async_update_data()

        assert result["success"] is True
        backoff_device.display_rendered_dashboard.assert_awaited_once()
        request = backoff_device.display_rendered_dashboard.await_args.args[0]
        assert request == RenderedDashboardRequest(
            image_data=b"jpeg",
            filename="dashboard.jpg",
            allow_destructive_album_management=True,
            try_menu_navigation=False,
        )

    @pytest.mark.asyncio
    async def test_startup_builtin_state_skips_render_without_custom_request(
        self, hass, backoff_device, simple_options
    ):
        """Test startup still respects a device already showing a built-in theme."""
        backoff_device.get_state = AsyncMock(
            return_value=DeviceState(theme=1, brightness=50, current_image=None)
        )
        backoff_device.is_builtin_theme = MagicMock(return_value=True)
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            result = await coordinator._async_update_data()

        assert result["builtin_mode"] is True
        assert coordinator.display_mode == "builtin"
        backoff_device.display_rendered_dashboard.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_custom_selection_renders_even_when_device_reports_builtin_theme(
        self, hass, backoff_device, simple_options
    ):
        """Test selected HA views are not blocked by the device's current theme."""
        backoff_device.get_state = AsyncMock(
            return_value=DeviceState(theme=1, brightness=50, current_image=None)
        )
        backoff_device.is_builtin_theme = MagicMock(return_value=True)
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)
        coordinator.set_display_mode("custom", 0)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            result = await coordinator._async_update_data()

        assert result["success"] is True
        assert coordinator.display_mode == "custom"
        backoff_device.display_rendered_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assigned_views_switch_from_builtin_to_custom_rendering(
        self, hass, backoff_device, simple_options
    ):
        """Test panel view checkboxes make HA rendering authoritative."""
        backoff_device.get_state = AsyncMock(
            return_value=DeviceState(theme=1, brightness=50, current_image=None)
        )
        backoff_device.is_builtin_theme = MagicMock(return_value=True)
        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)
        coordinator.set_display_mode("builtin", 1)

        coordinator.update_options(
            {
                **simple_options,
                CONF_ASSIGNED_VIEWS: ["view_1"],
            }
        )

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            result = await coordinator._async_update_data()

        assert result["success"] is True
        assert coordinator.display_mode == "custom"
        backoff_device.display_rendered_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pro_picture_entry_is_not_automated(self, hass, backoff_device, simple_options):
        """Test Pro button navigation is never attempted by HA refreshes."""
        backoff_device.model = MODEL_PRO
        coordinator = GeekMagicCoordinator(
            hass,
            backoff_device,
            {**simple_options, CONF_MANAGE_PRO_ALBUM: True},
        )

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            await coordinator._async_update_data()

        requests = [
            call.args[0] for call in backoff_device.display_rendered_dashboard.await_args_list
        ]
        assert requests[0].try_menu_navigation is False
        assert requests[1].try_menu_navigation is False

    @pytest.mark.asyncio
    async def test_first_failure_marks_offline(self, hass, backoff_device, simple_options):
        """Test that first update failure marks device offline and applies backoff."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Mock upload to fail
        backoff_device.display_rendered_dashboard = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        # Mock the rendering to succeed but upload fails
        with (
            patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")),
            pytest.raises(UpdateFailed),
        ):
            await coordinator._async_update_data()

        # Verify offline state was set
        assert coordinator._device_offline is True
        assert coordinator._consecutive_failures == 1
        assert coordinator._last_update_success is False

        # Verify backoff was applied
        assert coordinator.update_interval == timedelta(seconds=20)  # 10 * 2^1

    @pytest.mark.asyncio
    async def test_test_connection_exception_handled(self, hass, backoff_device, simple_options):
        """Test that exceptions from test_connection() are handled gracefully.

        When test_connection() itself raises an exception (e.g., network timeout),
        it should be treated as device still offline with backoff applied.
        """
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = GeekMagicCoordinator(hass, backoff_device, simple_options)

        # Mark device as offline
        coordinator._device_offline = True
        coordinator._consecutive_failures = 3

        # Set up test_connection to raise an exception
        backoff_device.test_connection = AsyncMock(side_effect=Exception("Network timeout"))

        # Update should fail and apply backoff
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Network timeout" in str(exc_info.value)

        # Verify backoff was applied
        assert coordinator._consecutive_failures == 4
        assert coordinator._device_offline is True

        # Verify expensive operations were NOT called
        backoff_device.display_rendered_dashboard.assert_not_called()


class TestCoordinatorPause:
    """Tests for the sleep/wake (pause) feature.

    Verifies that setting _paused=True causes _async_update_data to skip
    all rendering and uploading, and that async_set_active properly
    manages the paused state and brightness.
    """

    @pytest.fixture
    def pause_device(self):
        """Create mock device for pause tests."""
        device = MagicMock()
        device.host = "192.168.1.100"
        device.model = "unknown"
        device.display_rendered_dashboard = AsyncMock()
        device.set_brightness = AsyncMock()
        device.get_brightness = AsyncMock(return_value=75)
        device.get_state = AsyncMock(return_value=None)
        device.get_space = AsyncMock(return_value=None)
        return device

    @pytest.fixture
    def simple_options(self):
        """Create simple single-screen options."""
        return {
            CONF_REFRESH_INTERVAL: 10,
            CONF_SCREENS: [
                {
                    "name": "Test",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                }
            ],
        }

    def test_initial_paused_state_is_false(self, hass, pause_device, simple_options):
        """Test that coordinator starts unpaused."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)

        assert coordinator._paused is False
        assert coordinator._pre_pause_brightness is None

    @pytest.mark.asyncio
    async def test_update_skips_render_when_paused(self, hass, pause_device, simple_options):
        """Test that _async_update_data returns early without rendering when paused."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._paused = True

        result = await coordinator._async_update_data()

        assert result == {"success": True, "paused": True}
        pause_device.display_rendered_dashboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_active_false_dims_screen_and_pauses(
        self, hass, pause_device, simple_options
    ):
        """Test async_set_active(False) saves brightness, dims to 0, sets paused."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._device_brightness = 75

        await coordinator.async_set_active(False)

        assert coordinator._paused is True
        assert coordinator._pre_pause_brightness == 75
        assert coordinator._device_brightness == 0
        pause_device.set_brightness.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_set_active_true_restores_brightness_and_refreshes(
        self, hass, pause_device, simple_options
    ):
        """Test async_set_active(True) restores brightness and triggers refresh."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._paused = True
        coordinator._pre_pause_brightness = 75
        coordinator._device_brightness = 0

        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            await coordinator.async_set_active(True)

        assert coordinator._paused is False
        assert coordinator._pre_pause_brightness is None
        assert coordinator._device_brightness == 75
        pause_device.set_brightness.assert_called_once_with(75)
        mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_active_false_handles_no_brightness(self, hass, pause_device, simple_options):
        """Test async_set_active(False) works when brightness was never polled."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._device_brightness = None  # never polled

        await coordinator.async_set_active(False)

        assert coordinator._paused is True
        assert coordinator._pre_pause_brightness is None
        pause_device.set_brightness.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_set_active_true_skips_brightness_when_none_stored(
        self, hass, pause_device, simple_options
    ):
        """Test async_set_active(True) does not call set_brightness if none was stored."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._paused = True
        coordinator._pre_pause_brightness = None

        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            await coordinator.async_set_active(True)

        assert coordinator._paused is False
        pause_device.set_brightness.assert_not_called()
        mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_active_false_twice_preserves_pre_pause_brightness(
        self, hass, pause_device, simple_options
    ):
        """Test that calling sleep twice does not overwrite the stored brightness."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._device_brightness = 80

        await coordinator.async_set_active(False)
        assert coordinator._pre_pause_brightness == 80

        # Second call while already paused should not overwrite the stored value
        await coordinator.async_set_active(False)
        assert coordinator._pre_pause_brightness == 80

    @pytest.mark.asyncio
    async def test_set_active_false_notifies_listeners(self, hass, pause_device, simple_options):
        """Test that sleeping calls async_update_listeners for an immediate UI state update."""
        coordinator = GeekMagicCoordinator(hass, pause_device, simple_options)
        coordinator._device_brightness = 60

        with patch.object(coordinator, "async_update_listeners") as mock_notify:
            await coordinator.async_set_active(False)

        mock_notify.assert_called_once()


class TestPreviewUpdates:
    """Tests for the preview image update behavior (issue #81).

    The preview must refresh on every successful render cycle, not only
    after config changes — otherwise the Display Preview image entity
    shows a stale frame between configuration edits.
    """

    @pytest.fixture
    def preview_device(self):
        """Create mock device for preview tests."""
        device = MagicMock()
        device.host = "192.168.1.100"
        device.model = "unknown"
        device.display_rendered_dashboard = AsyncMock()
        device.set_brightness = AsyncMock()
        device.get_brightness = AsyncMock(return_value=50)
        device.get_state = AsyncMock(return_value=None)
        device.get_space = AsyncMock(return_value=None)
        device.is_builtin_theme = MagicMock(return_value=False)
        device.set_theme_custom = AsyncMock()
        return device

    @pytest.fixture
    def simple_options(self):
        """Create simple single-screen options."""
        return {
            CONF_REFRESH_INTERVAL: 10,
            CONF_SCREENS: [
                {
                    "name": "Test",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_preview_updates_on_every_render_cycle(
        self, hass, preview_device, simple_options
    ):
        """Periodic refreshes (no config change) update the preview each time."""
        coordinator = GeekMagicCoordinator(hass, preview_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            await coordinator._async_update_data()
        assert coordinator.preview_just_updated is True
        assert coordinator.last_image == b"png1"

        # Second cycle with NO config change — preview must still refresh
        with patch.object(coordinator, "_render_display", return_value=(b"jpeg2", b"png2")):
            await coordinator._async_update_data()
        assert coordinator.preview_just_updated is True
        assert coordinator.last_image == b"png2"

    @pytest.mark.asyncio
    async def test_pause_does_not_signal_preview_update(self, hass, preview_device, simple_options):
        """Pausing notifies listeners out-of-cycle; the leftover flag from the
        last render must not make the preview entity re-signal an unchanged
        image."""
        coordinator = GeekMagicCoordinator(hass, preview_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
        assert coordinator.preview_just_updated is True

        await coordinator.async_set_active(False)
        assert coordinator.preview_just_updated is False

    @pytest.mark.asyncio
    async def test_builtin_mode_does_not_signal_preview_update(
        self, hass, preview_device, simple_options
    ):
        """Cycles that render nothing (builtin mode) reset the preview flag."""
        coordinator = GeekMagicCoordinator(hass, preview_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            await coordinator._async_update_data()
        assert coordinator.preview_just_updated is True

        coordinator.set_display_mode("builtin", 1)
        result = await coordinator._async_update_data()

        assert result["builtin_mode"] is True
        assert coordinator.preview_just_updated is False
        # Last rendered image is kept for the entity's image content
        assert coordinator.last_image == b"png1"

    @pytest.mark.asyncio
    async def test_paused_cycle_does_not_signal_preview_update(
        self, hass, preview_device, simple_options
    ):
        """Paused cycles reset the preview flag."""
        coordinator = GeekMagicCoordinator(hass, preview_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            await coordinator._async_update_data()
        assert coordinator.preview_just_updated is True

        coordinator._paused = True
        result = await coordinator._async_update_data()

        assert result == {"success": True, "paused": True}
        assert coordinator.preview_just_updated is False

    @pytest.mark.asyncio
    async def test_failed_upload_still_updates_preview_to_latest_render(
        self, hass, preview_device, simple_options
    ):
        """The preview reflects the latest render even if the upload fails.

        Rendering succeeded before the upload was attempted, so the preview
        entity legitimately shows the freshly rendered frame.
        """
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = GeekMagicCoordinator(hass, preview_device, simple_options)

        preview_device.display_rendered_dashboard = AsyncMock(side_effect=Exception("boom"))
        with (
            patch.object(coordinator, "_render_display", return_value=(b"jpeg2", b"png2")),
            pytest.raises(UpdateFailed),
        ):
            await coordinator._async_update_data()

        assert coordinator.preview_just_updated is True
        assert coordinator.last_image == b"png2"


class TestUploadSkip:
    """Tests for skipping the device upload when the frame is unchanged (#96).

    Uploading identical frames every cycle wears the device flash. The
    coordinator skips device.display_rendered_dashboard() when the new JPEG
    is byte-identical to the last successful upload AND the freshly polled
    device state confirms our dashboard image is still displayed in the
    custom theme. Any uncertainty (failed poll, mismatching device state,
    config change, forced refresh, failure recovery) forces an upload.
    """

    DEVICE_STATE_DASHBOARD = DeviceState(
        theme=3, brightness=50, current_image="/image/dashboard.jpg"
    )

    @pytest.fixture
    def skip_device(self):
        """Create mock device reporting our dashboard image in custom theme."""
        device = MagicMock()
        device.host = "192.168.1.100"
        device.model = "unknown"
        device.display_rendered_dashboard = AsyncMock()
        device.set_brightness = AsyncMock()
        device.get_brightness = AsyncMock(return_value=50)
        device.get_state = AsyncMock(return_value=self.DEVICE_STATE_DASHBOARD)
        device.get_space = AsyncMock(return_value=None)
        device.is_builtin_theme = MagicMock(return_value=False)
        device.is_custom_theme = MagicMock(return_value=True)
        device.set_theme_custom = AsyncMock()
        return device

    @pytest.fixture
    def simple_options(self):
        """Create simple single-screen options."""
        return {
            CONF_REFRESH_INTERVAL: 10,
            CONF_SCREENS: [
                {
                    "name": "Test",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [{"type": "clock", "slot": 0}],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_unchanged_frame_skips_upload(self, hass, skip_device, simple_options):
        """An identical frame with confirmed device state skips the upload."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            first = await coordinator._async_update_data()
            second = await coordinator._async_update_data()

        assert first["skipped_upload"] is False
        assert second["skipped_upload"] is True
        assert second["success"] is True
        assert skip_device.display_rendered_dashboard.await_count == 1

    @pytest.mark.asyncio
    async def test_changed_frame_uploads(self, hass, skip_device, simple_options):
        """A frame with different bytes always uploads."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            await coordinator._async_update_data()
        with patch.object(coordinator, "_render_display", return_value=(b"jpeg2", b"png2")):
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_forced_refresh_uploads_unchanged_frame(self, hass, skip_device, simple_options):
        """async_refresh_display invalidates the cache so the next cycle uploads."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            assert (await coordinator._async_update_data())["skipped_upload"] is True

            with patch.object(coordinator, "async_request_refresh", AsyncMock()):
                await coordinator.async_refresh_display()
            assert coordinator._last_uploaded_jpeg is None

            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_update_options_invalidates_upload_cache(self, hass, skip_device, simple_options):
        """A config change forces the next cycle to upload."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            coordinator.update_options(simple_options)
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_device_showing_other_image_uploads(self, hass, skip_device, simple_options):
        """If the device shows another image, an identical frame still uploads."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            # User switched the device to a different image
            skip_device.get_state = AsyncMock(
                return_value=DeviceState(theme=3, brightness=50, current_image="/image/other.gif")
            )
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_device_in_builtin_theme_uploads(self, hass, skip_device, simple_options):
        """If the device left the custom theme, an identical frame still uploads."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)
        coordinator.set_display_mode("custom", 0)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            skip_device.is_custom_theme = MagicMock(return_value=False)
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_failed_state_poll_uploads(self, hass, skip_device, simple_options):
        """A failed device-state poll (stale state) never suppresses an upload."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            # Poll fails; self._device_state stays stale from the first cycle
            skip_device.get_state = AsyncMock(side_effect=Exception("timeout"))
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_synthesized_pro_state_never_skips(self, hass, skip_device, simple_options):
        """Pro firmware without app.json echoes our own commands (is_live=False).

        That echo always claims dashboard.jpg is displayed, so trusting it
        would skip forever and never recover from out-of-band device changes.
        """
        skip_device.get_state = AsyncMock(
            return_value=DeviceState(
                theme=3,
                brightness=None,
                current_image="/image/dashboard.jpg",
                is_live=False,
            )
        )
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_sdpro_without_current_image_never_skips(self, hass, skip_device, simple_options):
        """Devices reporting current_image=None (SD_PRO) upload every cycle."""
        skip_device.get_state = AsyncMock(
            return_value=DeviceState(theme=3, brightness=50, current_image=None)
        )
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_offline_recovery_uploads(self, hass, skip_device, simple_options):
        """The first cycle after a failed cycle always uploads (cache cleared)."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            await coordinator._async_update_data()

        # Upload of a changed frame fails — cycle fails and the cache is cleared
        skip_device.display_rendered_dashboard = AsyncMock(side_effect=Exception("boom"))
        with (
            patch.object(coordinator, "_render_display", return_value=(b"jpeg2", b"png2")),
            pytest.raises(UpdateFailed),
        ):
            await coordinator._async_update_data()
        assert coordinator._last_uploaded_jpeg is None

        # Recovery: a frame identical to the first upload must upload again
        skip_device.display_rendered_dashboard = AsyncMock()
        skip_device.test_connection = AsyncMock(
            return_value=ConnectionResult(success=True, error="none", message="OK")
        )
        with patch.object(coordinator, "_render_display", return_value=(b"jpeg1", b"png1")):
            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        skip_device.display_rendered_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resume_from_pause_uploads(self, hass, skip_device, simple_options):
        """Waking from pause invalidates the cache so the next cycle uploads."""
        coordinator = GeekMagicCoordinator(hass, skip_device, simple_options)

        with patch.object(coordinator, "_render_display", return_value=(b"jpeg", b"png")):
            await coordinator._async_update_data()
            assert (await coordinator._async_update_data())["skipped_upload"] is True

            with patch.object(coordinator, "async_request_refresh", AsyncMock()):
                await coordinator.async_set_active(False)
                await coordinator.async_set_active(True)

            result = await coordinator._async_update_data()

        assert result["skipped_upload"] is False
        assert skip_device.display_rendered_dashboard.await_count == 2
