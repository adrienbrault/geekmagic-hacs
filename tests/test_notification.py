"""Tests for GeekMagic notification service."""

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
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.hero_simple import HeroSimpleLayout


@pytest.fixture
def coordinator_device():
    """Create mock GeekMagic device."""
    device = MagicMock()
    device.display_rendered_dashboard = AsyncMock()
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
    """Test notification functionality."""

    @pytest.mark.asyncio
    async def test_trigger_notification(self, hass, coordinator_device, options):
        """Test triggering a notification sets state."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        refresh = AsyncMock()
        object.__setattr__(coordinator, "async_request_refresh", refresh)

        data = {"message": "Hello World", "title": "Alert", "duration": 5, "icon": "mdi:test"}

        with (
            patch("time.time", return_value=1000),
            patch.object(hass.loop, "call_later") as mock_call_later,
        ):
            await coordinator.trigger_notification(data)

            assert coordinator._notification_data == data
            assert coordinator._notification_expiry == 1005
            assert refresh.called
            mock_call_later.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_layout_creation(self, hass, coordinator_device, options):
        """Test notification layout is created correctly (HeroSimpleLayout)."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        data = {
            "message": "Test Message",
            # title is removed from expected logic
            "icon": "mdi:check",
            "image": "camera.test",
        }

        layout = coordinator._create_notification_layout(data)

        assert isinstance(layout, HeroSimpleLayout)
        # Slot 0 should be CameraWidget because image starts with camera.
        camera_slot = layout.get_slot(0)
        assert camera_slot is not None
        assert camera_slot.widget is not None
        assert camera_slot.widget.config.widget_type == "camera"

        # Slot 1 should be TextWidget with message only
        text_slot = layout.get_slot(1)
        assert text_slot is not None
        assert text_slot.widget is not None
        text_widget = text_slot.widget
        assert text_widget.config.widget_type == "text"
        assert text_widget.config.options["text"] == "Test Message"
        assert text_widget.config.options["align"] == "center"

    @pytest.mark.asyncio
    async def test_notification_layout_image_only(self, hass, coordinator_device, options):
        """Test notification layout with no message (FullscreenLayout)."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        data = {
            # No message provided
            "image": "camera.test"
        }

        layout = coordinator._create_notification_layout(data)
        assert isinstance(layout, FullscreenLayout)

        # Slot 0 should be full screen camera
        camera_slot = layout.get_slot(0)
        assert camera_slot is not None
        assert camera_slot.widget is not None
        camera_widget = camera_slot.widget
        assert camera_widget.config.widget_type == "camera"
        assert camera_widget.config.options["fit"] == "contain"

    @pytest.mark.asyncio
    async def test_notification_layout_image_entity(self, hass, coordinator_device, options):
        """Test notification layout with an image entity."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        data = {"message": "Image Entity", "image": "image.reolink_snap"}

        layout = coordinator._create_notification_layout(data)
        assert isinstance(layout, HeroSimpleLayout)

        # Slot 0 should be CameraWidget even for image. entities
        image_slot = layout.get_slot(0)
        assert image_slot is not None
        assert image_slot.widget is not None
        image_widget = image_slot.widget
        assert image_widget.config.widget_type == "camera"
        assert image_widget.config.entity_id == "image.reolink_snap"

    @pytest.mark.asyncio
    async def test_notification_layout_icon_only(self, hass, coordinator_device, options):
        """Test notification with no message and no image (Fullscreen Icon)."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        data = {
            "icon": "mdi:alert"
            # No message
        }

        layout = coordinator._create_notification_layout(data)
        assert isinstance(layout, FullscreenLayout)

        icon_slot = layout.get_slot(0)
        assert icon_slot is not None
        assert icon_slot.widget is not None
        icon_widget = icon_slot.widget
        assert icon_widget.config.widget_type == "icon"
        assert icon_widget.config.options["icon"] == "mdi:alert"
        assert icon_widget.config.options["size"] == "huge"

    @pytest.mark.asyncio
    async def test_render_notification_active(self, hass, coordinator_device, options):
        """An active notification takes over the screen selection."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        coordinator._notification_data = {"message": "Active"}
        coordinator._notification_expiry = 2000

        with patch("time.time", return_value=1000):
            layout = coordinator._resolve_layout()

        assert isinstance(layout, HeroSimpleLayout)
        assert layout is not coordinator._layouts[0]

    @pytest.mark.asyncio
    async def test_render_notification_expired(self, hass, coordinator_device, options):
        """An expired notification leaves the configured view on screen."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        coordinator._notification_data = {"message": "Expired"}
        coordinator._notification_expiry = 900

        with patch("time.time", return_value=1000):
            layout = coordinator._resolve_layout()

        assert layout is coordinator._layouts[0]

    @pytest.mark.asyncio
    async def test_update_renders_the_notification_then_the_view(
        self, hass, coordinator_device, options
    ):
        """A full update cycle draws whatever ``_resolve_layout`` picked.

        The notification override only reaches the display if the layout
        resolved in the event loop is the one handed to the executor
        render — the two used to be decided separately, so the device
        could ship the view while the notification was "active".
        """
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        rendered: list = []

        def _capture(layout):
            rendered.append(layout)
            return (b"jpeg", b"png", "dashboard.jpg")

        object.__setattr__(coordinator, "_render_display", _capture)
        object.__setattr__(coordinator, "async_request_refresh", AsyncMock())

        with patch.object(hass.loop, "call_later"):
            await coordinator.trigger_notification({"message": "Hello", "duration": 5})
            await coordinator._async_update_data()

            assert isinstance(rendered[-1], HeroSimpleLayout)
            assert rendered[-1] is not coordinator._layouts[0]

            coordinator._clear_notification()
            await hass.async_block_till_done()
            await coordinator._async_update_data()

        assert rendered[-1] is coordinator._layouts[0]

    @pytest.mark.asyncio
    async def test_update_renders_a_fullscreen_notification(
        self, hass, coordinator_device, options
    ):
        """An icon-only notification reaches the render as a FullscreenLayout."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        rendered: list = []

        def _capture(layout):
            rendered.append(layout)
            return (b"jpeg", b"png", "dashboard.jpg")

        object.__setattr__(coordinator, "_render_display", _capture)
        object.__setattr__(coordinator, "async_request_refresh", AsyncMock())

        with patch.object(hass.loop, "call_later"):
            await coordinator.trigger_notification({"icon": "mdi:alert", "duration": 5})
            await coordinator._async_update_data()

        assert isinstance(rendered[-1], FullscreenLayout)

    @pytest.mark.asyncio
    async def test_notification_image_is_fetched_through_the_resolver(
        self, hass, coordinator_device, options, aioclient_mock
    ):
        """The notification declares its image need like any other screen.

        The camera widget the notification layout builds carries the
        image source, so nothing has to know that a notification is
        special — the layout is resolved first, then prefetched.
        """
        import io
        import time as time_module

        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (8, 8), (0, 128, 255)).save(buf, format="PNG")

        hass.config.internal_url = "https://example.com"
        hass.config.external_url = None
        hass.states.async_set(
            "image.doorbell", "idle", {"entity_picture": "/api/image_proxy/image.doorbell"}
        )
        aioclient_mock.get(
            "https://example.com/api/image_proxy/image.doorbell",
            content=buf.getvalue(),
            status=200,
        )

        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)
        coordinator._notification_data = {"image": "image.doorbell"}
        coordinator._notification_expiry = time_module.time() + 100

        layout = coordinator._resolve_layout()
        await coordinator._resolver.async_prefetch(layout)
        states = coordinator._resolver.build_states(layout)

        assert isinstance(layout, FullscreenLayout)
        assert states[0].image is not None
        assert states[0].image.size == (8, 8)
