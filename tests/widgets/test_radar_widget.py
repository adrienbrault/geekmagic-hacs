"""Rain Radar widget: placeholder, frame timing, size rules and GIF budget."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.geekmagic.animation import frame_timing
from custom_components.geekmagic.const import MAX_IMAGE_SIZE
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.hero_simple import HeroSimpleLayout
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.view import render_still
from custom_components.geekmagic.widgets import RadarWidget, WidgetConfig, build_widget
from custom_components.geekmagic.widgets.radar import LOOP_SECONDS, tick_windows
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import get_theme
from scripts.generate_samples import create_fake_radar

NEWEST = datetime(2026, 11, 16, 8, 20, tzinfo=UTC)
NOW = NEWEST + timedelta(minutes=6)
THEME = get_theme("watchos")


@pytest.fixture(scope="module")
def snapshot():
    return create_fake_radar(NEWEST)


@pytest.fixture(scope="module")
def heavy():
    return create_fake_radar(NEWEST, heavy=True)


def _widget(**options) -> RadarWidget:
    return RadarWidget(WidgetConfig(widget_type="radar", slot=0, options=options))


def _ctx(width: int, height: int) -> CellContext:
    return CellContext(width=width, height=height, slot_index=0, theme=THEME)


def _render(widget, snapshot, width=240, height=240, *, now=NOW, entities=None) -> str:
    cell = snapshot.for_cell(width, height) if snapshot is not None else None
    state = WidgetState(radar=cell, now=now, entities=entities or {})
    return widget.render_html(_ctx(width, height), state)


# --- options ----------------------------------------------------------------------


def test_defaults():
    widget = _widget()
    assert widget.zoom == 7
    assert widget.frame_count == 7
    assert widget.is_animated()
    assert widget.animation_seconds() == LOOP_SECONDS
    assert widget.location is None
    assert widget.get_entities() == []


def test_options():
    widget = _widget(
        zoom="Wide",
        period="1 hour",
        animate=False,
        latitude=50,
        longitude="8.5",
        forecast_entity="sensor.next_rain",
    )
    assert widget.zoom == 5
    assert widget.frame_count == 4
    assert not widget.is_animated()
    assert widget.animation_seconds() is None
    assert widget.location == (50.0, 8.5)
    assert widget.get_entities() == ["sensor.next_rain"]


@pytest.mark.parametrize(
    "options",
    [
        {"latitude": 50},
        {"latitude": "", "longitude": ""},
        {"latitude": 91, "longitude": 8},
        {"latitude": "x", "longitude": 8},
        {"latitude": float("nan"), "longitude": 8},
    ],
)
def test_incomplete_or_invalid_location_means_home(options):
    assert _widget(**options).location is None


def test_garbage_options_build():
    widget = build_widget(
        {
            "type": "radar",
            "options": {"zoom": 3, "period": None, "forecast_entity": 7, "latitude": []},
        }
    )
    assert isinstance(widget, RadarWidget)
    assert widget.zoom == 7
    assert widget.frame_count == 7


# --- placeholder ------------------------------------------------------------------


@pytest.mark.parametrize("size", [240, 120, 72])
def test_placeholder_without_frames(size):
    html = _render(_widget(), None, size, size)
    assert "RADAR" in html.upper()
    assert "<img" not in html


# --- frame timing -----------------------------------------------------------------


def test_tick_windows():
    windows, hold = tick_windows(7, 28)
    assert hold == 10
    assert windows[0] == (9.5, 12.5)
    assert windows[-1] == (24.5, 27.5)
    windows, hold = tick_windows(4, 28)
    assert hold == 10
    assert [end for _, end in windows] == [15.5, 21.5, 27.5]


def _keyframes(html: str) -> dict[str, str]:
    return dict(re.findall(r"@keyframes (\w+)\{(.*?\})\}", html))


@pytest.mark.parametrize("period", ["1 hour", "2 hours"])
def test_newest_frame_shows_first_and_edges_avoid_ticks(snapshot, period):
    html = _render(_widget(period=period), snapshot)
    frames = _keyframes(html)
    count = 4 if period == "1 hour" else 7
    assert len(frames) == count
    newest = frames[f"rf{count - 1}"]
    assert newest.startswith("0%,")
    assert newest.split("{", 1)[1].startswith("opacity:1")
    ticks = frame_timing(LOOP_SECONDS).frame_count
    assert ticks == 28
    for name, body in frames.items():
        for pct in re.findall(r"([\d.]+)%", body):
            value = float(pct)
            if value in (0.0, 100.0):
                continue
            tick = value / 100 * ticks
            assert abs(tick - round(tick)) > 0.1, (name, value)
        # Older frames start hidden
        if name != f"rf{count - 1}":
            assert body.startswith("0%,") and body.split("{", 1)[1].startswith("opacity:0")


def test_exactly_one_frame_visible_on_every_tick(snapshot):
    html = _render(_widget(), snapshot)
    frames = _keyframes(html)
    ticks = frame_timing(LOOP_SECONDS).frame_count

    def visible(body: str, pct: float) -> bool:
        for selectors, value in re.findall(r"([\d.%,]+)\{opacity:(\d)\}", body):
            bounds = [float(p.rstrip("%")) for p in selectors.split(",")]
            if bounds[0] <= pct <= bounds[-1]:
                return value == "1"
        raise AssertionError(pct)

    for tick in range(ticks):
        pct = tick / ticks * 100
        shown = [name for name, body in frames.items() if visible(body, pct)]
        assert len(shown) == 1, (tick, shown)
    assert [name for name, body in frames.items() if visible(body, 0.0)] == ["rf6"]


def test_still_shows_only_the_newest_frame(snapshot):
    html = _render(_widget(animate=False), snapshot)
    assert "@keyframes" not in html
    assert (
        html.count('style="position:absolute;left:0;top:0;width:100%') == 3
    )  # base, frame, labels
    assert "08:20" in html


def test_labels_use_frame_times_in_the_frame_timezone(snapshot):
    paris = NOW.astimezone(ZoneInfo("Europe/Paris"))
    html = _render(_widget(), snapshot, now=paris)
    assert "09:20" in html  # newest frame, UTC+1
    assert "07:20" in html  # oldest, two hours earlier
    # Unchanged data renders identical bytes, however late the frame
    assert html == _render(_widget(), snapshot, now=paris + timedelta(minutes=2))


def test_stale_label_turns_warning(snapshot):
    assert "var(--warning);white-space" not in _render(_widget(), snapshot)
    late = _render(_widget(), snapshot, now=NEWEST + timedelta(minutes=45))
    assert "color:var(--warning)" in late


# --- size rules -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "capsule", "timeline", "labels"),
    [
        ((240, 240), True, True, True),
        ((228, 150), True, True, True),
        ((111, 111), True, True, False),
        ((228, 76), True, False, False),
        ((72, 72), False, False, False),
    ],
)
def test_cell_size_rules(snapshot, size, capsule, timeline, labels):
    html = _render(_widget(), snapshot, *size)
    assert "background:var(--error)" in html  # home marker, always
    assert ("08:20" in html) is capsule
    assert ('background:rgba(0,0,0,0.55)">' in html) is timeline
    assert ("RainViewer" in html) is labels
    images = html.count("<img")
    assert images == 1 + 7 + (1 if labels else 0)


def test_next_hour_segments(snapshot):
    forecast = EntityState(
        "sensor.next_rain",
        "x",
        {"1_hour_forecast": {"0 min": "Temps sec", "20 min": "Pluie forte", "40 min": "??"}},
    )
    html = _render(
        _widget(forecast_entity="sensor.next_rain"),
        snapshot,
        entities={"sensor.next_rain": forecast},
    )
    assert "background:var(--secondary)" in html
    assert "background:var(--muted)" in html
    # Two hours of past then one of forecast: "now" at two thirds
    assert "left:66.67%" in html


def test_no_hex_colours(snapshot):
    html = _render(_widget(forecast_entity="sensor.x"), snapshot)
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", re.sub(r'src="[^"]*"', "", html))


# --- rendered ---------------------------------------------------------------------


def _states(layout, snapshot):
    states = {}
    for slot in layout.slots:
        if slot.widget is None:
            continue
        x1, y1, x2, y2 = slot.rect
        states[slot.index] = WidgetState(radar=snapshot.for_cell(x2 - x1, y2 - y1), now=NOW)
    return states


def test_still_render_is_the_first_animation_frame(snapshot):
    renderer = Renderer()
    layout = FullscreenLayout()
    layout.set_widget(0, _widget())
    states = _states(layout, snapshot)
    timing = frame_timing(LOOP_SECONDS)
    frames = layout.render_animation(renderer, states, list(timing.times[:11]))
    assert frames is not None
    still = render_still(renderer, layout, states)
    assert still.tobytes() == frames[0].tobytes()
    # The newest frame holds the first ten ticks, then the oldest takes over
    assert frames[9].tobytes() == frames[0].tobytes()
    assert frames[10].tobytes() != frames[0].tobytes()


@pytest.mark.parametrize("layout_class", [FullscreenLayout, HeroSimpleLayout])
def test_heavy_rain_gif_fits_the_upload_budget(heavy, layout_class):
    renderer = Renderer()
    layout = layout_class()
    layout.theme = get_theme("neon")  # the glow pass is the costliest
    layout.set_widget(0, _widget())
    timing = frame_timing(LOOP_SECONDS)
    frames = layout.render_animation(renderer, _states(layout, heavy), list(timing.times))
    assert frames is not None
    gif = renderer.to_gif(frames, fps=timing.fps)
    assert len(gif) < MAX_IMAGE_SIZE / 2


def test_newest_frame_is_visible_without_animation(snapshot):
    html = _render(_widget(), snapshot)
    styles = re.findall(r'<img src="data:[^"]*" style="([^"]*)"', html)
    frame_styles = [st for st in styles if "animation:" in st]
    assert len(frame_styles) == 7
    assert "opacity:0" not in frame_styles[-1]
    assert all("opacity:0" in st for st in frame_styles[:-1])


def test_still_radar_fetches_and_shows_only_now(snapshot):
    still = _widget(animate=False)
    assert still.frames_to_fetch == 1
    assert _widget().frames_to_fetch == 7
    assert _widget(period="1 hour").frames_to_fetch == 4
    # No past to show: no timeline without a forecast...
    assert "background:var(--warning)" not in _render(still, snapshot)
    # ...and only the next hour with one, "now" at its left edge
    forecast = EntityState("sensor.next_rain", "x", {"1_hour_forecast": [0, 3.0]})
    html = _render(
        _widget(animate=False, forecast_entity="sensor.next_rain"),
        snapshot,
        entities={"sensor.next_rain": forecast},
    )
    assert "left:0.00%;top:-2px" in html
    assert "left:50.00%" in html
    assert "background:var(--warning)" not in html


def _light_rain_snapshot(snapshot):
    """Rain without a single red pixel: nothing else in the GIF is red."""
    from io import BytesIO

    from PIL import Image, ImageDraw

    from custom_components.geekmagic.radar_tiles import RadarSnapshot

    rings = [
        ((194, 180, 130, 140), 200),
        ((108, 209, 235, 255), 150),
        ((0, 154, 213, 255), 100),
        ((0, 85, 136, 255), 50),
    ]
    tiles = []
    for k, (stamp, _) in enumerate(snapshot.frames):
        tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)
        for color, radius in rings:
            cx = 180 + 8 * k
            draw.ellipse((cx - radius, 300 - radius, cx + radius, 300 + radius), fill=color)
        buf = BytesIO()
        tile.save(buf, format="PNG")
        tiles.append((stamp, buf.getvalue()))
    return RadarSnapshot(tiles, (0, 0), snapshot.base, snapshot.labels)


@pytest.mark.parametrize("theme", ["watchos", "classic"])
@pytest.mark.parametrize("layout_class", [FullscreenLayout, HeroSimpleLayout])
def test_home_marker_stays_red_in_the_gif(snapshot, theme, layout_class):
    """The few marker pixels keep their own palette entry instead of turning tan."""
    from io import BytesIO

    from PIL import Image

    renderer = Renderer()
    layout = layout_class()
    layout.theme = get_theme(theme)
    layout.set_widget(0, _widget())
    timing = frame_timing(LOOP_SECONDS)
    states = _states(layout, _light_rain_snapshot(snapshot))
    frames = layout.render_animation(renderer, states, list(timing.times))
    assert frames is not None
    gif = renderer.to_gif(frames, fps=timing.fps, keep_colors=layout.animation_key_colors())
    first = Image.open(BytesIO(gif)).convert("RGB")
    x1, y1, x2, y2 = layout.slots[0].rect
    pixel = first.getpixel(((x1 + x2) // 2, (y1 + y2) // 2))
    assert isinstance(pixel, tuple)
    r, g, b = pixel[:3]
    assert r >= 220, (r, g, b)
    assert r - max(g, b) >= 100, (r, g, b)


@pytest.mark.parametrize("theme", ["watchos", "classic"])
@pytest.mark.parametrize("layout_class", [FullscreenLayout, HeroSimpleLayout])
def test_timeline_cursor_keeps_its_colour_in_the_gif(snapshot, theme, layout_class):
    """The timeline cursor's few pixels keep the theme's warning colour."""
    from io import BytesIO

    from PIL import Image

    renderer = Renderer()
    layout = layout_class()
    layout.theme = get_theme(theme)
    layout.set_widget(0, _widget())
    timing = frame_timing(LOOP_SECONDS)
    states = _states(layout, _light_rain_snapshot(snapshot))
    frames = layout.render_animation(renderer, states, list(timing.times))
    assert frames is not None
    gif = renderer.to_gif(frames, fps=timing.fps, keep_colors=layout.animation_key_colors())
    first = Image.open(BytesIO(gif)).convert("RGB")
    warning = tuple(layout.theme.warning[:3])
    exact = sum(1 for pixel in first.getdata() if pixel == warning)
    assert exact >= 10, (warning, exact)
