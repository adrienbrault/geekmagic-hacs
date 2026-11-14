"""Status List entries in every shape the config can hold (issue #183).

The panel editor saves Status List rows as objects
(``{"entity_id", "label"?, "icon"?}``), while older configs hold bare
entity ids or ``[entity_id, label]`` pairs. The widget used to understand
only the latter two: an editor-made list handed a dict to
``build_entity_states`` (``TypeError: unhashable type: 'dict'``), which
took the whole screen offline on the device and failed the preview.
These tests drive editor-shaped options through every reader.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from custom_components.geekmagic.const import LAYOUT_GRID_2X2
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.icons import get_mdi_char
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.preview import (
    MockHass,
    _build_widget_state_for_preview,
    render_preview,
)
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.websocket import _build_preview_widget_states
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.state import (
    EntityState,
    WidgetState,
    build_entity_states,
)
from custom_components.geekmagic.widgets.status import (
    StatusEntry,
    StatusListWidget,
    normalize_status_entries,
)
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)

# Exactly what the panel editor stores for a two-row list: one row with a
# label and an icon override, one with only an entity picked (the editor
# leaves the untouched fields out, or as "" once they were edited).
PANEL_ENTITIES: list[dict[str, Any]] = [
    {"entity_id": "binary_sensor.garage_door", "label": "Garage", "icon": "mdi:garage"},
    {"entity_id": "binary_sensor.back_door", "label": "", "icon": ""},
]


def _glyph(icon: str) -> str:
    """The HTML character reference ``mdi_span`` emits for ``icon``."""
    return f"&#x{ord(get_mdi_char(icon)):X};"


def _widget(entities: Any) -> StatusListWidget:
    return StatusListWidget(
        WidgetConfig(
            widget_type="status_list", slot=0, options={"title": "Doors", "entities": entities}
        )
    )


def _mock_hass() -> Any:
    hass = cast("Any", MockHass())
    hass.states.set(
        "binary_sensor.garage_door",
        "on",
        {"friendly_name": "Garage Door", "device_class": "garage_door"},
    )
    hass.states.set(
        "binary_sensor.back_door",
        "off",
        {"friendly_name": "Back Door", "device_class": "door"},
    )
    return hass


def _no_render_errors(caplog: pytest.LogCaptureFixture) -> None:
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], [r.getMessage() for r in errors]


class TestNormalizeStatusEntries:
    """Every stored shape parses to the same rows; junk is skipped."""

    def test_panel_objects(self):
        assert normalize_status_entries(PANEL_ENTITIES) == [
            StatusEntry("binary_sensor.garage_door", "Garage", "mdi:garage"),
            StatusEntry("binary_sensor.back_door"),
        ]

    def test_legacy_strings_and_pairs(self):
        assert normalize_status_entries(
            ["binary_sensor.front_door", ["binary_sensor.back_door", "Back"]]
        ) == [
            StatusEntry("binary_sensor.front_door"),
            StatusEntry("binary_sensor.back_door", "Back"),
        ]

    def test_mixed_formats(self):
        assert normalize_status_entries(
            [
                "light.porch",
                ("light.hall", "Hall"),
                {"entity_id": "light.desk", "icon": "mdi:desk-lamp"},
            ]
        ) == [
            StatusEntry("light.porch"),
            StatusEntry("light.hall", "Hall"),
            StatusEntry("light.desk", icon="mdi:desk-lamp"),
        ]

    @pytest.mark.parametrize(
        "junk",
        [
            {"entity_id": ""},  # the row the editor's "Add" creates
            {"entity_id": None},  # a cleared selector
            {"label": "No entity"},
            {"entity_id": {"nested": "dict"}},
            [],
            [None, "Label"],
            "",
            "   ",
            None,
            42,
        ],
    )
    def test_malformed_entries_skipped(self, junk):
        assert normalize_status_entries([junk, "light.ok"]) == [StatusEntry("light.ok")]

    def test_single_element_pair(self):
        assert normalize_status_entries([["light.ok"]]) == [StatusEntry("light.ok")]

    @pytest.mark.parametrize("raw", [None, "light.ok", {"entity_id": "light.ok"}, 3])
    def test_non_list_option(self, raw):
        assert normalize_status_entries(raw) == []


class TestPanelShapedStatusList:
    """Editor-made lists resolve, render, and keep their overrides."""

    def test_get_entities_returns_ids(self):
        assert _widget(PANEL_ENTITIES).get_entities() == [
            "binary_sensor.garage_door",
            "binary_sensor.back_door",
        ]

    def test_build_entity_states_resolves_rows(self):
        """The production/preview snapshot sees every row (TypeError on main)."""
        _, additional = build_entity_states(_mock_hass().states.get, _widget(PANEL_ENTITIES))
        assert set(additional) == {"binary_sensor.garage_door", "binary_sensor.back_door"}

    def test_render_labels_states_and_icon_override(self):
        widget = _widget(PANEL_ENTITIES)
        _, additional = build_entity_states(_mock_hass().states.get, widget)
        fragment = widget.render_html(CTX, _state(additional))

        assert "Garage" in fragment  # configured label
        assert "Garage Door" not in fragment  # ... beats the friendly name
        assert "Back Door" in fragment  # blank label falls back to the friendly name
        assert "Open" in fragment  # garage_door "on"
        assert "Closed" in fragment  # door "off"
        assert _glyph("mdi:garage") in fragment  # the row's icon override ...
        assert _glyph("mdi:garage-open") not in fragment  # ... replaces the derived glyph
        # The back door has no override: its derived closed-door glyph shows.
        assert _glyph("mdi:door-closed") in fragment

    def test_override_icon_keeps_state_tint(self):
        widget = _widget([{"entity_id": "binary_sensor.garage_door", "icon": "mdi:garage"}])
        _, additional = build_entity_states(_mock_hass().states.get, widget)
        fragment = widget.render_html(CTX, _state(additional))
        glyph_at = fragment.index(_glyph("mdi:garage"))
        span_start = fragment.rindex("<span", 0, glyph_at)
        assert "color: var(--success)" in fragment[span_start:glyph_at]

    def test_unknown_override_icon_falls_back_to_derived(self):
        widget = _widget([{"entity_id": "binary_sensor.back_door", "icon": "mdi:not-a-glyph"}])
        _, additional = build_entity_states(_mock_hass().states.get, widget)
        fragment = widget.render_html(CTX, _state(additional))
        assert _glyph("mdi:door-closed") in fragment

    def test_freshly_added_empty_row_renders_placeholder(self):
        """The editor's "Add" saves ``[{"entity_id": ""}]`` before a pick."""
        widget = _widget([{"entity_id": ""}])
        assert widget.get_entities() == []
        fragment = widget.render_html(CTX, _state({}))
        assert "DOORS" in fragment


def _state(entities: dict[str, EntityState]) -> WidgetState:
    return WidgetState(entities=entities, now=datetime(2025, 12, 29, tzinfo=UTC))


class TestRenderPaths:
    """The full device, websocket-preview and config-flow-preview paths."""

    async def test_coordinator_states_and_layout_render(self, hass, caplog):
        """Device path: the frame builds and the cell renders without error."""
        hass.states.async_set(
            "binary_sensor.garage_door",
            "on",
            {"friendly_name": "Garage Door", "device_class": "garage_door"},
        )
        hass.states.async_set(
            "binary_sensor.back_door", "off", {"friendly_name": "Back Door", "device_class": "door"}
        )
        layout = Grid2x2()
        layout.set_widget(0, _widget(PANEL_ENTITIES))
        coordinator = GeekMagicCoordinator(hass, MagicMock(), {})

        states = await hass.async_add_executor_job(coordinator._build_widget_states, layout)
        assert set(states[0].entities) == {"binary_sensor.garage_door", "binary_sensor.back_door"}

        renderer = Renderer()
        img, draw = renderer.create_canvas()
        before = img.tobytes()
        await hass.async_add_executor_job(layout.render, renderer, draw, states)
        assert img.tobytes() != before
        _no_render_errors(caplog)

    def test_websocket_preview_states(self):
        states = _build_preview_widget_states(
            _mock_hass(), {0: _widget(PANEL_ENTITIES)}, {}, {}, {}
        )
        assert set(states[0].entities) == {"binary_sensor.garage_door", "binary_sensor.back_door"}

    def test_config_flow_preview(self, caplog):
        config = {"type": "status_list", "slot": 0, "options": {"entities": PANEL_ENTITIES}}
        state = _build_widget_state_for_preview(config, _mock_hass())
        assert set(state.entities) == {"binary_sensor.garage_door", "binary_sensor.back_door"}

        png = render_preview(LAYOUT_GRID_2X2, [config])
        assert png.startswith(b"\x89PNG")
        _no_render_errors(caplog)
