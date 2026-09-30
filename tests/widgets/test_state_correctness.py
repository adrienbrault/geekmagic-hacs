"""Regression tests for widgets that painted misleading states.

Each section pins one finding from the correctness review: a value the
widget rendered as if it were a real reading when it was not (negative,
unavailable, NaN), or a state rendered with the wrong meaning.
"""

from __future__ import annotations

import re
from typing import Any

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


def _entity(entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> EntityState:
    return EntityState(entity_id=entity_id, state=state, attributes=attributes or {})


def _fill_widths(fragment: str) -> list[float]:
    """Every bar fill width (``width: N%``) the fragment paints."""
    return [float(w) for w in re.findall(r"width: (-?[\d.]+)%", fragment)]


# ---------------------------------------------------------------------------
# Progress: a negative reading must not paint a full bar
# ---------------------------------------------------------------------------


def test_progress_negative_value_paints_empty_bar() -> None:
    widget = ProgressWidget(
        WidgetConfig(widget_type="progress", slot=0, entity_id="sensor.x", options={"target": 100})
    )
    fragment = widget.render_html(CTX, WidgetState(entity=_entity("sensor.x", "-20")))
    # ``width: -20%`` is invalid CSS and Blitz falls back to a full-width fill.
    assert all(w >= 0 for w in _fill_widths(fragment))
    assert "width: 0.0%" in fragment


def test_multi_progress_negative_value_paints_empty_bar() -> None:
    widget = MultiProgressWidget(
        WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            options={"items": [{"entity_id": "sensor.x", "target": 100, "label": "X"}]},
        )
    )
    state = WidgetState(entities={"sensor.x": _entity("sensor.x", "-20")})
    fragment = widget.render_html(CTX, state)
    assert all(w >= 0 for w in _fill_widths(fragment))
    assert "width: 0.0%" in fragment
