"""Widget components for GeekMagic displays."""

from .base import Widget, WidgetConfig
from .clock import ClockWidget
from .entity import EntityWidget
from .media import MediaWidget
from .chart import ChartWidget
from .text import TextWidget

__all__ = [
    "Widget",
    "WidgetConfig",
    "ClockWidget",
    "EntityWidget",
    "MediaWidget",
    "ChartWidget",
    "TextWidget",
]
