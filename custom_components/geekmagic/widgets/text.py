"""Text widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_GRAY, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


class TextWidget(Widget):
    """Widget that displays static or dynamic text."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the text widget."""
        super().__init__(config)
        self.text = config.options.get("text", "")
        self.size = config.options.get("size", "regular")  # small, regular, large, xlarge
        self.align = config.options.get("align", "center")  # left, center, right

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the text widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get text to display
        text = self._get_text(hass)

        # Get scaled font based on container height
        font = ctx.get_font(self.size)
        font_label = ctx.get_font("small")

        # Calculate position with relative padding
        padding = int(ctx.width * 0.04)
        if self.align == "left":
            x = padding
            anchor = "lm"
        elif self.align == "right":
            x = ctx.width - padding
            anchor = "rm"
        else:  # center
            x = ctx.width // 2
            anchor = "mm"

        y = ctx.height // 2

        # Draw text
        color = self.config.color or COLOR_WHITE
        ctx.draw_text(text, (x, y), font=font, color=color, anchor=anchor)

        # Draw label if provided
        if self.config.label:
            label_y = int(ctx.height * 0.15)
            ctx.draw_text(
                self.config.label.upper(),
                (ctx.width // 2, label_y),
                font=font_label,
                color=COLOR_GRAY,
                anchor="mm",
            )

    def _get_text(self, hass: HomeAssistant | None) -> str:
        """Get the text to display.

        If entity_id is set, returns the entity state.
        Otherwise returns the configured text.
        """
        if self.config.entity_id and hass:
            state = self.get_entity_state(hass)
            if state:
                return state.state

        return self.text
