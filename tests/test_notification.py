"""Integration tests for the notification flow through the coordinator."""

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


@pytest.fixture
def coordinator_device():
    """Create mock GeekMagic device."""
    device = MagicMock()
    device.upload_and_display = AsyncMock()
    device.set_brightness = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=None)
    return device


@pytest.fixture
def options():
    """Create default options."""
    return {
        CONF_REFRESH_INTERVAL: 60,
        CONF_SCREENS: [
            {
                "name": "Screen 1",
                CONF_LAYOUT: LAYOUT_GRID_2X2,
                CONF_WIDGETS: [{"type": "clock", "slot": 0}],
            }
        ],
    }


class TestNotification:
    """Coordinator-level notification behaviour: delegates to NotificationManager."""

    @pytest.mark.asyncio
    async def test_trigger_notification_routes_to_manager(self, hass, coordinator_device, options):
        """trigger_notification stores data on the manager and requests a refresh."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        refresh = AsyncMock()
        object.__setattr__(coordinator, "async_request_refresh", refresh)
        # NotificationManager was bound to the original bound method; rebind it.
        coordinator._notifications._request_refresh = refresh

        data = {"message": "Hello World", "duration": 5, "icon": "mdi:test"}

        with (
            patch("time.time", return_value=1000),
            patch.object(hass.loop, "call_later") as mock_call_later,
        ):
            await coordinator.trigger_notification(data)

            assert coordinator._notifications.is_active is True
            assert coordinator._notifications.image_source is None
            refresh.assert_awaited()
            mock_call_later.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_uses_notification_layout_when_active(
        self, hass, coordinator_device, options
    ):
        """Active notification overrides the screen layout in the render loop."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        # Make a notification active without going through the asyncio timer.
        coordinator._notifications._data = {"message": "Active"}
        coordinator._notifications._expiry = 2000

        object.__setattr__(
            coordinator.renderer,
            "create_canvas",
            MagicMock(return_value=(MagicMock(), MagicMock())),
        )
        object.__setattr__(coordinator.renderer, "to_jpeg", MagicMock(return_value=b"jpeg"))
        object.__setattr__(coordinator.renderer, "to_png", MagicMock(return_value=b"png"))
        object.__setattr__(coordinator, "_build_widget_states", MagicMock(return_value={}))

        with (
            patch("time.time", return_value=1000),
            patch.object(
                coordinator._notifications,
                "build_layout",
                wraps=coordinator._notifications.build_layout,
            ) as mock_build,
        ):
            coordinator._render_display()
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_ignores_notification_when_expired(
        self, hass, coordinator_device, options
    ):
        """Expired notification yields no layout override."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        coordinator._notifications._data = {"message": "Expired"}
        coordinator._notifications._expiry = 900

        object.__setattr__(
            coordinator.renderer,
            "create_canvas",
            MagicMock(return_value=(MagicMock(), MagicMock())),
        )
        object.__setattr__(coordinator.renderer, "to_jpeg", MagicMock(return_value=b"jpeg"))
        object.__setattr__(coordinator.renderer, "to_png", MagicMock(return_value=b"png"))
        object.__setattr__(coordinator, "_build_widget_states", MagicMock(return_value={}))

        with patch("time.time", return_value=1000):
            coordinator._render_display()
            # Expired: build_layout returns None, and the screen layout is used.
            assert coordinator._notifications.build_layout() is None
