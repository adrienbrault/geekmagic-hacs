"""A multi-progress row for a sensor with no reading draws no number.

The single progress widget learned this in #288 (``reading_of``): a sensor
that reports ``unavailable`` / ``unknown`` / a non-finite value has no
reading, and absence is not a measured zero. The multi-progress row kept
calling ``EntityState.numeric()``, which answers ``0.0`` for anything it
cannot parse — so a stack of dead sensors headlined "0/100 steps" and a
"0 %" readout over an empty bar, claiming a progress that was never
measured.

The row now reads through ``reading_of`` too: a missing reading shows the
family's "--" in both the raw-value slot and the percent column, and the
bar stays empty. A real ``0`` still reads 0, and a row with no entity
configured is still a goal nothing has counted toward yet.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.progress import MultiProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
# A cell where every band (label, raw value, percent) survives.
CELL = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# The bar's fill: ``width: <share>%; height: 100%; background: <colour>``.
_FILL_WIDTH = re.compile(r"width: (-?[\d.]+)%; height: 100%; background")
# A row's percent readout, in its fixed-width column.
_ROW_PERCENT = re.compile(r'text-align: right">([^<]*)</span>')
# A row's raw "amount/target unit" text.
_ROW_VALUE = re.compile(r'color: var\(--text-secondary\)">([^<]*)</span>')

# States that carry no number, plus the non-finite ones ``float()`` accepts.
ABSENT = ("unavailable", "unknown", "", "NaN", "inf", "-inf")


def _entity(state: str, **attributes: Any) -> EntityState:
    return EntityState(
        entity_id="sensor.steps",
        state=state,
        attributes={
            "friendly_name": "Steps",
            "unit_of_measurement": "steps",
            **attributes,
        },
    )


def _state(entity: EntityState | None) -> WidgetState:
    return WidgetState(entity=entity, now=NOW)


def _multi(items: list[dict[str, Any]]) -> MultiProgressWidget:
    return MultiProgressWidget(
        WidgetConfig(widget_type="multi_progress", slot=0, options={"items": items})
    )


def _row(**item: Any) -> MultiProgressWidget:
    return _multi([{"entity_id": "sensor.steps", "target": 100, **item}])


@pytest.mark.parametrize("state", ABSENT)
def test_percent_column_shows_the_placeholder(state: str) -> None:
    """No reading means no percentage — not 0 % of the way to the target."""
    fragment = _row().render_html(CELL, _state(_entity(state)))
    assert _ROW_PERCENT.findall(fragment) == ["--"], fragment


@pytest.mark.parametrize("state", ABSENT)
def test_raw_value_is_the_placeholder_without_a_target(state: str) -> None:
    """The row's "amount/target" slot drops the target it knows nothing about."""
    fragment = _row().render_html(CELL, _state(_entity(state)))
    assert _ROW_VALUE.findall(fragment) == ["--"], fragment


@pytest.mark.parametrize("state", ABSENT)
def test_bar_draws_no_progress(state: str) -> None:
    """The fill is a valid 0 % width, never a full bar from a dead sensor."""
    fragment = _row().render_html(CELL, _state(_entity(state)))
    assert _FILL_WIDTH.findall(fragment) == ["0.0"], fragment


@pytest.mark.parametrize("state", ABSENT)
def test_the_unit_does_not_ride_the_placeholder(state: str) -> None:
    """ "-- steps" would name a unit for a value there is none of.

    The unit is lowercase and the row's label is upper-cased, so a bare
    ``steps`` in the fragment can only be the unit.
    """
    fragment = _row().render_html(CELL, _state(_entity(state)))
    assert "steps" not in fragment, fragment


def test_a_real_zero_is_still_a_reading() -> None:
    """A sensor that reports 0 has counted nothing — that is a measurement."""
    fragment = _row().render_html(CELL, _state(_entity("0")))
    assert _ROW_VALUE.findall(fragment) == ["0/100 steps"], fragment
    assert _ROW_PERCENT.findall(fragment) == ["0%"], fragment


def test_a_reading_that_is_present_still_reads() -> None:
    fragment = _row().render_html(CELL, _state(_entity("42")))
    assert _ROW_VALUE.findall(fragment) == ["42/100 steps"], fragment
    assert _ROW_PERCENT.findall(fragment) == ["42%"], fragment


def test_a_row_with_no_entity_is_a_bar_nothing_counted_toward() -> None:
    """An unconfigured row is not a dead sensor: 0 of its target is the truth."""
    fragment = _multi([{"entity_id": "", "target": 100}]).render_html(CELL, _state(None))
    assert _ROW_VALUE.findall(fragment) == ["0/100"], fragment
    assert _ROW_PERCENT.findall(fragment) == ["0%"], fragment


def test_an_absent_row_keeps_its_label() -> None:
    """The row still says which sensor is down — only the numbers go."""
    fragment = _row().render_html(CELL, _state(_entity("unavailable")))
    assert "STEPS" in fragment, fragment


def test_absent_and_live_rows_share_one_column() -> None:
    """The percent column keeps its width, so the bars still end together."""
    widget = _multi(
        [
            {"entity_id": "sensor.steps", "target": 100},
            {"entity_id": "sensor.dead", "target": 100},
        ]
    )
    live = _entity("50")
    dead = EntityState(entity_id="sensor.dead", state="unavailable", attributes={})
    state = WidgetState(entity=live, entities={"sensor.dead": dead}, now=NOW)
    fragment = widget.render_html(CELL, state)
    assert _ROW_PERCENT.findall(fragment) == ["50%", "--"], fragment
