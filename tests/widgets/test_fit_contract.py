"""The measured fitters must keep their promise, for every family.

Since the gauge family's estimating twin was deleted, one caption fitter
and one hero core serve every widget. That makes their contract worth
stating once, in the terms the panel actually cares about — Blitz paints
overflow straight over the bezel, so a fit that lies is a clipped glyph
on a 2" screen.

The contract, checked over a grid of cell sizes x themes (Nunito,
DejaVu, and a theme whose chrome uppercases the kit labels) x captions
(short, long, CJK, and a two-word one with a short discriminator):

* what comes back FITS — its measured width at the returned size, plus
  whatever the caller reserved beside it, is inside the budget;
* the size is inside ``[CAPTION_MIN_PX, top]``, where ``top`` is the
  kit's ``.t-label`` clamp or the caller's ``max_px``;
* a truncated caption either carries ``min_keep`` of identity or comes
  back empty — never a stub that says nothing;
* size is given up BEFORE letters (the whole word at 10px beats a
  fragment at 12px);
* the hero fits its box the same way, suffix included — and where a
  caption drops to "" rather than overflow, a hero walks down to one
  glyph instead, because it IS the cell's content;
* the gauge family's fluid hero keeps that promise through CSS: the
  ``clamp()`` ``hero_font_css`` emits is parsed back out and RESOLVED at
  the cell size, floor and caps included, because that string is what
  ships — recomputing the cap the function just computed would assert
  nothing at all.

Measurement here goes through ``metrics_for(theme)`` — the same engine
shaper the fitters use — so this is a self-consistency contract, not a
second estimate of the truth.
"""

from __future__ import annotations

import re
from dataclasses import replace
from unicodedata import east_asian_width

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets._cellkit import cell_box, label_px
from custom_components.geekmagic.widgets._fit import (
    CAPTION_MIN_PX,
    HERO_UNIT_GAP,
    HERO_UNIT_SCALE,
    fit_caption,
    fit_caption_sized,
    fit_hero,
    hero_font_css,
    hero_width_em,
)
from custom_components.geekmagic.widgets._textfit import metrics_for
from custom_components.geekmagic.widgets.theme import get_theme

# A 3x3 tile, a 2x2 tile, a hero slot, a fullscreen panel, and the two
# extreme shapes (wide/short footer, narrow/tall column) where the kit's
# vmin and vw terms swap places.
SIZES = [(76, 76), (118, 118), (240, 240), (240, 74), (74, 240), (160, 100)]

# watchos: Nunito, mixed-case labels. light: Nunito with 6px of chrome.
# retro: DejaVu AND uppercased labels at wide tracking — the widest
# combination the kit ships, and the one an estimator got most wrong.
THEMES = ["watchos", "light", "retro", "minimal"]

CAPTIONS = [
    "HUMIDITY",
    "POWER CONSUMPTION",
    "リビング温度",
    "SWITCH ON",
    "A",
    "Living Room Temperature Sensor",
]

# Float slack: a width-bound fit lands exactly on its budget.
EPS = 1.0

# The emitted ``clamp()`` terms are rounded to one decimal of vw, worth
# up to 0.05vw — 0.12px on a fullscreen cell — of rounding UP.
ROUND_EPS = 0.25


def _ctx(theme_name: str, size: tuple[int, int]) -> CellContext:
    width, height = size
    return CellContext(width=width, height=height, slot_index=0, theme=get_theme(theme_name))


def _hero_metrics(ctx: CellContext):
    """The measurer the hero fitters use: mixed case even on retro."""
    return replace(metrics_for(ctx.theme), uppercase=False)


def _caption_width(text: str, ctx: CellContext, px: float) -> float:
    """Width the caption markup will really draw, at ``px``."""
    metrics = metrics_for(ctx.theme)
    return metrics.width(text, px, "bold", metrics.label_tracking)


def _identity(stub: str) -> float:
    """How much of a name a stub still carries, in Latin-character units.

    The test's OWN scale, deliberately not ``_fit._kept_weight``: grading
    the fitter with the fitter's own private helper proves only that the
    code equals itself, and would keep passing if that helper's rule
    silently changed. Stated independently here: a character carries one
    unit, a fullwidth East-Asian glyph two (a CJK room name says as much
    in two glyphs as a Latin one does in six), and the ellipsis carries
    none — it is the mark of what was lost, not part of what survived.
    """
    return sum(2.0 if east_asian_width(ch) in {"W", "F"} else 1.0 for ch in stub if ch != "…")


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("caption", CAPTIONS)
@pytest.mark.parametrize("reserve_em", [0.0, 1.6])
def test_fit_caption_sized_fits_its_budget(
    theme_name: str, size: tuple[int, int], caption: str, reserve_em: float
) -> None:
    """The returned (text, px) pair fits ``avail_w``, reserve included."""
    ctx = _ctx(theme_name, size)
    avail_w = cell_box(ctx)[0]
    text, px = fit_caption_sized(caption, ctx, avail_w, reserve_em=reserve_em)
    if not text:
        return
    drawn = _caption_width(text, ctx, px) + reserve_em * px
    assert drawn <= avail_w + EPS, f"{text!r} at {px:.1f}px draws {drawn:.1f} of {avail_w:.1f}"


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("caption", CAPTIONS)
def test_fit_caption_sized_stays_between_the_floor_and_the_top(
    theme_name: str, size: tuple[int, int], caption: str
) -> None:
    """Never below the 10px floor, never above the kit's ``.t-label``."""
    ctx = _ctx(theme_name, size)
    _text, px = fit_caption_sized(caption, ctx, cell_box(ctx)[0])
    top = max(12.0, min(0.12 * min(ctx.width, ctx.height), 18.0))
    assert CAPTION_MIN_PX <= px <= top + 1e-6


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("caption", CAPTIONS)
@pytest.mark.parametrize("max_px", [11.0, 14.0, 26.0])
def test_fit_caption_sized_honours_max_px(
    theme_name: str, size: tuple[int, int], caption: str, max_px: float
) -> None:
    """``max_px`` is the top for a caption in a band of its own."""
    ctx = _ctx(theme_name, size)
    avail_w = cell_box(ctx)[0] * 0.86  # a ring's hole
    text, px = fit_caption_sized(caption, ctx, avail_w, max_px=max_px)
    assert CAPTION_MIN_PX <= px <= max_px + 1e-6
    if text:
        assert _caption_width(text, ctx, px) <= avail_w + EPS


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("caption", CAPTIONS)
@pytest.mark.parametrize("min_keep", [0, 4, 6])
def test_truncation_keeps_identity_or_says_nothing(
    theme_name: str, size: tuple[int, int], caption: str, min_keep: int
) -> None:
    """A stub either carries ``min_keep`` of identity or is dropped."""
    ctx = _ctx(theme_name, size)
    # Deliberately tight, so most of the grid ends up truncating.
    avail_w = cell_box(ctx)[0] * 0.45
    text, px = fit_caption_sized(caption, ctx, avail_w, min_keep=min_keep)
    if not text or text == caption.upper():
        return
    # A stub that survives carries at least min_keep of identity, graded
    # on the whole returned string. That covers the head-truncated
    # discriminator form ("SWI… ON") too, which the fitter returns from
    # its own branch WITHOUT consulting min_keep — it is asserted here
    # rather than exempted, because a form that keeps the discriminator
    # and loses the subject would be exactly the stub this rule rejects.
    assert _identity(text) >= min_keep, f"{text!r} keeps {_identity(text)} < {min_keep}"
    # ...and whatever survives still fits.
    assert _caption_width(text, ctx, px) <= avail_w + EPS


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
def test_size_is_given_up_before_letters(theme_name: str, size: tuple[int, int]) -> None:
    """A caption that fits at 10px is never truncated instead of shrunk."""
    ctx = _ctx(theme_name, size)
    caption = "POWER CONSUMPTION"
    # The width at which the whole word survives at the floor.
    needed = _caption_width(caption, ctx, CAPTION_MIN_PX)
    text, px = fit_caption_sized(caption, ctx, needed + EPS)
    assert text == caption, f"{text!r} truncated although {caption!r} fits at the floor"
    assert px >= CAPTION_MIN_PX


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("caption", CAPTIONS)
def test_fit_caption_fits_at_the_size_it_was_measured_for(
    theme_name: str, size: tuple[int, int], caption: str
) -> None:
    """The text-only fitter fits at the kit size and at a custom one."""
    ctx = _ctx(theme_name, size)
    avail_w = cell_box(ctx)[0] * 0.7
    for font_px in (None, 9.0, label_px(ctx)):
        text = fit_caption(caption, ctx, avail_w, font_px=font_px, min_keep=0)
        if not text:
            continue
        px = font_px if font_px is not None else label_px(ctx)
        assert _caption_width(text, ctx, px) <= avail_w + EPS


def _resolve_clamp(css: str, ctx: CellContext) -> float:
    """Resolve an emitted ``clamp()`` the way the engine will, in px.

    The gauge family's hero is not sized in Python — ``hero_font_css``
    hands the engine a ``clamp(<floor>, min(<n>vmin, <n>vw), <max>)``
    and the cell's own viewport decides. So the contract has to be
    checked on the SHIPPED STRING, resolved against the cell it was
    emitted for; asserting the arithmetic that produced the vw cap would
    only restate the function's own body.
    """
    match = re.fullmatch(
        r"clamp\(\s*([\d.]+)px\s*,\s*min\(\s*([\d.]+)vmin\s*,\s*([\d.]+)vw\s*\)\s*,"
        r"\s*([\d.]+)px\s*\)",
        css,
    )
    assert match is not None, f"unexpected hero font-size CSS: {css!r}"
    low, vmin_term, vw_term, high = (float(group) for group in match.groups())
    preferred = min(vmin_term * min(ctx.width, ctx.height), vw_term * ctx.width) / 100.0
    return max(low, min(preferred, high))


# Values whose fitted hero is comfortable, plus two that are long enough
# to drive the emitted size into its floor on a small cell.
GAUGE_VALUES = [
    ("73", "%"),
    ("100", "%"),
    ("21.5", "°C"),
    ("1234", "W"),
    ("-40", "°F"),
    ("8", ""),
    ("1234567890", "kWh"),
    ("-273.15", "°C"),
]


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize(("value", "unit"), GAUGE_VALUES)
def test_gauge_hero_css_fits_its_box(
    theme_name: str, size: tuple[int, int], value: str, unit: str
) -> None:
    """The CSS ``hero_font_css`` emits draws inside the cell's box.

    The engine resolves the emitted ``clamp()``; this asserts what that
    resolves TO, times the width the value plus its unit occupies per em,
    stays inside the content box — the same promise ``fit_hero`` keeps
    with an explicit pixel size.
    """
    ctx = _ctx(theme_name, size)
    box = cell_box(ctx)[0]
    hero_css, unit_css = hero_font_css(value, ctx, suffix=unit)
    hero_px = _resolve_clamp(hero_css, ctx)
    width_em = hero_width_em(
        value, ctx, suffix=unit, suffix_scale=HERO_UNIT_SCALE, gap=HERO_UNIT_GAP
    )
    assert hero_px * width_em <= box + EPS, (
        f"{hero_css} resolves to {hero_px:.1f}px, drawing {hero_px * width_em:.1f} of {box:.1f}"
    )
    # The value alone must clear the box with room left for the unit.
    assert _hero_metrics(ctx).width(value, hero_px, "extrabold") <= box + EPS
    # The unit rides the hero's cap at HERO_UNIT_SCALE — except where its
    # own 11px legibility floor holds it up, which is the ONE documented
    # place it draws wider than the share ``width_em`` reserved for it
    # (an 11px "%" beside a 20px hero is more than 0.38 of it). Bounded
    # here so a future edit cannot raise that floor, or break the
    # coupling, without saying so.
    if unit:
        unit_px = _resolve_clamp(unit_css, ctx)
        bound = max(11.0, hero_px * HERO_UNIT_SCALE)
        assert unit_px <= bound + ROUND_EPS, (
            f"unit {unit_css} resolves to {unit_px:.1f}px, over the "
            f"{bound:.1f}px a {hero_px:.1f}px hero allows it"
        )


@pytest.mark.parametrize("theme_name", THEMES)
# Real small slots: a 4x4-ish tile, a compact gauge cell, a 3x3 tile
# and a split column. Every one of them drives these values into the
# floor — the assertion below fails loudly if one stops doing so.
@pytest.mark.parametrize("size", [(40, 40), (52, 48), (69, 65), (69, 224)])
@pytest.mark.parametrize(
    ("value", "unit"), [("1234567890", "kWh"), ("-273.15", "°C"), ("1234567", "")]
)
def test_gauge_hero_css_shrinks_past_its_floor_rather_than_overflow(
    theme_name: str, size: tuple[int, int], value: str, unit: str
) -> None:
    """A value too long for the floor shrinks below it instead of bleeding.

    ``clamp()``'s first term is a floor the engine applies AFTER the vw
    cap, so a fixed one silently overrides the box on a small enough
    cell — which on this panel means glyphs on the bezel, the one thing
    the fit exists to prevent. ``hero_font_css`` therefore lowers the
    floor to the box when the two disagree, the fluid analogue of
    ``fit_hero`` measuring what it is about to return.

    Asserted on the reserve model (``width_em``), which is what the
    function computes its cap from. The unit's floor rides down with the
    hero's but keeps the kit's 11:16 ratio rather than its 0.38 share, so
    a floor-bound pair can still spend a few px over the box — bounded
    and documented in ``hero_font_css``, where the alternative is a
    discontinuous floor or unreadable units on every gauge tile.
    """
    ctx = _ctx(theme_name, size)
    box = cell_box(ctx)[0]
    hero_css, _unit_css = hero_font_css(value, ctx, suffix=unit)
    hero_px = _resolve_clamp(hero_css, ctx)
    width_em = hero_width_em(
        value, ctx, suffix=unit, suffix_scale=HERO_UNIT_SCALE, gap=HERO_UNIT_GAP
    )
    assert hero_px < 16.0, f"{hero_css} does not reach the floor — case proves nothing"
    assert hero_px * width_em <= box + EPS


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize(
    ("value", "suffix"),
    [("23", "°C"), ("12:45", ""), ("1.234", "kWh"), ("リビング", ""), ("Unavailable", "")],
)
def test_card_hero_fits_its_box(
    theme_name: str, size: tuple[int, int], value: str, suffix: str
) -> None:
    """``fit_hero``'s every line fits, suffix on the last one included."""
    ctx = _ctx(theme_name, size)
    avail_w, avail_h = cell_box(ctx)
    fit = fit_hero(value, ctx, avail_w, avail_h * 0.8, suffix=suffix)
    # Heroes render mixed-case even where the chrome uppercases labels,
    # and ``fit_hero`` was asked for the kit's default (zero) tracking.
    metrics = _hero_metrics(ctx)
    for index, line in enumerate(fit.lines):
        drawn = metrics.width(line, fit.px, "extrabold")
        if index == len(fit.lines) - 1 and suffix:
            drawn += metrics.width(suffix, fit.px, "bold") * 0.46
        assert drawn <= avail_w + 2 * EPS, f"{line!r} at {fit.px:.1f}px draws {drawn:.1f}"


# The min_px floor path: boxes narrow enough that even 12px cannot hold
# the value, so ``fit_hero`` has to truncate rather than shrink. Reached
# on real geometry — a 3x3 tile's hero band at 0.45 of its content box
# is ~28px, and "Unavailable" or a CJK room name blows straight past it.
# Every box here is wide enough for the documented one-glyph floor, so
# "fits" and "never empty" do not contradict each other: the widest
# combination below is retro's "km/h" reserve (15.4px at the 12px floor)
# beside a fullwidth glyph (12px), so 28px is the narrowest box that can
# hold a minimal hero at all. Narrower boxes are the floor's own
# territory and only promise a non-empty answer.
FLOOR_BOXES = [28.0, 34.0, 40.0, 48.0]
BELOW_FLOOR_BOXES = [6.0, 12.0, 18.0, 24.0]

FLOOR_VALUES = [
    ("Unavailable", ""),
    ("Preheating", ""),
    ("リビング温度", ""),
    ("室内温度", "°C"),
    ("1234567890", "kWh"),
    ("23.5", "km/h"),
    ("100", "%"),
]


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("box", FLOOR_BOXES)
@pytest.mark.parametrize(("value", "suffix"), FLOOR_VALUES)
def test_hero_at_the_min_px_floor_still_measures_inside_its_box(
    theme_name: str, box: float, value: str, suffix: str
) -> None:
    """A hero truncated at the floor fits — ``truncate`` alone does not.

    ``TextMetrics.truncate`` guarantees CHARACTERS, not width: below its
    ``min_chars`` it returns "Un…" whatever the budget, and the suffix
    reserve can drive that budget to zero or below. The fitter measures
    what it is about to return instead of trusting the promise.
    """
    ctx = _ctx(theme_name, (76, 76))
    metrics = _hero_metrics(ctx)
    fit = fit_hero(value, ctx, box, 24.0, suffix=suffix)

    reserve = metrics.width(suffix, fit.px, "bold") * 0.46 if suffix else 0.0
    drawn = metrics.width(fit.text, fit.px, "extrabold") + reserve
    assert drawn <= box + EPS, f"{fit.text!r} at {fit.px:.1f}px draws {drawn:.1f} of {box:.1f}"


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("box", [*BELOW_FLOOR_BOXES, *FLOOR_BOXES])
@pytest.mark.parametrize(("value", "suffix"), FLOOR_VALUES)
def test_a_hero_is_never_empty(theme_name: str, box: float, value: str, suffix: str) -> None:
    """A hero IS the cell's content — it degrades, it does not vanish.

    Where a caption drops to "" rather than paint over the bezel, a hero
    walks down to a single glyph. ``BELOW_FLOOR_BOXES`` are narrower than
    that floor: the only guarantee left there is that something comes
    back at all.
    """
    ctx = _ctx(theme_name, (76, 76))
    fit = fit_hero(value, ctx, box, 24.0, suffix=suffix)

    assert fit.lines
    assert all(line for line in fit.lines)


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("box", FLOOR_BOXES)
def test_forced_lines_are_measured_like_wrapped_ones(theme_name: str, box: float) -> None:
    """A clock's stacked HH/MM answers to the same rule.

    ``lines=`` skips the wrap search, not the measured tail — the floor
    can push a forced layout over its budget exactly like a lone value.
    """
    ctx = _ctx(theme_name, (76, 76))
    metrics = _hero_metrics(ctx)
    fit = fit_hero("12:45", ctx, box, 40.0, lines=["12", "45"])

    for line in fit.lines:
        drawn = metrics.width(line, fit.px, "extrabold")
        assert drawn <= box + EPS, f"{line!r} at {fit.px:.1f}px draws {drawn:.1f}"
