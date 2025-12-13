"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_WHITE, COLOR_GRAY, COLOR_CYAN
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from PIL import ImageDraw
    from homeassistant.core import HomeAssistant

    from ..renderer import Renderer


class EntityWidget(Widget):
    """Widget that displays a Home Assistant entity state."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the entity widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_unit = config.options.get("show_unit", True)
        self.icon = config.options.get("icon")

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the entity widget.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            hass: Home Assistant instance
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1
        center_x = x1 + width // 2
        center_y = y1 + height // 2

        # Get entity state
        state = self.get_entity_state(hass)

        if state is None:
            # No entity or no hass - show placeholder
            value = "--"
            unit = ""
            name = self.config.label or self.config.entity_id or "Unknown"
        else:
            value = state.state
            unit = state.attributes.get("unit_of_measurement", "") if self.show_unit else ""
            name = self.config.label or state.attributes.get("friendly_name", state.entity_id)

        # Truncate name if too long
        max_name_len = width // 8  # Approximate characters that fit
        if len(name) > max_name_len:
            name = name[:max_name_len - 2] + ".."

        # Calculate positions
        value_y = center_y if not self.show_name else center_y - 5
        name_y = center_y + 25

        # Draw value
        color = self.config.color or COLOR_CYAN
        value_text = f"{value}{unit}" if unit else value
        renderer.draw_text(
            draw,
            value_text,
            (center_x, value_y),
            font=renderer.font_large,
            color=color,
            anchor="mm",
        )

        # Draw name
        if self.show_name:
            renderer.draw_text(
                draw,
                name.upper(),
                (center_x, name_y),
                font=renderer.font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )
