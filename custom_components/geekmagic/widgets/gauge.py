"""Gauge widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from ..const import COLOR_CYAN, COLOR_DARK_GRAY, COLOR_GRAY, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


class GaugeWidget(Widget):
    """Widget that displays a value as a gauge (bar or ring)."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the gauge widget."""
        super().__init__(config)
        self.style = config.options.get("style", "bar")  # bar, ring, arc
        self.min_value = config.options.get("min", 0)
        self.max_value = config.options.get("max", 100)
        self.icon = config.options.get("icon")
        self.show_value = config.options.get("show_value", True)
        self.unit = config.options.get("unit", "")
        # Attribute to read value from (e.g., "temperature" for climate entities)
        self.attribute = config.options.get("attribute")

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the gauge widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get entity state
        state = self.get_entity_state(hass)
        value = 0.0
        display_value = "--"

        if state is not None:
            # Read from attribute if specified, otherwise from state
            raw_value = state.attributes.get(self.attribute) if self.attribute else state.state
            with contextlib.suppress(ValueError, TypeError):
                value = float(raw_value)
                display_value = f"{value:.0f}"
            if not self.unit:
                self.unit = state.attributes.get("unit_of_measurement", "")

        # Calculate percentage
        value_range = self.max_value - self.min_value
        if value_range > 0:
            percent = max(0, min(100, ((value - self.min_value) / value_range) * 100))
        else:
            percent = 0

        # Get label
        name = self.config.label
        if not name and state:
            name = state.attributes.get("friendly_name", "")
        name = name or ""

        color = self.config.color or COLOR_CYAN

        if self.style == "ring":
            self._render_ring(ctx, percent, display_value, name, color)
        elif self.style == "arc":
            self._render_arc(ctx, percent, display_value, name, color)
        else:
            self._render_bar(ctx, percent, display_value, name, color)

    def _render_bar(
        self,
        ctx: RenderContext,
        percent: float,
        value: str,
        name: str,
        color: tuple[int, int, int],
    ) -> None:
        """Render as horizontal progress bar."""
        # Get scaled fonts
        font_label = ctx.get_font("tiny")
        font_value = ctx.get_font("medium", bold=True)

        # Calculate layout relative to container
        icon_size = max(10, int(ctx.height * 0.23))
        label_y = int(ctx.height * 0.33)
        bar_height = max(6, int(ctx.height * 0.17))
        bar_y = int(ctx.height * 0.67) - bar_height // 2
        rel_padding = int(ctx.height * 0.13)

        # Draw icon if present
        text_start_x = rel_padding
        if self.icon is not None:
            ctx.draw_icon(
                self.icon,
                (rel_padding, label_y - icon_size // 2),
                size=icon_size,
                color=color,
            )
            text_start_x = rel_padding + icon_size + 4

        # Draw label
        if name:
            ctx.draw_text(
                name.upper(),
                (text_start_x, label_y),
                font=font_label,
                color=COLOR_GRAY,
                anchor="lm",
            )

        # Draw value
        if self.show_value:
            value_text = f"{value}{self.unit}" if self.unit else value
            ctx.draw_text(
                value_text,
                (ctx.width - rel_padding, label_y),
                font=font_value,
                color=COLOR_WHITE,
                anchor="rm",
            )

        # Draw bar
        bar_rect = (rel_padding, bar_y, ctx.width - rel_padding, bar_y + bar_height)
        ctx.draw_bar(bar_rect, percent, color, COLOR_DARK_GRAY)

    def _render_ring(
        self,
        ctx: RenderContext,
        percent: float,
        value: str,
        name: str,
        color: tuple[int, int, int],
    ) -> None:
        """Render as ring gauge."""
        center_x = ctx.width // 2
        center_y = ctx.height // 2

        # Get scaled fonts
        font_value = ctx.get_font("large")
        font_label = ctx.get_font("tiny")

        # Calculate ring size relative to container
        margin = int(min(ctx.width, ctx.height) * 0.12)
        radius = min(ctx.width, ctx.height) // 2 - margin
        ring_width = max(4, radius // 5)

        # Draw ring
        ctx.draw_ring_gauge(
            center=(center_x, center_y - int(ctx.height * 0.04)),
            radius=radius,
            percent=percent,
            color=color,
            background=COLOR_DARK_GRAY,
            width=ring_width,
        )

        # Draw value in center
        if self.show_value:
            value_text = f"{value}{self.unit}" if self.unit else value
            ctx.draw_text(
                value_text,
                (center_x, center_y - int(ctx.height * 0.04)),
                font=font_value,
                color=COLOR_WHITE,
                anchor="mm",
            )

        # Draw label below
        if name:
            ctx.draw_text(
                name.upper(),
                (center_x, ctx.height - int(ctx.height * 0.10)),
                font=font_label,
                color=COLOR_GRAY,
                anchor="mm",
            )

    def _render_arc(
        self,
        ctx: RenderContext,
        percent: float,
        value: str,
        name: str,
        color: tuple[int, int, int],
    ) -> None:
        """Render as arc gauge (semicircle)."""
        center_x = ctx.width // 2
        center_y = int(ctx.height * 0.55)

        # Get scaled fonts
        font_value = ctx.get_font("large")
        font_label = ctx.get_font("small")

        # Calculate arc size relative to container
        margin = int(min(ctx.width, ctx.height) * 0.08)
        radius = min(ctx.width, ctx.height) // 2 - margin

        # Draw arc using renderer's draw_arc method
        ctx.draw_arc(
            rect=(center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            percent=percent,
            color=color,
            background=COLOR_DARK_GRAY,
        )

        # Draw value
        if self.show_value:
            value_text = f"{value}{self.unit}" if self.unit else value
            ctx.draw_text(
                value_text,
                (center_x, center_y - int(ctx.height * 0.04)),
                font=font_value,
                color=COLOR_WHITE,
                anchor="mm",
            )

        # Draw label
        if name:
            ctx.draw_text(
                name.upper(),
                (center_x, int(ctx.height * 0.12)),
                font=font_label,
                color=COLOR_GRAY,
                anchor="mm",
            )
