"""Progress widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from ..const import COLOR_CYAN, COLOR_DARK_GRAY, COLOR_GRAY, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


class ProgressWidget(Widget):
    """Widget that displays progress with label (like fitness tracking)."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the progress widget."""
        super().__init__(config)
        self.target = config.options.get("target", 100)
        self.unit = config.options.get("unit", "")
        self.show_target = config.options.get("show_target", True)
        self.icon = config.options.get("icon")

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the progress widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get scaled fonts
        font_label = ctx.get_font("small")
        font_value = ctx.get_font("regular")
        font_percent = ctx.get_font("small")

        # Calculate relative padding and sizes
        padding = int(ctx.width * 0.05)
        icon_size = max(10, int(ctx.height * 0.23))
        bar_height = max(6, int(ctx.height * 0.17))

        # Get entity state
        state = self.get_entity_state(hass)
        current_value = 0.0
        display_value = "0"

        if state is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(state.state)
                display_value = f"{current_value:.0f}"
            if not self.unit:
                self.unit = state.attributes.get("unit_of_measurement", "")

        # Calculate percentage
        target = self.target or 100
        percent = min(100, (current_value / target) * 100) if target > 0 else 0

        # Get label
        name = self.config.label
        if not name and state:
            name = state.attributes.get("friendly_name", "")
        name = name or "Progress"

        color = self.config.color or COLOR_CYAN

        # Layout: icon/label on left, value/target on right, bar below
        top_y = int(ctx.height * 0.25)

        # Icon if present
        text_x = padding
        if self.icon:
            ctx.draw_icon(
                self.icon,
                (padding, top_y - icon_size // 2),
                size=icon_size,
                color=color,
            )
            text_x = padding + icon_size + 4

        # Label
        ctx.draw_text(
            name.upper(),
            (text_x, top_y),
            font=font_label,
            color=COLOR_GRAY,
            anchor="lm",
        )

        # Value / target
        value_text = f"{display_value}/{target:.0f}" if self.show_target else display_value
        if self.unit:
            value_text += f" {self.unit}"

        ctx.draw_text(
            value_text,
            (ctx.width - padding, top_y),
            font=font_value,
            color=COLOR_WHITE,
            anchor="rm",
        )

        # Bottom row: progress bar and percentage
        bar_y = int(ctx.height * 0.60)
        percent_width = int(ctx.width * 0.22)
        bar_rect = (padding, bar_y, ctx.width - percent_width, bar_y + bar_height)
        ctx.draw_bar(bar_rect, percent, color, COLOR_DARK_GRAY)

        # Percentage
        ctx.draw_text(
            f"{percent:.0f}%",
            (ctx.width - padding, bar_y + bar_height // 2),
            font=font_percent,
            color=COLOR_WHITE,
            anchor="rm",
        )


class MultiProgressWidget(Widget):
    """Widget that displays multiple progress items in a list."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the multi-progress widget."""
        super().__init__(config)
        # List of progress configs: [(entity_id, label, target, color, icon), ...]
        self.items = config.options.get("items", [])
        self.title = config.options.get("title")

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on."""
        return [item.get("entity_id") for item in self.items if item.get("entity_id")]

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the multi-progress widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get scaled fonts based on container height
        font_title = ctx.get_font("small")
        font_label = ctx.get_font("tiny")

        # Calculate relative padding
        padding = int(ctx.width * 0.05)
        current_y = padding

        # Draw title if present
        title_height = 0
        if self.title:
            ctx.draw_text(
                self.title.upper(),
                (padding, current_y),
                font=font_title,
                color=COLOR_GRAY,
                anchor="lm",
            )
            title_height = int(ctx.height * 0.14)
            current_y += title_height

        # Calculate row height relative to container
        available_height = ctx.height - current_y - padding
        row_count = len(self.items) or 1
        row_height = min(int(ctx.height * 0.35), available_height // row_count)
        bar_height = max(4, int(ctx.height * 0.06))
        icon_size = max(8, int(ctx.height * 0.09))

        # Draw each progress item
        for item in self.items:
            entity_id = item.get("entity_id")
            label = item.get("label", "")
            target = item.get("target", 100)
            color = item.get("color", COLOR_CYAN)
            icon = item.get("icon")
            unit = item.get("unit", "")

            # Get state
            current_value = 0.0
            if hass and entity_id:
                state = hass.states.get(entity_id)
                if state is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        current_value = float(state.state)
                    if not label:
                        label = state.attributes.get("friendly_name", entity_id)
                    if not unit:
                        unit = state.attributes.get("unit_of_measurement", "")

            label = label or entity_id or "Item"
            percent = min(100, (current_value / target) * 100) if target > 0 else 0

            # Draw icon if present
            label_x = padding
            if icon:
                ctx.draw_icon(
                    icon,
                    (padding, current_y + 2),
                    size=icon_size,
                    color=color,
                )
                label_x = padding + icon_size + 4

            # Draw label
            ctx.draw_text(
                label.upper(),
                (label_x, current_y + int(row_height * 0.2)),
                font=font_label,
                color=COLOR_GRAY,
                anchor="lm",
            )

            # Draw value/target
            value_text = f"{current_value:.0f}/{target:.0f}"
            if unit:
                value_text += f" {unit}"
            ctx.draw_text(
                value_text,
                (ctx.width - padding, current_y + int(row_height * 0.2)),
                font=font_label,
                color=COLOR_WHITE,
                anchor="rm",
            )

            # Draw progress bar
            bar_y = current_y + int(row_height * 0.55)
            percent_width = int(ctx.width * 0.20)
            bar_rect = (padding, bar_y, ctx.width - percent_width, bar_y + bar_height)
            ctx.draw_bar(bar_rect, percent, color, COLOR_DARK_GRAY)

            # Draw percentage
            ctx.draw_text(
                f"{percent:.0f}%",
                (ctx.width - padding, bar_y + bar_height // 2),
                font=font_label,
                color=COLOR_WHITE,
                anchor="rm",
            )

            current_y += row_height
