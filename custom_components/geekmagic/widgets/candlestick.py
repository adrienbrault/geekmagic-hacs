"""Candlestick chart widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from .base import Widget, WidgetConfig
from .components import THEME_TEXT_SECONDARY, Color, Component, Row, Spacer, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def aggregate_ohlc(
    timestamped_values: list[tuple[float, float]],
    interval_seconds: int,
    candle_count: int,
) -> list[tuple[float, float, float, float]]:
    """Aggregate timestamped values into OHLC candles.

    Args:
        timestamped_values: List of (timestamp, value) tuples, sorted by time.
        interval_seconds: Duration of each candle in seconds.
        candle_count: Number of candles to produce.

    Returns:
        List of (open, high, low, close) tuples, one per candle.
    """
    if not timestamped_values:
        return []

    # Determine the end time from the last data point
    end_ts = timestamped_values[-1][0]
    start_ts = end_ts - (candle_count * interval_seconds)

    # Bucket values into candles
    buckets: list[list[float]] = [[] for _ in range(candle_count)]

    for ts, value in timestamped_values:
        if ts < start_ts:
            continue
        bucket_idx = int((ts - start_ts) / interval_seconds)
        # Clamp to last bucket for points exactly at the end boundary
        bucket_idx = min(bucket_idx, candle_count - 1)
        if bucket_idx >= 0:
            buckets[bucket_idx].append(value)

    # Convert buckets to OHLC tuples
    candles: list[tuple[float, float, float, float]] = []
    last_close: float | None = None

    # Find first non-empty bucket to seed last_close
    for values in buckets:
        if values:
            last_close = values[0]
            break

    if last_close is None:
        return []

    # Also check for values before start_ts to seed last_close
    for ts, value in timestamped_values:
        if ts < start_ts:
            last_close = value
        else:
            break

    for values in buckets:
        if values:
            o = values[0]
            h = max(values)
            l = min(values)  # noqa: E741
            c = values[-1]
            candles.append((o, h, l, c))
            last_close = c
        else:
            # Empty bucket: flat candle at last close
            candles.append((last_close, last_close, last_close, last_close))

    return candles


@dataclass
class CandlestickDisplay(Component):
    """Candlestick chart display component."""

    data: list[tuple[float, float, float, float]] = field(default_factory=list)
    label: str | None = None
    current_value: float | None = None
    unit: str = ""
    show_value: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render candlestick chart with header and candles."""
        font_label = ctx.get_font("small")
        padding = int(width * 0.08)

        # Calculate chart area
        header_height = int(height * 0.15) if self.label else int(height * 0.08)
        footer_height = int(height * 0.04)
        chart_top = y + header_height
        chart_bottom = y + height - footer_height
        chart_left = x + padding
        chart_right = x + width - padding
        chart_height = chart_bottom - chart_top
        chart_width = chart_right - chart_left

        # Build header using declarative components
        header_children: list[Component] = []
        if self.label:
            header_children.append(
                Text(
                    text=self.label.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                    truncate=True,
                )
            )
        if self.show_value and self.current_value is not None:
            value_str = f"{self.current_value:.1f}{self.unit}"
            if self.label:
                header_children.append(Spacer())
            # Color the value based on last candle direction
            value_color: Color = THEME_TEXT_SECONDARY
            if self.data:
                last = self.data[-1]
                value_color = ctx.theme.success if last[3] >= last[0] else ctx.theme.error
            header_children.append(
                Text(text=value_str, font="regular", color=value_color, align="end")
            )

        if header_children:
            Row(
                children=header_children,
                gap=4,
                padding=padding,
                align="center",
            ).render(ctx, x, y, width, header_height)

        # Draw candles
        if not self.data:
            center_x = x + width // 2
            center_y = (chart_top + chart_bottom) // 2
            ctx.draw_text(
                "No data",
                (center_x, center_y),
                font=font_label,
                color=THEME_TEXT_SECONDARY,
                anchor="mm",
            )
            return

        # Find global min/max for scaling
        all_highs = [c[1] for c in self.data]
        all_lows = [c[2] for c in self.data]
        data_min = min(all_lows)
        data_max = max(all_highs)

        # Add small margin to prevent candles from touching edges
        data_range = data_max - data_min
        if data_range == 0:
            data_range = 1.0
            data_min -= 0.5
            data_max += 0.5

        margin = data_range * 0.05
        data_min -= margin
        data_max += margin
        data_range = data_max - data_min

        num_candles = len(self.data)
        # Each candle gets equal width with a gap between them
        candle_total_width = chart_width / num_candles
        gap = max(1, int(candle_total_width * 0.2))
        candle_body_width = max(1, int(candle_total_width - gap))

        for i, (o, h, l, c) in enumerate(self.data):  # noqa: E741
            bullish = c >= o
            color = ctx.theme.success if bullish else ctx.theme.error

            # X position for this candle
            candle_x = chart_left + int(i * candle_total_width) + gap // 2
            candle_center_x = candle_x + candle_body_width // 2

            # Y positions (inverted: higher value = lower y)
            def val_to_y(val: float) -> int:
                return chart_bottom - int((val - data_min) / data_range * chart_height)

            wick_top_y = val_to_y(h)
            wick_bottom_y = val_to_y(l)
            body_top_y = val_to_y(max(o, c))
            body_bottom_y = val_to_y(min(o, c))

            # Ensure body has at least 1px height
            if body_bottom_y <= body_top_y:
                body_bottom_y = body_top_y + 1

            # Draw wick (vertical line from high to low)
            ctx.draw_line(
                [(candle_center_x, wick_top_y), (candle_center_x, wick_bottom_y)],
                fill=color,
                width=1,
            )

            # Draw body (filled rectangle)
            ctx.draw_rect(
                (candle_x, body_top_y, candle_x + candle_body_width, body_bottom_y),
                fill=color,
            )


INTERVAL_TO_SECONDS: dict[str, int] = {
    "1 hour": 3600,
    "4 hours": 14400,
    "1 day": 86400,
}


class CandlestickWidget(Widget):
    """Widget that displays a candlestick chart from entity history."""

    INTERVAL_TO_HOURS: ClassVar[dict[str, float]] = {
        "1 hour": 1,
        "4 hours": 4,
        "1 day": 24,
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the candlestick widget."""
        super().__init__(config)
        self.candle_interval: str = config.options.get("candle_interval", "4 hours")
        self.candle_count: int = int(config.options.get("candle_count", 20))
        self.show_value: bool = config.options.get("show_value", True)

    @property
    def hours(self) -> float:
        """Total hours of history needed."""
        interval_hours = self.INTERVAL_TO_HOURS.get(self.candle_interval, 4)
        return interval_hours * self.candle_count

    @property
    def interval_seconds(self) -> int:
        """Candle interval in seconds."""
        return INTERVAL_TO_SECONDS.get(self.candle_interval, 14400)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the candlestick chart widget."""
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

        return CandlestickDisplay(
            data=list(state.candlestick_data),
            label=label,
            current_value=current_value if self.show_value else None,
            unit=unit,
            show_value=self.show_value,
        )
