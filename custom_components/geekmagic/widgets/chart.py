"""Chart widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import COLOR_CYAN  # Used as component dataclass default
from .base import Widget, WidgetConfig
from .components import THEME_TEXT_SECONDARY, Color, Component, Row, Spacer, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


@dataclass
class ChartDisplay(Component):
    """Sparkline chart display component."""

    data: list[float] = field(default_factory=list)
    label: str | None = None
    current_value: float | None = None
    unit: str = ""
    color: Color = COLOR_CYAN
    show_range: bool = True
    fill: bool = False
    gradient: bool = False

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render chart with header, sparkline, and optional range."""
        font_label = ctx.get_font("small")
        padding = int(width * 0.08)

        # Calculate chart area
        header_height = int(height * 0.15) if self.label else int(height * 0.08)
        is_binary = self._is_binary_data()
        if self.show_range and not is_binary:
            footer_height = int(height * 0.12)
        else:
            footer_height = int(height * 0.04)
        chart_top = y + header_height
        chart_bottom = y + height - footer_height
        chart_rect = (x + padding, chart_top, x + width - padding, chart_bottom)

        # Decide which header pieces fit. The value is more informative than
        # the label at narrow sizes, so drop the label first when the two
        # together would overflow the inner header width.
        inner_w = width - padding * 2
        value_str = f"{self.current_value:.1f}{self.unit}" if self.current_value is not None else ""

        show_label = bool(self.label)
        show_value = bool(value_str)
        if show_label and show_value:
            font_value = ctx.get_font("regular")
            label_w, _ = ctx.get_text_size(self.label.upper(), font_label)
            value_w, _ = ctx.get_text_size(value_str, font_value)
            if label_w + value_w + 4 > inner_w:
                show_label = False  # Value wins; label drops to make room.

        header_children: list[Component] = []
        if show_label:
            header_children.append(
                Text(
                    text=self.label.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                    truncate=True,
                )
            )
        if show_value:
            if show_label:
                header_children.append(Spacer())
            header_children.append(
                Text(
                    text=value_str,
                    font="regular",
                    color=self.color,
                    align="end" if show_label else "center",
                    auto_fit=True,
                )
            )

        if header_children:
            Row(
                children=header_children,
                gap=4,
                padding=padding,
                align="center",
                justify="center" if not show_label else "start",
            ).render(ctx, x, y, width, header_height)

        # Draw chart
        if len(self.data) >= 2:
            if is_binary:
                ctx.draw_timeline_bar(chart_rect, self.data, on_color=self.color)
            else:
                ctx.draw_sparkline(
                    chart_rect, self.data, color=self.color, fill=self.fill, gradient=self.gradient
                )

                if self.show_range:
                    min_val = min(self.data)
                    max_val = max(self.data)
                    range_y = chart_bottom + int(height * 0.08)
                    ctx.draw_text(
                        f"{min_val:.1f}",
                        (x + padding, range_y),
                        font=font_label,
                        color=THEME_TEXT_SECONDARY,
                        anchor="lm",
                    )
                    ctx.draw_text(
                        f"{max_val:.1f}",
                        (x + width - padding, range_y),
                        font=font_label,
                        color=THEME_TEXT_SECONDARY,
                        anchor="rm",
                    )
        else:
            center_x = x + width // 2
            center_y = (chart_top + chart_bottom) // 2
            ctx.draw_text(
                "No data",
                (center_x, center_y),
                font=font_label,
                color=THEME_TEXT_SECONDARY,
                anchor="mm",
            )

    def _is_binary_data(self) -> bool:
        """Check if data is binary (all 0.0 or 1.0)."""
        if not self.data:
            return False
        return all(v in {0.0, 1.0} for v in self.data)


class ChartWidget(Widget):
    """Widget that displays a sparkline chart from entity history."""

    WIDGET_TYPE: ClassVar[str] = "chart"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Chart",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {
                "key": "period",
                "type": "select",
                "label": "Period",
                "options": ["5 min", "15 min", "1 hour", "6 hours", "24 hours"],
                "default": "24 hours",
            },
            {
                "key": "show_value",
                "type": "boolean",
                "label": "Show Current Value",
                "default": True,
            },
            {
                "key": "show_range",
                "type": "boolean",
                "label": "Show Min/Max Range",
                "default": True,
            },
            {"key": "fill", "type": "boolean", "label": "Fill Area", "default": False},
            {
                "key": "color_gradient",
                "type": "boolean",
                "label": "Value Gradient",
                "default": False,
            },
        ],
    }

    PERIOD_TO_HOURS: ClassVar[dict[str, float]] = {
        "5 min": 5 / 60,
        "15 min": 15 / 60,
        "1 hour": 1,
        "6 hours": 6,
        "24 hours": 24,
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the chart widget."""
        super().__init__(config)
        period = config.options.get("period")
        if period and isinstance(period, str):
            self.hours = self.PERIOD_TO_HOURS.get(period, 24)
        elif period and isinstance(period, int | float):
            self.hours = period / 60
        else:
            self.hours = config.options.get("hours", 24)
        self.show_value = config.options.get("show_value", True)
        self.show_range = config.options.get("show_range", True)
        self.fill = config.options.get("fill", True)  # Default to filled area
        self.color_gradient = config.options.get("color_gradient", False)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the chart widget.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with history data
        """
        entity = state.entity
        current_value = None
        unit = ""
        label = self.config.label

        if entity is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(entity.state)
            unit = entity.unit or ""
            if not label:
                label = entity.friendly_name

        return ChartDisplay(
            data=list(state.history),
            label=label,
            current_value=current_value if self.show_value else None,
            unit=unit,
            color=self.config.color or ctx.theme.get_accent_color(self.config.slot),
            show_range=self.show_range,
            fill=self.fill,
            gradient=self.color_gradient,
        )
