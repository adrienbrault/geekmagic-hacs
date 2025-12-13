"""Clock widget for GeekMagic displays."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..const import COLOR_WHITE, COLOR_GRAY, COLOR_CYAN
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from PIL import ImageDraw
    from homeassistant.core import HomeAssistant

    from ..renderer import Renderer


class ClockWidget(Widget):
    """Widget that displays current time and date."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the clock widget."""
        super().__init__(config)
        self.show_date = config.options.get("show_date", True)
        self.show_seconds = config.options.get("show_seconds", False)
        self.time_format = config.options.get("time_format", "24h")

    def get_entities(self) -> list[str]:
        """Clock widget doesn't depend on entities."""
        return []

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the clock widget.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            hass: Home Assistant instance (used for timezone)
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1
        center_x = x1 + width // 2
        center_y = y1 + height // 2

        now = datetime.now()

        # Format time
        if self.show_seconds:
            if self.time_format == "12h":
                time_str = now.strftime("%I:%M:%S")
                ampm = now.strftime("%p")
            else:
                time_str = now.strftime("%H:%M:%S")
                ampm = None
        else:
            if self.time_format == "12h":
                time_str = now.strftime("%I:%M")
                ampm = now.strftime("%p")
            else:
                time_str = now.strftime("%H:%M")
                ampm = None

        # Calculate positions
        time_y = center_y - 10 if self.show_date else center_y

        # Draw time
        color = self.config.color or COLOR_WHITE
        renderer.draw_text(
            draw,
            time_str,
            (center_x, time_y),
            font=renderer.font_xlarge,
            color=color,
            anchor="mm",
        )

        # Draw AM/PM if 12-hour format
        if ampm:
            ampm_x = center_x + renderer.get_text_size(time_str, renderer.font_xlarge)[0] // 2 + 5
            renderer.draw_text(
                draw,
                ampm,
                (ampm_x, time_y - 10),
                font=renderer.font_small,
                color=COLOR_GRAY,
                anchor="lm",
            )

        # Draw date
        if self.show_date:
            date_str = now.strftime("%a, %b %d")
            date_y = center_y + 25
            renderer.draw_text(
                draw,
                date_str,
                (center_x, date_y),
                font=renderer.font_regular,
                color=COLOR_GRAY,
                anchor="mm",
            )

        # Draw label if provided
        if self.config.label:
            label_y = y1 + 15
            renderer.draw_text(
                draw,
                self.config.label.upper(),
                (center_x, label_y),
                font=renderer.font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )
