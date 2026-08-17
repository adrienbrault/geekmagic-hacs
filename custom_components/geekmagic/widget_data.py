"""The seam between "what a screen needs" and "what a widget renders".

Rendering a screen happens in two phases, because Home Assistant runs on
asyncio and Pillow/Blitz do not: everything that touches the event loop
(recorder queries, camera frames, HTTP fetches, service calls) has to
happen first, and the render itself runs in an executor thread from
whatever those phases produced.

``WidgetDataResolver`` owns both phases for every caller. It asks each
placed widget what it needs (``Widget.data_needs``), fetches exactly
that once, and hands back a ``WidgetState`` per slot. It never asks what
class a widget is — the four fields of ``DataNeeds`` are the whole
vocabulary — so a new widget that needs history is an edit to the
widget alone.

Both render paths use it: the coordinator's device render and the
websocket preview of an unsaved edit. They used to carry separate
implementations (the preview's read widget options off raw view dicts,
with its own period table), which is how the editor could show a chart
the device would never draw.

Caches live for the lifetime of the resolver and are keyed by entity id.
A failed fetch leaves the previous value in place: a screen that
rendered a minute ago should keep rendering through a recorder hiccup
rather than blanking. The two exceptions are deliberate — a media
player that has stopped publishing ``entity_picture`` has genuinely no
art, and bytes that fail to decode are worse than nothing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any, cast

from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.util import dt as dt_util
from PIL import Image

from .history import extract_timestamped_values, resample_history
from .widgets.candlestick import aggregate_ohlc
from .widgets.state import WidgetState, build_entity_states

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .layouts.base import Layout
    from .widgets.base import Widget
    from .widgets.state import CandleSpec, DataNeeds

_LOGGER = logging.getLogger(__name__)

# How long any single image fetch may take.
_IMAGE_TIMEOUT = ClientTimeout(total=10)


def _state_changes(hass: HomeAssistant, entity_id: str, start: datetime, end: datetime) -> list:
    """Fetch one entity's recorder history (sync, runs in the recorder's executor).

    Wrapped rather than called directly because ``async_add_executor_job``
    passes positional arguments only, while ``state_changes_during_period``
    needs keywords to reach the options we care about.
    """
    from homeassistant.components.recorder import history

    result = history.state_changes_during_period(
        hass,
        start,
        end,
        entity_id,
        include_start_time_state=True,
        no_attributes=True,
    )
    return result.get(entity_id, [])


class WidgetDataResolver:
    """Gathers every placed widget's needs, fetches once, builds the states.

    Two phases, matching the two threads a render spans:

    - ``async_prefetch`` runs in the event loop and fills the caches.
    - ``build_states`` is sync and executor-safe: entity snapshots,
      cache lookups, image decode.

    Call them in that order for the same layout. Calling ``build_states``
    without a prefetch is valid and yields entity-only states — that is
    what a widget with no declared needs gets anyway.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the resolver against a Home Assistant instance."""
        self._hass = hass
        self._history: dict[str, list[float]] = {}
        self._candles: dict[str, list[tuple[float, float, float, float]]] = {}
        self._images: dict[str, bytes] = {}
        # Entities whose last image fetch produced a WARNING (cleared on success)
        self._image_warned: set[str] = set()
        self._forecasts: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Phase 1 — event loop
    # ------------------------------------------------------------------

    async def async_prefetch(self, layout: Layout) -> None:
        """Fetch everything the layout's widgets declared they need.

        A layout whose widgets declare nothing costs nothing: no recorder
        query, no service call, no HTTP request.
        """
        placed = [
            (slot.widget, slot.widget.data_needs())
            for slot in layout.slots
            if slot.widget is not None
        ]

        await self._fetch_images(_unique(n.image_source for _, n in placed if n.image_source))
        await self._fetch_history(_by_entity(placed, lambda n: n.history_hours))
        await self._fetch_candles(_by_entity(placed, lambda n: n.candles))
        await self._fetch_forecasts(
            _unique(w.config.entity_id for w, n in placed if n.forecast and w.config.entity_id)
        )

    # -- images --------------------------------------------------------

    async def _fetch_images(self, sources: list[str]) -> None:
        """Fetch a camera frame or an ``entity_picture`` per image source."""
        for source in sources:
            if source.startswith("camera."):
                await self._fetch_camera_frame(source)
            else:
                await self._fetch_entity_picture(source)

    async def _fetch_camera_frame(self, entity_id: str) -> None:
        """Grab a still from a camera entity, keeping the last frame on failure."""
        from homeassistant.components.camera import async_get_image

        try:
            image = await async_get_image(self._hass, entity_id)
            if image and image.content:
                self._images[entity_id] = image.content
                _LOGGER.debug(
                    "Fetched camera image for %s: %d bytes", entity_id, len(image.content)
                )
        except Exception as e:
            _LOGGER.debug("Failed to fetch camera image for %s: %s", entity_id, e)

    async def _fetch_entity_picture(self, entity_id: str) -> None:
        """Download the entity's ``entity_picture`` (album art, snapshots, ...).

        Some integrations (Music Assistant, certain Spotify/Sonos configs)
        expose ``entity_picture`` as a full http(s):// URL — those are
        fetched directly. Internal paths like ``/api/media_player_proxy/...``
        are joined with the configured HA base URL.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return

        picture = state.attributes.get("entity_picture")
        if not picture:
            # No art available — drop cached bytes and reset warn state
            self._images.pop(entity_id, None)
            self._image_warned.discard(entity_id)
            return

        if picture.startswith(("http://", "https://")):
            image_url = picture
        elif picture.startswith("/"):
            try:
                base_url = get_url(self._hass)
            except NoURLAvailableError:
                _LOGGER.debug("No base URL available to fetch image for %s", entity_id)
                return
            image_url = f"{base_url.rstrip('/')}/{picture.lstrip('/')}"
        else:
            self._images.pop(entity_id, None)
            self._warn_image_failure(
                entity_id,
                picture,
                f"unsupported entity_picture scheme: {picture[:40]!r}",
            )
            return

        try:
            # Use Home Assistant's managed session so media proxy requests
            # carry the right auth/cookies.
            session = async_get_clientsession(self._hass)
            async with session.get(image_url, timeout=_IMAGE_TIMEOUT) as response:
                if response.status == 200:
                    self._images[entity_id] = await response.read()
                    self._image_warned.discard(entity_id)
                    _LOGGER.debug(
                        "Fetched image for %s: %d bytes", entity_id, len(self._images[entity_id])
                    )
                else:
                    self._images.pop(entity_id, None)
                    self._warn_image_failure(entity_id, image_url, f"HTTP {response.status}")
        except Exception as e:
            self._images.pop(entity_id, None)
            self._warn_image_failure(entity_id, image_url, str(e) or type(e).__name__)

    def _warn_image_failure(self, entity_id: str, url: str, reason: str) -> None:
        """Log an image fetch failure WARNING once per entity, then DEBUG.

        On the first failure for an entity since its last success, log at
        WARNING so users notice missing art without enabling DEBUG.
        Subsequent failures for the same entity log at DEBUG to avoid
        spam; a successful fetch re-arms the warning.
        """
        if entity_id in self._image_warned:
            _LOGGER.debug("Failed to fetch image for %s from %s: %s", entity_id, url, reason)
            return
        self._image_warned.add(entity_id)
        _LOGGER.warning(
            "Failed to fetch image for %s from %s: %s "
            "(further failures for this entity will be logged at DEBUG)",
            entity_id,
            url,
            reason,
        )

    # -- recorder history ----------------------------------------------

    def _recorder(self) -> Any | None:
        """Return the recorder instance, or None when it isn't available."""
        try:
            from homeassistant.components.recorder import get_instance
        except ImportError:
            _LOGGER.debug("Recorder not available, history widgets will show no data")
            return None

        try:
            return get_instance(self._hass)
        except KeyError:
            _LOGGER.debug("Recorder instance not available")
            return None

    async def _fetch_history(self, requests: list[tuple[str, float]]) -> None:
        """Resample each request's window into an evenly spaced series."""
        if not requests:
            return
        recorder = self._recorder()
        if recorder is None:
            return

        now = dt_util.utcnow()
        for entity_id, hours in requests:
            try:
                start_time = now - timedelta(hours=hours)
                history_states = await recorder.async_add_executor_job(
                    _state_changes, self._hass, entity_id, start_time, now
                )

                if history_states:
                    values = resample_history(history_states, start_time, now)
                    if values:
                        self._history[entity_id] = values
                        _LOGGER.debug("Fetched %d history points for %s", len(values), entity_id)
                    else:
                        _LOGGER.debug("No numeric values in history for %s", entity_id)
                else:
                    _LOGGER.debug("No history returned for %s", entity_id)
            except Exception as e:
                _LOGGER.warning("Failed to fetch history for %s: %s", entity_id, e)

    async def _fetch_candles(self, requests: list[tuple[str, CandleSpec]]) -> None:
        """Aggregate each request's window into OHLC candles."""
        if not requests:
            return
        recorder = self._recorder()
        if recorder is None:
            return

        now = dt_util.utcnow()
        for entity_id, spec in requests:
            try:
                start_time = now - timedelta(hours=spec.hours)
                history_states = await recorder.async_add_executor_job(
                    _state_changes, self._hass, entity_id, start_time, now
                )

                if history_states:
                    timestamped = extract_timestamped_values(history_states)
                    if timestamped:
                        candles = aggregate_ohlc(timestamped, spec.interval_seconds, spec.count)
                        if candles:
                            self._candles[entity_id] = candles
                            _LOGGER.debug("Aggregated %d candles for %s", len(candles), entity_id)
                    else:
                        _LOGGER.debug("No numeric timestamped values for %s", entity_id)
                else:
                    _LOGGER.debug("No history returned for candlestick %s", entity_id)
            except Exception as e:
                _LOGGER.warning("Failed to fetch candlestick history for %s: %s", entity_id, e)

    # -- forecasts -----------------------------------------------------

    async def _fetch_forecasts(self, entity_ids: list[str]) -> None:
        """Call ``weather.get_forecasts`` (daily) for each weather entity.

        The service exists because the ``forecast`` attribute was removed
        from weather entities in HA 2024.3 — there is nothing to read off
        the state.
        """
        for entity_id in entity_ids:
            try:
                response = await self._hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"type": "daily"},
                    target={"entity_id": entity_id},
                    blocking=True,
                    return_response=True,
                )

                forecast_response = response.get(entity_id) if isinstance(response, dict) else None
                if isinstance(forecast_response, dict):
                    raw = forecast_response.get("forecast", [])
                    # The response is JSON: assert the shape once, here,
                    # rather than leaving every weather cell to guess.
                    forecast = cast("list[dict[str, Any]]", raw if isinstance(raw, list) else [])
                    self._forecasts[entity_id] = forecast
                    _LOGGER.debug("Fetched %d forecast days for %s", len(forecast), entity_id)
            except Exception as e:
                _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, e)

    # ------------------------------------------------------------------
    # Phase 2 — executor
    # ------------------------------------------------------------------

    def build_states(
        self, layout: Layout, *, now: datetime | None = None
    ) -> dict[int, WidgetState]:
        """Build the ``WidgetState`` for every occupied slot in the layout.

        Sync and side-effect-free apart from evicting undecodable image
        bytes, so it is safe to call from the render executor.

        Args:
            layout: The layout being rendered.
            now: The instant to hand every widget. Defaults to now in
                Home Assistant's configured timezone; widgets that care
                about a different zone (the clock) convert it themselves.

        Returns:
            Slot index → state. Empty slots are omitted.
        """
        moment = now or datetime.now(tz=getattr(self._hass.config, "time_zone_obj", None) or UTC)

        states: dict[int, WidgetState] = {}
        for slot in layout.slots:
            widget = slot.widget
            if widget is None:
                continue

            primary_entity, additional = build_entity_states(self._hass.states.get, widget)
            needs = widget.data_needs()
            entity_id = widget.config.entity_id

            states[slot.index] = WidgetState(
                entity=primary_entity,
                entities=additional,
                history=self._history.get(entity_id, [])
                if needs.history_hours is not None and entity_id
                else [],
                candlestick_data=self._candles.get(entity_id, [])
                if needs.candles is not None and entity_id
                else [],
                image=self._decode_image(needs.image_source) if needs.image_source else None,
                forecast=self._forecasts.get(entity_id, []) if needs.forecast and entity_id else [],
                now=moment,
            )

        return states

    def _decode_image(self, source: str) -> Image.Image | None:
        """Decode this source's cached bytes; log and evict on failure.

        ``Image.open`` is lazy and only reads the header — the actual
        decode happens later (in widget render code) where there is no
        logging hook and a corrupt image silently downgrades to a text
        fallback. Forcing the decode here surfaces the error where it can
        be logged and drops the bad bytes from the cache.
        """
        image_bytes = self._images.get(source)
        if not image_bytes:
            return None

        try:
            decoded = Image.open(BytesIO(image_bytes))
            decoded.load()
        except Exception as e:
            _LOGGER.warning(
                "Failed to decode image for %s (%d bytes): %s", source, len(image_bytes), e
            )
            self._images.pop(source, None)
            return None
        else:
            return decoded


def _unique(values: Any) -> list[str]:
    """De-duplicate an iterable of ids, keeping first-seen order."""
    return list(dict.fromkeys(values))


def _by_entity(
    placed: list[tuple[Widget, DataNeeds]],
    pick: Any,
) -> list[tuple[str, Any]]:
    """Pair each widget's entity id with the need ``pick`` selects, when both exist.

    Later widgets win on a repeated entity id — two charts on the same
    sensor with different periods share one cache slot, as they always
    have.
    """
    return [
        (widget.config.entity_id, pick(needs))
        for widget, needs in placed
        if widget.config.entity_id and pick(needs) is not None
    ]
