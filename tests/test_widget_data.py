"""The widget-data seam: what widgets declare, and who resolves it.

Two halves, one contract. ``Widget.data_needs`` is how a widget says
what it needs fetched beyond entity state; ``WidgetDataResolver`` is the
only thing that fetches it and the only thing that turns the results
into per-slot ``WidgetState``. Nothing in between asks what class a
widget is, which is what these tests pin.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
