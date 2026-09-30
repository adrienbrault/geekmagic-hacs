"""Tests for the coordinator's per-cycle device-work reductions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    FORCED_REPUSH_INTERVAL,
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


async def _cycle(coordinator, payload=b"jpeg", filename="dashboard.jpg"):
    """Run one update cycle with a stubbed render."""
    with patch.object(coordinator, "_render_display", return_value=(payload, b"png", filename)):
        return await coordinator._async_update_data()


class TestUploadDedup:
    """An unchanged frame is not re-uploaded while the device still shows it."""

    @pytest.mark.asyncio
    async def test_unchanged_frame_is_not_reuploaded(self, hass, device, options):
        coordinator = GeekMagicCoordinator(hass, device, options)

        await _cycle(coordinator)
        result = await _cycle(coordinator)

        assert result["success"] is True
        assert coordinator.last_update_success is True
        device.display_rendered_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_changed_frame_is_uploaded(self, hass, device, options):
        coordinator = GeekMagicCoordinator(hass, device, options)

        await _cycle(coordinator, b"frame-1")
        await _cycle(coordinator, b"frame-2")

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_state_showing_another_theme_forces_push(self, hass, device, options):
        """The device left our custom theme (manual change, reboot): re-push."""
        device.get_state = AsyncMock(
            return_value=DeviceState(theme=1, brightness=50, current_image=None)
        )
        device.is_custom_theme = MagicMock(return_value=False)
        coordinator = GeekMagicCoordinator(hass, device, options)
        coordinator.set_display_mode("custom", 0)

        await _cycle(coordinator)
        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_state_showing_another_image_forces_push(self, hass, device, options):
        device.get_state = AsyncMock(
            return_value=DeviceState(theme=3, brightness=50, current_image="/image/other.jpg")
        )
        coordinator = GeekMagicCoordinator(hass, device, options)

        await _cycle(coordinator)
        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_state_showing_our_image_allows_skip(self, hass, device, options):
        device.get_state = AsyncMock(
            return_value=DeviceState(theme=3, brightness=50, current_image="/image/dashboard.jpg")
        )
        coordinator = GeekMagicCoordinator(hass, device, options)

        await _cycle(coordinator)
        await _cycle(coordinator)

        device.display_rendered_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_forced_repush_after_interval(self, hass, device, options):
        coordinator = GeekMagicCoordinator(hass, device, options)
        await _cycle(coordinator)
        assert coordinator._last_push is not None
        digest, filename, pushed_at = coordinator._last_push
        coordinator._last_push = (digest, filename, pushed_at - FORCED_REPUSH_INTERVAL)

        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    async def test_failed_upload_forces_next_push(self, hass, device, options):
        coordinator = GeekMagicCoordinator(hass, device, options)
        await _cycle(coordinator)
        device.display_rendered_dashboard.side_effect = Exception("reset")
        with pytest.raises(UpdateFailed):
            await _cycle(coordinator, b"frame-2")
        assert coordinator._last_push is None

        # Back online: the first frame goes out again even though it was the
        # last one the device accepted — the failed cycle may have left
        # anything on screen.
        device.display_rendered_dashboard.side_effect = None
        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 3

    @pytest.mark.asyncio
    async def test_failed_cycle_forces_push_on_reconnect(self, hass, device, options):
        """Any failed cycle (offline, render error) forces the next push."""
        coordinator = GeekMagicCoordinator(hass, device, options)
        await _cycle(coordinator)
        coordinator.last_update_success = False

        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalidate",
        [
            pytest.param(lambda c: c.async_refresh_display(), id="manual_refresh"),
            pytest.param(lambda c: c.async_set_active(True), id="resume"),
            pytest.param(lambda c: c.async_reload_views(), id="reload_views"),
            pytest.param(lambda c: c.trigger_notification({"message": "hi"}), id="notification"),
        ],
    )
    async def test_async_invalidation_forces_push(self, hass, device, options, invalidate):
        coordinator = GeekMagicCoordinator(hass, device, options)
        await _cycle(coordinator)

        with patch.object(coordinator, "async_request_refresh", AsyncMock()):
            await invalidate(coordinator)
        if coordinator._notification_clear_handle is not None:
            coordinator._notification_clear_handle.cancel()
        # Same bytes as before: only the invalidation can cause the upload.
        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalidate",
        [
            pytest.param(lambda c, o: c.update_options(o), id="options"),
            pytest.param(lambda c, o: c.set_display_mode("custom", 0), id="display_mode"),
            pytest.param(lambda c, o: c._clear_notification(), id="notification_end"),
        ],
    )
    async def test_sync_invalidation_forces_push(self, hass, device, options, invalidate):
        coordinator = GeekMagicCoordinator(hass, device, options)
        await _cycle(coordinator)

        with patch.object(coordinator, "async_request_refresh", MagicMock()):
            invalidate(coordinator, options)
        await _cycle(coordinator)

        assert device.display_rendered_dashboard.await_count == 2
