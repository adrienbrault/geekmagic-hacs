"""Gather what a frame needs, then render it: one path for device and preview.

A frame is a layout rendered against Home Assistant. Besides ``hass.states``
its widgets read inputs that must be fetched in the event loop before the
executor render: camera snapshots, album art, Image widget pictures, chart
and candlestick history, weather forecasts and label templates.

``FrameInputs`` holds those inputs (and what carries over between frames,
such as a forecast's refresh time). ``async_gather`` fetches everything a set
of widgets reads and renders their templates last, in the event loop, with no
await between the templates and the caller's executor hand-off.
``widget_states`` then assembles each widget's ``WidgetState`` in the
executor, and ``render_still`` paints the layout.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import callback
from homeassistant.helpers.network import NoURLAvailableError
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LAYOUT,
    CONF_SCREEN_THEME,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
    LAYOUT_GRID_3X3,
    LAYOUT_HERO,
    LAYOUT_HERO_BL,
    LAYOUT_HERO_BR,
    LAYOUT_HERO_SIMPLE,
    LAYOUT_HERO_TL,
    LAYOUT_HERO_TR,
    LAYOUT_SIDEBAR_LEFT,
    LAYOUT_SIDEBAR_RIGHT,
    LAYOUT_SPLIT_H,
    LAYOUT_SPLIT_H_1_2,
    LAYOUT_SPLIT_H_2_1,
    LAYOUT_SPLIT_V,
    LAYOUT_THREE_COLUMN,
    LAYOUT_THREE_ROW,
    THEME_WATCHOS,
    WEATHER_FORECAST_RETRY,
    WEATHER_FORECAST_TTL,
)
from .entity_images import PictureFetchError, async_fetch_media_art, decode_image
from .history import fetch_entity_history, resample_history
from .image_source import get_image_cache
from .layouts.corner_hero import HeroCornerBL, HeroCornerBR, HeroCornerTL, HeroCornerTR
from .layouts.fullscreen import FullscreenLayout
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from .layouts.hero import HeroLayout
from .layouts.hero_simple import HeroSimpleLayout
from .layouts.sidebar import SidebarLeft, SidebarRight
from .layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from .templating import WidgetTemplates
from .widgets import build_widget
from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget, aggregate_ohlc, extract_timestamped_values
from .widgets.chart import ChartWidget
from .widgets.image import ImageWidget
from .widgets.media import MediaWidget
from .widgets.state import WidgetState, build_entity_states
from .widgets.theme import get_theme
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant
    from PIL import Image

    from .layouts.base import Layout
    from .renderer import Renderer
    from .widgets.base import Widget

_LOGGER = logging.getLogger(__name__)

LAYOUT_CLASSES = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT_H: SplitHorizontal,
    LAYOUT_SPLIT_V: SplitVertical,
    LAYOUT_SPLIT_H_1_2: SplitHorizontal1To2,
    LAYOUT_SPLIT_H_2_1: SplitHorizontal2To1,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
    LAYOUT_THREE_ROW: ThreeRowLayout,
    LAYOUT_FULLSCREEN: FullscreenLayout,
    LAYOUT_HERO_SIMPLE: HeroSimpleLayout,
    LAYOUT_SIDEBAR_LEFT: SidebarLeft,
    LAYOUT_SIDEBAR_RIGHT: SidebarRight,
    LAYOUT_HERO_TL: HeroCornerTL,
    LAYOUT_HERO_TR: HeroCornerTR,
    LAYOUT_HERO_BL: HeroCornerBL,
    LAYOUT_HERO_BR: HeroCornerBR,
}


def build_layout(view_config: dict[str, Any]) -> Layout:
    """Build a view's layout, theme and widgets.

    An unknown layout falls back to a 2x2 grid, a view without a theme gets
    the default one, a view without widgets shows a clock, and widgets
    beyond the layout's slots (or of an unknown type) are left out.
    """
    layout_class = LAYOUT_CLASSES.get(view_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2), Grid2x2)
    layout = layout_class()
    layout.theme = get_theme(view_config.get(CONF_SCREEN_THEME, THEME_WATCHOS))

    widgets_config = view_config.get(CONF_WIDGETS, [])
    if not widgets_config:
        widgets_config = [{"type": "clock", "slot": 0}]

    for widget_config in widgets_config:
        slot = int(widget_config.get("slot", 0))
        if slot >= layout.get_slot_count():
            continue
        widget = build_widget(widget_config)
        if widget is not None:
            layout.set_widget(slot, widget)

    return layout


def layout_widgets(layout: Layout) -> list[Widget]:
    """The widgets placed in a layout, in slot order."""
    return [slot.widget for slot in layout.slots if slot.widget is not None]


def render_still(
    renderer: Renderer, layout: Layout, widget_states: dict[int, WidgetState]
) -> Image.Image:
    """Paint a layout's still frame (blocking: run in the executor)."""
    img, draw = renderer.create_canvas(background=layout.theme.background)
    layout.render(renderer, draw, widget_states)
    return img


async def async_fetch_entity_picture(hass: HomeAssistant, entity_id: str) -> bytes | None:
    """The picture an entity shows: a camera's snapshot, else its ``entity_picture``.

    The one place a widget's entity id becomes picture bytes (camera
    widgets, notification ``image`` entities). Returns None when there is
    no picture; failures are logged at DEBUG.
    """
    if entity_id.startswith("camera."):
        # Lazy: the camera component loads only when a camera is shown.
        from homeassistant.components.camera import async_get_image  # noqa: PLC0415

        try:
            image = await async_get_image(hass, entity_id)
        except Exception as e:
            _LOGGER.debug("Failed to fetch camera image for %s: %s", entity_id, e)
            return None
        _LOGGER.debug("Fetched camera image for %s: %d bytes", entity_id, len(image.content))
        return image.content

    state = hass.states.get(entity_id)
    picture = state.attributes.get("entity_picture") if state else None
    # Only Home Assistant's own pictures (internal paths)
    if not picture or not picture.startswith("/"):
        return None
    try:
        return await async_fetch_media_art(hass, picture)
    except (NoURLAvailableError, PictureFetchError) as e:
        _LOGGER.debug("Failed to fetch the picture of %s: %s", entity_id, e)
        return None


class FrameInputs:
    """What frames read besides ``hass.states``, kept between frames.

    One per owner: each device coordinator keeps its own across refreshes
    (a failed fetch keeps serving the last good input).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize empty inputs."""
        self.hass = hass
        # entity_id -> snapshot bytes of camera widgets / notify entities
        self.camera_images: dict[str, bytes] = {}
        # media_player entity_id -> album art bytes
        self.media_images: dict[str, bytes] = {}
        # Entities whose last album-art fetch produced a WARNING (cleared on success)
        self.media_image_warned: set[str] = set()
        # source -> decoded picture for image widgets / notify images, taken
        # from the HA-wide image cache before each render
        self.source_images: dict[str, Image.Image] = {}
        self.chart_history: dict[str, list[float]] = {}
        self.candlestick_data: dict[str, list[tuple[float, float, float, float]]] = {}
        self.weather_forecasts: dict[str, list[dict[str, Any]]] = {}
        # entity_id -> monotonic time before which the forecast is not re-fetched
        self.weather_forecast_next_fetch: dict[str, float] = {}
        # Label / text templates: compiled once, rendered in the event loop
        # each frame, then read by the executor render (issue #73)
        self.widget_templates = WidgetTemplates(hass)
        self.templates: dict[Widget, dict[str, str]] = {}

    async def async_gather(self, widgets: Iterable[Widget]) -> None:
        """Fetch every input ``widgets`` read, then render their templates.

        The templates render last, synchronously: the caller hands the
        frame to the executor with no await in between, so the widgets it
        renders are exactly those whose templates rendered (#184).
        """
        widgets = list(widgets)
        await self.async_fetch_camera_images(widgets)
        await self.async_fetch_media_images(widgets)
        await self.async_fetch_source_images(widgets)
        await self.async_fetch_chart_history(widgets)
        await self.async_fetch_candlestick_history(widgets)
        await self.async_fetch_weather_forecasts(widgets)
        self.async_render_templates(widgets)

    @callback
    def async_render_templates(self, widgets: Iterable[Widget]) -> None:
        """Render the label / text templates of ``widgets``.

        Home Assistant templates must render in the event loop, and the
        widgets render in the executor — so this runs first and
        ``widget_states`` hands each widget its results.
        """
        rendered: dict[Widget, dict[str, str]] = {}
        for widget in widgets:
            if templates := self.widget_templates.async_render(widget):
                rendered[widget] = templates
        self.templates = rendered

    async def async_fetch_camera_images(self, widgets: Iterable[Widget]) -> None:
        """Fetch the snapshot of every camera widget's entity."""
        entity_ids = {
            widget.config.entity_id
            for widget in widgets
            if isinstance(widget, CameraWidget) and widget.config.entity_id
        }
        for entity_id in entity_ids:
            if image_data := await async_fetch_entity_picture(self.hass, entity_id):
                self.camera_images[entity_id] = image_data

    async def async_fetch_media_images(self, widgets: Iterable[Widget]) -> None:
        """Fetch the album art of every media widget that draws it."""
        entity_ids = {
            widget.config.entity_id
            for widget in widgets
            if isinstance(widget, MediaWidget) and widget.show_album_art and widget.config.entity_id
        }
        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue

            entity_picture = state.attributes.get("entity_picture")
            if not entity_picture:
                # No art available — drop cached bytes and reset warn state
                self.media_images.pop(entity_id, None)
                self.media_image_warned.discard(entity_id)
                continue

            # Proxied art in-process, other pictures over HTTP
            try:
                image_data = await async_fetch_media_art(self.hass, entity_picture)
            except NoURLAvailableError:
                _LOGGER.debug("No base URL available to fetch album art for %s", entity_id)
                continue
            except PictureFetchError as e:
                self.media_images.pop(entity_id, None)
                self._log_media_fetch_failure(entity_id, e.url, e.reason)
                continue
            self.media_images[entity_id] = image_data
            self.media_image_warned.discard(entity_id)
            _LOGGER.debug("Fetched album art for %s: %d bytes", entity_id, len(image_data))

    def _log_media_fetch_failure(self, entity_id: str, url: str, reason: str) -> None:
        """Log an album-art fetch failure WARNING once per entity, then DEBUG.

        On the first failure for an entity since its last success, log at
        WARNING so users notice missing album art without enabling DEBUG.
        Subsequent failures log at DEBUG to avoid spam; a successful fetch
        clears the warned flag.
        """
        if entity_id in self.media_image_warned:
            _LOGGER.debug("Failed to fetch album art for %s from %s: %s", entity_id, url, reason)
            return
        self.media_image_warned.add(entity_id)
        _LOGGER.warning(
            "Failed to fetch album art for %s from %s: %s "
            "(further failures for this entity will be logged at DEBUG)",
            entity_id,
            url,
            reason,
        )

    async def async_fetch_source_images(self, widgets: Iterable[Widget]) -> None:
        """Load the pictures of image widgets (and of a notify URL/path image).

        Each source goes through the HA-wide image cache, which only fetches
        it again once the shortest refresh interval asking for it has passed.
        """
        wanted: dict[str, float] = {}
        for widget in widgets:
            if isinstance(widget, ImageWidget) and widget.source:
                previous = wanted.get(widget.source, widget.refresh_seconds)
                wanted[widget.source] = min(previous, widget.refresh_seconds)

        cache = get_image_cache(self.hass)
        images: dict[str, Image.Image] = {}
        for source, max_age in wanted.items():
            if (image := await cache.async_get(source, max_age)) is not None:
                images[source] = image
        self.source_images = images

    async def async_fetch_chart_history(self, widgets: Iterable[Widget]) -> None:
        """Fetch and resample the recorder history of every chart widget."""
        charts = [
            (widget.config.entity_id, widget)
            for widget in widgets
            if isinstance(widget, ChartWidget) and widget.config.entity_id
        ]
        if not charts or (recorder := self._recorder()) is None:
            return

        now = dt_util.utcnow()
        for entity_id, widget in charts:
            try:
                start_time = now - timedelta(hours=widget.hours)
                history_states = await recorder.async_add_executor_job(
                    fetch_entity_history, self.hass, entity_id, start_time, now
                )
                if not history_states:
                    _LOGGER.debug("No history returned for %s", entity_id)
                    continue
                if values := resample_history(history_states, start_time, now):
                    self.chart_history[entity_id] = values
                    _LOGGER.debug("Fetched %d history points for %s", len(values), entity_id)
                else:
                    _LOGGER.debug("No numeric values in history for %s", entity_id)
            except Exception as e:
                _LOGGER.warning("Failed to fetch history for %s: %s", entity_id, e)

    async def async_fetch_candlestick_history(self, widgets: Iterable[Widget]) -> None:
        """Fetch history and aggregate the OHLC candles of every candlestick widget."""
        charts = [
            (widget.config.entity_id, widget)
            for widget in widgets
            if isinstance(widget, CandlestickWidget) and widget.config.entity_id
        ]
        if not charts or (recorder := self._recorder()) is None:
            return

        now = dt_util.utcnow()
        for entity_id, widget in charts:
            try:
                start_time = now - timedelta(hours=widget.hours)
                history_states = await recorder.async_add_executor_job(
                    fetch_entity_history, self.hass, entity_id, start_time, now
                )
                if not history_states:
                    _LOGGER.debug("No history returned for candlestick %s", entity_id)
                    continue
                timestamped = extract_timestamped_values(history_states)
                if not timestamped:
                    _LOGGER.debug("No numeric timestamped values for %s", entity_id)
                    continue
                candles = aggregate_ohlc(timestamped, widget.interval_seconds, widget.candle_count)
                if candles:
                    self.candlestick_data[entity_id] = candles
                    _LOGGER.debug("Aggregated %d candles for %s", len(candles), entity_id)
            except Exception as e:
                _LOGGER.warning("Failed to fetch candlestick history for %s: %s", entity_id, e)

    def _recorder(self) -> Any:
        """The recorder instance, or None when it isn't loaded."""
        try:
            from homeassistant.components.recorder import get_instance  # noqa: PLC0415
        except ImportError:
            _LOGGER.debug("Recorder not available, charts will show no data")
            return None
        try:
            return get_instance(self.hass)
        except KeyError:
            _LOGGER.debug("Recorder instance not available")
            return None

    async def async_fetch_weather_forecasts(self, widgets: Iterable[Widget]) -> None:
        """Fetch the daily forecast of every weather widget that shows one.

        Uses the weather.get_forecasts action (the forecast attribute was
        removed from weather entities in 2024.3). Each call shows up in HA's
        action history, so the result is cached per entity for
        ``WEATHER_FORECAST_TTL`` (``WEATHER_FORECAST_RETRY`` after a
        failure) rather than re-fetched on every render (issue #224).
        Between fetches the last good forecast keeps being served.
        """
        entity_ids = {
            widget.config.entity_id
            for widget in widgets
            if isinstance(widget, WeatherWidget)
            and widget.show_forecast
            and widget.config.entity_id
        }

        now = time.monotonic()
        for entity_id in entity_ids:
            if now < self.weather_forecast_next_fetch.get(entity_id, 0.0):
                continue

            # Not loaded yet: don't stamp a retry, fetch as soon as it appears
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            self.weather_forecast_next_fetch[entity_id] = now + WEATHER_FORECAST_RETRY
            try:
                response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"type": "daily"},
                    target={"entity_id": entity_id},
                    blocking=True,
                    return_response=True,
                )
            except Exception as e:
                _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, e)
                continue

            forecast_response = response.get(entity_id) if isinstance(response, dict) else None
            if not isinstance(forecast_response, dict):
                _LOGGER.debug("No forecast returned for %s", entity_id)
                continue

            forecast = forecast_response.get("forecast", [])
            self.weather_forecasts[entity_id] = forecast
            self.weather_forecast_next_fetch[entity_id] = now + WEATHER_FORECAST_TTL
            _LOGGER.debug("Fetched %d forecast days for %s", len(forecast), entity_id)

    def widget_states(self, layout: Layout) -> dict[int, WidgetState]:
        """Assemble each placed widget's ``WidgetState`` (run in the executor).

        Entities are snapshotted from ``hass.states``; everything else comes
        from the inputs gathered beforehand. Pictures decode here, off the
        event loop.
        """
        states: dict[int, WidgetState] = {}
        # One instant in HA's timezone for every widget in the frame
        now = dt_util.now()

        for slot in layout.slots:
            widget = slot.widget
            if widget is None:
                continue

            # Snapshot primary + additional entity dependencies
            primary_entity, additional = build_entity_states(self.hass.states.get, widget)
            entity_id = widget.config.entity_id

            history: list[float] = []
            if isinstance(widget, ChartWidget) and entity_id:
                history = self.chart_history.get(entity_id, [])

            candlestick_data: list[tuple[float, float, float, float]] = []
            if isinstance(widget, CandlestickWidget) and entity_id:
                candlestick_data = self.candlestick_data.get(entity_id, [])

            image = None
            if isinstance(widget, CameraWidget) and entity_id:
                image = self.decode_picture(entity_id, "camera")
            elif isinstance(widget, MediaWidget) and entity_id:
                image = self.decode_picture(entity_id, "media")
            elif isinstance(widget, ImageWidget):
                image = self.source_images.get(widget.source)

            forecast: list[dict[str, Any]] = []
            if isinstance(widget, WeatherWidget) and entity_id:
                forecast = self.weather_forecasts.get(entity_id, [])

            states[slot.index] = WidgetState(
                entity=primary_entity,
                entities=additional,
                history=history,
                candlestick_data=candlestick_data,
                image=image,
                forecast=forecast,
                now=now,
                templates=self.templates.get(widget, {}),
            )

        return states

    def decode_picture(self, entity_id: str, kind: str):
        """Decode an entity's fetched picture; log and evict it on failure.

        The decode is eager (``decode_image``), so a corrupt picture surfaces
        here, where it is logged and its bytes dropped.
        """
        cache = self.media_images if kind == "media" else self.camera_images
        image_bytes = cache.get(entity_id)
        if not image_bytes:
            return None
        try:
            return decode_image(image_bytes)
        except Exception as e:
            _LOGGER.warning(
                "Failed to decode %s image for %s (%d bytes): %s",
                kind,
                entity_id,
                len(image_bytes),
                e,
            )
            cache.pop(entity_id, None)
            return None
