"""Security and validation tests for the GeekMagic websocket API."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.geekmagic.const import DOMAIN

from .test_ha_integration import setup_integration

# One schema-valid payload per registered command, so the only thing that
# can reject a non-admin call is the admin gate itself.
COMMAND_PAYLOADS: list[dict] = [
    {"type": "geekmagic/config"},
    {"type": "geekmagic/views/list"},
    {"type": "geekmagic/views/get", "view_id": "view_x"},
    {"type": "geekmagic/views/create", "name": "Sneaky"},
    {"type": "geekmagic/views/update", "view_id": "view_x", "name": "Renamed"},
    {"type": "geekmagic/views/delete", "view_id": "view_x"},
    {"type": "geekmagic/views/duplicate", "view_id": "view_x"},
    {"type": "geekmagic/devices/list"},
    {"type": "geekmagic/devices/assign_views", "entry_id": "entry_x", "view_ids": []},
    {"type": "geekmagic/devices/settings", "entry_id": "entry_x", "brightness": 10},
    {"type": "geekmagic/preview/render", "view_config": {"layout": "grid_2x2"}},
    {"type": "geekmagic/entities/list"},
]


@pytest.mark.parametrize("payload", COMMAND_PAYLOADS, ids=lambda p: p["type"])
async def test_non_admin_is_rejected(
    hass: HomeAssistant,
    aioclient_mock,
    hass_ws_client,
    hass_read_only_access_token: str,
    payload: dict,
) -> None:
    """Every command is admin-only, matching the admin-only panel."""
    await setup_integration(hass, aioclient_mock)
    store = hass.data[DOMAIN]["store"]
    views_before = store.get_views_list()

    client = await hass_ws_client(hass, access_token=hass_read_only_access_token)
    await client.send_json({"id": 1, **payload})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"
    assert store.get_views_list() == views_before


async def test_admin_can_create_view(hass: HomeAssistant, aioclient_mock, hass_ws_client) -> None:
    """The default (admin) connection keeps full access."""
    await setup_integration(hass, aioclient_mock)
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "geekmagic/views/create", "name": "Mine"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["view"]["name"] == "Mine"


@pytest.mark.parametrize(
    "widgets",
    [
        [{"type": "clock", "slot": "abc"}],
        [{"type": "clock", "slot": -1}],
        [{"type": "clock"}],
        [{"type": "clock", "slot": 0, "color": [255, 0]}],
        [{"type": "clock", "slot": 0, "color": ["red", 0, 0]}],
        [{"type": "clock", "slot": 0, "options": "not-a-dict"}],
        ["not-a-widget"],
    ],
)
async def test_create_view_rejects_malformed_widgets(
    hass: HomeAssistant, aioclient_mock, hass_ws_client, widgets: list
) -> None:
    """Widgets the coordinator could not rebuild are refused at the door."""
    await setup_integration(hass, aioclient_mock)
    store = hass.data[DOMAIN]["store"]
    client = await hass_ws_client(hass)

    await client.send_json(
        {"id": 1, "type": "geekmagic/views/create", "name": "Bad", "widgets": widgets}
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"
    assert store.get_views_list() == []


async def test_create_view_rejects_blank_name(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    """A view needs a visible name."""
    await setup_integration(hass, aioclient_mock)
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "geekmagic/views/create", "name": "   "})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"


async def test_create_and_update_view_accept_panel_widgets(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    """The shapes the panel sends keep working, extra keys included."""
    await setup_integration(hass, aioclient_mock)
    client = await hass_ws_client(hass)
    widgets = [
        {"type": "clock", "slot": 0, "options": {"show_date": True}},
        {"type": "entity", "slot": 1, "entity_id": "sensor.t", "label": None, "extra": 1},
        {"type": "text", "slot": 2, "color": [10, 20, 30]},
    ]

    await client.send_json(
        {"id": 1, "type": "geekmagic/views/create", "name": "Good", "widgets": widgets}
    )
    msg = await client.receive_json()
    assert msg["success"]
    view_id = msg["result"]["view_id"]
    assert msg["result"]["view"]["widgets"] == widgets

    await client.send_json(
        {
            "id": 2,
            "type": "geekmagic/views/update",
            "view_id": view_id,
            "widgets": [{"type": "clock", "slot": 3.0}],
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["view"]["widgets"] == [{"type": "clock", "slot": 3}]


async def test_update_view_rejects_malformed_widgets(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    """A rejected update leaves the stored view untouched."""
    await setup_integration(hass, aioclient_mock)
    store = hass.data[DOMAIN]["store"]
    view_id = await store.async_create_view(name="Keep", widgets=[{"type": "clock", "slot": 0}])
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/views/update",
            "view_id": view_id,
            "name": "",
            "widgets": [{"type": "clock", "slot": "x"}],
        }
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"
    view = store.get_view(view_id)
    assert view["name"] == "Keep"
    assert view["widgets"] == [{"type": "clock", "slot": 0}]


async def test_assign_views_rejects_unknown_view_ids(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    """Assigning a view that does not exist is refused, options unchanged."""
    entry = await setup_integration(hass, aioclient_mock)
    store = hass.data[DOMAIN]["store"]
    view_id = await store.async_create_view(name="Real")
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/devices/assign_views",
            "entry_id": entry.entry_id,
            "view_ids": [view_id, "view_missing"],
        }
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"
    assert "view_missing" in msg["error"]["message"]
    assert "assigned_views" not in entry.options


async def test_preview_rejects_malformed_widgets(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    """The preview validates widgets like create/update do."""
    await setup_integration(hass, aioclient_mock)
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/preview/render",
            "view_config": {"layout": "grid_2x2", "widgets": ["nope"]},
        }
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"
