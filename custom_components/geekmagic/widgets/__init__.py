"""Widget components for GeekMagic displays."""

from typing import Any

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

_ALL_WIDGETS: list[type[Widget]] = [
    AttributeListWidget,
    CameraWidget,
    CandlestickWidget,
    ChartWidget,
    ClimateWidget,
    ClockWidget,
    EntityWidget,
    GaugeWidget,
    IconWidget,
    MediaWidget,
    MultiProgressWidget,
    ProgressWidget,
    StatusListWidget,
    StatusWidget,
    TextWidget,
    WeatherWidget,
]

# Built from each widget class's WIDGET_TYPE attribute
WIDGET_CLASSES: dict[str, type[Widget]] = {
    cls.WIDGET_TYPE: cls for cls in _ALL_WIDGETS if cls.WIDGET_TYPE
}

# Built from each widget class's SCHEMA attribute (only widgets exposed to the frontend)
WIDGET_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    cls.WIDGET_TYPE: cls.SCHEMA for cls in _ALL_WIDGETS if cls.WIDGET_TYPE and cls.SCHEMA
}

__all__ = [
    "WIDGET_CLASSES",
    "WIDGET_TYPE_SCHEMAS",
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
