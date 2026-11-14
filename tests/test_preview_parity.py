"""The panel preview shows exactly the frame the device is sent.

Each case renders one view config twice, against the same Home Assistant
states: once through the device update cycle (``_async_update_data``, whose
PNG is the frame it uploaded) and once through ``geekmagic/preview/render``.
Renders are deterministic (#230), so the two PNGs must be byte-identical.

Every input a frame reads beyond ``hass.states`` is covered: a camera
snapshot, album art, an Image widget picture, a weather forecast and a label
template. The camera fetch is mocked at HA's camera API and the pictures are
served over HTTP, below anything the integration owns, so the test holds
whichever code path gathers them.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import websocket_api
from homeassistant.components.camera import Image as CameraImage
from homeassistant.core import ServiceCall, SupportsResponse
from PIL import Image

from custom_components.geekmagic.const import (
    CONF_DISPLAY_ROTATION,
    CONF_ENABLE_ANIMATIONS,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.websocket import ws_preview_render

CAMERA = "camera.front_door"
PLAYER = "media_player.living_room"
ART_URL = "https://art.example.com/cover.png"
PICTURE_URL = "https://pictures.example.com/garden.png"
WEATHER = "weather.home"
SENSOR = "sensor.bird"
FORECAST = [
    {"datetime": "2026-11-15T12:00:00+00:00", "condition": "rainy", "temperature": 9, "templow": 3},
    {"datetime": "2026-11-16T12:00:00+00:00", "condition": "sunny", "temperature": 12},
    {"datetime": "2026-11-17T12:00:00+00:00", "condition": "cloudy", "temperature": 10},
]


def _picture(size: tuple[int, int], fmt: str) -> bytes:
    """A gradient, so a resampling or decode difference changes pixels."""
    width, height = size
    image = Image.new("RGB", size)
    image.putdata(
        [(x * 255 // width, y * 255 // height, 128) for y in range(height) for x in range(width)]
    )
    buf = BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


CAMERA_JPEG = _picture((640, 360), "JPEG")
ART_PNG = _picture((300, 300), "PNG")
PICTURE_PNG = _picture((200, 120), "PNG")

CAMERA_WIDGET = {"type": "camera", "slot": 0, "entity_id": CAMERA, "options": {"show_label": True}}
MEDIA_WIDGET = {"type": "media", "slot": 0, "entity_id": PLAYER}
IMAGE_WIDGET = {"type": "image", "slot": 0, "options": {"source": PICTURE_URL}}
WEATHER_WIDGET = {"type": "weather", "slot": 0, "entity_id": WEATHER}
TEMPLATE_WIDGET = {
    "type": "entity",
    "slot": 0,
    "entity_id": SENSOR,
    "label": "{{ states('" + SENSOR + "') | upper }}",
}


def _at(widget: dict[str, Any], slot: int) -> dict[str, Any]:
    return {**widget, "slot": slot}


CASES: dict[str, dict[str, Any]] = {
    "camera": {"layout": "fullscreen", "theme": "watchos", "widgets": [CAMERA_WIDGET]},
    "media": {"layout": "fullscreen", "theme": "watchos", "widgets": [MEDIA_WIDGET]},
    "image": {"layout": "fullscreen", "theme": "watchos", "widgets": [IMAGE_WIDGET]},
    "weather": {"layout": "fullscreen", "theme": "watchos", "widgets": [WEATHER_WIDGET]},
    "template": {"layout": "fullscreen", "theme": "standby", "widgets": [TEMPLATE_WIDGET]},
    "all": {
        "layout": "grid_2x3",
        "theme": "watchos",
        "widgets": [
            _at(CAMERA_WIDGET, 0),
            _at(MEDIA_WIDGET, 1),
            _at(IMAGE_WIDGET, 2),
            _at(WEATHER_WIDGET, 3),
            _at(TEMPLATE_WIDGET, 4),
        ],
    },
    # A view without a theme gets the device's default theme
    "default_theme": {"layout": "fullscreen", "widgets": [TEMPLATE_WIDGET]},
    # A view without widgets shows the device's default clock
    "empty": {"layout": "fullscreen", "theme": "watchos", "widgets": []},
}

# What the preview got wrong before it shared the device's frame pipeline
FAILED_BEFORE = {"camera", "all", "default_theme", "empty"}


@pytest.fixture
def world(hass, aioclient_mock):
    """Real HA states plus the pictures and forecast behind them."""
    hass.states.async_set(CAMERA, "idle", {"friendly_name": "Front Door"})
    hass.states.async_set(
        PLAYER,
        "playing",
        {
            "friendly_name": "Living Room",
            "media_title": "Blue in Green",
            "media_artist": "Miles Davis",
            "entity_picture": ART_URL,
        },
    )
    hass.states.async_set(
        WEATHER,
        "rainy",
        {"friendly_name": "Home", "temperature": 8.5, "humidity": 81, "temperature_unit": "°C"},
    )
    hass.states.async_set(SENSOR, "great tit", {"friendly_name": "Bird"})
    aioclient_mock.get(ART_URL, content=ART_PNG)
    aioclient_mock.get(PICTURE_URL, content=PICTURE_PNG)

    forecast_calls: list[ServiceCall] = []

    async def get_forecasts(call: ServiceCall):
        forecast_calls.append(call)
        return {WEATHER: {"forecast": FORECAST}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    camera_image = AsyncMock(return_value=CameraImage("image/jpeg", CAMERA_JPEG))
    with patch("homeassistant.components.camera.async_get_image", camera_image):
        yield {
            "camera": lambda: camera_image.await_count,
            "media": lambda: sum(str(call[1]) == ART_URL for call in aioclient_mock.mock_calls),
            "image": lambda: sum(str(call[1]) == PICTURE_URL for call in aioclient_mock.mock_calls),
            "weather": lambda: len(forecast_calls),
        }


def _device() -> MagicMock:
    device = MagicMock()
    device.host = "192.168.1.100"
    device.model = "unknown"
    device.capabilities.brightness_range = (0, 100)
    device.display_rendered_dashboard = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=None)
    device.is_builtin_theme = MagicMock(return_value=False)
    return device


async def _device_frame(hass, view_config: dict[str, Any]) -> bytes:
    """The PNG of the frame one device update cycle uploads."""
    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_DISPLAY_ROTATION: 0,
        CONF_ENABLE_ANIMATIONS: False,
        CONF_SCREENS: [{"name": "Parity", **view_config}],
    }
    device = _device()
    coordinator = GeekMagicCoordinator(hass, device, options)
    result = await coordinator._async_update_data()
    assert result["uploaded"], result
    device.display_rendered_dashboard.assert_awaited_once()
    assert coordinator.last_image is not None
    return coordinator.last_image


async def _preview_frame(client, view_config: dict[str, Any]) -> bytes:
    await client.send_json(
        {"id": 1, "type": "geekmagic/preview/render", "view_config": view_config}
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    return base64.b64decode(msg["result"]["image"])


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            name,
            marks=pytest.mark.xfail(strict=True, reason="preview drifted from the device")
            if name in FAILED_BEFORE
            else (),
        )
        for name in CASES
    ],
)
async def test_preview_matches_device_frame(hass, hass_ws_client, freezer, world, case):
    """The editor preview and the uploaded frame are the same PNG."""
    websocket_api.async_register_command(hass, ws_preview_render)
    client = await hass_ws_client(hass)
    # ``freezer`` holds one instant for both renders: clocks, "now", history
    view_config = CASES[case]

    device_png = await _device_frame(hass, view_config)
    # The device frame really drew each fetched input: matching a preview
    # that also lacks it would prove nothing.
    for widget in view_config["widgets"]:
        if (fetched := world.get(widget["type"])) is not None:
            assert fetched() >= 1, f"device frame never fetched its {widget['type']} input"
    preview_png = await _preview_frame(client, view_config)

    assert preview_png == device_png, "the preview differs from the frame sent to the device"
