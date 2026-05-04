"""Clock widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
    Component,
    _resolve_color,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


@dataclass
class ClockDisplay(Component):
    """Clock display component with time, date, and optional label.

    Time fills the available space, date scales proportionally.
    All sizing is computed together to ensure proper layout.
    """

    time_str: str
    date_str: str | None = None
    ampm: str | None = None
    label: str | None = None
    time_color: Color = THEME_TEXT_PRIMARY
    date_color: Color = THEME_TEXT_SECONDARY
    label_color: Color = THEME_TEXT_SECONDARY

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render clock with time, date, and optional AM/PM indicator.

        watchOS pattern: hero time fills the cell, caps-tracked date below
        in tertiary text, AM/PM as a small tinted accent next to the time.
        """
        # Resolve theme-aware colors
        time_color = _resolve_color(self.time_color, ctx)
        date_color = _resolve_color(self.date_color, ctx)
        label_color = _resolve_color(self.label_color, ctx)

        padding = max(4, int(width * 0.03))
        inner_width = width - padding * 2
        inner_height = height - padding * 2

        # Vertical space allocation — bias more toward the hero time.
        label_height = int(inner_height * 0.12) if self.label else 0
        date_height = int(inner_height * 0.16) if self.date_str else 0
        gap = 2

        # Time gets the remainder
        time_height = inner_height - label_height - date_height
        if self.label:
            time_height -= gap
        if self.date_str:
            time_height -= gap

        total_content = label_height + time_height + date_height
        if self.label:
            total_content += gap
        if self.date_str:
            total_content += gap
        start_y = y + padding + (inner_height - total_content) // 2

        current_y = start_y
        center_x = x + width // 2

        # Caps-tracked label at top
        if self.label:
            ctx.draw_label(
                self.label,
                (center_x, current_y + label_height // 2),
                color=label_color,
                anchor="mm",
                size="tertiary",
            )
            current_y += label_height + gap

        # Hero time — bold, fills available space (watchOS large complication)
        time_font = ctx.fit_text(
            self.time_str,
            max_width=int(inner_width * 0.96),
            max_height=int(time_height * 0.95),
            bold=True,
        )
        time_y = current_y + time_height // 2

        if self.ampm:
            # 12-hour: time + small tinted AM/PM
            time_w, time_h = ctx.get_text_size(self.time_str, time_font)
            ampm_font = ctx.get_font("tertiary", semibold=True)
            ampm_w, _ = ctx.get_text_size(self.ampm, ampm_font)
            spacing = 4
            total_w = time_w + spacing + ampm_w
            time_x = center_x - total_w // 2 + time_w // 2
            ctx.draw_text(
                self.time_str, (time_x, time_y), font=time_font, color=time_color, anchor="mm"
            )
            # AM/PM in primary tint (the theme's primary color), aligned to top
            # of the time so it reads as a small superscript-like accent.
            uses_default_color = isinstance(self.time_color, tuple) and self.time_color == (
                -1,
                -1,
                -1,
            )
            ampm_color = ctx.theme.primary if uses_default_color else time_color
            ctx.draw_text(
                self.ampm,
                (time_x + time_w // 2 + spacing + ampm_w // 2, time_y - time_h // 4),
                font=ampm_font,
                color=ampm_color,
                anchor="mm",
            )
        else:
            ctx.draw_text(
                self.time_str,
                (center_x, time_y),
                font=time_font,
                color=time_color,
                anchor="mm",
            )

        current_y += time_height + gap

        # Caps-tracked date below
        if self.date_str:
            ctx.draw_label(
                self.date_str,
                (center_x, current_y + date_height // 2),
                color=date_color,
                anchor="mm",
                size="tertiary",
                adjust=+1,
            )


class ClockWidget(Widget):
    """Widget that displays current time and date."""

    WIDGET_TYPE: ClassVar[str] = "clock"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Clock",
        "needs_entity": False,
        "options": [
            {"key": "show_date", "type": "boolean", "label": "Show Date", "default": True},
            {"key": "show_seconds", "type": "boolean", "label": "Show Seconds", "default": False},
            {
                "key": "time_format",
                "type": "select",
                "label": "Time Format",
                "options": ["24h", "12h"],
                "default": "24h",
            },
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the clock widget."""
        super().__init__(config)
        self.show_date = config.options.get("show_date", True)
        self.show_seconds = config.options.get("show_seconds", False)
        self.time_format = config.options.get("time_format", "24h")
        self.timezone = config.options.get("timezone")

    def get_entities(self) -> list[str]:
        """Clock widget doesn't depend on entities."""
        return []

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the clock widget as a Component tree.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with current time
        """
        # Get time from state (coordinator handles timezone)
        now = state.now or datetime.now(tz=UTC)

        # Format time
        if self.show_seconds:
            if self.time_format == "12h":
                time_str = now.strftime("%I:%M:%S")
                ampm = now.strftime("%p")
            else:
                time_str = now.strftime("%H:%M:%S")
                ampm = None
        elif self.time_format == "12h":
            time_str = now.strftime("%I:%M")
            ampm = now.strftime("%p")
        else:
            time_str = now.strftime("%H:%M")
            ampm = None

        date_str = now.strftime("%a, %b %d") if self.show_date else None
        color = self.config.color or THEME_TEXT_PRIMARY

        return ClockDisplay(
            time_str=time_str,
            date_str=date_str,
            ampm=ampm,
            label=self.config.label,
            time_color=color,
        )
