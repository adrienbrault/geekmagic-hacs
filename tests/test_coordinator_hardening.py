"""Regression tests for coordinator resilience (bad stored data, device errors)."""

from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.device import ConnectionResult, GeekMagicDevice


@pytest.fixture
def device():
    """Mock device whose I/O all succeeds."""
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


def _options(widgets: list) -> dict:
    return {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREENS: [{"name": "Stored", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: widgets}],
    }


def test_malformed_stored_widgets_are_skipped(hass, device, caplog) -> None:
    """Bad persisted widgets are skipped instead of failing coordinator setup."""
    coordinator = GeekMagicCoordinator(
        hass,
        device,
        _options(
            [
                {"type": "clock", "slot": "abc"},
                {"type": "text", "slot": 1, "color": ["red", 0, 0]},
                "not-a-widget",
                {"type": "clock", "slot": 2},
            ]
        ),
    )

    layout = coordinator._layouts[0]
    placed = {i: s.widget.config.widget_type for i, s in enumerate(layout.slots) if s.widget}
    assert placed == {2: "clock"}
    assert caplog.text.count("Skipping malformed widget") == 3


RENDERED = (b"jpeg", b"png", "dashboard.jpg")


def _simple_options() -> dict:
    return _options([{"type": "clock", "slot": 0}])


async def test_probe_ok_but_upload_failing_keeps_backing_off(hass, device, caplog) -> None:
    """A reachable device whose uploads fail must back off, not flap online/offline."""
    coordinator = GeekMagicCoordinator(hass, device, _simple_options())
    device.display_rendered_dashboard.side_effect = aiohttp.ClientError("upload broke")

    failures, intervals = [], []
    with (
        patch.object(coordinator, "_render_display", return_value=RENDERED),
        caplog.at_level(logging.INFO),
    ):
        for _ in range(4):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
            failures.append(coordinator._consecutive_failures)
            intervals.append(coordinator.update_interval)

        assert failures == [1, 2, 3, 4]
        assert intervals == sorted(intervals)
        assert intervals[-1] > intervals[0]
        # Probed (and answered) on every cycle after the first failure...
        assert device.test_connection.await_count == 3
        # ...without ever claiming to be back online.
        assert "back online" not in caplog.text

        device.display_rendered_dashboard.side_effect = None
        result = await coordinator._async_update_data()

    assert result["success"] is True
    assert coordinator._consecutive_failures == 0
    assert coordinator._device_offline is False
    assert coordinator.update_interval == timedelta(seconds=10)
    assert caplog.text.count("back online after 4 failed attempts") == 1


async def test_recovery_in_builtin_mode_clears_backoff(hass, device) -> None:
    """A device that comes back while showing a built-in mode leaves backoff too."""
    coordinator = GeekMagicCoordinator(hass, device, _simple_options())
    coordinator._device_offline = True
    coordinator._consecutive_failures = 3
    coordinator._apply_backoff()
    coordinator.set_display_mode("builtin", 1)

    result = await coordinator._async_update_data()

    assert result["builtin_mode"] is True
    assert coordinator._consecutive_failures == 0
    assert coordinator.update_interval == timedelta(seconds=10)


@pytest.mark.parametrize("error", [ValueError("template broke"), OSError("cannot encode")])
async def test_render_errors_do_not_mark_device_offline(hass, device, caplog, error) -> None:
    """Render bugs are reported, not mistaken for an unreachable device."""
    coordinator = GeekMagicCoordinator(hass, device, _simple_options())

    with patch.object(coordinator, "_render_display", side_effect=error):
        for _ in range(2):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    assert coordinator._device_offline is False
    assert coordinator._consecutive_failures == 0
    assert coordinator.update_interval == timedelta(seconds=10)
    device.test_connection.assert_not_awaited()
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info is not None


async def test_connection_test_failures_log_at_debug(caplog) -> None:
    """The coordinator owns offline logging; the probe itself stays quiet."""
    session = MagicMock()
    session.get = MagicMock(
        side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("refused"))
    )
    probe_device = GeekMagicDevice("192.168.1.100", session=session)

    with caplog.at_level(logging.DEBUG):
        result = await probe_device.test_connection()

    assert not result
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


async def test_builtin_mode_selected_during_render_is_not_overridden(hass, device) -> None:
    """Picking a built-in mode mid-render must not be undone by that render's upload."""
    coordinator = GeekMagicCoordinator(hass, device, _simple_options())

    def render_while_user_selects_builtin():
        coordinator.set_display_mode("builtin", 6)
        return RENDERED

    with patch.object(
        coordinator, "_render_display", side_effect=render_while_user_selects_builtin
    ):
        result = await coordinator._async_update_data()

    assert result == {"success": True, "builtin_mode": True, "theme": 6}
    device.display_rendered_dashboard.assert_not_awaited()
    assert coordinator.display_mode == "builtin"


async def test_pause_during_render_skips_upload(hass, device) -> None:
    """Pausing mid-render must not wake the display with a fresh upload."""
    coordinator = GeekMagicCoordinator(hass, device, _simple_options())

    def render_while_user_pauses():
        coordinator._paused = True
        return RENDERED

    with patch.object(coordinator, "_render_display", side_effect=render_while_user_pauses):
        result = await coordinator._async_update_data()

    assert result == {"success": True, "paused": True}
    device.display_rendered_dashboard.assert_not_awaited()
