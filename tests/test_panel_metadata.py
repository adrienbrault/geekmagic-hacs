"""What the panel needs from the backend to draw its pickers and overlay.

The panel has no layout or widget knowledge of its own: layout tiles are
drawn from ``geekmagic/config`` rects, widget tiles from schema metadata,
option visibility from ``visible_when``, and the click-to-select overlay
from the slot rects each preview returns.
"""

from __future__ import annotations

import pytest

from custom_components.geekmagic.const import LAYOUT_GRID_2X2, LAYOUT_SLOT_COUNTS
from custom_components.geekmagic.frame import LAYOUT_CLASSES
from custom_components.geekmagic.websocket import async_register_websocket_commands
from custom_components.geekmagic.widgets import WIDGET_TYPE_SCHEMAS

CATEGORIES = {"values", "home", "time", "history", "pictures", "custom"}


async def _ws(hass, hass_ws_client, message: dict) -> dict:
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(message)
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]


async def test_config_names_and_draws_every_layout(hass, hass_ws_client):
    config = await _ws(hass, hass_ws_client, {"type": "geekmagic/config"})
    layouts = config["layout_types"]
    assert set(layouts) == set(LAYOUT_SLOT_COUNTS)
    names = [layout["name"] for layout in layouts.values()]
    assert len(set(names)) == len(names), "layout names must be distinct"
    assert layouts[LAYOUT_GRID_2X2]["name"] == "Grid 2\u00d72"
    for key, layout in layouts.items():
        assert len(layout["rects"]) == layout["slots"], key
        for x, y, w, h in layout["rects"]:
            assert 0 <= x < 1 and 0 <= y < 1, key
            assert 0 < w <= 1 and 0 < h <= 1, key
            assert x + w <= 1.0001 and y + h <= 1.0001, key


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
def test_widget_schema_carries_picker_metadata(widget_type: str):
    schema = WIDGET_TYPE_SCHEMAS[widget_type]
    assert schema["icon"].startswith("mdi:")
    assert schema["category"] in CATEGORIES
    assert schema["description"]
    assert isinstance(schema.get("uses_label", True), bool)


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
def test_visible_when_refers_to_real_options(widget_type: str):
    """A typo in a condition would hide an option forever."""
    options = {o["key"]: o for o in WIDGET_TYPE_SCHEMAS[widget_type].get("options", [])}
    for option in options.values():
        for key, allowed in option.get("visible_when", {}).items():
            assert key in options, f"{widget_type}.{option['key']} depends on unknown {key}"
            assert key != option["key"]
            assert isinstance(allowed, list)
            assert allowed
            choices = options[key].get("options")
            if choices:
                values = [c["value"] if isinstance(c, dict) else c for c in choices]
                assert set(allowed) <= set(values), (widget_type, key, allowed)


@pytest.mark.parametrize("theme", ["watchos", "retro"])
async def test_preview_returns_the_slot_rects_it_drew(hass, hass_ws_client, theme):
    """Rects depend on the theme's padding and gap, so they come with the image."""
    result = await _ws(
        hass,
        hass_ws_client,
        {
            "type": "geekmagic/preview/render",
            "view_config": {"layout": LAYOUT_GRID_2X2, "theme": theme, "widgets": []},
        },
    )
    layout = LAYOUT_CLASSES[LAYOUT_GRID_2X2]()
    from custom_components.geekmagic.widgets.theme import get_theme

    layout.theme = get_theme(theme)
    assert result["slots"] == [list(slot.rect) for slot in layout.slots]
    assert len(result["slots"]) == 4
