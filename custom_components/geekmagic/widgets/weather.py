"""Weather widget for GeekMagic displays."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import mdi_span
from ._cardfit import (
    HERO_SHARE_SOLO,
    HERO_SHARE_STACKED,
    fit_caption_sized,
    fit_hero,
    hero_block,
)
from ._cellkit import caption_visible, cell_box, chip_band_px, label_px
from .base import Widget, WidgetConfig
from .state import DataNeeds

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState


WEATHER_ICONS = {
    "sunny": "weather-sunny",
    "clear-night": "weather-night",
    "partlycloudy": "weather-partly-cloudy",
    "cloudy": "weather-cloudy",
    "rainy": "weather-rainy",
    "pouring": "weather-pouring",
    "snowy": "weather-snowy",
    "snowy-rainy": "weather-snowy-rainy",
    "fog": "weather-fog",
    "hail": "weather-hail",
    "windy": "weather-windy",
    "windy-variant": "weather-windy-variant",
    "lightning": "weather-lightning",
    "lightning-rainy": "weather-lightning-rainy",
    "exceptional": "alert-circle",
}

# Condition → theme palette CSS variable. Each weather condition resolves
# to a role on the active theme so candy/retro/neon/etc. show tints from
# their own palette, not hardcoded watchOS-system colors.
#
# Mapping rationale:
#   sunny / hot      → warning  (orange-ish on most themes)
#   clear-night      → secondary
#   cloudy / partly  → primary  (uses the theme's brand accent)
#   rain / snow / hail → info   (cool/water/data role — themes that
#                                 lack blue map this to mint/cyan/etc.)
#   wind             → success
#   lightning        → secondary
#   exceptional      → error
#   fog              → muted
WEATHER_COLORS: dict[str, str] = {
    "sunny": "var(--warning)",
    "clear-night": "var(--secondary)",
    "partlycloudy": "var(--primary)",
    "cloudy": "var(--primary)",
    "rainy": "var(--info)",
    "pouring": "var(--info)",
    "snowy": "var(--info)",
    "snowy-rainy": "var(--info)",
    "fog": "var(--muted)",
    "hail": "var(--info)",
    "windy": "var(--success)",
    "windy-variant": "var(--success)",
    "lightning": "var(--secondary)",
    "lightning-rainy": "var(--secondary)",
    "exceptional": "var(--error)",
}


# Weekday abbreviations
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The forecast strip needs a column per day plus legible numerals; below
# this width the columns collide, so the strip drops out entirely. This
# is the strip's own geometry, not the kit's ``.hide-small`` breakpoint
# it happens to equal (``_cellkit.HIDE_SMALL``): the strip is a
# Python-placed band, and its sibling chip row deliberately runs down to
# 100x70. Retune these for the columns, never to track the kit.
_STRIP_MIN_W = 130
_STRIP_MIN_H = 130

# A cell narrower than _STRIP_MIN_W can still carry the forecast if it is
# tall enough to list the days as rows (split-v columns are 114x228).
_LIST_MIN_H = 190

# The width at which a cell stops being a tile and starts being a row:
# wide enough for a column per forecast day, for the hi/lo pair, and for
# the icon to sit beside the value instead of over it.
_COMPACT_MIN_W = 100

# Short-wide cells (a hero footer, a 2x3 tile) have no room for day
# names or lows, but three tinted glyphs with their highs still read as
# a forecast — and beat a lone temperature floating in an empty band.
_MINI_MIN_H = 58
_MINI_DAYS = 3
# The mini strip regains its day names when the cell can spend ~12px on
# them (a 224x108 split cell can; a 108x69 tile cannot), and its lows
# when the columns are wide enough to set "26° 17°" side by side.
_MINI_DAY_MIN_H = 92
_MINI_LO_COL_W = 60

# DAY + icon + hi + lo needs ~86px on one row. Narrower than this the
# columns collide: the day wraps under the icon and the low bleeds past
# the cell edge (Blitz clips neither), so the row tightens and sheds the
# low instead.
_LIST_MIN_W = 88

# Cells at least this wide put the condition icon *beside* the hero
# instead of above it — the icon then reads at poster size and the
# temperature still owns the middle of the cell.
_SIDE_BY_SIDE_MIN_W = 170
# ...and cells too short to stack do the same whatever their width: a
# 111x72 tile has no vertical room for icon over value.
_STACK_MIN_H = 95

# Icon geometry, mirroring .wx-icon's clamp so Python can reserve for it.
_ICON_MIN_PX = 15.0
_ICON_MAX_PX = 78.0
_ICON_VMIN = 0.33
# Stacked, the icon may take at most half the pair's band. The CSS clamp
# alone knows nothing about what sits underneath, so in a 148px cell
# carrying a forecast strip it claims 49px of a 40px band and pushes the
# strip's bottom row off the cell.
_STACK_ICON_SHARE = 0.5
# With nothing under it the hero is sized from the free HEIGHT instead:
# side by side, icon + value saturate the cell's WIDTH at about a third
# of its height and strand the rest.
_SOLO_ICON_SHARE = 0.42
_SOLO_ICON_MAX_PX = 132.0
_SOLO_STACK_RATIO = 0.8

# Today's hi/lo chips. They run narrower than the kit's 130px so 2x2
# tiles carry the pair; below _CHIP_ARROWS_MIN_W the ↑/↓ glyphs cost
# more width than they add meaning and the pair reads "26° / 14°".
_CHIPS_MIN_H = 70
_CHIP_ARROWS_MIN_W = 150

# Humidity rides along in the caption only while the pair still renders
# at nearly the kit's label size.
_CAPTION_PAIR_SHARE = 0.85

# Strip geometry: .wx-col's 0.2em and .wx-block's 0.45em gaps resolve
# against the inherited 16px body size, and the hairline rule adds 1px.
# The clamps are modelled below; the slack covers rounding in the
# engine's line boxes — under-reserving clips the strip's last row.
_EM_GAP = 3.2
_BLOCK_GAP = 7.2
_RULE_H = 1.0
_LIST_GAP = 5.0
_STRIP_SLACK = 1.08
# Below this the icon + value pair stops reading as a glance, so the
# strip sheds its low row to give the band back.
_HERO_MIN_BAND = 40.0

# Width safety margin handed to ``fit_hero``: it solves for the size at
# which value+suffix exactly fills the budget, so its own truncation
# check lands on float equality and can cut a value that does fit.
_FIT_SLACK = 0.99

# Placeholder shown when the weather entity reports no temperature.
_NO_VALUE = "--"


def _parse_forecast_day_name(datetime_str: str, fallback: str) -> str:
    """Parse datetime string and return weekday abbreviation.

    Args:
        datetime_str: ISO format datetime string (e.g., "2025-12-29T00:00:00+00:00")
        fallback: Fallback string if parsing fails

    Returns:
        Weekday abbreviation (Mon, Tue, etc.) or fallback
    """
    if not datetime_str:
        return fallback

    try:
        # Try parsing ISO format (with or without timezone)
        # Remove timezone suffix for simpler parsing
        dt_str = datetime_str.split("+", 1)[0].split("Z", 1)[0]
        dt = datetime.fromisoformat(dt_str)
        return WEEKDAY_NAMES[dt.weekday()]
    except (ValueError, IndexError):
        # If parsing fails, try to use first 3 chars as fallback
        # (might be already a day name like "Mon")
        if len(datetime_str) >= 3 and datetime_str[:3].isalpha():
            return datetime_str[:3]
        return fallback


def _fmt_num(value: Any) -> Any:
    """Round a number to a whole integer for compact secondary display.

    Every temperature the widget shows — hero included — is a whole
    degree (``22.6`` -> ``23``, ``14.0`` -> ``14``), matching how weather
    apps present temperature and buying several display sizes for the
    hero numerals on a 2" panel. Non-numbers (``"--"``, ``None``) pass
    through untouched.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(value)
    return value


def _temp_str(value: Any) -> str:
    """Format a temperature value as ``"22°"`` (or ``"--"`` when missing)."""
    if value is None or value == _NO_VALUE:
        return _NO_VALUE
    return f"{value}°"


def _condition_label(condition: str) -> str:
    """Human-readable condition label ("partlycloudy" → "Partly Cloudy")."""
    if condition == "partlycloudy":
        return "Partly Cloudy"
    return condition.replace("-", " ").title()


def _tinted_chip(text: str, icon: str, icon_color: str) -> str:
    """A chip whose icon carries a semantic tint while the text stays neutral.

    ``chip_html``'s ``color`` tints the whole chip; hi/lo chips want only
    the ↑/↓ arrow tinted (warning/info) with secondary text.
    """
    icon_html = mdi_span(icon, "icon", f"color: {icon_color}")
    return f'<span class="chip">{icon_html}<span>{escape(text)}</span></span>'


# Widget-scoped CSS. Blitz honours <style> inside the body (including
# media queries), and a cell document only ever contains this widget, so
# these class names cannot collide with anything else on the display.
#
# Sizing notes:
# - .wx-icon is its own clamp rather than .i-lg/.i-md so the icon can be
#   genuinely large next to the hero at 240px but still shrink to a
#   glyph in a 3x3 tile.
# - .wx-col uses flex:1 1 0 (not space-evenly) so every day column is
#   exactly the same width — that is what makes the hi/lo numerals line
#   up vertically across the strip.
_WEATHER_CSS = """
<style>
.wx-main { display: flex; align-items: center; justify-content: center;
           gap: 0.06em; max-width: 100%; }
.wx-main.stack { flex-direction: column; gap: 0.02em; }
.wx-icon { font-family: "Material Design Icons"; font-weight: 400; line-height: 1;
           font-size: clamp(15px, 33vmin, 78px); }
.wx-block { display: flex; flex-direction: column; align-items: center;
            width: 100%; gap: 0.45em; }
.wx-rule { width: 90%; height: 1px; background: var(--hairline); }
.wx-strip { display: flex; width: 100%; align-items: flex-start; }
.wx-list { display: flex; flex-direction: column; width: 100%; gap: 5px; }
.wx-row { display: flex; align-items: center; gap: 4px; width: 100%; }
.wx-row .wx-day { flex: 1 1 0; min-width: 0; text-align: left; }
.wx-temps { display: flex; align-items: baseline; gap: 4px; }
.wx-temps .wx-hi, .wx-temps .wx-lo { min-width: 2.1em; text-align: right; }
.wx-list.tight .wx-row { gap: 2px; }
.wx-list.tight .wx-day { font-size: 10px; letter-spacing: 0.03em; }
.wx-list.tight .icon { font-size: 11px; }
.wx-list.tight .wx-hi { font-size: 11px; min-width: 0; }
.wx-col { display: flex; flex: 1 1 0; min-width: 0; flex-direction: column;
          align-items: center; gap: 0.2em; }
.wx-col .icon { font-size: clamp(11px, 9.5vmin, 22px); }
.wx-strip.mini .wx-col { gap: 0.1em; }
.wx-strip.mini .icon { font-size: clamp(14px, 26vmin, 30px); }
.wx-strip.mini .wx-hi { font-size: clamp(12px, 19vmin, 22px); }
.wx-hi { font-size: clamp(11px, 8.5vmin, 19px); font-weight: 700; line-height: 1.05;
         color: var(--text-primary); }
.wx-lo { font-size: clamp(10px, 7vmin, 16px); font-weight: 600; line-height: 1.05;
         color: var(--text-tertiary); }
.wx-day { font-size: clamp(11px, 7.5vmin, 15px); font-weight: 700; line-height: 1;
          letter-spacing: 0.1em; color: var(--text-tertiary); }
</style>
"""


def _weather_placeholder(ctx: CellContext) -> str:
    """Placeholder fragment when no weather data is available.

    An alert glyph, not a cloud: a grey cloudy icon in a cell too short
    for its caption impersonates a real reading. The caption shrinks —
    and shortens to "NO DATA" — instead of hiding, so the cell always
    says why it is empty.
    """
    icon = mdi_span("alert-circle-outline", "icon i-md", "color: var(--muted)")
    avail_w = cell_box(ctx)[0]
    full = "NO WEATHER DATA"
    text, px = fit_caption_sized(full, ctx, avail_w)
    if text != full:
        text, px = fit_caption_sized("NO DATA", ctx, avail_w)
    if not text:
        return f'<div class="cell">{icon}</div>'
    return (
        f'<div class="cell">{icon}'
        f'<div class="t-label" style="font-size: {px:.1f}px">{escape(text)}</div></div>'
    )


class WeatherWidget(Widget):
    """Widget that displays weather information.

    Fullscreen reads as an Apple-Weather glance:
      caption = condition label (+ humidity when it fits)
      hero    = big condition icon beside whole-degree temperature
      rule    = hairline separator
      strip   = equal-width day columns, each DAY / icon / hi over lo

    Smaller cells shed bands from the bottom up: the strip drops below
    130px, the hero stacks under the icon below 170px wide, and a 3x3
    tile is icon + temperature only.
    """

    WIDGET_TYPE: ClassVar[str] = "weather"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Weather",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [
            {"key": "show_forecast", "type": "boolean", "label": "Show Forecast", "default": True},
            {
                "key": "forecast_days",
                "type": "number",
                "label": "Forecast Days",
                "default": 3,
                "min": 1,
                "max": 5,
            },
            {
                "key": "forecast_start_tomorrow",
                "type": "boolean",
                "label": "Forecast Starts Tomorrow",
                "default": False,
            },
            {"key": "show_humidity", "type": "boolean", "label": "Show Humidity", "default": True},
            {"key": "show_high_low", "type": "boolean", "label": "Show High/Low", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the weather widget."""
        super().__init__(config)
        self.show_forecast = config.options.get("show_forecast", True)
        self.forecast_days = config.options.get("forecast_days", 3)
        self.forecast_start_tomorrow = config.options.get("forecast_start_tomorrow", False)
        self.show_humidity = config.options.get("show_humidity", True)
        self.show_high_low = config.options.get("show_high_low", True)

    def data_needs(self) -> DataNeeds:
        """The daily forecast is a service call, not a state attribute."""
        return DataNeeds(forecast=bool(self.config.entity_id))

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _visible_forecast(self, forecast: list[dict]) -> list[dict]:
        """Return the forecast entries to display.

        Daily forecasts include today as the first entry. When
        ``forecast_start_tomorrow`` is set we drop it so the strip begins
        at tomorrow instead.
        """
        items = forecast[1:] if self.forecast_start_tomorrow else forecast
        return items[: self.forecast_days]

    @staticmethod
    def _today_high_low(forecast: list[dict]) -> tuple[Any, Any]:
        """Return ``(high, low)`` from the first forecast day, if available."""
        if not forecast:
            return (None, None)
        day = forecast[0]
        return (day.get("temperature"), day.get("templow"))

    def _strip_columns(self, ctx: CellContext, forecast: list[dict]) -> list[dict]:
        """Forecast days that fit the cell, or ``[]`` when the strip is off.

        Each column needs roughly 42px to keep ``DAY`` and a two-digit
        temperature legible, so wide cells show every requested day and
        narrower ones truncate rather than crush the columns together.
        """
        if not self.show_forecast:
            return []
        items = self._visible_forecast(forecast)
        if ctx.height < _STRIP_MIN_H:
            # Short cells have no room for day names or lows, but a
            # tomorrow-and-after glance still beats a lone temperature —
            # they get the mini strip (tinted icon over the high).
            return items[:_MINI_DAYS] if self._is_mini(ctx) else []
        if ctx.width < _STRIP_MIN_W:
            # Too narrow for side-by-side columns, but a tall split-v cell
            # has the height to list the same days as rows instead.
            return items[:3] if ctx.height >= _LIST_MIN_H else []
        return items[: max(1, int(ctx.width * 0.94 // 42))]

    def _is_mini(self, ctx: CellContext) -> bool:
        """True in short-wide cells, where the strip is icon + high only."""
        return (
            ctx.height < _STRIP_MIN_H and ctx.width >= _COMPACT_MIN_W and ctx.height >= _MINI_MIN_H
        )

    def _is_list(self, ctx: CellContext) -> bool:
        """True when the forecast is laid out as rows, not columns."""
        return ctx.width < _STRIP_MIN_W and not self._is_mini(ctx)

    # ------------------------------------------------------------------
    # Fragment builders
    # ------------------------------------------------------------------

    def _forecast_column(self, day: dict, index: int, high_only: bool) -> str:
        """One day column: ``DAY`` / tinted icon / hi over lo."""
        day_condition = day.get("condition", "sunny")
        day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
        day_tint = WEATHER_COLORS.get(day_condition, "var(--warning)")
        day_low = day.get("templow")
        day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}")

        hi = escape(_temp_str(_fmt_num(day.get("temperature", "--"))))
        temps = f'<div class="wx-hi">{hi}</div>'
        if self.show_high_low and not high_only and day_low is not None:
            lo = escape(_temp_str(_fmt_num(day_low)))
            temps += f'<div class="wx-lo">{lo}</div>'

        return (
            '<div class="wx-col">'
            f'<div class="wx-day">{escape(day_name.upper())}</div>'
            f"{mdi_span(day_icon, 'icon', f'color: {day_tint}')}"
            f"{temps}</div>"
        )

    def _mini_shows_day(self, ctx: CellContext) -> bool:
        """Day names in the mini strip need ~12px of extra band height."""
        return ctx.height >= _MINI_DAY_MIN_H

    def _mini_metrics(self, ctx: CellContext) -> tuple[float, float, float]:
        """(day_px, icon_px, hi_px) for the mini strip's columns.

        Sized by the COLUMN width, not vmin: the CSS clamps grew with
        square cells (26vmin of a 111px tile is a 29px glyph in a 35px
        column) until the three highs collided and the band clipped at
        the cell's bottom edge.
        """
        col_w = cell_box(ctx)[0] / _MINI_DAYS
        day = min(11.0, 0.30 * col_w) if self._mini_shows_day(ctx) else 0.0
        icon = max(13.0, min(0.60 * col_w, 26.0))
        hi = max(11.0, min(0.42 * col_w, 18.0))
        return day, icon, hi

    def _mini_column(
        self,
        day: dict,
        index: int,
        *,
        show_day: bool,
        show_lo: bool,
        day_px: float,
        icon_px: float,
        hi_px: float,
    ) -> str:
        """Short-cell column: tinted condition icon over the high.

        A 69px-tall cell cannot carry more, but three tinted glyphs with
        their highs still read as a forecast at arm's length. Day names
        return above the icon when the band has the height, and the low
        joins the high when the column has the width.
        """
        day_condition = day.get("condition", "sunny")
        day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
        day_tint = WEATHER_COLORS.get(day_condition, "var(--warning)")
        name = ""
        if show_day:
            day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}")
            name = (
                f'<div class="wx-day" style="font-size: {day_px:.1f}px">'
                f"{escape(day_name.upper())}</div>"
            )
        hi = escape(_temp_str(_fmt_num(day.get("temperature", "--"))))
        temps = f'<span class="wx-hi" style="font-size: {hi_px:.1f}px">{hi}</span>'
        day_low = day.get("templow")
        if show_lo and self.show_high_low and day_low is not None:
            temps += (
                f' <span class="wx-lo" style="font-size: {hi_px * 0.85:.1f}px">'
                f"{escape(_temp_str(_fmt_num(day_low)))}</span>"
            )
        return (
            '<div class="wx-col">'
            f"{name}"
            f"{mdi_span(day_icon, 'icon', f'color: {day_tint}; font-size: {icon_px:.1f}px')}"
            f"<div>{temps}</div></div>"
        )

    def _forecast_row(self, day: dict, index: int, *, tight: bool = False) -> str:
        """One day as a row: ``DAY`` · icon · hi · lo, for narrow cells."""
        day_condition = day.get("condition", "sunny")
        day_icon = WEATHER_ICONS.get(day_condition, "weather-sunny")
        day_tint = WEATHER_COLORS.get(day_condition, "var(--warning)")
        day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}")
        day_low = day.get("templow")

        hi = escape(_temp_str(_fmt_num(day.get("temperature", "--"))))
        lo_html = ""
        if self.show_high_low and day_low is not None and not tight:
            lo_html = f'<span class="wx-lo">{escape(_temp_str(_fmt_num(day_low)))}</span>'
        return (
            '<div class="wx-row">'
            f'<span class="wx-day">{escape(day_name.upper())}</span>'
            f"{mdi_span(day_icon, 'icon', f'color: {day_tint}')}"
            f'<span class="wx-temps"><span class="wx-hi">{hi}</span>{lo_html}</span></div>'
        )

    def _strip_height(self, ctx: CellContext, count: int, *, high_only: bool) -> float:
        """Height the forecast block occupies, mirroring its CSS clamps.

        Under-reserving here is what clips the strip's last row against
        the cell's bottom edge, so the flex gaps and the hairline are
        counted explicitly rather than folded into one fudge factor.
        """
        vmin = min(ctx.width, ctx.height)
        day = max(11.0, min(0.075 * vmin, 15.0))
        icon = max(11.0, min(0.095 * vmin, 22.0))
        hi = max(11.0, min(0.085 * vmin, 19.0))
        lo = 0.0 if high_only else max(10.0, min(0.07 * vmin, 16.0))
        if self._is_mini(ctx):
            # Exact mirror of _mini_metrics — the strip's sizes are
            # inline px, so the budget can't drift from the render.
            mini_day, mini_icon, mini_hi = self._mini_metrics(ctx)
            return (mini_day * 1.1 + mini_icon + mini_hi * 1.05 + 0.1 * 16) * _STRIP_SLACK
        if self._is_list(ctx):
            rows = count * max(icon, hi) * 1.35 + max(0, count - 1) * _LIST_GAP
            return (rows + _BLOCK_GAP + _RULE_H) * _STRIP_SLACK
        # .wx-hi/.wx-lo carry line-height 1.05; the column has one gap
        # between each of its bands.
        bands = day + icon + (hi + lo) * 1.05
        gaps = (3 if lo else 2) * _EM_GAP
        return (bands + gaps + _BLOCK_GAP + _RULE_H) * _STRIP_SLACK

    def _forecast_strip(self, ctx: CellContext, items: list[dict], *, high_only: bool) -> str:
        """Hairline rule plus the day columns (or rows in narrow cells).

        Rule and days share one wrapper so ``space-evenly`` treats them
        as a single band — otherwise the hairline floats midway between
        the hero and the forecast instead of capping it.
        """
        if not items:
            return ""
        if self._is_mini(ctx):
            # No hairline: at this height the rule costs more than the
            # separation it buys. Day names and lows come back as soon
            # as the cell affords them — a 224x108 split cell has both.
            show_day = self._mini_shows_day(ctx)
            show_lo = ctx.width * 0.94 / max(1, len(items)) >= _MINI_LO_COL_W
            day_px, icon_px, hi_px = self._mini_metrics(ctx)
            body = "".join(
                self._mini_column(
                    day,
                    i,
                    show_day=show_day,
                    show_lo=show_lo,
                    day_px=day_px,
                    icon_px=icon_px,
                    hi_px=hi_px,
                )
                for i, day in enumerate(items)
            )
            return f'<div class="wx-strip mini">{body}</div>'
        if self._is_list(ctx):
            tight = ctx.width < _LIST_MIN_W
            body = "".join(self._forecast_row(day, i, tight=tight) for i, day in enumerate(items))
            klass = "wx-list tight" if tight else "wx-list"
            inner = f'<div class="{klass}">{body}</div>'
        else:
            body = "".join(self._forecast_column(day, i, high_only) for i, day in enumerate(items))
            inner = f'<div class="wx-strip">{body}</div>'
        return f'<div class="wx-block"><div class="wx-rule"></div>{inner}</div>'

    def _chips(self, ctx: CellContext, forecast: list[dict]) -> list[str]:
        """Today's hi/lo chip strip, or ``[]``.

        The band runs down to _COMPACT_MIN_W x 70 rather than 130x130: a
        2x2 tile has the room, and a hero floating over an empty half
        cell is the worse trade. Under _CHIP_ARROWS_MIN_W the ↑/↓ glyphs
        and the second pill cost more width than they earn, so the pair
        collapses into one arrowless "26° / 14°" chip.
        """
        if not self.show_high_low or ctx.width < _COMPACT_MIN_W or ctx.height < _CHIPS_MIN_H:
            return []
        high, low = self._today_high_low(forecast)
        if high is None and low is None:
            return []
        if ctx.width < _CHIP_ARROWS_MIN_W:
            pair = " / ".join(f"{_fmt_num(t)}°" for t in (high, low) if t is not None)
            return [f'<span class="chip">{escape(pair)}</span>']
        chips: list[str] = []
        if high is not None:
            chips.append(_tinted_chip(f"{_fmt_num(high)}°", "arrow-up-thin", "var(--warning)"))
        if low is not None:
            chips.append(_tinted_chip(f"{_fmt_num(low)}°", "arrow-down-thin", "var(--info)"))
        return chips

    @staticmethod
    def _caption_html(ctx: CellContext, condition: str, humidity: str | None) -> tuple[str, bool]:
        """Condition label, with humidity appended when it genuinely fits.

        Humidity is the lower-priority datum, so it is dropped whole
        rather than allowed to push the condition into an ellipsis — a
        caption reading "PARTLY CL… · 62%" trades the useful word for
        the ornamental number. Measuring the pair at the *kit* size alone
        dropped it from the cells with the most room (a 240px cell fits
        "PARTLY CLOUDY · 62%" at 17.5px, a hair under the kit's 18), so
        the pair goes through the same shrink-then-truncate fit as the
        condition and rides along while it stays near full size.
        """
        avail_w = cell_box(ctx)[0]
        px = label_px(ctx)
        upper = condition.upper()
        fitted, fit_px = fit_caption_sized(upper, ctx, avail_w)
        humidity_shown = False
        if humidity:
            pair, pair_px = fit_caption_sized(f"{upper}  ·  {humidity}", ctx, avail_w)
            # Near the 12px label FLOOR the share test excludes a 10px
            # fit by a fraction — any whole un-truncated pair at or
            # above the caption floor keeps its humidity.
            if pair.startswith(upper) and (
                pair_px >= px * _CAPTION_PAIR_SHARE or (pair_px >= 10.0 and "…" not in pair)
            ):
                fitted, fit_px = pair, pair_px
                humidity_shown = True
        size = f' style="font-size: {fit_px:.1f}px"'
        return (
            f'<div class="t-label caption-row hide-short"{size}>{escape(fitted)}</div>',
            humidity_shown,
        )

    def _hero_html(
        self,
        ctx: CellContext,
        condition_icon: tuple[str, str],
        temp: Any,
        avail_w: float,
        avail_h: float,
        *,
        solo: bool,
    ) -> str:
        """Condition icon + whole-degree temperature, side by side or stacked.

        Wide cells set the icon beside the value so both read at poster
        size; narrow ones stack it above, where the value keeps the full
        cell width to itself. ``solo`` means nothing follows the pair —
        then the cell's height is theirs to spend.

        The icon size is always resolved here rather than by .wx-icon's
        clamp: the clamp knows the cell but not what shares it, so it
        claims a band the strip below it needs.
        """
        icon, tint = condition_icon
        # Squarish cells with nothing underneath stack: side by side the
        # pair is width-bound, saturating the cell at a third of its
        # height. Short cells do the opposite for the same reason.
        solo_stack = solo and avail_h >= avail_w * _SOLO_STACK_RATIO
        side_by_side = not solo_stack and (
            ctx.width >= _SIDE_BY_SIDE_MIN_W
            or (ctx.width >= _COMPACT_MIN_W and ctx.height < _STACK_MIN_H)
        )
        if solo_stack:
            icon_px = min(avail_h * _SOLO_ICON_SHARE, avail_w * 0.55, _SOLO_ICON_MAX_PX)
        else:
            icon_px = max(_ICON_MIN_PX, min(_ICON_VMIN * min(ctx.width, ctx.height), _ICON_MAX_PX))
            icon_px = min(icon_px, avail_h * (0.95 if side_by_side else _STACK_ICON_SHARE))
        icon_px = max(_ICON_MIN_PX, icon_px)
        icon_html = mdi_span(icon, "wx-icon", f"color: {tint}; font-size: {icon_px:.1f}px")
        hero_w = avail_w - icon_px * 1.15 if side_by_side else avail_w
        hero_h = avail_h if side_by_side else max(20.0, avail_h - icon_px)

        # The degree sign stays *inside* the hero rather than becoming a
        # smaller .t-unit: a bare "°" is a ring that occupies only the top
        # of its em, so shrinking it and dropping it on the baseline reads
        # as a subscript. Full size keeps the Apple-Weather "19°" shape.
        value = _temp_str(_fmt_num(temp))
        # An absent reading must not shout: fitted to the band, "--" is
        # two bars the size of the temperature it stands in for.
        missing = value == _NO_VALUE
        max_px = min(46.0, hero_h * 0.5) if missing else 128.0
        fit = fit_hero(value, ctx, max(24.0, hero_w) * _FIT_SLACK, hero_h, max_px=max_px)
        style = ' style="color: var(--text-secondary)"' if missing else ""
        temp_html = f'<div class="t-hero"{style}>{hero_block(fit.text, fit.px)}</div>'
        stack = "" if side_by_side else " stack"
        return f'<div class="wx-main{stack}">{icon_html}{temp_html}</div>'

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the weather widget."""
        entity = state.entity
        if entity is None:
            return _weather_placeholder(ctx)

        condition = entity.state
        icon_name = WEATHER_ICONS.get(condition, "weather-sunny")
        icon_tint = WEATHER_COLORS.get(condition, "var(--warning)")
        humidity = entity.get("humidity", "--")

        columns = self._strip_columns(ctx, state.forecast)
        humidity_text = None
        # No width cliff at all: _caption_html measures the combined
        # pair and keeps it only while it fits whole, and the tall-cell
        # fallback line has its own height gate — a 108px split column
        # earns its humidity either way.
        if self.show_humidity and humidity != "--":
            humidity_text = f"{_fmt_num(humidity)}%"

        # Today's hi/lo only earns a chip row when the forecast strip is
        # absent — with the strip up, its first column already says it.
        chips = self._chips(ctx, state.forecast) if not columns else []

        avail_w, avail_h = cell_box(ctx)
        spent = 0.0
        show_caption = caption_visible(ctx)
        if show_caption:
            spent += label_px(ctx)
        if chips:
            spent += chip_band_px(ctx)
        high_only = len(columns) > 3
        if columns:
            strip_h = self._strip_height(ctx, len(columns), high_only=high_only)
            if not high_only and avail_h - spent - strip_h < _HERO_MIN_BAND:
                # The low row is the first thing to go: three highs read
                # better than a hi/lo pair with its bottom line clipped.
                high_only = True
                strip_h = self._strip_height(ctx, len(columns), high_only=True)
            spent += strip_h

        share = HERO_SHARE_SOLO if not (chips or columns) else HERO_SHARE_STACKED
        bands: list[str] = []
        humidity_shown = not humidity_text
        if show_caption:
            caption_html, humidity_shown = self._caption_html(
                ctx, _condition_label(condition), humidity_text
            )
            bands.append(caption_html)
        if humidity_text and not humidity_shown and ctx.height >= 190:
            # The one-line pair missed the caption floor, but a tall
            # column has a whole line to spare — humidity gets its own
            # small tinted row under the condition instead of vanishing.
            drop = mdi_span("water", "icon", "color: var(--info); font-size: 10px")
            bands.append(
                '<div class="t-label caption-row hide-short" style="font-size: 10.0px">'
                f"{drop}{escape(humidity_text)}</div>"
            )
            spent += 12.0
        bands.append(
            self._hero_html(
                ctx,
                (icon_name, icon_tint),
                entity.get("temperature", "--"),
                avail_w,
                max(24.0, avail_h - spent) * share,
                solo=not (chips or columns),
            )
        )
        if chips:
            bands.append(f'<div class="chips">{"".join(chips)}</div>')
        bands.append(self._forecast_strip(ctx, columns, high_only=high_only))
        return f'{_WEATHER_CSS}<div class="cell">{"".join(bands)}</div>'
