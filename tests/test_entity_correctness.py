"""Regression tests for integration-side correctness fixes.

Coordinator, entity platform and service behaviours that reported or
rendered the wrong thing. Widget-level regressions live in
``tests/widgets/test_state_correctness.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.preview import MockHass
from custom_components.geekmagic.websocket import _build_preview_widget_states
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.climate import ClimateWidget


def _device() -> MagicMock:
    device = MagicMock()
    device.display_rendered_dashboard = AsyncMock()
    device.set_brightness = AsyncMock()
    return device


def _options(widgets: list[dict]) -> dict:
    return {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREENS: [{"name": "Main", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: widgets}],
    }


# ---------------------------------------------------------------------------
# Climate: the HA system temperature unit reaches the widget
# ---------------------------------------------------------------------------


async def test_widget_states_carry_system_temperature_unit(hass) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    hass.states.async_set("climate.living", "heat", {"current_temperature": 72, "temperature": 70})
    coordinator = GeekMagicCoordinator(
        hass,
        _device(),
        _options([{"type": "climate", "slot": 0, "entity_id": "climate.living"}]),
    )
    layout = coordinator._layouts[0]
    states = coordinator._build_widget_states(layout)
    assert states[0].temperature_unit == "°F"


def test_preview_widget_states_carry_system_temperature_unit() -> None:
    hass = cast("Any", MockHass())
    hass.config.units = SimpleNamespace(temperature_unit="°F")
    widget = ClimateWidget(WidgetConfig(widget_type="climate", slot=0, entity_id="climate.x"))
    states = _build_preview_widget_states(hass, {0: widget}, {}, {}, {})
    assert states[0].temperature_unit == "°F"
