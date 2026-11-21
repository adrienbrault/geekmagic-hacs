"""Rain radar geometry, frame selection and per-cell images (HA-free).

The Rain Radar widget shows RainViewer radar frames over an Esri basemap.
``radar_source`` fetches the bytes in Home Assistant; everything that
works on them lives here, so tools and tests run it without Home
Assistant (no ``homeassistant`` or ``aiohttp`` import):

- web-mercator geometry: ``mercator_px``, ``basemap_cover``, ``home_offset``
- which frames of the RainViewer index to show: ``parse_index``,
  ``select_frames``
- ``RadarSnapshot``: the fetched frames and basemap of one location,
  turned into ``RadarCell`` images cropped to one cell size
- ``parse_next_hour``: a next-hour precipitation forecast attribute,
  whatever its shape, as timeline segments

Geometry: a RainViewer 512-px tile at zoom ``z`` is centred exactly on
the requested lat/lon and spans 512 px of a ``512 * 2**z`` px world, i.e.
the same pixel grid as 256-px XYZ tiles at ``z + 1`` (the basemap zoom).
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import re
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from PIL import Image

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_LOGGER = logging.getLogger(__name__)

MAX_LATITUDE = 85.05112878
RADAR_TILE_PX = 512
BASEMAP_TILE_PX = 256
# RainViewer serves zoom 0-7 (z8+ answers HTTP 200 with a "Zoom Level Not
# Supported" picture), so every requested zoom is clamped to this range.
MIN_RADAR_ZOOM = 1
MAX_RADAR_ZOOM = 7
# Source pixels shown across a cell's long side (0.9 CSS px per tile px in
# a 240 px cell, the scale the widget was designed at).
VIEW_SPAN = 267
# Square of source pixels kept around home: VIEW_SPAN plus rounding slack.
REGION_PX = 272
# Frames in the RainViewer index are 600 s apart; the widget shows every
# second one (20 min apart).
FRAME_STEP_SECONDS = 1200
# Requested coordinates are rounded to this many decimals (0.1°): the
# exact home location never leaves Home Assistant, and nearby homes share
# RainViewer's cache.
COORD_DECIMALS = 1

# Radar intensity classes. Index 0 is transparent (no echo); the others
# are opaque, one fixed colour each, so a looping GIF of the radar needs
# a handful of palette entries instead of every blend of RainViewer's
# translucent ramp over the map.
NO_ECHO, DRIZZLE, LIGHT, MODERATE, HEAVY, INTENSE = range(6)
CLASS_COLORS: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (38, 92, 140),  # drizzle, snow flurries
    (100, 205, 240),  # light rain, snow (RainViewer's pale cyan rim)
    (0, 140, 215),  # moderate rain (the blue core)
    (255, 200, 0),  # heavy rain
    (235, 45, 30),  # intense rain, hail
)
# Translucent echoes fainter than this are drawn as nothing (RainViewer's
# faintest drizzle tint is mostly ground clutter at a glance).
_MIN_ECHO_ALPHA = 60
_PALETTE: list[int] = [channel for color in CLASS_COLORS for channel in color]


# --- geometry ----------------------------------------------------------------


def mercator_px(
    lat: float, lon: float, zoom: int, tile_px: int = BASEMAP_TILE_PX
) -> tuple[float, float]:
    """World pixel of ``lat``/``lon`` in a ``tile_px * 2**zoom`` px web-mercator world.

    Latitude is clamped to the projection's +-85.05°; longitude is taken
    as given (callers wrap tile columns).
    """
    world = tile_px * (2**zoom)
    lat = max(-MAX_LATITUDE, min(MAX_LATITUDE, lat))
    sin = math.sin(math.radians(lat))
    x = (lon + 180.0) / 360.0 * world
    y = (0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi)) * world
    return x, y


def basemap_cover(
    lat: float, lon: float, zoom: int, width: int, height: int
) -> list[tuple[int, int, int, int]]:
    """The 256-px tiles at ``zoom`` covering a ``width`` x ``height`` box centred on lat/lon.

    Returns ``(x, y, left, top)`` per tile: its XYZ column (wrapped around
    the antimeridian) and row, and where its top-left corner lands in the
    box. Rows beyond the poles are left out (the box stays transparent
    there).
    """
    cx, cy = mercator_px(lat, lon, zoom)
    origin_x = math.floor(cx - width / 2)
    origin_y = math.floor(cy - height / 2)
    count = 2**zoom
    rows = range(origin_y // BASEMAP_TILE_PX, (origin_y + height - 1) // BASEMAP_TILE_PX + 1)
    cols = range(origin_x // BASEMAP_TILE_PX, (origin_x + width - 1) // BASEMAP_TILE_PX + 1)
    return [
        (tx % count, ty, tx * BASEMAP_TILE_PX - origin_x, ty * BASEMAP_TILE_PX - origin_y)
        for ty in rows
        if 0 <= ty < count
        for tx in cols
    ]


def rounded_location(lat: float, lon: float) -> tuple[float, float]:
    """The coordinates RainViewer is asked for: rounded to 0.1°, never -0.0."""
    lat = max(-MAX_LATITUDE, min(MAX_LATITUDE, lat))
    lon = ((lon + 180.0) % 360.0) - 180.0
    return round(lat, COORD_DECIMALS) + 0.0, round(lon, COORD_DECIMALS) + 0.0


def clamp_zoom(zoom: int) -> int:
    """A RainViewer zoom the tile server actually renders."""
    return max(MIN_RADAR_ZOOM, min(MAX_RADAR_ZOOM, int(zoom)))


def home_offset(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Where home sits relative to the centre of its (rounded) radar tile, in tile px.

    Positive x is east, positive y is south (screen axes).
    """
    rlat, rlon = rounded_location(lat, lon)
    hx, hy = mercator_px(lat, lon, zoom, RADAR_TILE_PX)
    cx, cy = mercator_px(rlat, rlon, zoom, RADAR_TILE_PX)
    world = RADAR_TILE_PX * (2**zoom)
    dx = (hx - cx + world / 2) % world - world / 2  # across the antimeridian
    return dx, hy - cy


def radar_tile_url(host: str, path: str, lat: float, lon: float, zoom: int) -> str:
    """URL of the 512-px radar tile of one frame, centred on the rounded location."""
    rlat, rlon = rounded_location(lat, lon)
    return f"{host}{path}/{RADAR_TILE_PX}/{clamp_zoom(zoom)}/{rlat:.1f}/{rlon:.1f}/2/1_1.png"


# --- the RainViewer index ------------------------------------------------------


def parse_index(data: Any) -> tuple[str, list[tuple[int, str]]] | None:
    """``(host, [(time, path), ...])`` of a weather-maps.json body, oldest first.

    None when the body isn't usable. Malformed frames are skipped.
    """
    if not isinstance(data, dict):
        return None
    host = data.get("host")
    radar = data.get("radar")
    if not isinstance(host, str) or not host.startswith("https://") or not isinstance(radar, dict):
        return None
    past = radar.get("past")
    if not isinstance(past, list):
        return None
    frames: dict[int, str] = {}
    for frame in past:
        if not isinstance(frame, dict):
            continue
        stamp, path = frame.get("time"), frame.get("path")
        if (
            isinstance(stamp, int)
            and not isinstance(stamp, bool)
            and isinstance(path, str)
            and path.startswith("/")
            and ".." not in path
        ):
            frames[stamp] = path
    if not frames:
        return None
    return host.rstrip("/"), sorted(frames.items())


def select_frames(
    frames: Sequence[tuple[int, str]], count: int, step: int = FRAME_STEP_SECONDS
) -> list[tuple[int, str]]:
    """The newest frame and up to ``count - 1`` older ones ``step`` seconds apart, oldest first.

    A frame missing from the index (an outage) leaves a gap rather than
    pulling in a frame at the wrong time.
    """
    if not frames or count < 1:
        return []
    by_time = dict(frames)
    newest = max(by_time)
    picked = []
    for k in range(count):
        target = newest - k * step
        if target in by_time:
            picked.append((target, by_time[target]))
    return sorted(picked)


# --- images --------------------------------------------------------------------


def classify_color(rgba: tuple[int, ...]) -> int:
    """The intensity class of one RainViewer "Universal Blue" pixel.

    Translucent tan/white tints are drizzle and light snow; opaque pale
    cyans (the outer rim of an echo) and pale blues light rain and snow;
    the darker blues inside them moderate rain; yellow and orange heavy
    rain; reds, magentas and pinks intense rain and hail.
    """
    if len(rgba) < 4:
        r, g, b = rgba[:3]
        a = 255
    else:
        r, g, b, a = rgba[:4]
    if a < _MIN_ECHO_ALPHA:
        return NO_ECHO
    if a < 255:
        return DRIZZLE
    if r >= 250 and b >= 250:
        return INTENSE  # magenta
    if b < r:
        return HEAVY if b < 60 and g >= 120 else INTENSE
    return MODERATE if r < 20 else LIGHT


def posterize(tile: Image.Image) -> Image.Image:
    """A radar tile as a palette image of the intensity classes (index 0 transparent).

    One lookup per distinct colour (a tile holds a few hundred), then a
    table lookup per pixel.
    """
    rgba = tile.convert("RGBA")
    colors = rgba.getcolors(maxcolors=rgba.width * rgba.height) or []
    lut = {color: classify_color(color) for _, color in colors if isinstance(color, tuple)}
    pixels = cast("Iterable[tuple[int, ...]]", rgba.getdata())
    data = bytes(map(lut.__getitem__, pixels))
    classes = Image.frombytes("P", rgba.size, data)
    classes.putpalette(_PALETTE)
    classes.info["transparency"] = 0
    return classes


def _home_region(data: bytes, offset: tuple[float, float]) -> Image.Image:
    """The ``REGION_PX`` square around home of one radar tile (blocking)."""
    with Image.open(io.BytesIO(data)) as tile:
        if tile.width > 2 * RADAR_TILE_PX or tile.height > 2 * RADAR_TILE_PX:
            msg = f"unexpected tile size {tile.size}"
            raise ValueError(msg)
        tile.load()
        cx = tile.width / 2 + offset[0]
        cy = tile.height / 2 + offset[1]
        return _crop_centered(tile, cx, cy, REGION_PX, REGION_PX)


def _png_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    if image.mode == "P":
        image.save(buf, format="PNG", transparency=0)
    else:
        image.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _crop_centered(
    image: Image.Image, cx: float, cy: float, width: int, height: int
) -> Image.Image:
    left = round(cx - width / 2)
    top = round(cy - height / 2)
    return image.crop((left, top, left + width, top + height))


def cell_source_size(width: int, height: int) -> tuple[int, int]:
    """Source pixels a ``width`` x ``height`` cell shows: VIEW_SPAN across its long side."""
    scale = max(width, height, 1) / VIEW_SPAN
    return max(1, round(width / scale)), max(1, round(height / scale))


@dataclass(frozen=True)
class RadarCell:
    """One snapshot cropped to one cell size, ready for the widget's HTML.

    ``frames`` are ``(epoch seconds, data URI)`` oldest first; every
    image (frames, ``base_uri``, ``labels_uri``) is ``src_size`` source
    pixels with home at its centre.
    """

    frames: tuple[tuple[int, str], ...]
    base_uri: str | None
    labels_uri: str | None
    src_size: tuple[int, int]


class RadarSnapshot:
    """The radar frames and basemap of one location, as fetched.

    Immutable once built; ``radar_source`` hands out the same instance
    while nothing changes, so the per-size crops below are computed once
    per new frame, not per render. Safe to share between executor threads.
    """

    def __init__(
        self,
        frames: Sequence[tuple[int, bytes]],
        offset: tuple[float, float],
        base: Image.Image | None = None,
        labels: Image.Image | None = None,
    ) -> None:
        """``frames``: (time, radar tile PNG) oldest first.

        ``offset``: home relative to the tiles' centre (``home_offset``).
        ``base`` / ``labels``: basemap layers, ``REGION_PX`` square and
        centred on home (``basemap_cover``), or None when not loaded.
        """
        self.frames: tuple[tuple[int, bytes], ...] = tuple(sorted(frames))
        self.offset = offset
        self.base = base
        self.labels = labels
        self._lock = threading.Lock()
        self._regions: list[tuple[int, Image.Image]] | None = None
        self._cells: dict[tuple[int, int], RadarCell] = {}

    @property
    def times(self) -> tuple[int, ...]:
        """Frame times, oldest first."""
        return tuple(stamp for stamp, _ in self.frames)

    def for_cell(self, width: int, height: int) -> RadarCell:
        """The snapshot cropped for a ``width`` x ``height`` cell (memoized per size)."""
        key = (int(width), int(height))
        with self._lock:
            if (cell := self._cells.get(key)) is None:
                cell = self._cells[key] = self._build_cell(*key)
            return cell

    def _posterized_regions(self) -> list[tuple[int, Image.Image]]:
        """Each frame's ``REGION_PX`` square around home, posterized (decoded once)."""
        if self._regions is None:
            regions = []
            for stamp, data in self.frames:
                try:
                    region = _home_region(data, self.offset)
                except Exception as err:  # a corrupt frame costs itself only
                    _LOGGER.debug("Skipping unreadable radar frame %s: %s", stamp, err)
                    continue
                regions.append((stamp, posterize(region)))
            self._regions = regions
        return self._regions

    def _build_cell(self, width: int, height: int) -> RadarCell:
        src_w, src_h = cell_source_size(width, height)
        center = REGION_PX / 2
        frames = tuple(
            (stamp, _png_uri(_crop_centered(region, center, center, src_w, src_h)))
            for stamp, region in self._posterized_regions()
        )
        base_uri = labels_uri = None
        if self.base is not None:
            base_uri = _png_uri(
                _crop_centered(self.base.convert("RGB"), center, center, src_w, src_h)
            )
        if self.labels is not None:
            labels_uri = _png_uri(
                _crop_centered(self.labels.convert("RGBA"), center, center, src_w, src_h)
            )
        return RadarCell(
            frames=frames, base_uri=base_uri, labels_uri=labels_uri, src_size=(src_w, src_h)
        )


def stitch_basemap(
    tiles: Sequence[tuple[int, int, bytes]], width: int = REGION_PX, height: int = REGION_PX
) -> Image.Image:
    """Paste basemap tiles (``(left, top, image bytes)``) into one RGBA box (blocking)."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for left, top, data in tiles:
        with Image.open(io.BytesIO(data)) as tile:
            if tile.size != (BASEMAP_TILE_PX, BASEMAP_TILE_PX):
                raise ValueError(f"unexpected basemap tile size {tile.size}")
            layer = tile.convert("RGBA")
        # Tiles never overlap: a plain paste (clipped at the edges) is exact
        canvas.paste(layer, (left, top))
    return canvas


# --- next-hour forecast ------------------------------------------------------------

# Levels of a next-hour segment; None is a value nothing understood (muted).
DRY, RAIN_LIGHT, RAIN_MODERATE, RAIN_HEAVY = range(4)
NEXT_HOUR_MINUTES = 60

_PHRASES: dict[str, int] = {
    # Météo-France's 1_hour_forecast
    "temps sec": DRY,
    "pluie faible": RAIN_LIGHT,
    "pluie modérée": RAIN_MODERATE,
    "pluie forte": RAIN_HEAVY,
}
_MINUTE_KEY = re.compile(r"^\s*(\d{1,3})(?:\s*(?:min|mn|m)\b.*)?\s*$", re.IGNORECASE)


def _rate_level(rate: float) -> int | None:
    """A precipitation rate (mm/h) as a level (light < 2.5 <= moderate < 7.6 <= heavy)."""
    if math.isnan(rate) or rate < 0:
        return None
    if rate < 0.1:
        return DRY
    if rate < 2.5:
        return RAIN_LIGHT
    return RAIN_MODERATE if rate < 7.6 else RAIN_HEAVY


def _value_level(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return _rate_level(float(value))
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _PHRASES:
            return _PHRASES[text]
        try:
            return _rate_level(float(text.replace(",", ".")))
        except ValueError:
            return None
    return None


def _minute_of(key: Any) -> int | None:
    if isinstance(key, int) and not isinstance(key, bool):
        return key
    if isinstance(key, str) and (match := _MINUTE_KEY.match(key)):
        return int(match.group(1))
    return None


def parse_next_hour(value: Any) -> list[tuple[int, int, int | None]]:
    """A next-hour forecast attribute as ``(start min, end min, level)`` segments.

    Understands a dict of minute labels to phrases (Météo-France's
    ``1_hour_forecast``: ``{"0 min": "Temps sec", "5 min": "Pluie
    faible", ...}``), a dict of minutes to mm/h numbers, a list of mm/h
    numbers spread evenly over the hour, and a JSON string of any of
    those. A value it doesn't understand gets level None; anything else
    unusable yields no segments.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    points: list[tuple[int, int | None]] = []
    if isinstance(value, dict):
        items = list(value.items())
        minutes = [_minute_of(key) for key, _ in items]
        if any(minute is None for minute in minutes):
            # Keys we can't place in time: keep their order, evenly spaced
            minutes = [round(i * NEXT_HOUR_MINUTES / len(items)) for i in range(len(items))]
        points = [
            (minute, _value_level(item))
            for minute, (_, item) in zip(minutes, items, strict=True)
            if minute is not None
        ]
    elif isinstance(value, list | tuple):
        if not value:
            return []
        span = NEXT_HOUR_MINUTES / len(value)
        points = [(round(i * span), _value_level(item)) for i, item in enumerate(value)]
    else:
        return []

    points = sorted(
        ((m, level) for m, level in points if 0 <= m < NEXT_HOUR_MINUTES), key=lambda p: p[0]
    )
    segments: list[tuple[int, int, int | None]] = []
    for i, (start, level) in enumerate(points):
        end = points[i + 1][0] if i + 1 < len(points) else NEXT_HOUR_MINUTES
        if end > start:
            segments.append((start, end, level))
    return segments
