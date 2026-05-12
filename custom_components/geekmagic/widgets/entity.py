"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from ..const import (
    PLACEHOLDER_NAME,
    PLACEHOLDER_VALUE,
)
from .base import Widget, WidgetConfig
from .components import Component, Panel
from .data_card import DataCard
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

    WIDGET_TYPE: ClassVar[str] = "entity"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Entity",
        "needs_entity": True,
        "entity_domains": None,  # All domains
        "options": [
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_unit", "type": "boolean", "label": "Show Unit", "default": True},
            {"key": "show_icon", "type": "boolean", "label": "Show Icon", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon Override"},
            {"key": "show_panel", "type": "boolean", "label": "Panel Background", "default": False},
            {
                "key": "precision",
                "type": "number",
                "label": "Decimal Places",
                "min": 0,
                "max": 5,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the entity widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_unit = config.options.get("show_unit", True)
        self.show_icon = config.options.get("show_icon", True)
        # Treat empty string (cleared icon picker) the same as missing.
        self.icon = config.options.get("icon") or None  # Explicit icon override
        self.show_panel = config.options.get("show_panel", False)
        self.precision = config.options.get("precision")  # Decimal places for numeric values
        # Attribute to read value from (instead of state)
        self.attribute = config.options.get("attribute")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the entity widget."""
        entity = state.entity

        if entity is None:
            value = PLACEHOLDER_VALUE
            unit = ""
            name = self.label_for(None, fallback=self.config.entity_id or PLACEHOLDER_NAME)
        else:
            # Get value from attribute or state
            if self.attribute:
                raw_value = entity.get(self.attribute)
                value = str(raw_value) if raw_value is not None else PLACEHOLDER_VALUE
            else:
                value = entity.state
                if entity.entity_id.startswith("binary_sensor."):
                    value = translate_binary_state(value, entity.device_class)
                elif isinstance(value, str) and value.isalpha() and len(value) <= 16:
                    # Title-case short alpha flag states ('on'→'On', 'home'→'Home')
                    # to match binary-sensor 'Open'/'Closed' style.
                    value = value.title()
            # Apply precision formatting if specified and value is numeric
            if self.precision is not None:
                try:
                    numeric_value = float(value)
                    value = f"{numeric_value:.{self.precision}f}"
                except (ValueError, TypeError):
                    pass  # Keep original value if not numeric
            unit = entity.unit if self.show_unit else ""
            name = self.label_for(entity)

        # Build display value with unit
        value_text = f"{value}{unit}" if unit else value

        # Determine icon to use
        icon = self.icon
        if not icon and self.show_icon:
            icon = _get_entity_icon(entity)

        card = DataCard(
            caption=name if self.show_name else None,
            icon=icon,
            icon_color=self.config.color or ctx.theme.get_accent_color(self.config.slot),
            # Promote the icon to its own band (was IconValueDisplay's
            # default look). The entity icon is the cell's primary
            # visual identifier — chip size loses the read.
            icon_role="feature",
            hero=value_text,
        )
        return Panel(child=card) if self.show_panel else card
