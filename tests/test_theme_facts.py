"""Every theme's declared facts must match its stylesheet.

``Theme`` declares three things Python-side layout needs to know about
CSS it does not otherwise read: how much room ``.root``'s chrome takes
(``chrome_inset``), whether the chrome uppercases the kit's text classes
(``uppercase_labels``), and which family the cell renders in
(``rounded_font``). Widgets used to recover all three by sniffing
``chrome_css``/``font_stack`` at render time — an adapter that quietly
went wrong the day a theme wrote the same rule differently.

The sniffing now lives HERE, and only here: these are the exact
expressions the production code used, kept as the oracle the declared
values are checked against. A theme that edits its chrome without
updating its facts fails this test instead of shifting geometry.
"""

from __future__ import annotations

import re

import pytest

from custom_components.geekmagic.widgets.theme import THEMES, Theme

# The parser production code used to run on every cell, verbatim: the
# first ``.root`` rule's ``padding`` shorthand plus its ``border``
# shorthand. Its quirks are part of the contract — a multi-value
# ``padding: 5px 3px 3px`` counts only the first value, and a
# ``border-top`` shorthand counts as no border at all.
_ROOT_RULE = re.compile(r"\.root\s*\{(.*?)\}", re.DOTALL)
_PADDING_PX = re.compile(r"padding:\s*([\d.]+)px")
_BORDER_PX = re.compile(r"border:\s*([\d.]+)px")


def _parsed_chrome_inset(theme: Theme) -> float:
    """Inset recovered from the stylesheet, the pre-declaration way."""
    css = theme.chrome_css or ""
    rule = _ROOT_RULE.search(css)
    if rule is None:
        return 0.0
    body = rule.group(1)
    padding = _PADDING_PX.search(body)
    border = _BORDER_PX.search(body)
    return (float(padding.group(1)) if padding else 0.0) + (
        float(border.group(1)) if border else 0.0
    )


@pytest.mark.parametrize("theme", THEMES.values(), ids=list(THEMES))
class TestDeclaredThemeFacts:
    """Declared facts agree with the CSS they describe."""

    def test_chrome_inset_matches_root_rule(self, theme: Theme):
        assert theme.chrome_inset == pytest.approx(_parsed_chrome_inset(theme))

    def test_uppercase_labels_matches_chrome(self, theme: Theme):
        sniffed = "text-transform: uppercase" in (theme.chrome_css or "").lower()
        assert theme.uppercase_labels is sniffed

    def test_rounded_font_matches_font_stack(self, theme: Theme):
        head = (theme.font_stack or "").lower().split(",")[0]
        assert theme.rounded_font is ("dejavu" not in head)


def test_every_theme_declares_facts():
    """Guards the parametrization against an empty/partial theme table."""
    assert len(THEMES) == 15
