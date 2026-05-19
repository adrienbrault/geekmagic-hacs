"""Assemble per-widget WidgetState for a layout from pre-fetched data + hass.

The coordinator and the websocket preview both need to turn a Layout plus
its pre-fetched extras (camera images, chart history, weather forecasts,
…) into a `dict[slot_index, WidgetState]` ready to hand to
`layout.render`. Both call `build_widget_states` here so the per-widget
assembly rules — which widget reads which cache, how clock timezone
overrides work, how additional entities are resolved — live in one place.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from PIL import Image

from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget
from .widgets.chart import ChartWidget
from .widgets.clock import ClockWidget
from .widgets.media import MediaWidget
from .widgets.state import EntityState, WidgetState
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .layouts.base import Layout


@dataclass
class PrefetchedData:
    """All pre-fetched data the widgets on a layout might need.

    Each dict is keyed by entity_id. Widgets that don't find their entity
    in the relevant dict simply render with empty/no data — this is the
    same fallback behaviour the coordinator and websocket both had inline.
    """

    camera_images: dict[str, bytes] = field(default_factory=dict)
    media_images: dict[str, bytes] = field(default_factory=dict)
    chart_history: dict[str, list[float]] = field(default_factory=dict)
    candlestick_data: dict[str, list[tuple[float, float, float, float]]] = field(
        default_factory=dict
    )
    weather_forecasts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def build_widget_states(
    layout: Layout,
    hass: HomeAssistant,
    prefetched: PrefetchedData,
) -> dict[int, WidgetState]:
    """Build a WidgetState for every populated slot in `layout`."""
    states: dict[int, WidgetState] = {}

    tz = getattr(hass.config, "time_zone_obj", None) or UTC
    base_now = datetime.now(tz=tz)

    for slot in layout.slots:
        widget = slot.widget
        if widget is None:
            continue

        primary_entity = _build_primary_entity(hass, widget.config.entity_id)
        additional = _build_additional_entities(hass, widget, widget.config.entity_id)

        history: list[float] = []
        if isinstance(widget, ChartWidget) and widget.config.entity_id:
            history = prefetched.chart_history.get(widget.config.entity_id, [])

        candlestick_data: list[tuple[float, float, float, float]] = []
        if isinstance(widget, CandlestickWidget) and widget.config.entity_id:
            candlestick_data = prefetched.candlestick_data.get(widget.config.entity_id, [])

        image = _load_image_for_widget(widget, prefetched)

        forecast: list[dict[str, Any]] = []
        if isinstance(widget, WeatherWidget) and widget.config.entity_id:
            forecast = prefetched.weather_forecasts.get(widget.config.entity_id, [])

        widget_now = _resolve_widget_now(widget, base_now)

        states[slot.index] = WidgetState(
            entity=primary_entity,
            entities=additional,
            history=history,
            candlestick_data=candlestick_data,
            image=image,
            forecast=forecast,
            now=widget_now,
        )

    return states


def _build_primary_entity(hass: HomeAssistant, entity_id: str | None) -> EntityState | None:
    if not entity_id:
        return None
    ha_state = hass.states.get(entity_id)
    if ha_state is None:
        return None
    return EntityState(
        entity_id=ha_state.entity_id,
        state=ha_state.state,
        attributes=dict(ha_state.attributes),
    )


def _build_additional_entities(
    hass: HomeAssistant, widget, primary_id: str | None
) -> dict[str, EntityState]:
    additional: dict[str, EntityState] = {}
    for eid in widget.get_entities():
        if eid == primary_id:
            continue
        ha_state = hass.states.get(eid)
        if ha_state is None:
            continue
        additional[eid] = EntityState(
            entity_id=ha_state.entity_id,
            state=ha_state.state,
            attributes=dict(ha_state.attributes),
        )
    return additional


def _load_image_for_widget(widget, prefetched: PrefetchedData):
    """Decode pre-fetched bytes into a PIL image for camera/media widgets."""
    entity_id = widget.config.entity_id
    if not entity_id:
        return None
    if isinstance(widget, CameraWidget):
        image_bytes = prefetched.camera_images.get(entity_id)
    elif isinstance(widget, MediaWidget):
        image_bytes = prefetched.media_images.get(entity_id)
    else:
        return None
    if not image_bytes:
        return None
    with contextlib.suppress(Exception):
        return Image.open(BytesIO(image_bytes))
    return None


def _resolve_widget_now(widget, base_now: datetime) -> datetime:
    """Honour ClockWidget's timezone option; otherwise return the base time."""
    if isinstance(widget, ClockWidget) and getattr(widget, "timezone", None):
        with contextlib.suppress(Exception):
            return datetime.now(tz=ZoneInfo(widget.timezone))
    return base_now
