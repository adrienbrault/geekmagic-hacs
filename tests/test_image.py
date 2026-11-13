"""Tests for the Display Preview image entity (issue #81)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DOMAIN,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.image import GeekMagicPreviewImage
from custom_components.geekmagic.models import ConnectionResult


@pytest.fixture
def preview_device():
    """Create a mock device whose update cycle always succeeds."""
    device = MagicMock()
    device.host = "192.168.1.100"
    device.model = "unknown"
    device.model_name = "SmallTV"
    device.firmware_version = None
    device.capabilities.brightness_range = (0, 100)
    device.capabilities.display_name = "SmallTV"
    device.capabilities.firmware_version = None
    device.display_rendered_dashboard = AsyncMock()
    device.set_brightness = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=None)
    device.is_builtin_theme = MagicMock(return_value=False)
    return device


@pytest.fixture
def options():
    """Single-screen options."""
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


@pytest.fixture
async def wired(hass, preview_device, options):
    """A real coordinator with the preview entity listening to it.

    ``async_write_ha_state`` is mocked: its call count is the entity churn
    (each write is a recorder row and a frontend image re-fetch).
    """
    entry = MockConfigEntry(domain=DOMAIN, data={"host": preview_device.host})
    coordinator = GeekMagicCoordinator(hass, preview_device, options)
    entity = GeekMagicPreviewImage(hass, coordinator, entry)
    entity.async_write_ha_state = MagicMock()
    remove_listener = coordinator.async_add_listener(entity._handle_coordinator_update)
    yield coordinator, entity
    remove_listener()
    await coordinator.async_shutdown()


async def _refresh(coordinator, png: bytes) -> None:
    """Run a full coordinator refresh (update + listener notification)."""
    with patch.object(coordinator, "_render_display", return_value=(b"jpeg", png, "dashboard.jpg")):
        await coordinator.async_refresh()


@pytest.mark.asyncio
async def test_changed_render_updates_entity(wired):
    """New content on a periodic refresh bumps the entity and serves it."""
    coordinator, entity = wired
    await _refresh(coordinator, b"png1")
    first = entity.image_last_updated
    assert first is not None
    assert await entity.async_image() == b"png1"
    entity.async_write_ha_state.reset_mock()

    await _refresh(coordinator, b"png2")

    entity.async_write_ha_state.assert_called_once()
    assert entity.image_last_updated is not None
    assert entity.image_last_updated >= first
    assert await entity.async_image() == b"png2"


@pytest.mark.asyncio
async def test_unchanged_render_does_not_touch_entity(wired):
    """An identical render leaves the entity state alone."""
    coordinator, entity = wired
    await _refresh(coordinator, b"png1")
    first = entity.image_last_updated
    entity.async_write_ha_state.reset_mock()

    await _refresh(coordinator, b"png1")

    entity.async_write_ha_state.assert_not_called()
    assert entity.image_last_updated == first


@pytest.mark.asyncio
async def test_pause_and_restore_do_not_touch_entity(hass, wired):
    """Out-of-cycle notifications (pause, restored pause) are not updates."""
    coordinator, entity = wired
    await _refresh(coordinator, b"png1")
    first = entity.image_last_updated
    entity.async_write_ha_state.reset_mock()

    await coordinator.async_set_active(False)
    coordinator.async_restore_paused()
    await hass.async_block_till_done()

    entity.async_write_ha_state.assert_not_called()
    assert entity.image_last_updated == first


@pytest.mark.asyncio
async def test_back_to_back_upload_failures_do_not_lose_an_update(wired, preview_device):
    """HA only notifies listeners on the first of consecutive failed refreshes.

    A render that never reached the device must not be committed to the
    preview, or the next successful cycle sees identical bytes, stays
    silent, and the entity is stuck on a stale frame.
    """
    coordinator, entity = wired
    preview_device.test_connection = AsyncMock(
        return_value=ConnectionResult(success=True, error="none", message="OK")
    )
    await _refresh(coordinator, b"png1")

    preview_device.display_rendered_dashboard = AsyncMock(side_effect=Exception("boom"))
    await _refresh(coordinator, b"png2")
    await _refresh(coordinator, b"png3")
    # The second failure really rendered (device reachable again)
    assert preview_device.display_rendered_dashboard.await_count == 2

    preview_device.display_rendered_dashboard = AsyncMock()
    entity.async_write_ha_state.reset_mock()
    await _refresh(coordinator, b"png3")

    entity.async_write_ha_state.assert_called_once()
    assert await entity.async_image() == b"png3"
