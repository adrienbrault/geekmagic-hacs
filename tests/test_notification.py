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
from custom_components.geekmagic.widgets.components import THEME_TEXT_PRIMARY
from custom_components.geekmagic.widgets.data_card import DataCard
from custom_components.geekmagic.widgets.state import WidgetState
from custom_components.geekmagic.widgets.theme import get_theme


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
        """Test render loop uses notification layout when active."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        # Setup active notification
        coordinator._notification_data = {"message": "Active"}
        coordinator._notification_expiry = 2000

        # Mock renderer methods to avoid actual PIL calls
        object.__setattr__(
            coordinator.renderer,
            "create_canvas",
            MagicMock(return_value=(MagicMock(), MagicMock())),
        )
        object.__setattr__(coordinator.renderer, "to_jpeg", MagicMock(return_value=b"jpeg"))
        object.__setattr__(coordinator.renderer, "to_png", MagicMock(return_value=b"png"))

        # Build widget states mock
        object.__setattr__(coordinator, "_build_widget_states", MagicMock(return_value={}))

        with (
            patch("time.time", return_value=1000),
            patch.object(
                coordinator,
                "_create_notification_layout",
                wraps=coordinator._create_notification_layout,
            ) as mock_create,
        ):
            coordinator._render_display()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_notification_expired(self, hass, coordinator_device, options):
        """Test render loop ignores notification when expired."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        # Setup expired notification
        coordinator._notification_data = {"message": "Expired"}
        coordinator._notification_expiry = 900

        # Mock renderer methods
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
                coordinator,
                "_create_notification_layout",
                wraps=coordinator._create_notification_layout,
            ) as mock_create,
        ):
            coordinator._render_display()
            mock_create.assert_not_called()


class TestNotificationThemeColor:
    """Regression tests for issue #95: notification text unreadable on light theme.

    The notification text widget used to hardcode color=COLOR_WHITE, which
    overrode the layout theme and made the message invisible on the light
    theme's near-white background. The fix removed the override so TextWidget
    falls back to the THEME_TEXT_PRIMARY sentinel, which resolves to the
    active theme's text_primary at render time.
    """

    @pytest.mark.asyncio
    async def test_notification_text_has_no_color_override(self, hass, coordinator_device, options):
        """Notification text must not hardcode a color — theme decides."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        layout = coordinator._create_notification_layout({"message": "Hello", "theme": "light"})

        assert isinstance(layout, HeroSimpleLayout)
        assert layout.theme.name == "light"

        text_slot = layout.get_slot(1)
        assert text_slot is not None
        text_widget = text_slot.widget
        assert text_widget is not None
        assert text_widget.config.widget_type == "text"
        # Regression guard: any reintroduced hardcoded color (e.g. white)
        # would fail here and override the theme's text color.
        assert text_widget.config.color is None

    @pytest.mark.asyncio
    async def test_notification_text_falls_back_to_theme_text_primary(
        self, hass, coordinator_device, options
    ):
        """With no color override, the hero color is the theme sentinel."""
        coordinator = GeekMagicCoordinator(hass, coordinator_device, options)

        layout = coordinator._create_notification_layout({"message": "Hello", "theme": "light"})
        text_slot = layout.get_slot(1)
        assert text_slot is not None
        text_widget = text_slot.widget
        assert text_widget is not None

        component = text_widget.render(MagicMock(), WidgetState(entity=None))
        assert isinstance(component, DataCard)
        assert component.hero_color is THEME_TEXT_PRIMARY

        # The light theme resolves the sentinel to dark text, not white.
        light = get_theme("light")
        assert light.text_primary == (28, 28, 32)
        assert light.text_primary != (255, 255, 255)
