"""Progress widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import css_rgb, mdi_span
from ._card import chip_html
from ._cardfit import fit_caption, fit_caption_sized
from ._cellkit import cell_box, label_px
from ._gauge import (
    bar_html,
    caption_band,
    feature_icon_px,
    hero_font_css,
    track_css,
    value_unit_html,
)
from ._textfit import metrics_for
from .base import Widget, WidgetConfig
from .helpers import format_number

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

# Progress bars are supporting evidence for the percent hero, not the
# subject (that's what the gauge widget is for), so they run slimmer
# than a bar gauge. Legacy thin/normal/thick option, re-tuned.
_BAR_HEIGHT_CSS: dict[str, str] = {
    "thin": "clamp(4px, 5vmin, 9px)",
    "normal": "clamp(6px, 8vmin, 14px)",
    "thick": "clamp(9px, 13vmin, 22px)",
}

# Below this the multi-progress rows would be thinner than their own
# type; extra items are dropped rather than crushed.
_MIN_ROW_PX = 13.0

# A multi-progress row label is the row's identity, so it shrinks to this
# floor instead of vanishing — one row of a stack has far less height to
# spend than a single-value cell.
_ROW_LABEL_MIN_PX = 9.0

# Weights the markup below draws with, named for :mod:`._textfit`.
_CHIP_WEIGHT = "semibold"  # .chip is font-weight 600
_ROW_VALUE_WEIGHT = "bold"  # the percent readout is 700
_ROW_SUPPORT_WEIGHT = "semibold"  # the raw "5000/10000" is 600

# Slack between the percent column and the bar beside it.
_PCT_PAD_PX = 2.0

# Pitch a labelled row needs: the label stacked over the bar/percent line
# with a hair of air between them. The title only displaces rows that
# keep at least this much.
_LABELLED_ROW_PX = 24.0


class ProgressWidget(Widget):
    """Widget that displays progress with label."""

    WIDGET_TYPE: ClassVar[str] = "progress"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Progress",
        "needs_entity": True,
        "entity_domains": None,  # Any entity with numeric state
        "options": [
            {"key": "target", "type": "number", "label": "Target Value", "default": 100},
            {"key": "unit", "type": "text", "label": "Unit"},
            {"key": "show_target", "type": "boolean", "label": "Show Target", "default": True},
            {"key": "icon", "type": "icon", "label": "Icon"},
            {
                "key": "bar_height",
                "type": "select",
                "label": "Bar Height",
                "options": ["thin", "normal", "thick"],
                "default": "normal",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the progress widget."""
        super().__init__(config)
        self.target = config.options.get("target", 100)
        self.unit = config.options.get("unit", "")
        self.show_target = config.options.get("show_target", True)
        self.icon = config.options.get("icon") or None
        self.bar_height_style = config.options.get("bar_height", "normal")

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the widget: caption / percent hero / bar / value chip."""
        entity = state.entity
        value = entity.numeric() if entity is not None else 0.0

        unit = self.unit
        if not unit and entity:
            unit = entity.unit or ""

        label = self.label_for(entity, fallback="Progress")

        target = self.target or 100
        percent = min(100, (value / target) * 100) if target > 0 else 0

        rgb = self.config.color
        color = css_rgb(rgb) if rgb else ctx.accent()
        bar_height = _BAR_HEIGHT_CSS.get(self.bar_height_style, _BAR_HEIGHT_CSS["normal"])

        icon_html = mdi_span(self.icon, "icon i-sm", f"color: {color}") if self.icon else ""
        stack_icon = (
            mdi_span(self.icon, "icon", f"color: {color}; font-size: {feature_icon_px(ctx):.0f}px")
            if self.icon
            else ""
        )
        # The caption band carries the icon too, so ``hide-short`` would
        # cost a footer cell both its name and its tint. ``caption_band``
        # shrinks it to the 10px floor and decides visibility in Python.
        caption = caption_band(ctx, label, icon_html, stack_icon_html=stack_icon)
        # The percent is the hero and stays theme text — the tint lives
        # in the icon and the bar fill (one accent per cell).
        hero_css, unit_css = hero_font_css(f"{percent:.0f}", "%")
        hero = value_unit_html(f"{percent:.0f}", "%", hero_css=hero_css, unit_css=unit_css)
        bar = bar_html(percent, color=color, track=track_css(ctx, rgb), thickness=bar_height)
        chip = self._value_chip(ctx, value, target, unit)
        return f'<div class="cell">{caption}{hero}{bar}{chip}</div>'

    def _value_chip(self, ctx: CellContext, value: float, target: float, unit: str) -> str:
        """Raw progress as a pill: "4.2k of 10k steps".

        Degrades by dropping the least important part first (unit, then
        target) so the chip never spills out of a narrow cell.
        """
        amount = format_number(value)
        variants = [amount]
        if self.show_target:
            variants.insert(0, f"{amount} of {format_number(target)}")
        if unit:
            variants.insert(0, f"{variants[0]} {unit}")

        px = max(10.0, min(0.11 * min(ctx.width, ctx.height), 16.0))
        avail_w, _ = cell_box(ctx)
        # The pill's own 0.85em padding on each side, at the chip size.
        budget = avail_w - 1.9 * px
        # Chip text is mixed-case body copy, not a kit label: no theme
        # uppercases ``.chip``, so measuring it uppercased would reserve
        # width the render never spends.
        metrics = replace(metrics_for(ctx.theme), uppercase=False)
        text = next((v for v in variants if metrics.width(v, px, _CHIP_WEIGHT) <= budget), "")
        if not text:
            text = metrics.truncate(variants[-1], px, budget, _CHIP_WEIGHT, min_chars=3)
        return f'<div class="chips hide-small">{chip_html(text)}</div>'


class MultiProgressWidget(Widget):
    """Widget that displays multiple progress items."""

    WIDGET_TYPE: ClassVar[str] = "multi_progress"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Multi Progress",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "items", "type": "progress_items", "label": "Progress Items"},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the multi-progress widget."""
        super().__init__(config)
        self.items = config.options.get("items", [])
        self.title = config.options.get("title")

    def get_entities(self) -> list[str]:
        """Return list of entity IDs."""
        return [item.get("entity_id") for item in self.items if item.get("entity_id")]

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render progress rows that share the cell height evenly.

        Every row is ``flex: 1`` so the rhythm is even by construction —
        no dead space at the bottom, no rows crushed together at the top.
        """
        avail_w, avail_h = cell_box(ctx)
        lbl_px = label_px(ctx)

        # The title is the first thing to go, but it goes on the height it
        # costs the rows — not on the cell's short side, which stripped
        # the heading off every narrow column whatever its height. It
        # shrinks to the 10px floor before it is dropped.
        title_html = ""
        if self.title:
            title_text, title_px = fit_caption_sized(self.title, ctx, avail_w)
            count = max(1, len(self.items))
            if title_text and (avail_h - title_px * 1.8) / count >= _LABELLED_ROW_PX:
                size = f"font-size: {title_px:.1f}px; " if title_px < lbl_px - 0.25 else ""
                title_html = (
                    f'<div class="t-label" style="{size}flex: none; text-align: left">'
                    f"{escape(title_text)}</div>"
                )
                avail_h -= title_px * 1.8

        rows_fit = max(1, int(avail_h / _MIN_ROW_PX))
        items = self.items[:rows_fit]
        if not items:
            return f'<div class="cell" style="align-items: stretch">{title_html}</div>'

        metrics = replace(metrics_for(ctx.theme), uppercase=False)
        row_h = avail_h / len(items)
        # Row type is list-sized, not hero-sized: several rows share the
        # cell, so it scales with the row rather than the cell.
        text_px = max(9.0, min(20.0, 0.11 * min(ctx.width, ctx.height), row_h * 0.44))
        label_px_row = max(_ROW_LABEL_MIN_PX, min(text_px * 0.78, 0.075 * ctx.width))
        bar_px = max(4.0, min(14.0, row_h * 0.22))
        # One column for every percent so the bars all end on the same
        # pixel — a ragged right edge is what makes stacked bars look
        # accidental.
        pct_w = metrics.width("100%", text_px, _ROW_VALUE_WEIGHT) + _PCT_PAD_PX
        # The raw value column only survives in cells the kit keeps it in.
        value_shown = ctx.width >= 130 and ctx.height >= 130
        # The label names the bar, so it answers to the ROW's pitch, not
        # the cell height: a short cell drops the raw value (above) and
        # keeps a 9px label rather than leaving a row of anonymous bars.
        labels_shown = row_h >= label_px_row + bar_px + 3.0

        text_css = f"font-size: {text_px:.1f}px; font-weight: 700; line-height: 1;"
        # The tracking is the measurer's, not a hand-picked 0.1em: the
        # label is fitted with ``fit_caption`` (which budgets at
        # ``label_tracking``), and measuring one tracking while drawing
        # another is how a fitted string still lands over the edge.
        label_css = (
            f"font-size: {label_px_row:.1f}px; font-weight: 700; line-height: 1; "
            f"letter-spacing: {metrics_for(ctx.theme).label_tracking}em; "
            "color: var(--text-tertiary); text-align: left;"
        )

        rows = [
            self._row_html(
                ctx,
                state,
                item,
                index,
                avail_w=avail_w,
                text_px=text_px,
                label_px_row=label_px_row,
                bar_px=bar_px,
                pct_w=pct_w,
                text_css=text_css,
                label_css=label_css,
                value_shown=value_shown,
                labels_shown=labels_shown,
            )
            for index, item in enumerate(items)
        ]
        # Rows are separated by more than their own label sits from its
        # bar, so each label + bar reads as one unit.
        gap = max(3.0, row_h * 0.14)
        return (
            f'<div class="cell" style="align-items: stretch; gap: {gap:.0f}px">'
            f"{title_html}{''.join(rows)}</div>"
        )

    def _row_html(
        self,
        ctx: CellContext,
        state: WidgetState,
        item: dict[str, Any],
        index: int,
        *,
        avail_w: float,
        text_px: float,
        label_px_row: float,
        bar_px: float,
        pct_w: float,
        text_css: str,
        label_css: str,
        value_shown: bool,
        labels_shown: bool,
    ) -> str:
        """One progress row: label + raw value over bar + percent."""
        entity_id = item.get("entity_id")
        entity = state.get_entity(entity_id) if entity_id else None
        value = entity.numeric() if entity is not None else 0.0

        label = item.get("label", "")
        if entity and not label:
            label = entity.friendly_name
        label = label or entity_id or "Item"

        unit = item.get("unit", "")
        if entity and not unit:
            unit = entity.unit or ""

        target = item.get("target", 100)
        percent = min(100, (value / target) * 100) if target > 0 else 0

        rgb = item.get("color")
        if isinstance(rgb, list):
            rgb = tuple(rgb)
        if rgb is None and ctx.theme is not None:
            # Accent-cycled per row so a stack of bars reads as a set.
            rgb = ctx.theme.get_accent_color(index)
        color = css_rgb(rgb) if rgb else "var(--primary)"

        value_text = f"{value:.0f}/{target:.0f}"
        if unit:
            value_text += f" {unit}"

        icon = item.get("icon")
        # Row icons are sized to the row's own type, not the kit's cell
        # scale, or they tower over the label they belong to.
        icon_html = (
            mdi_span(icon, "icon", f"font-size: {label_px_row * 1.25:.1f}px; color: {color}")
            if icon
            else ""
        )

        label_row = ""
        if labels_shown:
            budget = avail_w - pct_w * 0.2
            if icon_html:
                budget -= label_px_row * 1.7
            if value_shown:
                metrics = replace(metrics_for(ctx.theme), uppercase=False)
                budget -= metrics.width(value_text, label_px_row, _ROW_SUPPORT_WEIGHT) + 6
            # min_keep=0: the label is the row's identity, so a stub of it
            # beats a row of anonymous bars.
            label_text = fit_caption(label, ctx, budget, font_px=label_px_row, min_keep=0)
            # Label and raw value share one size so the line reads as a
            # pair; the percent below is the row's actual readout. The
            # raw value is what a short row gives up — the label names
            # the bar, ``5000/10000`` only restates the percent.
            raw = ""
            if value_shown:
                raw = (
                    f'<span style="font-size: {label_px_row:.1f}px; '
                    "font-weight: 600; line-height: 1; flex: none; "
                    f'color: var(--text-secondary)">{escape(value_text)}</span>'
                )
            # No hide-short wrapper: the row decided for itself that it
            # has the pitch for a label, and the kit's media rule would
            # blank the label and its icon in every cell under 100px.
            label_row = (
                '<div style="display: flex; align-items: center; gap: 5px">'
                f"{icon_html}"
                f'<span style="{label_css} flex: 1 1 0; min-width: 0">'
                f"{escape(label_text)}</span>"
                f"{raw}</div>"
            )

        bar = bar_html(percent, color=color, track=track_css(ctx, rgb), thickness=f"{bar_px:.1f}px")
        bar_row = (
            '<div style="display: flex; align-items: center; gap: 6px">'
            f'<div style="flex: 1 1 0; min-width: 0; display: flex">{bar}</div>'
            f'<span style="{text_css} flex: none; width: {pct_w:.0f}px; text-align: right">'
            f"{percent:.0f}%</span>"
            "</div>"
        )
        return (
            '<div style="flex: 1 1 0; min-height: 0; display: flex; flex-direction: column; '
            f'justify-content: center; gap: {max(2.0, bar_px * 0.35):.0f}px">'
            f"{label_row}{bar_row}</div>"
        )
