"""Quick visual test for the candlestick widget."""

from datetime import UTC, datetime

from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.candlestick import CandlestickWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState

renderer = Renderer()
img, draw = renderer.create_canvas()
rect = (0, 0, 240, 240)
ctx = RenderContext(draw, rect, renderer)

widget = CandlestickWidget(
    WidgetConfig(
        widget_type="candlestick",
        slot=0,
        entity_id="sensor.btc",
        label="BTC/USD:",
        options={"candle_count": 25},
    )
)

# Simulated BTC-like price action — realistic downtrend from ~71k to ~68k
candles = [
    (71200, 71650, 70900, 71400),
    (71400, 71800, 71100, 71600),
    (71600, 71700, 70800, 70900),
    (70900, 71300, 70600, 71100),
    (71100, 71500, 70700, 70800),
    (70800, 71200, 70500, 71000),
    (71000, 71400, 70200, 70400),
    (70400, 70800, 69800, 70100),
    (70100, 70600, 69700, 70300),
    (70300, 70500, 69500, 69700),
    (69700, 70200, 69400, 70000),
    (70000, 70300, 69200, 69400),
    (69400, 69900, 69100, 69600),
    (69600, 69800, 68800, 69000),
    (69000, 69500, 68600, 69200),
    (69200, 69400, 68500, 68700),
    (68700, 69300, 68400, 69100),
    (69100, 69200, 68200, 68400),
    (68400, 68900, 68100, 68600),
    (68600, 68800, 67800, 68000),
    (68000, 68500, 67600, 68300),
    (68300, 68400, 67400, 67600),
    (67600, 68200, 67300, 68000),
    (68000, 68300, 67500, 67700),
    (67700, 68100, 67400, 67928),
]

state = WidgetState(
    entity=EntityState(
        "sensor.btc",
        "67928.0",
        {"friendly_name": "BTC/USD:", "unit_of_measurement": "$"},
    ),
    candlestick_data=candles,
    now=datetime.now(tz=UTC),
)

component = widget.render(ctx, state)
component.render(ctx, 0, 0, 240, 240)

img.save("candlestick_preview.png")
img.save("samples/candlestick_example.png")
print("Saved candlestick_preview.png and samples/candlestick_example.png")
