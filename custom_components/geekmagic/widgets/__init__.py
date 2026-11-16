"""Widget components for GeekMagic displays."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from .attribute_list import AttributeListWidget
from .base import BrokenWidget, Widget, WidgetConfig
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

_LOGGER = logging.getLogger(__name__)

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


def _stored_color(value: object) -> tuple[int, int, int] | None:
    """A stored widget colour as an RGB tuple, or None when it isn't one.

    The panel saves ``[r, g, b]``, but a view can be hand-edited, imported
    or migrated, so the value may be anything. An unreadable colour is
    dropped — the widget falls back to its theme accent — instead of
    raising: ``build_layout`` calls this once per widget, and one bad
    field must not cost the whole view (never mind the device's setup).
    Channels are clamped so a stored ``300`` cannot emit invalid CSS.
    """
    if not isinstance(value, list | tuple) or len(value) != 3:
        return None
    try:
        red, green, blue = (int(channel) for channel in value)
    except (TypeError, ValueError, OverflowError):
        return None
    return (max(0, min(255, red)), max(0, min(255, green)), max(0, min(255, blue)))


def stored_slot(widget_config: Mapping[str, Any]) -> int | None:
    """A stored widget's slot index, or None when it isn't a whole number.

    A view can be hand-edited, imported or migrated, so the slot may be
    anything. Callers skip a widget whose slot can't be read: one bad
    field must cost that widget, not the whole view (``build_layout`` runs
    once per view at setup, so a raise here failed the device's entry).
    """
    raw = widget_config.get("slot", 0)
    if isinstance(raw, bool):
        return None
    try:
        slot = int(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return slot if slot == raw or isinstance(raw, str) else None


def build_widget(widget_config: Mapping[str, Any]) -> Widget | None:
    """Instantiate a widget from its stored (view/screen) dict.

    The one parser for the dict shape the panel saves, shared by the
    coordinator, the editor preview and the sample renderer so they can't
    read the same view differently. Returns None for unknown types; the
    caller decides whether the slot exists in its layout. A config the
    widget can't be built from yields a BrokenWidget (an error cell). A
    colour that isn't three readable channels is dropped, so the cell keeps
    its theme accent.
    """
    widget_type = str(widget_config.get("type", "text"))
    widget_class = WIDGET_CLASSES.get(widget_type)
    if widget_class is None:
        return None

    entity_id = widget_config.get("entity_id")
    label = widget_config.get("label")
    slot = stored_slot(widget_config)

    config = WidgetConfig(
        widget_type=widget_type,
        slot=slot if slot is not None else 0,
        entity_id=str(entity_id) if entity_id is not None else None,
        label=str(label) if label is not None else None,
        color=_stored_color(widget_config.get("color")),
        options=cast("dict[str, Any]", widget_config.get("options") or {}),
    )
    try:
        return widget_class(config)
    except Exception:
        # A config this widget can't read must cost its own cell, not the
        # whole screen (or the device's update loop).
        _LOGGER.exception("Could not build %s widget for slot %s", widget_type, config.slot)
        return BrokenWidget(config)
