"""Chart widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_WHITE, COLOR_GRAY, COLOR_CYAN
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from PIL import ImageDraw
    from homeassistant.core import HomeAssistant

    from ..renderer import Renderer


class ChartWidget(Widget):
    """Widget that displays a sparkline chart from entity history."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the chart widget."""
        super().__init__(config)
        self.hours = config.options.get("hours", 24)
        self.show_value = config.options.get("show_value", True)
        self.show_range = config.options.get("show_range", True)

        # History data cache (populated externally)
        self._history_data: list[float] = []

    def set_history(self, data: list[float]) -> None:
        """Set the history data for the chart.

        Args:
            data: List of numeric values
        """
        self._history_data = data

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the chart widget.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            hass: Home Assistant instance
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        height = y2 - y1
        padding = 10

        # Get current value from entity
        state = self.get_entity_state(hass)
        current_value = None
        unit = ""
        name = self.config.label or "Chart"

        if state is not None:
            try:
                current_value = float(state.state)
            except (ValueError, TypeError):
                pass
            unit = state.attributes.get("unit_of_measurement", "")
            name = self.config.label or state.attributes.get("friendly_name", "Chart")

        # Calculate chart area
        chart_top = y1 + (35 if self.config.label else 20)
        chart_bottom = y2 - (25 if self.show_range else 10)
        chart_rect = (x1 + padding, chart_top, x2 - padding, chart_bottom)

        # Draw label
        if self.config.label:
            center_x = x1 + width // 2
            renderer.draw_text(
                draw,
                name.upper(),
                (center_x, y1 + 12),
                font=renderer.font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )

        # Draw current value
        if self.show_value and current_value is not None:
            value_str = f"{current_value:.1f}{unit}"
            renderer.draw_text(
                draw,
                value_str,
                (x2 - padding, y1 + 12),
                font=renderer.font_regular,
                color=self.config.color or COLOR_CYAN,
                anchor="rm",
            )

        # Draw sparkline
        if self._history_data and len(self._history_data) >= 2:
            color = self.config.color or COLOR_CYAN
            renderer.draw_sparkline(draw, chart_rect, self._history_data, color=color, fill=True)

            # Draw min/max range
            if self.show_range:
                min_val = min(self._history_data)
                max_val = max(self._history_data)
                range_y = chart_bottom + 12

                renderer.draw_text(
                    draw,
                    f"{min_val:.1f}",
                    (x1 + padding, range_y),
                    font=renderer.font_small,
                    color=COLOR_GRAY,
                    anchor="lm",
                )
                renderer.draw_text(
                    draw,
                    f"{max_val:.1f}",
                    (x2 - padding, range_y),
                    font=renderer.font_small,
                    color=COLOR_GRAY,
                    anchor="rm",
                )
        else:
            # No data - show placeholder
            center_x = x1 + width // 2
            center_y = (chart_top + chart_bottom) // 2
            renderer.draw_text(
                draw,
                "No data",
                (center_x, center_y),
                font=renderer.font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )
