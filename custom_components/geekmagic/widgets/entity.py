"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import (
    COLOR_CYAN,
    PLACEHOLDER_NAME,
    PLACEHOLDER_VALUE,
)
from .base import Widget, WidgetConfig
from .component_helpers import CenteredValue, IconValue
from .components import THEME_TEXT_PRIMARY, THEME_TEXT_SECONDARY, Component, Panel
from .helpers import get_binary_sensor_icon, translate_binary_state

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def _get_entity_icon(entity_state) -> str | None:
    """Get icon from entity state, handling MDI format and state-specific icons."""
    if entity_state is None:
        return None

    # For binary sensors, get state-specific icon
    if entity_state.entity_id.startswith("binary_sensor."):
        icon = get_binary_sensor_icon(entity_state.state, entity_state.device_class)
        if icon:
            return icon.removeprefix("mdi:")

    # Check explicit icon attribute
    icon = entity_state.icon
    if icon and icon.startswith("mdi:"):
        return icon.removeprefix("mdi:")
    return None


class EntityWidget(Widget):
    """Widget that displays a Home Assistant entity state."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the entity widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_unit = config.options.get("show_unit", True)
        self.show_icon = config.options.get("show_icon", True)
        self.icon = config.options.get("icon")  # Explicit icon override
        self.show_panel = config.options.get("show_panel", False)
        self.precision = config.options.get("precision")  # Decimal places for numeric values

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the entity widget."""
        entity = state.entity

        if entity is None:
            value = PLACEHOLDER_VALUE
            unit = ""
            name = self.config.label or self.config.entity_id or PLACEHOLDER_NAME
        else:
            value = entity.state
            # Translate binary sensor states (e.g., "on" -> "Open" for door sensors)
            if entity.entity_id.startswith("binary_sensor."):
                value = translate_binary_state(value, entity.device_class)
            # Apply precision formatting if specified and value is numeric
            if self.precision is not None:
                try:
                    numeric_value = float(value)
                    value = f"{numeric_value:.{self.precision}f}"
                except (ValueError, TypeError):
                    pass  # Keep original value if not numeric
            unit = entity.unit if self.show_unit else ""
            name = self.config.label or entity.friendly_name or entity.entity_id

        # Build display value with unit
        value_text = f"{value}{unit}" if unit else value
        label = name if self.show_name else None

        # Determine icon to use
        icon = self.icon
        if not icon and self.show_icon:
            icon = _get_entity_icon(entity)

        color = self.config.color or COLOR_CYAN

        # Build component based on whether we have an icon
        if icon:
            content = IconValue(
                icon=icon,
                value=value_text,
                label=label or "",
                color=color,
                value_color=THEME_TEXT_PRIMARY,
                label_color=THEME_TEXT_SECONDARY,
            )
        else:
            content = CenteredValue(
                value=value_text,
                label=label,
                value_color=THEME_TEXT_PRIMARY,
                label_color=THEME_TEXT_SECONDARY,
            )

        # Wrap in panel if enabled
        if self.show_panel:
            return Panel(child=content)

        return content
