"""A lock reads as off when it is locked, on when it is unlocked.

Home Assistant reports a lock as ``locked`` or ``unlocked``, and treats
the *unlocked* one as the active state: ``translate_binary_state("on",
"lock")`` says "Unlocked", ``get_domain_state_icon`` draws a closed padlock
for ``locked``, and the chart history maps ``unlocked`` to 1.0. The shared
``ON_STATES`` table listed both spellings, so a Status widget bound to a
lock always chose its on-text and its success colour: the tile could never
say the door was locked.
"""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import Widget, WidgetConfig
from custom_components.geekmagic.widgets.helpers import ON_STATES
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import (
    StatusListWidget,
    StatusWidget,
    _is_entity_on,
)
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

# The three Status layouts: stack, strip, compact.
_CELLS = [(240, 240), (228, 74), (74, 56)]


def ctx_for(width: int, height: int) -> CellContext:
    return CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)


def lock(state: str) -> EntityState:
    return EntityState(
        entity_id="lock.front_door",
        state=state,
        attributes={"friendly_name": "Front Door"},
    )


def render(widget: Widget, state: WidgetState, width: int = 240, height: int = 240) -> str:
    return widget.render_html(ctx_for(width, height), state)


@pytest.mark.parametrize(
    ("state", "expected"),
    [("locked", False), ("unlocked", True), ("on", True), ("off", False), ("home", True)],
)
def test_on_states_match_home_assistant(state: str, expected: bool) -> None:
    """The shared table agrees with how Home Assistant reads each state."""
    entity = EntityState(entity_id="lock.front_door", state=state)
    assert _is_entity_on(entity) is expected


def test_locked_is_not_an_on_state() -> None:
    """``locked`` is the resting state of a lock, so it is not in the table."""
    assert "locked" not in ON_STATES
    assert "unlocked" in ON_STATES


@pytest.mark.parametrize(("width", "height"), _CELLS)
def test_status_widget_tells_a_locked_lock_from_an_unlocked_one(width: int, height: int) -> None:
    """Every Status layout switches text and tint with the lock."""
    widget = StatusWidget(
        WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="lock.front_door",
            options={"on_text": "OPEN", "off_text": "SHUT"},
        )
    )

    shut = render(widget, WidgetState(entity=lock("locked")), width, height)
    open_ = render(widget, WidgetState(entity=lock("unlocked")), width, height)

    assert "SHUT" in shut
    assert "OPEN" not in shut
    assert "OPEN" in open_
    assert "SHUT" not in open_


# A status list spends its height on rows, so the 74x56 cell drops the
# state text for every row (see ``_state_text`` callers) and cannot say it.
_LIST_CELLS = [(240, 240), (228, 74)]


@pytest.mark.parametrize(("width", "height"), _LIST_CELLS)
def test_status_list_row_tells_a_locked_lock_from_an_unlocked_one(width: int, height: int) -> None:
    """A lock in a status list gets its own row text, not always the on one."""
    widget = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "entities": [{"entity_id": "lock.front_door"}],
                "on_text": "OPEN",
                "off_text": "SHUT",
            },
        )
    )

    shut = render(widget, WidgetState(entities={"lock.front_door": lock("locked")}), width, height)
    open_ = render(
        widget, WidgetState(entities={"lock.front_door": lock("unlocked")}), width, height
    )

    assert "SHUT" in shut
    assert "OPEN" not in shut
    assert "OPEN" in open_
    assert "SHUT" not in open_


def _tint(html: str) -> dict[str, Any]:
    """The colours a rendered cell asks for, for the tint assertion."""
    return {"success": "var(--success)" in html, "muted": "var(--muted)" in html}


def test_a_locked_lock_is_not_tinted_as_success() -> None:
    """The colour is the meaning here: a locked door must not read green."""
    widget = StatusWidget(
        WidgetConfig(
            widget_type="status",
            slot=0,
            entity_id="lock.front_door",
            options={"on_text": "OPEN", "off_text": "SHUT"},
        )
    )

    assert _tint(render(widget, WidgetState(entity=lock("locked"))))["success"] is False
    assert _tint(render(widget, WidgetState(entity=lock("unlocked"))))["success"] is True
