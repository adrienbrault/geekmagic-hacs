"""Chart widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from ..const import COLOR_CYAN, COLOR_GRAY
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


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
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the chart widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get scaled fonts
        font_label = ctx.get_font("small")
        font_value = ctx.get_font("regular")

        # Calculate relative padding
        padding = int(ctx.width * 0.08)

        # Get current value from entity
        state = self.get_entity_state(hass)
        current_value = None
        unit = ""
        name = self.config.label or "Chart"

        if state is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(state.state)
            unit = state.attributes.get("unit_of_measurement", "")
            name = self.config.label or state.attributes.get("friendly_name", "Chart")

        # Calculate chart area relative to container
        header_height = int(ctx.height * 0.15) if self.config.label else int(ctx.height * 0.08)
        footer_height = int(ctx.height * 0.12) if self.show_range else int(ctx.height * 0.04)
        chart_top = header_height
        chart_bottom = ctx.height - footer_height
        chart_rect = (padding, chart_top, ctx.width - padding, chart_bottom)

        # Draw label
        if self.config.label:
            center_x = ctx.width // 2
            ctx.draw_text(
                name.upper(),
                (center_x, int(ctx.height * 0.08)),
                font=font_label,
                color=COLOR_GRAY,
                anchor="mm",
            )

        # Draw current value
        if self.show_value and current_value is not None:
            value_str = f"{current_value:.1f}{unit}"
            ctx.draw_text(
                value_str,
                (ctx.width - padding, int(ctx.height * 0.08)),
                font=font_value,
                color=self.config.color or COLOR_CYAN,
                anchor="rm",
            )

        # Draw sparkline
        if self._history_data and len(self._history_data) >= 2:
            color = self.config.color or COLOR_CYAN
            ctx.draw_sparkline(chart_rect, self._history_data, color=color, fill=True)

            # Draw min/max range
            if self.show_range:
                min_val = min(self._history_data)
                max_val = max(self._history_data)
                range_y = chart_bottom + int(ctx.height * 0.08)

                ctx.draw_text(
                    f"{min_val:.1f}",
                    (padding, range_y),
                    font=font_label,
                    color=COLOR_GRAY,
                    anchor="lm",
                )
                ctx.draw_text(
                    f"{max_val:.1f}",
                    (ctx.width - padding, range_y),
                    font=font_label,
                    color=COLOR_GRAY,
                    anchor="rm",
                )
        else:
            # No data - show placeholder
            center_x = ctx.width // 2
            center_y = (chart_top + chart_bottom) // 2
            ctx.draw_text(
                "No data",
                (center_x, center_y),
                font=font_label,
                color=COLOR_GRAY,
                anchor="mm",
            )
