"""Chart widget for GeekMagic displays.

Also hosts the small measurement + header primitives shared with the
candlestick widget: both draw an SVG plot under a caption/value header,
and both need to know how tall that plot box will be *before* the engine
lays it out.
"""

from __future__ import annotations

import contextlib
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from ..htmldoc import css_rgb, svg_sparkline
from ._cellkit import label_px as _kit_label_px
from ._fit import fit_caption_sized
from ._textfit import TextMetrics, metrics_for
from .base import Widget, WidgetConfig
from .state import DataNeeds

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState


def _format_period(hours: float) -> str:
    """Format a chart period as a compact label (e.g. "24h", "15m")."""
    if hours <= 0:
        return ""
    if hours < 1:
        return f"{round(hours * 60)}m"
    return f"{round(hours)}h"


def _is_binary_data(data: list[float]) -> bool:
    """Check if data is binary (all 0.0 or 1.0)."""
    if not data:
        return False
    return all(v in {0.0, 1.0} for v in data)


def _range_text(value: float) -> str:
    """Format a range bound: a decimal only where it still carries meaning."""
    return f"{value:.0f}" if abs(value) >= 100 else f"{value:.1f}"


def fit_px(low: float, value: float, high: float) -> float:
    """Python mirror of CSS ``clamp()`` — keeps layout maths and type in sync."""
    return max(low, min(value, high))


class PlotMetrics(NamedTuple):
    """Measured geometry of a chart cell, in CSS pixels.

    Blitz sizes an inline ``<svg>`` from its viewBox aspect ratio — a
    percentage height against a flex-sized parent does not resolve — so
    the plot box has to be measured in Python and handed to the SVG
    helpers as ``aspect``. Percentage *padding* is equally unusable: CSS
    resolves it against the cell width on both axes, which collapses
    wide/short cells. Hence px everywhere.
    """

    pad_x: int
    pad_y: int
    inner_w: float
    inner_h: float
    label_px: float
    value_px: float
    unit_px: float
    detail_px: float
    gap: float
    compact: bool


def plot_metrics(ctx: CellContext) -> PlotMetrics:
    """Measure a chart cell: insets, type sizes, and the band gap."""
    w, h = ctx.width, ctx.height
    pad_x = max(4, round(w * 0.055))
    pad_y = max(4, round(h * 0.05))
    # Mirror of the kit's clamp() sizing for .t-value; .t-label comes
    # from _cellkit, which owns the kit type mirrors.
    value_px = fit_px(13.0, min(0.17 * min(w, h), 0.115 * w), 31.0)
    return PlotMetrics(
        pad_x=pad_x,
        pad_y=pad_y,
        inner_w=max(24.0, w - 2.0 * pad_x),
        inner_h=max(24.0, h - 2.0 * pad_y),
        label_px=_kit_label_px(ctx),
        value_px=value_px,
        unit_px=value_px * 0.64,
        detail_px=fit_px(10.0, min(0.115 * min(w, h), 0.085 * w), 17.0),
        gap=max(3.0, h * 0.035),
        compact=h < 100 or w < 100,
    )


def value_header(
    *,
    caption: str,
    value_html: str,
    value_width: float,
    m: PlotMetrics,
    tm: TextMetrics,
) -> tuple[str, float]:
    """Caption + value header, and the height it occupies.

    Wide cells set caption (left) and value (right) on one baseline.
    When the row can't hold both without crushing the caption — narrow
    chart columns — the header STACKS instead: the caption takes its
    own full-width line above the value, so "BITCOIN" renders whole
    where the shared row managed "BITC…". ``value_width`` is the
    caller's measured width of the value group; captions never overflow
    because Blitz draws no ellipsis and does not clip text.
    """
    upper = caption.upper() if caption else ""
    inline_caption_w = tm.width(upper, m.label_px, "bold", tm.label_tracking) if upper else 0.0
    stacked = bool(upper) and value_width + inline_caption_w + 8.0 > m.inner_w

    if stacked:
        # Full width to itself: shrink toward 10px to keep the whole
        # word, then truncate.
        px = tm.fit_font_size(
            upper, m.inner_w, m.label_px, "bold", tracking=tm.label_tracking, min_px=10.0
        )
        text = tm.truncate(upper, px, m.inner_w, "bold", tracking=tm.label_tracking, min_chars=3)
        header = (
            '<div class="hide-short">'
            f'<div class="t-label" style="font-size: {px:.1f}px; text-align: left; '
            f'padding-bottom: {px * 0.3:.0f}px">{escape(text)}</div>'
            '<div style="display: flex; align-items: baseline; '
            f'justify-content: flex-start">{value_html}</div></div>'
        )
        return header, px * 1.3 + m.value_px

    caption_html = ""
    available = m.inner_w - value_width - 8.0
    if upper:
        text = tm.truncate(upper, m.label_px, available, weight="bold", tracking=tm.label_tracking)
        # A caption cut down to a letter or two is noise, not a label —
        # give the row to the value instead.
        if text == upper or len(text) > 4:
            caption_html = f'<span class="t-label">{escape(text)}</span>'
    if not caption_html and not value_html:
        return "", 0.0
    # With no caption the value anchors the row on its own; left-aligned
    # it reads as a heading rather than a stranded number.
    justify = "space-between" if caption_html else "flex-start"
    # Hide classes live on a plain wrapper: an inline display would
    # defeat the kit's display:none media queries.
    header = (
        '<div class="hide-short hide-narrow">'
        '<div style="display: flex; align-items: baseline; '
        f'justify-content: {justify}; gap: 6px">'
        f"{caption_html}{value_html}</div></div>"
    )
    return header, max(m.value_px if value_html else 0.0, m.label_px if caption_html else 0.0)


def compact_header(
    caption: str,
    ctx: CellContext,
    m: PlotMetrics,
    tm: TextMetrics,
    *,
    value_text: str = "",
    value_color: str | None = None,
) -> tuple[str, float]:
    """Compact tile header: caption over a small tinted value.

    Compact plot cells shed the full value row, but a tile should still
    say BOTH what it tracks and where it stands — the caption shrinks
    to keep the whole word (shared ``fit_caption_sized`` policy) and
    the value renders one step below it, small and tinted, leaving the
    rest of the tile to the plot.
    """
    bands: list[str] = []
    height = 0.0
    if caption:
        text, px = fit_caption_sized(caption, ctx, m.inner_w)
        if text:
            bands.append(
                f'<div class="t-label" style="font-size: {px:.1f}px; text-align: center">'
                f"{escape(text)}</div>"
            )
            height += px * 1.15
    if value_text:
        vpx = tm.fit_font_size(value_text, m.inner_w, min(16.0, m.value_px), "bold", min_px=10.0)
        fitted = tm.truncate(value_text, vpx, m.inner_w, "bold", min_chars=2)
        color = f" color: {value_color};" if value_color else ""
        bands.append(
            f'<div style="font-size: {vpx:.1f}px; font-weight: 700; line-height: 1.05; '
            f'text-align: center; white-space: nowrap;{color}">{escape(fitted)}</div>'
        )
        height += vpx * 1.15
    if not bands:
        return "", 0.0
    return "".join(bands), height


def empty_plot(m: PlotMetrics, plot_h: float) -> str:
    """Placeholder occupying the plot box when there is nothing to draw."""
    return (
        '<div style="display: flex; align-items: center; justify-content: center; '
        f'height: {plot_h:.0f}px">'
        f'<span style="font-size: {m.value_px * 0.68:.1f}px; font-weight: 700; '
        'letter-spacing: 0.08em; line-height: 1; color: var(--text-tertiary)">'
        "No data</span></div>"
    )


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
            {"key": "fill", "type": "boolean", "label": "Fill Area", "default": True},
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

    def data_needs(self) -> DataNeeds:
        """A chart plots recorder history over its configured period."""
        if not self.config.entity_id:
            return DataNeeds()
        return DataNeeds(history_hours=self.hours)

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the chart: value header, sparkline, low/high range strip."""
        m = plot_metrics(ctx)
        tm = metrics_for(ctx.theme)

        entity = state.entity
        current_value = None
        unit = ""
        if entity is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(entity.state)
            unit = entity.unit or ""

        color = css_rgb(self.config.color) if self.config.color else ctx.accent()

        data = state.history
        has_data = state.has_history()
        binary = _is_binary_data(data)

        header, header_h = "", 0.0
        footer, footer_h = "", 0.0
        if not m.compact:
            header, header_h = self._header(
                self.label_for(entity), m, tm, current_value=current_value, unit=unit, color=color
            )
            footer, footer_h = self._footer(
                data, self.show_range and has_data and not binary, m, tm
            )
        else:
            # Compact tiles keep the caption AND a small tinted value:
            # an unlabeled trace is a squiggle, and a labeled one with
            # no reading only says "something changed". The range rows
            # stay dropped.
            value_text = ""
            if self.show_value and current_value is not None:
                value_text = f"{current_value:.1f}{unit}"
            header, header_h = compact_header(
                self.label_for(entity),
                ctx,
                m,
                tm,
                value_text=value_text,
                value_color=color,
            )

        bands = 1 + bool(header) + bool(footer)
        plot_h = max(16.0, m.inner_h - header_h - footer_h - m.gap * (bands - 1))
        # ``aspect`` drives the SVG's rendered height (width / aspect).
        # inner_w deliberately ignores theme chrome padding: the real box
        # can only be narrower, so the plot can only come out shorter
        # than budgeted — never tall enough to overflow the cell.
        aspect = m.inner_w / plot_h

        if has_data:
            stroke_w = fit_px(1.8, 1.6 + min(ctx.width, ctx.height) / 240.0 * 1.6, 3.2)
            spark = svg_sparkline(
                data,
                stroke=color,
                # A wash you can actually see from across the room — the
                # gradient still fades to nothing at the baseline.
                fill_opacity=0.50 if self.fill else 0.0,
                stroke_width=stroke_w,
                aspect=aspect,
                # Bezier smoothing overshoots on square binary traces.
                smooth=not binary,
                show_dot=True,
            )
            plot = f'<div style="width: 100%">{spark}</div>'
        else:
            plot = empty_plot(m, plot_h)

        justify = "center" if bands == 1 else "space-between"
        return (
            f'<div class="cell" style="align-items: stretch; justify-content: {justify}; '
            f'padding: {m.pad_y}px {m.pad_x}px">'
            f"{header}{plot}{footer}"
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
    ) -> tuple[str, float]:
        """Caption + current value; the value carries the chart's tint.

        Value and line then read as one visual unit — the gauge-family
        exception to the "hero stays text-primary" rule.
        """
        value_html = ""
        value_w = 0.0
        if self.show_value and current_value is not None:
            value_text = f"{current_value:.1f}"
            value_w = tm.width(value_text, m.value_px, "bold")
            unit_html = ""
            if unit:
                value_w += tm.width(unit, m.unit_px, "semibold")
                unit_html = (
                    f'<span class="t-unit" style="font-size: {m.unit_px:.1f}px; '
                    f'color: {color}">{escape(unit)}</span>'
                )
            value_html = (
                f'<span class="t-value" style="font-size: {m.value_px:.1f}px; color: {color}">'
                f"{escape(value_text)}{unit_html}</span>"
            )

        return value_header(caption=caption, value_html=value_html, value_width=value_w, m=m, tm=tm)

    def _footer(
        self,
        data: list[float],
        enabled: bool,
        m: PlotMetrics,
        tm: TextMetrics,
    ) -> tuple[str, float]:
        """Low / period / high strip — typographic, not arrow soup.

        ``L``/``H`` are tracked caps in the tertiary tone with the numbers
        a step larger in the secondary tone, and the period sits centered
        as a quiet tag. Both the tag and the letters drop out (in that
        order) when the numbers alone need the width.
        """
        if not enabled:
            return "", 0.0
        lo_text, hi_text = _range_text(min(data)), _range_text(max(data))
        num_w = tm.width(lo_text, m.detail_px, "bold") + tm.width(hi_text, m.detail_px, "bold")
        letter_w = 2.0 * (tm.width("L", m.label_px, "bold", tm.label_tracking) + m.detail_px * 0.42)
        period = _format_period(self.hours)
        period_w = tm.width(period, m.label_px, "bold", tm.label_tracking) + 12.0

        show_letters = num_w + letter_w + 12.0 <= m.inner_w
        if num_w + 12.0 > m.inner_w:
            return "", 0.0
        show_period = bool(period) and (
            num_w + (letter_w if show_letters else 0.0) + period_w <= m.inner_w
        )

        group = "display: flex; align-items: baseline; gap: 0.42em"
        num = (
            f"font-size: {m.detail_px:.1f}px; font-weight: 700; line-height: 1; "
            "letter-spacing: -0.01em; color: var(--text-secondary); white-space: nowrap"
        )

        # A touch under .t-label's own size so the letters stay clearly
        # subordinate to the numbers they annotate.
        letter_px = min(m.label_px, m.detail_px * 0.82)

        def bound(letter: str, text: str) -> str:
            tag = (
                f'<span class="t-label" style="font-size: {letter_px:.1f}px">{letter}</span>'
                if show_letters
                else ""
            )
            return f'<span style="{group}">{tag}<span style="{num}">{escape(text)}</span></span>'

        period_html = (
            f'<span class="t-label hide-small">{escape(period)}</span>' if show_period else ""
        )
        return (
            '<div class="hide-short hide-narrow">'
            '<div style="display: flex; align-items: baseline; '
            'justify-content: space-between; gap: 6px">'
            f"{bound('L', lo_text)}{period_html}{bound('H', hi_text)}"
            "</div></div>",
            max(m.detail_px, m.label_px),
        )
