"""Shared label/value header used by chart and candlestick widgets.

Adapts to width and height: when both pieces fit on one line it's inline;
when they don't fit but there's vertical room, label sits above value;
otherwise the label is dropped and only the value is shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .components import THEME_TEXT_SECONDARY, Color, Column, Component, Row, Spacer, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext

HeaderMode = Literal["empty", "inline", "stacked", "value_only", "label_only"]


@dataclass
class LabelValueHeader(Component):
    """Adaptive label+value header. Picks inline / stacked / value_only / label_only.

    Caller reserves space via ``measure_height(ctx, inner_w, total_height)``
    (which caches the mode), then ``render`` draws into the slice the caller
    reserved.
    """

    label: str | None
    value: str
    value_color: Color
    padding: int = 0
    _cached_mode: HeaderMode | None = None

    def _mode(self, ctx: RenderContext, inner_w: int, total_height: int) -> HeaderMode:
        has_label = bool(self.label)
        has_value = bool(self.value)
        if not has_label and not has_value:
            return "empty"
        if has_label and not has_value:
            return "label_only"
        if not has_label and has_value:
            return "value_only"

        font_label = ctx.get_font("small")
        font_value = ctx.get_font("regular")
        label_w, label_h = ctx.get_text_size(self.label.upper(), font_label)
        value_w, value_h = ctx.get_text_size(self.value, font_value)
        inline_fits = label_w + value_w + 4 <= inner_w
        stack_fits = (label_h + value_h + 4) <= int(total_height * 0.32) and total_height >= 90
        # If label is wider than inner_w, stacked mode would render an
        # ellipsis-only stub — drop to value_only.
        label_fits = label_w <= inner_w
        if inline_fits:
            return "inline"
        if stack_fits and label_fits:
            return "stacked"
        return "value_only"

    def measure_height(self, ctx: RenderContext, inner_w: int, total_height: int) -> int:
        """Pick a mode for the given header width / widget height and return its height.

        Caches the mode so render() draws consistently with what the caller
        reserved.
        """
        mode = self._mode(ctx, inner_w, total_height)
        self._cached_mode = mode
        font_label = ctx.get_font("small")
        font_value = ctx.get_font("regular")
        _, label_h = ctx.get_text_size("Hg", font_label) if self.label else (0, 0)
        _, value_h = ctx.get_text_size("Hg", font_value) if self.value else (0, 0)
        if mode == "stacked":
            return label_h + value_h + 8
        if mode in ("inline", "value_only", "label_only"):
            return max(int(total_height * 0.18), max(label_h, value_h) + 4)
        return int(total_height * 0.08)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, self.measure_height(ctx, max_width - self.padding * 2, max_height))

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        # Use the cached mode from measure_height so render is consistent
        # with what the caller reserved space for.
        mode = self._cached_mode or self._mode(ctx, width - self.padding * 2, height)

        if mode == "empty":
            return

        if mode == "stacked":
            Column(
                children=[
                    Text(
                        text=self.label.upper(),
                        font="small",
                        color=THEME_TEXT_SECONDARY,
                        align="center",
                        truncate=True,
                    ),
                    Text(
                        text=self.value,
                        font="regular",
                        bold=True,
                        color=self.value_color,
                        align="center",
                        auto_fit=True,
                    ),
                ],
                gap=2,
                padding=2,
                align="stretch",
                justify="center",
            ).render(ctx, x, y, width, height)
        elif mode == "inline":
            # header_mode has already verified label_w + value_w fits — no
            # truncate (which can collapse a short label to "…" on sub-pixel
            # rounding).
            Row(
                children=[
                    Text(
                        text=self.label.upper(),
                        font="small",
                        color=THEME_TEXT_SECONDARY,
                        align="start",
                    ),
                    Spacer(),
                    Text(
                        text=self.value,
                        font="regular",
                        bold=True,
                        color=self.value_color,
                        align="end",
                        auto_fit=True,
                    ),
                ],
                gap=4,
                padding=self.padding,
                align="center",
                justify="start",
            ).render(ctx, x, y, width, height)
        elif mode == "value_only":
            Row(
                children=[
                    Text(
                        text=self.value,
                        font="regular",
                        bold=True,
                        color=self.value_color,
                        align="center",
                        auto_fit=True,
                    )
                ],
                padding=self.padding,
                align="center",
                justify="center",
            ).render(ctx, x, y, width, height)
        elif mode == "label_only":
            Row(
                children=[
                    Text(
                        text=self.label.upper(),
                        font="small",
                        color=THEME_TEXT_SECONDARY,
                        align="center",
                        truncate=True,
                    )
                ],
                padding=self.padding,
                align="center",
                justify="center",
            ).render(ctx, x, y, width, height)


__all__ = ["LabelValueHeader"]
