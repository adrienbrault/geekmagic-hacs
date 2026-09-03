"""Cell geometry and hero typography for the card-family widgets.

The fluid kit sizes the hero with ``clamp()``, which cannot know how
long a value is: six characters at the kit's cap overflow a 240px panel,
and Blitz neither shrinks nor clips the overflow. So the card family
(entity, clock, text, icon) measures its own content with the embedded
font metrics (:mod:`._textfit`) and hands a fitted pixel size to the
markup.

Two shapes are shared here on purpose, so the canonical widgets stay
typographically identical:

* :func:`cell_box` — the pixel box a fragment really has, after theme
  chrome and the kit's ``.cell`` padding.
* :func:`hero_block` — the hero band: big value, optional smaller
  secondary suffix (unit, AM/PM) sitting on the same baseline.

Everything here is geometry and structure; colour stays with the theme.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape
from typing import TYPE_CHECKING

from ._textfit import metrics_for

if TYPE_CHECKING:
    from ..htmldoc import CellContext

# Chromed themes paint ``.root`` with up to 6px of padding plus a 1px
# border; chrome-less themes (watchos) spend none of that — reserving it
# anyway costs the hero ~7% of its size. The kit's ``.cell`` adds 3%
# padding on all four sides (CSS resolves percentage padding against the
# width, vertically too).
_CHROME_INSET = 7.0
_CHROMELESS_INSET = 1.5
_CELL_PADDING = 0.03

# Share of the free height a hero may spend. What is left becomes the
# ``space-evenly`` gaps that give the cell its rhythm — a hero that eats
# 100% of the height reads as a cell about to burst. The kit's 4%
# padding already guarantees the outer inset, so a lone hero can be
# generous; stacked bands need room to read as separate bands.
HERO_SHARE_SOLO = 0.92
HERO_SHARE_STACKED = 0.80

# Kit line-heights (.t-hero is 0.85; wrapped text needs descender room).
HERO_LINE = 0.85
WRAP_LINE = 1.08

# The secondary half of a hero (unit, AM/PM) relative to the value.
SUFFIX_SCALE = 0.46
# Units that start with a symbol (°C, %) hang off the digits; word units
# (W, km/h) need a real word space.
_SUFFIX_GAP_TIGHT = 0.05
_SUFFIX_GAP_WORD = 0.20

# Kit breakpoints, mirrored so Python can predict which bands survive.
HIDE_SHORT_H = 100
HIDE_SMALL = 130

# Hero weight to measure with: the kit's 700. Themes that lighten it
# only ever get narrower, so this stays on the safe side.
_HERO_WEIGHT = "bold"

# The kit's .t-hero tracking, restated on fitted heroes (see hero_block).
HERO_TRACKING_EM = -0.02

# Wrapping only wins if it buys a meaningfully bigger value; below this
# it just costs a line break.
_WRAP_GAIN = 1.15

# A width-bound fit lands exactly on the budget, where float noise can
# read as an overflow — never truncate for less than this many pixels.
_FIT_EPS = 1.0


def cell_box(ctx: CellContext) -> tuple[float, float]:
    """Usable content box (width, height) in px inside a cell."""
    theme = ctx.theme
    chromed = theme is not None and bool((theme.chrome_css or "").strip())
    inset = _CHROME_INSET if chromed else _CHROMELESS_INSET
    inner_w = max(12.0, ctx.width - 2 * inset)
    inner_h = max(12.0, ctx.height - 2 * inset)
    pad = 2 * _CELL_PADDING * inner_w
    return max(8.0, inner_w - pad), max(8.0, inner_h - pad)


def label_px(ctx: CellContext) -> float:
    """Size the kit resolves for ``.t-label`` in this cell.

    Mirrors ``clamp(12px, min(12vmin, 9vw), 18px)``.
    """
    return max(12.0, min(0.12 * min(ctx.width, ctx.height), 0.09 * ctx.width, 18.0))


def chip_px(ctx: CellContext) -> float:
    """Size the kit resolves for ``.chip`` — ``clamp(10px, 11vmin, 18px)``."""
    return max(10.0, min(0.11 * min(ctx.width, ctx.height), 18.0))


def chip_band_px(ctx: CellContext) -> float:
    """Outer height of a chip strip (font + the pill's 0.42em padding)."""
    return chip_px(ctx) * 1.9


def caption_visible(ctx: CellContext) -> bool:
    """True when the kit keeps ``.hide-short`` bands (caption, feature icon)."""
    return ctx.height >= HIDE_SHORT_H


def small_visible(ctx: CellContext) -> bool:
    """True when the kit keeps ``.hide-small`` bands (chip strips)."""
    return ctx.width >= HIDE_SMALL and ctx.height >= HIDE_SMALL


# A caption may shrink this far below the kit size before truncating —
# a whole word at 10px beats "LIVI…" at 12px on a panel this small.
CAPTION_MIN_PX = 10.0

# A trailing word this short (ON / OFF / AC / TV) is what tells two
# captions apart, so truncation keeps it; a longer one (DOOR) is dropped
# whole in favour of the leading word.
_DISCRIMINATOR_LEN = 3

# Shorter words for captions that cannot fit whole, tried before any
# letter is cut. Deliberately tiny: only words a glance reads the same.
_SHORT_WORDS = {
    "TEMPERATURE": "TEMP",
    "HUMIDITY": "HUMID",
    "ILLUMINANCE": "LIGHT",
    "PRECIPITATION": "RAIN",
    "CONSUMPTION": "USAGE",
    "PRODUCTION": "OUTPUT",
    "BATTERY": "BATT",
    "PRESSURE": "PRESS",
    "BATHROOM": "BATH",
    "BEDROOM": "BED",
}


def _kept_weight(stub: str) -> float:
    """Identity carried by a truncated stub, in Latin-character units.

    Fullwidth (CJK) glyphs carry roughly a word each — "リビ" says as
    much as "LIVING" — so the Latin-centric "4 characters" survival rule
    counts them double.
    """
    from unicodedata import east_asian_width  # noqa: PLC0415 (stdlib, hot path)

    return sum(2.0 if east_asian_width(ch) in ("W", "F") else 1.0 for ch in stub.rstrip("…"))


def fit_caption_sized(
    text: str,
    ctx: CellContext,
    avail_w: float,
    *,
    reserve_em: float = 0.0,
) -> tuple[str, float]:
    """Fit a caps caption: shrink to the full word before truncating.

    Returns ``(text, px)``. The caption starts at the kit's ``.t-label``
    size and gives up size before it gives up letters, down to
    ``CAPTION_MIN_PX``; only below that is it ellipsized. ``reserve_em``
    is width spent beside the caption (an inline chip icon), in caption
    ems, so it scales down with the type.

    A stub is worse than nothing — but only a genuinely destroyed stub:
    "TEMPERA…" still identifies a temperature, and even "GARAG…" says
    which room, while "GAR…" says nothing. A caption survives when at
    least 4 characters make it through; below that the cell spends the
    room on the value instead.
    """
    metrics = metrics_for(ctx.theme)
    upper = text.upper()
    # The kit clamp's vw term guards UNMEASURED captions against
    # overflow; a measured caption doesn't need it — a short "HUMID" in
    # a wide sidebar cell may take the full 18px cap instead of being
    # width-capped into a whisper.
    top = max(12.0, min(0.12 * min(ctx.width, ctx.height), 18.0))
    width_em = metrics.width(upper, 1.0, "bold", metrics.label_tracking) + reserve_em
    if width_em > 0:
        px_fit = avail_w / width_em
        if px_fit >= CAPTION_MIN_PX:
            return upper, min(top, px_fit)
    budget = avail_w - reserve_em * CAPTION_MIN_PX

    def fits(candidate: str) -> bool:
        return metrics.width(candidate, CAPTION_MIN_PX, "bold", metrics.label_tracking) <= budget

    # Before cutting letters: a shorter word for the same thing
    # ("TEMPERATURE" -> "TEMP"), then whole leading words ("LIVING ROOM"
    # -> "LIVING"). Both keep a caption that still names the cell where
    # "TEMPERA…" and "LIV… ROOM" only half do.
    short = " ".join(_SHORT_WORDS.get(word, word) for word in upper.split())
    if short != upper and fits(short):
        return short, CAPTION_MIN_PX
    words = upper.split()
    tail_discriminates = len(words) >= 2 and len(words[-1]) <= _DISCRIMINATOR_LEN
    if not tail_discriminates:
        for keep in range(len(words) - 1, 0, -1):
            head = " ".join(words[:keep])
            if _kept_weight(head) >= 4 and fits(head):
                return head, CAPTION_MIN_PX
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
        if tail_discriminates:
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
            if _kept_weight(head) >= 3:
                return f"{head} {tail}", CAPTION_MIN_PX
        if _kept_weight(fitted) < 4:
            return "", CAPTION_MIN_PX
    return fitted, CAPTION_MIN_PX


def fit_caption(text: str, ctx: CellContext, avail_w: float) -> str:
    """Truncate a caps caption to the width it actually has.

    Text-only variant of :func:`fit_caption_sized` for callers that keep
    the kit's ``.t-label`` size: measures at that size and truncates.
    """
    metrics = metrics_for(ctx.theme)
    upper = text.upper()
    fitted = metrics.truncate(
        upper,
        label_px(ctx),
        avail_w,
        "bold",
        tracking=metrics.label_tracking,
        style="end",
        min_chars=3,
    )
    if fitted != upper and _kept_weight(fitted) < 4:
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
    Blitz would draw the overflow straight over the panel edge.
    """
    # Heroes render mixed-case even on themes whose chrome uppercases the
    # LABELS (retro's text-transform sits on .t-label only) — measuring
    # them uppercased costs 9-14% of the size for nothing.
    metrics = replace(metrics_for(ctx.theme), uppercase=False)
    if not text:
        return HeroFit(min_px, (text,))

    def per_px(value: str) -> float:
        return metrics.width(value, 1.0, _HERO_WEIGHT, tracking)

    def fit_parts(parts: list[str], reserve_em: float = 0.0) -> float:
        widest = max(per_px(part) for part in parts) + reserve_em
        return min(
            max_px,
            avail_w / max(widest, 1e-6),
            avail_h / (len(parts) * (WRAP_LINE if len(parts) > 1 else HERO_LINE)),
        )

    reserve = suffix_width_em(suffix, ctx, scale=suffix_scale)

    if lines:
        return HeroFit(max(min_px, fit_parts(lines, reserve)), tuple(lines))

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
    fitted: list[str] = []
    for i, line in enumerate(layout):
        budget = avail_w - (reserve * px if i == len(layout) - 1 else 0.0)
        cut = line
        if metrics.width(line, px, _HERO_WEIGHT, tracking) > budget + _FIT_EPS:
            cut = metrics.truncate(
                line, px, budget, _HERO_WEIGHT, tracking=tracking, style="end", min_chars=2
            )
        fitted.append(cut)
    return HeroFit(px, tuple(fitted))


def suffix_width_em(suffix: str, ctx: CellContext, *, scale: float = SUFFIX_SCALE) -> float:
    """Width a hero suffix adds, in hero-em (0 when there is none)."""
    if not suffix:
        return 0.0
    # Suffixes ride the hero's band and render mixed-case (see fit_hero).
    metrics = replace(metrics_for(ctx.theme), uppercase=False)
    gap = _SUFFIX_GAP_WORD if suffix[0].isalnum() else _SUFFIX_GAP_TIGHT
    return metrics.width(suffix, 1.0, "bold") * scale + gap


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
    # -0.02em on .t-hero, which computes against the CLAMP size (up to
    # 124px → -2.5px) and inherits as that pixel value — at a fitted
    # 20px it swallows the space glyphs entirely. Restating it on the
    # fitted wrapper recomputes it against the real size.
    spacing = tracking if tracking is not None else HERO_TRACKING_EM
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
