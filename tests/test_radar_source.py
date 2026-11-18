"""The HA-wide radar cache: what it fetches, how often, and what it serves on errors."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

from custom_components.geekmagic import radar_source
from custom_components.geekmagic.radar_source import (
    CACHED_WAIT,
    IN_USE_SECONDS,
    INDEX_MIN_INTERVAL,
    INDEX_RETRY,
    INDEX_STALE_AFTER,
    INDEX_URL,
    MAX_BODY_BYTES,
    MAX_LOCATIONS,
    UNUSED_EVICT_SECONDS,
    RadarCache,
    get_radar_cache,
)

LAT, LON = 50.0, 8.0
HOST = "https://tilecache.example"
NEWEST = 1_736_937_000
TILE_RE = re.compile(r"^https://tilecache\.example/")
ESRI_RE = re.compile(r"^https://server\.arcgisonline\.com/")


def _png(size: tuple[int, int], color=(0, 98, 149, 255)) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


TILE = _png((512, 512))
BASEMAP_TILE = _png((256, 256), (40, 40, 40, 255))


def _index(newest: int = NEWEST, frames: int = 13) -> dict:
    return {
        "version": "2.0",
        "host": HOST,
        "radar": {
            "past": [
                {"time": newest - 600 * i, "path": f"/v2/radar/p{newest - 600 * i}"}
                for i in range(frames - 1, -1, -1)
            ],
            "nowcast": [],
        },
    }


class FakeClock:
    """Monotonic and wall clocks of radar_source, advanced by hand."""

    def __init__(self) -> None:
        self.mono = 1000.0
        self.wall = NEWEST + 60.0

    def advance(self, seconds: float) -> None:
        self.mono += seconds
        self.wall += seconds


@pytest.fixture
def clock():
    fake = FakeClock()
    with (
        patch.object(radar_source, "_monotonic", lambda: fake.mono),
        patch.object(radar_source, "_wall", lambda: fake.wall),
    ):
        yield fake


def _serve(
    aioclient_mock, *, index=None, index_status=200, tile=TILE, tile_status=200, esri_status=200
) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(INDEX_URL, json=index or _index(), status=index_status)
    aioclient_mock.get(TILE_RE, content=tile, status=tile_status)
    aioclient_mock.get(ESRI_RE, content=BASEMAP_TILE, status=esri_status)


def _calls(aioclient_mock, kind: str) -> list[str]:
    urls = [str(call[1]) for call in aioclient_mock.mock_calls]
    if kind == "index":
        return [u for u in urls if u == INDEX_URL]
    if kind == "tiles":
        return [u for u in urls if TILE_RE.match(u)]
    return [u for u in urls if ESRI_RE.match(u)]


async def _get(hass, count: int = 7, **kwargs):
    lat = kwargs.pop("lat", LAT)
    lon = kwargs.pop("lon", LON)
    return await get_radar_cache(hass).async_get(lat, lon, 7, count, wait=5, **kwargs)


async def test_fetches_index_tiles_and_basemap_once(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    snapshot = await _get(hass)
    assert snapshot is not None
    assert snapshot.times == tuple(NEWEST - 1200 * k for k in range(6, -1, -1))
    assert snapshot.base is not None
    assert snapshot.labels is not None
    assert len(_calls(aioclient_mock, "index")) == 1
    assert len(_calls(aioclient_mock, "tiles")) == 7
    assert 8 <= len(_calls(aioclient_mock, "esri")) <= 18

    # A second display (or the preview) of the same place shares everything
    clock.advance(30)
    again = await _get(hass)
    assert again is snapshot
    assert len(aioclient_mock.mock_calls) == 7 + 1 + len(_calls(aioclient_mock, "esri"))

    # The 1 hour period needs no new tile: it is a subset of the 2 hours
    one_hour = await _get(hass, count=4)
    assert one_hour is not None
    assert one_hour.times == snapshot.times[-4:]
    assert len(_calls(aioclient_mock, "tiles")) == 7


async def test_index_refetched_only_when_a_new_frame_is_due(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    await _get(hass)
    # The newest frame is not old enough yet
    clock.advance(INDEX_MIN_INTERVAL + 10)
    await _get(hass)
    assert len(_calls(aioclient_mock, "index")) == 1

    clock.wall = NEWEST + INDEX_STALE_AFTER + 1
    newer = _index(NEWEST + 600)
    _serve(aioclient_mock, index=newer)
    snapshot = await _get(hass)
    assert len(_calls(aioclient_mock, "index")) == 1
    # Every second frame back from the new newest: the other half of the index
    assert len(_calls(aioclient_mock, "tiles")) == 7
    assert snapshot is not None
    assert snapshot.times[-1] == NEWEST + 600

    # Never more often than INDEX_MIN_INTERVAL, however stale
    clock.wall += 3600
    _serve(aioclient_mock, index=newer)
    await _get(hass)
    assert _calls(aioclient_mock, "index") == []


async def test_tiles_are_fetched_once_per_path(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    await _get(hass)
    clock.wall = NEWEST + 600 + INDEX_STALE_AFTER + 1
    clock.advance(INDEX_MIN_INTERVAL)
    _serve(aioclient_mock, index=_index(NEWEST + 1200))
    snapshot = await _get(hass)
    tiles = _calls(aioclient_mock, "tiles")
    assert len(tiles) == 1
    assert f"/v2/radar/p{NEWEST + 1200}/" in tiles[0]
    assert snapshot is not None
    assert snapshot.times[-1] == NEWEST + 1200
    cache = get_radar_cache(hass)
    assert all(key[0] != f"/v2/radar/p{NEWEST - 7200}" for key in cache._tiles)


async def test_urls_carry_rounded_coordinates(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    snapshot = await _get(hass, lat=50.04321, lon=8.06789)
    assert snapshot is not None
    tiles = _calls(aioclient_mock, "tiles")
    assert tiles
    assert all("/512/7/50.0/8.1/2/1_1.png" in url for url in tiles)
    assert not any("50.04" in url or "8.06" in url for url in aioclient_mock_urls(aioclient_mock))
    # Home is off-centre in the tile, so the crop is shifted
    assert snapshot.offset[0] < 0
    assert snapshot.offset[1] < 0


def aioclient_mock_urls(aioclient_mock) -> list[str]:
    return [str(call[1]) for call in aioclient_mock.mock_calls]


async def test_stale_on_error_with_backoff_and_one_warning(hass, aioclient_mock, clock, caplog):
    _serve(aioclient_mock)
    snapshot = await _get(hass)
    clock.wall = NEWEST + INDEX_STALE_AFTER + 1
    clock.advance(INDEX_MIN_INTERVAL)
    _serve(aioclient_mock, index_status=500)
    with caplog.at_level(logging.DEBUG, logger=radar_source.__name__):
        assert await _get(hass) is snapshot
        # Not retried before INDEX_RETRY
        clock.advance(INDEX_RETRY / 2)
        assert await _get(hass) is snapshot
        assert len(_calls(aioclient_mock, "index")) == 1
        clock.advance(INDEX_RETRY)
        assert await _get(hass) is snapshot
        assert len(_calls(aioclient_mock, "index")) == 2
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "RainViewer index" in warnings[0].getMessage()


async def test_quiet_never_warns(hass, aioclient_mock, clock, caplog):
    _serve(aioclient_mock, index_status=500)
    with caplog.at_level(logging.DEBUG, logger=radar_source.__name__):
        assert await _get(hass, quiet=True) is None
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


async def test_gone_tile_refetches_the_index_once(hass, aioclient_mock, clock):
    """A 410 means the paths rotated: the index is fetched again, once."""
    rotated = _index(NEWEST)
    for frame in rotated["radar"]["past"]:
        frame["path"] += "r"
    indexes = iter([_index(), rotated, rotated])

    async def index(method, url, data):
        return AiohttpClientMockResponse(method, url, json=next(indexes))

    aioclient_mock.get(INDEX_URL, side_effect=index)
    aioclient_mock.get(re.compile(r"^https://tilecache\.example/v2/radar/p\d+/"), status=410)
    aioclient_mock.get(TILE_RE, content=TILE)
    aioclient_mock.get(ESRI_RE, content=BASEMAP_TILE)
    snapshot = await _get(hass)
    assert snapshot is not None
    assert len(snapshot.frames) == 7
    assert len(_calls(aioclient_mock, "index")) == 2
    assert len(_calls(aioclient_mock, "tiles")) == 14


async def test_gone_tiles_of_an_unchanged_index_are_not_hammered(
    hass, aioclient_mock, clock, caplog
):
    _serve(aioclient_mock, tile_status=410)
    with caplog.at_level(logging.DEBUG, logger=radar_source.__name__):
        assert await _get(hass) is None
    # Routine rotation: DEBUG, not WARNING
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(_calls(aioclient_mock, "index")) == 2
    assert len(_calls(aioclient_mock, "tiles")) == 7
    await _get(hass)
    assert len(_calls(aioclient_mock, "tiles")) == 7


async def test_oversized_bodies_are_rejected(hass, aioclient_mock, clock):
    _serve(aioclient_mock, tile=b"\0" * (MAX_BODY_BYTES + 1))
    assert await _get(hass) is None
    cache = get_radar_cache(hass)
    assert not cache._tiles


async def test_basemap_failure_still_yields_a_snapshot(hass, aioclient_mock, clock):
    _serve(aioclient_mock, esri_status=503)
    snapshot = await _get(hass)
    assert snapshot is not None
    assert snapshot.base is None
    assert len(snapshot.frames) == 7
    esri_calls = len(_calls(aioclient_mock, "esri"))
    # Retried after five minutes, not on every frame
    clock.advance(60)
    _serve(aioclient_mock)
    await _get(hass)
    assert _calls(aioclient_mock, "esri") == []
    clock.advance(5 * 60)
    with_map = await _get(hass)
    assert with_map is not None
    assert with_map.base is not None
    assert esri_calls


async def test_slow_server_neither_raises_nor_holds_the_frame(hass, aioclient_mock, clock):
    never = asyncio.Event()

    async def hang(method, url, data):
        await never.wait()

    aioclient_mock.get(INDEX_URL, side_effect=hang)
    start = time.monotonic()
    result = await get_radar_cache(hass).async_get(LAT, LON, 7, 7, wait=0.05)
    assert result is None
    assert time.monotonic() - start < 2
    # A second caller joins the pending refresh rather than starting another
    await get_radar_cache(hass).async_get(LAT, LON, 7, 7, wait=0.05)
    assert len(_calls(aioclient_mock, "index")) == 1


async def test_idle_locations_are_evicted_beyond_the_cap(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    for i in range(MAX_LOCATIONS + 1):
        await _get(hass, lat=40.0 + i, lon=2.0)
        clock.advance(1)
    cache = get_radar_cache(hass)
    # All in use (asked for within IN_USE_SECONDS): none is dropped yet
    assert len(cache._locations) == MAX_LOCATIONS + 1

    clock.advance(IN_USE_SECONDS + 1)
    await _get(hass, lat=60.0, lon=2.0)
    assert len(cache._locations) == MAX_LOCATIONS
    # The least recently used idle ones went, with their tiles
    assert (40.0, 2.0, 7) not in cache._locations
    assert (41.0, 2.0, 7) not in cache._locations
    assert all(key[1] not in (40.0, 41.0) for key in cache._tiles)

    clock.advance(UNUSED_EVICT_SECONDS + 1)
    await _get(hass, lat=61.0, lon=2.0)
    assert list(cache._locations) == [(61.0, 2.0, 7)]


async def test_more_live_locations_than_the_cap_do_not_refetch(hass, aioclient_mock, clock):
    """Displays showing more places than the cap don't thrash the cache."""
    _serve(aioclient_mock)
    places = [(40.0 + i, 2.0) for i in range(MAX_LOCATIONS + 3)]
    for lat, lon in places:
        await _get(hass, lat=lat, lon=lon)
    calls = len(aioclient_mock.mock_calls)
    for _ in range(3):  # three display cycles, 10 s apart
        clock.advance(10)
        for lat, lon in places:
            assert await _get(hass, lat=lat, lon=lon) is not None
    assert len(aioclient_mock.mock_calls) == calls


async def test_preview_coordinates_cannot_evict_a_shown_location(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    shown = await _get(hass)
    for i in range(3 * MAX_LOCATIONS):  # the editor, one keystroke at a time
        await _get(hass, lat=10.0 + i / 10, lon=2.0, quiet=True)
        clock.advance(1)
    calls = len(aioclient_mock.mock_calls)
    assert await _get(hass) is shown
    assert len(aioclient_mock.mock_calls) == calls


async def test_one_refresh_task_per_location(hass, aioclient_mock, clock):
    """A location whose refresh hangs is never evicted, so never fetched twice."""
    never = asyncio.Event()

    async def hang(method, url, data):
        await never.wait()

    aioclient_mock.get(INDEX_URL, json=_index())
    aioclient_mock.get(re.compile(r"/512/7/70\.0/2\.0/"), side_effect=hang)
    aioclient_mock.get(TILE_RE, content=TILE)
    aioclient_mock.get(ESRI_RE, content=BASEMAP_TILE)
    cache = get_radar_cache(hass)
    await cache.async_get(70.0, 2.0, 7, 7, wait=0.05)
    clock.advance(UNUSED_EVICT_SECONDS + 1)
    for i in range(MAX_LOCATIONS + 2):
        await _get(hass, lat=40.0 + i, lon=2.0)
    assert (70.0, 2.0, 7) in cache._locations
    await cache.async_get(70.0, 2.0, 7, 7, wait=0.05)
    hung = [u for u in _calls(aioclient_mock, "tiles") if "/70.0/2.0/" in u]
    assert len(hung) == 7


async def test_a_hung_refresh_does_not_stall_a_cached_location(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    snapshot = await _get(hass)
    never = asyncio.Event()

    async def hang(method, url, data):
        await never.wait()

    aioclient_mock.clear_requests()
    aioclient_mock.get(INDEX_URL, side_effect=hang)
    clock.wall = NEWEST + INDEX_STALE_AFTER + 1
    clock.advance(INDEX_MIN_INTERVAL)
    start = time.monotonic()
    assert await get_radar_cache(hass).async_get(LAT, LON, 7, 7, wait=10) is snapshot
    assert time.monotonic() - start < CACHED_WAIT + 0.5
    assert len(_calls(aioclient_mock, "index")) == 1


async def test_failed_labels_keep_the_base_layer(hass, aioclient_mock, clock):
    aioclient_mock.get(INDEX_URL, json=_index())
    aioclient_mock.get(TILE_RE, content=TILE)
    aioclient_mock.get(re.compile(r"World_Dark_Gray_Reference"), status=503)
    aioclient_mock.get(ESRI_RE, content=BASEMAP_TILE)
    snapshot = await _get(hass)
    assert snapshot is not None
    assert snapshot.base is not None
    assert snapshot.labels is None

    clock.advance(5 * 60 + 1)
    _serve(aioclient_mock)
    with_labels = await _get(hass)
    assert with_labels is not None
    assert with_labels.labels is not None
    esri = _calls(aioclient_mock, "esri")
    assert esri
    assert all("World_Dark_Gray_Reference" in url for url in esri)


async def test_newest_frame_never_steps_back(hass, aioclient_mock, clock):
    """Until the new newest tile is in hand, the previous snapshot stays."""
    _serve(aioclient_mock)
    snapshot = await _get(hass)
    clock.wall = NEWEST + 1200 + INDEX_STALE_AFTER + 1
    clock.advance(INDEX_MIN_INTERVAL)
    aioclient_mock.clear_requests()
    aioclient_mock.get(INDEX_URL, json=_index(NEWEST + 1200))
    aioclient_mock.get(re.compile(rf"/p{NEWEST + 1200}/"), status=503)
    aioclient_mock.get(TILE_RE, content=TILE)
    assert await _get(hass) is snapshot


async def test_a_waiting_display_gets_the_warning_a_preview_started(
    hass, aioclient_mock, clock, caplog
):
    release = asyncio.Event()

    async def slow_failure(method, url, data):
        await release.wait()
        return AiohttpClientMockResponse(method, url, status=500)

    aioclient_mock.get(INDEX_URL, side_effect=slow_failure)
    cache = get_radar_cache(hass)
    with caplog.at_level(logging.DEBUG, logger=radar_source.__name__):
        await cache.async_get(LAT, LON, 7, 7, wait=0.01, quiet=True)
        hass.loop.call_later(0.05, release.set)
        await cache.async_get(LAT, LON, 7, 7, wait=5)
    assert [r for r in caplog.records if r.levelno == logging.WARNING]


async def test_invalidate_refetches_the_index(hass, aioclient_mock, clock):
    _serve(aioclient_mock)
    await _get(hass)
    get_radar_cache(hass).invalidate()
    _serve(aioclient_mock)
    await _get(hass)
    assert len(_calls(aioclient_mock, "index")) == 1


async def test_garbage_index_is_a_failure(hass, aioclient_mock, clock):
    aioclient_mock.get(INDEX_URL, text="<html>nope</html>")
    assert await _get(hass) is None


def test_one_cache_per_hass(hass):
    assert get_radar_cache(hass) is get_radar_cache(hass)
    assert isinstance(get_radar_cache(hass), RadarCache)
