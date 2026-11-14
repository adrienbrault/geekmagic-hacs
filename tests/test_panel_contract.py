"""Contract: every view the panel can save must render.

The panel (TypeScript) writes view configs; the widgets (Python) read them.
Each side has its own tests, and both passed while the panel saved status
entities as ``{entity_id, label}`` objects the status list could not read:
one such widget took the whole device offline. These tests close that gap.

``tests/fixtures/panel_option_shapes.json`` holds one value per option type,
in exactly the shape the panel saves; ``frontend/src/panel-contract.test.ts``
type-checks the same file against the panel's types, so a shape change on
either side fails a test instead of a device.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.frame import FrameInputs
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.preview import MockHass
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS, build_widget
from custom_components.geekmagic.widgets.base import (
    WIDGET_ERROR_HTML,
    BrokenWidget,
    Widget,
    WidgetConfig,
)
from custom_components.geekmagic.widgets.state import WidgetState, build_entity_states
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

SHAPES: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "panel_option_shapes.json").read_text()
)


def _frame_states(hass: Any, widgets: dict[int, Widget]) -> dict[int, WidgetState]:
    """Each widget's state as a frame builds it (device and preview alike)."""
    layout = Grid2x2()
    for slot, widget in widgets.items():
        layout.set_widget(slot, widget)
    return FrameInputs(hass).widget_states(layout)


# Scalar option types: the value follows from the option's own schema.
SCALAR_TYPES = {"boolean", "number", "text", "textarea", "select"}

# An entity of the right domain for widgets that restrict their picker.
ENTITY_FOR_DOMAIN = {
    "camera": "camera.front",
    "climate": "climate.hvac",
    "media_player": "media_player.tv",
    "weather": "weather.home",
}


def make_hass() -> Any:
    """States for every entity the fixtures and widgets reference."""
    hass = cast("Any", MockHass())
    hass.states.set(
        "sensor.temp",
        "21.5",
        {"friendly_name": "Room", "unit_of_measurement": "°C", "device_class": "temperature"},
    )
    hass.states.set("sensor.humidity", "48", {"friendly_name": "Hum", "unit_of_measurement": "%"})
    hass.states.set("light.kitchen", "on", {"friendly_name": "Kitchen light"})
    hass.states.set("binary_sensor.door", "off", {"friendly_name": "Door", "device_class": "door"})
    hass.states.set("camera.front", "idle", {"friendly_name": "Front"})
    hass.states.set(
        "climate.hvac",
        "heat",
        {"friendly_name": "HVAC", "current_temperature": 20.5, "temperature": 22},
    )
    hass.states.set("media_player.tv", "playing", {"friendly_name": "TV", "media_title": "Song"})
    hass.states.set(
        "weather.home", "sunny", {"friendly_name": "Home", "temperature": 18, "humidity": 50}
    )
    return hass


def scalar_value(option: dict[str, Any]) -> Any:
    """A valid non-default value for a scalar option, as the panel stores it."""
    kind = option["type"]
    if kind == "boolean":
        return not option.get("default", False)
    if kind == "number":
        return option.get("min", option.get("default", 1))
    if kind == "select":
        first = option["options"][0]
        return first["value"] if isinstance(first, dict) else first
    return "{{ states('sensor.temp') }}" if kind == "textarea" else "x"


def full_config(widget_type: str) -> dict[str, Any]:
    """A slot with every option set, the way the panel saves it."""
    schema = WIDGET_TYPE_SCHEMAS[widget_type]
    config: dict[str, Any] = {"slot": 0, "type": widget_type, "label": "Label"}
    if schema.get("needs_entity"):
        domains = schema.get("entity_domains") or []
        config["entity_id"] = (
            ENTITY_FOR_DOMAIN.get(domains[0], "sensor.temp") if domains else ("sensor.temp")
        )
    options: dict[str, Any] = {}
    for option in schema.get("options", []):
        kind = option["type"]
        options[option["key"]] = scalar_value(option) if kind in SCALAR_TYPES else SHAPES[kind]
    config["options"] = options
    return config


def fresh_config(widget_type: str) -> dict[str, Any]:
    """What the panel saves right after a type is picked: nothing else set."""
    return {"slot": 0, "type": widget_type}


def render_like_production(config: dict[str, Any]) -> None:
    """Parse, resolve entities and render, as the device and preview both do."""
    widget = build_widget(config)
    assert widget is not None

    entity_ids = widget.get_entities()
    assert all(isinstance(e, str) for e in entity_ids), entity_ids

    states = _frame_states(make_hass(), {0: widget})
    for width, height in ((240, 240), (120, 120)):
        ctx = CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)
        html = widget.render_html(ctx, states[0])
        assert isinstance(html, str)
        assert html


def test_fixture_covers_every_option_type():
    """A new option type needs its panel shape recorded in the fixture."""
    used = {
        option["type"]
        for schema in WIDGET_TYPE_SCHEMAS.values()
        for option in schema.get("options", [])
    }
    missing = used - SCALAR_TYPES - set(SHAPES)
    assert not missing, f"add panel-shaped values for {sorted(missing)} to the fixture"


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
def test_widget_renders_every_option_the_panel_can_save(widget_type: str):
    render_like_production(full_config(widget_type))


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
def test_widget_renders_freshly_added_slot(widget_type: str):
    render_like_production(fresh_config(widget_type))


def test_status_list_honours_panel_labels_and_icons():
    """Panel rows carry a label and an icon; both must reach the render."""
    widget = build_widget(
        {
            "slot": 0,
            "type": "status_list",
            "options": {"entities": SHAPES["status_entities"]},
        }
    )
    assert widget is not None
    assert widget.get_entities() == ["light.kitchen", "binary_sensor.door"]

    states = _frame_states(make_hass(), {0: widget})
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    html = widget.render_html(ctx, states[0])
    assert "Kitchen" in html  # the panel label, not the friendly name
    assert "Kitchen light" not in html
    assert "Door" in html  # no label: falls back to the friendly name


# --- One broken widget costs one cell, never the device ---------------------


class _UnbuildableWidget(Widget):
    """A widget whose constructor rejects its config."""

    WIDGET_TYPE = "unbuildable"

    def __init__(self, config: WidgetConfig) -> None:
        raise ValueError("bad options")

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:  # pragma: no cover
        return ""


class _MalformedDependenciesWidget(Widget):
    """A widget whose config smuggles a non-id into its entity list."""

    def get_entities(self) -> list[str]:
        return cast("list[str]", [{"entity_id": "sensor.temp"}, "", "sensor.humidity"])

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        return "ok"


class _RaisingDependenciesWidget(_MalformedDependenciesWidget):
    def get_entities(self) -> list[str]:
        raise RuntimeError("boom")


def test_unbuildable_widget_becomes_an_error_cell(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(WIDGET_CLASSES, "unbuildable", _UnbuildableWidget)
    widget = build_widget({"slot": 1, "type": "unbuildable"})
    assert isinstance(widget, BrokenWidget)
    ctx = CellContext(width=120, height=120, slot_index=1, theme=DEFAULT_THEME)
    assert widget.render_html(ctx, WidgetState()) == WIDGET_ERROR_HTML


def test_malformed_entity_ids_are_skipped_not_fatal():
    widget = _MalformedDependenciesWidget(WidgetConfig(widget_type="x"))
    primary, additional = build_entity_states(make_hass().states.get, widget)
    assert primary is None
    assert set(additional) == {"sensor.humidity"}


def test_failing_entity_listing_leaves_the_widget_without_data():
    widget = _RaisingDependenciesWidget(WidgetConfig(widget_type="x"))
    assert build_entity_states(make_hass().states.get, widget) == (None, {})


def test_screen_still_renders_around_a_broken_widget(monkeypatch: pytest.MonkeyPatch):
    """The device path: build every slot, resolve states, composite the frame."""
    monkeypatch.setitem(WIDGET_CLASSES, "unbuildable", _UnbuildableWidget)
    layout = Grid2x2()
    widgets = {}
    for config in (
        {"slot": 0, "type": "clock"},
        {"slot": 1, "type": "unbuildable"},
        {"slot": 2, "type": "entity", "entity_id": "sensor.temp"},
    ):
        widget = build_widget(config)
        assert widget is not None
        layout.set_widget(config["slot"], widget)
        widgets[config["slot"]] = widget

    states = _frame_states(make_hass(), widgets)
    renderer = Renderer()
    img, draw = renderer.create_canvas()
    layout.render(renderer, draw, states)
    assert renderer.to_png(img)
