"""Drawing helpers for HTML widget templates: the built-ins' visual vocabulary.

A template calls ``ring(73, 'success')`` or ``icon('mdi:lock', 'muted')``
and gets the same markup the gauge, chart and card widgets draw, so a
custom cell sits next to built-in ones without looking foreign.

Colours are theme ROLE names (``'primary'``, ``'warning'``, ``'muted'``,
``'accent'``, ``'text-secondary'``, ...), also accepted spelled
``'var(--warning)'``, or any literal CSS colour. Roles resolve to the
cell theme's concrete colour, because Blitz does not resolve ``var()``
inside SVG paint attributes. A monochrome theme (night) owns every colour
on screen, so a literal colour there becomes the cell's accent, as user
colour options do on built-in widgets.
"""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING, Any

from jinja2 import Undefined
from markupsafe import Markup
from markupsafe import escape as markup_escape

from ..htmldoc import css_rgb, css_rgba, mdi_span, svg_arc, svg_ring, svg_sparkline
from ._gauge import _NEUTRAL_TRACK_OPACITY, STROKE_UNITS, bar_html, track_css
from ._textfit import metrics_for
from .helpers import calculate_percent

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..htmldoc import CellContext

RGB = tuple[int, int, int]

# Role name -> Theme attribute. Dashes and underscores are interchangeable.
_ROLES = {
    "primary": "primary",
    "secondary": "secondary",
    "success": "success",
    "warning": "warning",
    "error": "error",
    "info": "info",
    "muted": "muted",
    "text-primary": "text_primary",
    "text-secondary": "text_secondary",
    "text-tertiary": "text_tertiary",
    "bg": "background",
    "background": "background",
    "surface": "surface",
    "surface-variant": "surface_variant",
    "border": "border",
}

_VAR_RE = re.compile(r"var\(\s*--([a-z0-9_-]+)\s*\)", re.IGNORECASE)
_ACCENT_N_RE = re.compile(r"accent-?(\d+)")
_HEX_RE = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)
_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,[^)]*)?\)", re.IGNORECASE)

# Bar thickness, as the gauge widget draws its horizontal / vertical bars.
_BAR_THICKNESS = "clamp(8px, 11vmin, 18px)"
_VBAR_THICKNESS = "clamp(12px, 17vmin, 30px)"


def _parse_rgb(value: str) -> RGB | None:
    """``#rgb``, ``#rrggbb`` or ``rgb(r, g, b)`` as a tuple; None otherwise."""
    if match := _HEX_RE.fullmatch(value):
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    if match := _RGB_RE.fullmatch(value):
        r, g, b = (min(255, int(part)) for part in match.groups())
        return (r, g, b)
    return None


def resolve_color(ctx: CellContext, value: Any = None) -> tuple[str, RGB | None]:
    """A colour argument as (CSS colour, RGB when known).

    None, ``''`` and ``'accent'`` are the cell's accent (the theme's slot
    rotation); ``'accent-2'`` picks one accent; a role name is the
    theme's colour for that role; anything else is a literal CSS colour,
    escaped for an attribute (the accent on a monochrome theme).
    """
    theme = ctx.theme
    text = "" if value is None else str(value).strip()
    name = text.lower()
    if match := _VAR_RE.fullmatch(name):
        name = match.group(1)
    name = name.replace("_", "-")

    rgb: RGB | None = None
    if name in ("", "accent"):
        if theme is None:
            return ctx.accent(), None
        rgb = theme.get_accent_color(ctx.slot_index)
    elif match := _ACCENT_N_RE.fullmatch(name):
        if theme is None:
            return f"var(--accent-{match.group(1)})", None
        rgb = theme.accent_colors[int(match.group(1)) % len(theme.accent_colors)]
    elif name in _ROLES:
        if theme is None:
            return f"var(--{name})", None
        rgb = getattr(theme, _ROLES[name])
    elif theme is not None and theme.monochrome:
        rgb = theme.get_accent_color(ctx.slot_index)
    else:
        return escape(text, quote=True), _parse_rgb(text)
    return css_rgb(rgb), rgb


def _number(value: Any, default: float = 0.0) -> float:
    """A template value (often a state string) as a finite float.

    Jinja's ``Undefined`` (``[] | last``, a missing key) is missing data,
    not a template error: it raises on ``float()``, so it is caught first.
    """
    if isinstance(value, Undefined):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _bound(value: Any) -> float | None:
    """An optional scale bound: unset (or not a number) follows the data."""
    number = _number(value, math.nan)
    return None if math.isnan(number) else number


def _length(value: Any) -> str | None:
    """A size argument as a CSS length: numbers are px, strings pass through."""
    if value is None or value == "" or isinstance(value, Undefined):
        return None
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f"{value:g}px" if math.isfinite(value) else None
    return escape(str(value), quote=True)


def _svg_track(ctx: CellContext, rgb: RGB | None) -> str:
    """The gauge widget's SVG track for a fill of colour ``rgb``.

    A literal colour that can't be read as RGB gets the neutral track:
    tinting it with the accent would pair two unrelated colours.
    """
    theme = ctx.theme
    if rgb is None and theme is not None:
        return css_rgba(theme.text_primary, _NEUTRAL_TRACK_OPACITY)
    return track_css(ctx, rgb, svg=True)


def _boxed(markup: str, width: str | None, height: str | None) -> str:
    """Wrap SVG in a fixed, non-shrinking box (inline SVG sizes from its viewBox)."""
    if width is None and height is None:
        return markup
    style = "flex: none"
    if width is not None:
        style += f"; width: {width}"
    if height is not None:
        style += f"; height: {height}"
    return f'<div style="{style}">{markup}</div>'


def template_helpers(ctx: CellContext) -> dict[str, Callable[..., Any]]:
    """The drawing helpers for one render of one cell."""
    gradient_ids = itertools.count()

    def color(name: Any = None) -> str:
        """A theme role (or literal) as a concrete CSS colour, for your own SVG."""
        return resolve_color(ctx, name)[0]

    def icon(name: Any, color: Any = None, size: Any = None) -> Markup:
        """An MDI glyph (``'mdi:lock'``) from the embedded font (unknown: a help circle)."""
        style = []
        if color is not None:
            style.append(f"color: {resolve_color(ctx, color)[0]}")
        if (length := _length(size)) is not None:
            style.append(f"font-size: {length}")
        return Markup(mdi_span(str(name), "icon", "; ".join(style)))  # noqa: S704

    def _round(
        draw: Callable[..., str], value: Any, color: Any, *, lo: Any, hi: Any, size: Any
    ) -> Markup:
        css, rgb = resolve_color(ctx, color)
        percent = calculate_percent(_number(value), _number(lo), _number(hi, 100.0))
        svg = draw(percent, stroke=css, track=_svg_track(ctx, rgb), stroke_width=STROKE_UNITS)
        length = _length(size)
        return Markup(_boxed(svg, length, length))  # noqa: S704

    def ring(
        value: Any,
        color: Any = None,
        min: Any = 0,  # noqa: A002
        max: Any = 100,  # noqa: A002
        size: Any = None,
    ) -> Markup:
        """The gauge widget's Activity ring, filled to ``value`` on ``min..max``."""
        return _round(svg_ring, value, color, lo=min, hi=max, size=size)

    def arc(
        value: Any,
        color: Any = None,
        min: Any = 0,  # noqa: A002
        max: Any = 100,  # noqa: A002
        size: Any = None,
    ) -> Markup:
        """The gauge widget's 270 degree arc, filled to ``value`` on ``min..max``."""
        return _round(svg_arc, value, color, lo=min, hi=max, size=size)

    def bar(
        value: Any,
        color: Any = None,
        min: Any = 0,  # noqa: A002
        max: Any = 100,  # noqa: A002
        *,
        vertical: bool = False,
        thickness: Any = None,
    ) -> Markup:
        """The gauge widget's pill bar; fills its parent's width (or height)."""
        css, rgb = resolve_color(ctx, color)
        track = track_css(ctx, rgb) if rgb is not None else "var(--track)"
        percent = calculate_percent(_number(value), _number(min), _number(max, 100.0))
        default = _VBAR_THICKNESS if vertical else _BAR_THICKNESS
        return Markup(  # noqa: S704
            bar_html(
                percent,
                color=css,
                track=track,
                thickness=_length(thickness) or default,
                vertical=bool(vertical),
            )
        )

    def sparkline(
        values: Any,
        color: Any = None,
        *,
        width: Any = None,
        height: Any = None,
        fill: bool = True,
        dot: bool = True,
        smooth: Any = None,
        min: Any = None,  # noqa: A002
        max: Any = None,  # noqa: A002
    ) -> Markup:
        """The chart widget's sparkline of ``values`` (fewer than two: ``''``).

        Without ``width``/``height`` it fills its parent's width at a 2:1
        aspect. ``smooth`` defaults to on, except for on/off series.
        """
        try:
            points = [_number(v, math.nan) for v in values]
        except TypeError:
            return Markup("")
        points = [v for v in points if not math.isnan(v)]
        w, h = _number(width, 0.0), _number(height, 0.0)
        aspect = w / h if w > 0 and h > 0 else 2.0
        if smooth is None:
            smooth = not all(v in (0.0, 1.0) for v in points)
        css, _ = resolve_color(ctx, color)
        stroke_w = min_max(2.0 + min_side(ctx) / 240.0 * 2.0, 2.2, 4.0)
        svg = svg_sparkline(
            points,
            stroke=css,
            fill_opacity=0.50 if fill else 0.0,
            stroke_width=stroke_w,
            aspect=aspect,
            smooth=bool(smooth),
            show_dot=bool(dot),
            y_min=_bound(min),
            y_max=_bound(max),
            gradient_id=f"spark{next(gradient_ids)}",
        )
        if not svg:
            return Markup("")
        return Markup(_boxed(svg, _length(width), _length(height)))  # noqa: S704

    def fit(
        text: Any,
        width: Any = None,
        max: Any = None,  # noqa: A002
        min: Any = 12,  # noqa: A002
        weight: Any = "bold",
        tracking: Any = 0,
    ) -> Markup:
        """``text`` in a span sized to fit ``width`` px on one line.

        As large as ``max`` px, never under ``min``; when even ``min`` is
        too wide, the text is cut with "…". Measured with the engine and
        the theme's own face, as the built-in widgets fit their values,
        so a long state ("unavailable", a friendly name) can't run past
        the cell. Defaults: the cell's width less 16px, and half its
        height.

        The span sets its own font, weight, letter-spacing (``tracking``,
        in em) and ``text-transform: none``, so what is drawn is what was
        measured whatever the parent styles: pass caps already in the
        text (``name | upper``) and the tracking you want.
        """
        if text is None or isinstance(text, Undefined):
            return Markup("")
        # Markup arrives escaped: measure the text it shows, keep its escaping
        shown = text.unescape() if isinstance(text, Markup) else str(text)
        box = _number(width, ctx.width - 16) if width is not None else ctx.width - 16.0
        top = _number(max, ctx.height / 2) if max is not None else ctx.height / 2
        floor = min_max(_number(min, 12), 1, top)
        css_weight, measured_weight = _fit_weight(weight)
        em = _number(tracking)
        metrics = replace(metrics_for(ctx.theme), uppercase=False)
        px = math.floor(
            metrics.fit_font_size(shown, box, top, measured_weight, tracking=em, min_px=floor)
        )
        if metrics.width(shown, px, measured_weight, em) > box:
            body = markup_escape(metrics.truncate(shown, px, box, measured_weight, tracking=em))
        else:
            body = markup_escape(text) if isinstance(text, Markup) else markup_escape(shown)
        family = (getattr(ctx.theme, "font_stack", None) or _DEFAULT_FONT_STACK).replace('"', "'")
        style = (
            f"font-size: {px}px; font-weight: {css_weight}; font-family: {family}; "
            f"letter-spacing: {_fmt_number(em)}em; text-transform: none; white-space: nowrap"
        )
        return Markup(f'<span style="{style}">{body}</span>')  # noqa: S704

    return {
        "color": color,
        "icon": icon,
        "ring": ring,
        "arc": arc,
        "bar": bar,
        "sparkline": sparkline,
        "fit": fit,
    }


# CSS font-weight -> the measurer's weights (the embedded Nunito faces)
_MEASURED_WEIGHTS = ((500, "regular"), (650, "semibold"), (750, "bold"))
_WEIGHT_NAMES = {
    "normal": 400,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
}


def _fit_weight(value: Any) -> tuple[int, str]:
    """A weight (``'bold'``, ``800``, ``'700'``) as (CSS weight, measured face)."""
    text = str(value).strip().lower()
    css = _WEIGHT_NAMES.get(text) or int(min_max(_number(text, 700), 100, 900))
    for limit, name in _MEASURED_WEIGHTS:
        if css <= limit:
            return css, name
    return css, "extrabold"


def _fmt_number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


# The default theme's stack, for a cell rendered without a theme
_DEFAULT_FONT_STACK = '"Nunito", "DejaVu Sans", sans-serif'


def min_side(ctx: CellContext) -> float:
    """The cell's short side in px."""
    return float(min(ctx.width, ctx.height))


def min_max(value: float, lo: float, hi: float) -> float:
    """Clamp ``value`` to ``lo..hi``."""
    return max(lo, min(value, hi))
