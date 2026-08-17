"""The Python type-size mirrors must track the CSS they mirror.

``_cellkit.label_px`` / ``chip_px`` predict what the fluid kit's
``clamp()`` declarations resolve to, because a widget has to budget
space before the engine lays anything out. That makes them a copy of
CSS living in Python — the kind of duplication that rots silently: edit
the stylesheet, and the fitters keep budgeting for the old size until
something overflows on a real panel.

So the test does not restate the numbers. It parses the ``clamp()`` out
of the shipped CSS — ``.t-label`` from ``htmldoc.FLUID_KIT_CSS``,
``.chip`` from ``_card.CARD_CSS`` — evaluates it the way a browser
would over a grid of cell sizes, and compares. The CSS stays the source
of truth; the mirror only has to agree with it.
"""

from __future__ import annotations

import re

import pytest

from custom_components.geekmagic.htmldoc import FLUID_KIT_CSS, CellContext
from custom_components.geekmagic.widgets._card import CARD_CSS
from custom_components.geekmagic.widgets._cellkit import chip_px, label_px
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


def test_clamp_parser_reads_the_shipped_declarations():
    """The parser must actually find both rules — not vacuously pass."""
    assert _font_size_clamp(FLUID_KIT_CSS, ".t-label") == (12.0, "min(12vmin, 9vw)", 18.0)
    assert _font_size_clamp(CARD_CSS, ".chip") == (10.0, "11vmin", 18.0)
