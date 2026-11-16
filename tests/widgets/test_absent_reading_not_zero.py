"""A sensor with no reading draws no number, not a confident zero.

``EntityState.numeric`` answers its caller's default (``0.0``) for anything
it cannot parse. That is what arithmetic wants, but the gauge family read it
as a *measurement*: an ``unavailable`` battery headlined "0" over an empty
bar, and on a scale with a negative minimum (a temperature delta, a budget
gone negative) the same dead sensor filled the bar to the middle — the fill
was the true 0 on that scale.

Absence now goes through ``reading_of``: a reading is a finite number or
nothing, and nothing renders as the family's "--" with no fill and no
sibling type harmony. A real ``0`` still reads 0.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets._gauge import reading_of
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.progress import ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

NOW = datetime(2026, 5, 4, 9, 30, tzinfo=UTC)

# The bar's fill: ``width: <share>%; height: 100%; background: <colour>``.
_FILL = re.compile(r"width: (-?[\d.]+)%; height: 100%")
# The vertical bar fills by height instead.
_FILL_H = re.compile(r"height: (-?[\d.]+)%; background")
# The hero's text (the value span carries the fitted size inline).
_HERO = re.compile(r't-hero"[^>]*>([^<]*)<')
# A ring/arc's value arc: ``stroke-dasharray="<dash> <circumference>"``.
_DASH = re.compile(r'stroke-dasharray="([\d.]+) ')
# The progress widget's value chip.
_CHIP = re.compile(r'<span class="chip"><span>([^<]*)</span></span>')

# A cell where every band (caption, hero, bar, chip) survives.
CELL = CellContext(width=224, height=224, slot_index=0, theme=DEFAULT_THEME)

# States that carry no number. "" is a sensor mid-setup; NaN/inf are not
# readings either, and would otherwise poison every percentage.
ABSENT = ("unavailable", "unknown", "", "NaN", "inf", "-inf")


def _entity(state: str, **attributes: Any) -> EntityState:
    return EntityState(
        entity_id="sensor.probe",
        state=state,
        attributes={"friendly_name": "Probe", "unit_of_measurement": "%", **attributes},
    )


def _state(entity: EntityState | None) -> WidgetState:
    return WidgetState(entity=entity, now=NOW)


def _gauge(**options: Any) -> GaugeWidget:
    return GaugeWidget(
        WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.probe", options=options)
    )


def _progress(**options: Any) -> ProgressWidget:
    return ProgressWidget(
        WidgetConfig(widget_type="progress", slot=0, entity_id="sensor.probe", options=options)
    )


class TestReadingOf:
    """The conversion rule itself."""

    @pytest.mark.parametrize("state", ABSENT)
    def test_absent_states_are_not_numbers(self, state: str) -> None:
        assert reading_of(_entity(state)) is None

    def test_no_entity_is_not_a_number(self) -> None:
        assert reading_of(None) is None

    @pytest.mark.parametrize(("state", "value"), [("0", 0.0), ("42.5", 42.5), ("-3", -3.0)])
    def test_numbers_survive(self, state: str, value: float) -> None:
        assert reading_of(_entity(state)) == value

    def test_a_number_typed_state_is_a_number(self) -> None:
        assert reading_of(EntityState(entity_id="sensor.probe", state="7.25")) == 7.25

    def test_a_missing_attribute_is_not_a_number(self) -> None:
        entity = _entity("heat", humidity=None)
        assert reading_of(entity, "humidity") is None

    def test_a_present_attribute_wins_over_the_state(self) -> None:
        entity = _entity("heat", humidity="55")
        assert reading_of(entity, "humidity") == 55.0


class TestGaugeAbsentReading:
    """The gauge draws "--" and no fill when its sensor has no reading."""

    @pytest.mark.parametrize("state", ABSENT)
    def test_hero_is_the_placeholder(self, state: str) -> None:
        widget = _gauge(min=0, max=100)
        fragment = widget.render_html(CELL, _state(_entity(state)))
        assert _HERO.findall(fragment) == ["--"]

    @pytest.mark.parametrize("state", ABSENT)
    def test_bar_draws_no_progress(self, state: str) -> None:
        widget = _gauge(min=0, max=100)
        fragment = widget.render_html(CELL, _state(_entity(state)))
        assert _FILL.findall(fragment) == ["0.0"]

    @pytest.mark.parametrize("state", ABSENT)
    def test_a_negative_scale_does_not_fill_to_the_middle(self, state: str) -> None:
        # 0 is half-way up a -20..20 scale. A dead sensor must not sit there.
        widget = _gauge(min=-20, max=20)
        fragment = widget.render_html(CELL, _state(_entity(state)))
        assert _FILL.findall(fragment) == ["0.0"]

    def test_ring_draws_no_arc(self) -> None:
        widget = _gauge(style="ring", min=-20, max=20)
        fragment = widget.render_html(CELL, _state(_entity("unavailable")))
        # The value ring is the only dasharray: 0 leaves the track bare.
        assert _DASH.findall(fragment) == ["0.00"]
        assert _HERO.findall(fragment) == ["--"]

    def test_arc_draws_only_its_track(self) -> None:
        widget = _gauge(style="arc", min=-20, max=20)
        fragment = widget.render_html(CELL, _state(_entity("unavailable")))
        # The value path is only emitted above half a degree of sweep.
        assert fragment.count("<path") == 1
        assert _HERO.findall(fragment) == ["--"]

    def test_vertical_bar_draws_no_progress(self) -> None:
        widget = _gauge(min=-20, max=20, orientation="vertical")
        tall = CellContext(width=111, height=228, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(tall, _state(_entity("unavailable")))
        assert _FILL_H.findall(fragment) == ["0.0"]

    def test_an_absent_reading_takes_no_sibling_size(self) -> None:
        widget = _gauge(min=0, max=100)
        assert widget.hero_hint(CELL, _state(_entity("unavailable"))) is None

    def test_a_missing_attribute_reads_as_absent(self) -> None:
        widget = _gauge(attribute="humidity")
        fragment = widget.render_html(CELL, _state(_entity("heat", humidity=None)))
        assert _HERO.findall(fragment) == ["--"]
        assert _FILL.findall(fragment) == ["0.0"]

    def test_a_real_zero_is_still_a_reading(self) -> None:
        widget = _gauge(min=0, max=100)
        fragment = widget.render_html(CELL, _state(_entity("0")))
        assert _HERO.findall(fragment) == ["0"]
        assert _FILL.findall(fragment) == ["0.0"]
        assert widget.hero_hint(CELL, _state(_entity("0"))) is not None

    def test_a_real_zero_keeps_its_place_on_a_negative_scale(self) -> None:
        widget = _gauge(min=-20, max=20)
        fragment = widget.render_html(CELL, _state(_entity("0")))
        assert _HERO.findall(fragment) == ["0"]
        assert _FILL.findall(fragment) == ["50.0"]

    def test_a_value_still_reaches_the_threshold_colour(self) -> None:
        widget = _gauge(min=0, max=100, color_thresholds=[{"value": 40, "color": [255, 0, 0]}])
        hot = widget.render_html(CELL, _state(_entity("60")))
        cold = widget.render_html(CELL, _state(_entity("10")))
        assert "rgb(255, 0, 0)" in hot
        assert "rgb(255, 0, 0)" not in cold

    def test_an_absent_reading_ignores_thresholds(self) -> None:
        widget = _gauge(min=0, max=100, color_thresholds=[{"value": 0, "color": [255, 0, 0]}])
        fragment = widget.render_html(CELL, _state(_entity("unavailable")))
        # The threshold matches 0, but no reading means no state colour to
        # paint — the widget falls back to the theme/slot accent.
        assert "rgb(255, 0, 0)" not in fragment


class TestProgressAbsentReading:
    """The progress widget shows "--" rather than 0 % of the target."""

    @pytest.mark.parametrize("state", ABSENT)
    def test_hero_is_the_placeholder(self, state: str) -> None:
        widget = _progress(target=100)
        fragment = widget.render_html(CELL, _state(_entity(state)))
        assert _HERO.findall(fragment) == ["--"]
        # No "%" annotation on a value there is none of.
        assert _CHIP.findall(fragment) == ["--"]

    @pytest.mark.parametrize("state", ABSENT)
    def test_bar_draws_no_progress(self, state: str) -> None:
        widget = _progress(target=100)
        fragment = widget.render_html(CELL, _state(_entity(state)))
        assert _FILL.findall(fragment) == ["0.0"]

    def test_an_absent_reading_takes_no_sibling_size(self) -> None:
        widget = _progress(target=100)
        assert widget.hero_hint(CELL, _state(_entity("unavailable"))) is None

    def test_a_real_zero_is_still_a_reading(self) -> None:
        widget = _progress(target=100)
        fragment = widget.render_html(CELL, _state(_entity("0")))
        assert _HERO.findall(fragment) == ["0"]
        assert _CHIP.findall(fragment) == ["0 of 100 %"]

    def test_no_entity_is_a_bar_nothing_counted_toward(self) -> None:
        # A widget with no entity configured is not a dead sensor: it is a
        # goal nothing has been counted against yet, and 0 % is the truth.
        widget = ProgressWidget(
            WidgetConfig(widget_type="progress", slot=0, options={"target": 100})
        )
        fragment = widget.render_html(CELL, _state(None))
        assert _HERO.findall(fragment) == ["0"]


def test_reading_of_never_returns_a_non_finite_float() -> None:
    """A NaN/inf state must not reach ``calculate_percent``.

    ``width: nan%`` is invalid CSS: the fill div falls back to its natural
    width and paints the whole track.
    """
    for state in ("nan", "NaN", "inf", "-Infinity"):
        value = reading_of(_entity(state))
        assert value is None
    assert math.isfinite(reading_of(_entity("42")) or math.nan)
