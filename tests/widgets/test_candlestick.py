"""Tests for candlestick widget and OHLC aggregation."""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.candlestick import (
    CandlestickWidget,
    aggregate_ohlc,
)
from custom_components.geekmagic.widgets.state import EntityState, WidgetState


@pytest.fixture
def renderer():
    """Create a renderer instance."""
    return Renderer()


@pytest.fixture
def canvas(renderer):
    """Create a canvas for drawing."""
    return renderer.create_canvas()


@pytest.fixture
def rect():
    """Standard widget rectangle."""
    return (10, 10, 110, 110)


@pytest.fixture
def render_context(renderer, canvas, rect):
    """Create a RenderContext for widgets."""
    _, draw = canvas
    return RenderContext(draw, rect, renderer)


class TestAggregateOHLC:
    """Tests for the aggregate_ohlc function."""

    def test_empty_data(self):
        """Empty input returns empty output."""
        assert aggregate_ohlc([], 3600, 10) == []

    def test_single_data_point(self):
        """Single data point creates a flat candle."""
        data = [(1000.0, 50.0)]
        result = aggregate_ohlc(data, 3600, 1)
        assert len(result) == 1
        assert result[0] == (50.0, 50.0, 50.0, 50.0)

    def test_known_ohlc(self):
        """Test with known data that should produce specific OHLC values."""
        # 2 candles, each 3600 seconds (1 hour)
        # end_ts = 7200, start_ts = 7200 - (2 * 3600) = 0
        # Bucket 0: [0, 3600), Bucket 1: [3600, 7200)
        data = [
            (100.0, 10.0),  # bucket 0: open
            (1000.0, 15.0),  # bucket 0
            (2000.0, 8.0),  # bucket 0
            (3500.0, 12.0),  # bucket 0: close
            (3700.0, 20.0),  # bucket 1: open
            (5000.0, 25.0),  # bucket 1: high
            (6000.0, 18.0),  # bucket 1
            (7200.0, 22.0),  # bucket 1: close
        ]
        result = aggregate_ohlc(data, 3600, 2)
        assert len(result) == 2

        # Bucket 0: open=10, high=15, low=8, close=12
        assert result[0] == (10.0, 15.0, 8.0, 12.0)
        # Bucket 1: open=20, high=25, low=18, close=22
        assert result[1] == (20.0, 25.0, 18.0, 22.0)

    def test_empty_bucket_uses_last_close(self):
        """Empty buckets should use the last close price as a flat candle."""
        # 3 candles, each 3600 seconds
        # end_ts = 10800, start_ts = 10800 - (3 * 3600) = 0
        # Bucket 0: [0, 3600), Bucket 1: [3600, 7200), Bucket 2: [7200, 10800)
        data = [
            (100.0, 50.0),  # bucket 0
            (3000.0, 55.0),  # bucket 0
            # bucket 1 is empty
            (7500.0, 60.0),  # bucket 2
            (10800.0, 65.0),  # bucket 2
        ]
        result = aggregate_ohlc(data, 3600, 3)
        assert len(result) == 3

        # Bucket 0
        assert result[0] == (50.0, 55.0, 50.0, 55.0)
        # Bucket 1: flat candle at last close (55.0)
        assert result[1] == (55.0, 55.0, 55.0, 55.0)
        # Bucket 2
        assert result[2] == (60.0, 65.0, 60.0, 65.0)

    def test_constant_price(self):
        """Constant price should produce flat candles."""
        data = [
            (100.0, 42.0),
            (3700.0, 42.0),
            (7200.0, 42.0),
        ]
        result = aggregate_ohlc(data, 3600, 2)
        assert len(result) == 2
        for candle in result:
            assert candle == (42.0, 42.0, 42.0, 42.0)

    def test_data_before_window_seeds_last_close(self):
        """Data before the candle window should seed last_close for empty buckets."""
        # 2 candles, each 3600 seconds
        # end_ts = 7200, start_ts = 7200 - (2 * 3600) = 0
        # Data point at -100 (before window) should seed last_close
        data = [
            (-100.0, 99.0),  # before window
            # bucket 0 is empty
            (3700.0, 50.0),  # bucket 1
            (7200.0, 55.0),  # bucket 1
        ]
        result = aggregate_ohlc(data, 3600, 2)
        assert len(result) == 2
        # Bucket 0: flat at 99.0 (seeded from pre-window data)
        assert result[0] == (99.0, 99.0, 99.0, 99.0)
        # Bucket 1: normal
        assert result[1] == (50.0, 55.0, 50.0, 55.0)

    def test_candle_count_respected(self):
        """Output should have exactly candle_count candles."""
        data = [(float(i * 100), float(i)) for i in range(100)]
        result = aggregate_ohlc(data, 100, 5)
        assert len(result) == 5


class TestCandlestickWidget:
    """Tests for CandlestickWidget configuration."""

    def test_default_config(self):
        """Test default widget configuration."""
        config = WidgetConfig(widget_type="candlestick", slot=0, entity_id="sensor.btc")
        widget = CandlestickWidget(config)
        assert widget.candle_interval == "4 hours"
        assert widget.candle_count == 20
        assert widget.show_value is True
        assert widget.hours == 80  # 4 * 20

    def test_custom_config(self):
        """Test custom widget configuration."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
            options={
                "candle_interval": "1 hour",
                "candle_count": 10,
                "show_value": False,
            },
        )
        widget = CandlestickWidget(config)
        assert widget.candle_interval == "1 hour"
        assert widget.candle_count == 10
        assert widget.show_value is False
        assert widget.hours == 10  # 1 * 10

    def test_daily_interval(self):
        """Test daily interval hours calculation."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
            options={"candle_interval": "1 day", "candle_count": 30},
        )
        widget = CandlestickWidget(config)
        assert widget.hours == 720  # 24 * 30

    def test_interval_seconds(self):
        """Test interval_seconds property."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
            options={"candle_interval": "4 hours"},
        )
        widget = CandlestickWidget(config)
        assert widget.interval_seconds == 14400


class TestCandlestickRendering:
    """Tests for CandlestickDisplay rendering."""

    def test_render_with_data(self, render_context):
        """Test rendering with valid OHLC data."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
        )
        widget = CandlestickWidget(config)

        candle_data = [
            (100.0, 110.0, 95.0, 105.0),  # bullish
            (105.0, 115.0, 100.0, 98.0),  # bearish
            (98.0, 108.0, 90.0, 106.0),  # bullish
        ]

        state = WidgetState(
            entity=EntityState(
                entity_id="sensor.btc",
                state="106.0",
                attributes={"friendly_name": "Bitcoin", "unit_of_measurement": "$"},
            ),
            candlestick_data=candle_data,
            now=datetime.now(tz=UTC),
        )

        component = widget.render(render_context, state)
        # Should not raise
        component.render(render_context, 0, 0, 100, 100)

    def test_render_no_data(self, render_context):
        """Test rendering with no data shows 'No data'."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
        )
        widget = CandlestickWidget(config)

        state = WidgetState(
            entity=EntityState(
                entity_id="sensor.btc",
                state="100.0",
                attributes={"friendly_name": "Bitcoin"},
            ),
            candlestick_data=[],
            now=datetime.now(tz=UTC),
        )

        component = widget.render(render_context, state)
        # Should not raise
        component.render(render_context, 0, 0, 100, 100)

    def test_render_no_entity(self, render_context):
        """Test rendering without entity state."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
            label="BTC",
        )
        widget = CandlestickWidget(config)

        state = WidgetState(
            entity=None,
            candlestick_data=[
                (100.0, 105.0, 95.0, 102.0),
            ],
            now=datetime.now(tz=UTC),
        )

        component = widget.render(render_context, state)
        component.render(render_context, 0, 0, 100, 100)

    def test_render_constant_price(self, render_context):
        """Test rendering with constant price (zero range)."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
        )
        widget = CandlestickWidget(config)

        candle_data = [
            (50.0, 50.0, 50.0, 50.0),
            (50.0, 50.0, 50.0, 50.0),
        ]

        state = WidgetState(
            entity=EntityState(
                entity_id="sensor.btc",
                state="50.0",
                attributes={"friendly_name": "BTC"},
            ),
            candlestick_data=candle_data,
            now=datetime.now(tz=UTC),
        )

        component = widget.render(render_context, state)
        # Should not raise even with zero range
        component.render(render_context, 0, 0, 100, 100)

    def test_show_value_false(self, render_context):
        """Test rendering with show_value disabled."""
        config = WidgetConfig(
            widget_type="candlestick",
            slot=0,
            entity_id="sensor.btc",
            options={"show_value": False},
        )
        widget = CandlestickWidget(config)

        state = WidgetState(
            entity=EntityState(
                entity_id="sensor.btc",
                state="100.0",
                attributes={"friendly_name": "BTC"},
            ),
            candlestick_data=[(100.0, 105.0, 95.0, 102.0)],
            now=datetime.now(tz=UTC),
        )

        component = widget.render(render_context, state)
        assert component.current_value is None  # type: ignore[union-attr]
