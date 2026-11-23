"""geekmagic.show_view and geekmagic.set_view_cycling (issue #160), end to end in HA."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.geekmagic.const import CONF_SKIPPED_VIEWS, DOMAIN
from custom_components.geekmagic.coordinator import GeekMagicCoordinator

from .test_ha_integration import setup_integration
from .test_websocket_unloaded_devices import _add_unreachable

CLOCK = [{"type": "clock", "slot": 0}]


@pytest.fixture(autouse=True)
def fast_render():
    """These tests are about which view shows, not its pixels."""
    with patch.object(
        GeekMagicCoordinator, "_render_display", return_value=(b"jpeg", b"png", "dashboard.jpg")
    ):
        yield


async def _display(hass: HomeAssistant, aioclient_mock, *names: str):
    """A loaded display with views ``names`` assigned; (entry, device id, ids)."""
    entry = await setup_integration(hass, aioclient_mock, theme=3, options={"screens": []})
    store = hass.data[DOMAIN]["store"]
    ids = [await store.async_create_view(name, widgets=CLOCK) for name in names]
    hass.config_entries.async_update_entry(entry, options={**entry.options, "assigned_views": ids})
    await hass.async_block_till_done()
    (device,) = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    return entry, device.id, ids


async def _call(hass: HomeAssistant, service: str, **data) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)
    await hass.async_block_till_done()


async def test_skip_and_include_by_name(hass: HomeAssistant, aioclient_mock):
    entry, device_id, (kitchen, shower, garden) = await _display(
        hass, aioclient_mock, "Kitchen", "Shower", "Garden"
    )

    await _call(
        hass, "set_view_cycling", device_id=device_id, view=["garden", "Shower"], cycle=False
    )
    # Kept in assigned order, whatever order the call named them in
    assert entry.options[CONF_SKIPPED_VIEWS] == [shower, garden]
    assert hass.data[DOMAIN][entry.entry_id].skipped_view_ids == [shower, garden]

    await _call(hass, "set_view_cycling", device_id=device_id, view=shower, cycle=True)
    assert entry.options[CONF_SKIPPED_VIEWS] == [garden]

    # A view id works too
    await _call(hass, "set_view_cycling", device_id=device_id, view=kitchen, cycle=False)
    assert entry.options[CONF_SKIPPED_VIEWS] == [kitchen, garden]


async def test_show_view_for_a_duration_then_back(hass: HomeAssistant, aioclient_mock):
    entry, device_id, (kitchen, shower) = await _display(hass, aioclient_mock, "Kitchen", "Shower")
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.current_view_id == kitchen

    await _call(hass, "show_view", device_id=device_id, view="Shower", duration={"minutes": 30})

    assert coordinator.current_view_id == shower
    assert hass.states.get("select.test_display_display").state == "Shower"
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert coordinator.current_view_id == kitchen
    assert hass.states.get("select.test_display_display").state == "Kitchen"


async def test_unknown_or_ambiguous_view_fails_the_call(hass: HomeAssistant, aioclient_mock):
    entry, device_id, _ids = await _display(hass, aioclient_mock, "Kitchen", "Twin", "Twin")

    with pytest.raises(ServiceValidationError, match='no view named "Bathroom"'):
        await _call(hass, "show_view", device_id=device_id, view="Bathroom")
    with pytest.raises(ServiceValidationError, match='2 views named "Twin"'):
        await _call(hass, "set_view_cycling", device_id=device_id, view="Twin", cycle=False)
    # One bad name fails the whole call: nothing is half applied
    with pytest.raises(ServiceValidationError):
        await _call(
            hass, "set_view_cycling", device_id=device_id, view=["Kitchen", "Nope"], cycle=False
        )
    assert entry.options.get(CONF_SKIPPED_VIEWS, []) == []


async def test_a_view_of_another_display_is_not_found(hass: HomeAssistant, aioclient_mock):
    _entry, device_id, _ids = await _display(hass, aioclient_mock, "Kitchen")
    await hass.data[DOMAIN]["store"].async_create_view("Unassigned", widgets=CLOCK)

    with pytest.raises(ServiceValidationError, match="no view named"):
        await _call(hass, "show_view", device_id=device_id, view="Unassigned")


async def test_not_a_geekmagic_device(hass: HomeAssistant, aioclient_mock):
    await _display(hass, aioclient_mock, "Kitchen")

    with pytest.raises(ServiceValidationError, match="not a GeekMagic display"):
        await _call(hass, "show_view", device_id="nope", view="Kitchen")


async def test_skipping_works_for_an_unreachable_display(hass: HomeAssistant, aioclient_mock):
    """Like the assignment, it is saved and applies once the display loads."""
    store_entry, _device_id, (kitchen,) = await _display(hass, aioclient_mock, "Kitchen")
    entry = await _add_unreachable(
        hass, aioclient_mock, options={"screens": [], "assigned_views": [kitchen]}
    )
    # Registered when the display last loaded
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}
    )

    await _call(hass, "set_view_cycling", device_id=device.id, view="Kitchen", cycle=False)
    assert entry.options[CONF_SKIPPED_VIEWS] == [kitchen]

    with pytest.raises(ServiceValidationError, match="not loaded"):
        await _call(hass, "show_view", device_id=device.id, view="Kitchen")
    assert store_entry.options.get(CONF_SKIPPED_VIEWS, []) == []
