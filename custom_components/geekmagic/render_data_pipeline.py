"""Pre-fetch every piece of async data a layout's widgets need before render.

Owns the five caches (camera images, media album art, chart history,
candlestick OHLC, weather forecasts) and the five fetcher methods that
populate them. Single entry point — `prefetch(layout, image_source)` —
hands callers back a `PrefetchedData` ready for `build_widget_states`.

The coordinator (production) and the websocket preview (already passes
its own caches) are the two callers. New pre-fetchable widget types add a
case here; the coordinator's update loop doesn't change.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .history_fetcher import HistoryFetcher
from .widget_state_builder import PrefetchedData
from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget
from .widgets.chart import ChartWidget
from .widgets.media import MediaWidget
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .layouts.base import Layout

_LOGGER = logging.getLogger(__name__)

# 10s upper bound on any single image download — keeps a slow camera or
# stalled media-proxy connection from blocking the whole pre-fetch step.
_IMAGE_FETCH_TIMEOUT = ClientTimeout(total=10)


class RenderDataPipeline:
    """Pre-fetches everything `build_widget_states` will need for a layout."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        # Caches persist across update cycles; widgets that don't repopulate
        # their entry simply see the stale value, matching the original
        # coordinator behaviour. The exception is media album art, which is
        # cleared per-cycle when the entity_picture goes away.
        self._camera_images: dict[str, bytes] = {}
        self._media_images: dict[str, bytes] = {}
        self._chart_history: dict[str, list[float]] = {}
        self._candlestick_data: dict[str, list[tuple[float, float, float, float]]] = {}
        self._weather_forecasts: dict[str, list[dict[str, Any]]] = {}

    # Coordinator surface for entities/callers that want raw cache access
    # (e.g. the camera preview entity reads back a fetched image).

    def get_camera_image(self, entity_id: str) -> bytes | None:
        return self._camera_images.get(entity_id)

    async def prefetch(
        self,
        layout: Layout,
        image_source: str | None = None,
    ) -> PrefetchedData:
        """Run all relevant pre-fetches for `layout`, return the result bundle.

        `image_source` is an optional extra entity id (typically the active
        notification's image) added to the camera/media-image fetch set.
        Each fan-out is gated on the layout actually containing a widget
        of that type, so empty layouts pay no recorder/HTTP cost.
        """
        await self._fetch_camera_and_url_images(layout, image_source)
        await self._fetch_media_images(layout)
        await self._fetch_chart_history(layout)
        await self._fetch_candlestick_history(layout)
        await self._fetch_weather_forecasts(layout)
        return PrefetchedData(
            camera_images=self._camera_images,
            media_images=self._media_images,
            chart_history=self._chart_history,
            candlestick_data=self._candlestick_data,
            weather_forecasts=self._weather_forecasts,
        )

    # --- camera / image / notification ---

    async def _fetch_camera_and_url_images(self, layout: Layout, image_source: str | None) -> None:
        camera_entity_ids: set[str] = set()
        other_entity_ids: set[str] = set()

        for slot in layout.slots:
            if slot.widget and isinstance(slot.widget, CameraWidget):
                entity_id = slot.widget.config.entity_id
                if entity_id:
                    (
                        camera_entity_ids if entity_id.startswith("camera.") else other_entity_ids
                    ).add(entity_id)

        if image_source:
            (camera_entity_ids if image_source.startswith("camera.") else other_entity_ids).add(
                image_source
            )

        # Non-camera entities first — they populate the same cache and may
        # be overwritten if a camera widget has the same id (unlikely).
        for entity_id in other_entity_ids:
            await self._fetch_url_image_to_cache(entity_id)

        from homeassistant.components.camera import async_get_image  # noqa: PLC0415

        for entity_id in camera_entity_ids:
            try:
                image = await async_get_image(self._hass, entity_id)
            except Exception as e:
                _LOGGER.debug("Failed to fetch camera image for %s: %s", entity_id, e)
                continue
            if image and image.content:
                self._camera_images[entity_id] = image.content
                _LOGGER.debug(
                    "Fetched camera image for %s: %d bytes", entity_id, len(image.content)
                )

    async def _fetch_url_image_to_cache(self, source: str) -> None:
        """Fetch entity_picture for an entity (image./media_player./etc.) and cache it."""
        image_url = None
        state = self._hass.states.get(source)
        if state:
            image_url = state.attributes.get("entity_picture")

        if not image_url or not image_url.startswith("/"):
            return

        try:
            base_url = get_url(self._hass)
        except NoURLAvailableError:
            _LOGGER.debug("No base URL available for entity picture fetch")
            return

        full_url = f"{base_url.rstrip('/')}/{image_url.lstrip('/')}"
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(full_url, timeout=_IMAGE_FETCH_TIMEOUT) as response:
                if response.status == 200:
                    image_data = await response.read()
                    self._camera_images[source] = image_data
                    _LOGGER.debug(
                        "Fetched image for notification from %s: %d bytes", source, len(image_data)
                    )
                else:
                    _LOGGER.debug(
                        "Failed to fetch notification image from %s: HTTP %d",
                        source,
                        response.status,
                    )
        except Exception as e:
            _LOGGER.debug("Failed to fetch notification image from %s: %s", source, e)

    # --- media album art ---

    async def _fetch_media_images(self, layout: Layout) -> None:
        media_entity_ids: set[str] = {
            slot.widget.config.entity_id
            for slot in layout.slots
            if slot.widget and isinstance(slot.widget, MediaWidget) and slot.widget.config.entity_id
        }
        if not media_entity_ids:
            return

        for entity_id in media_entity_ids:
            state = self._hass.states.get(entity_id)
            if state is None:
                continue
            entity_picture = state.attributes.get("entity_picture")
            if not entity_picture or not entity_picture.startswith("/"):
                # Clear any cached image if no internal picture available
                self._media_images.pop(entity_id, None)
                continue

            try:
                base_url = get_url(self._hass)
            except NoURLAvailableError:
                continue

            image_url = f"{base_url.rstrip('/')}/{entity_picture.lstrip('/')}"
            session = async_get_clientsession(self._hass)
            try:
                async with session.get(image_url, timeout=_IMAGE_FETCH_TIMEOUT) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        self._media_images[entity_id] = image_data
                        _LOGGER.debug(
                            "Fetched album art for %s: %d bytes", entity_id, len(image_data)
                        )
                    else:
                        _LOGGER.debug(
                            "Failed to fetch album art for %s: HTTP %d",
                            entity_id,
                            response.status,
                        )
            except Exception as e:
                _LOGGER.debug("Failed to fetch album art for %s: %s", entity_id, e)

    # --- chart / candlestick history ---

    async def _fetch_chart_history(self, layout: Layout) -> None:
        widgets: list[tuple[str, ChartWidget]] = []
        for slot in layout.slots:
            if slot.widget and isinstance(slot.widget, ChartWidget):
                entity_id = slot.widget.config.entity_id
                if entity_id:
                    widgets.append((entity_id, slot.widget))
        if not widgets:
            return

        fetcher = HistoryFetcher(self._hass)
        if not fetcher.available:
            return

        for entity_id, widget in widgets:
            values = await fetcher.fetch_numeric(entity_id, widget.hours)
            if values:
                self._chart_history[entity_id] = values
                _LOGGER.debug("Fetched %d history points for %s", len(values), entity_id)

    async def _fetch_candlestick_history(self, layout: Layout) -> None:
        widgets: list[tuple[str, CandlestickWidget]] = []
        for slot in layout.slots:
            if slot.widget and isinstance(slot.widget, CandlestickWidget):
                entity_id = slot.widget.config.entity_id
                if entity_id:
                    widgets.append((entity_id, slot.widget))
        if not widgets:
            return

        fetcher = HistoryFetcher(self._hass)
        if not fetcher.available:
            return

        for entity_id, widget in widgets:
            candles = await fetcher.fetch_ohlc(
                entity_id, widget.hours, widget.interval_seconds, widget.candle_count
            )
            if candles:
                self._candlestick_data[entity_id] = candles
                _LOGGER.debug("Aggregated %d candles for %s", len(candles), entity_id)

    # --- weather forecasts ---

    async def _fetch_weather_forecasts(self, layout: Layout) -> None:
        """Pre-fetch daily forecasts via `weather.get_forecasts` (HA 2024.3+)."""
        weather_entity_ids: set[str] = {
            slot.widget.config.entity_id
            for slot in layout.slots
            if slot.widget
            and isinstance(slot.widget, WeatherWidget)
            and slot.widget.config.entity_id
        }
        if not weather_entity_ids:
            return

        for entity_id in weather_entity_ids:
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
                continue

            forecast_response = response.get(entity_id) if isinstance(response, dict) else None
            if not isinstance(forecast_response, dict):
                continue
            raw_forecast = forecast_response.get("forecast", [])
            # Coerce to list[dict] — HA's response is typed as JsonValueType.
            # We trust the documented shape but defend against an unexpected
            # one rather than letting a stray int/str poison the cache.
            if not isinstance(raw_forecast, list):
                continue
            forecast: list[dict[str, Any]] = [d for d in raw_forecast if isinstance(d, dict)]
            self._weather_forecasts[entity_id] = forecast
            _LOGGER.debug("Fetched %d forecast days for %s", len(forecast), entity_id)
