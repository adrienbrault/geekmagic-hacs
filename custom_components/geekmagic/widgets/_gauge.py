"""Gauge primitives shared by the gauge and progress widget families.

Bars, rings and arcs speak one visual language:

* a **track** — the accent tinted down (Apple Activity style) when the
  theme opts in, otherwise the neutral ``--track`` derived from the text
  color so it reads correctly on light themes too;
* a **fill** in the accent itself, pill-capped at every size;
* a **hero value** whose digits carry the weight while the unit sits one
  step smaller and lighter next to them, baseline aligned.

Keeping these here means a bar in ``gauge.py`` and a bar in
``progress.py`` are literally the same object.

What is NOT here is the fitting: captions and hero sizes go through
:mod:`._fit`, the one measured fitter every widget family uses. This
module used to carry an estimating twin (average glyph advances by font
family), which made the same caption fit differently in a gauge cell
than in an entity cell and could not see a fullwidth glyph at all.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from ..htmldoc import css_rgba
from ._cellkit import cell_box
from ._fit import fit_caption_sized

if TYPE_CHECKING:
    from ..htmldoc import CellContext

# Opacity of the neutral (untinted) track. Mirrors the kit's --track var,
# which SVG paint attributes cannot resolve.
_NEUTRAL_TRACK_OPACITY = 0.12
# Fallback when no theme is available (contexts built without one).
_NEUTRAL_TRACK_FALLBACK = "rgba(128, 128, 128, 0.20)"

# Pill radius shared by every bar, in both directions.
PILL_RADIUS = "999px"

# Ring/arc stroke as a share of the gauge diameter (SVG user units on the
# 100x100 viewBox). ~10.5% keeps the ring bold without closing the hole.
STROKE_UNITS = 10.5

# The gauge family's band thresholds — the second dialect of the question
# ``_bands.plan_bands`` answers for the card family. Both are measured
# against the RAW cell height rather than a content box, and both sit
# under the kit's 100px ``.hide-short`` cliff on purpose: these cells
# carry a bar as well as a value, so the card family's plan cannot be
# spent here without changing what they draw. That is why
# :func:`caption_band` decides in Python and emits no hide class.
#
# Cell height from which the feature icon stacks above the caption
# instead of riding inline (matches entity.py's _FEATURE_MIN_H + insets).
STACK_MIN_CELL_H = 64.0

# Below this the cell cannot hold a caption band on top of its value and
# its bar; above it, even a hero-layout footer (~65px) has room for the
# 10px name, and an unlabeled bar is a number without a meaning.
CAPTION_MIN_CELL_H = 46.0


def feature_icon_px(ctx: CellContext) -> float:
    """Feature-band glyph size for a caption-topped gauge/progress card.

    Geometry-driven like the entity card's, but smaller — these cells
    also carry a bar — with the same tall-cell bonus so narrow columns
    don't strand their height.
    """
    vmin = min(ctx.width, ctx.height)
    bonus = 0.10 * max(0.0, ctx.height - ctx.width)
    return max(14.0, min(0.24 * vmin + bonus, 0.5 * ctx.width, 40.0))


def caption_band(
    ctx: CellContext,
    name: str,
    icon_html: str = "",
    *,
    width_ratio: float = 1.0,
    stack_icon_html: str = "",
) -> str:
    """Caps caption band whose visibility is decided here, not by the kit.

    ``hide-short`` would blank the row in every cell under 100px tall,
    icon included — but those cells still have room for a 10px name, and
    they are exactly the cells that most need one. The band is therefore
    sized in Python and carries no hide class.

    With ``stack_icon_html`` and a cell tall enough for the stack, the
    icon takes its own band above the caption (the watchOS feature-icon
    pattern the entity card uses); the inline chip row is the fallback
    for genuinely short cells.
    """
    if not name or ctx.height < CAPTION_MIN_CELL_H:
        return ""
    # The stack (icon + 10px caption + value) fits from ~64px of cell
    # height — the old design stacked even 3x3 tiles, and it reads far
    # better than an inline speck beside the label.
    stacked = bool(stack_icon_html) and ctx.height >= STACK_MIN_CELL_H
    inline_icon = "" if stacked else icon_html
    reserve_em = 1.6 if inline_icon else 0.0
    text, px = fit_caption_sized(name, ctx, cell_box(ctx)[0] * width_ratio, reserve_em=reserve_em)
    if not (text or inline_icon or stacked):
        return ""
    # Always inline the fitted size: it may sit above the kit clamp
    # (wide cell, short word) as well as below it.
    size = f' style="font-size: {px:.1f}px"'
    row = f'<div class="t-label caption-row"{size}>{inline_icon}{escape(text)}</div>'
    if stacked:
        return f'<div class="card-icon">{stack_icon_html}</div>{row}'
    return row


def track_css(
    ctx: CellContext,
    rgb: tuple[int, int, int] | None = None,
    *,
    svg: bool = False,
) -> str:
    """Track color for a gauge fill.

    Themes with ``tint_track`` get the accent at low opacity (the value
    and its track read as one object). Otherwise the neutral track is
    used: ``var(--track)`` in HTML, a concrete rgba in SVG — Blitz does
    not resolve ``var()`` inside SVG paint attributes.
    """
    theme = ctx.theme
    if theme is not None and theme.tint_track:
        tint = rgb if rgb is not None else theme.get_accent_color(ctx.slot_index)
        return css_rgba(tint, theme.tint_track_opacity)
    if not svg:
        return "var(--track)"
    if theme is None:
        return _NEUTRAL_TRACK_FALLBACK
    return css_rgba(theme.text_primary, _NEUTRAL_TRACK_OPACITY)


def bar_html(
    percent: float,
    *,
    color: str,
    track: str,
    thickness: str,
    vertical: bool = False,
) -> str:
    """A pill track with a pill fill.

    ``thickness`` is any CSS length (the cross-axis size). The element is
    ``flex: none`` so a flex column never squashes it — a fixed height on
    a flex child is only a *basis*, and an overflowing cell would
    otherwise shrink the bar to a hairline.
    """
    if vertical:
        return (
            f'<div style="width: {thickness}; height: 100%; flex: none; '
            f"background: {track}; border-radius: {PILL_RADIUS}; "
            'position: relative; overflow: hidden">'
            '<div style="position: absolute; left: 0; right: 0; bottom: 0; '
            f"height: {percent:.1f}%; background: {color}; "
            f'border-radius: {PILL_RADIUS}"></div>'
            "</div>"
        )
    return (
        f'<div style="width: 100%; height: {thickness}; flex: none; '
        f'background: {track}; border-radius: {PILL_RADIUS}; overflow: hidden">'
        f'<div style="width: {percent:.1f}%; height: 100%; background: {color}; '
        f'border-radius: {PILL_RADIUS}"></div>'
        "</div>"
    )


# Line box hugging the numerals (see value_unit_html).
_HERO_LINE_HEIGHT = 0.8


def value_unit_html(
    digits: str,
    unit: str = "",
    *,
    hero_css: str | None = None,
    unit_css: str | None = None,
    color: str | None = None,
    unit_color: str | None = None,
    hero_class: str = "t-hero",
) -> str:
    """Hero value with the unit baseline-aligned beside it.

    The unit keeps its own (smaller, lighter) type so "73" reads as the
    number and "%" as an annotation — the same relationship Apple uses
    for every large metric.

    Digits have no descenders, so the kit's line box leaves dead space
    under them and the next band drifts away; ``_HERO_LINE_HEIGHT``
    hugs the numerals instead, which is what makes the caption / value /
    bar gaps read even.
    """
    if not digits and not unit:
        return ""
    hero_style = f"line-height: {_HERO_LINE_HEIGHT};"
    if hero_css:
        hero_style += f" font-size: {hero_css};"
    if color:
        hero_style += f" color: {color};"
    hero_attr = f' style="{hero_style.strip()}"'
    hero_html = f'<span class="{hero_class}"{hero_attr}>{escape(digits)}</span>'
    if not unit:
        return hero_html
    unit_style = f"line-height: {_HERO_LINE_HEIGHT};"
    if unit_css:
        unit_style += f" font-size: {unit_css};"
    if unit_color:
        unit_style += f" color: {unit_color};"
    unit_attr = f' style="{unit_style.strip()}"' if unit_style else ""
    unit_html = f'<span class="t-unit"{unit_attr}>{escape(unit)}</span>'
    return (
        '<div style="display: flex; align-items: baseline; justify-content: center; '
        f'gap: 0.07em">{hero_html}{unit_html}</div>'
    )
