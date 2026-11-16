"""``geekmagic/views/check``: what the panel's import checks before saving.

The panel pastes a view designed elsewhere (by the offline renderer, by an
AI), maps the entity ids this Home Assistant doesn't have, previews it and
saves it. The check remaps with ``view_io.remap_entities`` and validates
with ``view_io.validate_view``: the same code as the offline renderer's
``--map`` and ``--check``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from custom_components.geekmagic.view_io import view_entities
from custom_components.geekmagic.websocket import async_register_websocket_commands
from custom_components.geekmagic.widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS, build_widget
from tests.test_panel_contract import full_config


def _widget(widget_type: str) -> dict[str, Any]:
    """Every option the panel can save; panel-less widgets get an entity and a label."""
    if widget_type in WIDGET_TYPE_SCHEMAS:
        return full_config(widget_type)
    return {
        "slot": 0,
        "type": widget_type,
        "entity_id": "sensor.temp",
        "label": "{{ states('sensor.humidity') }}",
    }


LABEL = "{{ states('sensor.co2') }} {{ states.light.desk.state }}"


def _view(*widgets: dict[str, Any], layout: str = "grid_2x2") -> dict[str, Any]:
    return {"name": "Imported", "layout": layout, "theme": "watchos", "widgets": list(widgets)}


@pytest.fixture
async def check(hass, hass_ws_client):
    """Send ``geekmagic/views/check`` and return its result."""
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)

    async def _check(view: dict[str, Any], entity_map: dict[str, str] | None = None):
        message: dict[str, Any] = {"type": "geekmagic/views/check", "view_config": view}
        if entity_map is not None:
            message["entity_map"] = entity_map
        await client.send_json_auto_id(message)
        msg = await client.receive_json()
        assert msg["success"], msg
        return msg["result"]

    return _check


def _quoted(entity_id: str, dumped: str) -> bool:
    """``entity_id`` appears as a whole JSON string or a quoted template literal."""
    return any(f"{q}{entity_id}{q}" in dumped for q in ('"', "'", '\\"'))


@pytest.mark.parametrize("widget_type", sorted(WIDGET_CLASSES))
async def test_remaps_every_entity_of_every_widget(hass, check, widget_type):
    """Every option shape the panel saves: after the map, only the new ids are read."""
    original = _view(_widget(widget_type))
    old_ids = view_entities(original)
    mapping = {old: old.replace(".", ".mapped_", 1) for old in old_ids}
    for new in mapping.values():
        hass.states.async_set(new, "1")

    result = await check(original, mapping)

    before = build_widget(original["widgets"][0])
    after = build_widget(result["view"]["widgets"][0])
    assert before is not None
    assert after is not None
    assert set(after.get_entities()) == {mapping[e] for e in before.get_entities()}
    dumped = json.dumps(result["view"])
    for old in old_ids:
        assert not _quoted(old, dumped), f"{old} is still in the view"
    assert result["errors"] == []
    assert {e["id"] for e in result["entities"]} == set(mapping.values())
    assert all(e["exists"] for e in result["entities"])


async def test_lists_what_this_home_assistant_lacks(hass, check):
    hass.states.async_set("sensor.here", "1")
    view = _view(
        {"type": "entity", "slot": 0, "entity_id": "sensor.here"},
        {"type": "weather", "slot": 1, "entity_id": "weather.demo_home"},
        {"type": "text", "slot": 2, "label": LABEL},
    )

    result = await check(view)

    assert result["entities"] == [
        {"id": "sensor.here", "exists": True, "domain": "sensor"},
        {"id": "weather.demo_home", "exists": False, "domain": "weather"},
        {"id": "sensor.co2", "exists": False, "domain": "sensor"},
        {"id": "light.desk", "exists": False, "domain": "light"},
    ]
    assert result["view"] == view
    assert result["errors"] == []


async def test_maps_ids_inside_label_templates(hass, check):
    view = _view({"type": "text", "slot": 0, "label": LABEL})

    result = await check(view, {"sensor.co2": "sensor.office_co2", "light.desk": "light.lamp"})

    assert result["view"]["widgets"][0]["label"] == (
        "{{ states('sensor.office_co2') }} {{ states.light.lamp.state }}"
    )
    assert [e["id"] for e in result["entities"]] == ["sensor.office_co2", "light.lamp"]


@pytest.mark.parametrize(
    ("view", "error"),
    [
        ({"layout": "nope", "widgets": []}, "unknown layout"),
        (_view({"type": "nope", "slot": 0}), "unknown widget type"),
        (_view({"type": "clock", "slot": 9}), "outside the layout"),
        ({"layout": "grid_2x2", "theme": "nope", "widgets": []}, "unknown theme"),
    ],
)
async def test_reports_errors(check, view, error):
    result = await check(view)
    assert any(error in message for message in result["errors"]), result["errors"]


async def test_warns_without_a_theme(check):
    result = await check({"layout": "fullscreen", "widgets": [{"type": "clock", "slot": 0}]})
    assert result["errors"] == []
    assert any("no theme" in w for w in result["warnings"])


async def test_saves_nothing(hass, check):
    """A check is read-only: no store is needed, none is touched."""
    await check(_view({"type": "clock", "slot": 0}))
    assert "geekmagic" not in hass.data
