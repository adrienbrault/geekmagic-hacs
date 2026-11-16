"""A text widget's own Entity option wins over a leftover entity_id.

``TextWidget.__init__`` documents the option as the stronger binding
("from options, takes precedence over widget entity_id"), and the panel
agrees: this widget type sets ``needs_entity: False``, so its schema's
"Entity (dynamic text)" option is the only entity control the editor ever
shows for it.

A widget-level ``entity_id`` can still be there. The panel carries it over
when a slot's type changes (``setWidgetType`` keeps ``entity_id``), so
turning an Entity widget on ``sensor.a`` into a Text widget leaves
``entity_id: sensor.a`` stored — and ``_get_text`` read that first. The
entity picked in the option was then silently ignored: the cell kept
showing the old sensor's value.

The option is now read first, with the widget-level id kept as the
fallback for a widget that has no option set (and for an option naming an
entity Home Assistant no longer has, which resolves to nothing).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.const import PLACEHOLDER_VALUE
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
CELL = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# The hero block holds the widget's text in a fitted inner div.
_HERO = re.compile(r'class="t-hero"[^>]*>.*?<div[^>]*>([^<]*)</div>')


def _entity(entity_id: str, state: str) -> EntityState:
    return EntityState(entity_id=entity_id, state=state, attributes={})


def _widget(entity_id: str | None, option_entity: str | None) -> TextWidget:
    options: dict[str, Any] = {}
    if option_entity is not None:
        options["entity_id"] = option_entity
    return TextWidget(
        WidgetConfig(widget_type="text", slot=0, entity_id=entity_id, options=options)
    )


def _state(primary: EntityState | None, *extra: EntityState) -> WidgetState:
    return WidgetState(
        entity=primary,
        entities={entity.entity_id: entity for entity in extra},
        now=NOW,
    )


def _text(widget: TextWidget, state: WidgetState) -> list[str]:
    return _HERO.findall(widget.render_html(CELL, state))


def test_the_option_entity_wins_over_the_widget_entity() -> None:
    """A type switch leaves entity_id behind; the option must still win."""
    widget = _widget("sensor.a", "sensor.b")
    state = _state(_entity("sensor.a", "alpha"), _entity("sensor.b", "bravo"))
    assert _text(widget, state) == ["bravo"]


def test_the_option_alone_still_reads_its_entity() -> None:
    widget = _widget(None, "sensor.b")
    assert _text(widget, _state(None, _entity("sensor.b", "bravo"))) == ["bravo"]


def test_the_widget_entity_alone_still_reads_its_entity() -> None:
    """The common case — no option set — keeps working."""
    widget = _widget("sensor.a", None)
    assert _text(widget, _state(_entity("sensor.a", "alpha"))) == ["alpha"]


def test_an_option_that_does_not_resolve_falls_back_to_the_widget_entity() -> None:
    """An option naming a deleted entity must not blank the cell."""
    widget = _widget("sensor.a", "sensor.gone")
    assert _text(widget, _state(_entity("sensor.a", "alpha"))) == ["alpha"]


def test_an_absent_option_entity_reads_as_the_placeholder() -> None:
    """Absence still maps to "--"; the precedence fix does not change that."""
    widget = _widget("sensor.a", "sensor.b")
    state = _state(_entity("sensor.a", "alpha"), _entity("sensor.b", "unavailable"))
    assert _text(widget, state) == [PLACEHOLDER_VALUE]


def test_no_entity_at_all_shows_the_configured_text() -> None:
    widget = TextWidget(WidgetConfig(widget_type="text", slot=0, options={"text": "Ready"}))
    assert _text(widget, _state(None)) == ["Ready"]


@pytest.mark.parametrize("option_entity", ["sensor.b", None])
def test_both_dependencies_are_declared(option_entity: str | None) -> None:
    """Whichever id wins, the coordinator has to snapshot both."""
    widget = _widget("sensor.a", option_entity)
    assert widget.get_entities() == ["sensor.a", *(("sensor.b",) if option_entity else ())]
