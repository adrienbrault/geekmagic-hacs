"""A malformed Forecast Days option must not cost the weather cell.

``self.forecast_days`` went straight into a slice (``items[:days]``), and
the panel stores whatever ``parseFloat`` made of the number field: typing
3.5 keeps 3.5, and a view written by hand can carry ``"3"``. A slice bound
that is not an int raises ``TypeError``, which the layout catches by
painting WIDGET ERROR over the cell and logging on every refresh.

The option is now coerced to an int inside the schema's 1..5, the way the
gauge's Decimal Places already degrades a fractional value instead of
breaking the render.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import THEMES
from custom_components.geekmagic.widgets.weather import WeatherWidget, _forecast_days

NOW = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)

# A fullscreen cell reaches the forecast strip (>=130px wide and tall).
CELL = CellContext(width=224, height=224, slot_index=0, theme=THEMES["watchos"])

FORECAST = [
    {
        "datetime": f"2026-05-0{4 + i}T12:00:00+00:00",
        "temperature": 20 + i,
        "templow": 10 + i,
        "condition": "sunny",
    }
    for i in range(5)
]

WEATHER = EntityState(
    entity_id="weather.home",
    state="sunny",
    attributes={"friendly_name": "Home", "temperature": 21.0, "humidity": 55},
)


def _render(**options: Any) -> str:
    widget = WeatherWidget(
        WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home", options=options)
    )
    return widget.render_html(CELL, WidgetState(entity=WEATHER, forecast=FORECAST, now=NOW))


def _columns(fragment: str) -> int:
    return fragment.count('class="wx-col"')


@pytest.mark.parametrize(
    ("stored", "days"),
    [
        (3, 3),
        (3.0, 3),
        (3.5, 3),
        (2.9, 2),
        ("3", 3),
        (" 4 ", 4),
        (None, 3),
        ("", 3),
        ([], 3),
        (0, 1),
        (-2, 1),
        (99, 5),
    ],
)
def test_forecast_days_is_coerced_into_range(stored: Any, days: int) -> None:
    assert _forecast_days(stored) == days


@pytest.mark.parametrize("stored", [3.5, "3", None, "", 0, 99])
def test_a_malformed_count_still_renders_the_strip(stored: Any) -> None:
    fragment = _render(forecast_days=stored)
    assert 'class="wx-col"' in fragment
    assert _columns(fragment) >= 1


@pytest.mark.parametrize(("stored", "days"), [(3, 3), (3.5, 3), ("2", 2), (99, 5)])
def test_the_count_decides_how_many_days_show(stored: Any, days: int) -> None:
    assert _columns(_render(forecast_days=stored)) == days


def test_the_default_is_three_days() -> None:
    assert _columns(_render()) == 3
