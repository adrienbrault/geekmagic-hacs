"""The measured caption and hero fitters, for every widget family.

The fluid kit sizes the hero with ``clamp()``, which cannot know how
long a value is: six characters at the kit's cap overflow a 240px panel,
and Blitz neither shrinks nor clips the overflow. So widgets measure
their own content with the embedded font metrics (:mod:`._textfit`) and
hand a fitted pixel size to the markup.

Both fitters live here so a caption fits the same way wherever it is
drawn. A gauge's "HUMIDITY" and an entity card's "HUMIDITY" are the same
string in the same cell, and used to reach different lengths because the
gauge family carried its own estimator (average glyph advances by font
family) beside this module's engine-shaped measurement — which also cost
the gauges CJK safety, since an estimator cannot know that a fullwidth
glyph is an em wide. There is now one implementation:

* :func:`fit_caption_sized` / :func:`fit_caption` — a caps caption gives
  up SIZE before it gives up letters, down to :data:`CAPTION_MIN_PX`,
  and only then truncates; ``min_keep`` says how much identity has to
  survive for the stub to be worth drawing.
* :func:`fit_hero` / :func:`hero_block` — the big value plus an optional
  smaller secondary suffix (unit, AM/PM) on the same baseline, fitted to
  a known pixel box. :func:`hero_font_css` is the fluid variant for
  widgets whose hero band has no measured height (the gauge family):
  same measured width, emitted as the ``clamp()`` cap.

:func:`hero_width_em` is the core both hero paths share — the width of a
value plus its suffix, in units of the hero's own font size.

The box a fit lands in comes from :mod:`._cellkit`, which owns cell
geometry for every widget family. Widgets import that module directly,
so this one's interface is fitting and nothing else.

Everything here is geometry and structure; colour stays with the theme.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape
from typing import TYPE_CHECKING

from ._cellkit import cell_box, label_px
from ._textfit import metrics_for

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ._textfit import TextMetrics

# Share of the free height a hero may spend. What is left becomes the
# ``space-evenly`` gaps that give the cell its rhythm — a hero that eats
# 100% of the height reads as a cell about to burst. The kit's 3%
# padding already guarantees the outer inset, so a lone hero can be
# generous; stacked bands need room to read as separate bands.
HERO_SHARE_SOLO = 0.92
HERO_SHARE_STACKED = 0.80

# Kit line-heights (.t-hero is 0.85; wrapped text needs descender room).
HERO_LINE = 0.85
WRAP_LINE = 1.08

# The secondary half of a hero (unit, AM/PM) relative to the value.
SUFFIX_SCALE = 0.46
# The gauge family's unit is smaller still — the kit's ratio between
# .t-unit and .t-hero — and rides a baseline flex row whose gap it
# declares itself.
HERO_UNIT_SCALE = 0.38
HERO_UNIT_GAP = 0.07
# Units that start with a symbol (°C, %) hang off the digits; word units
# (W, km/h) need a real word space.
_SUFFIX_GAP_TIGHT = 0.05
_SUFFIX_GAP_WORD = 0.20

# Hero weight to measure with: the kit's 800. Themes that lighten it
# only ever get narrower, so this stays on the safe side.
_HERO_WEIGHT = "extrabold"

# Wrapping only wins if it buys a meaningfully bigger value; below this
# it just costs a line break.
_WRAP_GAIN = 1.15

# A width-bound fit lands exactly on the budget, where float noise can
# read as an overflow — never truncate for less than this many pixels.
_FIT_EPS = 1.0


# A caption may shrink this far below the kit size before truncating —
# a whole word at 10px beats "LIVI…" at 12px on a panel this small.
CAPTION_MIN_PX = 10.0

# Identity a truncated caption must still carry to be worth drawing, in
# the Latin-character units of :func:`_kept_weight`. "NET…" is noise;
# "NETW…" is not. Callers whose cell has nothing else left to say pass
# ``min_keep=0`` — an unlabeled gauge is a number without a meaning.
CAPTION_MIN_KEEP = 4


def _kept_weight(stub: str) -> float:
    """Identity carried by a truncated stub, in Latin-character units.

    Fullwidth (CJK) glyphs carry roughly a word each — "リビ" says as
    much as "LIVING" — so the Latin-centric "4 characters" survival rule
    counts them double.
    """
    from unicodedata import east_asian_width  # noqa: PLC0415 (stdlib, hot path)

    return sum(2.0 if east_asian_width(ch) in ("W", "F") else 1.0 for ch in stub.rstrip("…"))


def _caption_fits(text: str, metrics: TextMetrics, px: float, budget: float) -> bool:
    """Whether a caption really lands inside ``budget`` as drawn.

    :meth:`TextMetrics.truncate` promises a minimum number of characters,
    not a width: on a budget too narrow for even a three-letter stub it
    hands back "HUM…" anyway. Blitz would paint that over the bezel, so
    the last word on a fit is measured, not assumed.
    """
    return metrics.width(text, px, "bold", metrics.label_tracking) <= budget + _FIT_EPS


def fit_caption_sized(
    text: str,
    ctx: CellContext,
    avail_w: float,
    *,
    reserve_em: float = 0.0,
    max_px: float | None = None,
    min_keep: int = CAPTION_MIN_KEEP,
) -> tuple[str, float]:
    """Fit a caps caption: shrink to the full word before truncating.

    Returns ``(text, px)``. The caption starts at the kit's ``.t-label``
    size and gives up size before it gives up letters, down to
    ``CAPTION_MIN_PX``; only below that is it ellipsized. ``reserve_em``
    is width spent beside the caption (an inline chip icon), in caption
    ems, so it scales down with the type. ``max_px`` replaces the kit
    size as the top for a caption that lives in a band of its own — a
    ring's hole caps its caption by the value it sits under, not by the
    cell.

    A stub is worse than nothing — but only a genuinely destroyed stub:
    "TEMPERA…" still identifies a temperature, and even "GARAG…" says
    which room, while "GAR…" says nothing. A caption survives when
    ``min_keep`` characters make it through; below that the cell spends
    the room on the value instead. ``min_keep=0`` relaxes THAT rule only,
    for a cell whose caption is all it has left to say: whatever survives
    must still MEASURE inside the band (:func:`_caption_fits`), because a
    stub Blitz paints over the bezel is not a caption at any ``min_keep``.
    """
    metrics = metrics_for(ctx.theme)
    upper = text.upper()
    # The kit clamp's vw term guards UNMEASURED captions against
    # overflow; a measured caption doesn't need it — a short "HUMID" in
    # a wide sidebar cell may take the full 18px cap instead of being
    # width-capped into a whisper.
    top = (
        max(CAPTION_MIN_PX, max_px)
        if max_px is not None
        else max(12.0, min(0.12 * min(ctx.width, ctx.height), 18.0))
    )
    width_em = metrics.width(upper, 1.0, "bold", metrics.label_tracking) + reserve_em
    if width_em > 0:
        px_fit = avail_w / width_em
        if px_fit >= CAPTION_MIN_PX:
            return upper, min(top, px_fit)
    budget = avail_w - reserve_em * CAPTION_MIN_PX
    fitted = metrics.truncate(
        upper,
        CAPTION_MIN_PX,
        budget,
        "bold",
        tracking=metrics.label_tracking,
        style="end",
        min_chars=3,
    )
    if fitted != upper:
        # End-truncation can cut exactly the discriminating token —
        # "SWITCH ON" and "SWITCH OFF" both become "SWITCH…". When the
        # last word is a short discriminator, keep it and truncate the
        # head instead: "SWI… ON" / "SWI… OFF".
        words = upper.split()
        if len(words) >= 2 and len(words[-1]) <= 4:
            tail = words[-1]
            tail_w = metrics.width(f" {tail}", CAPTION_MIN_PX, "bold", metrics.label_tracking)
            head = metrics.truncate(
                " ".join(words[:-1]),
                CAPTION_MIN_PX,
                budget - tail_w,
                "bold",
                tracking=metrics.label_tracking,
                style="end",
                min_chars=3,
            )
            combined = f"{head} {tail}"
            if _kept_weight(head) >= 3 and _caption_fits(combined, metrics, CAPTION_MIN_PX, budget):
                return combined, CAPTION_MIN_PX
        if _kept_weight(fitted) < min_keep:
            return "", CAPTION_MIN_PX
    if not _caption_fits(fitted, metrics, CAPTION_MIN_PX, budget):
        return "", CAPTION_MIN_PX
    return fitted, CAPTION_MIN_PX


def fit_caption(
    text: str,
    ctx: CellContext,
    avail_w: float,
    *,
    font_px: float | None = None,
    min_keep: int = CAPTION_MIN_KEEP,
) -> str:
    """Truncate a caps caption to the width it actually has.

    Text-only variant of :func:`fit_caption_sized` for callers whose
    caption size is already decided — the kit's ``.t-label`` by default,
    or ``font_px`` when the caller draws it at a size of its own (a
    multi-progress row label answers to the ROW's pitch, not the cell).
    """
    metrics = metrics_for(ctx.theme)
    upper = text.upper()
    px = font_px if font_px is not None else label_px(ctx)
    fitted = metrics.truncate(
        upper,
        px,
        avail_w,
        "bold",
        tracking=metrics.label_tracking,
        style="end",
        min_chars=3,
    )
    if fitted != upper and (
        _kept_weight(fitted) < min_keep or not _caption_fits(fitted, metrics, px, avail_w)
    ):
        return ""
    return fitted


def _balance(text: str, count: int = 2) -> list[str]:
    """Split text over ``count`` lines of near-equal length.

    Balanced beats greedy here: minimising the longest line is what lets
    the type be biggest, and it avoids the orphan word a greedy wrap
    strands on the last line.
    """
    words = text.split()
    if len(words) < 2 or count < 2:
        return [text]
    count = min(count, len(words))
    # best[k][i]: shortest possible longest-line for the first i words
    # over k lines (line length measured in characters, which tracks
    # width closely enough for balancing).
    best: list[list[float]] = [[float("inf")] * (len(words) + 1) for _ in range(count + 1)]
    split: list[list[int]] = [[0] * (len(words) + 1) for _ in range(count + 1)]
    best[0][0] = 0.0
    for k in range(1, count + 1):
        for i in range(1, len(words) + 1):
            for j in range(k - 1, i):
                line = len(" ".join(words[j:i]))
                score = max(best[k - 1][j], line)
                if score < best[k][i]:
                    best[k][i] = score
                    split[k][i] = j
    lines: list[str] = []
    i = len(words)
    for k in range(count, 0, -1):
        j = split[k][i]
        lines.append(" ".join(words[j:i]))
        i = j
    return list(reversed(lines))


@dataclass(frozen=True)
class HeroFit:
    """A fitted hero: the size, and the lines it was fitted to."""

    px: float
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        """The fitted value as one string."""
        return " ".join(self.lines)

    @property
    def wrapped(self) -> bool:
        """True when the value was laid out over several lines."""
        return len(self.lines) > 1


def fit_hero(
    text: str,
    ctx: CellContext,
    avail_w: float,
    avail_h: float,
    *,
    suffix: str = "",
    suffix_scale: float = SUFFIX_SCALE,
    tracking: float = 0.0,
    allow_wrap: bool = False,
    max_lines: int = 2,
    lines: list[str] | None = None,
    max_px: float = 128.0,
    min_px: float = 12.0,
) -> HeroFit:
    """Largest size at which ``text`` (+ its suffix) fits its band.

    ``tracking`` is the letter-spacing the markup will apply, in em —
    measuring without it throws away the width tight tracking buys back.
    ``lines`` forces a multi-line layout (a clock stacking HH over MM);
    otherwise ``allow_wrap`` lets a multi-word value take up to
    ``max_lines`` lines when that makes the type meaningfully bigger.
    Anything that still does not fit at ``min_px`` is truncated, because
    Blitz would draw the overflow straight over the panel edge — and the
    truncated form is MEASURED before it is returned, down to the one-glyph
    floor :func:`_line_inside` documents. A hero is never empty.
    """
    metrics = _hero_metrics(ctx)
    if not text:
        return HeroFit(min_px, (text,))

    def fit_parts(parts: list[str], reserve_em: float = 0.0) -> float:
        widest = max(value_width_em(part, ctx, tracking=tracking) for part in parts) + reserve_em
        return min(
            max_px,
            avail_w / max(widest, 1e-6),
            avail_h / (len(parts) * (WRAP_LINE if len(parts) > 1 else HERO_LINE)),
        )

    reserve = suffix_width_em(suffix, ctx, scale=suffix_scale)

    if lines:
        # A forced layout (a clock stacking HH over MM) skips the wrap
        # search, but not the measured tail: the min_px floor can put its
        # lines over the budget exactly like a single one's.
        px, layout = fit_parts(lines, reserve), list(lines)
    else:
        px = fit_parts([text], reserve)
        layout = [text]
        if allow_wrap and not suffix:
            for count in range(2, max_lines + 1):
                parts = _balance(text, count)
                if len(parts) < count:
                    break
                candidate = fit_parts(parts)
                if candidate > px * _WRAP_GAIN:
                    px, layout = candidate, parts

    px = max(min_px, px)
    # The min_px floor can push lines back over the budget — EVERY line,
    # not just a lone one: Blitz draws the overflow straight over the
    # panel edge, and a wrapped sentence at the floor clips mid-glyph on
    # both sides. The suffix rides the last line only.
    fitted = [
        _line_inside(
            line,
            metrics,
            px,
            avail_w - (reserve * px if i == len(layout) - 1 else 0.0),
            tracking,
        )
        for i, line in enumerate(layout)
    ]
    return HeroFit(px, tuple(fitted))


def _line_inside(line: str, metrics: TextMetrics, px: float, budget: float, tracking: float) -> str:
    """``line``, shortened until it MEASURES inside ``budget`` at ``px``.

    :meth:`TextMetrics.truncate` promises a minimum number of CHARACTERS,
    not a width: below its ``min_chars`` it hands back "Un…" whatever the
    budget, and at the ``min_px`` floor the budget can be arbitrarily
    small — even negative, when a "kWh" suffix reserves more than the box
    on a 3x3 tile. Blitz would paint that stub over the bezel.

    A caption answers this by returning "" (see :func:`_caption_fits`).
    A hero cannot: it IS the cell's content, and an empty one says less
    than a clipped one. So it walks the stub down a glyph at a time and
    stops at the widest form that fits, in this order:

    1. the whole line, then progressively shorter ``"<head>…"`` stubs;
    2. one character plus the ellipsis ("2…") — the documented minimum
       for a truncated hero;
    3. that character bare ("2"), for the box too narrow even for the
       mark.

    Step 3 is the floor. If a single glyph still does not fit, it is
    returned anyway: below one character there is no hero left to draw,
    and every caller has already spent its cell on this value.
    """

    def fits(candidate: str) -> bool:
        return metrics.width(candidate, px, _HERO_WEIGHT, tracking) <= budget + _FIT_EPS

    if fits(line):
        return line
    cut = metrics.truncate(
        line, px, budget, _HERO_WEIGHT, tracking=tracking, style="end", min_chars=2
    )
    if fits(cut):
        return cut
    head = cut.rstrip("…") or line
    for keep in range(len(head) - 1, 0, -1):
        candidate = head[:keep].rstrip() + "…"
        if fits(candidate):
            return candidate
    return head[:1]


def _hero_metrics(ctx: CellContext) -> TextMetrics:
    """Measurer for hero text.

    Heroes render mixed-case even on themes whose chrome uppercases the
    LABELS (retro's ``text-transform`` sits on ``.t-label`` only) —
    measuring them uppercased costs 9-14% of the size for nothing.
    """
    return replace(metrics_for(ctx.theme), uppercase=False)


def value_width_em(text: str, ctx: CellContext, *, tracking: float = 0.0) -> float:
    """Width of a hero value, in units of its own font size."""
    return _hero_metrics(ctx).width(text, 1.0, _HERO_WEIGHT, tracking)


def suffix_width_em(
    suffix: str, ctx: CellContext, *, scale: float = SUFFIX_SCALE, gap: float | None = None
) -> float:
    """Width a hero suffix adds, in hero-em (0 when there is none).

    ``gap`` overrides the default word/symbol spacing for markup that
    declares its own (the gauge family's baseline flex row). Reserving
    more gap than the markup draws only makes the hero smaller;
    reserving less puts it over the bezel — so a caller's gap must be at
    least the one it renders.
    """
    if not suffix:
        return 0.0
    if gap is None:
        gap = _SUFFIX_GAP_WORD if suffix[0].isalnum() else _SUFFIX_GAP_TIGHT
    return _hero_metrics(ctx).width(suffix, 1.0, "bold") * scale + gap


def hero_width_em(
    text: str,
    ctx: CellContext,
    *,
    suffix: str = "",
    suffix_scale: float = SUFFIX_SCALE,
    gap: float | None = None,
    tracking: float = 0.0,
) -> float:
    """Width of a hero value plus its suffix, in units of the hero size.

    The core every hero fitter shares: divide the box by this and you
    have the size that fits it, whether the caller spends the answer as
    a pixel size (:func:`fit_hero`), a ``clamp()`` cap
    (:func:`hero_font_css`) or a circle's chord (a ring's hole).
    """
    return value_width_em(text, ctx, tracking=tracking) + suffix_width_em(
        suffix, ctx, scale=suffix_scale, gap=gap
    )


def hero_font_css(
    text: str,
    ctx: CellContext,
    *,
    suffix: str = "",
    cap_vw: float = 38.0,
    cap_vmin: float = 48.0,
) -> tuple[str, str]:
    """Fluid ``(hero, suffix)`` font sizes for a value + unit pair.

    For heroes whose band has no measured height — the gauge family
    spreads its bands with ``space-evenly``, so only the engine knows
    what the hero ends up with. The vmin term keeps that fluidity; the
    WIDTH cap is what Python can answer exactly, and it is the one the
    kit gets wrong: ``.t-hero`` caps at ``30vw`` because it must survive
    a five-character value, while a gauge knows its own string. Short
    values grow, long ones shrink, and nothing is ever clipped.
    """
    width_em = hero_width_em(
        text, ctx, suffix=suffix, suffix_scale=HERO_UNIT_SCALE, gap=HERO_UNIT_GAP
    )
    # The cap is in vw, so the budget has to be too: the content box the
    # fragment really has, as a share of the cell viewport.
    share = 100.0 * cell_box(ctx)[0] / max(ctx.width, 1e-6)
    cap = min(cap_vw, share / max(width_em, 1e-6))
    hero = f"clamp(16px, min({cap_vmin:.0f}vmin, {cap:.1f}vw), 124px)"
    unit_css = (
        f"clamp(11px, min({cap_vmin * HERO_UNIT_SCALE:.0f}vmin, "
        f"{cap * HERO_UNIT_SCALE:.1f}vw), 46px)"
    )
    return hero, unit_css


def hero_block(
    fit: HeroFit | str,
    px: float | None = None,
    *,
    suffix: str = "",
    suffix_scale: float = SUFFIX_SCALE,
    tracking: float | None = None,
) -> str:
    """The hero band: fitted value plus an optional secondary suffix.

    Takes the :class:`HeroFit` (which carries the line layout), or a
    ``text, px`` pair for single-line heroes.

    Rendered as a block child of ``.t-hero``: a block child suppresses
    the parent's line-box strut, so the band is exactly as tall as the
    fitted type instead of reserving room for the kit's ``clamp()`` cap.
    Multi-line heroes get one block per line rather than an engine wrap —
    Blitz breaks lines against the flex item's own width, which ignores
    the cell's percentage padding, so leaving it to wrap puts long lines
    into the margin.

    The suffix is an inline ``.t-unit`` span on the last line, which
    keeps it on the value's baseline — smaller and secondary, the way a
    unit should read.
    """
    if isinstance(fit, HeroFit):
        lines, size = fit.lines, fit.px
    else:
        lines, size = (fit,), float(px or 0.0)

    multiline = len(lines) > 1
    # letter-spacing MUST be restated here in em: the kit declares
    # -0.035em on .t-hero, which computes against the CLAMP size (up to
    # 124px → -4.3px) and inherits as that pixel value — at a fitted
    # 20px it swallows the space glyphs entirely. Restating it on the
    # fitted wrapper recomputes it against the real size.
    spacing = tracking if tracking is not None else -0.035
    style = (
        f"font-size: {size:.1f}px; "
        f"line-height: {WRAP_LINE if multiline else HERO_LINE}; "
        f"letter-spacing: {spacing}em"
    )

    tail = ""
    if suffix:
        gap = _SUFFIX_GAP_WORD if suffix[0].isalnum() else _SUFFIX_GAP_TIGHT
        tail = (
            f'<span class="t-unit" style="font-size: {suffix_scale}em; '
            f'margin-left: {gap}em">{escape(suffix)}</span>'
        )

    body = "".join(
        f"<div>{escape(line)}{tail if i == len(lines) - 1 else ''}</div>"
        if multiline
        else f"{escape(line)}{tail}"
        for i, line in enumerate(lines)
    )
    return f'<div style="{style}">{body}</div>'
