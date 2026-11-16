"""The GeekMagic LLM tools: what Assist and MCP clients edit views with.

Instances come from ``llm.async_get_api``, the call a conversation agent
and the MCP server make, so the admin gate, the schemas and the result
type are tested as an agent meets them: from Home Assistant's own
"Home Assistant" API on cores that have it (the ``llm`` platform), from
the standalone GeekMagic API before.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import llm
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import DOMAIN, LAYOUT_SLOT_COUNTS
from custom_components.geekmagic.llm_api import (
    API_PROMPT,
    DATA_RENDERS,
    LLM_API_ID,
    async_setup_llm_api,
    core_has_home_assistant_api,
)
from custom_components.geekmagic.store import GeekMagicStore
from custom_components.geekmagic.widgets import WIDGET_TYPE_SCHEMAS

SHAPES: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "panel_option_shapes.json").read_text()
)

ALL_TOOLS = {
    "geekmagic__get_catalog",
    "geekmagic__get_views",
    "geekmagic__find_entities",
    "geekmagic__create_view",
    "geekmagic__update_view",
    "geekmagic__set_widget",
    "geekmagic__clear_widget",
    "geekmagic__assign_views",
    "geekmagic__show_view",
    "geekmagic__render_view",
}


def _llm_context(user_id: str | None) -> llm.LLMContext:
    """An LLMContext on any core (its fields changed across releases)."""
    values: dict[str, Any] = {
        "platform": "test",
        "context": Context(user_id=user_id),
        "user_prompt": None,
        "language": "en",
        "assistant": "conversation",
        "device_id": None,
    }
    fields = {f.name for f in dataclasses.fields(llm.LLMContext)}
    return llm.LLMContext(**{k: v for k, v in values.items() if k in fields})


def _data(result: Any) -> dict[str, Any]:
    """A tool result's payload (``ToolResult`` on newer cores, a dict before)."""
    return result.data if hasattr(result, "data") else result


@pytest.fixture
async def store(hass: HomeAssistant) -> GeekMagicStore:
    store = GeekMagicStore(hass)
    await store.async_load()
    hass.data.setdefault(DOMAIN, {})["store"] = store
    async_setup_llm_api(hass)
    hass.states.async_set(
        "sensor.temp", "21.5", {"friendly_name": "Room", "unit_of_measurement": "°C"}
    )
    hass.states.async_set("sensor.humidity", "48", {"friendly_name": "Humidity"})
    hass.states.async_set("sensor.broken", "unavailable", {"friendly_name": "Broken"})
    hass.states.async_set("light.kitchen", "on", {"friendly_name": "Kitchen"})
    hass.states.async_set("binary_sensor.door", "off", {"friendly_name": "Door"})
    hass.states.async_set("weather.home", "sunny", {"friendly_name": "Home"})
    hass.states.async_set("camera.front", "idle", {"friendly_name": "Front"})
    hass.states.async_set("climate.hvac", "heat", {"friendly_name": "HVAC"})
    hass.states.async_set("media_player.tv", "playing", {"friendly_name": "TV"})
    return store


async def _get_api(hass: HomeAssistant, user_id: str | None) -> llm.APIInstance:
    """The API instance an agent of ``user_id`` gets the GeekMagic tools from."""
    if core_has_home_assistant_api():
        hass.config.components.add(DOMAIN)  # so the llm integration finds llm.py
        assert await async_setup_component(hass, "llm", {})
        api_id = llm.LLM_API_HOME_ASSISTANT  # ty: ignore[missing-attribute]
    else:
        api_id = LLM_API_ID
    return await llm.async_get_api(hass, api_id, _llm_context(user_id))


@pytest.fixture
async def api(hass: HomeAssistant, store: GeekMagicStore, hass_admin_user) -> llm.APIInstance:
    return await _get_api(hass, hass_admin_user.id)


async def _call(api: llm.APIInstance, name: str, /, **args: Any) -> dict[str, Any]:
    """Call a tool as an agent does: schema first, then the tool.

    Not through ``APIInstance.async_call_tool``: that only adds a
    conversation trace entry, and importing the conversation integration
    needs its requirements (hassil...), which change with every core.
    """
    tool = next(t for t in api.tools if t.name == name)
    tool_input = llm.ToolInput(tool_name=name, tool_args=tool.parameters(dict(args)))
    return _data(await tool.async_call(api.api.hass, tool_input, api.llm_context))


# =============================================================================
# Who gets the tools
# =============================================================================


async def test_admin_gets_every_tool(api: llm.APIInstance) -> None:
    geekmagic = {tool.name for tool in api.tools if tool.name.startswith("geekmagic__")}
    assert geekmagic == ALL_TOOLS
    assert API_PROMPT in api.api_prompt


@pytest.mark.parametrize("user", ["read_only", "none"])
async def test_only_admins_get_tools(
    hass: HomeAssistant, store: GeekMagicStore, hass_read_only_user, user: str
) -> None:
    """Anyone else gets no tools: no user is a voice satellite.

    Core's "Home Assistant" API refuses them outright. The standalone API
    hands them an empty instance instead: an error would break Assist
    itself for an agent that has both APIs ticked.
    """
    user_id = hass_read_only_user.id if user == "read_only" else None
    if core_has_home_assistant_api():
        with pytest.raises(Unauthorized):
            await _get_api(hass, user_id)
    else:
        assert (await _get_api(hass, user_id)).tools == []


async def test_not_offered_to_assist(hass: HomeAssistant, store: GeekMagicStore) -> None:
    """Assist is bounded by exposed entities; these tools configure displays."""
    pytest.importorskip("homeassistant.components.llm")  # the platform's cores only
    from custom_components.geekmagic.llm import async_get_tools

    assert async_get_tools(hass, _llm_context(None), "assist") is None


async def test_tool_refuses_a_non_admin_caller(
    hass: HomeAssistant, api: llm.APIInstance, hass_read_only_user
) -> None:
    """Each call checks again: an instance must not outlive its user's rights."""
    tool = next(t for t in api.tools if t.name == "geekmagic__get_views")
    with pytest.raises(HomeAssistantError, match="administrator"):
        await tool.async_call(
            hass,
            llm.ToolInput(tool_name=tool.name, tool_args={}),
            _llm_context(hass_read_only_user.id),
        )


async def test_registering_twice_is_harmless(hass: HomeAssistant, store: GeekMagicStore) -> None:
    async_setup_llm_api(hass)


async def test_standalone_api_only_before_the_home_assistant_api(
    hass: HomeAssistant, store: GeekMagicStore
) -> None:
    """Never both: an agent with both ticked would get every tool twice."""
    registered = {api.id for api in llm.async_get_apis(hass)}
    assert (LLM_API_ID in registered) is not core_has_home_assistant_api()


async def test_schemas_convert_for_agents(api: llm.APIInstance) -> None:
    """Every tool's parameters become a JSON schema, as agents and MCP send them."""
    try:
        from probatio import to_openapi as convert  # ty: ignore[import-not-found]
    except ImportError:
        from voluptuous_openapi import convert
    for tool in api.tools:
        schema = convert(tool.parameters, custom_serializer=api.custom_serializer)
        assert schema["type"] == "object", tool.name
        json.dumps(schema)


# =============================================================================
# Reading
# =============================================================================


async def test_catalog_lists_everything(api: llm.APIInstance) -> None:
    catalog = await _call(api, "geekmagic__get_catalog")
    json.dumps(catalog)
    assert set(catalog["widget_types"]) == set(WIDGET_TYPE_SCHEMAS)
    assert set(catalog["layouts"]) == set(LAYOUT_SLOT_COUNTS)
    for layout_id, layout in catalog["layouts"].items():
        assert len(layout["slot_sizes"]) == LAYOUT_SLOT_COUNTS[layout_id]
    assert catalog["layouts"]["fullscreen"]["slot_sizes"] == ["240x240"]
    gauge = {o["key"]: o for o in catalog["widget_types"]["gauge"]["options"]}
    assert gauge["style"]["options"] == ["bar", "ring", "arc"]
    assert "row_fields" in gauge["color_thresholds"]


async def test_find_entities(api: llm.APIInstance) -> None:
    found = await _call(api, "geekmagic__find_entities", domain="sensor")
    assert [e["entity_id"] for e in found["entities"]] == [
        "sensor.broken",
        "sensor.humidity",
        "sensor.temp",
    ]

    found = await _call(api, "geekmagic__find_entities", query="room")
    assert found["entities"] == [
        {
            "entity_id": "sensor.temp",
            "name": "Room",
            "state": "21.5",
            "unit": "°C",
            "device_class": None,
        }
    ]

    # Word starts rank first: "temp" is in "attempted" too
    hass = api.api.hass
    hass.states.async_set("sensor.backup_attempted", "x", {"friendly_name": "Backup"})
    found = await _call(api, "geekmagic__find_entities", query="temp")
    assert [e["entity_id"] for e in found["entities"]] == [
        "sensor.temp",
        "sensor.backup_attempted",
    ]

    found = await _call(api, "geekmagic__find_entities", widget_type="weather")
    assert [e["entity_id"] for e in found["entities"]] == ["weather.home"]

    found = await _call(api, "geekmagic__find_entities", limit=1)
    assert len(found["entities"]) == 1
    assert found["total"] > 1


async def test_get_views_lists_displays_loaded_or_not(
    hass: HomeAssistant, api: llm.APIInstance
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Desk", options={"assigned_views": ["v1"]})
    entry.add_to_hass(hass)
    result = await _call(api, "geekmagic__get_views")
    assert result["displays"] == [
        {
            "display_id": entry.entry_id,
            "name": "Desk",
            "online": False,
            "assigned_views": ["v1"],
            "current_view_id": None,
        }
    ]


# =============================================================================
# Writing
# =============================================================================


async def test_build_a_view(api: llm.APIInstance, store: GeekMagicStore) -> None:
    created = await _call(api, "geekmagic__create_view", name="Desk", layout="split_vertical")
    view_id = created["view_id"]
    assert [s["problems"] for s in created["slots"]] == [["empty"], ["empty"]]

    result = await _call(
        api,
        "geekmagic__set_widget",
        view="desk",  # by name, case-insensitive
        slot=0,
        type="gauge",
        entity_id="sensor.temp",
        color="#FF8800",
        options={"style": "ring", "max": 40, "color_thresholds": SHAPES["thresholds"]},
    )
    await _call(api, "geekmagic__set_widget", view=view_id, slot=1, type="clock")

    # Stored exactly as the panel stores it
    view = store.get_view(view_id)
    assert view is not None
    assert view["widgets"] == [
        {
            "type": "gauge",
            "slot": 0,
            "entity_id": "sensor.temp",
            "color": [255, 136, 0],
            "options": {"style": "ring", "max": 40, "color_thresholds": SHAPES["thresholds"]},
        },
        {"type": "clock", "slot": 1},
    ]
    assert "problems" not in result["slots"][0]
    assert result["slots"][0]["widget"]["color"] == [255, 136, 0]
    assert result["slots"][0]["size"].count("x") == 1

    # Replace, then clear
    await _call(api, "geekmagic__set_widget", view=view_id, slot=0, type="text", label="Hi")
    assert view["widgets"][0] == {"type": "text", "slot": 0, "label": "Hi"}
    cleared = await _call(api, "geekmagic__clear_widget", view=view_id, slot=0)
    assert view["widgets"] == [{"type": "clock", "slot": 1}]
    assert cleared["slots"][0]["problems"] == ["empty"]


async def test_set_widget_reports_every_problem(
    api: llm.APIInstance, store: GeekMagicStore
) -> None:
    view_id = await store.async_create_view(name="V", layout="grid_2x2")
    with pytest.raises(HomeAssistantError) as err:
        await _call(
            api,
            "geekmagic__set_widget",
            view=view_id,
            slot=7,
            type="gauge",
            entity_id="sensor.nope",
            options={"style": "donut", "colour": "red", "precision": 9, "show_value": "yes"},
        )
    message = str(err.value)
    assert "slots 0 to 3" in message
    assert "sensor.nope does not exist" in message
    assert "'donut'" in message
    assert "not an option of gauge" in message
    assert "between 0 and 5" in message
    assert store.views[view_id]["widgets"] == []  # nothing saved


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ({"type": "sparkles"}, "Unknown widget type"),
        ({"type": "entity"}, "needs an entity"),
        ({"type": "weather", "entity_id": "sensor.temp"}, "domains weather"),
        ({"type": "text", "color": "red"}, "#rrggbb"),
        ({"type": "entity", "entity_id": "sensor.temp", "options": {"icon": "bulb"}}, "mdi:"),
        (
            {"type": "status_list", "options": {"entities": [{"entity_id": "x.y", "z": 1}]}},
            "unknown field 'z'",
        ),
    ],
)
async def test_set_widget_rejects(
    api: llm.APIInstance, store: GeekMagicStore, args: dict[str, Any], expected: str
) -> None:
    view_id = await store.async_create_view(name="V")
    with pytest.raises(HomeAssistantError, match=expected):
        await _call(api, "geekmagic__set_widget", view=view_id, slot=0, **args)


def _panel_value(spec: dict[str, Any]) -> Any:
    """The value the panel would save for this option."""
    kind = spec["type"]
    if kind == "select":
        return spec["options"][-1]
    if kind == "boolean":
        return not spec.get("default", False)
    if kind == "number":
        return spec.get("min", spec.get("default", 1))
    if kind in ("text", "textarea"):
        return "x"
    if kind == "entity":
        return "sensor.temp"
    return SHAPES[kind]


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
async def test_accepts_everything_the_panel_saves(
    api: llm.APIInstance, store: GeekMagicStore, widget_type: str
) -> None:
    """The validator must never refuse a value the panel itself saves."""
    schema = WIDGET_TYPE_SCHEMAS[widget_type]
    entity = {
        "camera": "camera.front",
        "climate": "climate.hvac",
        "media_player": "media_player.tv",
        "sensor": "sensor.temp",
        "weather": "weather.home",
    }[(schema.get("entity_domains") or ["sensor"])[0]]
    options = {spec["key"]: _panel_value(spec) for spec in schema["options"]}
    view_id = await store.async_create_view(name="V")
    await _call(
        api,
        "geekmagic__set_widget",
        view=view_id,
        slot=0,
        type=widget_type,
        entity_id=entity,
        options=options,
    )
    stored = store.views[view_id]["widgets"][0]
    # The panel's blank "Add" rows are dropped; everything else is kept as is
    for key, value in options.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            assert stored["options"][key] == [r for r in value if r.get("entity_id") != ""]
        else:
            assert stored["options"][key] == value


async def test_update_view_validates_and_reports_hidden_widgets(
    api: llm.APIInstance, store: GeekMagicStore
) -> None:
    view_id = await store.async_create_view(
        name="V",
        layout="grid_2x2",
        widgets=[{"type": "clock", "slot": 0}, {"type": "text", "slot": 3, "label": "x"}],
    )
    with pytest.raises(HomeAssistantError, match="layout: one of"):
        await _call(api, "geekmagic__update_view", view=view_id, layout="grid_9x9")

    result = await _call(api, "geekmagic__update_view", view=view_id, layout="split_vertical")
    assert result["layout"] == "split_vertical"
    assert result["hidden_widgets"]["widgets"] == [{"type": "text", "slot": 3, "label": "x"}]


async def test_assign_views_by_name(
    hass: HomeAssistant, api: llm.APIInstance, store: GeekMagicStore
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Desk", options={"other": 1})
    entry.add_to_hass(hass)
    view_id = await store.async_create_view(name="Weather")
    result = await _call(api, "geekmagic__assign_views", display="desk", views=["weather"])
    assert result["assigned_views"] == [view_id]
    assert entry.options == {"other": 1, "assigned_views": [view_id]}

    with pytest.raises(HomeAssistantError, match='No view "nope"'):
        await _call(api, "geekmagic__assign_views", display="desk", views=["nope"])


async def test_show_view_needs_a_connected_display(
    hass: HomeAssistant, api: llm.APIInstance, store: GeekMagicStore
) -> None:
    MockConfigEntry(domain=DOMAIN, title="Desk").add_to_hass(hass)
    view_id = await store.async_create_view(name="V")
    with pytest.raises(HomeAssistantError, match="isn't connected"):
        await _call(api, "geekmagic__show_view", display="Desk", view=view_id)


# =============================================================================
# Rendering
# =============================================================================


async def test_render_reports_problems(
    hass: HomeAssistant, api: llm.APIInstance, store: GeekMagicStore
) -> None:
    view_id = await store.async_create_view(
        name="V",
        layout="grid_2x2",
        widgets=[
            {"type": "entity", "slot": 0, "entity_id": "sensor.gone"},
            {"type": "entity", "slot": 1, "entity_id": "sensor.broken"},
            {"type": "entity", "slot": 2, "entity_id": "sensor.temp"},
        ],
    )
    result = await _call(api, "geekmagic__render_view", view=view_id)
    problems = {s["slot"]: s.get("problems") for s in result["slots"]}
    assert problems == {
        0: ["sensor.gone does not exist"],
        1: ["sensor.broken is unavailable"],
        2: None,
        3: ["empty"],
    }
    assert "render_error" not in result


async def test_render_links_to_the_png(
    hass: HomeAssistant, api: llm.APIInstance, store: GeekMagicStore, hass_client_no_auth
) -> None:
    """The signed URL serves the PNG without a header; the bare path does not."""
    assert await async_setup_component(hass, "http", {})
    async_setup_llm_api(hass)  # registers the view, now that there is HTTP
    client = await hass_client_no_auth()
    view_id = await store.async_create_view(
        name="V", layout="fullscreen", widgets=[{"type": "clock", "slot": 0}]
    )
    result = await _call(api, "geekmagic__render_view", view=view_id)
    url = result["image_url"]
    path = url[url.index("/api/") :]

    response = await client.get(path)
    assert response.status == 200
    assert response.content_type == "image/png"
    assert (await response.read()).startswith(b"\x89PNG")

    unsigned = await client.get(path.split("?")[0])
    assert unsigned.status == 401

    hass.data[DATA_RENDERS].clear()
    assert (await client.get(path)).status == 404
