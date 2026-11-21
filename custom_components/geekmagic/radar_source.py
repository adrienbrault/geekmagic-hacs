"""Fetch and cache what the Rain Radar widget shows: RainViewer frames and an Esri basemap.

One cache per Home Assistant instance (``get_radar_cache``), shared by
every device coordinator and the panel preview, so N displays (and every
preview) showing one location fetch it once.

- The RainViewer index (``weather-maps.json``) lists the last two hours
  of frames, 10 minutes apart, under rotating paths. It is refetched once
  its newest frame is ``INDEX_STALE_AFTER`` old (a new frame is due),
  never more often than ``INDEX_MIN_INTERVAL``, and ``INDEX_RETRY`` after
  a failure. A tile answering 410 (its path rotated out) refetches the
  index once.
- Radar tiles never change once published: each is fetched once, kept as
  raw bytes, and dropped when its path leaves the index. They are
  requested at the location rounded to 0.1° (the exact home location
  never leaves Home Assistant); the crop is shifted so home stays centred.
- The basemap (Esri dark gray canvas, base under the radar and place
  names over it) is stitched once per location and zoom, in the executor,
  and kept in memory; a failure is retried after ``BASEMAP_RETRY``. Esri
  only ever sees tile indices.

Nothing is written to disk. Nothing here raises: a failure keeps serving
what was fetched before (or nothing), and is logged at WARNING once, then
at DEBUG until a fetch succeeds again (always DEBUG for the preview).
Each location refreshes in a background task, and callers wait for it at
most their deadline: a slow server never holds a frame back longer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.hass_dict import HassKey

from .radar_tiles import (
    REGION_PX,
    RadarSnapshot,
    basemap_cover,
    clamp_zoom,
    home_offset,
    parse_index,
    radar_tile_url,
    rounded_location,
    select_frames,
    stitch_basemap,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from PIL import Image

_LOGGER = logging.getLogger(__name__)

INDEX_URL = "https://api.rainviewer.com/public/weather-maps.json"
ESRI_TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{layer}/MapServer/tile/{z}/{y}/{x}"
)
BASE_LAYER = "World_Dark_Gray_Base"
LABELS_LAYER = "World_Dark_Gray_Reference"

# Largest body accepted (index or tile); real radar tiles are under 110 KB.
MAX_BODY_BYTES = 512 * 1024
# Upper bound, in seconds, for one request (callers wait less: see async_get)
FETCH_TIMEOUT = 20
# A new frame is published every 600 s; the index is stale once its newest
# frame is this old.
INDEX_STALE_AFTER = 660
INDEX_MIN_INTERVAL = 120
INDEX_RETRY = 60
TILE_RETRY = 60
BASEMAP_RETRY = 5 * 60
# Locations nothing asked for in this long are dropped. Beyond
# MAX_LOCATIONS, the least recently used IDLE ones go too (the preview feeds
# every half-typed coordinate) — never one refreshing, nor one asked for in
# the last IN_USE_SECONDS (a display showing it), so a busy cache can't
# thrash or evict what a device shows.
UNUSED_EVICT_SECONDS = 15 * 60
IN_USE_SECONDS = 5 * 60
MAX_LOCATIONS = 8
# How long a caller waits for a refresh when it gives no deadline; with a
# snapshot already in hand it waits at most CACHED_WAIT and shows that.
DEFAULT_WAIT = 10.0
CACHED_WAIT = 1.0

DATA_RADAR: HassKey[RadarCache] = HassKey("geekmagic_radar")


def _monotonic() -> float:
    return time.monotonic()


def _wall() -> float:
    return time.time()


class RadarFetchError(Exception):
    """A request that returned no usable body."""


class RadarGoneError(RadarFetchError):
    """HTTP 410: the frame's path left RainViewer's index."""


# (lat, lon, radar zoom) of a requested location, lat/lon to 4 decimals
_LocationKey = tuple[float, float, int]
# (frame path, rounded lat, rounded lon, zoom)
_TileKey = tuple[str, float, float, int]


@dataclass
class _Location:
    last_used: float = 0.0
    max_count: int = 1
    base: Image.Image | None = None
    labels: Image.Image | None = None
    basemap_retry_at: float = 0.0
    task: asyncio.Task[None] | None = None
    # Failures of the running refresh log at DEBUG only while every caller
    # waiting on it is quiet (the panel preview)
    quiet: bool = False
    # frame count -> (what it was built from, the snapshot)
    snapshots: dict[int, tuple[tuple, RadarSnapshot]] = field(default_factory=dict)

    @property
    def refreshing(self) -> bool:
        return self.task is not None and not self.task.done()


class RadarCache:
    """RainViewer index, radar tiles and basemaps, shared by every display."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an empty cache."""
        self._hass = hass
        self._index: tuple[str, list[tuple[int, str]]] | None = None
        self._index_fetched_at: float | None = None
        self._index_retry_at = 0.0
        self._index_lock = asyncio.Lock()
        self._tiles: dict[_TileKey, bytes] = {}
        self._tile_retry_at: dict[_TileKey, float] = {}
        self._locations: dict[_LocationKey, _Location] = {}
        self._warned: set[str] = set()

    # --- public -------------------------------------------------------------

    async def async_get(
        self,
        lat: float,
        lon: float,
        zoom: int,
        count: int,
        *,
        wait: float | None = None,
        quiet: bool = False,
    ) -> RadarSnapshot | None:
        """The latest snapshot of ``count`` frames around lat/lon, or None.

        Starts (or joins) the location's refresh when something is due and
        waits for it at most ``wait`` seconds — at most ``CACHED_WAIT``
        when a snapshot is already cached, so a hung server never stalls a
        display that has something to show. Past that, what is cached is
        returned and the refresh carries on in the background. The same
        snapshot object is returned while nothing changed. Never raises.
        """
        try:
            zoom = clamp_zoom(zoom)
            key: _LocationKey = (round(lat, 4), round(lon, 4), zoom)
            now = _monotonic()
            loc = self._locations.get(key)
            if loc is None:
                loc = self._locations[key] = _Location()
            loc.last_used = now
            loc.max_count = max(loc.max_count, count)
            if loc.refreshing:
                loc.quiet = loc.quiet and quiet
            elif self._refresh_due(key, loc, now):
                loc.quiet = quiet
                loc.task = self._hass.async_create_background_task(
                    self._async_refresh(key, loc), f"geekmagic radar {zoom}"
                )
            if loc.task is not None and loc.refreshing:
                timeout = DEFAULT_WAIT if wait is None else wait
                if count in loc.snapshots:
                    timeout = min(timeout, CACHED_WAIT)
                await asyncio.wait({loc.task}, timeout=timeout)
            self._evict(_monotonic())
            return self._snapshot(key, loc, count)
        except Exception as err:  # never cost the frame
            self._log_failure("radar", quiet, "Rain radar failed: %s", err)
            return None

    def invalidate(self) -> None:
        """Make the index (and failed tiles/basemaps) refetch on the next request."""
        self._index_fetched_at = None
        self._index_retry_at = 0.0
        self._tile_retry_at.clear()
        for loc in self._locations.values():
            loc.basemap_retry_at = 0.0

    # --- what is due ----------------------------------------------------------

    def _index_due(self, now: float) -> bool:
        if now < self._index_retry_at:
            return False
        if self._index is None or self._index_fetched_at is None:
            return True
        if now - self._index_fetched_at < INDEX_MIN_INTERVAL:
            return False
        newest = self._index[1][-1][0]
        return _wall() >= newest + INDEX_STALE_AFTER

    def _missing_tiles(
        self, key: _LocationKey, count: int, now: float
    ) -> list[tuple[_TileKey, str]]:
        """(tile key, url) of the selected frames not fetched yet nor failing."""
        if self._index is None:
            return []
        host, frames = self._index
        lat, lon, zoom = key
        rlat, rlon = rounded_location(lat, lon)
        missing = []
        for _, path in select_frames(frames, count):
            tile_key = (path, rlat, rlon, zoom)
            if tile_key in self._tiles or now < self._tile_retry_at.get(tile_key, 0.0):
                continue
            missing.append((tile_key, radar_tile_url(host, path, lat, lon, zoom)))
        return missing

    @staticmethod
    def _basemap_due(loc: _Location, now: float) -> bool:
        return (loc.base is None or loc.labels is None) and now >= loc.basemap_retry_at

    def _refresh_due(self, key: _LocationKey, loc: _Location, now: float) -> bool:
        return (
            self._index_due(now)
            or bool(self._missing_tiles(key, loc.max_count, now))
            or self._basemap_due(loc, now)
        )

    # --- fetching -----------------------------------------------------------

    async def _async_refresh(self, key: _LocationKey, loc: _Location) -> None:
        try:
            if self._index_due(_monotonic()):
                await self._async_refresh_index(loc)
            if await self._async_fetch_tiles(key, loc):
                # A path rotated out under us: the index is newer than ours
                await self._async_refresh_index(loc, force=True)
                await self._async_fetch_tiles(key, loc)
            if self._basemap_due(loc, _monotonic()):
                await self._async_fetch_basemap(key, loc)
        except Exception as err:
            self._log_failure("radar", loc.quiet, "Rain radar refresh failed: %s", err)

    async def _async_download(self, url: str) -> bytes:
        session = async_get_clientsession(self._hass)
        async with session.get(url, timeout=ClientTimeout(total=FETCH_TIMEOUT)) as response:
            if response.status == 410:
                raise RadarGoneError("HTTP 410")
            if response.status != 200:
                raise RadarFetchError(f"HTTP {response.status}")
            # The cap holds on the bytes received, whatever Content-Length says
            data = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > MAX_BODY_BYTES:
                    raise RadarFetchError(f"larger than {MAX_BODY_BYTES} bytes")
            return bytes(data)

    async def _async_refresh_index(self, loc: _Location, *, force: bool = False) -> None:
        async with self._index_lock:
            # Another location's refresh may have fetched it meanwhile
            if not force and not self._index_due(_monotonic()):
                return
            try:
                index = _parse_index_body(await self._async_download(INDEX_URL))
            except Exception as err:
                self._index_retry_at = _monotonic() + INDEX_RETRY
                self._log_failure(
                    "index", loc.quiet, "Failed to fetch the RainViewer index: %s", _reason(err)
                )
                return
            self._index = index
            self._index_fetched_at = _monotonic()
            self._index_retry_at = 0.0
            self._warned.discard("index")
            # Tiles of frames that left the index are never shown again
            paths = {path for _, path in index[1]}
            for tile_key in [k for k in self._tiles if k[0] not in paths]:
                del self._tiles[tile_key]
            for tile_key in [k for k in self._tile_retry_at if k[0] not in paths]:
                del self._tile_retry_at[tile_key]
            _LOGGER.debug("Fetched the RainViewer index: %d frames", len(index[1]))

    async def _async_fetch_tiles(self, key: _LocationKey, loc: _Location) -> bool:
        """Fetch the missing radar tiles; True when one answered 410."""
        missing = self._missing_tiles(key, loc.max_count, _monotonic())
        if not missing:
            return False
        results = await asyncio.gather(
            *(self._async_download(url) for _, url in missing), return_exceptions=True
        )
        gone = False
        for (tile_key, url), result in zip(missing, results, strict=True):
            if isinstance(result, bytes):
                self._tiles[tile_key] = result
                self._tile_retry_at.pop(tile_key, None)
                self._warned.discard("tiles")
                continue
            self._tile_retry_at[tile_key] = _monotonic() + TILE_RETRY
            if isinstance(result, RadarGoneError):
                # Routine: the path rotated out; the index refetch handles it
                gone = True
                _LOGGER.debug("Radar tile %s is gone (410)", url)
                continue
            self._log_failure(
                "tiles", loc.quiet, "Failed to fetch radar tile %s: %s", url, _reason(result)
            )
        return gone

    async def _async_fetch_layer(self, layer: str, zoom: int, cover: list) -> Image.Image:
        bodies = await asyncio.gather(
            *(
                self._async_download(ESRI_TILE_URL.format(layer=layer, z=zoom, x=x, y=y))
                for x, y, _, _ in cover
            )
        )
        tiles = [(left, top, body) for (_, _, left, top), body in zip(cover, bodies, strict=True)]
        return await self._hass.async_add_executor_job(stitch_basemap, tiles)

    async def _async_fetch_basemap(self, key: _LocationKey, loc: _Location) -> None:
        """Fetch whichever basemap layer is missing; each one is kept as it arrives."""
        lat, lon, zoom = key
        cover = basemap_cover(lat, lon, zoom + 1, REGION_PX, REGION_PX)
        failure: BaseException | None = None
        for layer, attr in ((BASE_LAYER, "base"), (LABELS_LAYER, "labels")):
            if getattr(loc, attr) is not None:
                continue
            try:
                setattr(loc, attr, await self._async_fetch_layer(layer, zoom + 1, cover))
            except Exception as err:
                failure = err
        if failure is not None:
            loc.basemap_retry_at = _monotonic() + BASEMAP_RETRY
            self._log_failure(
                "basemap", loc.quiet, "Failed to fetch the radar basemap: %s", _reason(failure)
            )
            return
        self._warned.discard("basemap")
        _LOGGER.debug("Stitched the radar basemap from %d tiles per layer", len(cover))

    # --- snapshots ----------------------------------------------------------

    def _snapshot(self, key: _LocationKey, loc: _Location, count: int) -> RadarSnapshot | None:
        """The snapshot of what is cached; the previous one while nothing better is.

        A new snapshot needs the newest frame of the index: until its tile
        is in hand (or while it fails), the previous snapshot stays rather
        than stepping back in time.
        """
        previous = loc.snapshots.get(count)
        if self._index is None:
            return previous[1] if previous else None
        lat, lon, zoom = key
        rlat, rlon = rounded_location(lat, lon)
        selected = select_frames(self._index[1], count)
        frames = [
            (stamp, path, self._tiles[(path, rlat, rlon, zoom)])
            for stamp, path in selected
            if (path, rlat, rlon, zoom) in self._tiles
        ]
        if not frames or (previous is not None and frames[-1][0] != selected[-1][0]):
            return previous[1] if previous else None
        source = (tuple((stamp, path) for stamp, path, _ in frames), id(loc.base), id(loc.labels))
        if previous is not None and previous[0] == source:
            return previous[1]
        snapshot = RadarSnapshot(
            [(stamp, data) for stamp, _, data in frames],
            home_offset(lat, lon, zoom),
            loc.base,
            loc.labels,
        )
        loc.snapshots[count] = (source, snapshot)
        return snapshot

    def _evict(self, now: float) -> None:
        def idle(loc: _Location) -> bool:
            return not loc.refreshing and now - loc.last_used > IN_USE_SECONDS

        for k in [
            k
            for k, loc in self._locations.items()
            if not loc.refreshing and now - loc.last_used > UNUSED_EVICT_SECONDS
        ]:
            del self._locations[k]
        excess = len(self._locations) - MAX_LOCATIONS
        if excess > 0:
            candidates = sorted(
                (k for k, loc in self._locations.items() if idle(loc)),
                key=lambda k: self._locations[k].last_used,
            )
            for k in candidates[:excess]:
                del self._locations[k]
        # Tiles of locations no longer shown
        live = {(*rounded_location(lat, lon), zoom) for lat, lon, zoom in self._locations}
        for tile_key in [k for k in self._tiles if k[1:] not in live]:
            del self._tiles[tile_key]

    def _log_failure(self, kind: str, quiet: bool, msg: str, *args: object) -> None:
        """WARNING the first time ``kind`` fails since it last worked, then DEBUG."""
        if quiet or kind in self._warned:
            _LOGGER.debug(msg, *args)
            return
        self._warned.add(kind)
        _LOGGER.warning(msg + " (further failures are logged at DEBUG)", *args)


def _parse_index_body(body: bytes) -> tuple[str, list[tuple[int, str]]]:
    if (index := parse_index(json.loads(body))) is None:
        msg = "unexpected index format"
        raise RadarFetchError(msg)
    return index


def _reason(err: BaseException) -> str:
    return str(err) or type(err).__name__


def get_radar_cache(hass: HomeAssistant) -> RadarCache:
    """The HA-wide radar cache, created on first use."""
    if (cache := hass.data.get(DATA_RADAR)) is None:
        cache = hass.data[DATA_RADAR] = RadarCache(hass)
    return cache
