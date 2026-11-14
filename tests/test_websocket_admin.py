"""Every geekmagic/* websocket command is admin-only.

The panel is registered admin-only, but websocket commands are reachable
by any logged-in user. The commands save views and render previews, and
widget labels can hold Home Assistant templates, which core only lets
admins render (its own render_template command is admin-only).
"""

import pytest

from custom_components.geekmagic.websocket import async_register_websocket_commands

# One schema-valid message per command (schemas validate before the
# admin check, so each must pass validation to reach it).
COMMANDS = [
    {"type": "geekmagic/config"},
    {"type": "geekmagic/views/list"},
    {"type": "geekmagic/views/get", "view_id": "v"},
    {"type": "geekmagic/views/create", "name": "n"},
    {"type": "geekmagic/views/update", "view_id": "v", "name": "n"},
    {"type": "geekmagic/views/delete", "view_id": "v"},
    {"type": "geekmagic/views/duplicate", "view_id": "v"},
    {"type": "geekmagic/devices/list"},
    {"type": "geekmagic/devices/assign_views", "entry_id": "e", "view_ids": []},
    {"type": "geekmagic/devices/settings", "entry_id": "e", "brightness": 50},
    {
        "type": "geekmagic/preview/render",
        "view_config": {
            "layout": "fullscreen",
            "widgets": [{"type": "text", "slot": 0, "label": "{{ 1 + 1 }}"}],
        },
    },
    {"type": "geekmagic/entities/list"},
]


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: c["type"])
async def test_non_admin_is_refused(hass, hass_ws_client, hass_read_only_access_token, command):
    """A non-admin user gets ``unauthorized`` from every command."""
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json_auto_id(dict(command))
    msg = await client.receive_json()

    assert msg["success"] is False
    assert msg["error"]["code"] == "unauthorized"


def test_every_registered_command_is_covered():
    """Adding a command without listing it here would skip its admin test."""
    import inspect

    from custom_components.geekmagic import websocket

    source = inspect.getsource(websocket)
    registered = source.count("websocket_api.async_register_command(")
    gated = source.count("@websocket_api.require_admin")
    assert registered == len(COMMANDS) == gated
