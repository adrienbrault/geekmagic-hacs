"""View → layout construction.

A *view* is the stored, JSON-shaped definition of one screen: a layout
type, a theme name and a list of widget dicts. A *screen* is what that
definition becomes at runtime — a ``Layout`` with widgets in its slots.
This module owns the single adapter between the two.

Everything that turns a view into a screen goes through
``build_layout``: the coordinator when it materializes a device's
assigned views, and the websocket preview when the panel asks for a
render of an unsaved edit. Both used to carry their own copy of the
loop, and the copies had already drifted (differing coercion, differing
defaults). Keeping one path means the editor preview cannot disagree
with the device about what a view means.

The two callers still differ in what they want from an *empty* view, so
that stays at the seam as explicit parameters (``default_theme``,
``default_widgets``) rather than as branches inside the loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .const import (
    CONF_LAYOUT,
    CONF_SCREEN_THEME,
    CONF_WIDGETS,
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

# Insertion order is part of the panel's contract: the websocket
# ``geekmagic/config`` payload is built from this registry and the
# frontend renders the layout picker in ``Object.entries`` order.
LAYOUT_CLASSES: dict[str, type[Layout]] = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT_H: SplitHorizontal,
    LAYOUT_SPLIT_V: SplitVertical,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
    LAYOUT_THREE_ROW: ThreeRowLayout,
    LAYOUT_SPLIT_H_1_2: SplitHorizontal1To2,
    LAYOUT_SPLIT_H_2_1: SplitHorizontal2To1,
    LAYOUT_SIDEBAR_LEFT: SidebarLeft,
    LAYOUT_SIDEBAR_RIGHT: SidebarRight,
    LAYOUT_HERO_TL: HeroCornerTL,
    LAYOUT_HERO_TR: HeroCornerTR,
    LAYOUT_HERO_BL: HeroCornerBL,
    LAYOUT_HERO_BR: HeroCornerBR,
    LAYOUT_HERO_SIMPLE: HeroSimpleLayout,
    LAYOUT_FULLSCREEN: FullscreenLayout,
}

# Slot counts are a property of the layout classes, not a table to keep
# in sync with them: ``get_slot_count`` needs an instance, so the
# registry is walked once at import (pure geometry, no rendering).
LAYOUT_SLOT_COUNTS: dict[str, int] = {
    layout_type: layout_class().get_slot_count()
    for layout_type, layout_class in LAYOUT_CLASSES.items()
}


def layout_slot_count(layout_type: str) -> int:
    """Return how many widget slots a layout type exposes.

    Unknown types report the slot count of the fallback layout, matching
    what ``build_layout`` would actually construct for them.
    """
    return LAYOUT_SLOT_COUNTS.get(layout_type, LAYOUT_SLOT_COUNTS[LAYOUT_GRID_2X2])


def _parse_color(raw_color: Any) -> tuple[int, int, int] | None:
    """Coerce a stored color to an RGB tuple, or None when unusable."""
    if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
        try:
            return (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))
        except (TypeError, ValueError):
            return None
    return None


def build_layout(
    view_config: dict[str, Any],
    *,
    default_theme: str,
    default_widgets: list[dict[str, Any]] | None = None,
) -> Layout:
    """Build a runtime screen from a stored view definition.

    Args:
        view_config: View dict — ``layout``, ``theme`` and ``widgets``
            keys, as stored by the panel or the legacy screens option.
        default_theme: Theme applied when the view names none.
        default_widgets: Widget dicts used when the view has an empty
            widget list. ``None`` leaves an empty view empty.

    Returns:
        A layout with its theme set and its slots populated. Callers
        needing the widget-per-slot mapping read ``layout.slots``.

    Unusable entries are skipped rather than raising — an unknown widget
    type or an out-of-range slot (a view authored for a roomier layout)
    costs that one cell, not the whole screen.
    """
    layout_type = view_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
    layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)
    layout = layout_class()

    layout.theme = get_theme(view_config.get(CONF_SCREEN_THEME, default_theme))

    widgets_config = view_config.get(CONF_WIDGETS, [])
    if not widgets_config and default_widgets:
        widgets_config = default_widgets

    for widget_config in widgets_config:
        widget_type = str(widget_config.get("type", "text"))
        try:
            slot = int(widget_config.get("slot", 0))
        except (TypeError, ValueError):
            # A slot that isn't a number names no cell — same class of
            # damage as an out-of-range one, same cost: this widget.
            continue

        if slot >= layout.get_slot_count():
            continue

        widget_class = WIDGET_CLASSES.get(widget_type)
        if widget_class is None:
            continue

        entity_id = widget_config.get("entity_id")
        label = widget_config.get("label")
        widget_options = widget_config.get("options") or {}

        config = WidgetConfig(
            widget_type=widget_type,
            slot=slot,
            entity_id=str(entity_id) if entity_id is not None else None,
            label=str(label) if label is not None else None,
            color=_parse_color(widget_config.get("color")),
            options=cast("dict[str, Any]", widget_options),
        )

        layout.set_widget(slot, widget_class(config))

    return layout
