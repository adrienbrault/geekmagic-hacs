"""An attribute-list row reads absence as absence, not as a word.

``AttributeListWidget`` maps a missing attribute to the family's ``"--"``
(``_format_value(None)``), but the special ``state`` key returned the raw
state verbatim. A dead sensor's row therefore read "unavailable" — the
longest word a cell can hold, and the one thing the row is least able to
say — while every other widget in the codebase maps that state to ``"--"``
(``entity.py``, ``text.py``).

The state key now goes through the same rule, and the three widgets share
one ``ABSENT_STATES`` constant so the rule cannot drift apart again. A
real state is still shown as published, and a missing attribute is still
``"--"``.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.const import ABSENT_STATES, PLACEHOLDER_VALUE
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.attribute_list import AttributeListWidget
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
# Wide enough for the inline rows (not the stacked ones).
CELL = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# One inline row's value cell. ``--`` also appears in the CSS variables
# (``var(--text-tertiary)``), so the values are matched, never counted.
_ROW_VALUE = re.compile(r"text-align: right; white-space: nowrap;[^\"]*\"[^>]*>([^<]*)</span>")


def _entity(state: str, **attributes: Any) -> EntityState:
    return EntityState(
        entity_id="sensor.arrival",
        state=state,
        attributes={"friendly_name": "Arrival", **attributes},
    )


def _state(entity: EntityState | None) -> WidgetState:
    return WidgetState(entity=entity, now=NOW)


def _list(*attributes: dict[str, Any] | str) -> AttributeListWidget:
    return AttributeListWidget(
        WidgetConfig(
            widget_type="attribute_list",
            slot=0,
            entity_id="sensor.arrival",
            options={"attributes": list(attributes)},
        )
    )


def _values(fragment: str) -> list[str]:
    return _ROW_VALUE.findall(fragment)


@pytest.mark.parametrize("state", sorted(ABSENT_STATES))
def test_state_row_shows_the_placeholder(state: str) -> None:
    """Every "no reading" state reads as the family's marker."""
    fragment = _list({"key": "state", "label": "Arrives"}).render_html(CELL, _state(_entity(state)))
    assert _values(fragment) == [PLACEHOLDER_VALUE], fragment
    assert "unavailable" not in fragment, fragment


@pytest.mark.parametrize("state", ["home", "on", "Off", "23.5", "Arriving"])
def test_a_real_state_is_shown_as_published(state: str) -> None:
    """Absence is the only thing remapped — the published state is kept."""
    fragment = _list({"key": "state", "label": "Arrives"}).render_html(CELL, _state(_entity(state)))
    assert _values(fragment) == [state], fragment


def test_a_missing_attribute_still_reads_as_the_placeholder() -> None:
    """The attribute half of the rule is unchanged."""
    fragment = _list({"key": "route", "label": "Route"}).render_html(
        CELL, _state(_entity("unavailable"))
    )
    assert _values(fragment) == [PLACEHOLDER_VALUE], fragment


def test_an_absent_entity_still_reads_as_the_placeholder() -> None:
    """No entity at all was already handled; the state key agrees with it."""
    fragment = _list({"key": "state", "label": "Arrives"}).render_html(CELL, _state(None))
    assert _values(fragment) == [PLACEHOLDER_VALUE], fragment


def test_the_state_and_an_attribute_agree_in_one_cell() -> None:
    """Two rows of the same dead sensor must not disagree about absence."""
    widget = _list({"key": "state", "label": "Arrives"}, {"key": "route", "label": "Route"})
    fragment = widget.render_html(CELL, _state(_entity("unavailable")))
    assert _values(fragment) == [PLACEHOLDER_VALUE, PLACEHOLDER_VALUE], fragment


def test_the_shared_constant_is_what_the_other_widgets_read() -> None:
    """entity.py and text.py draw the same marker for the same states."""
    entity_widget = EntityWidget(
        WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.arrival")
    )
    text_widget = TextWidget(
        WidgetConfig(widget_type="text", slot=0, options={"entity_id": "sensor.arrival"})
    )
    absent = _state(_entity("unavailable"))
    assert PLACEHOLDER_VALUE in entity_widget.render_html(CELL, absent)
    assert PLACEHOLDER_VALUE in text_widget.render_html(CELL, absent)
