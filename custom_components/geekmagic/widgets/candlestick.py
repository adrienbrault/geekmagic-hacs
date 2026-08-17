"""Candlestick chart widget for GeekMagic displays."""

from __future__ import annotations

import contextlib
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import css_rgb, css_rgba, mdi_span
from ._textfit import metrics_for
from .base import Widget, WidgetConfig
from .chart import PlotMetrics, compact_header, empty_plot, fit_px, plot_metrics, value_header
from .state import CandleSpec, DataNeeds

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from ._textfit import TextMetrics
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
            low = min(values)
            c = values[-1]
            candles.append((o, h, low, c))
            last_close = c
        else:
            # Empty bucket: flat candle at last close
            candles.append((last_close, last_close, last_close, last_close))

    return candles


INTERVAL_TO_SECONDS: dict[str, int] = {
    "1 hour": 3600,
    "4 hours": 14400,
    "1 day": 86400,
}


def _candles_svg(
    data: list[tuple[float, float, float, float]],
    up_color: str,
    down_color: str,
    *,
    aspect: float = 2.0,
    box_h: float = 100.0,
    wick_px: float = 1.2,
    corner_px: float = 1.3,
    baseline_color: str | None = None,
) -> str:
    """Build an OHLC candle chart as inline SVG.

    The viewBox matches the box the SVG will fill (``aspect`` =
    width/height), so one viewBox unit is the same number of device
    pixels on both axes — that is what keeps the rounded body corners
    circular and the inter-candle gaps optically even under stretching.
    Wicks keep a constant on-screen width via ``vector-effect:
    non-scaling-stroke``. Colors must be concrete CSS colors —
    ``var()`` does not resolve inside SVG paint attributes in Blitz.

    Args:
        data: OHLC tuples, oldest first.
        up_color: Fill/stroke for bullish candles.
        down_color: Fill/stroke for bearish candles.
        aspect: Width / height of the box the SVG fills.
        box_h: Height of that box in CSS pixels (converts px-sized
            details — corner radius, minimum body — into viewBox units).
        wick_px: Wick stroke width in CSS pixels.
        corner_px: Body corner radius in CSS pixels.
        baseline_color: When set, a dashed hairline is drawn at the last
            close price.
    """
    vb_w = 100.0 * max(0.4, aspect)
    unit = 100.0 / max(8.0, box_h)  # viewBox units per CSS pixel

    # Find global min/max for scaling
    all_highs = [c[1] for c in data]
    all_lows = [c[2] for c in data]
    data_min = min(all_lows)
    data_max = max(all_highs)

    data_range = data_max - data_min
    if data_range == 0:
        data_range = 1.0
        data_min -= 0.5
        data_max += 0.5

    # Small margin so candles never touch the edges
    margin = data_range * 0.06
    data_min -= margin
    data_max += margin
    data_range = data_max - data_min

    num_candles = len(data)
    # Equal slots with a breathing gap; bodies never fall under a pixel.
    slot = vb_w / num_candles
    body_w = max(slot * 0.72, min(slot * 0.9, 1.0 * unit))
    min_body_h = 1.4 * unit

    def val_to_y(val: float) -> float:
        return 100.0 - (val - data_min) / data_range * 100.0

    parts = [
        f'<svg viewBox="0 0 {vb_w:.1f} 100" preserveAspectRatio="none" '
        'style="width:100%;height:100%;display:block">'
    ]

    if baseline_color:
        # Last close reference line — the "you are here" of a price chart.
        base_y = val_to_y(data[-1][3])
        parts.append(
            f'<line x1="0" x2="{vb_w:.1f}" y1="{base_y:.2f}" y2="{base_y:.2f}" '
            f'stroke="{baseline_color}" stroke-width="1" stroke-dasharray="2.5 3.5" '
            'vector-effect="non-scaling-stroke"/>'
        )

    for i, (o, h, low, c) in enumerate(data):
        bullish = c >= o
        color = up_color if bullish else down_color

        center_x = (i + 0.5) * slot
        body_x = center_x - body_w / 2

        wick_top = val_to_y(h)
        wick_bottom = val_to_y(low)
        body_top = val_to_y(max(o, c))
        body_h = val_to_y(min(o, c)) - body_top

        # Keep flat/doji candles visible as a thin bar.
        if body_h < min_body_h:
            body_top = min(body_top - (min_body_h - body_h) / 2, 100.0 - min_body_h)
            body_top = max(body_top, 0.0)
            body_h = min_body_h

        radius = min(corner_px * unit, body_w * 0.38, body_h * 0.38)

        parts.append(
            f'<line x1="{center_x:.2f}" x2="{center_x:.2f}" '
            f'y1="{wick_top:.2f}" y2="{wick_bottom:.2f}" '
            f'stroke="{color}" stroke-width="{wick_px:.2f}" stroke-linecap="round" '
            'vector-effect="non-scaling-stroke"/>'
        )
        parts.append(
            f'<rect x="{body_x:.2f}" y="{body_top:.2f}" '
            f'width="{body_w:.2f}" height="{body_h:.2f}" rx="{radius:.2f}" fill="{color}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


class CandlestickWidget(Widget):
    """Widget that displays a candlestick chart from entity history."""

    WIDGET_TYPE: ClassVar[str] = "candlestick"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Candlestick Chart",
        "needs_entity": True,
        "entity_domains": None,
        "options": [
            {
                "key": "candle_interval",
                "type": "select",
                "label": "Candle Interval",
                "options": ["1 hour", "4 hours", "1 day"],
                "default": "4 hours",
            },
            {
                "key": "candle_count",
                "type": "number",
                "label": "Number of Candles",
                "min": 5,
                "max": 40,
                "default": 20,
            },
            {
                "key": "show_value",
                "type": "boolean",
                "label": "Show Current Value",
                "default": True,
            },
        ],
    }

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

    def data_needs(self) -> DataNeeds:
        """Candles are aggregated from history, not read off the state."""
        if not self.config.entity_id:
            return DataNeeds()
        return DataNeeds(
            candles=CandleSpec(
                hours=self.hours,
                interval_seconds=self.interval_seconds,
                count=self.candle_count,
            )
        )

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the candlestick chart: price header above the candles."""
        m = plot_metrics(ctx)
        tm = metrics_for(ctx.theme)

        entity = state.entity
        current_value = None
        unit = ""
        if entity is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(entity.state)
            unit = entity.unit or ""

        data = list(state.candlestick_data)

        # Bull/bear tints resolved from the theme: var() does not resolve
        # inside SVG paint attributes, so the SVG needs concrete colors.
        # (HTML text can still use the CSS variables.)
        up_color = css_rgb(ctx.theme.success) if ctx.theme else "var(--success)"
        down_color = css_rgb(ctx.theme.error) if ctx.theme else "var(--error)"

        # The header takes the direction of the most recent candle — here
        # the tint IS the meaning, so it carries the value as well as the
        # caret.
        bullish = bool(data) and data[-1][3] >= data[-1][0]
        value_color = "var(--text-secondary)"
        caret = ""
        if data:
            value_color = "var(--success)" if bullish else "var(--error)"
            caret = "menu-up" if bullish else "menu-down"

        header, header_h = "", 0.0
        if not m.compact:
            header, header_h = self._header(
                self.label_for(entity),
                m,
                tm,
                current_value=current_value,
                unit=unit,
                color=value_color,
                caret=caret,
            )
        else:
            # Compact tiles keep the caption AND a small tinted value —
            # unlabeled candles are noise, and a labeled tile without
            # its price only says "it moved".
            value_text = ""
            if current_value is not None:
                value_text = f"{current_value:.1f}{unit}"
            header, header_h = compact_header(
                self.label_for(entity),
                ctx,
                m,
                tm,
                value_text=value_text,
                value_color=value_color,
            )

        bands = 1 + bool(header)
        plot_h = max(16.0, m.inner_h - header_h - m.gap * (bands - 1))
        # ``aspect`` drives the SVG's rendered height (width / aspect) —
        # see PlotMetrics for why this is measured in Python.
        aspect = m.inner_w / plot_h

        if data:
            svg = _candles_svg(
                data,
                up_color,
                down_color,
                aspect=aspect,
                box_h=plot_h,
                wick_px=fit_px(1.0, 0.9 + min(ctx.width, ctx.height) / 240.0 * 0.6, 1.5),
                corner_px=fit_px(0.8, min(ctx.width, ctx.height) / 240.0 * 1.6, 1.6),
                # The reference line needs room to read as structure
                # rather than as a stray edge — skip it in tiny cells.
                baseline_color=(
                    css_rgba(ctx.theme.text_primary, 0.15) if ctx.theme and not m.compact else None
                ),
            )
            chart = f'<div style="width: 100%">{svg}</div>'
        else:
            chart = empty_plot(m, plot_h)

        justify = "center" if bands == 1 else "space-between"
        return (
            f'<div class="cell" style="align-items: stretch; justify-content: {justify}; '
            f'padding: {m.pad_y}px {m.pad_x}px">'
            f"{header}{chart}"
            "</div>"
        )

    def _header(
        self,
        caption: str,
        m: PlotMetrics,
        tm: TextMetrics,
        *,
        current_value: float | None,
        unit: str,
        color: str,
        caret: str,
    ) -> tuple[str, float]:
        """Caption + last price, tinted by the last candle's direction.

        Here the tint IS the meaning (the documented status exception),
        so the caret, the number and the unit all take it.
        """
        value_html = ""
        value_w = 0.0
        if self.show_value and current_value is not None:
            value_text = f"{current_value:.1f}"
            caret_html = ""
            # Below ~16px the triangle degenerates into a nub — the tint
            # already carries the direction, so spend the width on the
            # caption instead.
            if caret and m.value_px >= 16.0:
                caret_px = m.value_px * 0.72
                value_w += caret_px  # MDI glyphs advance exactly 1em
                caret_html = mdi_span("mdi:" + caret, "icon", f"font-size: {caret_px:.1f}px")
            value_w += tm.width(value_text, m.value_px, "bold")
            unit_html = ""
            if unit:
                value_w += tm.width(unit, m.unit_px, "semibold")
                unit_html = (
                    f'<span class="t-unit" style="font-size: {m.unit_px:.1f}px; '
                    f'color: {color}">{escape(unit)}</span>'
                )
            value_html = (
                f'<span class="t-value" style="font-size: {m.value_px:.1f}px; color: {color}">'
                f"{caret_html}{escape(value_text)}{unit_html}</span>"
            )

        return value_header(caption=caption, value_html=value_html, value_width=value_w, m=m, tm=tm)
