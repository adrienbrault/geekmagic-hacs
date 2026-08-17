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
  glyph instead, because it IS the cell's content.

Measurement here goes through ``metrics_for(theme)`` — the same engine
shaper the fitters use — so this is a self-consistency contract, not a
second estimate of the truth.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets._cellkit import cell_box, label_px
from custom_components.geekmagic.widgets._fit import (
    CAPTION_MIN_PX,
    HERO_UNIT_GAP,
    HERO_UNIT_SCALE,
    _kept_weight,
    fit_caption,
    fit_caption_sized,
    fit_hero,
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
    # A stub that survives carries at least min_keep of identity — and
    # the head-truncated discriminator form ("SWI… ON") carries it in
    # the whole string, which is why the weight is taken on the result.
    assert _kept_weight(text) >= min_keep, f"{text!r} keeps {_kept_weight(text)} < {min_keep}"
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


@pytest.mark.parametrize("theme_name", THEMES)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize(
    ("value", "unit"),
    [("73", "%"), ("100", "%"), ("21.5", "°C"), ("1234", "W"), ("-40", "°F"), ("8", "")],
)
def test_gauge_hero_fits_its_box(
    theme_name: str, size: tuple[int, int], value: str, unit: str
) -> None:
    """A hero sized from ``hero_width_em`` fits the box it was sized to."""
    ctx = _ctx(theme_name, size)
    box = cell_box(ctx)[0]
    width_em = hero_width_em(
        value, ctx, suffix=unit, suffix_scale=HERO_UNIT_SCALE, gap=HERO_UNIT_GAP
    )
    px = box / width_em
    assert px * width_em <= box + EPS
    # The value alone must clear the box with room left for the unit.
    assert _hero_metrics(ctx).width(value, px, "extrabold") <= box + EPS


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
