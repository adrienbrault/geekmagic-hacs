"""Rain Radar widget: the last hours of RainViewer radar around home, animated.

The frames, basemap and crop come from ``WidgetState.radar`` (a
``radar_tiles.RadarCell`` already cut to this cell's size, every image
centred on the location); this module only lays them out. Pure HTML,
no fetching.

Layers, bottom to top: the basemap, one image per radar frame (only one
visible at a time), the basemap's place names, a home marker, the frame's
time in a capsule, a timeline bar (past frames, the "now" line and an
optional next-hour forecast) and the attribution.

Animation: the GIF loop is ``LOOP_SECONDS`` sampled at the shared frame
grid (``animation.frame_timing``: 28 ticks at 7 fps). The NEWEST frame
holds the first ticks, so the still frame (t = 0) shows it, then the
older frames play oldest first, a few ticks each. Every keyframe edge
sits half-way between two ticks, so no GIF frame catches a cross-fade.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..animation import frame_timing
from ..htmldoc import css_rgba
from ..radar_tiles import (
    DRY,
    FRAME_STEP_SECONDS,
    NEXT_HOUR_MINUTES,
    RAIN_HEAVY,
    RAIN_LIGHT,
    RAIN_MODERATE,
    parse_next_hour,
)
from .base import Widget, WidgetConfig
from .camera import placeholder_html

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ..radar_tiles import RadarCell
    from .state import WidgetState

LOOP_SECONDS = 4.0
# Zoom choice -> RainViewer zoom (the basemap is one level deeper)
ZOOMS: dict[str, int] = {"close": 7, "medium": 6, "wide": 5}
DEFAULT_ZOOM = "Close"
PERIODS: dict[str, int] = {"1 hour": 4, "2 hours": 7}
DEFAULT_PERIOD = "2 hours"
DEFAULT_FORECAST_ATTRIBUTE = "1_hour_forecast"
# The newest frame turns the time label to the warning tint past this age
STALE_SECONDS = 30 * 60
# Ticks given to each older frame, out of the GIF's 28; the newest frame
# holds the rest.
_OLDER_FRAME_TICKS = 20
# Geometry is designed at a 240 px cell and scales with its long side
_DESIGN_PX = 240.0


def _number(value: Any, low: float, high: float) -> float | None:
    """A stored number option within [low, high], or None (blank, garbage)."""
    if value is None or isinstance(value, bool) or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not low <= number <= high:
        return None
    return number


def _choice(value: Any, choices: dict[str, int], default: str) -> int:
    key = str(value).strip().lower() if value is not None else ""
    return choices.get(key, choices[default.lower()])


def tick_windows(frame_count: int, ticks: int) -> tuple[list[tuple[float, float]], int]:
    """Visible window of each older frame, in ticks, and the newest frame's hold.

    Older frames (oldest first) get ``step`` ticks each and the newest
    frame holds ticks ``0 .. hold - 1``; windows are ``[start, end)`` on
    half ticks. With 7 frames over 28 ticks: hold 10, step 3.
    """
    older = frame_count - 1
    if older <= 0:
        return [], ticks
    step = max(1, _OLDER_FRAME_TICKS // older)
    hold = ticks - step * older
    if hold < 1:
        step = max(1, (ticks - 1) // older)
        hold = ticks - step * older
    windows = [(hold + j * step - 0.5, hold + (j + 1) * step - 0.5) for j in range(older)]
    return windows, hold


def _pct(value: float) -> str:
    return f"{value:.2f}%"


def _window_keyframes(name: str, start: float, end: float) -> str:
    """Opacity 1 within [start, end] percent, 0 outside, with hard edges."""
    steps = []
    if start > 0:
        steps.append(f"0%,{_pct(start - 0.01)}{{opacity:0}}")
    steps.append(f"{_pct(start)},{_pct(end - 0.01) if end < 100 else '100%'}{{opacity:1}}")
    if end < 100:
        steps.append(f"{_pct(end)},100%{{opacity:0}}")
    return f"@keyframes {name}{{{''.join(steps)}}}"


def _newest_keyframes(name: str, hold_end: float, wrap_start: float) -> str:
    """Opacity 1 from 0 to ``hold_end`` percent and again from ``wrap_start``."""
    steps = [f"0%,{_pct(hold_end - 0.01)}{{opacity:1}}"]
    if wrap_start < 100:
        steps.append(f"{_pct(hold_end)},{_pct(wrap_start - 0.01)}{{opacity:0}}")
        steps.append(f"{_pct(wrap_start)},100%{{opacity:1}}")
    else:
        steps.append(f"{_pct(hold_end)},100%{{opacity:0}}")
    return f"@keyframes {name}{{{''.join(steps)}}}"


class RadarWidget(Widget):
    """Animated rain radar centred on the Home Assistant location."""

    WIDGET_TYPE: ClassVar[str] = "radar"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Rain Radar",
        "icon": "mdi:radar",
        "category": "time",
        "description": "Animated rain radar around home (RainViewer)",
        "uses_label": False,
        "needs_entity": False,
        "options": [
            {
                "key": "zoom",
                "type": "select",
                "label": "Zoom",
                "options": ["Close", "Medium", "Wide"],
                "default": DEFAULT_ZOOM,
            },
            {
                "key": "period",
                "type": "select",
                "label": "Period",
                "options": list(PERIODS),
                "default": DEFAULT_PERIOD,
            },
            {
                "key": "animate",
                "type": "boolean",
                "label": "Animate (needs the device's Animations switch)",
                "default": True,
            },
            {"key": "show_time", "type": "boolean", "label": "Show Time", "default": True},
            {"key": "show_timeline", "type": "boolean", "label": "Show Timeline", "default": True},
            {
                "key": "forecast_entity",
                "type": "entity",
                "label": "Next-Hour Forecast Entity (optional)",
            },
            {
                "key": "forecast_attribute",
                "type": "text",
                "label": "Forecast Attribute",
                "placeholder": DEFAULT_FORECAST_ATTRIBUTE,
            },
            {
                "key": "latitude",
                "type": "number",
                "label": "Latitude (blank: home)",
                "min": -85,
                "max": 85,
            },
            {
                "key": "longitude",
                "type": "number",
                "label": "Longitude (blank: home)",
                "min": -180,
                "max": 180,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Read the options; anything unreadable falls back to its default."""
        super().__init__(config)
        options = config.options
        self.zoom = _choice(options.get("zoom"), ZOOMS, DEFAULT_ZOOM)
        self.frame_count = _choice(options.get("period"), PERIODS, DEFAULT_PERIOD)
        self.animate = bool(options.get("animate", True))
        self.show_time = bool(options.get("show_time", True))
        self.show_timeline = bool(options.get("show_timeline", True))
        entity = options.get("forecast_entity")
        self.forecast_entity = (
            entity.strip() if isinstance(entity, str) and entity.strip() else None
        )
        attribute = options.get("forecast_attribute")
        self.forecast_attribute = (
            attribute.strip()
            if isinstance(attribute, str) and attribute.strip()
            else DEFAULT_FORECAST_ATTRIBUTE
        )
        lat = _number(options.get("latitude"), -85.0, 85.0)
        lon = _number(options.get("longitude"), -180.0, 180.0)
        # Both or neither: half a location is no location
        self.location: tuple[float, float] | None = (
            (lat, lon) if lat is not None and lon is not None else None
        )

    @property
    def frames_to_fetch(self) -> int:
        """Frames the snapshot needs: the period's, or only the newest when still."""
        return self.frame_count if self.animate else 1

    def is_animated(self) -> bool:
        """Animated unless the user turned it off."""
        return self.animate

    def animation_seconds(self) -> float | None:
        """The frames need the longest loop the device plays."""
        return LOOP_SECONDS if self.animate else None

    def get_entities(self) -> list[str]:
        """The next-hour forecast entity, when one is set."""
        return [self.forecast_entity] if self.forecast_entity else []

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the radar map, or a placeholder until frames arrive."""
        cell = state.radar
        if cell is None or not cell.frames:
            return placeholder_html(ctx, "radar", "Radar")
        return self._radar_html(ctx, state, cell)

    def _next_hour(self, state: WidgetState) -> list[tuple[int, int, int | None]] | None:
        """Next-hour segments; None when no forecast entity is configured."""
        if not self.forecast_entity:
            return None
        entity = state.get_entity(self.forecast_entity)
        if entity is None:
            return []
        return parse_next_hour(entity.get(self.forecast_attribute))

    def _radar_html(self, ctx: CellContext, state: WidgetState, cell: RadarCell) -> str:
        width, height = ctx.width, ctx.height
        short = min(width, height)
        s = max(width, height) / _DESIGN_PX
        frames = cell.frames[-self.frame_count :] if self.animate else cell.frames[-1:]
        count = len(frames)
        animated = self.animate and count > 1

        timing = frame_timing(LOOP_SECONDS)
        windows, hold = tick_windows(count, timing.frame_count)
        ticks = timing.frame_count
        css: list[str] = []
        anims: list[str] = []
        for k in range(count):
            if not animated:
                anims.append("")
                continue
            name = f"rf{k}"
            if k == count - 1:
                css.append(
                    _newest_keyframes(
                        name, (hold - 0.5) / ticks * 100, windows[-1][1] / ticks * 100
                    )
                )
            else:
                start, end = windows[k]
                css.append(_window_keyframes(name, start / ticks * 100, end / ticks * 100))
            # The newest frame is visible without its animation too: the
            # still frame never depends on evaluating keyframes at t = 0
            hidden = "" if k == count - 1 else "opacity:0;"
            anims.append(f"{hidden}animation:{name} {timing.loop_seconds:g}s linear infinite;")

        fill = (
            "position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:block;"
        )
        parts: list[str] = []
        if cell.base_uri:
            parts.append(f'<img src="{cell.base_uri}" style="{fill}">')
        parts.extend(
            f'<img src="{uri}" style="{fill}{anim}">'
            for (_, uri), anim in zip(frames, anims, strict=True)
        )
        if cell.labels_uri and short >= 130:
            parts.append(f'<img src="{cell.labels_uri}" style="{fill}">')

        marker = max(5.0, round(8 * s))
        parts.append(
            f'<div style="position:absolute;left:50%;top:50%;width:{marker:g}px;'
            f"height:{marker:g}px;margin-left:{-marker / 2 - 1:g}px;"
            f"margin-top:{-marker / 2 - 1:g}px;border-radius:50%;background:var(--error);"
            'border:1px solid rgba(255,255,255,0.9)"></div>'
        )

        tz = state.now.tzinfo if state.now is not None and state.now.tzinfo else UTC
        newest_time = frames[-1][0]
        stale = state.now is not None and state.now.timestamp() - newest_time > STALE_SECONDS
        if self.show_time and width >= 100:
            parts.extend(self._time_capsules(frames, anims, tz, s, stale=stale))

        inset = max(4.0, 6 * s)
        bar_bottom = max(3.0, 5 * s)
        bar_h = max(4.0, round(7 * s))
        timeline_html = ""
        if self.show_timeline and short >= 100:
            timeline_html = self._timeline_html(
                ctx, state, frames, anims, inset=inset, bottom=bar_bottom, height=bar_h, s=s
            )
        timeline = bool(timeline_html)
        parts.append(timeline_html)

        if short >= 130:
            attribution = "RainViewer · Esri" if cell.base_uri else "RainViewer"
            bottom = bar_bottom + bar_h + 3 * s if timeline else inset
            font = max(7.0, round(7.5 * s, 1))
            parts.append(
                f'<div style="position:absolute;right:{inset:g}px;bottom:{bottom:.1f}px;'
                f"font-size:{font:g}px;line-height:1.2;font-weight:600;"
                "color:rgba(255,255,255,0.7);background:rgba(0,0,0,0.45);"
                f'border-radius:3px;padding:0 0.35em;white-space:nowrap">{attribution}</div>'
            )

        style = f"<style>{''.join(css)}</style>" if css else ""
        return (
            f"{style}"
            '<div style="position:relative;width:100%;height:100%;overflow:hidden;'
            'border-radius:inherit;background:var(--surface)">'
            f"{''.join(parts)}"
            "</div>"
        )

    def _time_capsules(
        self,
        frames: tuple[tuple[int, str], ...],
        anims: list[str],
        tz: Any,
        s: float,
        *,
        stale: bool,
    ) -> list[str]:
        """One capsule per frame with its time; only the visible frame's shows."""
        font = max(9.0, min(13.0, round(11 * s, 1)))
        inset = max(4.0, round(6 * s, 1))
        color = "var(--warning)" if stale else "rgba(255,255,255,0.95)"
        capsules = []
        for (stamp, _), anim in zip(frames, anims, strict=True):
            label = datetime.fromtimestamp(stamp, tz).strftime("%H:%M")
            capsules.append(
                f'<div style="position:absolute;top:{inset:g}px;left:{inset:g}px;'
                "background:rgba(0,0,0,0.55);border:1px solid rgba(255,255,255,0.12);"
                f"border-radius:999px;padding:0.2em 0.6em;font-size:{font:g}px;"
                f"font-weight:700;line-height:1.25;color:{color};white-space:nowrap;"
                f'{anim}">{escape(label)}</div>'
            )
        return capsules

    def _timeline_html(
        self,
        ctx: CellContext,
        state: WidgetState,
        frames: tuple[tuple[int, str], ...],
        anims: list[str],
        *,
        inset: float,
        bottom: float,
        height: float,
        s: float,
    ) -> str:
        """Past frames on a bar, the "now" line, and the next hour when known.

        A still radar has no past to show: its bar is the next hour alone
        (nothing at all without a forecast entity).
        """
        next_hour = self._next_hour(state)
        newest = frames[-1][0]
        past = max(1, self.frame_count - 1) * FRAME_STEP_SECONDS if self.animate else 0
        total = past + (NEXT_HOUR_MINUTES * 60 if next_hour is not None else 0)
        if total == 0:
            return ""
        start = newest - past
        now_pct = past / total * 100

        theme = ctx.theme
        light = css_rgba(theme.info, 0.5) if theme is not None else "var(--info)"
        colors = {
            DRY: "rgba(255,255,255,0.14)",
            RAIN_LIGHT: light,
            RAIN_MODERATE: "var(--info)",
            RAIN_HEAVY: "var(--secondary)",
        }
        inner = []
        if past:
            inner.append(
                f'<div style="position:absolute;left:0;top:35%;height:30%;width:{_pct(now_pct)};'
                'background:rgba(255,255,255,0.35);border-radius:2px"></div>'
            )
        for seg_start, seg_end, level in next_hour or []:
            left = (past + seg_start * 60) / total * 100
            span = (seg_end - seg_start) * 60 / total * 100
            color = colors.get(level, "var(--muted)") if level is not None else "var(--muted)"
            inner.append(
                f'<div style="position:absolute;top:0;bottom:0;left:{_pct(left)};'
                f'width:{_pct(span)};background:{color}"></div>'
            )
        inner.append(
            f'<div style="position:absolute;left:{_pct(now_pct)};top:-2px;bottom:-2px;'
            'width:2px;margin-left:-1px;background:rgba(255,255,255,0.9)"></div>'
        )
        cursor = max(3.0, round(5 * s))
        for (stamp, _), anim in zip(frames if past else (), anims, strict=False):
            pos = min(100.0, max(0.0, (stamp - start) / total * 100))
            inner.append(
                f'<div style="position:absolute;left:{_pct(pos)};top:-2px;bottom:-2px;'
                f"width:{cursor:g}px;margin-left:{-cursor / 2:g}px;border-radius:2px;"
                f'background:var(--warning);{anim}"></div>'
            )
        return (
            f'<div style="position:absolute;left:{inset:g}px;right:{inset:g}px;'
            f"bottom:{bottom:g}px;height:{height:g}px;border-radius:{height / 2:g}px;"
            f'background:rgba(0,0,0,0.55)">{"".join(inner)}</div>'
        )
