"""Weather forecast day names follow Home Assistant's timezone (issue #75).

Providers such as AEMET and Pirate Weather send each daily entry as local
midnight expressed in UTC: Thursday 15 Oct in Madrid arrives as
``2026-10-14T22:00:00+00:00``. Reading the UTC date labelled every day
one day early. The weekday must be taken from the instant converted to
the timezone ``state.now`` carries (HA's), as the HA weather card does.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from custom_components.geekmagic.widgets.weather import (
    WEEKDAY_NAMES,
    WeatherWidget,
    _parse_forecast_day_name,
)

MADRID = ZoneInfo("Europe/Madrid")
NEW_YORK = ZoneInfo("America/New_York")

# Thursday 15 Oct 2026, mid-morning in Madrid (CEST, UTC+2).
MADRID_NOW = datetime(2026, 10, 15, 10, 0, tzinfo=MADRID)

# Cell shapes that reach each forecast builder: day columns, rows in a
# narrow split column, and the short-cell mini strip with day names.
CELLS = {
    "columns": (240, 240),
    "list": (111, 228),
    "mini": (224, 108),
}


def _widget(**options: Any) -> WeatherWidget:
    return WeatherWidget(
        WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home", options=options)
    )


def _state(forecast: list[dict[str, Any]], now: datetime | None) -> WidgetState:
    entity = EntityState(
        entity_id="weather.home",
        state="sunny",
        attributes={"friendly_name": "Home", "temperature": 22},
    )
    return WidgetState(entity=entity, forecast=forecast, now=now)


def _day(when: str, high: int = 20) -> dict[str, Any]:
    return {"datetime": when, "condition": "sunny", "temperature": high, "templow": 10}


def _labels(fragment: str) -> list[str]:
    """Weekday labels in the order the strip renders them."""
    names = {name.upper() for name in WEEKDAY_NAMES}
    found: list[tuple[int, str]] = []
    for name in names:
        start = 0
        while (pos := fragment.find(f">{name}<", start)) != -1:
            found.append((pos, name))
            start = pos + 1
    return [name for _, name in sorted(found)]


@pytest.mark.parametrize("cell", CELLS.values(), ids=CELLS.keys())
@pytest.mark.parametrize(
    ("when", "tz", "expected"),
    [
        # AEMET / Pirate Weather: local midnight as UTC, "+00:00" or "Z".
        ("2026-10-14T22:00:00+00:00", MADRID, "THU"),
        ("2026-10-14T22:00:00Z", MADRID, "THU"),
        # The provider's own (positive) offset.
        ("2026-10-15T00:00:00+02:00", MADRID, "THU"),
        # A negative offset is an instant too: 18:00 at -04:00 is
        # Thursday 00:00 in Madrid.
        ("2026-10-14T18:00:00-04:00", MADRID, "THU"),
        # Same instant convention west of UTC.
        ("2026-10-15T04:00:00Z", NEW_YORK, "THU"),
        # Each instant gets its own UTC offset across the DST change
        # (Madrid leaves CEST on 25 Oct 2026).
        ("2026-10-24T22:00:00+00:00", MADRID, "SUN"),
        ("2026-10-25T23:00:00+00:00", MADRID, "MON"),
        # Naive values and plain dates are already local wall time.
        ("2026-10-15T00:00:00", MADRID, "THU"),
        ("2026-10-15", MADRID, "THU"),
        ("2026-10-15", NEW_YORK, "THU"),
    ],
)
def test_day_name_in_ha_timezone(when, tz, expected, cell):
    """Every builder labels the day the instant falls on in HA's timezone."""
    width, height = cell
    ctx = CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)
    now = datetime(2026, 10, 15, 10, 0, tzinfo=tz)
    fragment = _widget(forecast_days=1).render_html(ctx, _state([_day(when)], now))
    assert _labels(fragment) == [expected]


def test_today_and_tomorrow_line_up_with_now():
    """The first entry reads as today, and "start tomorrow" begins at tomorrow."""
    forecast = [
        _day("2026-10-14T22:00:00+00:00", 21),  # Thu 15 Oct, Madrid
        _day("2026-10-15T22:00:00+00:00", 22),  # Fri
        _day("2026-10-16T22:00:00+00:00", 23),  # Sat
        _day("2026-10-17T22:00:00+00:00", 24),  # Sun
    ]
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    today = MADRID_NOW.strftime("%a").upper()

    fragment = _widget().render_html(ctx, _state(forecast, MADRID_NOW))
    assert _labels(fragment) == [today, "FRI", "SAT"]

    fragment = _widget(forecast_start_tomorrow=True).render_html(ctx, _state(forecast, MADRID_NOW))
    assert _labels(fragment) == ["FRI", "SAT", "SUN"]
    assert today not in _labels(fragment)


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        # Without a timezone the instant keeps its own offset's date.
        ("2026-10-14T22:00:00+00:00", "Wed"),
        ("2026-10-14T22:00:00Z", "Wed"),
        ("2026-10-15T00:00:00+02:00", "Thu"),
        ("2026-10-14T18:00:00-04:00", "Wed"),
        ("2026-10-15", "Thu"),
    ],
)
def test_day_name_without_timezone(when, expected):
    """No known timezone (state without ``now``): read the value as given."""
    assert _parse_forecast_day_name(when, "D1") == expected


def test_render_without_now_keeps_value_offset():
    """A state with no ``now`` still renders, reading the provider's offset."""
    ctx = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
    fragment = _widget(forecast_days=1).render_html(
        ctx, _state([_day("2026-10-15T00:00:00+02:00")], None)
    )
    assert _labels(fragment) == ["THU"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", "D2"),
        ("Mon", "Mon"),
        ("Tuesday", "Tue"),
        ("12345", "D2"),
        ("2026-13-45", "D2"),
        ("not a date", "not"),
    ],
)
def test_unparsable_values_fall_back(value, expected):
    """Strings that aren't dates keep the day-name / positional fallback."""
    assert _parse_forecast_day_name(value, "D2") == expected
