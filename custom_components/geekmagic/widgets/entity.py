"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import (
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_WHITE,
    PLACEHOLDER_NAME,
    PLACEHOLDER_VALUE,
)
from .base import Widget, WidgetConfig
from .component_helpers import CenteredValue, IconValue
from .components import Component, Panel

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def _get_entity_icon(entity_state) -> str | None:
    """Get icon from entity state, handling MDI format."""
    if entity_state is None:
        return None
    icon = entity_state.icon
    if icon and icon.startswith("mdi:"):
        return icon[4:]  # Strip "mdi:" prefix
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
                value_color=COLOR_WHITE,
                label_color=COLOR_GRAY,
            )
        else:
            content = CenteredValue(
                value=value_text,
                label=label,
                value_color=color,
                label_color=COLOR_GRAY,
            )

        # Wrap in panel if enabled
        if self.show_panel:
            return Panel(child=content)

        return content
