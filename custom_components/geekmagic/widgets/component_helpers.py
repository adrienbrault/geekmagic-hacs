"""Convenience component factories for common widget patterns.

These functions return pre-built component trees for common layouts,
reducing boilerplate in widget implementations.

Example:
    def render(self, ctx, hass) -> Component:
        # Pass a theme role sentinel — resolves to the active theme's
        # primary colour at render time (no hardcoded RGB).
        return BarGauge(percent=75, value="75%", label="CPU", color=THEME_PRIMARY)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Adaptive,
    Arc,
    Bar,
    Column,
    Component,
    Flex,
    Icon,
    IconValueDisplay,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
    VerticalBar,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext

Color = tuple[int, int, int]

BarGaugeMode = Literal["auto", "compact", "stacked", "vertical"]


def _pick_bar_mode(width: int, height: int) -> BarGaugeMode:
    """Auto-pick a BarGauge layout based on cell shape.

    - vertical: genuinely tall+narrow cells (height > 1.8x width). The
      threshold is intentionally generous (1.8 not 1.4) — at lower
      ratios the vertical bar reads as a chunky block rather than a
      thermometer, and a horizontal compact bar fills the cell better.
    - stacked:  square-ish + at least ~100x100 → label/value/bar hero layout
    - compact:  everything else (wide+short, tiny grids)
    """
    if height > width * 1.8:
        return "vertical"
    aspect = width / max(height, 1)
    if 0.7 <= aspect <= 1.5 and min(width, height) >= 100:
        return "stacked"
    return "compact"


@dataclass
class BarGauge(Component):
    """Adaptive bar gauge — picks `compact`, `stacked`, or `vertical` based
    on cell shape, or honors an explicit mode override.

    - `compact` (default for landscape cells): caps label + value pinned
      to the top of the cell, thicker tinted bar pinned to the bottom
      via `justify="space-evenly"`. Fills the cell height.
    - `stacked` (auto on cells ≥100x100, square-ish): caps label centred
      top, big bold tinted value centred middle (auto-fit), thick bar
      bottom — Apple-Watch Modular-Large bar pattern.
    - `vertical` (auto on tall+narrow cells): a `VerticalBar` on the
      right ~35% of the cell, value+label stacked on the left.
    """

    percent: float
    value: str
    label: str
    color: Color
    icon: str | None = None
    background: Color | None = None  # None = theme tinted track
    padding: int = 6
    mode: BarGaugeMode = "auto"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        chosen = self.mode if self.mode != "auto" else _pick_bar_mode(width, height)
        if chosen == "stacked":
            tree = self._build_stacked()
        elif chosen == "vertical":
            tree = self._build_vertical(width)
        else:
            tree = self._build_compact()
        tree.render(ctx, x, y, width, height)

    # ---- mode builders ----

    def _build_compact(self) -> Component:
        """Header row pinned to top (icon + caps label + value); thicker
        tinted bar pinned to bottom. Uses justify=space-between so the
        cell fills regardless of natural content height.
        """
        header_children: list[Component | None] = []
        if self.icon:
            header_children.append(Icon(self.icon, size=16, color=self.color))
        header_children.extend(
            [
                Text(
                    self.label.upper(),
                    font="tiny",
                    color=THEME_TEXT_SECONDARY,
                    truncate=True,
                    auto_fit=True,
                ),
                Spacer(),
                Text(
                    self.value,
                    font="medium",
                    bold=True,
                    color=THEME_TEXT_PRIMARY,
                    auto_fit=True,
                ),
            ]
        )

        return Column(
            gap=5,
            padding=self.padding,
            align="stretch",
            justify="space-evenly",
            children=[
                Adaptive(children=[c for c in header_children if c is not None], gap=6),
                Bar(percent=self.percent, color=self.color, background=self.background),
            ],
        )

    def _build_stacked(self) -> Component:
        """Modular-Large pattern: caps label top, hero value middle (bold,
        tinted, auto-fit), thick bar at the bottom — three clear bands.
        """
        # Bar component natural height is ~15% of available space — that
        # under-represents what feels right in a hero cell. Pass an
        # explicit height so the bar reads as substantial.
        bar = Bar(
            percent=self.percent,
            color=self.color,
            background=self.background,
        )
        return Column(
            gap=4,
            padding=self.padding,
            align="stretch",
            justify="space-evenly",
            children=[
                Row(
                    children=[
                        Text(
                            self.label.upper(),
                            font="tiny",
                            color=THEME_TEXT_SECONDARY,
                            truncate=True,
                        )
                    ],
                    justify="center",
                    align="center",
                ),
                Row(
                    children=[
                        Text(
                            self.value,
                            font="huge",
                            bold=True,
                            color=self.color,
                            auto_fit=True,
                        )
                    ],
                    justify="center",
                    align="center",
                ),
                bar,
            ],
        )

    def _build_vertical(self, width: int) -> Component:
        """Tall+narrow cells: thermometer / level-meter look.

        Two flavours, picked by cell width:
          - very narrow (<90 px, e.g. 3-column layout): stack everything
            vertically — value on top, caps label below, bar fills the
            rest at full cell width. Side-by-side compresses the bar
            into a sliver and crowds the text.
          - wider verticals: value+label column on the left, vertical
            bar on the right.
        """
        if width < 90:
            return Column(
                gap=4,
                padding=self.padding,
                align="stretch",
                justify="start",
                children=[
                    Row(
                        children=[
                            Text(
                                self.value,
                                font="medium",
                                bold=True,
                                color=self.color,
                                auto_fit=True,
                            )
                        ],
                        justify="center",
                        align="center",
                    ),
                    Row(
                        children=[
                            Text(
                                self.label.upper(),
                                font="tiny",
                                color=THEME_TEXT_SECONDARY,
                                truncate=True,
                                auto_fit=True,
                            )
                        ],
                        justify="center",
                        align="center",
                    ),
                    # Flex makes the bar swallow the remaining vertical
                    # space; with align="stretch" above it gets the full
                    # cell width, so the gauge is substantial.
                    Flex(
                        VerticalBar(
                            percent=self.percent,
                            color=self.color,
                            background=self.background,
                            # Allow the bar to use almost the entire cell
                            # width — it's the dominant visual element.
                            width=max(20, int(width * 0.6)),
                        )
                    ),
                ],
            )

        # Wider verticals: side-by-side text column + bar.
        left = Column(
            gap=2,
            padding=2,
            align="center",
            justify="center",
            children=[
                Text(
                    self.value,
                    font="medium",
                    bold=True,
                    color=self.color,
                    auto_fit=True,
                ),
                Text(
                    self.label.upper(),
                    font="tiny",
                    color=THEME_TEXT_SECONDARY,
                    truncate=True,
                    auto_fit=True,
                ),
            ],
        )
        return Row(
            gap=8,
            padding=self.padding,
            align="stretch",
            justify="start",
            children=[
                left,
                VerticalBar(
                    percent=self.percent,
                    color=self.color,
                    background=self.background,
                ),
            ],
        )


def _ring_label_outside_threshold(width: int, height: int) -> bool:
    """Return True when the cell is roomy enough to show the label
    *outside* the ring (its own band on top), not inside it.

    Putting the label outside avoids the in-ring overlap that happens
    when the ring fills the cell. The 100-px threshold covers 2x2 grid
    cells (~111x111 with default padding), which is exactly where the
    overlap was visible in the neon theme sample.
    """
    return width >= 100 and height >= 100


@dataclass
class RingGauge(Component):
    """Adaptive ring gauge.

    - In cells >= 120x120: caps label gets its own row above the ring
      (clear of the ring stroke); ring fills the rest, value bold-tinted
      in the centre. Solves the label-overlapping-the-ring issue.
    - In smaller cells: label stays inside the ring with the value
      (more compact, label is a tiny caption below the value).
    """

    percent: float
    value: str
    label: str
    color: Color
    background: Color | None = None  # None = theme tinted track

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if _ring_label_outside_threshold(width, height):
            tree = self._build_label_outside()
        else:
            tree = self._build_label_inside()
        tree.render(ctx, x, y, width, height)

    def _build_label_inside(self) -> Component:
        """Compact: ring fills the cell, value+label centred inside."""
        return Stack(
            children=[
                Ring(percent=self.percent, color=self.color, background=self.background),
                Column(
                    align="center",
                    justify="center",
                    gap=2,
                    children=[
                        # font="large" (~24px) comfortably fits inside the
                        # ring's inner clear space; bold + tint give the
                        # watchOS look.
                        Text(self.value, font="large", bold=True, color=self.color),
                        Text(
                            self.label.upper(),
                            font="tiny",
                            color=THEME_TEXT_SECONDARY,
                            truncate=True,
                            auto_fit=True,
                        ),
                    ],
                ),
            ],
        )

    def _build_label_outside(self) -> Component:
        """Roomy: label gets its own row above the ring; value inside ring."""
        return Column(
            gap=2,
            padding=4,
            align="stretch",
            justify="start",
            children=[
                Row(
                    children=[
                        Text(
                            self.label.upper(),
                            font="tiny",
                            color=THEME_TEXT_SECONDARY,
                            truncate=True,
                        )
                    ],
                    justify="center",
                    align="center",
                ),
                # The remaining space is taken by the Stack via Flex so the
                # ring grows to fill what's left after the label band.
                Flex(
                    Stack(
                        children=[
                            Ring(
                                percent=self.percent,
                                color=self.color,
                                background=self.background,
                            ),
                            Column(
                                align="center",
                                justify="center",
                                children=[
                                    Text(
                                        self.value,
                                        font="xlarge",
                                        bold=True,
                                        color=self.color,
                                        auto_fit=True,
                                    ),
                                ],
                            ),
                        ],
                    )
                ),
            ],
        )


@dataclass
class ArcGauge(Component):
    """Adaptive arc gauge (270 degrees).

    - Cells >= 120x120: caps label above arc, arc in middle, value below.
    - Smaller cells: tight stack with label in top padding, value below.
    """

    percent: float
    value: str
    label: str
    color: Color
    background: Color | None = None  # None = theme tinted track

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if _ring_label_outside_threshold(width, height):
            tree = self._build_label_outside()
        else:
            tree = self._build_compact()
        tree.render(ctx, x, y, width, height)

    def _build_compact(self) -> Component:
        """Compact ArcGauge: caps label at top, arc with value inside below.

        Column-based (not Stack) so the label band can't overlap the arc stroke.
        """
        return Column(
            gap=2,
            padding=4,
            align="stretch",
            justify="start",
            children=[
                # Label band (caption tier).
                Row(
                    children=[
                        Text(self.label.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                    ],
                    justify="center",
                    align="center",
                ),
                # Arc + value in the remaining space. Flex gives this
                # Stack the leftover height; the arc auto-sizes to fit
                # and the value stays centred inside.
                Flex(
                    Stack(
                        children=[
                            Arc(
                                percent=self.percent,
                                color=self.color,
                                background=self.background,
                            ),
                            Column(
                                align="center",
                                justify="center",
                                children=[
                                    Text(
                                        self.value,
                                        font="medium",
                                        bold=True,
                                        color=self.color,
                                    ),
                                ],
                            ),
                        ],
                    )
                ),
            ],
        )

    def _build_label_outside(self) -> Component:
        return Column(
            gap=2,
            padding=4,
            align="stretch",
            justify="start",
            children=[
                Row(
                    children=[
                        Text(
                            self.label.upper(),
                            font="tiny",
                            color=THEME_TEXT_SECONDARY,
                            truncate=True,
                        )
                    ],
                    justify="center",
                    align="center",
                ),
                Flex(
                    Stack(
                        children=[
                            Column(
                                align="center",
                                justify="center",
                                padding=8,
                                children=[
                                    Arc(
                                        percent=self.percent,
                                        color=self.color,
                                        background=self.background,
                                    ),
                                ],
                            ),
                            Column(
                                align="center",
                                justify="center",
                                children=[
                                    Text(
                                        self.value,
                                        font="large",
                                        bold=True,
                                        color=self.color,
                                    ),
                                ],
                            ),
                        ],
                    )
                ),
            ],
        )


def IconValue(
    icon: str,
    value: str,
    label: str,
    color: Color,
    value_color: Color = THEME_TEXT_PRIMARY,
    label_color: Color = THEME_TEXT_SECONDARY,
    icon_size: int | None = None,
) -> Component:
    """Icon with value and label - uses IconValueDisplay for proper sizing.

    Args:
        icon: Icon name
        value: Display value
        label: Label text
        color: Icon color
        value_color: Value text color
        label_color: Label text color
        icon_size: Optional fixed icon size

    Returns:
        IconValueDisplay component
    """
    return IconValueDisplay(
        icon=icon,
        value=value,
        label=label,
        icon_color=color,
        value_color=value_color,
        label_color=label_color,
        icon_size=icon_size,
    )


def CenteredValue(
    value: str,
    label: str | None = None,
    value_color: Color = THEME_TEXT_PRIMARY,
    label_color: Color = THEME_TEXT_SECONDARY,
    value_font: str = "large",
    label_font: str = "small",
) -> Component:
    """Centered value with optional label below.

    Args:
        value: Display value
        label: Optional label text
        value_color: Value text color
        label_color: Label text color
        value_font: Font size for value
        label_font: Font size for label

    Returns:
        Component tree
    """
    children: list[Component] = [
        Text(value, font=value_font, color=value_color),
    ]
    if label:
        children.append(Text(label.upper(), font=label_font, color=label_color))

    return Column(
        align="center",
        justify="center",
        gap=8,
        children=children,
    )


__all__ = [
    "ArcGauge",
    "BarGauge",
    "CenteredValue",
    "IconValue",
    "RingGauge",
]
