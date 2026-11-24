"""``radar_tiles``: radar geometry, frame selection, per-cell images, next-hour parsing."""

from __future__ import annotations

import ast
import base64
import io
from pathlib import Path

import pytest
from PIL import Image

from custom_components.geekmagic import radar_tiles
from custom_components.geekmagic.radar_tiles import (
    CLASS_COLORS,
    DRY,
    HEAVY,
    INTENSE,
    LIGHT,
    MODERATE,
    NO_ECHO,
    RAIN_HEAVY,
    RAIN_LIGHT,
    RAIN_MODERATE,
    REGION_PX,
    VIEW_SPAN,
    RadarSnapshot,
    basemap_cover,
    cell_source_size,
    classify_color,
    home_offset,
    mercator_px,
    parse_index,
    parse_next_hour,
    posterize,
    radar_tile_url,
    rounded_location,
    select_frames,
    stitch_basemap,
)

NEWEST = 1_736_937_000


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _decode(uri: str) -> Image.Image:
    assert uri.startswith("data:image/png;base64,")
    image = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    image.load()
    return image


# --- geometry ---------------------------------------------------------------------


def test_mercator_reference_points():
    assert mercator_px(0, 0, 0) == pytest.approx((128, 128))
    assert mercator_px(0, -180, 1) == pytest.approx((0, 256))
    # A 512 px tile at zoom z is the 256 px grid at z + 1
    assert mercator_px(50.0, 8.0, 7, 512) == pytest.approx(mercator_px(50.0, 8.0, 8))
    # Classic XYZ tile of (50, 8) at zoom 8: column 133, row 86
    x, y = mercator_px(50.0, 8.0, 8)
    assert (int(x // 256), int(y // 256)) == (133, 86)


def test_mercator_clamps_latitude():
    assert mercator_px(89.9, 0, 3) == mercator_px(radar_tiles.MAX_LATITUDE, 0, 3)
    assert mercator_px(-90, 0, 3)[1] == pytest.approx(256 * 8)
    assert mercator_px(90, 0, 3)[1] == pytest.approx(0, abs=1e-6)


def test_basemap_cover_tiles_the_box():
    tiles = basemap_cover(50.0, 8.0, 8, REGION_PX, REGION_PX)
    assert 4 <= len(tiles) <= 9
    canvas = Image.new("1", (REGION_PX, REGION_PX), 0)
    for _, _, left, top in tiles:
        canvas.paste(1, (left, top, left + 256, top + 256))
    assert canvas.getextrema() == (1, 1)
    assert all(-256 < left <= 0 or 0 <= left < REGION_PX for _, _, left, _ in tiles)
    assert {(x, y) for x, y, _, _ in tiles} >= {(133, 86)}


def test_basemap_cover_wraps_the_antimeridian_and_skips_beyond_the_poles():
    tiles = basemap_cover(85.0, -180.0, 6, REGION_PX, REGION_PX)
    assert {x for x, _, _, _ in tiles} == {63, 0}
    assert all(y >= 0 for _, y, _, _ in tiles)


def test_rounded_location_never_negative_zero():
    assert rounded_location(-0.04, -0.01) == (0.0, 0.0)
    assert str(rounded_location(-0.04, -0.01)[0]) == "0.0"
    assert rounded_location(50.04, 8.06) == (50.0, 8.1)
    assert rounded_location(10, 190) == (10.0, -170.0)


def test_tile_url_carries_rounded_coordinates_and_clamped_zoom():
    url = radar_tile_url("https://tiles.example", "/v2/radar/abc", 50.04, 7.96, 9)
    assert url == "https://tiles.example/v2/radar/abc/512/7/50.0/8.0/2/1_1.png"


def test_home_offset_signs():
    # Home east of the rounded point: positive x; north of it: negative y
    dx, dy = home_offset(50.04, 8.04, 7)
    assert dx > 0
    assert dy < 0
    dx, dy = home_offset(49.96, 7.96, 7)
    assert dx < 0
    assert dy > 0
    assert home_offset(50.0, 8.0, 7) == pytest.approx((0, 0))
    # 0.04° of longitude at zoom 7 is 0.04 / 360 * 65536 px
    assert home_offset(50.0, 8.04, 7)[0] == pytest.approx(0.04 / 360 * 65536, rel=1e-3)


# --- the index ------------------------------------------------------------------------


def _index(times: list[int]) -> dict:
    return {
        "host": "https://tilecache.example",
        "radar": {"past": [{"time": t, "path": f"/v2/radar/{t}"} for t in times]},
    }


def test_parse_index_sorts_and_skips_garbage():
    data = _index([NEWEST, NEWEST - 600])
    data["radar"]["past"] += [
        {"time": "x", "path": "/a"},
        {"time": 1, "path": "relative"},
        {"time": True, "path": "/b"},
        "garbage",
    ]
    host, frames = parse_index(data) or ("", [])
    assert host == "https://tilecache.example"
    assert frames == [(NEWEST - 600, f"/v2/radar/{NEWEST - 600}"), (NEWEST, f"/v2/radar/{NEWEST}")]


@pytest.mark.parametrize(
    "data",
    [None, [], {}, {"host": "http://insecure", "radar": {"past": []}}, {"host": "https://x"}],
)
def test_parse_index_rejects_unusable_bodies(data):
    assert parse_index(data) is None


def test_select_frames_newest_then_every_second_back():
    frames = [(NEWEST - 600 * i, f"/p{i}") for i in range(13)][::-1]
    picked = select_frames(frames, 7)
    assert [t for t, _ in picked] == [NEWEST - 1200 * k for k in range(6, -1, -1)]
    assert [t for t, _ in select_frames(frames, 4)] == [NEWEST - 1200 * k for k in (3, 2, 1, 0)]
    # A missing frame leaves a gap
    gappy = [f for f in frames if f[0] != NEWEST - 2400]
    assert NEWEST - 2400 not in [t for t, _ in select_frames(gappy, 7)]
    assert select_frames([], 7) == []


# --- images --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rgba", "expected"),
    [
        ((0, 0, 0, 0), NO_ECHO),
        ((99, 97, 89, 20), NO_ECHO),
        ((194, 180, 130, 140), radar_tiles.DRIZZLE),
        ((0, 71, 104, 255), MODERATE),
        ((0, 163, 224, 255), MODERATE),
        ((27, 174, 226, 255), LIGHT),
        ((136, 221, 238, 255), LIGHT),
        ((191, 255, 255, 255), LIGHT),
        ((255, 238, 0, 255), HEAVY),
        ((255, 129, 0, 255), HEAVY),
        ((255, 68, 0, 255), INTENSE),
        ((93, 0, 0, 255), INTENSE),
        ((255, 78, 255, 255), INTENSE),
        ((255, 170, 196, 255), INTENSE),
    ],
)
def test_classify_universal_blue(rgba, expected):
    assert classify_color(rgba) == expected


def test_posterize_uses_the_fixed_palette():
    tile = Image.new("RGBA", (4, 1))
    tile.putdata([(0, 0, 0, 0), (0, 98, 149, 255), (255, 210, 0, 255), (217, 27, 0, 255)])
    classes = posterize(tile)
    assert classes.mode == "P"
    assert list(classes.tobytes()) == [NO_ECHO, MODERATE, HEAVY, INTENSE]
    rgba = classes.convert("RGBA")
    assert rgba.getpixel((0, 0)) == (0, 0, 0, 0)
    assert rgba.getpixel((2, 0)) == (*CLASS_COLORS[HEAVY], 255)


def _tile_with_dot(dx: int, dy: int) -> bytes:
    """A 512 tile with one heavy-rain pixel at (256 + dx, 256 + dy)."""
    tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    tile.putpixel((256 + dx, 256 + dy), (255, 210, 0, 255))
    return _png(tile)


@pytest.mark.parametrize(("width", "height"), [(240, 240), (228, 150), (72, 72), (111, 72)])
def test_cells_are_cropped_around_home(width, height):
    # Home sits 10 px east and 6 px north of the tile centre: the echo
    # drawn exactly at home lands at the middle of every crop.
    snapshot = RadarSnapshot([(NEWEST, _tile_with_dot(10, -6))], (10.0, -6.0))
    cell = snapshot.for_cell(width, height)
    src_w, src_h = cell_source_size(width, height)
    assert cell.src_size == (src_w, src_h)
    assert max(src_w, src_h) == VIEW_SPAN
    frame = _decode(cell.frames[0][1])
    assert frame.size == (src_w, src_h)
    hot = [(x, y) for y in range(src_h) for x in range(src_w) if frame.getpixel((x, y)) == HEAVY]
    assert len(hot) == 1
    x, y = hot[0]
    assert abs(x - src_w / 2) <= 1
    assert abs(y - src_h / 2) <= 1
    assert cell.base_uri is None
    assert cell.labels_uri is None


def test_cell_sizes():
    assert cell_source_size(240, 240) == (267, 267)
    assert cell_source_size(228, 150) == (267, 176)
    assert cell_source_size(72, 72) == (267, 267)


def test_basemap_layers_are_cropped_too():
    base = Image.new("RGBA", (REGION_PX, REGION_PX), (40, 40, 40, 255))
    labels = Image.new("RGBA", (REGION_PX, REGION_PX), (0, 0, 0, 0))
    snapshot = RadarSnapshot([(NEWEST, _tile_with_dot(0, 0))], (0, 0), base, labels)
    cell = snapshot.for_cell(228, 150)
    assert cell.base_uri is not None
    assert cell.labels_uri is not None
    assert _decode(cell.base_uri).size == (267, 176)
    assert _decode(cell.labels_uri).size == (267, 176)


def test_for_cell_is_memoized_per_size():
    snapshot = RadarSnapshot([(NEWEST, _tile_with_dot(0, 0))], (0, 0))
    first = snapshot.for_cell(240, 240)
    assert snapshot.for_cell(240, 240) is first
    assert snapshot.for_cell(120, 120) is not first


def test_corrupt_frame_costs_only_itself():
    snapshot = RadarSnapshot(
        [(NEWEST - 1200, b"not a png"), (NEWEST, _tile_with_dot(0, 0))], (0, 0)
    )
    cell = snapshot.for_cell(120, 120)
    assert [t for t, _ in cell.frames] == [NEWEST]


def test_stitch_basemap_places_tiles():
    red = _png(Image.new("RGB", (256, 256), (200, 0, 0)))
    blue = _png(Image.new("RGB", (256, 256), (0, 0, 200)))
    canvas = stitch_basemap([(-100, -100, red), (156, -100, blue)], 200, 200)
    assert canvas.getpixel((10, 10)) == (200, 0, 0, 255)
    assert canvas.getpixel((190, 10)) == (0, 0, 200, 255)
    assert canvas.getpixel((10, 190)) == (0, 0, 0, 0)


def test_radar_tiles_is_ha_free():
    source = Path(radar_tiles.__file__).read_text(encoding="utf-8")
    modules = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(m.startswith(("homeassistant", "aiohttp")) for m in modules)


# --- next-hour forecast ---------------------------------------------------------------


def test_meteo_france_phrases():
    forecast = {
        "0 min": "Temps sec",
        "5 min": "Temps sec",
        "10 min": "Pluie faible",
        "15 min": "Pluie modérée",
        "20 min": "Pluie forte",
        "25 min": "Pluie forte",
        "35 min": "Pluie faible",
        "45 min": "Temps sec",
        "55 min": "Neige",
    }
    assert parse_next_hour(forecast) == [
        (0, 5, DRY),
        (5, 10, DRY),
        (10, 15, RAIN_LIGHT),
        (15, 20, RAIN_MODERATE),
        (20, 25, RAIN_HEAVY),
        (25, 35, RAIN_HEAVY),
        (35, 45, RAIN_LIGHT),
        (45, 55, DRY),
        (55, 60, None),
    ]


def test_numeric_dict_and_list():
    assert parse_next_hour({"0": 0, "30": 1.2, "45": "8"}) == [
        (0, 30, DRY),
        (30, 45, RAIN_LIGHT),
        (45, 60, RAIN_HEAVY),
    ]
    assert parse_next_hour([0, 3.0, 0.5, 10]) == [
        (0, 15, DRY),
        (15, 30, RAIN_MODERATE),
        (30, 45, RAIN_LIGHT),
        (45, 60, RAIN_HEAVY),
    ]


def test_json_string_and_unplaceable_keys():
    assert parse_next_hour('{"0 min": "Pluie faible"}') == [(0, 60, RAIN_LIGHT)]
    # Keys that aren't minutes keep their order, spread over the hour
    assert parse_next_hour({"soon": 0, "later": 5}) == [(0, 30, DRY), (30, 60, RAIN_MODERATE)]


@pytest.mark.parametrize(
    "value",
    [None, "", "Temps sec", 42, [], {}, object(), b"bytes", {"90 min": 1}],
)
def test_garbage_forecasts_yield_no_segments(value):
    assert parse_next_hour(value) == []


def test_unknown_values_are_muted_not_dropped():
    assert parse_next_hour([None, True, "?", -1]) == [
        (0, 15, None),
        (15, 30, None),
        (30, 45, None),
        (45, 60, None),
    ]
