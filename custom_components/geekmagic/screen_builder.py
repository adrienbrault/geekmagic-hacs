"""Build Layout + Widget trees from a coordinator's options or a raw view config.

Single source of truth for:
- the layout-type → Layout-class registry
- the legacy → new options format migration
- the two-format read (assigned_views via store, or inline screens)
- per-widget instantiation (registry lookup, color coercion, default widget)
- per-view theme resolution

Callers (coordinator, websocket preview, configuration preview) hand in a
config dict; they don't need to know which format it is, what the registries
are, or how widgets get wired into slots.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from .const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREEN_THEME,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    LAYOUT_FULLSCREEN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
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
    THEME_WATCHOS,
)
from .layouts.corner_hero import HeroCornerBL, HeroCornerBR, HeroCornerTL, HeroCornerTR
from .layouts.fullscreen import FullscreenLayout
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from .layouts.hero import HeroLayout
from .layouts.hero_simple import HeroSimpleLayout
from .layouts.sidebar import SidebarLeft, SidebarRight
from .layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from .widgets import WIDGET_CLASSES
from .widgets.base import WidgetConfig
from .widgets.theme import get_theme

if TYPE_CHECKING:
    from .layouts.base import Layout

_LOGGER = logging.getLogger(__name__)

# Config key for new global views format
CONF_ASSIGNED_VIEWS = "assigned_views"


LAYOUT_CLASSES: dict[str, type[Layout]] = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_HERO_SIMPLE: HeroSimpleLayout,
    LAYOUT_SPLIT_H: SplitHorizontal,
    LAYOUT_SPLIT_H_1_2: SplitHorizontal1To2,
    LAYOUT_SPLIT_H_2_1: SplitHorizontal2To1,
    LAYOUT_SPLIT_V: SplitVertical,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
    LAYOUT_THREE_ROW: ThreeRowLayout,
    LAYOUT_SIDEBAR_LEFT: SidebarLeft,
    LAYOUT_SIDEBAR_RIGHT: SidebarRight,
    LAYOUT_HERO_TL: HeroCornerTL,
    LAYOUT_HERO_TR: HeroCornerTR,
    LAYOUT_HERO_BL: HeroCornerBL,
    LAYOUT_HERO_BR: HeroCornerBR,
    LAYOUT_FULLSCREEN: FullscreenLayout,
}


def migrate_options(options: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy single-screen options to the multi-screen format.

    Idempotent: options already in new format are returned unchanged.
    """
    if CONF_SCREENS in options:
        return options

    return {
        CONF_REFRESH_INTERVAL: options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
        CONF_SCREENS: [
            {
                "name": "Screen 1",
                CONF_LAYOUT: options.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
                CONF_WIDGETS: options.get(CONF_WIDGETS, [{"type": "clock", "slot": 0}]),
            }
        ],
    }


def build_layout(view_config: dict[str, Any]) -> Layout:
    """Build one Layout (with theme + widgets wired into slots) from a view config.

    A view config is the dict shape used by both inline `screens` entries and
    entries in the global view store: `{layout, theme, widgets, name}`.
    """
    layout_type = view_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
    layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)
    layout = layout_class()

    theme_name = view_config.get(CONF_SCREEN_THEME, THEME_WATCHOS)
    layout.theme = get_theme(theme_name)

    widgets_config = view_config.get(CONF_WIDGETS, []) or [{"type": "clock", "slot": 0}]

    for widget_config in widgets_config:
        widget_type = str(widget_config.get("type", "text"))
        slot = int(widget_config.get("slot", 0))

        if slot >= layout.get_slot_count():
            continue

        widget_class = WIDGET_CLASSES.get(widget_type)
        if widget_class is None:
            continue

        entity_id = widget_config.get("entity_id")
        label = widget_config.get("label")
        raw_color = widget_config.get("color")
        widget_options = widget_config.get("options") or {}

        parsed_color: tuple[int, int, int] | None = None
        if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
            parsed_color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))

        config = WidgetConfig(
            widget_type=widget_type,
            slot=slot,
            entity_id=str(entity_id) if entity_id is not None else None,
            label=str(label) if label is not None else None,
            color=parsed_color,
            options=cast("dict[str, Any]", widget_options),
        )
        layout.set_widget(slot, widget_class(config))

    return layout


def build_screens(
    options: dict[str, Any],
    store: Any,
) -> list[tuple[str, Layout]]:
    """Build (name, Layout) pairs for every screen described by options.

    Handles both formats:
      - new: `assigned_views: [view_id, ...]` resolved via `store`
      - legacy: `screens: [{name, layout, widgets, ...}]` inline

    Missing views are skipped with a warning. If the new format is requested
    but no store is available, falls back to the legacy format.
    """
    assigned_views = options.get(CONF_ASSIGNED_VIEWS, [])
    if assigned_views:
        if store is None:
            _LOGGER.warning("Store not available, falling back to legacy config")
            return _build_legacy_screens(options)
        return _build_from_global_views(assigned_views, store)
    return _build_legacy_screens(options)


def _build_from_global_views(view_ids: list[str], store: Any) -> list[tuple[str, Layout]]:
    """Resolve view IDs against the store and build their layouts."""
    _LOGGER.debug("Setting up %d view(s) from global store", len(view_ids))
    results: list[tuple[str, Layout]] = []
    for i, view_id in enumerate(view_ids):
        view_config = store.get_view(view_id)
        if not view_config:
            _LOGGER.warning("View %s not found in store, skipping", view_id)
            continue
        name = view_config.get("name", f"View {i + 1}")
        layout = build_layout(view_config)
        results.append((name, layout))
        _LOGGER.debug(
            "Created view %d '%s' with layout %s (%d slots)",
            i,
            name,
            view_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
            layout.get_slot_count(),
        )
    return results


def _build_legacy_screens(options: dict[str, Any]) -> list[tuple[str, Layout]]:
    """Build layouts from inline `screens` entries."""
    screens = options.get(CONF_SCREENS, [])
    _LOGGER.debug("Setting up %d screen(s) from legacy config", len(screens))
    results: list[tuple[str, Layout]] = []
    for i, screen_config in enumerate(screens):
        name = screen_config.get("name", f"Screen {i + 1}")
        layout = build_layout(screen_config)
        results.append((name, layout))
        _LOGGER.debug(
            "Created screen %d '%s' with layout %s (%d slots)",
            i,
            name,
            screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
            layout.get_slot_count(),
        )
    return results


def screen_name_at(
    options: dict[str, Any],
    index: int,
    store: Any,
) -> str:
    """Return the configured name of the screen at `index`, or 'Unknown'."""
    assigned_views = options.get(CONF_ASSIGNED_VIEWS, [])
    if assigned_views:
        if 0 <= index < len(assigned_views) and store is not None:
            view = store.get_view(assigned_views[index])
            if view:
                return view.get("name", f"View {index + 1}")
        return "Unknown"

    screens = options.get(CONF_SCREENS, [])
    if 0 <= index < len(screens):
        return screens[index].get("name", f"Screen {index + 1}")
    return "Unknown"
