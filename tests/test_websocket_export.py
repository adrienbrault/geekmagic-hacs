"""``geekmagic/views/export``: a stored view, with the entity data it reads.

The panel's "Copy for AI" hands this to an AI that renders the view
offline (``render_view.py``). The point is parity: the export, written to a
file and rendered by ``view_io`` without Home Assistant, is the panel
preview's PNG byte for byte. And it carries no pictures and no secrets or
locations.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import ServiceCall, SupportsResponse

from custom_components.geekmagic.const import DOMAIN
from custom_components.geekmagic.frame import FrameInputs
from custom_components.geekmagic.store import GeekMagicStore
from custom_components.geekmagic.view import history_series
from custom_components.geekmagic.view_io import load_states, render_view
from custom_components.geekmagic.websocket import async_register_websocket_commands
from custom_components.geekmagic.widgets import build_widget
from custom_components.geekmagic.widgets.candlestick import CandlestickWidget

MANIFEST = json.loads(
    (Path(__file__).parent.parent / "custom_components" / "geekmagic" / "manifest.json").read_text()
)

# Before Paris leaves summer time (2026-10-25 01:00 UTC): "now" is +02:00,
# while the forecast's days after the change are +01:00
FROZEN = "2026-10-24 20:00:00+00:00"
FORECAST = [
    {"datetime": f"2026-10-{day}T22:30:00+00:00", "condition": cond, "temperature": t}
    for day, cond, t in (("24", "sunny", 18), ("25", "rainy", 14), ("26", "cloudy", 12))
]

VIEW: dict[str, Any] = {
    "name": "Everything but pictures",
    "layout": "grid_2x3",
    "theme": "standby",
    "widgets": [
        {
            "type": "entity",
            "slot": 0,
            "entity_id": "sensor.temp",
            "label": "{{ name }} {{ states('sensor.co2') }}",
        },
        {"type": "chart", "slot": 1, "entity_id": "sensor.power", "options": {"period": "6 hours"}},
        {"type": "candlestick", "slot": 2, "entity_id": "sensor.price"},
        {"type": "weather", "slot": 3, "entity_id": "weather.home"},
        {
            "type": "html",
            "slot": 4,
            "options": {
                "html": "<div>{{ states('sensor.temp') }} {{ history('sensor.power', 6) | length }}"
                " {{ forecast('weather.home') | length }}</div>"
            },
        },
        {"type": "clock", "slot": 5},
    ],
}

# Big enough for the forecast strip and its day names
WEATHER_VIEW: dict[str, Any] = {
    "name": "Forecast",
    "layout": "fullscreen",
    "theme": "watchos",
    "widgets": [{"type": "weather", "slot": 0, "entity_id": "weather.home"}],
}

PRIVATE = {
    "access_token": "secret-token",
    "entity_picture": "/api/camera_proxy/camera.x?token=abc",
    "latitude": 48.85,
    "longitude": 2.35,
    "gps_accuracy": 12,
    "refresh_token_id": "x",
}


def _history(entity_id: str, hours: float) -> list[float]:
    return [float(i % 7) + hours for i in range(48)]


def _candles(count: int) -> list[tuple[float, float, float, float]]:
    return [(10.0 + i, 12.0 + i, 9.0 + i, 11.0 + i) for i in range(count)]


@pytest.fixture
async def world(hass, hass_ws_client, freezer):
    """Entities, a forecast service, recorder series, a store and a client."""
    async_register_websocket_commands(hass)
    # Authenticated before the clock moves: tokens don't predate their issue
    client = await hass_ws_client(hass)
    freezer.move_to(FROZEN)
    await hass.config.async_set_time_zone("Europe/Paris")
    hass.states.async_set(
        "sensor.temp",
        "21.5",
        {"friendly_name": "Room", "unit_of_measurement": "°C", **PRIVATE},
    )
    hass.states.async_set("sensor.co2", "612", {"unit_of_measurement": "ppm"})
    hass.states.async_set("sensor.power", "340", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.price", "11", {"unit_of_measurement": "€"})
    hass.states.async_set(
        "weather.home", "sunny", {"temperature": 19, "humidity": 60, "friendly_name": "Home"}
    )

    async def get_forecasts(call: ServiceCall):
        return {"weather.home": {"forecast": FORECAST}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )

    # The recorder can't hand back an exact series: serve one, and keep
    # everything downstream of the fetch real (export, preview alike)
    async def chart_history(self: FrameInputs, widgets: Any) -> None:
        for entity_id, hours in history_series(widgets):
            self.chart_history[entity_id, hours] = _history(entity_id, hours)

    async def candlesticks(self: FrameInputs, widgets: Any) -> None:
        for widget in widgets:
            if isinstance(widget, CandlestickWidget) and widget.config.entity_id:
                key = (widget.config.entity_id, widget.interval_seconds, widget.candle_count)
                self.candlestick_data[key] = _candles(widget.candle_count)

    store = GeekMagicStore(hass)
    hass.data[DOMAIN] = {"store": store}
    with (
        patch.object(FrameInputs, "async_fetch_chart_history", chart_history),
        patch.object(FrameInputs, "async_fetch_candlestick_history", candlesticks),
    ):
        yield store, client


async def _store(store: GeekMagicStore, view: dict[str, Any]) -> str:
    return await store.async_create_view(
        name=view["name"], layout=view["layout"], theme=view["theme"], widgets=view["widgets"]
    )


async def _call(client, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]


async def _export_and_preview(world, view: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    store, client = world
    view_id = await _store(store, view)
    export = (
        await _call(
            client, {"type": "geekmagic/views/export", "view_id": view_id, "include_data": True}
        )
    )["export"]
    preview = await _call(
        client, {"type": "geekmagic/preview/render", "view_config": store.get_view(view_id)}
    )
    return export, base64.b64decode(preview["image"])


async def _render_file(hass, export: dict[str, Any], path: Path) -> bytes:
    """Write the export, load it as a states file, render its view offline."""

    def _render() -> bytes:
        path.write_text(json.dumps(export), encoding="utf-8")
        return render_view(export["view"], load_states(path))

    return await hass.async_add_executor_job(_render)


@pytest.mark.parametrize("view", [VIEW, WEATHER_VIEW], ids=["everything", "forecast"])
async def test_the_export_renders_as_the_preview(hass, world, tmp_path, view):
    """Export, write, load and render offline == geekmagic/preview/render."""
    export, preview_png = await _export_and_preview(world, view)

    offline_png = await _render_file(hass, export, tmp_path / "export.json")

    assert offline_png == preview_png, "the exported view renders differently offline"


async def test_the_timezone_keeps_forecast_days_across_dst(hass, world, tmp_path):
    """With "now"'s UTC offset alone, days after the DST change get the wrong name."""
    export, preview_png = await _export_and_preview(world, WEATHER_VIEW)
    del export["timezone"]

    offset_only = await _render_file(hass, export, tmp_path / "export.json")

    assert offset_only != preview_png


async def test_the_export_carries_what_the_frame_reads(hass, world):
    store, client = world
    view_id = await _store(store, VIEW)

    export = (
        await _call(
            client, {"type": "geekmagic/views/export", "view_id": view_id, "include_data": True}
        )
    )["export"]

    assert export["version"] == 1
    assert export["integration_version"] == MANIFEST["version"]
    assert export["timezone"] == "Europe/Paris"
    assert export["now"] == "2026-10-24T22:00:00+02:00"
    assert export["view"] == VIEW
    assert set(export["entities"]) == {
        "sensor.temp",
        "sensor.co2",
        "sensor.power",
        "sensor.price",
        "weather.home",
    }
    power = export["entities"]["sensor.power"]
    assert power["history"] == {"6": _history("sensor.power", 6.0)}  # chart and history()
    candlestick = build_widget(VIEW["widgets"][2])
    assert isinstance(candlestick, CandlestickWidget)
    candles = _candles(candlestick.candle_count)
    assert export["entities"]["sensor.price"]["candles"] == [list(c) for c in candles]
    assert export["entities"]["weather.home"]["forecast"] == FORECAST
    assert export["templates"] == {"0": {VIEW["widgets"][0]["label"]: "Room 612"}}


async def test_the_export_strips_secrets_pictures_and_locations(hass, world):
    store, client = world
    view_id = await _store(store, VIEW)

    export = (
        await _call(
            client, {"type": "geekmagic/views/export", "view_id": view_id, "include_data": True}
        )
    )["export"]

    attributes = export["entities"]["sensor.temp"]["attributes"]
    assert attributes == {"friendly_name": "Room", "unit_of_measurement": "°C"}
    dumped = json.dumps(export)
    for value in ("secret-token", "camera_proxy", "48.85", "2.35"):
        assert value not in dumped


async def test_the_export_fetches_no_pictures(hass, world, aioclient_mock):
    """Camera snapshots and album art are never fetched, nor exported."""
    hass.states.async_set("camera.door", "idle", {"entity_picture": "/api/camera_proxy/x"})
    hass.states.async_set(
        "media_player.tv", "playing", {"entity_picture": "https://art.example.com/a.jpg"}
    )
    view = {
        "name": "Pictures",
        "layout": "split_vertical",
        "theme": "watchos",
        "widgets": [
            {"type": "camera", "slot": 0, "entity_id": "camera.door"},
            {"type": "media", "slot": 1, "entity_id": "media_player.tv"},
        ],
    }
    store, client = world
    view_id = await _store(store, view)
    snapshot = AsyncMock()

    with patch("homeassistant.components.camera.async_get_image", snapshot):
        export = (
            await _call(
                client,
                {"type": "geekmagic/views/export", "view_id": view_id, "include_data": True},
            )
        )["export"]

    snapshot.assert_not_awaited()
    assert aioclient_mock.call_count == 0
    for entity in export["entities"].values():
        assert "picture" not in entity
        assert "entity_picture" not in entity["attributes"]


async def test_the_view_alone(hass, world):
    """Without data: the view as the panel stores it, minus id and timestamps."""
    store, client = world
    view_id = await _store(store, VIEW)

    result = await _call(client, {"type": "geekmagic/views/export", "view_id": view_id})

    assert result == {"export": VIEW}


async def test_an_unknown_view(hass, world):
    _, client = world
    await client.send_json_auto_id({"type": "geekmagic/views/export", "view_id": "nope"})
    msg = await client.receive_json()
    assert msg["error"]["code"] == "not_found"
