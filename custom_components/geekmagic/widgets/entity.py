"""Entity widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_CYAN, COLOR_GRAY, COLOR_PANEL, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


class EntityWidget(Widget):
    """Widget that displays a Home Assistant entity state."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the entity widget."""
        super().__init__(config)
        self.show_name = config.options.get("show_name", True)
        self.show_unit = config.options.get("show_unit", True)
        self.icon = config.options.get("icon")
        self.show_panel = config.options.get("show_panel", False)

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the entity widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Draw panel background if enabled
        if self.show_panel:
            ctx.draw_panel((0, 0, ctx.width, ctx.height), COLOR_PANEL, radius=4)

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

        # Truncate value if too long
        max_value_len = (ctx.width - 20) // 10
        if len(value) > max_value_len:
            value = value[: max_value_len - 2] + ".."

        # Truncate name if too long
        max_name_len = (ctx.width - 10) // 7
        if len(name) > max_name_len:
            name = name[: max_name_len - 2] + ".."

        color = self.config.color or COLOR_CYAN

        # Layout depends on whether we have an icon
        if self.icon:
            self._render_with_icon(ctx, value, unit, name, color)
        else:
            self._render_centered(ctx, value, unit, name, color)

    def _render_centered(
        self,
        ctx: RenderContext,
        value: str,
        unit: str,
        name: str,
        color: tuple[int, int, int],
    ) -> None:
        """Render with value centered and name below."""
        center_x = ctx.width // 2
        center_y = ctx.height // 2

        # Get scaled fonts based on container height
        font_value = ctx.get_font("large")
        font_name = ctx.get_font("tiny")

        # Calculate positions relative to container
        offset_y = int(ctx.height * 0.07) if self.show_name else 0
        value_y = center_y - offset_y
        name_y = ctx.height - int(ctx.height * 0.12)

        # Draw value
        value_text = f"{value}{unit}" if unit else value
        ctx.draw_text(
            value_text,
            (center_x, value_y),
            font=font_value,
            color=color,
            anchor="mm",
        )

        # Draw name
        if self.show_name:
            ctx.draw_text(
                name.upper(),
                (center_x, name_y),
                font=font_name,
                color=COLOR_GRAY,
                anchor="mm",
            )

    def _render_with_icon(
        self,
        ctx: RenderContext,
        value: str,
        unit: str,
        name: str,
        color: tuple[int, int, int],
    ) -> None:
        """Render with icon on top, value below, name at bottom."""
        center_x = ctx.width // 2

        # Get scaled fonts based on container height
        font_value = ctx.get_font("medium", bold=True)
        font_name = ctx.get_font("tiny")

        # Layout: icon at top, value in middle, name at bottom
        # Scale icon size relative to container
        icon_size = max(12, min(24, int(ctx.height * 0.25)))
        padding = int(ctx.height * 0.08)

        # Draw icon (self.icon is guaranteed to be set when this method is called)
        assert self.icon is not None
        ctx.draw_icon(
            self.icon,
            (center_x - icon_size // 2, padding),
            size=icon_size,
            color=color,
        )

        # Draw value
        value_text = f"{value}{unit}" if unit else value
        value_y = int(ctx.height * 0.55)
        ctx.draw_text(
            value_text,
            (center_x, value_y),
            font=font_value,
            color=COLOR_WHITE,
            anchor="mm",
        )

        # Draw name
        if self.show_name:
            ctx.draw_text(
                name.upper(),
                (center_x, ctx.height - int(ctx.height * 0.12)),
                font=font_name,
                color=COLOR_GRAY,
                anchor="mm",
            )
