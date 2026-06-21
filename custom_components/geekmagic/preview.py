"""Preview rendering for GeekMagic configuration flow."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from .const import (
    CONF_BACKGROUND_ENTITY,
    CONF_BACKGROUND_IMAGE,
    CONF_BACKGROUND_MODE,
    CONF_LAYOUT,
    CONF_TEXT_OPACITY,
    CONF_WIDGET_CONTRAST,
    CONF_WIDGETS,
    LAYOUT_CUSTOM,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
    LAYOUT_GRID_3X3,
    LAYOUT_HERO,
    LAYOUT_HERO_BL,
    LAYOUT_HERO_BR,
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
from .layouts.custom import CustomLayout
from .layouts.fullscreen import FullscreenLayout
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from .layouts.hero import HeroLayout
from .layouts.sidebar import SidebarLeft, SidebarRight
from .layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from .renderer import Renderer
from .widgets import WIDGET_CLASSES
from .widgets.base import WidgetConfig
from .widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LAYOUT_CLASSES = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
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
    LAYOUT_CUSTOM: CustomLayout,
}


@dataclass
class MockState:
    """Mock entity state for preview rendering."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


class MockStates:
    """Mock states registry for preview rendering."""

    def __init__(self) -> None:
        """Initialize the mock states registry."""
        self._states: dict[str, MockState] = {}

    def set(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> None:
        """Set a mock entity state."""
        self._states[entity_id] = MockState(
            entity_id=entity_id,
            state=state,
            attributes=attributes or {},
        )

    def get(self, entity_id: str) -> MockState | None:
        """Get a mock entity state."""
        return self._states.get(entity_id)


class MockConfig:
    """Mock Home Assistant config."""

    time_zone_obj = None


class MockHass:
    """Mock Home Assistant instance for preview rendering."""

    def __init__(self) -> None:
        """Initialize the mock Home Assistant."""
        self.states = MockStates()
        self.config = MockConfig()


def _set_mock_state_for_widget(mock: MockHass, widget_config: dict[str, Any]) -> None:
    """Set mock state for a widget based on its type.

    Args:
        mock: MockHass instance
        widget_config: Widget configuration dictionary
    """
    widget_type = widget_config.get("type", "")
    entity_id = widget_config.get("entity_id")

    if not entity_id:
        return

    # Set appropriate mock state based on widget type
    if widget_type == "entity":
        mock.states.set(
            entity_id,
            "42",
            {"unit_of_measurement": "", "friendly_name": widget_config.get("label", "Entity")},
        )
    elif widget_type == "gauge":
        mock.states.set(
            entity_id,
            "65",
            {"unit_of_measurement": "%", "friendly_name": widget_config.get("label", "Gauge")},
        )
    elif widget_type == "progress":
        mock.states.set(
            entity_id,
            "75",
            {"unit_of_measurement": "", "friendly_name": widget_config.get("label", "Progress")},
        )
    elif widget_type == "status":
        mock.states.set(
            entity_id,
            "on",
            {"friendly_name": widget_config.get("label", "Status")},
        )
    elif widget_type == "media":
        mock.states.set(
            entity_id,
            "playing",
            {
                "friendly_name": "Media Player",
                "media_title": "Sample Track",
                "media_artist": "Sample Artist",
                "media_position": 120,
                "media_duration": 300,
            },
        )
    elif widget_type == "chart":
        mock.states.set(
            entity_id,
            "23",
            {"unit_of_measurement": "°C", "friendly_name": widget_config.get("label", "Chart")},
        )
    elif widget_type == "weather":
        mock.states.set(
            entity_id,
            "sunny",
            {
                "temperature": 24,
                "humidity": 45,
                "friendly_name": "Weather",
                # Note: forecast is no longer in attributes (HA 2024.3+)
                # It's now provided via WidgetState.forecast
            },
        )
    elif widget_type == "text" and entity_id:
        mock.states.set(
            entity_id,
            widget_config.get("options", {}).get("text", "Sample"),
            {"friendly_name": widget_config.get("label", "Text")},
        )

    # Handle list-based widgets
    options = widget_config.get("options", {})

    if widget_type == "multi_progress":
        items = options.get("items", [])
        for item in items:
            item_entity = item.get("entity_id")
            if item_entity:
                mock.states.set(
                    item_entity,
                    "50",
                    {"unit_of_measurement": "", "friendly_name": item.get("label", "Item")},
                )

    elif widget_type == "status_list":
        entities = options.get("entities", [])
        for entry in entities:
            ent_id = entry[0] if isinstance(entry, list | tuple) else entry
            if ent_id:
                friendly = (
                    entry[1] if isinstance(entry, list | tuple) and len(entry) > 1 else ent_id
                )
                mock.states.set(ent_id, "on", {"friendly_name": friendly})


def _build_widget_state_for_preview(
    widget_config: dict[str, Any],
    mock: MockHass,
) -> WidgetState:
    """Build WidgetState for a widget in preview mode.

    Args:
        widget_config: Widget configuration dictionary
        mock: MockHass instance with mock states

    Returns:
        WidgetState for the widget
    """
    widget_type = widget_config.get("type", "")
    entity_id = widget_config.get("entity_id")
    options = widget_config.get("options", {})

    # Build primary entity state
    entity: EntityState | None = None
    if entity_id:
        mock_state = mock.states.get(entity_id)
        if mock_state:
            entity = EntityState(
                entity_id=mock_state.entity_id,
                state=mock_state.state,
                attributes=mock_state.attributes,
            )

    # Build additional entities for multi-entity widgets
    entities: dict[str, EntityState] = {}

    if widget_type == "multi_progress":
        items = options.get("items", [])
        for item in items:
            item_entity_id = item.get("entity_id")
            if item_entity_id:
                mock_state = mock.states.get(item_entity_id)
                if mock_state:
                    entities[item_entity_id] = EntityState(
                        entity_id=mock_state.entity_id,
                        state=mock_state.state,
                        attributes=mock_state.attributes,
                    )

    elif widget_type == "status_list":
        entity_entries = options.get("entities", [])
        for entry in entity_entries:
            ent_id = entry[0] if isinstance(entry, list | tuple) else entry
            if ent_id:
                mock_state = mock.states.get(ent_id)
                if mock_state:
                    entities[ent_id] = EntityState(
                        entity_id=mock_state.entity_id,
                        state=mock_state.state,
                        attributes=mock_state.attributes,
                    )

    # Build mock chart history for chart widgets
    history: list[float] = []
    if widget_type == "chart":
        history = [20, 22, 21, 23, 25, 24, 22, 23, 21, 20, 22, 23]

    # Build mock forecast for weather widgets
    # Use realistic ISO datetime format like Home Assistant returns
    forecast: list[dict[str, Any]] = []
    if widget_type == "weather":
        forecast = [
            {
                "datetime": "2025-12-29T00:00:00+00:00",
                "condition": "sunny",
                "temperature": 26,
                "templow": 14,
            },
            {
                "datetime": "2025-12-30T00:00:00+00:00",
                "condition": "cloudy",
                "temperature": 22,
                "templow": 12,
            },
            {
                "datetime": "2025-12-31T00:00:00+00:00",
                "condition": "rainy",
                "temperature": 18,
                "templow": 10,
            },
            {
                "datetime": "2026-01-01T00:00:00+00:00",
                "condition": "partlycloudy",
                "temperature": 20,
                "templow": 11,
            },
            {
                "datetime": "2026-01-02T00:00:00+00:00",
                "condition": "sunny",
                "temperature": 24,
                "templow": 13,
            },
        ]

    return WidgetState(
        entity=entity,
        entities=entities,
        history=history,
        forecast=forecast,
        image=None,
        now=datetime.now(tz=UTC),
    )


def render_preview(
    layout_type: str,
    widgets_config: list[dict[str, Any]],
    hass: HomeAssistant | None = None,
    background_image: str | None = None,
    background_mode: str = "stretch",
    background_entity: str | None = None,
    widget_contrast: float = 0.5,
    text_opacity: float = 1.0,
) -> bytes:
    """Render a preview image for the given configuration.

    Args:
        layout_type: Layout type string (grid_2x2, grid_2x3, hero, split)
        widgets_config: List of widget configuration dictionaries
        hass: Optional Home Assistant instance (uses mock if None)
        background_image: Optional static path to a local background image
        background_mode: How to fit the image: stretch, contain, cover
        background_entity: Optional HA entity whose state resolves to a path
        widget_contrast: Opacity of the contrast backdrop behind widgets (0..1).
        text_opacity: Opacity multiplier for text/icon colors (0..1).

    Returns:
        PNG image bytes
    """
    # Resolve background entity if hass is available
    if background_entity and hass is not None:
        state = hass.states.get(background_entity)
        if state and isinstance(state.state, str):
            resolved = state.state.strip()
            if resolved and resolved.lower() not in ("unavailable", "unknown", "none", ""):
                if not resolved.startswith("/"):
                    resolved = f"/config/{resolved}"
                if os.path.isfile(resolved):
                    background_image = resolved

    # Build mock states for preview
    mock = MockHass()
    for widget_config in widgets_config:
        _set_mock_state_for_widget(mock, widget_config)

    # Create renderer and layout
    renderer = Renderer()
    layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)

    if isinstance(background_image, str):
        background_image = background_image.strip() or None
    if background_mode not in ("stretch", "contain", "cover"):
        background_mode = "stretch"

    layout_kwargs = dict(
        background_image=background_image,
        background_mode=background_mode,
        widget_contrast=widget_contrast,
        text_scale=1.0,
        text_opacity=text_opacity,
    )
    if layout_type == LAYOUT_CUSTOM:
        layout_kwargs["widgets"] = widgets_config

    layout = layout_class(**layout_kwargs)

    # Build widget_states dict for all slots
    widget_states: dict[int, WidgetState] = {}

    # Create and assign widgets
    for widget_index, widget_config in enumerate(widgets_config):
        widget_type = str(widget_config.get("type", "text"))
        if layout_type == LAYOUT_CUSTOM:
            slot = widget_index
        else:
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

        # Parse color
        parsed_color: tuple[int, int, int] | None = None
        if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
            parsed_color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))

        widget_text_scale = 1.0
        try:
            widget_text_scale = float(widget_config.get("text_scale", 1.0))
        except (TypeError, ValueError):
            widget_text_scale = 1.0
        widget_text_scale = max(0.5, min(3.0, widget_text_scale))

        config = WidgetConfig(
            widget_type=widget_type,
            slot=slot,
            entity_id=str(entity_id) if entity_id is not None else None,
            label=str(label) if label is not None else None,
            color=parsed_color,
            text_scale=widget_text_scale,
            options=cast("dict[str, Any]", widget_options),
        )

        widget = widget_class(config)
        layout.set_widget(slot, widget)

        # Build widget state for this slot
        widget_states[slot] = _build_widget_state_for_preview(widget_config, mock)

    # Render to image
    img, draw = renderer.create_canvas()
    layout.render(renderer, draw, widget_states)

    return renderer.to_png(img)


def render_screen_preview(
    screen_config: dict[str, Any], hass: HomeAssistant | None = None
) -> bytes:
    """Render a preview for a complete screen configuration.

    Args:
        screen_config: Screen configuration with layout and widgets
        hass: Optional Home Assistant instance

    Returns:
        PNG image bytes
    """
    layout_type = screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
    widgets_config = screen_config.get(CONF_WIDGETS, [])
    background_image = screen_config.get(CONF_BACKGROUND_IMAGE)
    background_mode = screen_config.get(CONF_BACKGROUND_MODE, "stretch")
    background_entity = screen_config.get(CONF_BACKGROUND_ENTITY)

    widget_contrast = screen_config.get(CONF_WIDGET_CONTRAST, 0.5)
    try:
        widget_contrast = float(widget_contrast)
    except (TypeError, ValueError):
        widget_contrast = 0.5
    widget_contrast = max(0.0, min(1.0, widget_contrast))

    text_opacity = screen_config.get(CONF_TEXT_OPACITY, 1.0)
    try:
        text_opacity = float(text_opacity)
    except (TypeError, ValueError):
        text_opacity = 1.0
    text_opacity = max(0.0, min(1.0, text_opacity))

    return render_preview(
        layout_type,
        widgets_config,
        hass,
        background_image=background_image,
        background_mode=background_mode,
        background_entity=background_entity,
        widget_contrast=widget_contrast,
        text_opacity=text_opacity,
    )
