"""Tests for the screen_builder module."""

from __future__ import annotations

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
    LAYOUT_HERO,
)
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.screen_builder import (
    CONF_ASSIGNED_VIEWS,
    LAYOUT_CLASSES,
    build_layout,
    build_screens,
    migrate_options,
    screen_name_at,
)
from custom_components.geekmagic.widgets.clock import ClockWidget


class FakeStore:
    """Stand-in for GeekMagicStore used in tests."""

    def __init__(self, views: dict[str, dict]) -> None:
        self._views = views

    def get_view(self, view_id: str):
        return self._views.get(view_id)


class TestMigrateOptions:
    def test_already_in_new_format_is_unchanged(self):
        options = {CONF_SCREENS: [{"name": "A", CONF_LAYOUT: LAYOUT_GRID_2X2}]}
        assert migrate_options(options) is options

    def test_legacy_options_get_wrapped_in_screens(self):
        legacy = {CONF_LAYOUT: LAYOUT_HERO, CONF_WIDGETS: [{"type": "clock", "slot": 0}]}
        migrated = migrate_options(legacy)
        assert CONF_SCREENS in migrated
        assert migrated[CONF_SCREENS][0][CONF_LAYOUT] == LAYOUT_HERO

    def test_legacy_empty_options_get_default_clock(self):
        migrated = migrate_options({})
        assert migrated[CONF_SCREENS][0][CONF_WIDGETS] == [{"type": "clock", "slot": 0}]


class TestBuildLayout:
    def test_returns_correct_layout_class_for_known_type(self):
        layout = build_layout({CONF_LAYOUT: LAYOUT_HERO, CONF_WIDGETS: []})
        assert isinstance(layout, HeroLayout)

    def test_falls_back_to_grid_2x2_for_unknown_type(self):
        layout = build_layout({CONF_LAYOUT: "totally-made-up", CONF_WIDGETS: []})
        assert isinstance(layout, Grid2x2)

    def test_wires_widget_into_slot(self):
        layout = build_layout(
            {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: [{"type": "clock", "slot": 1}]}
        )
        assert isinstance(layout.slots[1].widget, ClockWidget)
        assert layout.slots[0].widget is None

    def test_skips_widget_in_out_of_range_slot(self):
        layout = build_layout(
            {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: [{"type": "clock", "slot": 99}]}
        )
        assert all(slot.widget is None for slot in layout.slots)

    def test_skips_unknown_widget_type(self):
        layout = build_layout(
            {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: [{"type": "not-real", "slot": 0}]}
        )
        assert layout.slots[0].widget is None

    def test_color_list_is_coerced_to_rgb_tuple(self):
        layout = build_layout(
            {
                CONF_LAYOUT: LAYOUT_GRID_2X2,
                CONF_WIDGETS: [{"type": "clock", "slot": 0, "color": [10, 20, 30]}],
            }
        )
        widget = layout.slots[0].widget
        assert widget is not None
        assert widget.config.color == (10, 20, 30)

    def test_empty_widget_list_gets_default_clock(self):
        layout = build_layout({CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []})
        assert isinstance(layout.slots[0].widget, ClockWidget)


class TestBuildScreens:
    def test_legacy_screens_path(self):
        options = {
            CONF_SCREENS: [
                {"name": "Home", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []},
                {"name": "Office", CONF_LAYOUT: LAYOUT_HERO, CONF_WIDGETS: []},
            ]
        }
        pairs = build_screens(options, store=None)
        assert [name for name, _ in pairs] == ["Home", "Office"]
        assert isinstance(pairs[0][1], Grid2x2)
        assert isinstance(pairs[1][1], HeroLayout)

    def test_global_views_path(self):
        store = FakeStore(
            {
                "v1": {"name": "Dash", CONF_LAYOUT: LAYOUT_HERO, CONF_WIDGETS: []},
                "v2": {"name": "Stats", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []},
            }
        )
        pairs = build_screens({CONF_ASSIGNED_VIEWS: ["v1", "v2"]}, store=store)
        assert [name for name, _ in pairs] == ["Dash", "Stats"]

    def test_missing_view_is_skipped(self):
        store = FakeStore({"v1": {"name": "Only", CONF_LAYOUT: LAYOUT_HERO, CONF_WIDGETS: []}})
        pairs = build_screens({CONF_ASSIGNED_VIEWS: ["v1", "ghost"]}, store=store)
        assert len(pairs) == 1
        assert pairs[0][0] == "Only"

    def test_global_views_without_store_falls_back_to_legacy(self):
        options = {
            CONF_ASSIGNED_VIEWS: ["v1"],
            CONF_SCREENS: [{"name": "Fallback", CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: []}],
        }
        pairs = build_screens(options, store=None)
        assert pairs[0][0] == "Fallback"


class TestScreenNameAt:
    def test_legacy_screen_name(self):
        options = {CONF_SCREENS: [{"name": "Home"}, {"name": "Office"}]}
        assert screen_name_at(options, 1, store=None) == "Office"

    def test_legacy_screen_out_of_range(self):
        options = {CONF_SCREENS: [{"name": "Home"}]}
        assert screen_name_at(options, 5, store=None) == "Unknown"

    def test_global_view_name(self):
        store = FakeStore({"v1": {"name": "Dash"}})
        assert screen_name_at({CONF_ASSIGNED_VIEWS: ["v1"]}, 0, store=store) == "Dash"

    def test_global_view_unknown_without_store(self):
        assert screen_name_at({CONF_ASSIGNED_VIEWS: ["v1"]}, 0, store=None) == "Unknown"


def test_layout_classes_registry_covers_known_layouts():
    # Sanity: registry contains entries for every layout constant string used in tests
    assert LAYOUT_GRID_2X2 in LAYOUT_CLASSES
    assert LAYOUT_HERO in LAYOUT_CLASSES
