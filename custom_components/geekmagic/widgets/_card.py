"""HTML card primitives — the watchOS three-band pattern as markup.

``card_html`` is the HTML successor of the old ``DataCard`` component:
caption band, hero band, supporting chip strip. Band visibility is
CSS-driven via the fluid kit (captions drop in short cells, chips drop
in small cells), so one fragment adapts to every cell size.

Widgets emit semantic classes; themes restyle them via ``chrome_css``.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING

from ..htmldoc import mdi_span

if TYPE_CHECKING:
    from ..htmldoc import CellContext

# Styles for card structure — part of every cell document (appended to
# the fluid kit by htmldoc so themes can override).
#
# Chips are soft pills filled with --chip-bg (a text-color-derived
# neutral, so they work on dark and light themes alike).
CARD_CSS = """
.chips { display: flex; gap: 5px; align-items: center; justify-content: center; }
.chip { display: flex; gap: 0.35em; align-items: center; line-height: 1;
        font-size: clamp(11px, 11vmin, 18px); font-weight: 600;
        color: var(--text-secondary);
        background: var(--chip-bg); border-radius: 999px;
        padding: 0.42em 0.85em; }
.card-icon { line-height: 1; }
.caption-row { display: flex; gap: 0.4em; align-items: center; justify-content: center; }
.caption-row .icon { font-size: 1.35em; }
.card-head { display: flex; flex-direction: column; align-items: center; }
.t-date { font-weight: 600; line-height: 1; color: var(--text-secondary);
          white-space: nowrap; letter-spacing: 0.01em; }
/* The display:flex rules above are appended after the fluid kit, so they
   would override its single-class hide-* media rules; re-assert hiding
   with higher specificity. */
@media (max-height: 99px) {
  .caption-row.hide-short, .chips.hide-short, .card-head.hide-short { display: none; }
}
@media (max-height: 129px), (max-width: 129px) {
  .chips.hide-small, .caption-row.hide-small, .card-head.hide-small { display: none; }
}
"""

# Header geometry. The icon is the cell's identifier — a tinted glyph
# reads from a metre away where a 12px word does not — so it is set a
# step larger than the caption it labels. Inline (icon beside caption)
# is the default; narrow cells with height to spare (a 2x3 tile, a
# split column) stack the icon over the caption instead, which gives
# the word the full width. The choice is GEOMETRIC, never per content:
# sibling cells in a grid must all carry the same header shape, or the
# row reads as a mistake.
HEADER_ICON_EM = 1.35
STACK_ICON_EM = 1.55
_ICON_MIN_PX = 13.0
_STACK_MAX_W = 92.0
_STACK_MIN_H = 85.0


def header_stacks(ctx: CellContext) -> bool:
    """True when this cell's header puts the icon above the caption."""
    from ._cardfit import cell_box  # noqa: PLC0415 (lazy)

    box_w, box_h = cell_box(ctx)
    return box_w < _STACK_MAX_W and box_h >= _STACK_MIN_H


@dataclass(frozen=True)
class Header:
    """A fitted identity band: markup plus the height it costs."""

    html: str
    band_px: float
    stacked: bool = False

    def __bool__(self) -> bool:
        return bool(self.html)


def header_html(  # noqa: PLR0911 - one exit per header shape
    ctx: CellContext,
    name: str,
    icon: str | None,
    tint: str | None,
    *,
    width_px: float,
    hide: str = "",
    max_px: float | None = None,
) -> Header:
    """The card header: tinted icon + caps caption, inline or stacked.

    ``width_px`` is the width the band really has; ``hide`` is a kit
    class for bands whose visibility the kit decides ("" when the
    widget decided in Python). ``max_px`` caps the caption size.
    """
    from ._cardfit import CAPTION_MIN_PX, fit_caption_sized, label_px  # noqa: PLC0415 (lazy)

    if not (name or icon):
        return Header("", 0.0)
    cap_top = min(label_px(ctx), max_px) if max_px else label_px(ctx)
    hide_cls = f" {hide}" if hide else ""
    tint_style = f"color: {tint}" if tint else ""

    if not name:
        px = max(_ICON_MIN_PX, cap_top * STACK_ICON_EM)
        glyph = mdi_span(icon or "", "icon", f"{tint_style}; font-size: {px:.1f}px".strip("; "))
        return Header(f'<div class="card-icon{hide_cls}">{glyph}</div>', px * 1.15, True)

    upper = name.upper()
    if icon and not header_stacks(ctx):
        # Inline: the icon rides at 1.35em plus the row gap.
        text, px = fit_caption_sized(upper, ctx, width_px, reserve_em=HEADER_ICON_EM + 0.4)
        px = min(px, cap_top)
        glyph = mdi_span(icon, "icon", tint_style)
        row = (
            f'<div class="t-label caption-row{hide_cls}" style="font-size: {px:.1f}px">'
            f"{glyph}{escape(text)}</div>"
        )
        return Header(row, px * HEADER_ICON_EM * 1.2)
    if icon:
        # Stacked: the caption gets the whole width, the icon its own line.
        text, px = fit_caption_sized(upper, ctx, width_px)
        px = min(px, cap_top)
        icon_px = max(_ICON_MIN_PX, px * STACK_ICON_EM)
        gap = max(2.0, px * 0.25)
        glyph = mdi_span(icon, "icon", f"{tint_style}; font-size: {icon_px:.1f}px".strip("; "))
        label = f'<div class="t-label" style="font-size: {px:.1f}px">{escape(text)}</div>'
        if not text:
            return Header(f'<div class="card-icon{hide_cls}">{glyph}</div>', icon_px * 1.15, True)
        return Header(
            f'<div class="card-head{hide_cls}" style="gap: {gap:.1f}px">'
            f'<div class="card-icon">{glyph}</div>{label}</div>',
            icon_px * 1.05 + gap + px * 1.1,
            True,
        )

    text, px = fit_caption_sized(upper, ctx, width_px)
    if not text:
        return Header("", 0.0)
    px = max(CAPTION_MIN_PX, min(px, cap_top))
    return Header(
        f'<div class="t-label caption-row{hide_cls}" style="font-size: {px:.1f}px">'
        f"{escape(text)}</div>",
        px * 1.25,
    )


def caption_fit(
    ctx: CellContext | None, text: str, *, reserve_em: float = 0.0
) -> tuple[str, float | None]:
    """Fit a caps caption to the width it actually has.

    Measures with the embedded font metrics (theme-aware family,
    tracking, and case) rather than an average glyph estimate, shrinking
    to keep the whole word before truncating. Returns ``(text, px)``
    where ``px`` is ``None`` when the kit's ``.t-label`` size applies
    unchanged (or when no context is available).
    """
    if ctx is None:
        return text, None
    from ._cardfit import cell_box, fit_caption_sized  # noqa: PLC0415 (lazy)

    fitted, px = fit_caption_sized(text, ctx, cell_box(ctx)[0], reserve_em=reserve_em)
    # Always report the fitted size: it may sit ABOVE the kit clamp
    # (wide cell, short word) as well as below it.
    return fitted, px


def label_px_for(ctx: CellContext | None) -> float:
    """The kit's ``.t-label`` size for a cell (12px without a context)."""
    if ctx is None:
        return 12.0
    from ._cardfit import label_px  # noqa: PLC0415 (lazy)

    return label_px(ctx)


def chip_html(text: str, icon: str | None = None, color: str | None = None) -> str:
    """A small icon+text supporting metric (chip strip element)."""
    style = f' style="color: {color}"' if color else ""
    icon_html = mdi_span(icon, "icon") if icon else ""
    return f'<span class="chip"{style}>{icon_html}<span>{escape(text)}</span></span>'


def card_html(
    *,
    caption: str | None = None,
    caption_hide: str = "hide-short",
    icon: str | None = None,
    icon_color: str | None = None,
    icon_hide: str = "hide-short",
    icon_role: str = "chip",
    icon_size: float | None = None,
    hero: str = "",
    hero_color: str | None = None,
    chips: list[str] | None = None,
    chips_hide: str = "hide-small",
    extra: str = "",
    hero_is_html: bool = False,
    ctx: CellContext | None = None,
    caption_reserve_em: float | None = None,
    header: Header | None = None,
    stack_gap_px: float | None = None,
) -> str:
    """Build the three-band card fragment.

    Args:
        header: A pre-fitted :class:`Header` (see :func:`header_html`)
            that replaces the ``icon``/``caption`` bands.
        stack_gap_px: When the card has only a header and a hero, centre
            them as one block with this gap instead of spreading them
            to the cell's ends with ``space-evenly``.
        caption: Caps label band (auto-hidden in short cells).
        caption_hide: Which kit breakpoint sheds the caption row
            ("hide-short" by default, or "" to always keep it — a widget
            that shrinks its caption for short cells manages visibility
            itself).
        icon: MDI icon name.
        icon_color: CSS color for the icon.
        icon_hide: Which kit breakpoint sheds a feature icon band
            ("hide-short" by default, or "" when the widget decided in
            Python that a short cell keeps its stacked icon — the kit
            must not re-hide it).
        icon_role: "feature" renders the icon as its own band above the
            caption; "chip" keeps it inline beside the caption.
        icon_size: Explicit glyph size in px for the icon (overrides the
            kit's ``i-md`` / ``i-sm`` clamp for either role).
        caption_reserve_em: Width beside the caption to reserve for an
            inline icon, in caption ems (derived from ``icon_size`` when
            omitted).
        hero: Primary value text.
        hero_color: CSS color for the hero (default: theme text).
        chips: Pre-rendered chip fragments (see :func:`chip_html`).
        chips_hide: Which kit breakpoint sheds the chip strip
            ("hide-small", "hide-short", or "" to always keep it).
        extra: Raw HTML appended after the chip strip (indicators).
        hero_is_html: Set True when ``hero`` is already markup.
        ctx: When provided, captions are truncated in Python with real
            font metrics (Blitz has no ellipsis and clips mid-glyph).
    """
    bands: list[str] = []

    if header is not None:
        icon, caption = None, None
        if header.html:
            bands.append(header.html)

    icon_style = f"color: {icon_color}" if icon_color else ""
    if icon and icon_role == "feature":
        glyph_style = icon_style
        glyph_classes = "icon i-md"
        if icon_size is not None:
            glyph_style = f"{icon_style}; font-size: {icon_size:.0f}px".strip("; ")
            glyph_classes = "icon"
        hide = f" {icon_hide}" if icon_hide else ""
        bands.append(
            f'<div class="card-icon{hide}">{mdi_span(icon, glyph_classes, glyph_style)}</div>'
        )

    if caption:
        inline_icon = bool(icon and icon_role == "chip")
        # An inline header icon is set ~1.3 caption-ems tall plus the
        # row's 0.45em gap; reserve that width so the caption fit is
        # measured against what it really has.
        reserve = 0.0
        if inline_icon:
            reserve = (
                caption_reserve_em
                if caption_reserve_em is not None
                else (icon_size / label_px_for(ctx) if icon_size and ctx else 1.1) + 0.5
            )
        text, fitted_px = caption_fit(ctx, caption.upper(), reserve_em=reserve)
        if text or inline_icon:
            caption_inner = escape(text)
            if inline_icon:
                glyph_classes = "icon i-sm"
                glyph_style = icon_style
                if icon_size is not None:
                    glyph_classes = "icon"
                    glyph_style = f"{icon_style}; font-size: {icon_size:.1f}px".strip("; ")
                caption_inner = mdi_span(icon, glyph_classes, glyph_style) + caption_inner
            hide = f" {caption_hide}" if caption_hide else ""
            size = f' style="font-size: {fitted_px:.1f}px"' if fitted_px else ""
            bands.append(f'<div class="t-label caption-row{hide}"{size}>{caption_inner}</div>')

    hero_html = hero if hero_is_html else escape(hero)
    hero_style = f' style="color: {hero_color}"' if hero_color else ""
    bands.append(f'<div class="t-hero"{hero_style}>{hero_html}</div>')

    if chips:
        hide = f" {chips_hide}" if chips_hide else ""
        bands.append(f'<div class="chips{hide}">{"".join(chips)}</div>')

    if extra:
        bands.append(extra)

    style = ""
    if stack_gap_px is not None and len(bands) == 2:
        style = f' style="justify-content: center; gap: {stack_gap_px:.1f}px"'
    return f'<div class="cell"{style}>{"".join(bands)}</div>'
