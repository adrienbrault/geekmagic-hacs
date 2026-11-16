"""The weather widget never paints a sun it has no reading for.

An ``unavailable`` weather entity rendered an orange sun above the
"UNAVAILABLE" caption: every condition the icon map did not know —
HA's ``unavailable``/``unknown`` states, a forecast day without a
condition, a provider's non-standard string — fell back to sunny. A sun
claims fair weather when we know nothing; those cases get the muted
no-data glyph instead, at every size and in every forecast builder.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.icons import get_mdi_char, is_valid_icon
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import THEMES
from custom_components.geekmagic.widgets.weather import (
    _NO_DATA_ICON,
    WEATHER_COLORS,
    WEATHER_ICONS,
    WeatherWidget,
)

SUN = f"&#x{ord(get_mdi_char('weather-sunny')):X};"
NO_DATA = f"&#x{ord(get_mdi_char(_NO_DATA_ICON)):X};"

# Every icon the widget draws is an mdi_span whose inline style opens
# with its tint: ``<span class="wx-icon" style="color: X; ...">&#x...;``.
_ICON_SPAN = re.compile(
    r'<span class="(?:wx-icon|icon)" style="color: ([^;"]+)[^"]*">(&#x[0-9A-F]+;)</span>'
)

# Cell shapes that reach each branch: fullscreen (side by side + strip),
# a 2x2 tile (stacked + chips), a 3x3 tile (icon + value only), a narrow
# split column (forecast rows) and a short split cell (mini strip).
CELLS = {
    "fullscreen": (224, 224),
    "2x2": (108, 108),
    "3x3": (69, 69),
    "list": (111, 228),
    "mini": (224, 108),
}

FORECAST_CELLS = {k: CELLS[k] for k in ("fullscreen", "list", "mini")}


def _ctx(cell: tuple[int, int], theme: str = "watchos") -> CellContext:
    width, height = cell
    return CellContext(width=width, height=height, slot_index=0, theme=THEMES[theme])


def _widget() -> WeatherWidget:
    return WeatherWidget(WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home"))


def _entity(condition: str, **attrs: Any) -> EntityState:
    return EntityState(
        entity_id="weather.home",
        state=condition,
        attributes={"friendly_name": "Home", **attrs},
    )


def _icons(fragment: str) -> list[tuple[str, str]]:
    """``(tint, glyph)`` for every icon in the fragment, in order."""
    return _ICON_SPAN.findall(fragment)


def test_no_data_glyph_is_in_the_embedded_font():
    assert is_valid_icon(_NO_DATA_ICON)


def test_every_known_condition_has_a_tint():
    assert WEATHER_ICONS.keys() == WEATHER_COLORS.keys()


@pytest.mark.parametrize("theme", ["watchos", "night"])
@pytest.mark.parametrize("cell", CELLS.values(), ids=CELLS.keys())
@pytest.mark.parametrize("condition", ["unavailable", "unknown", "smoky"])
def test_condition_without_a_glyph_is_muted_not_sunny(condition, cell, theme):
    """Unavailable, unknown and unrecognised conditions draw the muted no-data glyph."""
    fragment = _widget().render_html(_ctx(cell, theme), WidgetState(entity=_entity(condition)))

    icons = _icons(fragment)
    assert SUN not in fragment
    assert icons[0] == ("var(--muted)", NO_DATA)


@pytest.mark.parametrize("cell", CELLS.values(), ids=CELLS.keys())
def test_unavailable_keeps_the_placeholder_value(cell):
    fragment = _widget().render_html(_ctx(cell), WidgetState(entity=_entity("unavailable")))
    assert "--" in fragment
    assert "°" not in fragment


@pytest.mark.parametrize("cell", CELLS.values(), ids=CELLS.keys())
def test_missing_entity_shows_the_placeholder(cell):
    fragment = _widget().render_html(_ctx(cell), WidgetState(entity=None))
    assert SUN not in fragment
    assert all(tint == "var(--muted)" for tint, _ in _icons(fragment))


@pytest.mark.parametrize("cell", FORECAST_CELLS.values(), ids=FORECAST_CELLS.keys())
@pytest.mark.parametrize(
    "day",
    [
        {"condition": "smoky"},
        {"condition": "unavailable"},
        {},  # no condition key at all
    ],
    ids=["unrecognised", "unavailable", "missing"],
)
def test_forecast_day_without_a_glyph_is_muted_not_sunny(day, cell):
    """Columns, rows and the mini strip all share the no-data fallback."""
    forecast = [{"datetime": "2025-12-29T00:00:00+00:00", "temperature": 20, "templow": 10, **day}]
    state = WidgetState(entity=_entity("rainy", temperature=18), forecast=forecast)
    fragment = _widget().render_html(_ctx(cell), state)

    icons = _icons(fragment)
    assert SUN not in fragment
    # The hero (rainy) first, then the one forecast day.
    assert icons[-1] == ("var(--muted)", NO_DATA)


def test_known_condition_keeps_its_glyph():
    fragment = _widget().render_html(
        _ctx(CELLS["fullscreen"]), WidgetState(entity=_entity("sunny", temperature=24))
    )
    assert _icons(fragment)[0] == ("var(--warning)", SUN)
