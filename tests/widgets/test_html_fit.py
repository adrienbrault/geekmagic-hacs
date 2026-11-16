"""The HTML widget's fit() helper: one line of text sized to fit."""

from __future__ import annotations

import re

import pytest

from custom_components.geekmagic.engine import get_engine
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets._htmlkit import template_helpers
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

pytestmark = pytest.mark.skipif(get_engine() is None, reason="blitz-py not installed")

FIT = template_helpers(CellContext(width=240, height=240, theme=DEFAULT_THEME))["fit"]


def size(markup: str) -> int:
    match = re.search(r"font-size: (\d+)px", markup)
    assert match, markup
    return int(match.group(1))


def text(markup: str) -> str:
    match = re.search(r">([^<]*)</span>", markup)
    assert match, markup
    return match.group(1)


def test_short_value_takes_the_max() -> None:
    assert size(FIT("A", max=82)) == 82


def test_longer_value_shrinks() -> None:
    assert size(FIT("unavailable", max=82)) < size(FIT("21.5°C", max=82)) <= 82


def test_too_long_even_at_min_is_cut() -> None:
    fitted = FIT("Living room temperature sensor downstairs", max=40, min=24)
    assert size(fitted) == 24
    assert text(fitted).endswith("…")


def test_width_bounds_the_size() -> None:
    assert size(FIT("unavailable", width=100, max=82)) < size(FIT("unavailable", max=82))


def test_weight_and_tracking_are_rendered() -> None:
    fitted = FIT("21.5", weight="extrabold", tracking=-0.02)
    assert "font-weight: 800" in fitted
    assert "letter-spacing: -0.02em" in fitted
    assert "font-weight: 600" in FIT("21.5", weight=600)


def test_escapes_and_handles_missing_values() -> None:
    assert "&lt;b&gt;" in FIT("<b>")
    assert FIT(None) == ""


def test_defaults_follow_the_cell() -> None:
    small = template_helpers(CellContext(width=76, height=76, theme=DEFAULT_THEME))["fit"]
    assert size(small("A")) == 38  # half the cell's height
