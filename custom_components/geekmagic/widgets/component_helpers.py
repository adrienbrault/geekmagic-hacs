"""Convenience component factories for common widget patterns.

These functions return pre-built component trees for common layouts,
reducing boilerplate in widget implementations.

Example:
    def render(self, ctx, hass) -> Component:
        return BarGauge(percent=75, value="75%", label="CPU", color=COLOR_CYAN)
"""

from __future__ import annotations

from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Adaptive,
    Arc,
    Bar,
    Column,
    Component,
    Empty,
    Icon,
    IconValueDisplay,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
)

Color = tuple[int, int, int]


def BarGauge(
    percent: float,
    value: str,
    label: str,
    color: Color,
    icon: str | None = None,
    background: Color | None = None,  # None = theme tinted track
    padding: int = 6,
) -> Component:
    """Bar gauge: caps-tracked label/icon row + thin tinted progress bar.

    The header row puts the label on the left and the value on the right
    (semibold, primary text color); the bar fills the row beneath.
    """
    header_children: list[Component | None] = []
    if icon:
        header_children.append(Icon(icon, size=16, color=color))
    # Use legacy fixed sizes (tiny/medium) so density doesn't blow up in
    # large cells; auto_fit lets them shrink in narrow cells.
    header_children.extend(
        [
            Text(
                label.upper(),
                font="tiny",
                color=THEME_TEXT_SECONDARY,
                truncate=True,
                auto_fit=True,
            ),
            Spacer(),
            Text(
                value,
                font="medium",
                bold=True,
                color=THEME_TEXT_PRIMARY,
                auto_fit=True,
            ),
        ]
    )

    return Column(
        gap=5,
        padding=padding,
        justify="center",
        children=[
            Adaptive(children=[c for c in header_children if c is not None], gap=6),
            Bar(percent=percent, color=color, background=background),
        ],
    )


def RingGauge(
    percent: float,
    value: str,
    label: str,
    color: Color,
    background: Color | None = None,  # None = theme tinted track
) -> Component:
    """Ring gauge with centered bold value and caption label.

    watchOS Activity-ring style: tinted track, thick ring, bold value
    in the ring's tint sized to fit inside the ring's inner space.
    """
    return Stack(
        children=[
            Ring(percent=percent, color=color, background=background),
            Column(
                align="center",
                justify="center",
                gap=2,
                children=[
                    # font="large" matches old proportions (≈24px) so the
                    # value comfortably fits inside the ring's inner clear
                    # space; bold + tint give the watchOS look.
                    Text(value, font="large", bold=True, color=color),
                    Text(label.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                ],
            ),
        ],
    )


def ArcGauge(
    percent: float,
    value: str,
    label: str,
    color: Color,
    background: Color | None = None,  # None = theme tinted track
) -> Component:
    """Arc gauge (270 degrees): caption label on top, bold tinted value below."""
    return Stack(
        children=[
            Column(
                justify="start",
                align="center",
                padding=8,  # Extra top padding so the label isn't clipped
                children=[
                    Text(label.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                ],
            ),
            Column(
                justify="center",
                align="center",
                padding=12,
                children=[
                    Arc(percent=percent, color=color, background=background),
                ],
            ),
            Column(
                align="center",
                justify="center",
                children=[
                    Text(value, font="medium", bold=True, color=color),
                ],
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


def LabelValue(
    label: str,
    value: str,
    label_color: Color = THEME_TEXT_SECONDARY,
    value_color: Color = THEME_TEXT_PRIMARY,
    font: str = "small",
) -> Component:
    """Horizontal label + value pair that adapts to available space.

    Args:
        label: Label text
        value: Value text
        label_color: Label text color
        value_color: Value text color
        font: Font size for both

    Returns:
        Component tree
    """
    return Adaptive(
        children=[
            Text(label, font=font, color=label_color, align="start"),
            Spacer(),
            Text(value, font=font, color=value_color, align="end"),
        ],
        gap=6,
    )


def StatusIndicator(
    label: str,
    is_on: bool,
    on_color: Color,
    off_color: Color,
    on_text: str = "ON",
    off_text: str = "OFF",
) -> Component:
    """Status indicator with colored dot and status text.

    Args:
        label: Item label
        is_on: Whether status is on/active
        on_color: Color when on
        off_color: Color when off
        on_text: Text to show when on
        off_text: Text to show when off

    Returns:
        Component tree
    """
    color = on_color if is_on else off_color
    status_text = on_text if is_on else off_text

    return Row(
        gap=10,
        align="center",
        justify="space-between",
        children=[
            Row(
                gap=8,
                children=[
                    # Status indicator icon - 14px for visibility on small display
                    Icon("check" if is_on else "warning", size=14, color=color),
                    Text(label, font="small", color=THEME_TEXT_PRIMARY),
                ],
            ),
            Text(status_text, font="small", color=color),
        ],
    )


def ProgressRow(
    label: str,
    value: str,
    percent: float,
    color: Color,
    icon: str | None = None,
) -> Component:
    """Single progress row with label, value, bar, and percentage.

    Args:
        label: Label text
        value: Value/target text (e.g., "680/800")
        percent: Progress percentage
        color: Progress bar color
        icon: Optional icon

    Returns:
        Component tree
    """
    header_children: list[Component | None] = []
    if icon:
        # Fixed 14px icon for progress row header
        header_children.append(Icon(icon, size=14, color=color))
    header_children.extend(
        [
            Text(label.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
            Spacer(),
            Text(value, font="small", color=THEME_TEXT_PRIMARY),
        ]
    )

    return Column(
        gap=4,
        children=[
            Row(
                gap=6,
                justify="space-between",
                children=[c for c in header_children if c is not None],
            ),
            Row(
                gap=6,
                children=[
                    Bar(percent=percent, color=color, height=6),
                    Text(f"{percent:.0f}%", font="tiny", color=THEME_TEXT_PRIMARY),
                ],
            ),
        ],
    )


def Conditional(
    condition: bool,
    if_true: Component,
    if_false: Component | None = None,
) -> Component:
    """Conditional component rendering.

    Args:
        condition: Condition to evaluate
        if_true: Component to render if condition is True
        if_false: Component to render if condition is False (default: Empty)

    Returns:
        The appropriate component based on condition
    """
    if condition:
        return if_true
    return if_false or Empty()


__all__ = [
    "ArcGauge",
    "BarGauge",
    "CenteredValue",
    "Conditional",
    "IconValue",
    "LabelValue",
    "ProgressRow",
    "RingGauge",
    "StatusIndicator",
]
