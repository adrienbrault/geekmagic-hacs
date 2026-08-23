"""Tests for widget classes (HTML fragment rendering contract).

Widgets return HTML fragment strings from ``render_html(ctx, state)``.
Tests assert on fragment substrings (values, classes, CSS variables) —
never exact full-string equality — so styling tweaks don't break them.
Blitz rasterization is deliberately NOT exercised here (pipeline render
tests live elsewhere).
"""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from PIL import Image

from custom_components.geekmagic.const import COLOR_CYAN
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.widgets.attribute_list import AttributeListWidget
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.chart import (
    ChartWidget,
    _format_period,
    _is_binary_data,
)
from custom_components.geekmagic.widgets.climate import ClimateWidget, _format_temp
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.gauge import GaugeWidget
from custom_components.geekmagic.widgets.helpers import (
    calculate_percent,
    format_number,
    format_value_with_unit,
    get_binary_sensor_icon,
    get_domain_state_icon,
    parse_color,
    translate_binary_state,
    truncate_text,
)
from custom_components.geekmagic.widgets.icon import IconWidget
from custom_components.geekmagic.widgets.media import MediaWidget, _format_time
from custom_components.geekmagic.widgets.progress import MultiProgressWidget, ProgressWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.status import StatusListWidget, StatusWidget
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from custom_components.geekmagic.widgets.weather import WeatherWidget, _fmt_num

# A Monday, so date strings are deterministic ("Mon, Dec 29").
FIXED_NOW = datetime(2025, 12, 29, 13, 45, 30, tzinfo=UTC)


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
    history: list[float] | None = None,
    forecast: list[dict[str, Any]] | None = None,
    image: Image.Image | None = None,
) -> WidgetState:
    """Build a WidgetState for testing."""
    return WidgetState(
        entity=entity,
        entities=entities or {},
        history=history or [],
        forecast=forecast or [],
        image=image,
        now=FIXED_NOW,
    )


@pytest.fixture
def ctx():
    """Fullscreen cell context (240x240)."""
    return CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


@pytest.fixture
def compact_ctx():
    """Compact 3x3-grid-sized cell context."""
    return CellContext(width=74, height=71, slot_index=0, theme=DEFAULT_THEME)


# ============================================================================
# Helper functions (pure)
# ============================================================================


class TestTranslateBinaryState:
    """Tests for translate_binary_state helper."""

    def test_door_sensor_on(self):
        assert translate_binary_state("on", "door") == "Open"

    def test_door_sensor_off(self):
        assert translate_binary_state("off", "door") == "Closed"

    def test_motion_sensor_on(self):
        assert translate_binary_state("on", "motion") == "Detected"

    def test_motion_sensor_off(self):
        assert translate_binary_state("off", "motion") == "Clear"

    def test_window_sensor(self):
        assert translate_binary_state("on", "window") == "Open"
        assert translate_binary_state("off", "window") == "Closed"

    def test_lock_sensor(self):
        """Lock is inverted: on = unlocked."""
        assert translate_binary_state("on", "lock") == "Unlocked"
        assert translate_binary_state("off", "lock") == "Locked"

    def test_connectivity_sensor(self):
        assert translate_binary_state("on", "connectivity") == "Connected"
        assert translate_binary_state("off", "connectivity") == "Disconnected"

    def test_no_device_class(self):
        assert translate_binary_state("on", None) == "on"
        assert translate_binary_state("off", None) == "off"

    def test_unknown_device_class(self):
        assert translate_binary_state("on", "unknown_class") == "on"
        assert translate_binary_state("off", "unknown_class") == "off"

    def test_case_insensitive(self):
        assert translate_binary_state("ON", "door") == "Open"
        assert translate_binary_state("Off", "door") == "Closed"

    def test_other_states_unchanged(self):
        assert translate_binary_state("unavailable", "door") == "unavailable"
        assert translate_binary_state("unknown", "motion") == "unknown"


class TestBinarySensorIcons:
    """Tests for get_binary_sensor_icon helper - reads from HA JSON files."""

    def test_door_sensor_icons(self):
        assert get_binary_sensor_icon("on", "door") == "mdi:door-open"
        assert get_binary_sensor_icon("off", "door") == "mdi:door-closed"

    def test_motion_sensor_icons(self):
        assert get_binary_sensor_icon("on", "motion") == "mdi:motion-sensor"
        assert get_binary_sensor_icon("off", "motion") == "mdi:motion-sensor-off"

    def test_window_sensor_icons(self):
        assert get_binary_sensor_icon("on", "window") == "mdi:window-open"
        assert get_binary_sensor_icon("off", "window") == "mdi:window-closed"

    def test_lock_sensor_icons(self):
        assert get_binary_sensor_icon("on", "lock") == "mdi:lock-open"
        assert get_binary_sensor_icon("off", "lock") == "mdi:lock"

    def test_connectivity_icons(self):
        assert get_binary_sensor_icon("on", "connectivity") == "mdi:check-network-outline"
        assert get_binary_sensor_icon("off", "connectivity") == "mdi:close-network-outline"

    def test_no_device_class_returns_none(self):
        assert get_binary_sensor_icon("on", None) is None
        assert get_binary_sensor_icon("off", None) is None

    def test_unknown_device_class_returns_none(self):
        assert get_binary_sensor_icon("on", "nonexistent_class") is None

    def test_case_insensitive(self):
        assert get_binary_sensor_icon("ON", "door") == "mdi:door-open"
        assert get_binary_sensor_icon("Off", "door") == "mdi:door-closed"


class TestDomainStateIcons:
    """Tests for get_domain_state_icon helper - reads from HA JSON files."""

    def test_light_on_off_icons(self):
        assert get_domain_state_icon("light", "on") == "mdi:lightbulb"
        assert get_domain_state_icon("light", "off") == "mdi:lightbulb-off"

    def test_switch_on_off_icons(self):
        assert get_domain_state_icon("switch", "on") == "mdi:toggle-switch-variant"
        assert get_domain_state_icon("switch", "off") == "mdi:toggle-switch-variant-off"

    def test_fan_on_off_icons(self):
        assert get_domain_state_icon("fan", "on") == "mdi:fan"
        assert get_domain_state_icon("fan", "off") == "mdi:fan-off"

    def test_lock_state_icons(self):
        assert get_domain_state_icon("lock", "locked") == "mdi:lock"
        assert get_domain_state_icon("lock", "unlocked") == "mdi:lock-open-variant"

    def test_unknown_domain_returns_none(self):
        assert get_domain_state_icon("nonexistent_domain", "on") is None

    def test_case_insensitive(self):
        assert get_domain_state_icon("light", "OFF") == "mdi:lightbulb-off"
        assert get_domain_state_icon("switch", "On") == "mdi:toggle-switch-variant"


class TestParseColor:
    """Tests for parse_color helper function."""

    def test_parse_tuple(self):
        assert parse_color((255, 128, 0), (0, 0, 0)) == (255, 128, 0)

    def test_parse_list(self):
        result = parse_color([255, 128, 0], (0, 0, 0))
        assert result == (255, 128, 0)
        assert isinstance(result, tuple)

    def test_parse_list_with_strings(self):
        assert parse_color(["255", "128", "0"], (0, 0, 0)) == (255, 128, 0)

    def test_parse_none_returns_default(self):
        default = (100, 100, 100)
        assert parse_color(None, default) == default

    def test_parse_invalid_list_returns_default(self):
        default = (100, 100, 100)
        assert parse_color([255, 128], default) == default
        assert parse_color([255, 128, 0, 255], default) == default
        assert parse_color(["invalid", "values", "here"], default) == default

    def test_parse_invalid_type_returns_default(self):
        default = (100, 100, 100)
        assert parse_color("red", default) == default
        assert parse_color(12345, default) == default
        assert parse_color({"r": 255, "g": 128, "b": 0}, default) == default


class TestTruncateText:
    """Tests for truncate_text helper."""

    def test_short_text_unchanged(self):
        assert truncate_text("hello", 10) == "hello"

    def test_end_truncation(self):
        assert truncate_text("very long text", 9) == "very lon…"

    def test_middle_truncation(self):
        result = truncate_text("very long text", 9, style="middle")
        assert len(result) == 9
        assert "…" in result
        assert result.startswith("very")
        assert result.endswith("ext")

    def test_start_truncation(self):
        result = truncate_text("very long text", 9, style="start")
        assert result.startswith("…")
        assert result.endswith("ng text")

    def test_no_trailing_space_before_ellipsis(self):
        """ "SWITCH …" reads as a floating dot-dot-dot — strip the space."""
        assert truncate_text("SWITCH ON", 8) == "SWITCH…"


class TestCalculatePercent:
    """Tests for calculate_percent helper."""

    def test_basic_percent(self):
        assert calculate_percent(50, 0, 100) == 50.0

    def test_clamped_high(self):
        assert calculate_percent(150, 0, 100) == 100.0

    def test_clamped_low(self):
        assert calculate_percent(-10, 0, 100) == 0.0

    def test_custom_range(self):
        assert calculate_percent(30, 10, 50) == 50.0

    def test_zero_range(self):
        assert calculate_percent(50, 100, 100) == 0.0


class TestFormatHelpers:
    """Tests for format_number / format_value_with_unit helpers."""

    def test_format_number_small(self):
        assert format_number(500) == "500"
        assert format_number(42.5) == "42.5"

    def test_format_number_abbreviations(self):
        assert format_number(1000) == "1k"
        assert format_number(1500) == "1.5k"
        assert format_number(1_000_000) == "1M"
        assert format_number(1_500_000_000) == "1.5B"

    def test_format_number_negative(self):
        assert format_number(-1500) == "-1.5k"

    def test_format_number_non_numeric_string(self):
        assert format_number("abc") == "abc"

    def test_format_value_with_unit(self):
        assert format_value_with_unit("23.5", "°C") == "23.5°C"
        assert format_value_with_unit("42", "") == "42"

    def test_format_value_with_unit_abbreviated(self):
        assert format_value_with_unit(1500, " views", abbreviate=True) == "1.5k views"


# ============================================================================
# WidgetConfig
# ============================================================================


class TestWidgetConfig:
    """Tests for WidgetConfig."""

    def test_create_config(self):
        config = WidgetConfig(widget_type="clock", slot=0)
        assert config.widget_type == "clock"
        assert config.slot == 0
        assert config.entity_id is None

    def test_create_config_with_options(self):
        config = WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.temp",
            label="Temperature",
            color=COLOR_CYAN,
            options={"show_name": True},
        )
        assert config.entity_id == "sensor.temp"
        assert config.label == "Temperature"
        assert config.color == COLOR_CYAN
        assert config.options["show_name"] is True


# ============================================================================
# ClockWidget
# ============================================================================


class TestClockWidget:
    """Tests for ClockWidget."""

    def test_init(self):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        assert widget.show_date is True
        assert widget.show_seconds is False

    def test_init_with_options(self):
        widget = ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=0,
                options={"show_date": False, "show_seconds": True, "time_format": "12h"},
            )
        )
        assert widget.show_date is False
        assert widget.show_seconds is True
        assert widget.time_format == "12h"

    def test_get_entities(self):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        assert widget.get_entities() == []

    def test_render_24h(self, ctx):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        fragment = widget.render_html(ctx, make_state())
        assert "13:45" in fragment
        assert "t-hero" in fragment

    def test_render_12h(self, ctx):
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, options={"time_format": "12h"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "01:45" in fragment
        assert "PM" in fragment

    def test_render_seconds(self, ctx):
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, options={"show_seconds": True})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "13:45:30" in fragment

    def test_render_date_chip(self, ctx):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        fragment = widget.render_html(ctx, make_state())
        assert "Mon, Dec 29" in fragment
        assert "chip" in fragment

    def test_show_date_off_drops_date(self, ctx):
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, options={"show_date": False})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "Dec 29" not in fragment

    def test_label_renders_caption(self, ctx):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, label="Bedroom"))
        fragment = widget.render_html(ctx, make_state())
        assert "BEDROOM" in fragment

    def test_color_option_tints_hero(self, ctx):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, color=(255, 0, 0)))
        fragment = widget.render_html(ctx, make_state())
        assert "rgb(255, 0, 0)" in fragment

    def test_render_compact(self, compact_ctx):
        """Compact cells render the same fragment (CSS sheds the bands)."""
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        fragment = widget.render_html(compact_ctx, make_state())
        assert "13:45" in fragment

    def test_short_cell_keeps_label(self):
        """A 'Tokyo' and a 'London' clock in one grid must not render
        identically — the label survives short cells at a shrunk size."""
        footer = CellContext(width=228, height=76, slot_index=0, theme=DEFAULT_THEME)
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, label="Tokyo"))
        fragment = widget.render_html(footer, make_state())
        assert "TOKYO" in fragment
        assert "hide-short" not in fragment

    def test_tall_column_keeps_meridiem(self):
        """A 71x228 column has height to spare — a 12h clock without
        AM/PM is unreadable as a 12h clock."""
        column = CellContext(width=71, height=228, slot_index=0, theme=DEFAULT_THEME)
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, options={"time_format": "12h"})
        )
        fragment = widget.render_html(column, make_state())
        assert "PM" in fragment

    def test_seconds_stack_in_tall_cells(self):
        """HH/MM/SS stack in tall columns instead of one collapsed line."""
        column = CellContext(width=111, height=228, slot_index=0, theme=DEFAULT_THEME)
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, options={"show_seconds": True})
        )
        fragment = widget.render_html(column, make_state())
        assert fragment.count("<div>") >= 3  # one block per stacked line


# ============================================================================
# EntityWidget
# ============================================================================


class TestEntityWidget:
    """Tests for EntityWidget."""

    def test_init(self):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temperature")
        )
        assert widget.show_name is True
        assert widget.show_unit is True

    def test_get_entities(self):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temperature")
        )
        assert widget.get_entities() == ["sensor.temperature"]

    def test_render_without_entity_shows_placeholder(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temperature")
        )
        fragment = widget.render_html(ctx, make_state())
        assert "--" in fragment

    def test_render_with_entity(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temperature")
        )
        entity = make_entity(
            attributes={"friendly_name": "Temperature", "unit_of_measurement": "°C"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        # Value and unit are split typographically: fitted digits, with
        # the unit smaller and secondary on the same baseline.
        assert ">23.5<" in fragment
        assert 't-unit" style="font-size: 0.46em' in fragment
        assert ">°C</span>" in fragment
        assert "TEMPERATURE" in fragment  # caption is uppercased

    def test_render_door_sensor_shows_open(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="binary_sensor.front_door")
        )
        entity = make_entity(
            "binary_sensor.front_door",
            "on",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Open<" in fragment

    def test_render_door_sensor_shows_closed(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="binary_sensor.front_door")
        )
        entity = make_entity(
            "binary_sensor.front_door",
            "off",
            {"friendly_name": "Front Door", "device_class": "door"},
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Closed<" in fragment

    def test_render_motion_sensor_shows_detected(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="binary_sensor.motion")
        )
        entity = make_entity(
            "binary_sensor.motion", "on", {"friendly_name": "Motion", "device_class": "motion"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Detected<" in fragment

    def test_short_alpha_state_title_cased(self, ctx):
        """'home' -> 'Home' to match binary-sensor Open/Closed style."""
        widget = EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="person.adrien"))
        entity = make_entity("person.adrien", "home", {"friendly_name": "Adrien"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Home<" in fragment

    def test_show_name_off_drops_caption(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.temperature",
                options={"show_name": False},
            )
        )
        entity = make_entity(attributes={"friendly_name": "Temperature"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "TEMPERATURE" not in fragment

    def test_show_unit_off_drops_unit(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.temperature",
                options={"show_unit": False},
            )
        )
        entity = make_entity(
            attributes={"friendly_name": "Temperature", "unit_of_measurement": "°C"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "°C" not in fragment
        assert "23.5" in fragment

    def test_precision_formats_numeric_state(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.temperature",
                options={"precision": 0},
            )
        )
        entity = make_entity(state="23.456")
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">23<" in fragment

    def test_entity_icon_promoted_to_feature_band(self, ctx):
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temperature")
        )
        entity = make_entity(attributes={"icon": "mdi:thermometer"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "card-icon" in fragment

    def test_html_escaping_of_friendly_name(self, ctx):
        """Entity names containing markup must appear escaped."""
        widget = EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.evil"))
        entity = make_entity("sensor.evil", "42", {"friendly_name": "<script>alert(1)</script>"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "<script" not in fragment.lower()
        assert "&lt;" in fragment


class TestEntityWidgetCompactIdentity:
    """Short footer cells keep the value's identity (regression tests).

    Hero-layout footer cells (~69x65) sit below the kit's hide-short
    breakpoint. The caption and icon must collapse into a compact inline
    row there, not disappear — a bare "85" is a number without meaning.
    """

    FOOTER = CellContext(width=69, height=65, slot_index=0, theme=DEFAULT_THEME)

    def _widget(self, **options):
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.living_temp",
                label="Living",
                options=options,
            )
        )

    def test_footer_cell_keeps_caption(self):
        entity = make_entity("sensor.living_temp", "22")
        fragment = self._widget().render_html(self.FOOTER, make_state(entity))
        assert "LIVING" in fragment
        # The compact row manages its own visibility — hide-short would
        # re-hide the caption the widget deliberately shrank.
        assert "hide-short" not in fragment

    def test_footer_cell_stacks_icon(self):
        entity = make_entity("sensor.living_temp", "22", {"icon": "mdi:thermometer"})
        fragment = self._widget().render_html(self.FOOTER, make_state(entity))
        # Even a 65px footer stacks the icon above the caption (the old
        # design's tile anatomy); only sub-54px content bands go inline.
        assert "card-icon" in fragment
        tiny = CellContext(width=108, height=52, slot_index=0, theme=DEFAULT_THEME)
        fragment = self._widget().render_html(tiny, make_state(entity))
        assert "card-icon" not in fragment
        assert "i-sm" in fragment

    def test_footer_cell_keeps_short_unit(self):
        entity = make_entity("sensor.living_temp", "22", {"unit_of_measurement": "°C"})
        fragment = self._widget().render_html(self.FOOTER, make_state(entity))
        assert ">°C</span>" in fragment

    def test_narrow_cell_drops_long_unit(self):
        entity = make_entity("sensor.living_temp", "42", {"unit_of_measurement": "km/h"})
        fragment = self._widget().render_html(self.FOOTER, make_state(entity))
        assert "km/h" not in fragment

    def test_tiny_cell_drops_caption(self):
        tiny = CellContext(width=69, height=34, slot_index=0, theme=DEFAULT_THEME)
        entity = make_entity("sensor.living_temp", "22")
        fragment = self._widget().render_html(tiny, make_state(entity))
        assert "LIVING" not in fragment

    def test_compact_stacked_icon_is_not_hidden_by_the_kit(self):
        """A 3x3 tile's stacked feature icon must not carry hide-short —
        Python decided the stack fits; the kit would blank it below
        100px and leave icon-less cells."""
        tile = CellContext(width=72, height=72, slot_index=0, theme=DEFAULT_THEME)
        entity = make_entity("sensor.temp", "23.5", {"icon": "mdi:thermometer"})
        fragment = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.temp", label="Temp")
        ).render_html(tile, make_state(entity))
        assert '<div class="card-icon">' in fragment
        assert "hide-short" not in fragment

    def test_caption_shrinks_before_truncating(self):
        """A whole word at 10px beats "ONLIN…" at the kit size."""
        widget = EntityWidget(
            WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.online", label="Online")
        )
        entity = make_entity("sensor.online", "12")
        fragment = widget.render_html(self.FOOTER, make_state(entity))
        assert "ONLINE" in fragment
        assert "…" not in fragment

    def test_grid_icons_same_size_across_values(self):
        """Neighbouring grid cells carry equal icons regardless of value length."""
        cell = CellContext(width=108, height=108, slot_index=0, theme=DEFAULT_THEME)

        def icon_size(state: str) -> str:
            entity = make_entity("sensor.x", state, {"icon": "mdi:lightbulb"})
            fragment = EntityWidget(
                WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.x", label="X")
            ).render_html(cell, make_state(entity))
            match = re.search(r"card-icon.*?font-size: (\d+)px", fragment)
            assert match is not None
            return match.group(1)

        assert icon_size("On") == icon_size("Locked")


class TestEntityWidgetAttribute:
    """Tests for EntityWidget with attribute option (issue #38)."""

    def test_init_with_attribute(self):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={"attribute": "destination"},
            )
        )
        assert widget.attribute == "destination"

    def test_render_displays_attribute_value(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={"attribute": "destination"},
            )
        )
        entity = make_entity(
            "sensor.bus_arrival",
            "5 min",
            {"friendly_name": "Bus Arrival", "destination": "Downtown", "route_name": "42"},
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Downtown<" in fragment

    def test_render_attribute_with_precision(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.weather",
                options={"attribute": "temperature", "precision": 1},
            )
        )
        entity = make_entity(
            "sensor.weather", "sunny", {"friendly_name": "Weather", "temperature": 23.456}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">23.5<" in fragment

    def test_render_missing_attribute_shows_placeholder(self, ctx):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={"attribute": "nonexistent"},
            )
        )
        entity = make_entity("sensor.bus_arrival", "5 min", {"friendly_name": "Bus Arrival"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">--<" in fragment


# ============================================================================
# TextWidget
# ============================================================================


class TestTextWidget:
    """Tests for TextWidget."""

    def test_init(self):
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, options={"text": "Hello World"})
        )
        assert widget.text == "Hello World"

    def test_legacy_size_and_align_options_are_silently_ignored(self):
        """Stored configs may carry obsolete ``size`` / ``align`` options —
        the auto-fitting hero supersedes both; they must not crash init."""
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                options={"text": "Hello", "size": "xlarge", "align": "right"},
            )
        )
        assert widget.text == "Hello"

    def test_footer_cell_keeps_label(self):
        """Short footer cells keep a shrunk caption instead of dropping it."""
        footer = CellContext(width=69, height=65, slot_index=0, theme=DEFAULT_THEME)
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, label="Setup", options={"text": "Ready"})
        )
        fragment = widget.render_html(footer, make_state())
        assert "SETUP" in fragment
        assert "hide-short" not in fragment

    def test_render_static_text(self, ctx):
        widget = TextWidget(WidgetConfig(widget_type="text", slot=0, options={"text": "Hello"}))
        fragment = widget.render_html(ctx, make_state())
        assert ">Hello<" in fragment
        assert "t-hero" in fragment

    def test_render_entity_text(self, ctx):
        """Primary entity state wins over static text."""
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                entity_id="sensor.temperature",
                options={"text": "fallback"},
            )
        )
        entity = make_entity(state="23.5")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "23.5" in fragment
        assert "fallback" not in fragment

    def test_render_dynamic_entity_from_options(self, ctx):
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, options={"entity_id": "sensor.other"})
        )
        entities = {"sensor.other": make_entity("sensor.other", "dynamic value")}
        fragment = widget.render_html(ctx, make_state(entities=entities))
        # Text too long for one line is laid out over fitted line boxes
        # (the engine wraps against the flex item, not the cell padding).
        assert ">dynamic</div>" in fragment
        assert ">value</div>" in fragment

    def test_get_entities_includes_dynamic_entity(self):
        widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=0,
                entity_id="sensor.primary",
                options={"entity_id": "sensor.other"},
            )
        )
        assert widget.get_entities() == ["sensor.primary", "sensor.other"]

    def test_label_renders_caption(self, ctx):
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, label="Note", options={"text": "Hi"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "NOTE" in fragment

    def test_color_option(self, ctx):
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, color=(0, 128, 255), options={"text": "Hi"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "rgb(0, 128, 255)" in fragment

    def test_text_is_escaped(self, ctx):
        widget = TextWidget(
            WidgetConfig(widget_type="text", slot=0, options={"text": "<b>bold</b>"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "<b>" not in fragment
        assert "&lt;b&gt;" in fragment


# ============================================================================
# IconWidget
# ============================================================================


class TestIconWidget:
    """Tests for IconWidget."""

    def test_init_defaults(self):
        widget = IconWidget(WidgetConfig(widget_type="icon", slot=0))
        assert widget.icon == "mdi:help"
        assert widget.show_panel is False
        assert widget.size_mode == "regular"

    def test_get_entities(self):
        widget = IconWidget(WidgetConfig(widget_type="icon", slot=0))
        assert widget.get_entities() == []

    def test_render_icon_span(self, ctx):
        widget = IconWidget(
            WidgetConfig(widget_type="icon", slot=0, options={"icon": "mdi:lightbulb"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert '<span class="icon"' in fragment
        assert "&#x" in fragment  # glyph codepoint

    def test_unknown_icon_falls_back_to_help(self, ctx):
        widget = IconWidget(
            WidgetConfig(widget_type="icon", slot=0, options={"icon": "mdi:no-such-icon-xyz"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert '<span class="icon"' in fragment

    def test_color_option(self, ctx):
        widget = IconWidget(
            WidgetConfig(widget_type="icon", slot=0, color=(255, 0, 0), options={"icon": "fan"})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "rgb(255, 0, 0)" in fragment

    def test_huge_size_fills_cell(self, ctx):
        """The glyph is sized to the cell it got: "huge" fills it,
        "regular" is a deliberate half-cell mark."""

        def glyph_px(size_mode: str) -> float:
            widget = IconWidget(
                WidgetConfig(widget_type="icon", slot=0, options={"icon": "fan", "size": size_mode})
            )
            fragment = widget.render_html(ctx, make_state())
            return float(fragment.split("font-size: ")[1].split("px")[0])

        assert glyph_px("huge") > glyph_px("regular") > 0.35 * ctx.height
        assert glyph_px("huge") < ctx.height

    def test_show_panel_adds_surface(self, ctx):
        widget = IconWidget(
            WidgetConfig(widget_type="icon", slot=0, options={"icon": "fan", "show_panel": True})
        )
        fragment = widget.render_html(ctx, make_state())
        assert "var(--surface)" in fragment


# ============================================================================
# GaugeWidget
# ============================================================================


class TestGaugeWidget:
    """Tests for GaugeWidget."""

    def test_init(self):
        widget = GaugeWidget(WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.cpu"))
        assert widget.style == "bar"
        assert widget.min_value == 0
        assert widget.max_value == 100
        assert widget.show_value is True

    def test_init_with_options(self):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                options={"style": "ring", "min": 10, "max": 50, "unit": "%"},
            )
        )
        assert widget.style == "ring"
        assert widget.min_value == 10
        assert widget.max_value == 50
        assert widget.unit == "%"

    def test_defaults_show_name_and_show_unit(self):
        """show_name / show_unit default to True (parity with EntityWidget)."""
        widget = GaugeWidget(WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.cpu"))
        assert widget.show_name is True
        assert widget.show_unit is True

    def test_bar_footer_cell_keeps_caption(self):
        """A bar gauge in a short footer cell keeps its label."""
        footer = CellContext(width=69, height=65, slot_index=0, theme=DEFAULT_THEME)
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                label="CPU",
                options={"style": "bar"},
            )
        )
        entity = make_entity("sensor.cpu", "73", {"unit_of_measurement": "%"})
        fragment = widget.render_html(footer, make_state(entity))
        assert "CPU" in fragment
        assert "hide-short" not in fragment

    def test_cleared_icon_normalises_to_none(self):
        """ha-icon-picker writes ``""`` when cleared (issue #125)."""
        widget = GaugeWidget(
            WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.cpu", options={"icon": ""})
        )
        assert widget.icon is None

    def test_render_bar_style(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge", slot=0, entity_id="sensor.cpu", options={"style": "bar"}
            )
        )
        entity = make_entity("sensor.cpu", "75", {"friendly_name": "CPU"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "width: 75.0%" in fragment  # bar fill
        assert ">75<" in fragment  # hero value
        assert "CPU" in fragment

    def test_render_ring_style(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge", slot=0, entity_id="sensor.cpu", options={"style": "ring"}
            )
        )
        entity = make_entity("sensor.cpu", "50", {"friendly_name": "CPU"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "<svg" in fragment
        assert "<circle" in fragment
        assert "stroke-dasharray" in fragment

    def test_render_arc_style(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge", slot=0, entity_id="sensor.cpu", options={"style": "arc"}
            )
        )
        entity = make_entity("sensor.cpu", "25", {"friendly_name": "CPU"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "<svg" in fragment
        assert "<path" in fragment

    def test_render_without_entity_shows_placeholder_value(self, ctx):
        widget = GaugeWidget(WidgetConfig(widget_type="gauge", slot=0))
        fragment = widget.render_html(ctx, make_state())
        assert "--" in fragment

    def test_show_name_false_drops_caption(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                options={"show_name": False},
            )
        )
        entity = make_entity("sensor.cpu", "75", {"friendly_name": "CPU Usage"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "CPU USAGE" not in fragment

    def test_show_unit_false_strips_entity_unit(self, ctx):
        """show_unit=False suppresses the entity's native unit (issue #125)."""
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                options={"show_unit": False},
            )
        )
        entity = make_entity(
            "sensor.cpu", "75", {"friendly_name": "CPU", "unit_of_measurement": "%"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "75%" not in fragment
        assert ">75<" in fragment

    def test_show_unit_true_appends_entity_unit(self, ctx):
        """Value and unit are separate spans (unit reads lighter)."""
        widget = GaugeWidget(WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.cpu"))
        entity = make_entity(
            "sensor.cpu", "75", {"friendly_name": "CPU", "unit_of_measurement": "%"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">75<" in fragment
        assert 't-unit"' in fragment
        assert ">%<" in fragment

    def test_threshold_colors(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                options={
                    "color_thresholds": [
                        {"value": 0, "color": [0, 255, 0]},
                        {"value": 50, "color": [255, 0, 0]},
                    ]
                },
            )
        )
        entity = make_entity("sensor.cpu", "75", {"friendly_name": "CPU"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "rgb(255, 0, 0)" in fragment
        # Below the second threshold the first color applies
        entity_low = make_entity("sensor.cpu", "20", {"friendly_name": "CPU"})
        fragment_low = widget.render_html(ctx, make_state(entity_low))
        assert "rgb(0, 255, 0)" in fragment_low

    def test_vertical_orientation(self, ctx):
        widget = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=0,
                entity_id="sensor.cpu",
                options={"orientation": "vertical"},
            )
        )
        entity = make_entity("sensor.cpu", "60", {"friendly_name": "CPU"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "height: 60.0%" in fragment  # bottom-anchored fill

    def test_auto_orientation_goes_vertical_in_tall_cells(self):
        tall_ctx = CellContext(width=100, height=240, slot_index=0, theme=DEFAULT_THEME)
        widget = GaugeWidget(WidgetConfig(widget_type="gauge", slot=0, entity_id="sensor.cpu"))
        entity = make_entity("sensor.cpu", "60", {"friendly_name": "CPU"})
        fragment = widget.render_html(tall_ctx, make_state(entity))
        assert "height: 60.0%" in fragment


# ============================================================================
# StatusWidget
# ============================================================================


class TestStatusWidget:
    """Tests for StatusWidget."""

    def test_init(self):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door")
        )
        assert widget.on_text == "ON"
        assert widget.off_text == "OFF"
        assert widget.show_status_text is True
        assert widget.show_name is True

    def test_init_with_options(self):
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"on_text": "Open", "off_text": "Closed"},
            )
        )
        assert widget.on_text == "Open"
        assert widget.off_text == "Closed"

    def test_init_with_list_colors(self):
        """Colors from JSON lists resolve to CSS rgb() strings (issue #48)."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"on_color": [0, 255, 0], "off_color": [255, 0, 0]},
            )
        )
        assert widget.on_color == "rgb(0, 255, 0)"
        assert widget.off_color == "rgb(255, 0, 0)"

    def test_default_colors_use_theme_roles(self):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door")
        )
        assert widget.on_color == "var(--success)"
        assert widget.off_color == "var(--error)"

    def test_render_on_state(self, ctx):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door")
        )
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Front Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">ON<" in fragment
        assert "var(--success)" in fragment
        assert "FRONT DOOR" in fragment

    def test_render_off_state(self, ctx):
        widget = StatusWidget(
            WidgetConfig(widget_type="status", slot=0, entity_id="binary_sensor.door")
        )
        entity = make_entity("binary_sensor.door", "off", {"friendly_name": "Front Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">OFF<" in fragment
        assert "var(--error)" in fragment

    def test_render_with_custom_colors(self, ctx):
        """Custom JSON list colors appear in the fragment (issue #48)."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"on_color": [0, 255, 0], "off_color": [255, 0, 0]},
            )
        )
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Front Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "rgb(0, 255, 0)" in fragment

    def test_custom_on_off_text_rendered(self, ctx):
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"on_text": "Open", "off_text": "Closed"},
            )
        )
        entity = make_entity("binary_sensor.door", "on", {})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">Open<" in fragment

    def test_icon_only_mode(self, ctx):
        """show_status_text=False promotes the tinted icon to the hero."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"show_status_text": False, "icon": "door"},
            )
        )
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">ON<" not in fragment
        assert "i-lg" in fragment

    def test_hide_name(self, ctx):
        """show_name=False drops the name band but keeps the state (issue #180)."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"show_name": False},
            )
        )
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Front Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "FRONT DOOR" not in fragment
        assert ">ON<" in fragment

    def test_hide_name_strip_layout(self):
        """Wide cells also honor show_name=False (issue #180)."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"show_name": False},
            )
        )
        strip_ctx = CellContext(width=228, height=74, slot_index=0, theme=DEFAULT_THEME)
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Front Door"})
        fragment = widget.render_html(strip_ctx, make_state(entity))
        assert "FRONT DOOR" not in fragment
        assert ">ON<" in fragment

    def test_hide_name_and_status_text_icon_only(self, ctx):
        """Both hidden: only the tinted device icon remains (issue #180)."""
        widget = StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=0,
                entity_id="binary_sensor.door",
                options={"show_name": False, "show_status_text": False, "icon": "door"},
            )
        )
        entity = make_entity("binary_sensor.door", "on", {"friendly_name": "Front Door"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "FRONT DOOR" not in fragment
        assert ">ON<" not in fragment
        assert "i-lg" in fragment


# ============================================================================
# StatusListWidget
# ============================================================================


class TestStatusListWidget:
    """Tests for StatusListWidget."""

    def test_init(self):
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list", slot=0, options={"entities": [], "title": "Doors"}
            )
        )
        assert widget.entities == []
        assert widget.title == "Doors"

    def test_init_with_list_colors(self):
        """Colors from JSON lists resolve to CSS rgb() strings (issue #48)."""
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "entities": [],
                    "on_color": [0, 255, 0],
                    "off_color": [255, 0, 0],
                },
            )
        )
        assert widget.on_color == "rgb(0, 255, 0)"
        assert widget.off_color == "rgb(255, 0, 0)"

    def test_get_entities(self):
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "entities": [
                        "binary_sensor.front_door",
                        ["binary_sensor.back_door", "Back"],
                    ]
                },
            )
        )
        entities = widget.get_entities()
        assert "binary_sensor.front_door" in entities
        assert "binary_sensor.back_door" in entities

    def test_render_with_entities(self, ctx):
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "title": "Doors",
                    "entities": ["binary_sensor.front_door", "binary_sensor.back_door"],
                },
            )
        )
        entities = {
            "binary_sensor.front_door": make_entity(
                "binary_sensor.front_door", "on", {"friendly_name": "Front"}
            ),
            "binary_sensor.back_door": make_entity(
                "binary_sensor.back_door", "off", {"friendly_name": "Back"}
            ),
        }
        fragment = widget.render_html(ctx, make_state(entities=entities))
        assert "DOORS" in fragment  # title
        assert "Front" in fragment
        assert "Back" in fragment
        assert "var(--success)" in fragment  # on row
        assert "var(--error)" in fragment  # off row

    def test_render_with_custom_colors(self, ctx):
        """Custom JSON list colors appear in the fragment (issue #48)."""
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={
                    "entities": ["binary_sensor.front_door"],
                    "on_color": [0, 255, 0],
                    "off_color": [255, 0, 0],
                },
            )
        )
        entities = {
            "binary_sensor.front_door": make_entity(
                "binary_sensor.front_door", "on", {"friendly_name": "Front"}
            )
        }
        fragment = widget.render_html(ctx, make_state(entities=entities))
        assert "rgb(0, 255, 0)" in fragment

    def test_device_class_translates_state_text(self, ctx):
        """Binary sensor rows show 'Open'/'Closed' instead of 'On'/'Off'."""
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={"entities": ["binary_sensor.front_door"]},
            )
        )
        entities = {
            "binary_sensor.front_door": make_entity(
                "binary_sensor.front_door",
                "on",
                {"friendly_name": "Front", "device_class": "door"},
            )
        }
        fragment = widget.render_html(ctx, make_state(entities=entities))
        assert "Open" in fragment

    def test_custom_label_from_pair(self, ctx):
        widget = StatusListWidget(
            WidgetConfig(
                widget_type="status_list",
                slot=0,
                options={"entities": [["binary_sensor.back_door", "Garage"]]},
            )
        )
        fragment = widget.render_html(ctx, make_state())
        assert "Garage" in fragment


# ============================================================================
# ProgressWidget
# ============================================================================


class TestProgressWidget:
    """Tests for ProgressWidget."""

    def test_init(self):
        widget = ProgressWidget(
            WidgetConfig(widget_type="progress", slot=0, entity_id="sensor.steps")
        )
        assert widget.target == 100
        assert widget.show_target is True

    def test_init_with_options(self):
        widget = ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                options={"target": 10000, "unit": "steps", "show_target": False},
            )
        )
        assert widget.target == 10000
        assert widget.unit == "steps"
        assert widget.show_target is False

    def test_render_with_entity(self, ctx):
        widget = ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                options={"target": 10000},
            )
        )
        entity = make_entity(
            "sensor.steps", "5000", {"friendly_name": "Steps", "unit_of_measurement": "steps"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">50<" in fragment  # hero percent (digits)
        assert ">%<" in fragment  # unit renders as its own lighter span
        assert "5k of 10k steps" in fragment  # abbreviated chip
        assert "width: 50.0%" in fragment  # bar fill
        assert "STEPS" in fragment  # caption

    def test_show_target_off_drops_target(self, ctx):
        widget = ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                options={"target": 10000, "show_target": False},
            )
        )
        entity = make_entity("sensor.steps", "5000", {"friendly_name": "Steps"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "/10k" not in fragment
        assert "5k" in fragment

    def test_render_without_entity(self, ctx):
        widget = ProgressWidget(WidgetConfig(widget_type="progress", slot=0))
        fragment = widget.render_html(ctx, make_state())
        assert ">0<" in fragment
        assert ">%<" in fragment

    def test_show_name_off_drops_caption(self, ctx):
        widget = ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=0,
                entity_id="sensor.steps",
                options={"target": 10000, "show_name": False},
            )
        )
        entity = make_entity("sensor.steps", "5000", {"friendly_name": "Steps"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "STEPS" not in fragment
        assert ">50<" in fragment  # percent hero survives


# ============================================================================
# MultiProgressWidget
# ============================================================================


class TestMultiProgressWidget:
    """Tests for MultiProgressWidget."""

    def test_init(self):
        widget = MultiProgressWidget(
            WidgetConfig(
                widget_type="multi_progress", slot=0, options={"items": [], "title": "Fitness"}
            )
        )
        assert widget.items == []
        assert widget.title == "Fitness"

    def test_get_entities(self):
        widget = MultiProgressWidget(
            WidgetConfig(
                widget_type="multi_progress",
                slot=0,
                options={
                    "items": [
                        {"entity_id": "sensor.steps", "target": 10000},
                        {"entity_id": "sensor.calories", "target": 500},
                    ]
                },
            )
        )
        assert "sensor.steps" in widget.get_entities()
        assert "sensor.calories" in widget.get_entities()

    def test_render_with_items(self, ctx):
        widget = MultiProgressWidget(
            WidgetConfig(
                widget_type="multi_progress",
                slot=0,
                options={
                    "title": "Fitness",
                    "items": [
                        {"entity_id": "sensor.steps", "target": 10000, "label": "Steps"},
                        {"entity_id": "sensor.calories", "target": 500, "label": "Cal"},
                    ],
                },
            )
        )
        entities = {
            "sensor.steps": make_entity("sensor.steps", "5000", {"friendly_name": "Steps"}),
            "sensor.calories": make_entity("sensor.calories", "300", {"friendly_name": "Calories"}),
        }
        fragment = widget.render_html(ctx, make_state(entities=entities))
        assert "FITNESS" in fragment  # title
        assert "STEPS" in fragment
        assert "CAL" in fragment
        assert "50%" in fragment  # steps percent
        assert "60%" in fragment  # calories percent
        assert "5000/10000" in fragment  # raw value column (visible at 240px)


# ============================================================================
# ChartWidget
# ============================================================================


class TestChartWidget:
    """Tests for ChartWidget."""

    def test_init(self):
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temperature")
        )
        assert widget.hours == 24
        assert widget.show_value is True

    def test_period_option_mapping(self):
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=0,
                entity_id="sensor.temperature",
                options={"period": "6 hours"},
            )
        )
        assert widget.hours == 6

    def test_render_no_data(self, ctx):
        widget = ChartWidget(WidgetConfig(widget_type="chart", slot=0, label="Temperature"))
        fragment = widget.render_html(ctx, make_state())
        assert "No data" in fragment
        assert "<svg" not in fragment

    def test_render_with_data(self, ctx):
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temperature")
        )
        entity = make_entity(
            attributes={"friendly_name": "Temperature", "unit_of_measurement": "°C"}
        )
        history = [20.0, 21.5, 22.0, 21.0, 23.5, 24.0, 23.0]
        fragment = widget.render_html(ctx, make_state(entity, history=history))
        assert "<svg" in fragment
        assert "<path" in fragment  # smooth bezier line + gradient area
        assert "linearGradient" in fragment
        # Value and unit are separate spans (unit steps down in size).
        assert "23.5" in fragment  # current value in header
        assert '<span class="t-unit"' in fragment
        assert "°C" in fragment
        # Caption is measured against the space the value leaves and
        # truncated in Python (Blitz draws no ellipsis and never clips).
        assert "TEMPERAT" in fragment  # label

    def test_range_footer_shows_min_max_and_period(self, ctx):
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temperature")
        )
        entity = make_entity(attributes={"friendly_name": "Temp"})
        fragment = widget.render_html(ctx, make_state(entity, history=[20.0, 21.0, 22.5, 24.0]))
        assert "20.0" in fragment  # min
        assert "24.0" in fragment  # max
        assert "24h" in fragment  # period label

    def test_show_range_off_drops_footer(self, ctx):
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=0,
                entity_id="sensor.temperature",
                options={"show_range": False},
            )
        )
        entity = make_entity(attributes={"friendly_name": "Temp"})
        fragment = widget.render_html(ctx, make_state(entity, history=[20.0, 21.0, 24.0]))
        assert "24h" not in fragment

    def test_binary_data_suppresses_range_footer(self, ctx):
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="binary_sensor.door")
        )
        entity = make_entity("binary_sensor.door", "off", {"friendly_name": "Door"})
        history = [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0]
        fragment = widget.render_html(ctx, make_state(entity, history=history))
        assert "<svg" in fragment  # still charts
        assert "24h" not in fragment  # no range footer for binary data

    def test_fill_off_zeroes_area_opacity(self, ctx):
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=0,
                entity_id="sensor.temperature",
                options={"fill": False},
            )
        )
        entity = make_entity(attributes={"friendly_name": "Temp"})
        fragment = widget.render_html(ctx, make_state(entity, history=[20.0, 21.0, 24.0]))
        # With fill off, the gradient's top stop has zero opacity, so
        # the area fade disappears.
        assert 'stop-opacity="0"' in fragment
        assert 'stop-opacity="0.22"' not in fragment

    def test_compact_cell_keeps_caption_drops_value_bands(self, compact_ctx):
        """A 3x3 cell keeps the caption (an unlabeled trace is a
        squiggle) but sheds the value and range rows."""
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temperature")
        )
        entity = make_entity(attributes={"friendly_name": "Temp"})
        fragment = widget.render_html(compact_ctx, make_state(entity, history=[20.0, 21.0, 24.0]))
        assert "<svg" in fragment
        assert "TEMP" in fragment  # caption survives, shrunk if needed
        assert "t-value" not in fragment
        assert "hide-short" not in fragment  # visibility decided in Python

    def test_show_name_off_drops_caption(self, ctx):
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=0,
                entity_id="sensor.temperature",
                options={"show_name": False},
            )
        )
        entity = make_entity(
            attributes={"friendly_name": "Temperature", "unit_of_measurement": "°C"}
        )
        fragment = widget.render_html(ctx, make_state(entity, history=[20.0, 21.0, 23.5]))
        assert "TEMPERAT" not in fragment
        assert "23.5" in fragment  # value header survives
        assert "<svg" in fragment

    def test_show_name_off_compact_keeps_value(self, compact_ctx):
        widget = ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=0,
                entity_id="sensor.temperature",
                options={"show_name": False},
            )
        )
        entity = make_entity(attributes={"friendly_name": "Temp"})
        fragment = widget.render_html(compact_ctx, make_state(entity, history=[20.0, 21.0, 24.0]))
        assert "TEMP" not in fragment
        assert "<svg" in fragment

    def test_binary_history_draws_square_steps(self, ctx):
        """Bezier smoothing overshoots on binary traces, so it is off."""
        widget = ChartWidget(
            WidgetConfig(widget_type="chart", slot=0, entity_id="binary_sensor.door")
        )
        entity = make_entity("binary_sensor.door", "off", {"friendly_name": "Door"})
        fragment = widget.render_html(ctx, make_state(entity, history=[0.0, 1.0, 0.0, 1.0]))
        assert " C " not in fragment  # no cubic bezier segments in the path

    def test_is_binary_data_true(self):
        assert _is_binary_data([0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0]) is True

    def test_is_binary_data_false(self):
        assert _is_binary_data([20.0, 21.5, 22.0, 21.0, 23.5]) is False

    def test_is_binary_data_empty(self):
        assert _is_binary_data([]) is False

    def test_format_period(self):
        assert _format_period(24) == "24h"
        assert _format_period(6) == "6h"
        assert _format_period(1) == "1h"
        assert _format_period(15 / 60) == "15m"
        assert _format_period(5 / 60) == "5m"
        assert _format_period(0) == ""


# ============================================================================
# ClimateWidget
# ============================================================================


class TestClimateWidget:
    """Tests for ClimateWidget."""

    def test_init(self):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        assert widget.show_target is True
        assert widget.show_humidity is True
        assert widget.show_mode is True

    def test_init_with_options(self):
        widget = ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=0,
                entity_id="climate.thermostat",
                options={"show_target": False, "show_humidity": False, "show_mode": False},
            )
        )
        assert widget.show_target is False
        assert widget.show_humidity is False
        assert widget.show_mode is False

    def test_get_entities(self):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        assert widget.get_entities() == ["climate.thermostat"]

    def test_render_without_entity(self, ctx):
        widget = ClimateWidget(WidgetConfig(widget_type="climate", slot=0))
        fragment = widget.render_html(ctx, make_state())
        assert "NO CLIMATE DATA" in fragment

    def _thermostat(self, state: str, **attrs: Any) -> EntityState:
        return make_entity("climate.thermostat", state, {"friendly_name": "Thermostat", **attrs})

    def test_small_tile_caption_carries_mode_icon(self):
        """When the chips are shed (<100px), the caption icon is the only
        carrier of the hvac state — it must ride along."""
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat(
            "heat", current_temperature=21.5, temperature=22, hvac_action="heating"
        )
        tile = CellContext(width=69, height=108, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(tile, make_state(entity))
        assert "THERM" in fragment  # room caption survives (maybe truncated)
        # Narrow cells STACK the tinted state icon on its own band above
        # the name (inline, its reserve starved the caption to stubs).
        assert "card-icon" in fragment
        assert "icon i-md" in fragment

    def test_show_name_off_drops_room_name(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=0,
                entity_id="climate.thermostat",
                options={"show_name": False},
            )
        )
        entity = self._thermostat(
            "heat", current_temperature=21.5, temperature=22, hvac_action="heating"
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "THERMOSTAT" not in fragment
        assert "21.5" in fragment  # hero temperature survives
        assert "HEATING" in fragment  # mode chip survives

    def test_show_name_off_small_tile_keeps_state_icon(self):
        """With chips shed (<100px wide) the caption icon is the only
        carrier of the hvac state — hiding the name must not drop it."""
        widget = ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=0,
                entity_id="climate.thermostat",
                options={"show_name": False},
            )
        )
        entity = self._thermostat(
            "heat", current_temperature=21.5, temperature=22, hvac_action="heating"
        )
        tile = CellContext(width=69, height=108, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(tile, make_state(entity))
        assert "THERM" not in fragment
        assert "card-icon" in fragment  # tinted state icon band stays

    def test_short_cell_keeps_caption_row(self):
        """Short non-strip cells keep a shrunk caption instead of an
        anonymous temperature."""
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat(
            "heat", current_temperature=21.5, temperature=22, hvac_action="heating"
        )
        short = CellContext(width=108, height=69, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(short, make_state(entity))
        assert "THERMOSTAT" in fragment
        assert "hide-short" not in fragment

    def test_render_heating(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat(
            "heat", current_temperature=20.5, temperature=22, hvac_action="heating", humidity=45
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">20.5<" in fragment  # hero numerals
        assert "°C" in fragment  # unit, set smaller on the hero baseline
        assert "HEATING" in fragment  # mode chip
        assert "var(--warning)" in fragment  # heating tint
        assert "22°" in fragment  # target chip
        assert "45%" in fragment  # humidity chip
        assert "var(--info)" in fragment  # humidity tint

    def test_render_cooling(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat(
            "cool", current_temperature=26, temperature=23, hvac_action="cooling"
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">26<" in fragment
        assert "°C" in fragment
        assert "COOLING" in fragment
        assert "var(--info)" in fragment

    def test_render_idle_uses_muted(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat(
            "heat", current_temperature=22, temperature=22, hvac_action="idle"
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "IDLE" in fragment
        assert "var(--muted)" in fragment

    def test_render_off(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(widget_type="climate", slot=0, entity_id="climate.thermostat")
        )
        entity = self._thermostat("off", current_temperature=18)
        fragment = widget.render_html(ctx, make_state(entity))
        assert ">18<" in fragment
        assert "°C" in fragment
        assert "OFF" in fragment
        assert "var(--error)" in fragment

    def test_options_toggle_chips_off(self, ctx):
        widget = ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=0,
                entity_id="climate.thermostat",
                options={"show_target": False, "show_humidity": False, "show_mode": False},
            )
        )
        entity = self._thermostat(
            "heat", current_temperature=20.5, temperature=22, hvac_action="heating", humidity=45
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "HEATING" not in fragment
        assert "22°" not in fragment
        assert "45%" not in fragment
        assert ">20.5<" in fragment  # hero survives

    def test_format_temp(self):
        assert _format_temp(21) == "21°"
        assert _format_temp(21.5) == "21.5°"
        assert _format_temp(21.0) == "21°"
        assert _format_temp(None) == "--"
        assert _format_temp("bogus") == "--"


# ============================================================================
# WeatherWidget
# ============================================================================

FORECAST = [
    {
        "datetime": "2025-12-29T00:00:00+00:00",
        "condition": "sunny",
        "temperature": 26,
        "templow": 14,
    },
    {
        "datetime": "2025-12-30T00:00:00+00:00",
        "condition": "rainy",
        "temperature": 19,
        "templow": 10,
    },
    {
        "datetime": "2025-12-31T00:00:00+00:00",
        "condition": "cloudy",
        "temperature": 18,
        "templow": 9,
    },
]


class TestWeatherWidget:
    """Tests for WeatherWidget."""

    def _widget(self, **options: Any) -> WeatherWidget:
        return WeatherWidget(
            WidgetConfig(widget_type="weather", slot=0, entity_id="weather.home", options=options)
        )

    def _home(self, condition: str = "sunny", **attrs: Any) -> EntityState:
        return make_entity("weather.home", condition, {"friendly_name": "Home", **attrs})

    def test_init(self):
        widget = self._widget()
        assert widget.show_forecast is True
        assert widget.forecast_days == 3
        assert widget.show_humidity is True
        assert widget.forecast_start_tomorrow is False

    def test_init_with_options(self):
        widget = self._widget(
            show_forecast=False,
            forecast_days=5,
            show_humidity=False,
            forecast_start_tomorrow=True,
        )
        assert widget.show_forecast is False
        assert widget.forecast_days == 5
        assert widget.show_humidity is False
        assert widget.forecast_start_tomorrow is True

    def test_visible_forecast_starts_today_by_default(self):
        widget = self._widget()
        assert widget._visible_forecast(FORECAST) == FORECAST

    def test_visible_forecast_can_start_tomorrow(self):
        widget = self._widget(forecast_start_tomorrow=True)
        assert widget._visible_forecast(FORECAST) == FORECAST[1:]

    def test_visible_forecast_caps_at_forecast_days(self):
        widget = self._widget(forecast_days=2)
        assert widget._visible_forecast(FORECAST) == FORECAST[:2]

    def test_render_without_entity(self, ctx):
        widget = self._widget()
        fragment = widget.render_html(ctx, make_state())
        assert "NO WEATHER DATA" in fragment

    def test_render_with_entity(self, ctx):
        widget = self._widget()
        entity = self._home(temperature=22, humidity=45)
        fragment = widget.render_html(ctx, make_state(entity, forecast=FORECAST))
        assert "22°" in fragment  # hero temperature
        assert "SUNNY" in fragment  # condition caption
        assert "26°" in fragment  # today's high chip
        assert "14°" in fragment  # today's low chip
        assert "45%" in fragment  # humidity chip (wide cell)

    def test_condition_label_partlycloudy(self, ctx):
        widget = self._widget()
        entity = self._home("partlycloudy", temperature=18)
        fragment = widget.render_html(ctx, make_state(entity))
        assert "PARTLY CLOUDY" in fragment

    def test_forecast_strip_shows_day_names(self, ctx):
        widget = self._widget()
        entity = self._home(temperature=22)
        fragment = widget.render_html(ctx, make_state(entity, forecast=FORECAST))
        assert "MON" in fragment  # 2025-12-29
        assert "TUE" in fragment
        assert "WED" in fragment

    def test_show_forecast_off_drops_strip(self, ctx):
        widget = self._widget(show_forecast=False)
        entity = self._home(temperature=22)
        fragment = widget.render_html(ctx, make_state(entity, forecast=FORECAST))
        assert "MON" not in fragment

    def test_forecast_start_tomorrow_drops_today(self, ctx):
        widget = self._widget(forecast_start_tomorrow=True)
        entity = self._home(temperature=22)
        fragment = widget.render_html(ctx, make_state(entity, forecast=FORECAST))
        assert "MON" not in fragment
        assert "TUE" in fragment

    def test_show_high_low_off_drops_chips(self, ctx):
        widget = self._widget(show_high_low=False, show_forecast=False, show_humidity=False)
        entity = self._home(temperature=22)
        fragment = widget.render_html(ctx, make_state(entity, forecast=FORECAST))
        assert "26°" not in fragment
        assert "14°" not in fragment

    def test_humidity_hidden_in_narrow_cells(self, compact_ctx):
        """Humidity chip only appears in cells >= 180px wide."""
        widget = self._widget()
        entity = self._home(temperature=22, humidity=45)
        fragment = widget.render_html(compact_ctx, make_state(entity))
        assert "45%" not in fragment

    def test_forecast_column_high_low_pair(self):
        widget = self._widget()
        column = widget._forecast_column(FORECAST[0], 0, high_only=False)
        assert 'class="wx-hi">26°' in column
        assert 'class="wx-lo">14°' in column

    def test_forecast_column_high_only(self):
        widget = self._widget()
        column = widget._forecast_column(FORECAST[0], 0, high_only=True)
        assert 'class="wx-hi">26°' in column
        assert "wx-lo" not in column

    def test_forecast_temps_round_to_integer(self):
        """Forecast columns show whole-number temps (22.6 -> 23)."""
        widget = self._widget()
        day = {"datetime": "2025-12-29T00:00:00", "temperature": 26.4, "templow": 13.6}
        column = widget._forecast_column(day, 0, high_only=False)
        assert 'class="wx-hi">26°' in column
        assert 'class="wx-lo">14°' in column
        assert "26.4" not in column

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(26.0, 26), (22.6, 23), (22.4, 22), (45, 45), ("--", "--"), (None, None)],
    )
    def test_fmt_num(self, value, expected):
        """``_fmt_num`` rounds numbers to whole integers for secondary display."""
        assert _fmt_num(value) == expected


# ============================================================================
# MediaWidget
# ============================================================================


class TestMediaWidget:
    """Tests for MediaWidget."""

    def _widget(self, **options: Any) -> MediaWidget:
        return MediaWidget(
            WidgetConfig(
                widget_type="media",
                slot=0,
                entity_id="media_player.living_room",
                options=options,
            )
        )

    def _player(self, state: str, **attrs: Any) -> EntityState:
        return make_entity("media_player.living_room", state, attrs)

    def test_init(self):
        widget = self._widget()
        assert widget.show_artist is True
        assert widget.show_progress is True

    def test_render_idle(self, ctx):
        widget = self._widget()
        fragment = widget.render_html(ctx, make_state(self._player("idle")))
        assert "NO MEDIA" in fragment

    def test_render_paused_with_track_keeps_now_playing(self, ctx):
        """Paused with a known track keeps the full card, marked PAUSED."""
        widget = self._widget()
        entity = self._player("paused", media_title="Test Song", media_artist="Test Artist")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "PAUSED" in fragment
        assert "Test Song" in fragment

    def test_render_paused_without_track_is_placeholder(self, ctx):
        """Paused with no track information gets the quiet placeholder."""
        widget = self._widget()
        entity = self._player("paused")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "PAUSED" in fragment

    def test_idle_names_the_player(self, ctx):
        """Two idle players in one grid must not render identically."""
        widget = self._widget()
        entity = self._player("idle", friendly_name="Kitchen Speaker")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "KITCHEN" in fragment

    def test_off_distinct_from_idle(self, ctx):
        widget = self._widget()
        fragment = widget.render_html(ctx, make_state(self._player("off")))
        assert "OFF" in fragment
        assert "NO MEDIA" not in fragment

    def test_short_cell_keeps_paused_caption(self):
        """PAUSED must survive short cells — without it, paused and
        playing render identically in the text-only path."""
        widget = self._widget()
        entity = self._player(
            "paused", media_title="Song", media_artist="Artist", media_duration=300
        )
        short = CellContext(width=108, height=69, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(short, make_state(entity))
        assert "PAUSED" in fragment
        assert 'class="t-label" style=' in fragment  # Python-sized, no hide-short

    def test_narrow_art_cell_keeps_title(self):
        """Narrow album-art cells keep the fitted title — art plus an
        anonymous bar says nothing."""
        from PIL import Image as PILImage

        widget = self._widget()
        entity = self._player(
            "playing", media_title="Song Name", media_duration=300, media_position=10
        )
        art = PILImage.new("RGB", (64, 64), (40, 40, 80))
        narrow = CellContext(width=69, height=224, slot_index=0, theme=DEFAULT_THEME)
        fragment = widget.render_html(narrow, make_state(entity, image=art))
        assert "hide-narrow" not in fragment
        assert "Song" in fragment

    def test_render_playing_now_playing_card(self, ctx):
        widget = self._widget()
        entity = self._player(
            "playing",
            media_title="Test Song",
            media_artist="Test Artist",
            media_position=60,
            media_duration=180,
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "NOW PLAYING" in fragment
        assert "Test Song" in fragment
        assert "Test Artist" in fragment
        assert "1:00" in fragment  # position
        assert "3:00" in fragment  # duration

    def test_show_artist_off_drops_artist(self, ctx):
        widget = self._widget(show_artist=False)
        entity = self._player("playing", media_title="Song", media_artist="Artist Name")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "Artist Name" not in fragment

    def test_show_album_renders_album(self, ctx):
        widget = self._widget(show_album=True)
        entity = self._player("playing", media_title="Song", media_album_name="The Album")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "The Album" in fragment

    def test_album_art_embeds_data_uri(self, ctx):
        widget = self._widget()
        entity = self._player(
            "playing",
            media_title="Test Song",
            media_artist="Test Artist",
            media_position=60,
            media_duration=180,
        )
        art = Image.new("RGB", (64, 64), (10, 20, 30))
        fragment = widget.render_html(ctx, make_state(entity, image=art))
        assert "data:image/png;base64," in fragment
        assert "Test Song" in fragment  # overlay title

    def test_title_is_escaped(self, ctx):
        widget = self._widget()
        entity = self._player("playing", media_title="<Rock & Roll>")
        fragment = widget.render_html(ctx, make_state(entity))
        assert "<Rock" not in fragment
        assert "&lt;Rock &amp; Roll&gt;" in fragment

    def test_format_time(self):
        assert _format_time(0) == "0:00"
        assert _format_time(65) == "1:05"
        assert _format_time(3661) == "1:01:01"


# ============================================================================
# CameraWidget
# ============================================================================


class TestCameraWidget:
    """Tests for CameraWidget."""

    def _widget(self, **options: Any) -> CameraWidget:
        return CameraWidget(
            WidgetConfig(widget_type="camera", slot=0, entity_id="camera.front", options=options)
        )

    def test_get_entities(self):
        widget = self._widget()
        assert widget.get_entities() == ["camera.front"]

    def test_render_without_image(self, ctx):
        widget = self._widget()
        fragment = widget.render_html(ctx, make_state())
        assert "NO IMAGE" in fragment

    def test_render_with_image_embeds_data_uri(self, ctx):
        widget = self._widget()
        snapshot = Image.new("RGB", (32, 32), (200, 100, 50))
        fragment = widget.render_html(ctx, make_state(image=snapshot))
        assert "data:image/png;base64," in fragment
        assert "object-fit: cover" in fragment  # default fit matches SCHEMA

    def test_fit_cover_option(self, ctx):
        widget = self._widget(fit="cover")
        snapshot = Image.new("RGB", (32, 32))
        fragment = widget.render_html(ctx, make_state(image=snapshot))
        assert "object-fit: cover" in fragment

    def test_show_label_renders_chip(self, ctx):
        widget = self._widget(show_label=True)
        snapshot = Image.new("RGB", (32, 32))
        entity = make_entity("camera.front", "streaming", {"friendly_name": "Front Yard"})
        fragment = widget.render_html(ctx, make_state(entity, image=snapshot))
        assert "Front Yard" in fragment

    def test_no_label_by_default(self, ctx):
        widget = self._widget()
        snapshot = Image.new("RGB", (32, 32))
        entity = make_entity("camera.front", "streaming", {"friendly_name": "Front Yard"})
        fragment = widget.render_html(ctx, make_state(entity, image=snapshot))
        assert "Front Yard" not in fragment


# ============================================================================
# AttributeListWidget
# ============================================================================


class TestAttributeListWidget:
    """Tests for AttributeListWidget (issue #38)."""

    def test_init(self):
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={
                    "title": "Bus Info",
                    "attributes": [
                        {"key": "route_name", "label": "Route"},
                        {"key": "destination", "label": "To"},
                    ],
                },
            )
        )
        assert widget.title == "Bus Info"
        assert len(widget.attributes) == 2

    def test_init_simple_attributes(self):
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.test",
                options={"attributes": ["route_name", "destination"]},
            )
        )
        assert len(widget.attributes) == 2

    def test_render_with_entity(self, ctx):
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={
                    "title": "Bus Info",
                    "attributes": [
                        {"key": "route_name", "label": "Route"},
                        {"key": "destination", "label": "To"},
                        {"key": "state", "label": "Arrives"},
                    ],
                },
            )
        )
        entity = make_entity(
            "sensor.bus_arrival",
            "5 min",
            {"friendly_name": "Bus 42", "route_name": "42", "destination": "Downtown"},
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "BUS INFO" in fragment  # title
        assert "ROUTE" in fragment  # row labels are caps, like the title
        assert ">42<" in fragment
        assert "Downtown" in fragment
        assert "5 min" in fragment  # 'state' special key -> entity state

    def test_state_special_key_uses_entity_state(self, ctx):
        """'state' key returns the entity state, not a 'state' attribute."""
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={"attributes": [{"key": "state", "label": "Arrives"}]},
            )
        )
        entity = make_entity(
            "sensor.bus_arrival", "5 min", {"friendly_name": "Bus", "state": "wrong"}
        )
        fragment = widget.render_html(ctx, make_state(entity))
        assert "5 min" in fragment
        assert "wrong" not in fragment

    def test_render_without_entity_shows_placeholders(self, ctx):
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.nonexistent",
                options={"attributes": [{"key": "foo", "label": "Foo"}]},
            )
        )
        fragment = widget.render_html(ctx, make_state())
        assert "FOO" in fragment  # row labels are caps
        assert "--" in fragment

    def test_format_value_types(self):
        widget = AttributeListWidget(
            WidgetConfig(widget_type="attribute_list", slot=0, options={"attributes": []})
        )
        assert widget._format_value(None) == "--"
        assert widget._format_value(True) == "Yes"
        assert widget._format_value(False) == "No"
        assert widget._format_value(42.0) == "42"
        assert widget._format_value(42.5) == "42.5"
        assert widget._format_value("hello") == "hello"
        assert widget._format_value([1, 2, 3]) == "[3 items]"
        assert widget._format_value({"a": 1}) == "{1 keys}"

    def test_no_attributes_falls_back_to_friendly_name_title(self, ctx):
        widget = AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=0,
                entity_id="sensor.bus_arrival",
                options={"attributes": []},
            )
        )
        entity = make_entity("sensor.bus_arrival", "5 min", {"friendly_name": "Bus 42"})
        fragment = widget.render_html(ctx, make_state(entity))
        assert "BUS 42" in fragment
