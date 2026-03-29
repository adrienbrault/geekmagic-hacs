"""Widget components for GeekMagic displays."""

from __future__ import annotations

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

# All concrete widget classes
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

# Widget type string -> widget class mapping (derived from WIDGET_TYPE class attribute)
WIDGET_CLASSES: dict[str, type[Widget]] = {
    cls.WIDGET_TYPE: cls for cls in _ALL_WIDGETS if cls.WIDGET_TYPE
}

# Widget type string -> UI schema mapping (only widgets that define a SCHEMA)
WIDGET_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    cls.WIDGET_TYPE: cls.SCHEMA for cls in _ALL_WIDGETS if cls.WIDGET_TYPE and cls.SCHEMA
}
