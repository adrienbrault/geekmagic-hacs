"""Gauge widget for GeekMagic displays."""

from __future__ import annotations

import math
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import css_rgb, mdi_span, svg_arc, svg_ring
from ._cellkit import cell_box, label_px
from ._fit import (
    CAPTION_MIN_KEEP,
    CAPTION_MIN_PX,
    HERO_UNIT_GAP,
    HERO_UNIT_SCALE,
    fit_caption_sized,
    hero_font_css,
    hero_width_em,
)
from ._gauge import (
    STROKE_UNITS,
    bar_html,
    caption_band,
    feature_icon_px,
    track_css,
    value_unit_html,
)
from .base import Widget, WidgetConfig
from .helpers import calculate_percent

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# Bar thickness — ~7% of the cell's short side, floored so a 3x3 cell
# still reads as a bar and capped so a fullscreen cell keeps a slim,
# Activity-style pill rather than a slab.
_BAR_THICKNESS = "clamp(8px, 11vmin, 18px)"
_VBAR_THICKNESS = "clamp(12px, 17vmin, 30px)"

# A round gauge below this diameter cannot hold a caption inside as well
# as the value, so the caption moves above it (or sheds entirely).
_CAPTION_INSIDE_MIN = 132.0
_ROUND_MIN = 44.0
# ...but a gauge whose only reading is its caption may shrink to a token
# rather than push the word out of the cell.
_ROUND_TINY = 20.0
# Height a caption band really costs: the kit's .t-label is line-height 1,
# plus the breathing room space-evenly puts under it.
_CAPTION_BAND = 1.35
# Past this width/height ratio a centered round gauge strands the cell's
# sides, so the gauge moves left and the text stacks beside it.
_ROW_RATIO = 1.5
# ...and past its transpose the gauge is width-bound, so the value comes
# out of the hole and stands under the circle instead.
_COLUMN_RATIO = 1.6
# Smallest value type a row/column readout is worth keeping.
_VALUE_MIN = 18.0
# Share of a tall cell's height the standalone value may spend.
_COLUMN_VALUE_SHARE = 0.30
# Half the hero's line box, in em — ``_gauge`` draws the in-hole value at
# line-height 0.8, so half of it is what the chord has to clear.
_HALF_LINE_EM = 0.4


class GaugeWidget(Widget):
    """Widget that displays a value as a gauge (bar, ring, or arc)."""

    WIDGET_TYPE: ClassVar[str] = "gauge"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Gauge",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {
                "key": "style",
                "type": "select",
                "label": "Style",
                "options": ["bar", "ring", "arc"],
                "default": "bar",
            },
            {
                # Only meaningful when style="bar". Auto picks based on
                # cell shape (vertical for tall+narrow cells).
                "key": "orientation",
                "type": "select",
                "label": "Bar Orientation",
                "options": ["auto", "compact", "stacked", "vertical"],
                "default": "auto",
            },
            {"key": "min", "type": "number", "label": "Minimum", "default": 0},
            {"key": "max", "type": "number", "label": "Maximum", "default": 100},
            {"key": "unit", "type": "text", "label": "Unit Override"},
            {"key": "show_name", "type": "boolean", "label": "Show Name", "default": True},
            {"key": "show_value", "type": "boolean", "label": "Show Value", "default": True},
            {"key": "show_unit", "type": "boolean", "label": "Show Unit", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon"},
            {"key": "attribute", "type": "text", "label": "Entity Attribute"},
            {"key": "color_thresholds", "type": "thresholds", "label": "Color Thresholds"},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the gauge widget."""
        super().__init__(config)
        self.style = config.options.get("style", "bar")  # bar, ring, arc
        # auto / compact / stacked / vertical — only meaningful for bar style.
        self.orientation = config.options.get("orientation", "auto")
        self.min_value = config.options.get("min", 0)
        self.max_value = config.options.get("max", 100)
        # Normalise icon: ``ha-icon-picker`` writes ``""`` when cleared.
        self.icon = config.options.get("icon") or None
        self.show_name = config.options.get("show_name", True)
        self.show_value = config.options.get("show_value", True)
        self.show_unit = config.options.get("show_unit", True)
        self.unit = config.options.get("unit", "")
        # Attribute to read value from
        self.attribute = config.options.get("attribute")
        # Color thresholds
        self.color_thresholds = config.options.get("color_thresholds", [])

    def _get_threshold_color(self, value: float) -> tuple[int, int, int] | None:
        """Get color based on value and thresholds."""
        if not self.color_thresholds:
            return None

        sorted_thresholds = sorted(self.color_thresholds, key=lambda t: t.get("value", 0))
        matching_color: tuple[int, int, int] | None = None
        for threshold in sorted_thresholds:
            threshold_value = threshold.get("value", 0)
            threshold_color = threshold.get("color")
            if (
                value >= threshold_value
                and isinstance(threshold_color, list | tuple)
                and len(threshold_color) == 3
            ):
                matching_color = (
                    int(threshold_color[0]),
                    int(threshold_color[1]),
                    int(threshold_color[2]),
                )

        return matching_color

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the gauge widget."""
        entity = state.entity

        value = entity.numeric(self.attribute) if entity is not None else 0.0
        display_value = f"{value:.0f}" if entity is not None else "--"

        # Get unit (override > entity unit, suppressed when show_unit is off).
        if not self.show_unit:
            unit = ""
        else:
            unit = self.unit
            if not unit and entity is not None:
                unit = entity.unit or ""

        percent = calculate_percent(value, self.min_value, self.max_value)
        name = self.label_for(entity) if self.show_name else ""

        if not self.show_value:
            display_value = ""
            unit = ""

        threshold_color = self._get_threshold_color(value)
        rgb = threshold_color or self.config.color
        color = css_rgb(rgb) if rgb else ctx.accent()

        if self.style in ("ring", "arc"):
            return self._render_round(
                ctx,
                name,
                display_value,
                unit,
                percent=percent,
                color=color,
                track=track_css(ctx, rgb, svg=True),
            )
        return self._render_bar(
            ctx,
            name,
            display_value,
            unit,
            percent=percent,
            color=color,
            track=track_css(ctx, rgb),
        )

    # ------------------------------------------------------------------
    # Round gauges (ring / arc)
    # ------------------------------------------------------------------

    def _render_round(
        self,
        ctx: CellContext,
        name: str,
        digits: str,
        unit: str,
        *,
        percent: float,
        color: str,
        track: str,
    ) -> str:
        """Ring or arc: the gauge is sized in Python so it always fits.

        A square gauge in a non-square cell is bounded by the *short*
        side; leaving that to CSS (``aspect-ratio`` on a full-height box)
        overflows tall cells. Knowing the diameter also lets the value be
        sized against the hole rather than the cell, so text never
        collides with the stroke.
        """
        avail_w, avail_h = cell_box(ctx)

        if ctx.width > ctx.height * _ROW_RATIO:
            return self._render_round_row(
                ctx, name, digits, unit, percent=percent, color=color, track=track
            )
        if ctx.height > ctx.width * _COLUMN_RATIO:
            return self._render_round_column(
                ctx, name, digits, unit, percent=percent, color=color, track=track
            )

        # A gauge with nothing to read is its caption: it can never be
        # dropped, however tight the cell.
        no_value = not (digits or unit)
        # Big gauges hold the caption inside, under the value (Activity
        # style) — that buys the ring the whole cell. Smaller ones put it
        # above, shrinking it rather than shedding it.
        inside = bool(name) and min(avail_w, avail_h) >= _CAPTION_INSIDE_MIN
        caption, reserve = "", 0.0
        if not inside:
            caption, reserve = self._caption_band(
                ctx, name, avail_w, reserve_h=_ROUND_MIN, avail_h=avail_h, no_value=no_value
            )
        floor = _ROUND_TINY if no_value else _ROUND_MIN
        diameter = max(floor, min(avail_w, avail_h - reserve))

        hole = diameter - 2 * diameter * STROKE_UNITS / 100
        label_html = ""
        value_px = 0.0
        if digits or unit:
            value_px = self._hole_font_px(ctx, diameter, digits, unit)
            if inside:
                value_px *= 0.82
            label_html = self._value_html(digits, unit, value_px, color)
        if inside:
            # Inside the hole the caption is capped by the value it sits
            # under (or by the hole itself when there is no value); the
            # width budget is the hole, not the cell. Secondary tone and
            # a generous share of the value — tertiary at 30% read as
            # missing on a 240px ring. ``min_keep=0`` on an empty ring
            # only relaxes how much identity a stub must carry; one that
            # does not measure inside the hole is dropped regardless.
            cap_px = (
                min(label_px(ctx) * 1.4, value_px * 0.38) if value_px else min(hole * 0.20, 26.0)
            )
            text, caption_px = fit_caption_sized(
                name,
                ctx,
                hole * 0.86,
                max_px=max(CAPTION_MIN_PX, cap_px),
                min_keep=0 if no_value else CAPTION_MIN_KEEP,
            )
            if text:
                gap = f"margin-top: {value_px * 0.16:.1f}px" if value_px else ""
                label_html += (
                    f'<div class="t-label" style="font-size: {caption_px:.1f}px; '
                    f'color: var(--text-secondary); {gap}">'
                    f"{escape(text)}</div>"
                )

        box = self._gauge_box(diameter, percent, color, track, label_html)
        return f'<div class="cell">{caption}{box}</div>'

    def _render_round_row(
        self,
        ctx: CellContext,
        name: str,
        digits: str,
        unit: str,
        *,
        percent: float,
        color: str,
        track: str,
    ) -> str:
        """Wide cell: gauge left, caption + value stacked beside it.

        Centering a circle in a 3:1 cell wastes both sides and shrinks
        the gauge to a token; standing it at the left and setting the
        readout next to it (the Fitness-app row) keeps the gauge at full
        height and the value big.
        """
        avail_w, avail_h = cell_box(ctx)
        gap = avail_w * 0.05
        diameter = max(_ROUND_MIN, min(avail_h, avail_w * 0.46))
        text_w = max(24.0, avail_w - diameter - gap)
        no_value = not (digits or unit)
        # The value renders INSIDE the hole — a ring with an empty hole
        # and its number floating beside it reads as two broken widgets,
        # not one gauge (Activity rings never separate the two).
        inside = ""
        if not no_value:
            inside = self._value_html(
                digits, unit, self._hole_font_px(ctx, diameter, digits, unit), color
            )
        caption, _band = self._caption_band(
            ctx, name, text_w, reserve_h=0.0, avail_h=avail_h, no_value=no_value
        )
        box = self._gauge_box(diameter, percent, color, track, inside)
        return (
            f'<div class="cell row" style="gap: {gap:.0f}px">'
            f"{box}"
            '<div style="flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; '
            'align-items: center; justify-content: center; gap: 6%">'
            f"{caption}</div>"
            "</div>"
        )

    def _render_round_column(
        self,
        ctx: CellContext,
        name: str,
        digits: str,
        unit: str,
        *,
        percent: float,
        color: str,
        track: str,
    ) -> str:
        """Tall cell: caption above, then the gauge at full column width.

        A circle in a 1:3 cell is bound by the *width* — the extra
        height becomes breathing room, and the value stays INSIDE the
        hole where a gauge's reading belongs. The width-bound diameter
        makes the hole as large as this cell can offer, so the in-hole
        value is already the biggest this shape supports.
        """
        avail_w, avail_h = cell_box(ctx)
        no_value = not (digits or unit)
        caption, band = self._caption_band(
            ctx, name, avail_w, reserve_h=_ROUND_MIN, avail_h=avail_h, no_value=no_value
        )
        diameter = max(_ROUND_MIN, min(avail_w, (avail_h - band) * 0.92))
        inside = ""
        if not no_value:
            inside = self._value_html(
                digits, unit, self._hole_font_px(ctx, diameter, digits, unit), color
            )
        box = self._gauge_box(diameter, percent, color, track, inside)
        return f'<div class="cell">{caption}{box}</div>'

    @staticmethod
    def _caption_band(
        ctx: CellContext,
        name: str,
        width_px: float,
        *,
        reserve_h: float,
        avail_h: float,
        no_value: bool,
    ) -> tuple[str, float]:
        """Fitted caption markup plus the height band it costs.

        Visibility is decided here rather than by a pixel cliff or the
        kit's ``hide-short``: the caption shrinks toward its 10px floor
        first, and only a cell that cannot hold ``reserve_h`` (the gauge,
        or the value beside it) *and* a 10px label goes anonymous. A
        gauge with no value to show skips that HEIGHT cliff at any size
        and drops the identity rule with ``min_keep=0`` — an unlabeled
        empty ring says nothing at all. It does not skip the width
        guard: a name too wide to measure inside ``width_px`` even at the
        floor still comes back empty, because Blitz would paint the
        difference over the bezel.
        """
        if not name:
            return "", 0.0
        room = (avail_h - reserve_h) / _CAPTION_BAND
        if not no_value and room < CAPTION_MIN_PX:
            return "", 0.0
        cap_px = label_px(ctx) if no_value else min(label_px(ctx), room)
        text, px = fit_caption_sized(
            name,
            ctx,
            width_px,
            max_px=max(CAPTION_MIN_PX, cap_px),
            min_keep=0 if no_value else CAPTION_MIN_KEEP,
        )
        if not text:
            return "", 0.0
        html = (
            f'<div class="t-label caption-row" style="font-size: {px:.1f}px">{escape(text)}</div>'
        )
        return html, px * _CAPTION_BAND

    @staticmethod
    def _hole_font_px(ctx: CellContext, diameter: float, digits: str, unit: str) -> float:
        """Largest value type that fits inside a round gauge's hole.

        The text's bounding box has to clear the inner circle, so the
        half-diagonal — not the half-width — is what must fit: the value
        is measured (:func:`hero_width_em`) to get the half-width in em,
        and ``_HALF_LINE_EM`` is the half-height the line box draws.
        """
        hole = diameter - 2 * diameter * STROKE_UNITS / 100
        half_w = (
            hero_width_em(digits, ctx, suffix=unit, suffix_scale=HERO_UNIT_SCALE, gap=HERO_UNIT_GAP)
            / 2
        )
        fit = 0.47 * hole / math.sqrt(half_w**2 + _HALF_LINE_EM**2)
        return max(11.0, min(fit * 0.92, hole * 0.62))

    @staticmethod
    def _value_html(digits: str, unit: str, size_px: float, color: str) -> str:
        """Value + unit at an explicit pixel size (gauge-tinted)."""
        return value_unit_html(
            digits,
            unit,
            hero_css=f"{size_px:.1f}px",
            unit_css=f"{size_px * HERO_UNIT_SCALE:.1f}px",
            color=color,
            unit_color=color,
        )

    def _gauge_box(
        self, diameter: float, percent: float, color: str, track: str, label_html: str
    ) -> str:
        """Fixed-size square holding the SVG gauge and its centered label."""
        if self.style == "ring":
            gauge = svg_ring(percent, stroke=color, track=track, stroke_width=STROKE_UNITS)
        else:
            gauge = svg_arc(percent, stroke=color, track=track, stroke_width=STROKE_UNITS)
        overlay = ""
        if label_html:
            # Optical centering: text centered on the geometric middle of
            # a circle reads low, so lift it by a hair.
            overlay = (
                '<div style="position: absolute; inset: 0; display: flex; '
                "flex-direction: column; align-items: center; justify-content: center; "
                f'padding-bottom: {diameter * 0.035:.1f}px">{label_html}</div>'
            )
        return (
            f'<div style="position: relative; flex: none; width: {diameter:.0f}px; '
            f'height: {diameter:.0f}px">{gauge}{overlay}</div>'
        )

    # ------------------------------------------------------------------
    # Bar gauges
    # ------------------------------------------------------------------

    def _render_bar(
        self,
        ctx: CellContext,
        name: str,
        digits: str,
        unit: str,
        *,
        percent: float,
        color: str,
        track: str,
    ) -> str:
        """Bar gauge — horizontal by default, vertical for tall narrow cells."""
        vertical = self.orientation == "vertical" or (
            self.orientation == "auto" and ctx.height > ctx.width * 1.6
        )
        icon_html = mdi_span(self.icon, "icon i-sm", f"color: {color}") if self.icon else ""
        # Tall-enough cells promote the icon to its own band above the
        # caption (the entity card's feature pattern); the inline chip is
        # the short-cell fallback.
        stack_icon = (
            mdi_span(self.icon, "icon", f"color: {color}; font-size: {feature_icon_px(ctx):.0f}px")
            if self.icon
            else ""
        )

        if not vertical:
            caption = caption_band(ctx, name, icon_html, stack_icon_html=stack_icon)
            bar = bar_html(percent, color=color, track=track, thickness=_BAR_THICKNESS)
            return f'<div class="cell">{caption}{self._hero(ctx, digits, unit, color)}{bar}</div>'

        vbar = bar_html(percent, color=color, track=track, thickness=_VBAR_THICKNESS, vertical=True)
        if ctx.width > ctx.height * 1.15:
            # Wide cell, vertical bar: stand the bar up the left edge and
            # set the label + value beside it instead of stranding a stub
            # of a bar in the middle.
            caption = caption_band(ctx, name, icon_html, width_ratio=0.6)
            hero = self._hero(ctx, digits, unit, color, cap_vw=24.0, cap_vmin=44.0)
            return (
                '<div class="cell row" style="gap: 6%">'
                f'<div style="align-self: stretch; display: flex; flex: none">{vbar}</div>'
                '<div style="flex: 1 1 0; min-width: 0; display: flex; '
                "flex-direction: column; align-items: center; justify-content: center; "
                f'gap: 4%">{caption}{hero}</div>'
                "</div>"
            )

        # Tall cell: caption above, bar taking every spare pixel, value
        # under it. The value stays deliberately smaller than a
        # horizontal bar's hero so the column of colour stays the subject.
        # The bar's ``flex: 1`` leaves space-evenly nothing to distribute,
        # so the breathing room between the bands is explicit here. The
        # icon stays INLINE here — the vertical bar wants the height.
        caption = caption_band(ctx, name, icon_html)
        hero = self._hero(ctx, digits, unit, color, cap_vw=27.0, cap_vmin=30.0)
        gap = max(4.0, min(14.0, ctx.height * 0.045))
        return (
            f'<div class="cell" style="gap: {gap:.0f}px">'
            f"{caption}"
            '<div style="flex: 1 1 auto; min-height: 0; width: 100%; display: flex; '
            f'justify-content: center">{vbar}</div>'
            f"{hero}"
            "</div>"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hero(
        ctx: CellContext,
        digits: str,
        unit: str,
        color: str,
        *,
        cap_vw: float = 38.0,
        cap_vmin: float = 48.0,
    ) -> str:
        """Fluid hero value. Gauge-family exception: it wears the fill's
        tint so value and bar read as one object (Apple Activity)."""
        hero_css, unit_css = hero_font_css(
            digits, ctx, suffix=unit, cap_vw=cap_vw, cap_vmin=cap_vmin
        )
        return value_unit_html(
            digits, unit, hero_css=hero_css, unit_css=unit_css, color=color, unit_color=color
        )
