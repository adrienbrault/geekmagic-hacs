"""The Python mirrors of the cell document must track the CSS they mirror.

``_cellkit`` restates four things the stylesheet already says, because a
widget has to budget space before the engine lays anything out: what the
kit's ``clamp()`` type resolves to (``label_px`` / ``chip_px``), how much
``.cell`` spends on padding (``CELL_PADDING``), the height a chip strip
costs (``chip_band_px``), and at which sizes the ``.hide-*`` media rules
fire (``HIDE_SHORT_H`` / ``HIDE_SMALL``, read through ``caption_visible``
/ ``small_visible``). That is a copy of CSS living in Python — the kind
of duplication that rots silently: edit the stylesheet, and the fitters
keep budgeting for the old geometry until something overflows on a real
panel.

So the test does not restate the numbers. It parses them out of the
shipped CSS — the fluid kit from ``htmldoc.FLUID_KIT_CSS``, the card
primitives from ``_card.CARD_CSS`` — evaluates each declaration the way
a browser would over a grid of cell sizes, and compares. The CSS stays
the source of truth; the mirror only has to agree with it.

Two mirrors cannot be proved equal to their CSS, only bounded by it, and
those bounds are asserted with the derivation spelled out:

* ``chip_band_px``'s ``1.9`` factor covers a chip's own box — ``1em`` of
  line box (``line-height: 1``) plus its vertical ``padding`` — plus a
  little slack for the strip around it. The CSS gives the first two; the
  test pins the factor between them and a documented ceiling.
* ``.hide-narrow`` has no Python mirror at all (nothing budgets on it),
  so the test only pins its breakpoint to ``.hide-short``'s — the day
  they diverge, the height-only mirror stops being the whole story.
"""

from __future__ import annotations

import re

import pytest

from custom_components.geekmagic.htmldoc import FLUID_KIT_CSS, CellContext
from custom_components.geekmagic.widgets._card import CARD_CSS
from custom_components.geekmagic.widgets._cellkit import (
    CELL_PADDING,
    HIDE_SHORT_H,
    HIDE_SMALL,
    caption_visible,
    chip_band_px,
    chip_px,
    label_px,
    small_visible,
)
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

# Cell sizes to check: from a 3x3 grid cell up to fullscreen, on both
# axes independently so the wide/short and narrow/tall corners (where
# the vmin and vw terms swap places) are covered too.
_SIZES = range(40, 241, 20)


def _rule_body(css: str, selector: str) -> str:
    """The declarations of the first rule matching ``selector``."""
    match = re.search(rf"{re.escape(selector)}\s*\{{(.*?)\}}", css, re.DOTALL)
    assert match is not None, f"{selector} rule not found"
    return match.group(1)


def _font_size_clamp(css: str, selector: str) -> tuple[float, str, float]:
    """``(min_px, preferred, max_px)`` from the rule's ``font-size: clamp(...)``."""
    body = _rule_body(css, selector)
    match = re.search(r"font-size:\s*clamp\(\s*([\d.]+)px\s*,\s*(.+?)\s*,\s*([\d.]+)px\s*\)", body)
    assert match is not None, f"{selector} has no font-size: clamp()"
    return float(match.group(1)), match.group(2), float(match.group(3))


def _eval_preferred(expr: str, width: float, height: float) -> float:
    """Evaluate the clamp's preferred term: ``<n>vmin``/``<n>vw``, or ``min(...)``."""
    inner = re.fullmatch(r"min\(\s*(.+?)\s*\)", expr)
    if inner:
        return min(
            _eval_preferred(term.strip(), width, height) for term in inner.group(1).split(",")
        )
    match = re.fullmatch(r"([\d.]+)(vmin|vw|vh)", expr)
    assert match is not None, f"unhandled clamp term: {expr!r}"
    basis = {"vmin": min(width, height), "vw": width, "vh": height}[match.group(2)]
    return float(match.group(1)) * basis / 100.0


def _css_size(css: str, selector: str, width: float, height: float) -> float:
    """What the browser resolves ``selector``'s font-size to at this cell size."""
    low, preferred, high = _font_size_clamp(css, selector)
    return max(low, min(_eval_preferred(preferred, width, height), high))


def _padding(css: str, selector: str) -> list[str]:
    """The rule's ``padding`` shorthand, as its space-separated terms."""
    match = re.search(r"padding:\s*([^;}]+)", _rule_body(css, selector))
    assert match is not None, f"{selector} declares no padding"
    return match.group(1).split()


def _media_blocks(css: str) -> list[tuple[str, str]]:
    """``(conditions, body)`` for every ``@media`` block (one nesting level)."""
    return re.findall(r"@media\s*([^{]+)\{((?:[^{}]|\{[^{}]*\})*)\}", css)


def _hide_breakpoints(css: str, hide_class: str) -> set[tuple[str, float]]:
    """``(feature, px)`` conditions under which the stylesheet hides a class."""
    found: set[tuple[str, float]] = set()
    for conditions, body in _media_blocks(css):
        if not re.search(rf"\.{re.escape(hide_class)}\b", body) or "display: none" not in body:
            continue
        for feature, px in re.findall(
            r"\(\s*(max-width|max-height)\s*:\s*([\d.]+)px\s*\)", conditions
        ):
            found.add((feature, float(px)))
    return found


def _css_hidden(css: str, hide_class: str, width: float, height: float) -> bool:
    """Whether a media rule hides ``hide_class`` at this cell size."""
    axis = {"max-width": width, "max-height": height}
    return any(axis[feature] <= px for feature, px in _hide_breakpoints(css, hide_class))


@pytest.mark.parametrize("width", _SIZES)
@pytest.mark.parametrize("height", _SIZES)
class TestKitTypeMirrors:
    """Python mirrors agree with the CSS at every cell size."""

    def test_label_px_mirrors_t_label(self, width: int, height: int):
        ctx = CellContext(width=width, height=height, theme=DEFAULT_THEME)
        assert label_px(ctx) == pytest.approx(_css_size(FLUID_KIT_CSS, ".t-label", width, height))

    def test_chip_px_mirrors_chip(self, width: int, height: int):
        ctx = CellContext(width=width, height=height, theme=DEFAULT_THEME)
        assert chip_px(ctx) == pytest.approx(_css_size(CARD_CSS, ".chip", width, height))


@pytest.mark.parametrize("width", _SIZES)
@pytest.mark.parametrize("height", _SIZES)
class TestKitBreakpointMirrors:
    """``caption_visible`` / ``small_visible`` agree with the media rules."""

    def test_caption_visible_mirrors_hide_short(self, width: int, height: int):
        ctx = CellContext(width=width, height=height, theme=DEFAULT_THEME)
        assert caption_visible(ctx) is not _css_hidden(FLUID_KIT_CSS, "hide-short", width, height)

    def test_small_visible_mirrors_hide_small(self, width: int, height: int):
        ctx = CellContext(width=width, height=height, theme=DEFAULT_THEME)
        assert small_visible(ctx) is not _css_hidden(FLUID_KIT_CSS, "hide-small", width, height)

    def test_card_css_re_asserts_the_same_breakpoints(self, width: int, height: int):
        """``CARD_CSS`` re-hides ``.caption-row``/``.chips`` at the kit's sizes.

        Those rules exist only because the card's ``display: flex``
        declarations are appended after the kit and would otherwise win.
        They are a second copy of the same two breakpoints, so they are
        checked against the first.
        """
        for hide_class in ("hide-short", "hide-small"):
            assert _css_hidden(CARD_CSS, hide_class, width, height) is _css_hidden(
                FLUID_KIT_CSS, hide_class, width, height
            )


def test_cell_padding_mirrors_the_kit_rule():
    """``CELL_PADDING`` is ``.cell``'s percentage padding, as a fraction."""
    terms = _padding(FLUID_KIT_CSS, ".cell")
    assert len(terms) == 1, f".cell padding is no longer uniform: {terms}"
    percent = re.fullmatch(r"([\d.]+)%", terms[0])
    assert percent is not None, f".cell padding is not a percentage: {terms[0]!r}"
    assert pytest.approx(float(percent.group(1)) / 100.0) == CELL_PADDING


def test_chip_band_px_covers_the_pill_the_css_draws():
    """The chip strip's height factor is bounded by the CSS it budgets for.

    A chip is ``line-height: 1`` — a 1em line box — plus its own vertical
    padding on each side, so the pill itself is ``1 + 2 * pad_v`` ems.
    That is the floor the factor may not go under, or a strip of chips
    overflows the band a widget reserved for it. The rest is slack for
    the strip around the pill (the flex row's own rounding, and the
    border-radius' optical margin), and is capped here so the factor
    cannot quietly grow into a wasted band either.
    """
    vertical = re.fullmatch(r"([\d.]+)em", _padding(CARD_CSS, ".chip")[0])
    assert vertical is not None, ".chip's vertical padding is no longer in em"
    assert "line-height: 1;" in _rule_body(CARD_CSS, ".chip")
    pill_em = 1.0 + 2 * float(vertical.group(1))

    ctx = CellContext(width=160, height=160, theme=DEFAULT_THEME)
    factor = chip_band_px(ctx) / chip_px(ctx)
    assert pill_em <= factor <= pill_em + 0.1, (
        f"chip_band_px spends {factor:.2f}em on a pill the CSS draws {pill_em:.2f}em tall"
    )


def test_hide_narrow_shares_hide_shorts_breakpoint():
    """No Python mirrors ``.hide-narrow`` — it only has to match its twin.

    ``caption_visible`` gates on HEIGHT alone, which is the whole truth
    only while the narrow breakpoint sits at the same pixel as the short
    one. If the kit ever moves one of them, a width-axis mirror has to
    exist.
    """
    assert _hide_breakpoints(FLUID_KIT_CSS, "hide-narrow") == {("max-width", HIDE_SHORT_H - 1)}


def test_parsers_read_the_shipped_declarations():
    """The parsers must actually find the rules — not vacuously pass."""
    assert _font_size_clamp(FLUID_KIT_CSS, ".t-label") == (12.0, "min(12vmin, 9vw)", 18.0)
    assert _font_size_clamp(CARD_CSS, ".chip") == (10.0, "11vmin", 18.0)
    assert _padding(FLUID_KIT_CSS, ".cell") == ["3%"]
    assert _padding(CARD_CSS, ".chip") == ["0.42em", "0.85em"]
    # A ``max-`` breakpoint is the last size at which the band is hidden,
    # so the Python threshold — the first size at which it survives — is
    # one pixel above it.
    assert _hide_breakpoints(FLUID_KIT_CSS, "hide-short") == {("max-height", HIDE_SHORT_H - 1)}
    assert _hide_breakpoints(FLUID_KIT_CSS, "hide-small") == {
        ("max-height", HIDE_SMALL - 1),
        ("max-width", HIDE_SMALL - 1),
    }
