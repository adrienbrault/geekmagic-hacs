"""Widget components for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .attribute_list import AttributeListWidget
from .base import Widget, WidgetConfig
from .camera import CameraWidget
from .candlestick import CandlestickWidget
from .chart import ChartWidget
from .climate import ClimateWidget
from .clock import ClockWidget
from .datetime import DateTimeWidget
from .entity import EntityWidget
from .gauge import GaugeWidget
from .html import HtmlWidget
from .icon import IconWidget
from .image import ImageWidget
from .media import MediaWidget
from .progress import MultiProgressWidget, ProgressWidget
from .status import StatusListWidget, StatusWidget
from .text import TextWidget
from .weather import WeatherWidget

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "WIDGET_CLASSES",
    "WIDGET_TYPE_SCHEMAS",
    "AttributeListWidget",
    "CameraWidget",
    "CandlestickWidget",
    "ChartWidget",
    "ClimateWidget",
    "ClockWidget",
    "DateTimeWidget",
    "EntityWidget",
    "GaugeWidget",
    "HtmlWidget",
    "IconWidget",
    "ImageWidget",
    "MediaWidget",
    "MultiProgressWidget",
    "ProgressWidget",
    "StatusListWidget",
    "StatusWidget",
    "TextWidget",
    "WeatherWidget",
    "Widget",
    "WidgetConfig",
    "build_widget",
]

# All concrete widget classes
_ALL_WIDGETS: list[type[Widget]] = [
    AttributeListWidget,
    CameraWidget,
    CandlestickWidget,
    ChartWidget,
    ClimateWidget,
    ClockWidget,
    DateTimeWidget,
    EntityWidget,
    GaugeWidget,
    HtmlWidget,
    IconWidget,
    ImageWidget,
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


def build_widget(widget_config: Mapping[str, Any]) -> Widget | None:
    """Instantiate a widget from its stored (view/screen) dict.

    The one parser for the dict shape the panel saves, shared by the
    coordinator, the editor preview and the sample renderer so they can't
    read the same view differently. Returns None for unknown types; the
    caller decides whether the slot exists in its layout.
    """
    widget_type = str(widget_config.get("type", "text"))
    widget_class = WIDGET_CLASSES.get(widget_type)
    if widget_class is None:
        return None

    entity_id = widget_config.get("entity_id")
    label = widget_config.get("label")
    raw_color = widget_config.get("color")
    parsed_color: tuple[int, int, int] | None = None
    if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
        parsed_color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))

    return widget_class(
        WidgetConfig(
            widget_type=widget_type,
            slot=int(widget_config.get("slot", 0)),
            entity_id=str(entity_id) if entity_id is not None else None,
            label=str(label) if label is not None else None,
            color=parsed_color,
            options=cast("dict[str, Any]", widget_config.get("options") or {}),
        )
    )
