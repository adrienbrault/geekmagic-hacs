"""Compact-cell identity regressions for status, progress and attribute list.

Small cells must keep what names them — caption, row label, icon — by
shrinking type down to the 10px floor instead of shedding whole bands.
Where Python decides a band survives, the fragment must NOT carry the
kit's ``hide-*`` classes: those media rules would re-hide the very row
the widget shrank for.

Fragments are asserted on substrings, never full-string equality.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.attribute_list import AttributeListWidget
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget, StatusWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

FIXED_NOW = datetime(2025, 12, 29, 13, 45, 30, tzinfo=UTC)

# Real slot sizes: a 3x3 grid cell, a hero-layout footer, a split column.
GRID_3X3 = (69, 65)
FOOTER = (108, 69)
COLUMN = (69, 224)


def make_entity(
    entity_id: str = "sensor.temperature",
    state: str = "23.5",
    attributes: dict[str, Any] | None = None,
) -> EntityState:
    """Build an EntityState snapshot."""
    return EntityState(entity_id=entity_id, state=state, attributes=attributes or {})


def make_state(
    entity: EntityState | None = None,
    entities: dict[str, EntityState] | None = None,
) -> WidgetState:
    """Build a WidgetState for testing."""
    return WidgetState(
        entity=entity,
        entities=entities or {},
        history=[],
        forecast=[],
        image=None,
        now=FIXED_NOW,
    )


def cell(width: int, height: int) -> CellContext:
    """Cell context of an arbitrary size."""
    return CellContext(width=width, height=height, slot_index=0, theme=DEFAULT_THEME)


@pytest.fixture
def door():
    """An open door binary sensor."""
    return make_entity(
        "binary_sensor.front_door", "on", {"friendly_name": "Front Door", "device_class": "door"}
    )


def font_px(fragment: str, marker: str) -> float:
    """Pixel size declared on the element that holds ``marker``."""
    head = fragment[: fragment.index(marker)]
    start = head.rindex("<div")
    tag = head[start : head.index(">", start) + 1]
    return float(tag.split("font-size: ")[1].split("px")[0])


# ============================================================================
# StatusWidget — compact cells keep an identity row (S1)
# ============================================================================


class TestStatusCompactIdentity:
    """A 3x3 slot showing a bare "OPEN" names nothing."""

    def test_compact_cell_keeps_name_and_icon(self, door):
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.front_door",
                options={"on_text": "OPEN"},
            )
        )
        fragment = widget.render_html(cell(*GRID_3X3), make_state(door))
        assert ">OPEN<" in fragment  # the state is still the hero
        # ...but the cell says what is open. Truncation still PREFERS
        # the form that keeps the short discriminating last word ("FRO…
        # DOOR" beats "FRONT…"), and now takes it only where that form
        # measures inside the band — at this size it is 13px wider than
        # the caption's budget, so the head-kept "FRONT D…" lands
        # instead. It still separates FRO…/BAC… pairs, and it no longer
        # bleeds past the cell.
        # Asserted on the FITTED string: "FRONT" alone would also pass on
        # an untruncated "FRONT DOOR", which is the overflow this guards.
        assert ">FRONT D…<" in fragment
        assert "icon" in fragment  # glyph present (stacked chip at this height)

    def test_compact_identity_is_not_hidden_by_the_kit(self, door):
        """Python decided the row survives — hide-short would undo that."""
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.front_door")
        )
        fragment = widget.render_html(cell(*GRID_3X3), make_state(door))
        assert "hide-short" not in fragment

    def test_compact_identity_shrinks_to_the_floor(self, door):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.front_door")
        )
        fragment = widget.render_html(cell(*GRID_3X3), make_state(door))
        assert font_px(fragment, "FRO") <= 10.0

    def test_stack_bands_are_not_hidden_below_the_kit_breakpoint(self, door):
        """A 96px cell is sized for its chip and caption — and keeps them."""
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.front_door")
        )
        fragment = widget.render_html(cell(96, 96), make_state(door))
        assert "FRONT DOOR" in fragment
        assert "card-icon" in fragment
        assert "hide-short" not in fragment

    def test_icon_only_short_cell_keeps_caption(self, door):
        """show_status_text=False: the lozenge still needs a label."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.front_door",
                options={"show_status_text": False},
            )
        )
        fragment = widget.render_html(cell(*FOOTER), make_state(door))
        assert "FRONT DOOR" in fragment
        assert "hide-short" not in fragment


# ============================================================================
# StatusListWidget — title and per-row state in narrow cells (S4, S5)
# ============================================================================


class TestStatusListNarrowCells:
    """A narrow column still has to say what it is listing."""

    @staticmethod
    def _widget() -> StatusListWidget:
        return StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "title": "Doors",
                    "entities": ["binary_sensor.front_door", "binary_sensor.garage"],
                },
            )
        )

    @staticmethod
    def _entities() -> dict[str, EntityState]:
        return {
            "binary_sensor.front_door": make_entity(
                "binary_sensor.front_door",
                "on",
                {"friendly_name": "Front Door", "device_class": "door"},
            ),
            "binary_sensor.garage": make_entity(
                "binary_sensor.garage",
                "off",
                {"friendly_name": "Garage", "device_class": "garage_door"},
            ),
        }

    def test_title_survives_a_narrow_column(self):
        fragment = self._widget().render_html(cell(*COLUMN), make_state(entities=self._entities()))
        assert "DOORS" in fragment

    def test_title_yields_to_the_row_budget(self):
        """Two rows in a 40px cell have no pitch to spare for a heading."""
        fragment = self._widget().render_html(cell(69, 40), make_state(entities=self._entities()))
        assert "DOORS" not in fragment

    def test_state_degrades_to_bare_text_before_it_disappears(self):
        """Mid-size cells drop the pill's padding, not the state itself."""
        fragment = self._widget().render_html(cell(160, 120), make_state(entities=self._entities()))
        assert "Open" in fragment
        assert "Closed" in fragment
        assert 'class="chip"' not in fragment

    def test_wide_cells_keep_the_filled_pill(self):
        fragment = self._widget().render_html(cell(240, 240), make_state(entities=self._entities()))
        assert 'class="chip"' in fragment


# ============================================================================
# ProgressWidget — the caption band carries the icon too (P1, P2)
# ============================================================================


class TestProgressCompactCaption:
    """hide-short took the name AND the tint off every short cell."""

    @staticmethod
    def _widget() -> ProgressWidget:
        return ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                label="Daily Steps",
                options={"target": 10000, "icon": "walk"},
            )
        )

    def test_footer_cell_keeps_caption_and_icon(self):
        fragment = self._widget().render_html(
            cell(*FOOTER), make_state(make_entity("sensor.steps", "5000"))
        )
        assert "DAILY STEPS" in fragment
        # From ~64px of height the icon stacks above the caption.
        assert "card-icon" in fragment or 'class="icon i-sm"' in fragment
        assert "hide-short" not in fragment

    def test_caption_shrinks_before_it_truncates(self):
        """A whole "DAILY STEPS" at 11px beats "DAIL…" at the kit size."""
        fragment = self._widget().render_html(
            cell(120, 70), make_state(make_entity("sensor.steps", "5000"))
        )
        assert "DAILY STEPS" in fragment
        assert font_px(fragment, "DAILY STEPS") <= 12.0

    def test_cell_too_short_for_a_caption_drops_it(self):
        fragment = self._widget().render_html(
            cell(108, 40), make_state(make_entity("sensor.steps", "5000"))
        )
        assert "DAILY" not in fragment


# ============================================================================
# MultiProgressWidget — row labels and title (P4, P5)
# ============================================================================


class TestMultiProgressCompactRows:
    """Bars with no labels are a stack of anonymous colours."""

    @staticmethod
    def _widget() -> MultiProgressWidget:
        return MultiProgressWidget(
            WidgetConfig(
                widget_type="multi_progress",
                slot=0,
                options={
                    "title": "Fitness",
                    "items": [
                        {
                            "entity_id": "sensor.steps",
                            "target": 10000,
                            "label": "Steps",
                            "icon": "walk",
                        },
                        {"entity_id": "sensor.cal", "target": 500, "label": "Cal"},
                    ],
                },
            )
        )

    @staticmethod
    def _entities() -> dict[str, EntityState]:
        return {
            "sensor.steps": make_entity("sensor.steps", "5000"),
            "sensor.cal": make_entity("sensor.cal", "300"),
        }

    def test_short_cell_keeps_row_labels(self):
        fragment = self._widget().render_html(
            cell(*GRID_3X3), make_state(entities=self._entities())
        )
        assert "STEPS" in fragment
        assert "CAL" in fragment
        assert "50%" in fragment

    def test_short_cell_labels_are_not_hidden_by_the_kit(self):
        fragment = self._widget().render_html(
            cell(*GRID_3X3), make_state(entities=self._entities())
        )
        assert "hide-short" not in fragment

    def test_short_cell_drops_the_raw_value_not_the_label(self):
        fragment = self._widget().render_html(
            cell(*GRID_3X3), make_state(entities=self._entities())
        )
        assert "5000/10000" not in fragment

    def test_narrow_tall_cell_keeps_the_title(self):
        """The title answers to the height it costs, not the short side."""
        fragment = self._widget().render_html(cell(*COLUMN), make_state(entities=self._entities()))
        assert "FITNESS" in fragment

    def test_title_yields_when_rows_would_be_crushed(self):
        fragment = self._widget().render_html(
            cell(*GRID_3X3), make_state(entities=self._entities())
        )
        assert "FITNESS" not in fragment


# ============================================================================
# AttributeListWidget — per-row labels and the lone title (A1, A2, A3)
# ============================================================================


class TestAttributeListCompactRows:
    """One long attribute name used to strip every row's caption."""

    @staticmethod
    def _widget(**options: Any) -> AttributeListWidget:
        base: dict[str, Any] = {
            "title": "Bus Info",
            "attributes": [
                {"key": "route_name", "label": "Route"},
                {"key": "destination", "label": "Destination"},
                {"key": "state", "label": "Arrives"},
            ],
        }
        base.update(options)
        return AttributeListWidget(
            WidgetConfig(widget_type="attribute_list", slot=0, entity_id="sensor.bus", options=base)
        )

    @staticmethod
    def _entity() -> EntityState:
        return make_entity(
            "sensor.bus",
            "5 min",
            {"friendly_name": "Bus 42", "route_name": "42", "destination": "Downtown"},
        )

    def test_short_labels_survive_a_long_neighbour(self):
        """ROUTE fits even when DESTINATION cannot — labels are per-row."""
        fragment = self._widget().render_html(cell(*GRID_3X3), make_state(self._entity()))
        assert "ROUTE" in fragment
        assert ">42<" in fragment

    def test_narrow_cell_stacks_label_over_whole_value(self):
        """Narrow cells stack the label ABOVE the value, each taking the
        full width — "Downtown" renders whole at the size the width
        affords instead of truncating beside a cramped label."""
        fragment = self._widget().render_html(cell(111, 108), make_state(self._entity()))
        assert "Downtown" in fragment
        assert "Dow…" not in fragment
        assert "DESTINATION" in fragment

    def test_title_survives_a_narrow_cell(self):
        fragment = self._widget().render_html(cell(*GRID_3X3), make_state(self._entity()))
        assert "BUS INFO" in fragment

    def test_no_attributes_always_renders_the_title(self):
        """The title IS the widget here — a width gate left a blank cell."""
        widget = self._widget(attributes=[], title=None)
        fragment = widget.render_html(cell(*GRID_3X3), make_state(self._entity()))
        assert "BUS 42" in fragment

    def test_no_attributes_narrow_column_renders_the_title(self):
        widget = self._widget(attributes=[], title=None)
        fragment = widget.render_html(cell(*COLUMN), make_state(self._entity()))
        assert "BUS 42" in fragment


class TestStackedFeatureIcon:
    """Tall cells promote the icon to its own band above the caption
    (the entity card's feature pattern); the inline chip row is only the
    short-cell fallback."""

    def test_progress_tall_cell_stacks_icon(self):
        widget = ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                label="Steps",
                options={"icon": "walk"},
            )
        )
        entity = EntityState(entity_id="sensor.steps", state="8500", attributes={"max": "10000"})
        state = WidgetState(entity=entity, now=FIXED_NOW)
        tall = CellContext(width=69, height=108, slot_index=0, theme=DEFAULT_THEME)
        assert "card-icon" in widget.render_html(tall, state)
        # 69px still stacks (the old design stacked 3x3 tiles); only a
        # band with no vertical room keeps the inline row.
        short = CellContext(width=108, height=69, slot_index=0, theme=DEFAULT_THEME)
        assert "card-icon" in widget.render_html(short, state)
        very_short = CellContext(width=108, height=56, slot_index=0, theme=DEFAULT_THEME)
        assert "card-icon" not in widget.render_html(very_short, state)

    def test_status_tall_narrow_cell_uses_stack(self):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door", label="Door")
        )
        entity = EntityState(
            entity_id="binary_sensor.door", state="on", attributes={"device_class": "door"}
        )
        state = WidgetState(entity=entity, now=FIXED_NOW)
        tall = CellContext(width=69, height=108, slot_index=0, theme=DEFAULT_THEME)
        assert "card-icon" in widget.render_html(tall, state)
