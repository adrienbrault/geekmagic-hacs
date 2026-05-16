"""Tests for the widget_state_builder module."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.widget_state_builder import (
    PrefetchedData,
    build_widget_states,
)
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.chart import ChartWidget
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.entity import EntityWidget


def _make_hass(states: dict[str, MagicMock] | None = None):
    resolved = states or {}
    hass = MagicMock()
    hass.config.time_zone_obj = None
    hass.states.get = resolved.get
    return hass


def _ha_state(entity_id: str, state: str, attributes: dict | None = None):
    s = MagicMock()
    s.entity_id = entity_id
    s.state = state
    s.attributes = attributes or {}
    return s


class TestBuildWidgetStates:
    def test_empty_layout_returns_empty(self):
        layout = Grid2x2()
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states == {}

    def test_widget_with_no_entity_gets_state_with_none_entity(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert states[0].entity is None
        assert states[0].now is not None

    def test_widget_resolves_primary_entity_from_hass(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22", {"unit": "°C"})})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert states[0].entity is not None
        assert states[0].entity.state == "22"

    def test_chart_widget_pulls_history_from_prefetched(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(chart_history={"sensor.temp": [1.0, 2.0, 3.0]}),
        )
        assert states[0].history == [1.0, 2.0, 3.0]

    def test_chart_widget_without_history_gets_empty_list(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(layout, hass, PrefetchedData())
        assert states[0].history == []

    def test_non_chart_widget_ignores_chart_history(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp")),
        )
        hass = _make_hass({"sensor.temp": _ha_state("sensor.temp", "22")})
        states = build_widget_states(
            layout,
            hass,
            PrefetchedData(chart_history={"sensor.temp": [99.0]}),
        )
        assert states[0].history == []

    def test_empty_slot_is_skipped(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        # Slots 1, 2, 3 left empty
        states = build_widget_states(layout, _make_hass(), PrefetchedData())
        assert list(states.keys()) == [0]
