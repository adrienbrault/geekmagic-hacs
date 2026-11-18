"""What ``FrameInputs`` fetches for a frame, and what each widget gets of it."""

from __future__ import annotations

import base64
import re
from datetime import timedelta
from io import BytesIO
from unittest.mock import AsyncMock, patch

from homeassistant.components.camera import Image as CameraImage
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.util import dt as dt_util
from PIL import Image

from custom_components.geekmagic.const import SUPERSAMPLE_SCALE
from custom_components.geekmagic.frame import FrameInputs
from custom_components.geekmagic.view import build_layout, layout_widgets
from custom_components.geekmagic.widgets.html import HISTORY_POINTS

POWER = "sensor.power"
WEATHER = "weather.home"
CAMERA = "camera.front_door"
PLAYER = "media_player.den"
ART_URL = "https://art.example.com/cover.png"
FORECAST = [{"datetime": "2026-11-16T12:00:00+00:00", "condition": "sunny", "temperature": 12}]


def _ramp(hours: int) -> list[tuple[str, object]]:
    """One state change per hour over the last ``hours`` hours, rising from 0."""
    start = dt_util.utcnow() - timedelta(hours=hours)
    return [(str(i), start + timedelta(hours=i)) for i in range(hours)]


async def _states(hass, view: dict) -> dict:
    layout = build_layout(view)
    inputs = FrameInputs(hass)
    await inputs.async_gather(layout_widgets(layout))
    return await hass.async_add_executor_job(inputs.widget_states, layout)


async def test_charts_of_one_entity_keep_their_own_period(hass, recorder_history):
    """A 1 hour and a 24 hour chart of one sensor are two different series."""
    recorder_history[POWER] = _ramp(24)
    states = await _states(
        hass,
        {
            "layout": "split_horizontal",
            "widgets": [
                {"type": "chart", "slot": 0, "entity_id": POWER, "options": {"period": "1 hour"}},
                {"type": "chart", "slot": 1, "entity_id": POWER, "options": {"period": "24 hours"}},
            ],
        },
    )

    hour, day = states[0].history, states[1].history
    assert hour
    assert day
    # The last hour sits at the newest value; the day climbs through all of them
    assert min(hour) > min(day)
    assert len(recorder_history["calls"]) == 2


async def test_candlesticks_of_one_entity_keep_their_own_interval(hass, recorder_history):
    """A 1 hour and a 1 day candlestick of one sensor are two different series."""
    recorder_history[POWER] = _ramp(48)
    states = await _states(
        hass,
        {
            "layout": "split_horizontal",
            "widgets": [
                {
                    "type": "candlestick",
                    "slot": 0,
                    "entity_id": POWER,
                    "options": {"candle_interval": "1 hour", "candle_count": 6},
                },
                {
                    "type": "candlestick",
                    "slot": 1,
                    "entity_id": POWER,
                    "options": {"candle_interval": "1 day", "candle_count": 6},
                },
            ],
        },
    )

    hourly, daily = states[0].candlestick_data, states[1].candlestick_data
    assert len(hourly) == len(daily) == 6
    assert hourly != daily


def _html(source: str, slot: int = 0) -> dict:
    return {"type": "html", "slot": slot, "options": {"html": source}}


def _picture_bytes(size: tuple[int, int], fmt: str = "PNG") -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (200, 40, 40)).save(buf, format=fmt)
    return buf.getvalue()


def _data_uri_size(uri: str) -> tuple[int, int]:
    assert uri.startswith("data:image/png;base64,")
    return Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1]))).size


async def test_html_history_shares_the_chart_query(hass, recorder_history):
    """history() reads the Chart widget's resampled series, one query per window."""
    recorder_history[POWER] = _ramp(24)
    states = await _states(
        hass,
        {
            "layout": "grid_2x2",
            "widgets": [
                {"type": "chart", "slot": 0, "entity_id": POWER, "options": {"period": "6 hours"}},
                _html("{{ history('sensor.power', hours=6) }}", slot=1),
                _html("{{ history('sensor.power') }}{{ history('sensor.power', 24) }}", slot=2),
            ],
        },
    )

    assert states[1].histories[POWER, 6.0] == states[0].history
    assert len(states[1].histories[POWER, 6.0]) == HISTORY_POINTS
    assert list(states[2].histories) == [(POWER, 24.0)]
    assert sorted(
        hours for _, start, end in recorder_history["calls"] for hours in [end - start]
    ) == [
        timedelta(hours=6),
        timedelta(hours=24),
    ]


async def test_html_forecast_comes_from_the_shared_cache(hass):
    """forecast() gets the Weather widget's daily forecast, fetched once."""
    calls: list[ServiceCall] = []

    async def get_forecasts(call: ServiceCall):
        calls.append(call)
        return {WEATHER: {"forecast": FORECAST}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    hass.states.async_set(WEATHER, "rainy")

    states = await _states(
        hass,
        {
            "layout": "split_horizontal",
            "widgets": [
                {"type": "weather", "slot": 0, "entity_id": WEATHER},
                _html("{{ forecast('weather.home') }}", slot=1),
            ],
        },
    )

    assert states[1].forecasts == {WEATHER: FORECAST}
    assert len(calls) == 1


async def test_html_pictures_are_fetched_fitted_and_encoded(hass, aioclient_mock):
    """picture() gets a camera snapshot and album art, fitted to the cell."""
    hass.states.async_set(CAMERA, "idle")
    hass.states.async_set(PLAYER, "playing", {"entity_picture": ART_URL})
    aioclient_mock.get(ART_URL, content=_picture_bytes((120, 120)))
    snapshot = AsyncMock(
        return_value=CameraImage("image/jpeg", _picture_bytes((1920, 1080), "JPEG"))
    )

    with patch("homeassistant.components.camera.async_get_image", snapshot):
        states = await _states(
            hass,
            {
                "layout": "grid_2x2",
                "widgets": [
                    _html("{{ picture('camera.front_door') }}{{ picture('media_player.den') }}")
                ],
            },
        )

    pictures = states[0].pictures
    assert set(pictures) == {CAMERA, PLAYER}
    # A 2x2 cell is ~114px: the snapshot keeps just enough to cover it at 2x
    _, y1, _, y2 = build_layout({"layout": "grid_2x2"}).slots[0].rect
    width, height = _data_uri_size(pictures[CAMERA])
    assert height == (y2 - y1) * SUPERSAMPLE_SCALE
    assert width == round(1920 * height / 1080)
    # Smaller than the cell needs: kept as is
    assert _data_uri_size(pictures[PLAYER]) == (120, 120)


async def test_html_non_literal_picture_is_never_fetched(hass):
    """A picture() whose entity id isn't a literal fetches nothing and reads ''."""
    hass.states.async_set(CAMERA, "idle")
    snapshot = AsyncMock(return_value=CameraImage("image/jpeg", _picture_bytes((64, 64), "JPEG")))

    with patch("homeassistant.components.camera.async_get_image", snapshot):
        states = await _states(
            hass,
            {
                "layout": "fullscreen",
                "widgets": [_html("{% set c = 'camera.front_door' %}[{{ picture(c) }}]")],
            },
        )

    snapshot.assert_not_awaited()
    assert states[0].pictures == {}


# --- rain radar --------------------------------------------------------------------

RADAR_INDEX_URL = "https://api.rainviewer.com/public/weather-maps.json"
RADAR_TILE_RE = re.compile(r"^https://tilecache\.example/")
NEWEST_FRAME = 1_736_937_000


def _serve_radar(aioclient_mock) -> None:
    buf = BytesIO()
    Image.new("RGBA", (512, 512), (0, 98, 149, 255)).save(buf, format="PNG")
    basemap = BytesIO()
    Image.new("RGB", (256, 256), (40, 40, 40)).save(basemap, format="PNG")
    index = {
        "host": "https://tilecache.example",
        "radar": {
            "past": [{"time": NEWEST_FRAME - 600 * i, "path": f"/v2/radar/p{i}"} for i in range(13)]
        },
    }
    aioclient_mock.get(RADAR_INDEX_URL, json=index)
    aioclient_mock.get(RADAR_TILE_RE, content=buf.getvalue())
    aioclient_mock.get(
        re.compile(r"^https://server\.arcgisonline\.com/"), content=basemap.getvalue()
    )


def _tile_urls(aioclient_mock) -> list[str]:
    return [str(c[1]) for c in aioclient_mock.mock_calls if RADAR_TILE_RE.match(str(c[1]))]


async def test_radar_location_comes_from_home(hass, aioclient_mock):
    hass.config.latitude, hass.config.longitude = 50.0, 8.0
    _serve_radar(aioclient_mock)
    states = await _states(hass, {"layout": "fullscreen", "widgets": [{"type": "radar"}]})
    cell = states[0].radar
    assert cell is not None
    assert len(cell.frames) == 7
    assert cell.base_uri is not None
    assert all("/512/7/50.0/8.0/" in url for url in _tile_urls(aioclient_mock))


async def test_radar_location_override(hass, aioclient_mock):
    hass.config.latitude, hass.config.longitude = 50.0, 8.0
    _serve_radar(aioclient_mock)
    widget = {
        "type": "radar",
        "options": {"latitude": 45.0, "longitude": 10.0, "zoom": "Wide", "period": "1 hour"},
    }
    states = await _states(hass, {"layout": "fullscreen", "widgets": [widget]})
    assert states[0].radar is not None
    urls = _tile_urls(aioclient_mock)
    assert len(urls) == 4
    assert all("/512/5/45.0/10.0/" in url for url in urls)


async def test_radar_without_a_location_fetches_nothing(hass, aioclient_mock):
    hass.config.latitude, hass.config.longitude = 0.0, 0.0
    states = await _states(hass, {"layout": "fullscreen", "widgets": [{"type": "radar"}]})
    assert states[0].radar is None
    assert aioclient_mock.call_count == 0


async def test_two_radar_widgets_share_one_fetch(hass, aioclient_mock):
    hass.config.latitude, hass.config.longitude = 50.0, 8.0
    _serve_radar(aioclient_mock)
    states = await _states(
        hass,
        {
            "layout": "split_horizontal",
            "widgets": [
                {"type": "radar", "slot": 0},
                {"type": "radar", "slot": 1, "options": {"period": "1 hour"}},
            ],
        },
    )
    assert states[0].radar is not None
    assert states[1].radar is not None
    assert len(_tile_urls(aioclient_mock)) == 7
    indexes = [c for c in aioclient_mock.mock_calls if str(c[1]) == RADAR_INDEX_URL]
    assert len(indexes) == 1


async def test_failing_radar_fetch_costs_only_the_radar(hass):
    hass.config.latitude, hass.config.longitude = 50.0, 8.0
    with patch(
        "custom_components.geekmagic.frame.get_radar_cache", side_effect=RuntimeError("boom")
    ):
        states = await _states(
            hass,
            {
                "layout": "split_horizontal",
                "widgets": [{"type": "radar", "slot": 0}, {"type": "clock", "slot": 1}],
            },
        )
    assert states[0].radar is None
    assert 1 in states


async def test_still_radar_fetches_only_the_newest_frame(hass, aioclient_mock):
    hass.config.latitude, hass.config.longitude = 50.0, 8.0
    _serve_radar(aioclient_mock)
    widget = {"type": "radar", "options": {"animate": False}}
    states = await _states(hass, {"layout": "fullscreen", "widgets": [widget]})
    assert states[0].radar is not None
    assert len(states[0].radar.frames) == 1
    assert len(_tile_urls(aioclient_mock)) == 1
