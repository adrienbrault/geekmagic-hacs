"""Text widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_WHITE, COLOR_GRAY
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from PIL import ImageDraw
    from homeassistant.core import HomeAssistant

    from ..renderer import Renderer


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
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the text widget.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            hass: Home Assistant instance
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1

        # Get text to display
        text = self._get_text(hass)

        # Select font
        font = self._get_font(renderer)

        # Calculate position
        if self.align == "left":
            x = x1 + 5
            anchor = "lm"
        elif self.align == "right":
            x = x2 - 5
            anchor = "rm"
        else:  # center
            x = x1 + width // 2
            anchor = "mm"

        y = y1 + height // 2

        # Draw text
        color = self.config.color or COLOR_WHITE
        renderer.draw_text(draw, text, (x, y), font=font, color=color, anchor=anchor)

        # Draw label if provided
        if self.config.label:
            label_y = y1 + 12
            renderer.draw_text(
                draw,
                self.config.label.upper(),
                (x1 + width // 2, label_y),
                font=renderer.font_small,
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

    def _get_font(self, renderer: Renderer):
        """Get the font based on size setting."""
        fonts = {
            "small": renderer.font_small,
            "regular": renderer.font_regular,
            "large": renderer.font_large,
            "xlarge": renderer.font_xlarge,
        }
        return fonts.get(self.size, renderer.font_regular)
