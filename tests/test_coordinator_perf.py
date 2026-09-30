"""Tests for the coordinator's per-cycle device-work reductions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.device import ConnectionResult, DeviceState, SpaceInfo

RENDERED = (b"jpeg", b"png", "dashboard.jpg")


@pytest.fixture
def device():
    """Mock device whose every call succeeds."""
    device = MagicMock()
    device.host = "192.168.1.100"
    device.model = "unknown"
    device.display_rendered_dashboard = AsyncMock()
    device.set_brightness = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=SpaceInfo(total=1000, free=400))
    device.test_connection = AsyncMock(
        return_value=ConnectionResult(success=True, error="none", message="OK")
    )
    device.is_builtin_theme = MagicMock(return_value=False)
    device.is_custom_theme = MagicMock(return_value=True)
    device.set_theme_custom = AsyncMock()
    return device


@pytest.fixture
def options():
    """Single clock screen."""
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


class TestStoragePollCadence:
    """get_space only feeds a sensor: poll it on the slow cadence."""

    @pytest.mark.asyncio
    async def test_space_polled_on_first_cycle_then_rarely(self, hass, device, options):
        coordinator = GeekMagicCoordinator(hass, device, options)
        clock = [1000.0]
        with (
            patch.object(coordinator, "_render_display", return_value=RENDERED),
            patch("custom_components.geekmagic.coordinator.time.time", lambda: clock[0]),
        ):
            await coordinator._async_update_data()
            clock[0] += 10
            await coordinator._async_update_data()
            clock[0] += 10
            await coordinator._async_update_data()

            assert device.get_space.await_count == 1
            assert device.get_state.await_count == 3
            assert coordinator.space_info == SpaceInfo(total=1000, free=400)

            clock[0] += coordinator._brightness_poll_interval
            await coordinator._async_update_data()

        assert device.get_space.await_count == 2

    @pytest.mark.asyncio
    async def test_failed_space_poll_retries_next_cycle(self, hass, device, options):
        device.get_space = AsyncMock(
            side_effect=[Exception("boom"), SpaceInfo(total=1000, free=400)]
        )
        coordinator = GeekMagicCoordinator(hass, device, options)
        with patch.object(coordinator, "_render_display", return_value=RENDERED):
            await coordinator._async_update_data()
            assert coordinator.space_info is None
            await coordinator._async_update_data()

        assert device.get_space.await_count == 2
        assert coordinator.space_info == SpaceInfo(total=1000, free=400)

    @pytest.mark.asyncio
    async def test_state_failure_does_not_skip_space_poll(self, hass, device, options):
        device.get_state = AsyncMock(side_effect=Exception("no state path"))
        coordinator = GeekMagicCoordinator(hass, device, options)
        with patch.object(coordinator, "_render_display", return_value=RENDERED):
            result = await coordinator._async_update_data()

        assert result["success"] is True
        device.get_space.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_poll_returns_only_this_cycles_state(self, hass, device, options):
        """A failed read returns None rather than the previous cycle's state."""
        fresh = DeviceState(theme=3, brightness=50, current_image=None)
        device.get_state = AsyncMock(side_effect=[fresh, Exception("timeout")])
        coordinator = GeekMagicCoordinator(hass, device, options)

        assert await coordinator._async_poll_device(0.0) == fresh
        assert await coordinator._async_poll_device(1.0) is None
        # The sensors keep the last good reading.
        assert coordinator.device_state == fresh
