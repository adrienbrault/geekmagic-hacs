"""Load and cache pictures for the Image widget and notify images.

A source is either an ``http(s)://`` URL or a path to a local file. Local
paths are resolved against the HA config directory (``/local/...`` maps to
``<config>/www/...`` like HA's own static route) and must sit inside a
directory HA allows external access to (``hass.config.is_allowed_path``:
``www/``, the media dirs and ``allowlist_external_dirs``) — so a widget can
never read ``secrets.yaml`` or ``.storage``.

Pictures are decoded once, off the event loop, downscaled to what a
240x240 supersampled screen can show, and cached per source with a
refresh interval: a static picture is not re-downloaded on every render
tick. Animated GIFs show their first frame (see ``decode_image``).

One cache per HA instance is shared by every device coordinator and the
panel preview, so N displays showing the same picture fetch it once.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.hass_dict import HassKey
from PIL import Image, ImageOps

from .const import DISPLAY_HEIGHT, DISPLAY_WIDTH, IMAGE_SOURCE_RETRY, SUPERSAMPLE_SCALE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Upper bound, in seconds, for one download.
FETCH_TIMEOUT = 10
# Refuse anything larger: a picture for a 240px panel has no business
# being tens of megabytes, and the bytes are held in memory to decode.
MAX_SOURCE_BYTES = 10 * 1024 * 1024
# Decoded pictures are downscaled so their SHORT side is at most the
# supersampled panel size (``cover`` in a full-screen cell stays sharp)
# and their long side is bounded (a panorama can't pin megabytes).
MAX_SHORT_SIDE = max(DISPLAY_WIDTH, DISPLAY_HEIGHT) * SUPERSAMPLE_SCALE
MAX_LONG_SIDE = 2 * MAX_SHORT_SIDE
# Entries no widget or preview asked for in this long are dropped, and
# the cache never holds more than MAX_ENTRIES (the panel preview feeds it
# every half-typed URL while a source is being edited).
UNUSED_EVICT_SECONDS = 15 * 60
MAX_ENTRIES = 32

_LOCAL_PREFIX = "/local/"

DATA_IMAGE_SOURCES: HassKey[ImageSourceCache] = HassKey("geekmagic_image_sources")


class ImageSourceError(Exception):
    """A source that cannot be loaded (rejected path, HTTP error, ...)."""


def is_url(source: str) -> bool:
    """Whether the source is fetched over HTTP."""
    return source.startswith(("http://", "https://"))


def is_image_source(value: str) -> bool:
    """Whether a notify ``image`` value is a URL/path rather than an entity.

    Entity ids never contain a slash, while every usable path does (files
    must live in a directory such as ``www/``).
    """
    return is_url(value) or "/" in value


def resolve_local_path(config_dir: str, source: str) -> Path:
    """Map a local source to an absolute path, without touching the disk.

    Raises ImageSourceError for parent-directory segments: ``..`` is
    rejected outright rather than trusted to resolve somewhere allowed.
    """
    if source.startswith(_LOCAL_PREFIX):
        source = "www/" + source.removeprefix(_LOCAL_PREFIX)
    if ".." in PurePosixPath(source).parts:
        raise ImageSourceError("'..' is not allowed in image paths")
    path = Path(source)
    return path if path.is_absolute() else Path(config_dir) / path


def read_local_file(hass: HomeAssistant, source: str) -> bytes:
    """Read a local source (blocking — run in the executor).

    The path is resolved (symlinks included) BEFORE the allowlist check,
    and the resolved path is what gets read, so a symlink inside ``www/``
    cannot point the widget at a file outside it.
    """
    path = resolve_local_path(hass.config.config_dir, source)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as err:
        raise ImageSourceError(f"file not found: {path}") from err
    if not hass.config.is_allowed_path(str(resolved)):
        raise ImageSourceError(
            f"{resolved} is outside the directories Home Assistant allows "
            "(put it in <config>/www/ or add its folder to allowlist_external_dirs)"
        )
    if not resolved.is_file():
        raise ImageSourceError(f"not a file: {resolved}")
    if resolved.stat().st_size > MAX_SOURCE_BYTES:
        raise ImageSourceError(f"file larger than {MAX_SOURCE_BYTES} bytes")
    return resolved.read_bytes()


async def async_download(hass: HomeAssistant, url: str) -> bytes:
    """Download a URL through HA's shared session, with a size cap."""
    session = async_get_clientsession(hass)
    async with session.get(url, timeout=ClientTimeout(total=FETCH_TIMEOUT)) as response:
        if response.status != 200:
            raise ImageSourceError(f"HTTP {response.status}")
        # No Content-Length shortcut: the header is optional and may lie,
        # so the cap is enforced on the bytes actually received.
        data = bytearray()
        async for chunk in response.content.iter_chunked(64 * 1024):
            data += chunk
            if len(data) > MAX_SOURCE_BYTES:
                raise ImageSourceError(f"larger than {MAX_SOURCE_BYTES} bytes")
        return bytes(data)


def decode_image(data: bytes) -> Image.Image:
    """Decode a picture for display (blocking — run in the executor).

    Animated GIF/WebP/APNG show their FIRST frame: the device's animated
    path renders the whole screen at a fixed rate from a per-layer CSS
    clock, which has no way to step through a picture's own frames.

    EXIF orientation is applied (phone photos would otherwise lie on their
    side). Transparency is kept (logos sit on the theme background);
    everything else becomes RGB. The result is downscaled once here so
    renders never re-encode a full-size photo.
    """
    image = Image.open(BytesIO(data))
    if image.format == "JPEG":
        # Let libjpeg decode at a reduced scale (still >= the target).
        image.draft("RGB", (MAX_SHORT_SIDE, MAX_SHORT_SIDE))
    image.load()
    ImageOps.exif_transpose(image, in_place=True)
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA" if has_alpha else "RGB")
    width, height = image.size
    scale = min(1.0, MAX_SHORT_SIDE / min(width, height), MAX_LONG_SIDE / max(width, height))
    if scale < 1.0:
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image


@dataclass
class _Entry:
    image: Image.Image | None = None
    fetched_at: float | None = None  # monotonic time of the last success
    retry_at: float = 0.0  # monotonic time before which a failure is not retried
    last_used: float = 0.0
    warned: bool = False


class ImageSourceCache:
    """Per-source picture cache with a refresh interval and stale-on-error."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an empty cache."""
        self._hass = hass
        self._entries: dict[str, _Entry] = {}
        self._inflight: dict[str, asyncio.Future[None]] = {}

    async def async_get(
        self, source: str, max_age: float, *, quiet: bool = False
    ) -> Image.Image | None:
        """Return the picture for ``source``, refreshing it when stale.

        ``max_age`` is the requesting widget's refresh interval. A failed
        refresh keeps serving the last good picture and is retried after
        ``IMAGE_SOURCE_RETRY`` seconds. Returns None when the source has
        never loaded. ``quiet`` logs failures at DEBUG only (the panel
        preview loads every source the user types, half-typed ones too).

        Each caller gets its OWN copy: renders run in executor threads, and
        ``Image.save`` (``image_data_uri``) mutates the image it encodes.
        """
        source = source.strip()
        if not source:
            return None
        now = time.monotonic()
        entry = self._entries.setdefault(source, _Entry())
        entry.last_used = now
        fresh = entry.fetched_at is not None and now - entry.fetched_at < max_age
        if not fresh and now >= entry.retry_at:
            await self._async_refresh(source, entry, quiet)
        self._evict(now)
        return entry.image.copy() if entry.image is not None else None

    def invalidate(self, source: str | None = None) -> None:
        """Make one source (default: every source) refetch on its next request."""
        entries = self._entries.values() if source is None else [self._entries.get(source)]
        for entry in entries:
            if entry is not None:
                entry.fetched_at = None
                entry.retry_at = 0.0

    async def _async_refresh(self, source: str, entry: _Entry, quiet: bool) -> None:
        """Fetch one source; concurrent requests share a single fetch."""
        if (pending := self._inflight.get(source)) is not None:
            await asyncio.shield(pending)
            return
        future: asyncio.Future[None] = self._hass.loop.create_future()
        self._inflight[source] = future
        try:
            await self._async_load(source, entry, quiet)
        finally:
            del self._inflight[source]
            future.set_result(None)

    async def _async_load(self, source: str, entry: _Entry, quiet: bool) -> None:
        try:
            if is_url(source):
                data = await async_download(self._hass, source)
            else:
                data = await self._hass.async_add_executor_job(read_local_file, self._hass, source)
            image = await self._hass.async_add_executor_job(decode_image, data)
        except Exception as err:  # any failure keeps the stale picture
            entry.retry_at = time.monotonic() + IMAGE_SOURCE_RETRY
            reason = str(err) or type(err).__name__
            if entry.warned or quiet:
                _LOGGER.debug("Failed to load image %s: %s", source, reason)
            else:
                entry.warned = True
                _LOGGER.warning(
                    "Failed to load image %s: %s (retrying every %ds; further "
                    "failures are logged at DEBUG)",
                    source,
                    reason,
                    IMAGE_SOURCE_RETRY,
                )
            return
        entry.image = image
        entry.fetched_at = time.monotonic()
        entry.retry_at = 0.0
        entry.warned = False
        _LOGGER.debug("Loaded image %s (%dx%d)", source, *image.size)

    def _evict(self, now: float) -> None:
        stale = [
            key
            for key, entry in self._entries.items()
            if now - entry.last_used > UNUSED_EVICT_SECONDS and key not in self._inflight
        ]
        for key in stale:
            del self._entries[key]
        if len(self._entries) > MAX_ENTRIES:
            by_age = sorted(self._entries, key=lambda key: self._entries[key].last_used)
            for key in by_age[: len(self._entries) - MAX_ENTRIES]:
                if key not in self._inflight:
                    del self._entries[key]


def get_image_cache(hass: HomeAssistant) -> ImageSourceCache:
    """The HA-wide image cache, created on first use."""
    if (cache := hass.data.get(DATA_IMAGE_SOURCES)) is None:
        cache = hass.data[DATA_IMAGE_SOURCES] = ImageSourceCache(hass)
    return cache
