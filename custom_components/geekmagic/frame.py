"""Gather what a frame needs, then render it: one path for device and preview.

A frame is a layout rendered against Home Assistant. Besides ``hass.states``
its widgets read inputs that must be fetched in the event loop before the
executor render: camera snapshots, album art, Image widget pictures, chart
and candlestick history, weather forecasts, what HTML widget templates read
with ``forecast()`` / ``history()`` / ``picture()``, and label templates.

``FrameInputs`` holds those inputs (and what carries over between frames,
such as a forecast's refresh time). ``async_gather`` fetches everything a set
of widgets reads and renders their templates last, in the event loop, with no
await between the templates and the caller's executor hand-off.
``widget_states`` then assembles each widget's ``WidgetState`` in the
executor (``view.assemble_widget_states``), and ``view.render_still``
paints the layout.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import callback
from homeassistant.helpers.network import NoURLAvailableError
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .const import WEATHER_FORECAST_RETRY, WEATHER_FORECAST_TTL
from .entity_images import PictureFetchError, async_fetch_media_art
from .history import fetch_entity_history, resample_history
from .image_decode import decode_image
from .image_source import get_image_cache, is_image_entity
from .templating import WidgetTemplates
from .view import assemble_widget_states, is_media_player
from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget, aggregate_ohlc, extract_timestamped_values
from .widgets.chart import ChartWidget
from .widgets.html import HtmlWidget
from .widgets.image import ImageWidget
from .widgets.media import MediaWidget
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant
    from PIL import Image

    from .layouts.base import Layout
    from .view import PictureKind
    from .widgets.base import Widget
    from .widgets.state import WidgetState

_LOGGER = logging.getLogger(__name__)


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


class ForecastCache:
    """Daily weather forecasts by entity id, shared by every device and the preview.

    Forecasts come from the weather.get_forecasts action (the forecast
    attribute was removed from weather entities in 2024.3). Each call shows
    up in HA's action history, so a forecast is fetched at most once per
    ``WEATHER_FORECAST_TTL`` per entity (``WEATHER_FORECAST_RETRY`` after a
    failure) rather than on every render of every display, or every edit
    in the View Editor (issue #224).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an empty cache."""
        self._hass = hass
        self._forecasts: dict[str, list[dict[str, Any]]] = {}
        # entity_id -> monotonic time before which the forecast is not re-fetched
        self._next_fetch: dict[str, float] = {}
        # entity_id -> the fetch in progress, which concurrent callers share
        self._inflight: dict[str, asyncio.Future[None]] = {}

    async def async_get(self, entity_id: str) -> list[dict[str, Any]] | None:
        """Return the entity's forecast, fetching it when due.

        Between fetches, and after a failed one, the last good forecast is
        served; None until one has been fetched. A caller arriving while the
        entity is being fetched (the panel renders every view's preview at
        once) waits for that fetch instead of getting nothing.
        """
        if (pending := self._inflight.get(entity_id)) is not None:
            await asyncio.shield(pending)
        elif (now := time.monotonic()) >= self._next_fetch.get(entity_id, 0.0):
            future: asyncio.Future[None] = self._hass.loop.create_future()
            self._inflight[entity_id] = future
            try:
                await self._async_fetch(entity_id, now)
            finally:
                del self._inflight[entity_id]
                future.set_result(None)
        return self._forecasts.get(entity_id)

    def invalidate(self) -> None:
        """Make every forecast refetch on its next request."""
        self._next_fetch.clear()

    async def _async_fetch(self, entity_id: str, now: float) -> None:
        # Not loaded yet: don't stamp a retry, fetch as soon as it appears
        state = self._hass.states.get(entity_id)
        if state is None or state.state == STATE_UNAVAILABLE:
            return

        self._next_fetch[entity_id] = now + WEATHER_FORECAST_RETRY
        try:
            response = await self._hass.services.async_call(
                "weather",
                "get_forecasts",
                {"type": "daily"},
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception as e:
            _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, e)
            return

        forecast_response = response.get(entity_id) if isinstance(response, dict) else None
        if not isinstance(forecast_response, dict):
            _LOGGER.debug("No forecast returned for %s", entity_id)
            return

        forecast = forecast_response.get("forecast", [])
        self._forecasts[entity_id] = forecast
        self._next_fetch[entity_id] = now + WEATHER_FORECAST_TTL
        _LOGGER.debug("Fetched %d forecast days for %s", len(forecast), entity_id)


DATA_FORECASTS: HassKey[ForecastCache] = HassKey("geekmagic_forecasts")


def get_forecast_cache(hass: HomeAssistant) -> ForecastCache:
    """The HA-wide forecast cache, created on first use."""
    if (cache := hass.data.get(DATA_FORECASTS)) is None:
        cache = hass.data[DATA_FORECASTS] = ForecastCache(hass)
    return cache


class FrameInputs:
    """What frames read besides ``hass.states``, kept between frames.

    One per owner: each device coordinator keeps its own across refreshes
    (a failed fetch keeps serving the last good input), and every panel
    preview starts from a fresh one.
    """

    def __init__(
        self, hass: HomeAssistant, *, fetch_timeout: float | None = None, quiet: bool = False
    ) -> None:
        """Initialize empty inputs.

        ``fetch_timeout`` bounds each camera snapshot and album-art fetch
        (None: only their own timeouts). ``quiet`` logs failures at DEBUG:
        the panel preview renders every half-edited view, and a picture or
        history it can't load is not worth a WARNING.
        """
        self.hass = hass
        self._fetch_timeout = fetch_timeout
        self._quiet = quiet
        # entity_id -> snapshot bytes of camera widgets / notify entities
        self.camera_images: dict[str, bytes] = {}
        # image entity id -> decoded picture for camera widgets showing an
        # ``image.*`` entity, taken from the HA-wide image cache
        self.entity_images: dict[str, Image.Image] = {}
        # media_player entity_id -> album art bytes
        self.media_images: dict[str, bytes] = {}
        # Entities whose last album-art fetch produced a WARNING (cleared on success)
        self.media_image_warned: set[str] = set()
        # source -> decoded picture for image widgets / notify images, taken
        # from the HA-wide image cache before each render
        self.source_images: dict[str, Image.Image] = {}
        # (entity_id, hours) -> resampled history: two charts of one entity
        # over different periods are different series
        self.chart_history: dict[tuple[str, float], list[float]] = {}
        # (entity_id, interval, count) -> OHLC candles: two candlesticks of one
        # entity over different intervals (or windows) are different series
        self.candlestick_data: dict[
            tuple[str, int, int], list[tuple[float, float, float, float]]
        ] = {}
        self.weather_forecasts: dict[str, list[dict[str, Any]]] = {}
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
        """Fetch the picture of every camera widget's entity.

        Also the entities HTML widgets show with ``picture()``, except media
        players (``async_fetch_media_images``). ``image.*`` entities come
        from the HA-wide image cache, which reads them again only when they
        publish a new picture; any other entity (a camera's snapshot, else
        its ``entity_picture``) is fetched every frame.
        """
        entity_ids: set[str] = set()
        for widget in widgets:
            if isinstance(widget, CameraWidget) and widget.config.entity_id:
                entity_ids.add(widget.config.entity_id)
            elif isinstance(widget, HtmlWidget):
                entity_ids.update(e for e in widget.picture_entities if not is_media_player(e))
        image_entity_ids = {e for e in entity_ids if is_image_entity(e)}

        cache = get_image_cache(self.hass)
        images: dict[str, Image.Image] = {}
        for entity_id in image_entity_ids:
            if (picture := await cache.async_get_entity(entity_id, quiet=self._quiet)) is not None:
                images[entity_id] = picture
        self.entity_images = images

        results = await asyncio.gather(
            *(self._async_fetch_picture(e) for e in entity_ids - image_entity_ids)
        )
        for entity_id, image_data in results:
            if image_data:
                self.camera_images[entity_id] = image_data

    async def _async_fetch_picture(self, entity_id: str) -> tuple[str, bytes | None]:
        try:
            async with asyncio.timeout(self._fetch_timeout):
                return entity_id, await async_fetch_entity_picture(self.hass, entity_id)
        except TimeoutError:
            _LOGGER.debug("Timed out fetching the picture of %s", entity_id)
            return entity_id, None

    async def async_fetch_media_images(self, widgets: Iterable[Widget]) -> None:
        """Fetch the album art of every media widget that draws it.

        Also of the media players HTML widgets show with ``picture()``.
        """
        entity_ids: set[str] = set()
        for widget in widgets:
            if isinstance(widget, MediaWidget):
                if widget.show_album_art and widget.config.entity_id:
                    entity_ids.add(widget.config.entity_id)
            elif isinstance(widget, HtmlWidget):
                entity_ids.update(e for e in widget.picture_entities if is_media_player(e))
        await asyncio.gather(*(self._async_fetch_media_art(e) for e in entity_ids))

    async def _async_fetch_media_art(self, entity_id: str) -> None:
        state = self.hass.states.get(entity_id)
        if state is None:
            return

        entity_picture = state.attributes.get("entity_picture")
        if not entity_picture:
            # No art available — drop cached bytes and reset warn state
            self.media_images.pop(entity_id, None)
            self.media_image_warned.discard(entity_id)
            return

        # Proxied art in-process, other pictures over HTTP
        try:
            async with asyncio.timeout(self._fetch_timeout):
                image_data = await async_fetch_media_art(self.hass, entity_picture)
        except NoURLAvailableError:
            _LOGGER.debug("No base URL available to fetch album art for %s", entity_id)
            return
        except PictureFetchError as e:
            self.media_images.pop(entity_id, None)
            self._log_media_fetch_failure(entity_id, e.url, e.reason)
            return
        except TimeoutError:
            self.media_images.pop(entity_id, None)
            self._log_media_fetch_failure(entity_id, entity_picture, "timed out")
            return
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
        if self._quiet or entity_id in self.media_image_warned:
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
            if (image := await cache.async_get(source, max_age, quiet=self._quiet)) is not None:
                images[source] = image
        self.source_images = images

    async def async_fetch_chart_history(self, widgets: Iterable[Widget]) -> None:
        """Fetch and resample the recorder history of every chart widget.

        Also every ``history()`` series of HTML widgets: one query per
        (entity, hours), however many widgets draw it.
        """
        series: set[tuple[str, float]] = set()
        for widget in widgets:
            if isinstance(widget, ChartWidget) and widget.config.entity_id:
                series.add((widget.config.entity_id, widget.hours))
            elif isinstance(widget, HtmlWidget):
                series.update(widget.history_series)
        if not series or (recorder := self._recorder()) is None:
            return

        now = dt_util.utcnow()
        for entity_id, hours in sorted(series):
            try:
                start_time = now - timedelta(hours=hours)
                history_states = await recorder.async_add_executor_job(
                    fetch_entity_history, self.hass, entity_id, start_time, now
                )
                if not history_states:
                    _LOGGER.debug("No history returned for %s", entity_id)
                    continue
                if values := resample_history(history_states, start_time, now):
                    self.chart_history[entity_id, hours] = values
                    _LOGGER.debug("Fetched %d history points for %s", len(values), entity_id)
                else:
                    _LOGGER.debug("No numeric values in history for %s", entity_id)
            except Exception as e:
                self._log_failure("Failed to fetch history for %s: %s", entity_id, e)

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
                    key = (entity_id, widget.interval_seconds, widget.candle_count)
                    self.candlestick_data[key] = candles
                    _LOGGER.debug("Aggregated %d candles for %s", len(candles), entity_id)
            except Exception as e:
                self._log_failure("Failed to fetch candlestick history for %s: %s", entity_id, e)

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
        """Take the daily forecast of every weather widget that shows one.

        Also of every entity an HTML widget reads with ``forecast()``.
        Forecasts come from the HA-wide ``ForecastCache``: every device and
        the panel preview showing an entity share one fetch per TTL. The
        last forecast an entity had stays until a new one arrives.
        """
        entity_ids: set[str] = set()
        for widget in widgets:
            if isinstance(widget, WeatherWidget):
                if widget.show_forecast and widget.config.entity_id:
                    entity_ids.add(widget.config.entity_id)
            elif isinstance(widget, HtmlWidget):
                entity_ids.update(widget.forecast_entities)
        cache = get_forecast_cache(self.hass)
        for entity_id in entity_ids:
            if (forecast := await cache.async_get(entity_id)) is not None:
                self.weather_forecasts[entity_id] = forecast

    def widget_states(self, layout: Layout) -> dict[int, WidgetState]:
        """Assemble each placed widget's ``WidgetState`` (run in the executor).

        Entities are snapshotted from ``hass.states``; everything else comes
        from the inputs gathered beforehand. Pictures decode here, off the
        event loop. One instant in HA's timezone for every widget.
        """
        return assemble_widget_states(layout, self.hass.states.get, self, dt_util.now())

    def picture(self, entity_id: str, kind: PictureKind) -> Image.Image | None:
        """A fetched picture: an ``image.*`` entity's, else the decoded bytes."""
        if kind == "camera" and is_image_entity(entity_id):
            return self.entity_images.get(entity_id)
        return self.decode_picture(entity_id, kind)

    def decode_picture(self, entity_id: str, kind: str):
        """Decode an entity's fetched picture; log and evict it on failure.

        Same bounded decode as Image widget pictures (``image_source``): a
        byte and a pixel cap, EXIF orientation, one downscale to what the
        panel can show. The decode is eager, so a corrupt or oversized
        picture surfaces here, where it is logged and its bytes dropped.
        """
        cache = self.media_images if kind == "media" else self.camera_images
        image_bytes = cache.get(entity_id)
        if not image_bytes:
            return None
        try:
            return decode_image(image_bytes)
        except Exception as e:
            self._log_failure(
                "Failed to decode %s image for %s (%d bytes): %s",
                kind,
                entity_id,
                len(image_bytes),
                e,
            )
            cache.pop(entity_id, None)
            return None

    def _log_failure(self, msg: str, *args: object) -> None:
        """Log a failed input at WARNING, or at DEBUG for a quiet owner."""
        _LOGGER.log(logging.DEBUG if self._quiet else logging.WARNING, msg, *args)
