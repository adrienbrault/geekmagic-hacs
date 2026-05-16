"""Preview rendering for GeekMagic configuration flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import CONF_LAYOUT, CONF_WIDGETS, LAYOUT_GRID_2X2
from .renderer import Renderer
from .screen_builder import build_layout
from .widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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

    # Build the layout (with theme + widgets wired) using the same
    # construction path as production rendering.
    layout = build_layout({CONF_LAYOUT: layout_type, CONF_WIDGETS: widgets_config})

    # Mock widget states keyed by slot — only for widgets that were actually
    # placed into the layout (build_layout silently drops out-of-range and
    # unknown-type widgets).
    placed_slots = {slot.index for slot in layout.slots if slot.widget is not None}
    widget_states: dict[int, WidgetState] = {}
    for widget_config in widgets_config:
        slot = int(widget_config.get("slot", 0))
        if slot in placed_slots:
            widget_states[slot] = _build_widget_state_for_preview(widget_config, mock)

    renderer = Renderer()
    img, draw = renderer.create_canvas(background=layout.theme.background)
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
