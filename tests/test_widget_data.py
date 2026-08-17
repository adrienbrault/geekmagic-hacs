"""The widget-data seam: what widgets declare, and who resolves it.

Two halves, one contract. ``Widget.data_needs`` is how a widget says
what it needs fetched beyond entity state; ``WidgetDataResolver`` is the
only thing that fetches it and the only thing that turns the results
into per-slot ``WidgetState``. Nothing in between asks what class a
widget is, which is what these tests pin.
"""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import SupportsResponse
from homeassistant.util import dt as dt_util

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
    THEME_WATCHOS,
)
from custom_components.geekmagic.views import build_layout
from custom_components.geekmagic.widget_data import WidgetDataResolver
from custom_components.geekmagic.widgets import WIDGET_CLASSES
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.candlestick import CandlestickWidget
from custom_components.geekmagic.widgets.chart import ChartWidget
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.media import MediaWidget
from custom_components.geekmagic.widgets.state import CandleSpec, DataNeeds
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.weather import WeatherWidget

NOTHING = DataNeeds()


def config(widget_type: str, entity_id: str | None = None, **options) -> WidgetConfig:
    """A widget config with the given entity and options."""
    return WidgetConfig(widget_type=widget_type, slot=0, entity_id=entity_id, options=options)


class TestDefaultNeeds:
    """Most widgets render from entity state alone."""

    def test_text_widget_needs_nothing(self):
        assert TextWidget(config("text", options={"text": "hi"})).data_needs() == NOTHING

    def test_clock_widget_needs_nothing(self):
        assert ClockWidget(config("clock")).data_needs() == NOTHING

    def test_every_registered_widget_declares_needs(self):
        """The base default keeps new widgets working without an override."""
        for widget_type, widget_class in WIDGET_CLASSES.items():
            needs = widget_class(config(widget_type, entity_id="sensor.x")).data_needs()
            assert isinstance(needs, DataNeeds), widget_type


class TestChartNeeds:
    """A chart asks for history over its configured period."""

    def test_named_period_resolves_to_hours(self):
        widget = ChartWidget(config("chart", "sensor.power", period="6 hours"))
        assert widget.data_needs() == DataNeeds(history_hours=6)

    def test_sub_hour_period_keeps_its_fraction(self):
        widget = ChartWidget(config("chart", "sensor.power", period="5 min"))
        assert widget.data_needs().history_hours == 5 / 60

    def test_numeric_period_is_read_as_minutes(self):
        """The panel can store a raw minute count instead of a label."""
        widget = ChartWidget(config("chart", "sensor.power", period=30))
        assert widget.data_needs().history_hours == 0.5

    def test_hours_option_is_honoured(self):
        widget = ChartWidget(config("chart", "sensor.power", hours=12))
        assert widget.data_needs().history_hours == 12

    def test_default_period_is_a_day(self):
        widget = ChartWidget(config("chart", "sensor.power"))
        assert widget.data_needs().history_hours == 24

    def test_without_an_entity_nothing_is_needed(self):
        assert ChartWidget(config("chart", period="6 hours")).data_needs() == NOTHING


class TestCandlestickNeeds:
    """A candlestick asks for an aggregation, not a series."""

    def test_spec_is_built_from_the_widget_options(self):
        widget = CandlestickWidget(
            config("candlestick", "sensor.btc", candle_interval="1 hour", candle_count=12)
        )
        assert widget.data_needs() == DataNeeds(
            candles=CandleSpec(hours=12, interval_seconds=3600, count=12)
        )

    def test_default_spec_covers_twenty_four_hour_candles(self):
        needs = CandlestickWidget(config("candlestick", "sensor.btc")).data_needs()
        assert needs.candles == CandleSpec(hours=80, interval_seconds=14400, count=20)

    def test_daily_interval_widens_the_window(self):
        needs = CandlestickWidget(
            config("candlestick", "sensor.btc", candle_interval="1 day", candle_count=5)
        ).data_needs()
        assert needs.candles == CandleSpec(hours=120, interval_seconds=86400, count=5)

    def test_without_an_entity_nothing_is_needed(self):
        assert CandlestickWidget(config("candlestick")).data_needs() == NOTHING


class TestImageNeeds:
    """Camera frames and album art are the same need."""

    def test_camera_declares_its_entity_as_the_image_source(self):
        widget = CameraWidget(config("camera", "camera.front_door"))
        assert widget.data_needs() == DataNeeds(image_source="camera.front_door")

    def test_camera_without_an_entity_needs_nothing(self):
        assert CameraWidget(config("camera")).data_needs() == NOTHING

    def test_media_declares_its_entity_as_the_image_source(self):
        widget = MediaWidget(config("media", "media_player.living"))
        assert widget.data_needs() == DataNeeds(image_source="media_player.living")

    def test_media_declares_art_even_when_hidden(self):
        """``show_album_art`` is a layout choice, not a fetch gate."""
        widget = MediaWidget(config("media", "media_player.living", show_album_art=False))
        assert widget.data_needs().image_source == "media_player.living"

    def test_media_without_an_entity_needs_nothing(self):
        assert MediaWidget(config("media")).data_needs() == NOTHING


class TestForecastNeeds:
    """The daily forecast is a service call."""

    def test_weather_asks_for_a_forecast(self):
        assert WeatherWidget(config("weather", "weather.home")).data_needs() == DataNeeds(
            forecast=True
        )

    def test_weather_without_an_entity_needs_nothing(self):
        assert WeatherWidget(config("weather")).data_needs() == NOTHING


# ----------------------------------------------------------------------
# Resolver: one prefetch per layout, one state per slot
# ----------------------------------------------------------------------


class FakeRecorder:
    """Stands in for the recorder instance: records queries, returns canned states."""

    def __init__(self, states_by_entity: dict[str, list]) -> None:
        self._states = states_by_entity
        self.queries: list[tuple[str, datetime, datetime]] = []

    async def async_add_executor_job(self, _func, _hass, entity_id, start, end):
        """Record the window that was asked for and answer from the canned states."""
        self.queries.append((entity_id, start, end))
        return self._states.get(entity_id, [])


@dataclass
class FakeState:
    """A recorder row: a value and when it changed."""

    state: str
    last_changed: datetime


def series(entity_id: str, hours: float, values: list[float]) -> dict[str, list[FakeState]]:
    """Canned recorder rows spread evenly over the last ``hours``."""
    end = dt_util.utcnow()
    step = timedelta(hours=hours) / max(1, len(values))
    return {
        entity_id: [
            FakeState(str(value), end - timedelta(hours=hours) + step * (i + 0.5))
            for i, value in enumerate(values)
        ]
    }


def view(*widgets: dict) -> Any:
    """Build a runtime layout from widget dicts, the way a stored view does."""
    return build_layout(
        {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: list(widgets)},
        default_theme=THEME_WATCHOS,
    )


@pytest.fixture
def no_recorder(monkeypatch: pytest.MonkeyPatch):
    """Fail the test if anything reaches for the recorder."""
    import homeassistant.components.recorder as recorder_module

    def _boom(_hass):
        raise AssertionError("recorder must not be consulted")

    monkeypatch.setattr(recorder_module, "get_instance", _boom)


def use_recorder(monkeypatch: pytest.MonkeyPatch, states: dict[str, list]) -> FakeRecorder:
    """Install a fake recorder instance and return it for inspection."""
    import homeassistant.components.recorder as recorder_module

    fake = FakeRecorder(states)
    monkeypatch.setattr(recorder_module, "get_instance", lambda _hass: fake)
    return fake


def use_forecast(hass, response: Any) -> list[Any]:
    """Answer ``weather.get_forecasts`` with ``response``; return the recorded calls."""
    calls: list[Any] = []

    async def _handle(call):
        calls.append(call)
        return response

    hass.services.async_register(
        "weather", "get_forecasts", _handle, supports_response=SupportsResponse.ONLY
    )
    return calls


class TestPrefetch:
    """Phase one: gather every declared need and fetch it once."""

    async def test_history_reaches_the_right_slot(self, hass, monkeypatch):
        layout = view(
            {"type": "clock", "slot": 0},
            {
                "type": "chart",
                "slot": 1,
                "entity_id": "sensor.power",
                "options": {"period": "6 hours"},
            },
        )
        use_recorder(monkeypatch, series("sensor.power", 6, [1.0, 2.0, 3.0, 4.0]))

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)
        states = resolver.build_states(layout)

        assert states[1].has_history()
        assert states[0].history == []

    async def test_chart_period_sizes_the_recorder_window(self, hass, monkeypatch):
        """The window comes from the widget, so the preview can't invent its own."""
        layout = view(
            {
                "type": "chart",
                "slot": 0,
                "entity_id": "sensor.power",
                "options": {"period": "5 min"},
            }
        )
        recorder = use_recorder(monkeypatch, {})

        await WidgetDataResolver(hass).async_prefetch(layout)

        entity_id, start, end = recorder.queries[0]
        assert entity_id == "sensor.power"
        assert (end - start).total_seconds() == pytest.approx(300, abs=1)

    async def test_numeric_period_sizes_the_recorder_window(self, hass, monkeypatch):
        """A raw minute count is a period too — the widget already knew that."""
        layout = view(
            {"type": "chart", "slot": 0, "entity_id": "sensor.power", "options": {"period": 30}}
        )
        recorder = use_recorder(monkeypatch, {})

        await WidgetDataResolver(hass).async_prefetch(layout)

        _entity_id, start, end = recorder.queries[0]
        assert (end - start).total_seconds() == pytest.approx(1800, abs=1)

    async def test_candles_reach_the_right_slot(self, hass, monkeypatch):
        layout = view(
            {
                "type": "candlestick",
                "slot": 2,
                "entity_id": "sensor.btc",
                "options": {"candle_interval": "1 hour", "candle_count": 4},
            }
        )
        use_recorder(monkeypatch, series("sensor.btc", 4, [10.0, 12.0, 9.0, 11.0]))

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)
        states = resolver.build_states(layout)

        assert len(states[2].candlestick_data) == 4
        assert all(len(candle) == 4 for candle in states[2].candlestick_data)

    async def test_candle_spec_sizes_the_recorder_window(self, hass, monkeypatch):
        layout = view(
            {
                "type": "candlestick",
                "slot": 0,
                "entity_id": "sensor.btc",
                "options": {"candle_interval": "1 day", "candle_count": 3},
            }
        )
        recorder = use_recorder(monkeypatch, {})

        await WidgetDataResolver(hass).async_prefetch(layout)

        _entity_id, start, end = recorder.queries[0]
        assert (end - start).total_seconds() == pytest.approx(3 * 86400, abs=1)

    async def test_forecast_reaches_the_right_slot(self, hass, monkeypatch):
        layout = view({"type": "weather", "slot": 3, "entity_id": "weather.home"})
        forecast = [{"datetime": "2024-01-01", "temperature": 5}]
        calls = use_forecast(hass, {"weather.home": {"forecast": forecast}})

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)
        states = resolver.build_states(layout)

        assert states[3].forecast == forecast
        assert len(calls) == 1
        assert calls[0].data["type"] == "daily"

    async def test_unusable_forecast_response_leaves_no_data(self, hass, monkeypatch):
        layout = view({"type": "weather", "slot": 0, "entity_id": "weather.home"})
        use_forecast(hass, {})

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)

        assert resolver.build_states(layout)[0].forecast == []

    async def test_forecast_failure_leaves_the_widget_empty(self, hass):
        """A raising weather service costs the forecast, not the screen."""
        layout = view({"type": "weather", "slot": 0, "entity_id": "weather.home"})

        async def _boom(_call):
            raise RuntimeError("no forecast for you")

        hass.services.async_register(
            "weather", "get_forecasts", _boom, supports_response=SupportsResponse.ONLY
        )

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)

        assert resolver.build_states(layout)[0].forecast == []

    async def test_one_pass_serves_a_mixed_screen(self, hass, monkeypatch):
        """Chart, candlestick, weather and clock resolved from one prefetch."""
        layout = view(
            {"type": "chart", "slot": 0, "entity_id": "sensor.power"},
            {
                "type": "candlestick",
                "slot": 1,
                "entity_id": "sensor.btc",
                "options": {"candle_interval": "1 hour", "candle_count": 3},
            },
            {"type": "weather", "slot": 2, "entity_id": "weather.home"},
            {"type": "clock", "slot": 3},
        )
        use_recorder(
            monkeypatch,
            series("sensor.power", 24, [1.0, 2.0, 3.0]) | series("sensor.btc", 3, [5.0, 6.0, 7.0]),
        )
        use_forecast(hass, {"weather.home": {"forecast": [{"temperature": 1}]}})

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)
        states = resolver.build_states(layout)

        assert set(states) == {0, 1, 2, 3}
        assert states[0].has_history()
        assert states[1].candlestick_data
        assert states[2].forecast
        assert states[3].now is not None

    async def test_layout_without_needs_fetches_nothing(self, hass, no_recorder):
        """A screen of clocks and text costs no recorder query and no service call."""
        layout = view(
            {"type": "clock", "slot": 0},
            {"type": "text", "slot": 1, "options": {"text": "hi"}},
        )
        calls = use_forecast(hass, {})

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)

        assert calls == []
        assert resolver.build_states(layout)[0].history == []

    async def test_recorder_absence_is_not_an_error(self, hass):
        """No recorder configured → the chart renders empty, nothing raises."""
        layout = view({"type": "chart", "slot": 0, "entity_id": "sensor.power"})

        resolver = WidgetDataResolver(hass)
        await resolver.async_prefetch(layout)

        assert resolver.build_states(layout)[0].history == []


class TestBuildStates:
    """Phase two: one state per occupied slot, executor-safe."""

    def test_entities_are_snapshotted_per_slot(self, hass):
        hass.states.async_set("sensor.temp", "21.5", {"friendly_name": "Room"})
        layout = view({"type": "entity", "slot": 2, "entity_id": "sensor.temp"})

        states = WidgetDataResolver(hass).build_states(layout)

        assert set(states) == {2}
        assert states[2].entity is not None
        assert states[2].entity.state == "21.5"

    def test_empty_slots_are_omitted(self, hass):
        layout = view({"type": "clock", "slot": 0})
        assert set(WidgetDataResolver(hass).build_states(layout)) == {0}

    def test_states_without_a_prefetch_are_entity_only(self, hass):
        """Valid to skip phase one — widgets fall back to their empty states."""
        layout = view({"type": "chart", "slot": 0, "entity_id": "sensor.power"})

        state = WidgetDataResolver(hass).build_states(layout)[0]

        assert state.history == []
        assert state.candlestick_data == []
        assert state.image is None
        assert state.forecast == []

    def test_now_defaults_to_home_assistant_time(self, hass):
        layout = view({"type": "clock", "slot": 0})
        now = WidgetDataResolver(hass).build_states(layout)[0].now
        assert now is not None
        assert now.tzinfo is not None

    def test_explicit_now_is_handed_to_every_widget(self, hass):
        moment = datetime(2024, 6, 1, 8, 30, tzinfo=UTC)
        layout = view({"type": "clock", "slot": 0}, {"type": "clock", "slot": 1})

        states = WidgetDataResolver(hass).build_states(layout, now=moment)

        assert states[0].now == moment
        assert states[1].now == moment
