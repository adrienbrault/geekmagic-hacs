"""Every theme's declared facts must match its stylesheet.

``Theme`` declares three things Python-side layout needs to know about
CSS it does not otherwise read: how much room ``.root``'s chrome takes
(``chrome_inset`` / ``chrome_inset_y``), whether the chrome uppercases
the kit's text classes (``uppercase_labels``), and which family the cell
renders in (``rounded_font``). Widgets used to recover all three by
sniffing ``chrome_css``/``font_stack`` at render time — an adapter that
quietly went wrong the day a theme wrote the same rule differently.

The sniffing now lives HERE, and only here, as a real reading of the
``.root`` rule: the ``padding`` shorthand in CSS order, the ``border``
shorthand and its per-side longhands, and the ``calc(100% - Npx)``
shrink that buys ``brutal`` room for its offset shadow. What a fitter
spends is an axis BUDGET — twice the inset — so the declared value for
an asymmetric rule is that axis' average of its two sides, and the
shrink adds half of its N per side.

A theme that edits its chrome without updating its facts fails this test
instead of shifting geometry.
"""

from __future__ import annotations

import re

import pytest

from custom_components.geekmagic.widgets._cellkit import chrome_insets
from custom_components.geekmagic.widgets.theme import THEMES, Theme

_ROOT_RULE = re.compile(r"\.root\s*\{(.*?)\}", re.DOTALL)
_LENGTH_PX = re.compile(r"(-?[\d.]+)px")
_CALC_SHRINK = re.compile(r"calc\(\s*100%\s*-\s*([\d.]+)px\s*\)")

# CSS shorthand order, and which of a declaration's values each side
# takes for a 1-, 2-, 3- and 4-value shorthand.
_SIDES = ("top", "right", "bottom", "left")
_SHORTHAND_INDEX = {
    1: (0, 0, 0, 0),
    2: (0, 1, 0, 1),
    3: (0, 1, 2, 1),
    4: (0, 1, 2, 3),
}


def _first_px(value: str) -> float:
    """The first px length in a declaration's value, or 0."""
    found = _LENGTH_PX.search(value)
    return float(found.group(1)) if found else 0.0


def _apply_shorthand(sides: dict[str, float], value: str) -> None:
    """Spread a 1-4 value px shorthand over the four sides."""
    lengths = [float(n) for n in _LENGTH_PX.findall(value)]
    if not lengths or len(lengths) > 4:
        return
    for side, index in zip(_SIDES, _SHORTHAND_INDEX[len(lengths)], strict=True):
        sides[side] = lengths[index]


def _parsed_chrome_insets(theme: Theme) -> tuple[float, float]:
    """Inset ``(x, y)`` per side, read out of the theme's ``.root`` rule.

    Declarations are applied in source order so a longhand
    (``border-top``) overrides the shorthand it follows, the way a
    browser resolves them.
    """
    rule = _ROOT_RULE.search(theme.chrome_css or "")
    if rule is None:
        return 0.0, 0.0
    body = rule.group(1)

    padding = dict.fromkeys(_SIDES, 0.0)
    border = dict.fromkeys(_SIDES, 0.0)
    shrink = {"x": 0.0, "y": 0.0}

    for declaration in body.split(";"):
        prop, _, value = declaration.partition(":")
        prop, value = prop.strip().lower(), value.strip()
        if not value:
            continue
        if prop == "padding":
            _apply_shorthand(padding, value)
        elif prop.startswith("padding-") and prop[8:] in _SIDES:
            padding[prop[8:]] = _first_px(value)
        elif prop == "border":
            border.update(dict.fromkeys(_SIDES, _first_px(value)))
        elif prop.startswith("border-") and prop[7:] in _SIDES:
            border[prop[7:]] = _first_px(value)
        elif prop in ("width", "height"):
            # ``calc(100% - Npx)`` hands N px of the axis back to the
            # cell — brutal's room for its offset box-shadow.
            found = _CALC_SHRINK.search(value)
            if found:
                shrink["x" if prop == "width" else "y"] = float(found.group(1))

    side = {name: padding[name] + border[name] for name in _SIDES}
    return (
        (side["left"] + side["right"]) / 2 + shrink["x"] / 2,
        (side["top"] + side["bottom"]) / 2 + shrink["y"] / 2,
    )


@pytest.mark.parametrize("theme", THEMES.values(), ids=list(THEMES))
class TestDeclaredThemeFacts:
    """Declared facts agree with the CSS they describe."""

    def test_chrome_insets_match_root_rule(self, theme: Theme):
        parsed_x, parsed_y = _parsed_chrome_insets(theme)
        declared_x, declared_y = chrome_insets(theme)
        assert declared_x == pytest.approx(parsed_x)
        assert declared_y == pytest.approx(parsed_y)

    def test_uppercase_labels_matches_chrome(self, theme: Theme):
        sniffed = "text-transform: uppercase" in (theme.chrome_css or "").lower()
        assert theme.uppercase_labels is sniffed

    def test_rounded_font_matches_font_stack(self, theme: Theme):
        head = (theme.font_stack or "").lower().split(",")[0]
        assert theme.rounded_font is ("dejavu" not in head)


def test_every_theme_declares_facts():
    """Guards the parametrization against an empty/partial theme table."""
    assert len(THEMES) == 15


def test_symmetric_themes_leave_the_vertical_inset_unset():
    """Only a theme whose ``.root`` really is asymmetric declares y.

    ``chrome_inset_y=None`` means "same as x", so a symmetric theme that
    spelled it out anyway would be duplicating a fact rather than
    declaring one — and would drift the day its padding changes.
    """
    asymmetric = {name for name, theme in THEMES.items() if theme.chrome_inset_y is not None}
    assert asymmetric == {"minimal", "ink", "brutal"}


def test_the_asymmetric_themes_land_where_their_css_says():
    """The three hand-computed pairs, spelled out.

    minimal: ``padding: 5px 3px 3px`` + 1px ``border-top`` → 3/3 across,
    6/3 down. ink: the same padding + 2px top and 1px bottom borders →
    3/3 across, 7/4 down. brutal: 2px padding + 2px border every side,
    plus 3px per axis handed back by ``calc(100% - 3px)``.
    """
    assert chrome_insets(THEMES["minimal"]) == (3.0, 4.5)
    assert chrome_insets(THEMES["ink"]) == (3.0, 5.5)
    assert chrome_insets(THEMES["brutal"]) == (5.5, 5.5)
