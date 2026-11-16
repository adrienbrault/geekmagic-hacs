"""A negative progress value fills nothing, not the whole bar.

``percent = min(100, value / target * 100)`` bounded the share above but
not below. A sensor under the start of the scale (a budget gone negative,
a temperature delta) produced ``width: -20.0%`` on the bar's fill div.
A negative width is invalid CSS: the declaration is dropped, the fill
div falls back to ``width: auto`` and paints the *entire* track — so the
bar claimed 100 % while the hero beside it read "-20".

Both percentages now come from the same clamped helper the gauge uses,
so the bar and the number agree: below zero is 0 % of the way to the
target. The raw reading stays visible in the value chip.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CELL = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# The bar's fill: ``width: <share>%; height: 100%; background: <colour>``.
_FILL_WIDTH = re.compile(r"width: (-?[\d.]+)%; height: 100%; background")
# The single progress widget's percent hero: ``<span class="t-hero">73</span>``.
_HERO = re.compile(r'<span class="t-hero"[^>]*>(-?[\d.]+)</span>')
# A multi-progress row's percent readout: ``text-align: right">73%</span>``.
_ROW_PERCENT = re.compile(r'text-align: right">(-?\d+)%</span>')


def _state(entity_id: str, value: str) -> WidgetState:
    entity = EntityState(
        entity_id=entity_id,
        state=value,
        attributes={"friendly_name": entity_id.rsplit(".", maxsplit=1)[-1].title()},
    )
    return WidgetState(entity=entity, now=datetime(2026, 10, 15, 12, 0, tzinfo=UTC))


def _progress(value: str, **options: Any) -> ProgressWidget:
    return ProgressWidget(
        WidgetConfig(
            widget_type="progress",
            slot=0,
            entity_id="sensor.steps",
            options={"target": 100, **options},
        )
    )


def _multi(items: list[dict[str, Any]]) -> MultiProgressWidget:
    return MultiProgressWidget(
        WidgetConfig(
            widget_type="multi_progress",
            slot=0,
            entity_id=None,
            options={"items": items},
        )
    )


@pytest.mark.parametrize(
    ("value", "share"),
    [
        ("50", "50.0"),
        ("-20", "0.0"),
        ("-0.4", "0.0"),
        ("0", "0.0"),
        ("150", "100.0"),
    ],
)
def test_bar_share_never_goes_below_zero(value: str, share: str) -> None:
    """The fill is a valid 0..100 CSS width for any reading."""
    fragment = _progress(value).render_html(CELL, _state("sensor.steps", value))
    widths = _FILL_WIDTH.findall(fragment)
    assert widths == [share], fragment


@pytest.mark.parametrize("value", ["-20", "-0.4"])
def test_negative_reading_never_shows_a_negative_percent(value: str) -> None:
    """The hero agrees with the bar, and the raw reading is still shown."""
    fragment = _progress(value).render_html(CELL, _state("sensor.steps", value))
    assert _HERO.findall(fragment) == ["0"], fragment
    # The chip keeps the real reading, so nothing is hidden from the user.
    assert value in fragment


def test_hero_hint_sizes_the_clamped_percent() -> None:
    """Sibling harmony measures the same string the hero draws."""
    widget = _progress("-20")
    hint = widget.hero_hint(CELL, _state("sensor.steps", "-20"))
    assert hint is not None
    assert hint == _progress("0").hero_hint(CELL, _state("sensor.steps", "0"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("50", "50"), ("-20", "0"), ("-0.4", "0"), ("150", "100")],
)
def test_multi_progress_rows_are_clamped_too(value: str, expected: str) -> None:
    """One row below the scale must not paint a full bar either."""
    widget = _multi([{"entity_id": "sensor.steps", "target": 100}])
    fragment = widget.render_html(CELL, _state("sensor.steps", value))
    assert _ROW_PERCENT.findall(fragment) == [expected], fragment
    assert all(float(width) >= 0.0 for width in _FILL_WIDTH.findall(fragment)), fragment


def test_multi_progress_bar_share_matches_the_row_percent() -> None:
    """The bar and its own readout never disagree."""
    widget = _multi([{"entity_id": "sensor.steps", "target": 100}])
    fragment = widget.render_html(CELL, _state("sensor.steps", "-20"))
    assert _FILL_WIDTH.findall(fragment) == ["0.0"], fragment


@pytest.mark.parametrize("target", [0, -50])
def test_a_useless_target_still_draws_an_empty_bar(target: Any) -> None:
    """A zero or negative target has no share to draw."""
    widget = _multi([{"entity_id": "sensor.steps", "target": target}])
    fragment = widget.render_html(CELL, _state("sensor.steps", "20"))
    assert _ROW_PERCENT.findall(fragment) == ["0"], fragment
