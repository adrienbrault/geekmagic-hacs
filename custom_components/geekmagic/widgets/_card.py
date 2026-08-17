"""HTML card primitives — the watchOS three-band pattern as markup.

``card_html`` is the HTML successor of the old ``DataCard`` component:
caption band, hero band, supporting chip strip. Band visibility is
CSS-driven via the fluid kit (captions drop in short cells, chips drop
in small cells), so one fragment adapts to every cell size.

Which bands a cell keeps is not this module's decision: it comes in as a
:class:`._bands.BandPlan`, the one seam that answers that question for
every widget family. Passing the plan instead of three hand-plumbed
class strings is what keeps the caller's markup and its height budget
answering to the same rule.

Widgets emit semantic classes; themes restyle them via ``chrome_css``.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from ..htmldoc import mdi_span

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ._bands import BandPlan

# Styles for card structure — part of every cell document (appended to
# the fluid kit by htmldoc so themes can override).
#
# Chips are soft pills filled with --chip-bg (a text-color-derived
# neutral, so they work on dark and light themes alike).
CARD_CSS = """
.chips { display: flex; gap: 5px; align-items: center; justify-content: center; }
.chip { display: flex; gap: 0.35em; align-items: center; line-height: 1;
        font-size: clamp(10px, 11vmin, 18px); font-weight: 600;
        color: var(--text-secondary);
        background: var(--chip-bg); border-radius: 999px;
        padding: 0.42em 0.85em; }
.card-icon { line-height: 1; }
.caption-row { display: flex; gap: 0.45em; align-items: center; justify-content: center; }
/* The display:flex rules above are appended after the fluid kit, so they
   would override its single-class hide-* media rules; re-assert hiding
   with higher specificity. */
@media (max-height: 99px) {
  .caption-row.hide-short, .chips.hide-short { display: none; }
}
@media (max-height: 129px), (max-width: 129px) {
  .chips.hide-small, .caption-row.hide-small { display: none; }
}
"""


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
    from ._fit import cell_box, fit_caption_sized  # noqa: PLC0415 (lazy)

    fitted, px = fit_caption_sized(text, ctx, cell_box(ctx)[0], reserve_em=reserve_em)
    # Always report the fitted size: it may sit ABOVE the kit clamp
    # (wide cell, short word) as well as below it.
    return fitted, px


def chip_html(text: str, icon: str | None = None, color: str | None = None) -> str:
    """A small icon+text supporting metric (chip strip element)."""
    style = f' style="color: {color}"' if color else ""
    icon_html = mdi_span(icon, "icon") if icon else ""
    return f'<span class="chip"{style}>{icon_html}<span>{escape(text)}</span></span>'


def card_html(
    *,
    caption: str | None = None,
    icon: str | None = None,
    icon_color: str | None = None,
    icon_role: str = "chip",
    icon_size: float | None = None,
    hero: str = "",
    hero_color: str | None = None,
    chips: list[str] | None = None,
    extra: str = "",
    hero_is_html: bool = False,
    plan: BandPlan | None = None,
    ctx: CellContext | None = None,
) -> str:
    """Build the three-band card fragment.

    Args:
        caption: Caps label band (auto-hidden in short cells).
        icon: MDI icon name.
        icon_color: CSS color for the icon.
        icon_role: "feature" renders the icon as its own band above the
            caption; "chip" keeps it inline beside the caption.
        icon_size: Explicit glyph size in px for a feature icon
            (overrides the kit's ``i-md`` clamp).
        hero: Primary value text.
        hero_color: CSS color for the hero (default: theme text).
        chips: Pre-rendered chip fragments (see :func:`chip_html`).
        extra: Raw HTML appended after the chip strip (indicators).
        hero_is_html: Set True when ``hero`` is already markup.
        plan: The caller's :func:`._bands.plan_bands` result — it decides
            which hide class each optional band carries, so a band the
            widget deliberately kept below a kit breakpoint is not
            re-hidden by the media rule. Without one the bands take the
            kit's own breakpoints.
        ctx: When provided, captions are truncated in Python with real
            font metrics (Blitz has no ellipsis and clips mid-glyph).
    """
    caption_hide = "hide-short" if plan is None else plan.caption_hide
    icon_hide = "hide-short" if plan is None else plan.icon_hide
    chips_hide = "hide-small" if plan is None else plan.chips_hide

    bands: list[str] = []

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
        reserve = 1.5 if (icon and icon_role == "chip") else 0.0
        text, fitted_px = caption_fit(ctx, caption.upper(), reserve_em=reserve)
        if text or (icon and icon_role == "chip"):
            caption_inner = escape(text)
            if icon and icon_role == "chip":
                caption_inner = mdi_span(icon, "icon i-sm", icon_style) + caption_inner
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

    return f'<div class="cell">{"".join(bands)}</div>'
