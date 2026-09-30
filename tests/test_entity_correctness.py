"""Regression tests for integration-side correctness fixes.

Coordinator, entity platform and service behaviours that reported or
rendered the wrong thing. Widget-level regressions live in
``tests/widgets/test_state_correctness.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from homeassistant.const import CONF_HOST
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic import image as image_platform
from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DOMAIN,
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


async def _setup_preview_image(hass, entry: MockConfigEntry) -> list:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = MagicMock()
    added: list = []
    await image_platform.async_setup_entry(hass, entry, cast("Any", added.extend))
    return added


async def test_preview_image_unique_id_is_keyed_on_the_entry(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "10.0.0.5"}, entry_id="entry1")
    entry.add_to_hass(hass)
    added = await _setup_preview_image(hass, entry)
    assert added[0].unique_id == "entry1_preview"


async def test_preview_image_host_unique_id_is_migrated(hass) -> None:
    """A reconfigured host must not orphan the preview image entity."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "10.0.0.5"}, entry_id="entry1")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        "image", DOMAIN, "10.0.0.5_preview", config_entry=entry, suggested_object_id="desk"
    )
    await _setup_preview_image(hass, entry)
    migrated = registry.async_get(legacy.entity_id)
    assert migrated is not None
    assert migrated.unique_id == "entry1_preview"
    assert registry.async_get_entity_id("image", DOMAIN, "10.0.0.5_preview") is None


def test_preview_widget_states_carry_system_temperature_unit() -> None:
    hass = cast("Any", MockHass())
    hass.config.units = SimpleNamespace(temperature_unit="°F")
    widget = ClimateWidget(WidgetConfig(widget_type="climate", slot=0, entity_id="climate.x"))
    states = _build_preview_widget_states(hass, {0: widget}, {}, {}, {})
    assert states[0].temperature_unit == "°F"
