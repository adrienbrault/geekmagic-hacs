"""Preview rendering for GeekMagic configuration flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from .const import (
    CONF_LAYOUT,
    CONF_WIDGETS,
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
from .widgets.attribute_list import AttributeListWidget
from .widgets.base import WidgetConfig
from .widgets.chart import ChartWidget
from .widgets.clock import ClockWidget
from .widgets.entity import EntityWidget
from .widgets.gauge import GaugeWidget
from .widgets.media import MediaWidget
from .widgets.progress import MultiProgressWidget, ProgressWidget
from .widgets.state import EntityState, WidgetState
from .widgets.status import StatusListWidget, StatusWidget
from .widgets.text import TextWidget
from .widgets.weather import WeatherWidget

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
}

WIDGET_CLASSES = {
    "attribute_list": AttributeListWidget,
    "clock": ClockWidget,
    "entity": EntityWidget,
    "media": MediaWidget,
    "chart": ChartWidget,
    "text": TextWidget,
    "gauge": GaugeWidget,
    "progress": ProgressWidget,
    "multi_progress": MultiProgressWidget,
    "status": StatusWidget,
    "status_list": StatusListWidget,
    "weather": WeatherWidget,
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
) -> bytes:
    """Render a preview image for the given configuration.

    Args:
        layout_type: Layout type string (grid_2x2, grid_2x3, hero, split)
        widgets_config: List of widget configuration dictionaries
        hass: Optional Home Assistant instance (uses mock if None)

    Returns:
        PNG image bytes
    """
    # Build mock states for preview
    mock = MockHass()
    for widget_config in widgets_config:
        _set_mock_state_for_widget(mock, widget_config)

    # Create renderer and layout
    renderer = Renderer()
    layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)
    layout = layout_class()

    # Build widget_states dict for all slots
    widget_states: dict[int, WidgetState] = {}

    # Create and assign widgets
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

        # Parse color
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

    return render_preview(layout_type, widgets_config, hass)
