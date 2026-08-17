"""Tests for the view → layout construction seam.

``views.build_layout`` is the single adapter the coordinator and the
websocket preview both go through, so these tests pin the coercion and
skip rules directly rather than through either caller.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    LAYOUT_FULLSCREEN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_3X3,
    LAYOUT_HERO,
    LAYOUT_HERO_BL,
    LAYOUT_HERO_BR,
    LAYOUT_HERO_SIMPLE,
    LAYOUT_HERO_TL,
    LAYOUT_HERO_TR,
    LAYOUT_SIDEBAR_LEFT,
    LAYOUT_SIDEBAR_RIGHT,
    LAYOUT_SPLIT_H,
    LAYOUT_SPLIT_H_1_2,
    LAYOUT_SPLIT_H_2_1,
    LAYOUT_SPLIT_V,
    LAYOUT_THREE_COLUMN,
    LAYOUT_THREE_ROW,
    THEME_CLASSIC,
    THEME_WATCHOS,
)
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid3x3
from custom_components.geekmagic.views import (
    LAYOUT_CLASSES,
    LAYOUT_SLOT_COUNTS,
    build_layout,
)

# The slot-count table the panel used to be handed from a hand-written
# literal in const.py, key order included: the websocket ``config``
# payload is built from it and the frontend renders the layout picker in
# ``Object.entries`` order. Pinned here so deriving it from the layout
# classes cannot silently change what the panel sees.
EXPECTED_SLOT_COUNTS = [
    ("grid_2x2", 4),
    ("grid_2x3", 6),
    ("grid_3x2", 6),
    ("grid_3x3", 9),
    ("hero", 4),
    ("split_horizontal", 2),
    ("split_vertical", 2),
    ("three_column", 3),
    ("three_row", 3),
    ("split_h_1_2", 2),
    ("split_h_2_1", 2),
    ("sidebar_left", 4),
    ("sidebar_right", 4),
    ("hero_corner_tl", 6),
    ("hero_corner_tr", 6),
    ("hero_corner_bl", 6),
    ("hero_corner_br", 6),
    ("hero_simple", 2),
    ("fullscreen", 1),
]


def _slot_widgets(layout):
    """Widget-per-slot mapping, the way callers read it back."""
    return {slot.index: slot.widget for slot in layout.slots if slot.widget is not None}


class TestLayoutSlotCounts:
    """The derived slot-count table replacing the const.py literal."""

    def test_matches_the_published_table_including_order(self):
        assert list(LAYOUT_SLOT_COUNTS.items()) == EXPECTED_SLOT_COUNTS

    def test_registry_and_counts_cover_the_same_layouts(self):
        assert list(LAYOUT_CLASSES) == list(LAYOUT_SLOT_COUNTS)

    def test_every_layout_constant_is_registered(self):
        for layout_type in (
            LAYOUT_GRID_2X2,
            LAYOUT_GRID_3X3,
            LAYOUT_HERO,
            LAYOUT_HERO_SIMPLE,
            LAYOUT_HERO_TL,
            LAYOUT_HERO_TR,
            LAYOUT_HERO_BL,
            LAYOUT_HERO_BR,
            LAYOUT_SIDEBAR_LEFT,
            LAYOUT_SIDEBAR_RIGHT,
            LAYOUT_SPLIT_H,
            LAYOUT_SPLIT_H_1_2,
            LAYOUT_SPLIT_H_2_1,
            LAYOUT_SPLIT_V,
            LAYOUT_THREE_COLUMN,
            LAYOUT_THREE_ROW,
            LAYOUT_FULLSCREEN,
        ):
            assert layout_type in LAYOUT_CLASSES


class TestLayoutSelection:
    """Layout type resolution."""

    def test_named_layout(self):
        layout = build_layout({"layout": LAYOUT_GRID_3X3}, default_theme=THEME_WATCHOS)
        assert isinstance(layout, Grid3x3)
        assert layout.get_slot_count() == 9

    def test_unknown_layout_falls_back_to_grid_2x2(self):
        layout = build_layout({"layout": "not_a_layout"}, default_theme=THEME_WATCHOS)
        assert isinstance(layout, Grid2x2)

    def test_missing_layout_falls_back_to_grid_2x2(self):
        assert isinstance(build_layout({}, default_theme=THEME_WATCHOS), Grid2x2)


class TestTheme:
    """Theme resolution and the per-caller default."""

    def test_view_theme_wins(self):
        layout = build_layout({"theme": THEME_CLASSIC}, default_theme=THEME_WATCHOS)
        assert layout.theme.name == THEME_CLASSIC

    def test_default_theme_used_when_view_names_none(self):
        assert build_layout({}, default_theme=THEME_WATCHOS).theme.name == THEME_WATCHOS
        assert build_layout({}, default_theme=THEME_CLASSIC).theme.name == THEME_CLASSIC


class TestWidgetPlacement:
    """Which widget dicts make it into slots."""

    def test_widget_placed_in_its_slot(self):
        layout = build_layout(
            {"widgets": [{"type": "clock", "slot": 2}]}, default_theme=THEME_WATCHOS
        )
        widgets = _slot_widgets(layout)
        assert set(widgets) == {2}
        assert widgets[2].config.widget_type == "clock"

    def test_unknown_widget_type_skipped(self):
        layout = build_layout(
            {"widgets": [{"type": "no_such_widget", "slot": 0}, {"type": "clock", "slot": 1}]},
            default_theme=THEME_WATCHOS,
        )
        assert set(_slot_widgets(layout)) == {1}

    def test_out_of_range_slot_skipped(self):
        layout = build_layout(
            {
                "layout": LAYOUT_GRID_2X2,
                "widgets": [{"type": "clock", "slot": 0}, {"type": "clock", "slot": 7}],
            },
            default_theme=THEME_WATCHOS,
        )
        assert set(_slot_widgets(layout)) == {0}

    def test_missing_type_defaults_to_text(self):
        layout = build_layout({"widgets": [{"slot": 0}]}, default_theme=THEME_WATCHOS)
        assert _slot_widgets(layout)[0].config.widget_type == "text"

    def test_missing_slot_defaults_to_zero(self):
        layout = build_layout({"widgets": [{"type": "clock"}]}, default_theme=THEME_WATCHOS)
        assert set(_slot_widgets(layout)) == {0}

    def test_uncoercible_slot_skipped(self):
        """A slot that isn't a number costs its own cell, not the screen."""
        layout = build_layout(
            {"widgets": [{"type": "clock", "slot": "abc"}, {"type": "clock", "slot": 1}]},
            default_theme=THEME_WATCHOS,
        )
        assert set(_slot_widgets(layout)) == {1}

    def test_null_slot_skipped(self):
        layout = build_layout(
            {"widgets": [{"type": "clock", "slot": None}, {"type": "clock", "slot": 2}]},
            default_theme=THEME_WATCHOS,
        )
        assert set(_slot_widgets(layout)) == {2}


class TestWidgetCoercion:
    """Per-widget field coercion, unified on the stricter coordinator rules."""

    def _config(self, widget_config):
        layout = build_layout({"widgets": [widget_config]}, default_theme=THEME_WATCHOS)
        return _slot_widgets(layout)[0].config

    def test_slot_coerced_to_int(self):
        layout = build_layout(
            {"widgets": [{"type": "clock", "slot": "3"}]}, default_theme=THEME_WATCHOS
        )
        widgets = _slot_widgets(layout)
        assert set(widgets) == {3}
        assert widgets[3].config.slot == 3

    def test_entity_id_and_label_coerced_to_str(self):
        config = self._config({"type": "entity", "slot": 0, "entity_id": "sensor.a", "label": 42})
        assert config.entity_id == "sensor.a"
        assert config.label == "42"

    def test_absent_entity_id_and_label_stay_none(self):
        config = self._config({"type": "clock", "slot": 0})
        assert config.entity_id is None
        assert config.label is None

    def test_valid_color_becomes_int_tuple(self):
        assert self._config({"type": "clock", "slot": 0, "color": [255, 128, "0"]}).color == (
            255,
            128,
            0,
        )

    def test_color_tuple_accepted(self):
        assert self._config({"type": "clock", "slot": 0, "color": (1, 2, 3)}).color == (1, 2, 3)

    def test_short_color_rejected(self):
        assert self._config({"type": "clock", "slot": 0, "color": [255, 128]}).color is None

    def test_non_numeric_color_rejected(self):
        assert self._config({"type": "clock", "slot": 0, "color": "red"}).color is None
        assert self._config({"type": "clock", "slot": 0, "color": ["r", "g", "b"]}).color is None

    def test_absent_color_is_none(self):
        assert self._config({"type": "clock", "slot": 0}).color is None

    def test_options_passed_through(self):
        options = {"timezone": "Europe/Paris", "format": "24h"}
        assert self._config({"type": "clock", "slot": 0, "options": options}).options == options

    def test_null_options_become_empty_dict(self):
        assert self._config({"type": "clock", "slot": 0, "options": None}).options == {}

    def test_absent_options_become_empty_dict(self):
        assert self._config({"type": "clock", "slot": 0}).options == {}


class TestDefaultWidgets:
    """The coordinator's "never show an empty screen" fallback."""

    def test_applied_when_widget_list_is_empty(self):
        layout = build_layout(
            {"widgets": []},
            default_theme=THEME_WATCHOS,
            default_widgets=[{"type": "clock", "slot": 0}],
        )
        assert _slot_widgets(layout)[0].config.widget_type == "clock"

    def test_applied_when_widgets_key_is_absent(self):
        layout = build_layout(
            {},
            default_theme=THEME_WATCHOS,
            default_widgets=[{"type": "clock", "slot": 0}],
        )
        assert set(_slot_widgets(layout)) == {0}

    def test_not_applied_when_the_view_has_widgets(self):
        layout = build_layout(
            {"widgets": [{"type": "text", "slot": 1}]},
            default_theme=THEME_WATCHOS,
            default_widgets=[{"type": "clock", "slot": 0}],
        )
        widgets = _slot_widgets(layout)
        assert set(widgets) == {1}
        assert widgets[1].config.widget_type == "text"

    def test_empty_view_stays_empty_without_defaults(self):
        assert _slot_widgets(build_layout({}, default_theme=THEME_CLASSIC)) == {}
