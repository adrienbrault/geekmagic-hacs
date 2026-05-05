"""Shared label/value header used by chart and candlestick widgets.

Both widgets render a small header above their plot showing a label
(name of the series) and a current-value readout. The header has to
adapt to width / height: when both pieces fit on one line it's inline;
when they don't fit but there's vertical room, label sits above value;
otherwise the label is dropped and only the value is shown.

Pulling this into a single function keeps the two widgets in lock-step
and cuts ~80 LOC of duplicated branching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .components import THEME_TEXT_SECONDARY, Color, Column, Row, Spacer, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext

HeaderMode = Literal["empty", "inline", "stacked", "value_only", "label_only"]


def header_mode(
    ctx: RenderContext,
    *,
    label: str | None,
    value: str,
    inner_w: int,
    height: int,
) -> HeaderMode:
    """Choose how the label/value header should be laid out.

    Args:
        ctx: render context (for measuring text)
        label: optional label text (e.g. "TEMPERATURE")
        value: optional value text (e.g. "23.5°C")
        inner_w: header width minus padding
        height: full widget height — used to decide if vertical stacking
            would crush the plot below

    Returns one of: "empty", "inline" (label + value side by side),
    "stacked" (label on top of value), "value_only" (label dropped),
    "label_only" (no value).
    """
    has_label = bool(label)
    has_value = bool(value)
    if not has_label and not has_value:
        return "empty"
    if has_label and not has_value:
        return "label_only"
    if not has_label and has_value:
        return "value_only"

    font_label = ctx.get_font("small")
    font_value = ctx.get_font("regular")
    label_w, label_h = ctx.get_text_size(label.upper(), font_label)
    value_w, value_h = ctx.get_text_size(value, font_value)
    inline_fits = label_w + value_w + 4 <= inner_w
    stacked_h_needed = label_h + value_h + 4
    stack_fits = stacked_h_needed <= int(height * 0.32) and height >= 90
    if inline_fits:
        return "inline"
    if stack_fits:
        return "stacked"
    return "value_only"


def header_height_for(
    mode: HeaderMode,
    *,
    label_h: int,
    value_h: int,
    height: int,
) -> int:
    """Header height for the given mode, given measured text heights."""
    if mode == "stacked":
        return label_h + value_h + 8
    if mode in ("inline", "value_only", "label_only"):
        return max(int(height * 0.18), max(label_h, value_h) + 4)
    return int(height * 0.08)


def render_label_value_header(
    ctx: RenderContext,
    x: int,
    y: int,
    width: int,
    header_height: int,
    *,
    mode: HeaderMode,
    label: str | None,
    value: str,
    value_color: Color,
    padding: int,
) -> None:
    """Draw the header at the given mode.

    The caller is responsible for picking ``mode`` (via ``header_mode``)
    and reserving ``header_height`` rows above the plot.
    """
    if mode == "stacked":
        Column(
            children=[
                Text(
                    text=label.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="center",
                    truncate=True,
                ),
                Text(
                    text=value,
                    font="regular",
                    bold=True,
                    color=value_color,
                    align="center",
                    auto_fit=True,
                ),
            ],
            gap=2,
            padding=2,
            align="stretch",
            justify="center",
        ).render(ctx, x, y, width, header_height)
    elif mode == "inline":
        Row(
            children=[
                Text(
                    text=label.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                    truncate=True,
                ),
                Spacer(),
                Text(
                    text=value,
                    font="regular",
                    bold=True,
                    color=value_color,
                    align="end",
                    auto_fit=True,
                ),
            ],
            gap=4,
            padding=padding,
            align="center",
            justify="start",
        ).render(ctx, x, y, width, header_height)
    elif mode == "value_only":
        Row(
            children=[
                Text(
                    text=value,
                    font="regular",
                    bold=True,
                    color=value_color,
                    align="center",
                    auto_fit=True,
                )
            ],
            padding=padding,
            align="center",
            justify="center",
        ).render(ctx, x, y, width, header_height)
    elif mode == "label_only":
        Row(
            children=[
                Text(
                    text=label.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="center",
                    truncate=True,
                )
            ],
            padding=padding,
            align="center",
            justify="center",
        ).render(ctx, x, y, width, header_height)


__all__ = [
    "HeaderMode",
    "header_height_for",
    "header_mode",
    "render_label_value_header",
]
