"""``view_io``: checking, remapping and rendering views from states files."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from custom_components.geekmagic import view_io
from custom_components.geekmagic.view import build_layout
from custom_components.geekmagic.view_io import (
    States,
    StatesFrameData,
    ViewFileError,
    load_states,
    missing_data,
    parse_states,
    remap_entities,
    render_view,
    resolve_forecast,
    validate_view,
)
from custom_components.geekmagic.widgets import WIDGET_TYPE_SCHEMAS

REPO_ROOT = Path(__file__).parent.parent
SKILL = REPO_ROOT / "skills" / "geekmagic-views"
EXAMPLES = sorted((SKILL / "examples").glob("*.json"))
SHAPES: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "panel_option_shapes.json").read_text()
)
NOW = datetime(2026, 11, 16, 8, 30, tzinfo=UTC)


def _view(*widgets: Any, layout: str = "grid_2x2") -> dict[str, Any]:
    return {"name": "t", "layout": layout, "theme": "watchos", "widgets": list(widgets)}


# =============================================================================
# validate_view
# =============================================================================


def test_a_panel_view_is_valid():
    check = validate_view(_view({"type": "entity", "slot": 0, "entity_id": "sensor.x"}))
    assert check.ok
    assert check.warnings == []


@pytest.mark.parametrize(
    ("view", "error"),
    [
        ([], "a view is a JSON object"),
        ({"layout": "grid_9x9", "widgets": []}, "unknown layout 'grid_9x9'"),
        ({"widgets": []}, "unknown layout None"),
        ({"layout": "grid_2x2", "theme": "pink", "widgets": []}, "unknown theme 'pink'"),
        (_view({"type": "sparkles", "slot": 0}), "unknown widget type"),
        (_view({"type": "clock", "slot": 4}), "slot 4 is outside the layout (0-3)"),
        (_view({"type": "clock", "slot": "a"}), "slot 'a' is not a number"),
        (
            _view({"type": "clock", "slot": 1}, {"type": "clock", "slot": 1}),
            "slot 1 already has a widget",
        ),
        (_view("clock"), "a widget is a JSON object"),
        (_view({"type": "clock", "options": []}), "options is a JSON object"),
        ({"layout": "grid_2x2", "theme": [], "widgets": []}, "unknown theme []"),
        ({"layout": [], "widgets": []}, "unknown layout []"),
        (_view({"type": [], "slot": 0}), "unknown widget type"),
        (_view({"type": "clock", "color": ["a", "b", "c"]}), "color is [r, g, b]"),
    ],
)
def test_errors(view, error):
    check = validate_view(view)
    assert not check.ok
    assert any(error in e for e in check.errors), check.errors


@pytest.mark.parametrize(
    ("widget", "warning"),
    [
        ({"type": "clock", "options": {"sparkle": True}}, "unknown option 'sparkle'"),
        ({"type": "gauge", "entity_id": "sensor.x", "options": {"style": "pie"}}, "'style'"),
        ({"type": "gauge"}, "needs an entity_id"),
        ({"type": "clock", "colour": [1, 2, 3]}, "unknown key 'colour'"),
    ],
)
def test_warnings(widget, warning):
    check = validate_view(_view({"slot": 0, **widget}))
    assert check.ok, check.errors
    assert any(warning in w for w in check.warnings), check.warnings


def test_a_view_without_theme_warns():
    check = validate_view({"layout": "fullscreen", "widgets": []})
    assert check.ok
    assert any("no theme" in w for w in check.warnings)


# =============================================================================
# remap_entities
# =============================================================================


def _panel_widget(widget_type: str) -> dict[str, Any]:
    """A widget with every option set the way the panel saves it."""
    options: dict[str, Any] = {}
    for option in WIDGET_TYPE_SCHEMAS[widget_type].get("options", []):
        if option["type"] in SHAPES:
            options[option["key"]] = SHAPES[option["type"]]
    return {"type": widget_type, "slot": 0, "entity_id": "sensor.temp", "options": options}


@pytest.mark.parametrize("widget_type", sorted(WIDGET_TYPE_SCHEMAS))
def test_remap_reaches_every_option_shape(widget_type):
    """Entity ids in every option shape the panel saves get remapped."""
    old_ids = ["sensor.temp", "sensor.humidity", "light.kitchen", "binary_sensor.door"]
    mapping = {old: old.replace(".", ".new_") for old in old_ids}
    view = _view(_panel_widget(widget_type))

    remapped = remap_entities(view, mapping)

    dumped = json.dumps(remapped)
    for old, new in mapping.items():
        assert f'"{old}"' not in dumped
        if f'"{old}"' in json.dumps(view):
            assert f'"{new}"' in dumped
    assert remapped["widgets"][0]["entity_id"] == "sensor.new_temp"
    assert view["widgets"][0]["entity_id"] == "sensor.temp", "the input is left as is"


def test_remap_rewrites_template_literals():
    html = (
        "{% set f = forecast('weather.home') %}{{ states(\"sensor.x\") }}"
        "{{ state_attr('sensor.x', 'unit') }}{{ is_state('lock.door', 'locked') }}"
        "{{ history('sensor.x', hours=6) }}{{ picture('camera.door') }}"
        "{% set e = 'sensor.x' %}{{ states.sensor.x.state }}"
        "{{ states('sensor.x_2') }}{{ 'sensor.xy' }}"
    )
    view = _view(
        {
            "type": "html",
            "slot": 0,
            "options": {"html": html},
        },
        {
            "type": "entity",
            "slot": 1,
            "entity_id": "sensor.x",
            "label": "{{ states('sensor.x') }} / {{ states.sensor.x.attributes.unit }}",
        },
    )
    mapping = {
        "sensor.x": "sensor.y",
        "weather.home": "weather.cottage",
        "lock.door": "lock.front",
        "camera.door": "camera.porch",
    }

    remapped = remap_entities(view, mapping)

    out = remapped["widgets"][0]["options"]["html"]
    assert out == (
        "{% set f = forecast('weather.cottage') %}{{ states(\"sensor.y\") }}"
        "{{ state_attr('sensor.y', 'unit') }}{{ is_state('lock.front', 'locked') }}"
        "{{ history('sensor.y', hours=6) }}{{ picture('camera.porch') }}"
        "{% set e = 'sensor.y' %}{{ states.sensor.y.state }}"
        "{{ states('sensor.x_2') }}{{ 'sensor.xy' }}"
    )
    assert remapped["widgets"][1]["label"] == (
        "{{ states('sensor.y') }} / {{ states.sensor.y.attributes.unit }}"
    )
    assert remapped["widgets"][1]["entity_id"] == "sensor.y"


def test_remap_without_mapping_copies():
    view = _view({"type": "clock", "slot": 0})
    copy = remap_entities(view, {})
    assert copy == view
    assert copy is not view


# =============================================================================
# States files
# =============================================================================


def test_parse_states(tmp_path):
    states = parse_states(
        {
            "version": 1,
            "now": "2026-11-16T08:30:00+01:00",
            "entities": {"camera.x": {"state": "idle", "picture": "x.jpg"}},
            "templates": {"2": {"{{ name }}": "Kitchen"}},
            "images": {"/local/a.png": "a.png"},
        },
        tmp_path,
    )
    assert states.entities["camera.x"]["picture"] == tmp_path / "x.jpg"
    assert states.templates == {2: {"{{ name }}": "Kitchen"}}
    assert states.images == {"/local/a.png": tmp_path / "a.png"}
    assert states.now is not None and states.now.utcoffset() is not None
    entity = states.get("camera.x")
    assert entity is not None and entity.state == "idle" and entity.attributes == {}
    assert states.get("camera.y") is None


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"version": 2}, "version 2"),
        ([], "a states file is a JSON object"),
        ({"entities": {"sensor.x": "21"}}, "an entity is a JSON object"),
        ({"now": "2026-11-16T08:30:00"}, "needs a UTC offset"),
    ],
)
def test_bad_states(tmp_path, data, error):
    with pytest.raises(ViewFileError, match=error):
        parse_states(data, tmp_path)


def test_later_states_files_win(tmp_path):
    (tmp_path / "a.json").write_text(
        json.dumps(
            {
                "entities": {"sensor.a": {"state": "1"}, "sensor.b": {"state": "2"}},
                "templates": {"0": {"x": "1"}},
            }
        )
    )
    (tmp_path / "b.json").write_text(
        json.dumps({"entities": {"sensor.b": {"state": "3"}}, "templates": {"0": {"y": "2"}}})
    )

    states = load_states(tmp_path / "a.json", tmp_path / "b.json")

    assert {e: d["state"] for e, d in states.entities.items()} == {"sensor.a": "1", "sensor.b": "3"}
    assert states.templates == {0: {"x": "1", "y": "2"}}


def test_unreadable_states_file(tmp_path):
    with pytest.raises(ViewFileError):
        load_states(tmp_path / "missing.json")


def test_relative_forecast_dates():
    days = resolve_forecast([{"datetime": "+1", "condition": "sunny"}, {"datetime": "x"}], NOW)
    assert days[0]["datetime"] == "2026-11-17T12:00:00+00:00"
    assert days[1]["datetime"] == "x"


def test_frame_data_serves_what_widgets_ask(tmp_path):
    Image.new("RGB", (10, 10), (255, 0, 0)).save(tmp_path / "pic.png")
    states = parse_states(
        {
            "entities": {
                "sensor.a": {"state": "1", "history": [1, 2, 3]},
                "sensor.b": {"state": "1", "history": {"6": [4, 5], "24": [6, 7]}},
                "sensor.c": {"state": "1", "candles": [[1, 2, 0, 1]]},
                "weather.w": {"state": "sunny", "forecast": [{"datetime": "+0"}]},
                "camera.c": {"state": "idle", "picture": "pic.png"},
            },
            "images": {"/local/i.png": "pic.png"},
        },
        tmp_path,
    )
    layout = build_layout(
        _view(
            {"type": "chart", "slot": 0, "entity_id": "sensor.a", "options": {"hours": 12}},
            {"type": "chart", "slot": 1, "entity_id": "sensor.b", "options": {"hours": 6}},
            {"type": "candlestick", "slot": 2, "entity_id": "sensor.c"},
            {"type": "image", "slot": 3, "options": {"source": "/local/i.png"}},
            {"type": "weather", "slot": 4, "entity_id": "weather.w"},
            {"type": "camera", "slot": 5, "entity_id": "camera.c"},
            layout="grid_2x3",
        )
    )

    data = StatesFrameData(states, layout, NOW)

    assert data.chart_history[("sensor.a", 12.0)] == [1.0, 2.0, 3.0]
    assert data.chart_history[("sensor.b", 6.0)] == [4.0, 5.0]
    (((entity_id, _interval, _count), candles),) = data.candlestick_data.items()
    assert entity_id == "sensor.c"
    assert candles == [(1.0, 2.0, 0.0, 1.0)]
    assert data.weather_forecasts["weather.w"][0]["datetime"].startswith("2026-11-16T12:00")
    assert data.source_images["/local/i.png"].size == (10, 10)
    picture = data.picture("camera.c", "camera")
    assert picture is not None and picture.getpixel((0, 0)) == (255, 0, 0)
    assert data.picture("camera.none", "camera") is None
    # Only to the widgets that draw it, as Home Assistant fetches it
    assert data.picture("camera.c", "media") is None


def test_frame_data_skips_what_no_widget_draws(tmp_path):
    Image.new("RGB", (10, 10)).save(tmp_path / "pic.png")
    states = parse_states(
        {
            "entities": {
                "weather.w": {"state": "sunny", "forecast": [{"datetime": "+0"}]},
                "media_player.m": {"state": "playing", "picture": "pic.png"},
            }
        },
        tmp_path,
    )
    layout = build_layout(
        _view(
            {
                "type": "weather",
                "slot": 0,
                "entity_id": "weather.w",
                "options": {"show_forecast": False},
            },
            {
                "type": "media",
                "slot": 1,
                "entity_id": "media_player.m",
                "options": {"show_album_art": False},
            },
        )
    )

    data = StatesFrameData(states, layout, NOW)

    assert data.weather_forecasts == {}
    assert data.picture("media_player.m", "media") is None


def test_missing_data():
    states = States(entities={"sensor.a": {"state": "1"}})
    view = _view(
        {"type": "entity", "slot": 0, "entity_id": "sensor.a", "label": "{{ name }}!"},
        {"type": "entity", "slot": 1, "entity_id": "sensor.b"},
    )
    assert missing_data(view, states) == [
        "slot 0: template '{{ name }}!' has no rendered output, shown as is",
        "slot 1: no state for sensor.b",
    ]


def test_missing_data_names_the_history_window_a_widget_asks():
    """Changing a chart's period, or an HTML history() window, says why the cell is empty."""
    states = States(
        entities={
            "sensor.by_hours": {"state": "1", "history": {"24": [1, 2], "1": [3], "6": []}},
            "sensor.any_window": {"state": "1", "history": [1, 2, 3]},
            "sensor.none": {"state": "1"},
        }
    )
    html = "{{ history('sensor.none', 3) }}"
    view = _view(
        {
            "type": "chart",
            "slot": 0,
            "entity_id": "sensor.by_hours",
            "options": {"period": "6 hours"},
        },
        {"type": "chart", "slot": 1, "entity_id": "sensor.any_window"},
        {"type": "html", "slot": 2, "options": {"html": html}},
        {"type": "chart", "slot": 3, "entity_id": "sensor.absent"},
    )
    assert missing_data(view, states) == [
        "slot 0: no history for sensor.by_hours over 6h (has 24h, 1h)",
        "slot 2: no history for sensor.none over 3h",
        "slot 3: no state for sensor.absent",
    ]


def test_missing_data_names_missing_candles_forecasts_and_pictures():
    states = States(
        entities={
            "sensor.price": {"state": "1"},
            "weather.home": {"state": "sunny"},
            "camera.door": {"state": "idle"},
            "media_player.tv": {"state": "playing"},
        }
    )
    view = _view(
        {"type": "candlestick", "slot": 0, "entity_id": "sensor.price"},
        {"type": "weather", "slot": 1, "entity_id": "weather.home"},
        {"type": "camera", "slot": 2, "entity_id": "camera.door"},
        {
            "type": "html",
            "slot": 3,
            "options": {"html": "{{ picture('media_player.tv') }}{{ forecast('weather.home') }}"},
        },
        {"type": "image", "slot": 4, "options": {"source": "/local/plan.png"}},
        layout="grid_2x3",
    )
    assert missing_data(view, states) == [
        "slot 0: no candles for sensor.price",
        "slot 1: no forecast for weather.home",
        "slot 2: no picture for camera.door",
        "slot 3: no forecast for weather.home",
        "slot 3: no picture for media_player.tv",
        "slot 4: no picture for image source '/local/plan.png'",
    ]


def test_missing_data_leaves_out_what_a_widget_does_not_draw():
    """A weather widget without its forecast strip, or media without art, reads neither."""
    states = States(
        entities={"weather.home": {"state": "sunny"}, "media_player.m": {"state": "playing"}}
    )
    view = _view(
        {
            "type": "weather",
            "slot": 0,
            "entity_id": "weather.home",
            "options": {"show_forecast": False},
        },
        {
            "type": "media",
            "slot": 1,
            "entity_id": "media_player.m",
            "options": {"show_album_art": False},
        },
    )
    assert missing_data(view, states) == []


def test_rendered_templates_reach_their_widget():
    """A label template shows its rendered output, per slot."""
    view = _view(
        {"type": "entity", "slot": 0, "entity_id": "sensor.a", "label": "{{ name }}"},
        layout="fullscreen",
    )
    states = States(entities={"sensor.a": {"state": "1"}})
    raw = render_view(view, states, now=NOW)
    rendered = render_view(
        view, States(entities=states.entities, templates={0: {"{{ name }}": "Kitchen"}}), now=NOW
    )
    assert raw != rendered


# =============================================================================
# Rendering
# =============================================================================


def test_schema_lists_everything():
    schema = view_io.schema()
    assert len(schema["layouts"]["grid_2x2"]["slots"]) == 4
    assert "watchos" in schema["themes"]
    assert set(schema["widgets"]) == set(WIDGET_TYPE_SCHEMAS)
    json.dumps(schema, default=str)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_examples_render_against_the_demo_home(example, caplog):
    """Every example is valid, finds all its data in the demo, and renders cleanly."""
    view = json.loads(example.read_text())
    states = load_states(SKILL / "demo" / "home.json")

    check = validate_view(view)
    assert check.ok, check.errors
    assert check.warnings == []
    assert missing_data(view, states) == []

    with caplog.at_level(logging.WARNING, logger="custom_components.geekmagic"):
        png = render_view(view, states, now=NOW)

    image = Image.open(BytesIO(png))
    assert image.size == (240, 240)
    assert len(image.convert("RGB").getcolors(240 * 240) or []) > 64
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
