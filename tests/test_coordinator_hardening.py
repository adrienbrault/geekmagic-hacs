"""Regression tests for coordinator resilience (bad stored data, device errors)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.device import ConnectionResult


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
