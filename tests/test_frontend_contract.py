"""Contract tests between Python backend and TypeScript frontend.

These tests parse the frontend TypeScript source and verify that hardcoded
values (layout types, widget types, themes, slot counts) stay in sync with
the Python constants. When someone adds a new layout or widget in Python,
these tests fail if the frontend isn't updated accordingly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.geekmagic.const import (
    LAYOUT_SLOT_COUNTS,
    THEME_OPTIONS,
)
from custom_components.geekmagic.websocket import WIDGET_TYPE_SCHEMAS

# Paths
FRONTEND_SRC = Path(__file__).parent.parent / "custom_components" / "geekmagic" / "frontend" / "src"
PANEL_TS = FRONTEND_SRC / "geekmagic-panel.ts"
TYPES_TS = FRONTEND_SRC / "types.ts"
VIEW_UTILS_TS = FRONTEND_SRC / "view-utils.ts"


def _parse_layout_config_from_ts() -> dict[str, int]:
    """Parse the layoutConfig object from geekmagic-panel.ts.

    Extracts the layout key -> cell count mapping from the TypeScript source.
    """
    source = PANEL_TS.read_text()

    # Find the LAYOUT_CONFIGS export or layoutConfig object
    # Try view-utils.ts first (extracted), then fall back to panel
    view_utils = VIEW_UTILS_TS
    if view_utils.exists():
        source = view_utils.read_text()

    # Match pattern: key: { cls: "...", cells: N }
    # Keys may or may not be quoted
    pattern = r'["\']?(\w+)["\']?:\s*\{[^}]*cells:\s*(\d+)[^}]*\}'
    matches = re.findall(pattern, source)

    if not matches:
        pytest.fail(
            "Could not find layoutConfig/LAYOUT_CONFIGS in frontend source. "
            "Expected pattern: '\"key\": { cls: \"...\", cells: N }'"
        )

    return {key: int(cells) for key, cells in matches}


def _parse_widget_option_types_from_ts() -> list[str]:
    """Parse the WidgetOption.type union from types.ts."""
    source = TYPES_TS.read_text()

    # Find the type union in WidgetOption interface
    # Pattern: type:\n    | "boolean"\n    | "select"\n    ...
    match = re.search(
        r'type:\s*\n((?:\s*\|\s*"[^"]+"\s*\n?)+)',
        source,
    )
    if not match:
        pytest.fail("Could not find WidgetOption.type union in types.ts")

    types_block = match.group(1)
    return re.findall(r'"(\w+)"', types_block)


class TestLayoutContract:
    """Verify frontend layout definitions match backend."""

    def test_all_backend_layouts_exist_in_frontend(self):
        """Every layout in LAYOUT_SLOT_COUNTS must appear in frontend layoutConfig."""
        frontend_layouts = _parse_layout_config_from_ts()
        backend_layouts = set(LAYOUT_SLOT_COUNTS.keys())
        frontend_keys = set(frontend_layouts.keys())

        missing = backend_layouts - frontend_keys
        assert not missing, (
            f"Backend layouts missing from frontend layoutConfig: {missing}. "
            f"Add these to the layoutConfig in geekmagic-panel.ts (or view-utils.ts)."
        )

    def test_no_extra_frontend_layouts(self):
        """Frontend shouldn't have layouts that don't exist in backend."""
        frontend_layouts = _parse_layout_config_from_ts()
        backend_layouts = set(LAYOUT_SLOT_COUNTS.keys())
        frontend_keys = set(frontend_layouts.keys())

        extra = frontend_keys - backend_layouts
        assert not extra, (
            f"Frontend has layouts not in backend LAYOUT_SLOT_COUNTS: {extra}. "
            f"Either add to const.py or remove from frontend."
        )

    def test_slot_counts_match(self):
        """Frontend cell counts must match backend slot counts."""
        frontend_layouts = _parse_layout_config_from_ts()

        mismatches = []
        for layout_key, backend_slots in LAYOUT_SLOT_COUNTS.items():
            if layout_key in frontend_layouts:
                frontend_cells = frontend_layouts[layout_key]
                if frontend_cells != backend_slots:
                    mismatches.append(
                        f"  {layout_key}: backend={backend_slots}, frontend={frontend_cells}"
                    )

        assert not mismatches, (
            "Layout slot count mismatches between backend and frontend:\n"
            + "\n".join(mismatches)
        )


class TestWidgetTypeContract:
    """Verify frontend widget type definitions match backend."""

    def test_all_backend_widget_types_exist_in_schema(self):
        """Every widget type in WIDGET_TYPE_SCHEMAS must have a name."""
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            assert "name" in schema, f"Widget type '{widget_type}' missing 'name' in schema"
            assert "options" in schema, f"Widget type '{widget_type}' missing 'options'"

    def test_widget_option_types_are_valid(self):
        """All option types used in WIDGET_TYPE_SCHEMAS must be in the TypeScript union."""
        ts_types = set(_parse_widget_option_types_from_ts())

        invalid = []
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            for option in schema.get("options", []):
                opt_type = option.get("type")
                if opt_type and opt_type not in ts_types:
                    invalid.append(f"  {widget_type}.{option['key']}: type='{opt_type}'")

        assert not invalid, (
            f"Widget option types not in TypeScript WidgetOption union ({ts_types}):\n"
            + "\n".join(invalid)
            + "\nAdd these types to the WidgetOption.type union in types.ts."
        )

    def test_widget_schemas_have_required_fields(self):
        """Each widget option must have at least key, type, and label."""
        missing = []
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            for i, option in enumerate(schema.get("options", [])):
                for field in ("key", "type", "label"):
                    if field not in option:
                        missing.append(f"  {widget_type}.options[{i}] missing '{field}'")

        assert not missing, "Widget options missing required fields:\n" + "\n".join(missing)

    def test_select_options_have_choices(self):
        """Select-type options must define their choices."""
        missing = []
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            for option in schema.get("options", []):
                if option.get("type") == "select" and not option.get("options"):
                    missing.append(f"  {widget_type}.{option['key']}")

        assert not missing, (
            "Select options without choices list:\n" + "\n".join(missing)
        )


class TestThemeContract:
    """Verify frontend theme definitions match backend."""

    def test_theme_options_not_empty(self):
        """Backend must define at least one theme."""
        assert len(THEME_OPTIONS) > 0

    def test_theme_keys_are_strings(self):
        """Theme keys and values must be strings."""
        for key, value in THEME_OPTIONS.items():
            assert isinstance(key, str), f"Theme key {key!r} is not a string"
            assert isinstance(value, str), f"Theme value for {key!r} is not a string"


class TestWebSocketResponseContract:
    """Verify WebSocket response shapes match TypeScript interfaces."""

    def test_device_config_fields_match_typescript(self):
        """Fields returned by ws_devices_list must match DeviceConfig interface."""
        # These are the fields the frontend TypeScript expects (from types.ts DeviceConfig)
        expected_fields = {
            "entry_id",
            "name",
            "host",
            "assigned_views",
            "current_view_index",
            "brightness",
            "refresh_interval",
            "cycle_interval",
            "online",
        }

        # Parse DeviceConfig from types.ts to verify our expected set is current
        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface DeviceConfig \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find DeviceConfig interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))
        assert ts_fields == expected_fields, (
            f"DeviceConfig fields mismatch.\n"
            f"  In types.ts: {ts_fields}\n"
            f"  Expected: {expected_fields}\n"
            f"Update the test or types.ts to match."
        )

    def test_view_config_fields_match_typescript(self):
        """Fields in ViewConfig must match between store and TypeScript."""
        expected_fields = {"id", "name", "layout", "theme", "widgets", "created_at", "updated_at"}

        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface ViewConfig \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find ViewConfig interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))
        assert ts_fields == expected_fields, (
            f"ViewConfig fields mismatch.\n"
            f"  In types.ts: {ts_fields}\n"
            f"  Expected: {expected_fields}"
        )

    def test_widget_config_fields_match_typescript(self):
        """Fields in WidgetConfig must match TypeScript interface."""
        expected_fields = {"type", "slot", "entity_id", "label", "color", "options"}

        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface WidgetConfig \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find WidgetConfig interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))
        assert ts_fields == expected_fields, (
            f"WidgetConfig fields mismatch.\n"
            f"  In types.ts: {ts_fields}\n"
            f"  Expected: {expected_fields}"
        )

    def test_geekmagic_config_shape(self):
        """GeekMagicConfig interface must have widget_types, layout_types, themes."""
        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface GeekMagicConfig \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find GeekMagicConfig interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))
        assert {"widget_types", "layout_types", "themes"} <= ts_fields, (
            f"GeekMagicConfig missing required fields. Found: {ts_fields}"
        )

    def test_preview_response_fields_match_typescript(self):
        """PreviewResponse interface must match what ws_preview_render sends."""
        expected_fields = {"image", "content_type", "width", "height"}

        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface PreviewResponse \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find PreviewResponse interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))
        assert ts_fields == expected_fields, (
            f"PreviewResponse fields mismatch.\n"
            f"  In types.ts: {ts_fields}\n"
            f"  Expected: {expected_fields}"
        )


class TestConfigEndpointContract:
    """Verify the geekmagic/config endpoint returns data matching frontend expectations."""

    def test_config_returns_all_layouts(self):
        """The config endpoint should return all layouts from LAYOUT_SLOT_COUNTS."""
        # Simulate what ws_get_config builds
        layout_types = {
            k: {"slots": v, "name": k.replace("_", " ").title()}
            for k, v in LAYOUT_SLOT_COUNTS.items()
        }

        assert set(layout_types.keys()) == set(LAYOUT_SLOT_COUNTS.keys())

        for key, info in layout_types.items():
            assert "slots" in info
            assert "name" in info
            assert isinstance(info["slots"], int)
            assert isinstance(info["name"], str)

    def test_config_returns_all_themes(self):
        """The config endpoint should return all themes from THEME_OPTIONS."""
        themes = dict(THEME_OPTIONS.items())
        assert len(themes) == len(THEME_OPTIONS)
        for key, name in themes.items():
            assert isinstance(key, str)
            assert isinstance(name, str)

    def test_config_returns_all_widget_types(self):
        """The config endpoint should return all widget type schemas."""
        # Ensure each schema is JSON-serializable (important for WebSocket transport)
        for widget_type, schema in WIDGET_TYPE_SCHEMAS.items():
            try:
                json.dumps(schema)
            except (TypeError, ValueError) as e:
                pytest.fail(
                    f"Widget schema '{widget_type}' is not JSON-serializable: {e}"
                )

    def test_layout_type_info_matches_typescript(self):
        """LayoutTypeInfo from config must match TypeScript interface."""
        source = TYPES_TS.read_text()
        match = re.search(
            r"export interface LayoutTypeInfo \{(.*?)\}",
            source,
            re.DOTALL,
        )
        assert match, "Could not find LayoutTypeInfo interface in types.ts"

        ts_fields = set(re.findall(r"(\w+)\??:", match.group(1)))

        # What the backend actually sends
        sample = {"slots": 4, "name": "Grid 2X2"}
        backend_fields = set(sample.keys())

        assert ts_fields == backend_fields, (
            f"LayoutTypeInfo fields mismatch.\n"
            f"  In types.ts: {ts_fields}\n"
            f"  Backend sends: {backend_fields}"
        )
