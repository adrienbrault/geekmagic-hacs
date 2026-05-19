"""Tests for the widget_state_builder module."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from PIL import Image

from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.widget_state_builder import (
    PrefetchedData,
    build_widget_states,
)
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.candlestick import CandlestickWidget
from custom_components.geekmagic.widgets.chart import ChartWidget
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.media import MediaWidget
from custom_components.geekmagic.widgets.progress import MultiProgressWidget
from custom_components.geekmagic.widgets.weather import WeatherWidget


def _png_bytes(size: tuple[int, int] = (4, 4)) -> bytes:
    """Tiny in-memory PNG so Image.open works without disk I/O."""
    buf = BytesIO()
    Image.new("RGB", size, color=(1, 2, 3)).save(buf, format="PNG")
    return buf.getvalue()


def _make_hass(states: dict[str, MagicMock] | None = None):
    resolved = states or {}
    hass = MagicMock()
    hass.config.time_zone_obj = None
    hass.states.get = resolved.get
    return hass


def _ha_state(entity_id: str, state: str, attributes: dict | None = None):
    s = MagicMock()
    s.entity_id = entity_id
    s.state = state
    s.attributes = attributes or {}
    return s


class TestBuildWidgetStates:
    def test_empty_layout_returns_empty(self):
        layout = Grid2x2()
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states == {}

    def test_widget_with_no_entity_gets_state_with_none_entity(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states[0].entity is None
        assert states[0].now is not None

    def test_widget_resolves_primary_entity_from_hass(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22", {"unit": "°C"})})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert states[0].entity is not None
        assert states[0].entity.state == "22"

    def test_chart_widget_pulls_history_from_prefetched(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(chart_history={"sensor.temp": [1.0, 2.0, 3.0]}),
        )
        assert states[0].history == [1.0, 2.0, 3.0]

    def test_chart_widget_without_history_gets_empty_list(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert states[0].history == []

    def test_non_chart_widget_ignores_chart_history(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(chart_history={"sensor.temp": [99.0]}),
        )
        assert states[0].history == []

    def test_empty_slot_is_skipped(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        # Slots 1, 2, 3 left empty
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert list(states.keys()) == [0]


class TestImageLoading:
    def test_camera_widget_loads_image_from_camera_cache(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            CameraWidget(WidgetConfig(widget_type="camera", slot=0, entity_id="camera.front")),
        )
        states = build_widget_states(
            layout,
            _make_hass(),
            PrefetchedData(camera_images={"camera.front": _png_bytes()}),
        )
        assert isinstance(states[0].image, Image.Image)

    def test_camera_widget_with_no_cached_bytes_gets_none(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            CameraWidget(WidgetConfig(widget_type="camera", slot=0, entity_id="camera.front")),
        )
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states[0].image is None

    def test_camera_widget_with_corrupt_bytes_gets_none_not_raise(self):
        # Image.open raising should be suppressed
        layout = Grid2x2()
        layout.set_widget(
            0,
            CameraWidget(WidgetConfig(widget_type="camera", slot=0, entity_id="camera.front")),
        )
        states = build_widget_states(
            layout,
            _make_hass(),
            PrefetchedData(camera_images={"camera.front": b"not-an-image"}),
        )
        assert states[0].image is None

    def test_media_widget_loads_image_from_media_cache(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            MediaWidget(WidgetConfig(widget_type="media", slot=0, entity_id="media_player.spk")),
        )
        hass = _make_hass({"media_player.spk": _ha_state("media_player.spk", "playing")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(media_images={"media_player.spk": _png_bytes()}),
        )
        assert isinstance(states[0].image, Image.Image)

    def test_non_image_widget_ignores_caches(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(camera_images={"sensor.temp": _png_bytes()}),
        )
        assert states[0].image is None


class TestForecastAndCandlestick:
    def test_weather_widget_pulls_forecast_from_prefetched(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            WeatherWidget(WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home")),
        )
        hass = _make_hass({"weather.home": _ha_state("weather.home", "sunny")})
        forecast = [{"datetime": "2026-01-01T00:00:00+00:00", "temperature": 20}]
        states = build_widget_states(
            layout, hass, PrefetchedData(weather_forecasts={"weather.home": forecast})
        )
        assert states[0].forecast == forecast

    def test_weather_widget_without_forecast_gets_empty_list(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            WeatherWidget(WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home")),
        )
        hass = _make_hass({"weather.home": _ha_state("weather.home", "sunny")})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert states[0].forecast == []

    def test_candlestick_widget_pulls_data_from_prefetched(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            CandlestickWidget(
                WidgetConfig(widget_type="candlestick", slot=0, entity_id="sensor.btc")
            ),
        )
        hass = _make_hass({"sensor.btc": _ha_state("sensor.btc", "100")})
        candles = [(100.0, 110.0, 90.0, 105.0), (105.0, 115.0, 100.0, 110.0)]
        states = build_widget_states(
            layout, hass, PrefetchedData(candlestick_data={"sensor.btc": candles})
        )
        assert states[0].candlestick_data == candles


class TestClockTimezoneOverride:
    def test_clock_with_timezone_option_overrides_widget_now(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ClockWidget(
                WidgetConfig(widget_type="clock", slot=0, options={"timezone": "Asia/Tokyo"})
            ),
        )
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        # Should be in Tokyo's tz, not the base/UTC
        assert states[0].now.tzinfo == ZoneInfo("Asia/Tokyo")

    def test_clock_without_timezone_uses_base_now(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        # Base time = UTC fallback (no time_zone_obj on mock)
        assert states[0].now.tzinfo is not None

    def test_clock_with_invalid_timezone_falls_back_silently(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ClockWidget(
                WidgetConfig(widget_type="clock", slot=0, options={"timezone": "Not/A/Zone"})
            ),
        )
        # Must not raise — ZoneInfo error is suppressed and base time used
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states[0].now is not None


class TestAdditionalEntities:
    def test_multi_progress_widget_resolves_each_item_entity(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            MultiProgressWidget(
                WidgetConfig(
                    widget_type="multi_progress",
                    slot=0,
                    options={
                        "items": [
                            {"entity_id": "sensor.a", "label": "A"},
                            {"entity_id": "sensor.b", "label": "B"},
                        ]
                    },
                )
            ),
        )
        hass = _make_hass(
            {
                "sensor.a": _ha_state("sensor.a", "1"),
                "sensor.b": _ha_state("sensor.b", "2"),
            }
        )
        states = build_widget_states(layout, hass, PrefetchedData())
        assert set(states[0].entities.keys()) == {"sensor.a", "sensor.b"}
        assert states[0].entities["sensor.a"].state == "1"
        assert states[0].entities["sensor.b"].state == "2"

    def test_additional_entity_missing_in_hass_is_skipped(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            MultiProgressWidget(
                WidgetConfig(
                    widget_type="multi_progress",
                    slot=0,
                    options={
                        "items": [
                            {"entity_id": "sensor.a"},
                            {"entity_id": "sensor.gone"},
                        ]
                    },
                )
            ),
        )
        hass = _make_hass({"sensor.a": _ha_state("sensor.a", "1")})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert set(states[0].entities.keys()) == {"sensor.a"}
