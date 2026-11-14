"""The panel's device commands for displays whose config entry isn't loaded.

A display Home Assistant can't reach sits in ``setup_retry`` with no
coordinator. It is still configured, and its assigned views still live in
the entry's options, so the panel must keep listing it (field report: four
unreachable displays showed as "No displays yet", every view as "Not on
any display").
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import DOMAIN
from tests.test_device_control import _Panel
from tests.test_ha_integration import create_entry, setup_device_http_mocks, setup_integration

OFFLINE_HOST = "192.168.1.101"

# Every key the panel reads from a devices/list item.
DEVICE_KEYS = {
    "entry_id",
    "name",
    "host",
    "assigned_views",
    "current_view_index",
    "brightness",
    "refresh_interval",
    "cycle_interval",
    "online",
    "display_mode",
    "current_view_id",
    "builtin_mode",
    "entities",
    "state",
    "reason",
    "disabled",
}


async def _add_unreachable(
    hass: HomeAssistant, aioclient_mock, *, options: dict | None = None
) -> MockConfigEntry:
    """A display entry whose setup can't reach the device (``setup_retry``)."""
    aioclient_mock.get(f"http://{OFFLINE_HOST}/space.json", exc=TimeoutError("timed out"))
    entry = create_entry(host=OFFLINE_HOST, title="Kitchen", options=options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    return entry


async def _devices(panel: _Panel) -> dict[str, dict]:
    devices = (await panel.call(type="geekmagic/devices/list"))["devices"]
    return {device["entry_id"]: device for device in devices}


async def test_list_includes_a_display_in_setup_retry(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    """The reported case: the only display is unreachable."""
    entry = await _add_unreachable(
        hass,
        aioclient_mock,
        options={"screens": [], "assigned_views": ["view_a", "view_b"], "refresh_interval": 20},
    )
    panel = _Panel(await hass_ws_client(hass))

    device = (await _devices(panel))[entry.entry_id]

    assert set(device) == DEVICE_KEYS
    assert device["name"] == "Kitchen"
    assert device["host"] == OFFLINE_HOST
    assert device["assigned_views"] == ["view_a", "view_b"]
    assert device["refresh_interval"] == 20
    assert device["online"] is False
    assert device["state"] == "setup_retry"
    assert device["reason"].startswith(f"Could not connect to GeekMagic device at {OFFLINE_HOST}")
    assert device["disabled"] is False
    for key in ("brightness", "current_view_index", "display_mode", "current_view_id"):
        assert device[key] is None, key
    assert device["builtin_mode"] is None
    assert device["entities"] == {}


async def test_loaded_display_lists_as_before(hass: HomeAssistant, aioclient_mock, hass_ws_client):
    """Next to an unreachable one, a loaded display keeps its live fields."""
    loaded = await setup_integration(hass, aioclient_mock, theme=3, options={"screens": []})
    offline = await _add_unreachable(hass, aioclient_mock)
    panel = _Panel(await hass_ws_client(hass))

    devices = await _devices(panel)

    assert list(devices) == [loaded.entry_id, offline.entry_id]
    device = devices[loaded.entry_id]
    assert set(device) == DEVICE_KEYS
    assert device["state"] == "loaded"
    assert device["reason"] is None
    assert device["online"] is True
    assert device["brightness"] == 50
    assert device["display_mode"] == "custom"
    assert "brightness" in device["entities"]


async def test_list_includes_a_disabled_display(hass: HomeAssistant, hass_ws_client):
    from homeassistant.config_entries import ConfigEntryDisabler

    entry = create_entry(host=OFFLINE_HOST, title="Attic")
    entry.add_to_hass(hass)
    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
    # The domain (store, websocket commands) loads with any entry; here there
    # is none to load it, so set it up directly.
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, DOMAIN, {})
    panel = _Panel(await hass_ws_client(hass))

    device = (await _devices(panel))[entry.entry_id]

    assert device["state"] == "not_loaded"
    assert device["disabled"] is True
    assert device["reason"] is None


async def test_assign_views_to_an_unreachable_display_applies_once_it_loads(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    # Without "screens", options read as the legacy single-screen format and
    # assigned views are ignored (as in test_device_control).
    entry = await _add_unreachable(hass, aioclient_mock, options={"screens": []})
    panel = _Panel(await hass_ws_client(hass))
    views = [await panel.create_view("One"), await panel.create_view("Two")]

    await panel.call(
        type="geekmagic/devices/assign_views", entry_id=entry.entry_id, view_ids=views[::-1]
    )
    await hass.async_block_till_done()

    assert entry.options["assigned_views"] == views[::-1]
    assert (await _devices(panel))[entry.entry_id]["assigned_views"] == views[::-1]

    # The display comes back: setup starts from the edited options.
    aioclient_mock.clear_requests()
    setup_device_http_mocks(aioclient_mock, host=OFFLINE_HOST, theme=3)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    device = (await _devices(panel))[entry.entry_id]
    assert device["assigned_views"] == views[::-1]
    assert device["current_view_id"] == views[1]


async def test_assign_views_refuses_unknown_and_foreign_entries(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    await _add_unreachable(hass, aioclient_mock)
    foreign = MockConfigEntry(domain="other_integration", options={})
    foreign.add_to_hass(hass)
    panel = _Panel(await hass_ws_client(hass))

    for entry_id in ("nope", foreign.entry_id):
        error = await panel.error(
            type="geekmagic/devices/assign_views", entry_id=entry_id, view_ids=["v"]
        )
        assert error["code"] == "not_found"
    assert "assigned_views" not in foreign.options


async def test_brightness_needs_a_loaded_display(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    entry = await _add_unreachable(hass, aioclient_mock)
    panel = _Panel(await hass_ws_client(hass))

    error = await panel.error(
        type="geekmagic/devices/settings",
        entry_id=entry.entry_id,
        brightness=40,
        cycle_interval=60,
    )

    assert error["code"] == "not_loaded"
    assert "Kitchen" in error["message"]
    # Refused as a whole: nothing saved.
    assert "brightness" not in entry.options
    assert "screen_cycle_interval" not in entry.options


async def test_intervals_save_for_an_unreachable_display(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    entry = await _add_unreachable(hass, aioclient_mock)
    panel = _Panel(await hass_ws_client(hass))

    await panel.call(
        type="geekmagic/devices/settings",
        entry_id=entry.entry_id,
        refresh_interval=30,
        cycle_interval=60,
    )

    assert entry.options["refresh_interval"] == 30
    assert entry.options["screen_cycle_interval"] == 60


async def test_show_view_on_an_unreachable_display_says_why(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    entry = await _add_unreachable(hass, aioclient_mock)
    panel = _Panel(await hass_ws_client(hass))

    error = await panel.error(
        type="geekmagic/devices/show_view", entry_id=entry.entry_id, view_id="v"
    )

    assert error["code"] == "not_loaded"
    assert "Could not connect" in error["message"]


async def test_deleting_a_view_drops_it_from_an_unreachable_display(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
):
    entry = await _add_unreachable(hass, aioclient_mock, options={"screens": []})
    panel = _Panel(await hass_ws_client(hass))
    keep, drop = await panel.create_view("Keep"), await panel.create_view("Drop")
    await panel.call(
        type="geekmagic/devices/assign_views", entry_id=entry.entry_id, view_ids=[drop, keep]
    )

    await panel.call(type="geekmagic/views/delete", view_id=drop)
    await hass.async_block_till_done()

    assert entry.options["assigned_views"] == [keep]
