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
