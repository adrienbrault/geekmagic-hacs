"""Python-side mirrors of the cell document's geometry and neutrals.

Widgets that lay themselves out in Python (because Blitz will not clip
or ellipsize text for them) need to know two things the CSS knows and
they otherwise only guess at:

**How much room a cell actually has.** ``.cell`` is not the cell. Themes
paint chrome on ``.root`` — ``light`` adds 5px of padding plus a 1px
border, ``candy`` 5px plus 2px — and ``.cell``'s percentage padding then
resolves against what is left. Budgeting against the raw cell size
overstates the usable width by ~10px on every chrome theme, which is
exactly enough for a right-aligned pill to collide with the name beside
it. :func:`cell_box` does the arithmetic properly.

**What a translucent neutral resolves to.** Cell documents rasterize
onto transparency and the layout composites them, so a translucent fill
only lands at its stated strength if that hand-off is alpha-correct.
Today it is not: ``blitz_py.render_rgba`` returns *premultiplied* RGBA
which ``htmldoc.render_document`` wraps as straight alpha, so
``Image.paste`` applies the alpha a second time and a 16% fill lands at
2.6% — invisible on any theme whose chrome leaves ``.root`` transparent
(watchos, minimal, retro). Themes that paint an opaque ``.root`` are
unaffected, because Blitz composites those internally where the maths is
right. :func:`tint_css` and :func:`hairline_css` flatten the blend here
instead, so the widget emits the colour the translucent version was
meant to produce and renders identically before and after that pipeline
bug is fixed.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..htmldoc import css_rgb

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .theme import Color, Theme

# Kit parity: --hairline is the text colour at 10%.
HAIRLINE_ALPHA = 0.10

_FALLBACK_BG: tuple[int, int, int] = (0, 0, 0)
_FALLBACK_INK: tuple[int, int, int] = (235, 235, 235)

# Themes declare .root chrome as a single shorthand each; pull the px off
# the first rule rather than guessing from the surface_chrome flag, which
# minimal and retro leave False while still padding .root.
_ROOT_RULE = re.compile(r"\.root\s*\{(.*?)\}", re.DOTALL)
_PADDING_PX = re.compile(r"padding:\s*([\d.]+)px")
_BORDER_PX = re.compile(r"border:\s*([\d.]+)px")


def chrome_inset(theme: Theme | None) -> float:
    """Pixels the theme's ``.root`` chrome eats on each side of a cell."""
    css = getattr(theme, "chrome_css", "") or ""
    rule = _ROOT_RULE.search(css)
    if rule is None:
        return 0.0
    body = rule.group(1)
    padding = _PADDING_PX.search(body)
    border = _BORDER_PX.search(body)
    return (float(padding.group(1)) if padding else 0.0) + (
        float(border.group(1)) if border else 0.0
    )


def cell_inner(ctx: CellContext) -> tuple[float, float]:
    """The cell minus the theme's ``.root`` chrome."""
    inset = chrome_inset(ctx.theme)
    return max(1.0, ctx.width - 2 * inset), max(1.0, ctx.height - 2 * inset)


def cell_box(ctx: CellContext, pad_x: float = 0.03, pad_y: float = 0.03) -> tuple[float, float]:
    """Content box inside a ``.cell`` using *percentage* padding.

    ``pad_x``/``pad_y`` are the fractions in the fragment's ``padding``
    (the kit default is 4%). CSS resolves percentage padding against the
    containing block's *width* on every side — hence the width term in
    the vertical result, which is also why percentages are a poor choice
    for a short, wide cell: 5% of a 228px width is 11px of padding at
    each end of a 74px-tall slot. Prefer :func:`cell_box_px` there.
    """
    inner_w, inner_h = cell_inner(ctx)
    return inner_w * (1 - 2 * pad_x), inner_h - 2 * pad_y * inner_w


def cell_box_px(ctx: CellContext, pad_x: float, pad_y: float) -> tuple[float, float]:
    """Content box inside a ``.cell`` using absolute px padding."""
    inner_w, inner_h = cell_inner(ctx)
    return max(1.0, inner_w - 2 * pad_x), max(1.0, inner_h - 2 * pad_y)


def cell_padding(ctx: CellContext) -> tuple[float, float]:
    """Padding (x, y) in px that keeps a ~5% inset on *both* axes."""
    inner_w, inner_h = cell_inner(ctx)
    return (
        min(max(inner_w * 0.055, 4.0), 16.0),
        min(max(inner_h * 0.055, 3.0), 14.0),
    )


def label_px(ctx: CellContext) -> float:
    """The size the kit's ``.t-label`` resolves to for this cell.

    Mirrors ``clamp(12px, min(12vmin, 9vw), 18px)``; viewport units
    answer to the whole cell, chrome included.
    """
    return max(12.0, min(0.12 * min(ctx.width, ctx.height), 0.09 * ctx.width, 18.0))


def blend(color: Color, background: Color, alpha: float) -> tuple[int, int, int]:
    """``color`` at ``alpha`` over ``background``, as opaque RGB."""
    a = max(0.0, min(1.0, alpha))
    return (
        round(color[0] * a + background[0] * (1.0 - a)),
        round(color[1] * a + background[1] * (1.0 - a)),
        round(color[2] * a + background[2] * (1.0 - a)),
    )


def tint_css(color: Color, theme: Theme | None, alpha: float) -> str:
    """CSS colour for ``color`` shown at ``alpha`` on the theme's canvas."""
    background = getattr(theme, "background", _FALLBACK_BG) if theme else _FALLBACK_BG
    return css_rgb(blend(color, background, alpha))


def hairline_css(theme: Theme | None, alpha: float = HAIRLINE_ALPHA) -> str:
    """CSS colour for a 1px separator — the kit's ``--hairline``, resolved."""
    ink = getattr(theme, "text_primary", _FALLBACK_INK) if theme else _FALLBACK_INK
    return tint_css(ink, theme, alpha)
