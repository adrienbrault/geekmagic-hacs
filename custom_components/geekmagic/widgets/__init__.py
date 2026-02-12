"""Widget components for GeekMagic displays."""

from .attribute_list import AttributeListWidget
from .base import Widget, WidgetConfig
from .camera import CameraWidget
from .candlestick import CandlestickWidget
from .chart import ChartWidget
from .climate import ClimateWidget
from .clock import ClockWidget
from .entity import EntityWidget
from .gauge import GaugeWidget
from .icon import IconWidget
from .media import MediaWidget
from .progress import MultiProgressWidget, ProgressWidget
from .status import StatusListWidget, StatusWidget
from .text import TextWidget
from .weather import WeatherWidget

__all__ = [
    "AttributeListWidget",
    "CameraWidget",
    "CandlestickWidget",
    "ChartWidget",
    "ClimateWidget",
    "ClockWidget",
    "EntityWidget",
    "GaugeWidget",
    "IconWidget",
    "MediaWidget",
    "MultiProgressWidget",
    "ProgressWidget",
    "StatusListWidget",
    "StatusWidget",
    "TextWidget",
    "WeatherWidget",
    "Widget",
    "WidgetConfig",
]
