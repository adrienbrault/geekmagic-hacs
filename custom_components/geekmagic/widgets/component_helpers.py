"""Convenience component factories for common widget patterns.

These functions return pre-built component trees for common layouts,
reducing boilerplate in widget implementations.

Example:
    def render(self, ctx, hass) -> Component:
        return BarGauge(percent=75, value="75%", label="CPU", color=COLOR_CYAN)
"""

from __future__ import annotations

from ..const import COLOR_DARK_GRAY, COLOR_GRAY, COLOR_WHITE
from .components import (
    Adaptive,
    Arc,
    Bar,
    Column,
    Component,
    Empty,
    Icon,
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
    background: Color = COLOR_DARK_GRAY,
    padding: int = 8,
) -> Component:
    """Bar gauge with header row (icon/label/value) and progress bar below.

    Automatically adapts header to horizontal/vertical based on space.

    Args:
        percent: Progress percentage (0-100)
        value: Display value (e.g., "75%")
        label: Label text
        color: Bar and icon color
        icon: Optional icon name
        background: Bar background color
        padding: Outer padding

    Returns:
        Component tree for bar gauge
    """
    header_children: list[Component | None] = []
    if icon:
        header_children.append(Icon(icon, color=color))
    header_children.extend(
        [
            Text(label.upper(), font="tiny", color=COLOR_GRAY),
            Spacer(),
            Text(value, font="medium", bold=True, color=COLOR_WHITE),
        ]
    )

    return Column(
        gap=4,
        padding=padding,
        children=[
            Adaptive(children=[c for c in header_children if c is not None], gap=4),
            Bar(percent=percent, color=color, background=background),
        ],
    )


def RingGauge(
    percent: float,
    value: str,
    label: str,
    color: Color,
    background: Color = COLOR_DARK_GRAY,
) -> Component:
    """Ring gauge with centered value and label overlay.

    Args:
        percent: Progress percentage (0-100)
        value: Display value (e.g., "75%")
        label: Label text
        color: Ring color
        background: Ring background color

    Returns:
        Component tree for ring gauge
    """
    return Stack(
        children=[
            Ring(percent=percent, color=color, background=background),
            Column(
                align="center",
                justify="center",
                children=[
                    Text(value, font="large", color=COLOR_WHITE),
                    Text(label.upper(), font="tiny", color=COLOR_GRAY),
                ],
            ),
        ],
    )


def ArcGauge(
    percent: float,
    value: str,
    label: str,
    color: Color,
    background: Color = COLOR_DARK_GRAY,
) -> Component:
    """Arc gauge (270 degrees) with centered value and label at top.

    Args:
        percent: Progress percentage (0-100)
        value: Display value
        label: Label text
        color: Arc color
        background: Arc background color

    Returns:
        Component tree for arc gauge
    """
    return Stack(
        children=[
            Column(
                justify="start",
                align="center",
                padding=8,
                children=[
                    Text(label.upper(), font="small", color=COLOR_GRAY),
                ],
            ),
            Arc(percent=percent, color=color, background=background),
            Column(
                align="center",
                justify="center",
                children=[
                    Text(value, font="large", color=COLOR_WHITE),
                ],
            ),
        ],
    )


def IconValue(
    icon: str,
    value: str,
    label: str,
    color: Color,
    value_color: Color = COLOR_WHITE,
    label_color: Color = COLOR_GRAY,
    icon_size: int | None = None,
) -> Component:
    """Icon with value and label - adapts layout based on available space.

    For wide containers: horizontal layout [Icon] [Value + Label]
    For tall containers: vertical layout stacking Icon, Value, Label

    Args:
        icon: Icon name
        value: Display value
        label: Label text
        color: Icon color
        value_color: Value text color
        label_color: Label text color
        icon_size: Optional fixed icon size (default: auto-size but min 16)

    Returns:
        Component tree using Adaptive for responsive layout
    """
    # Use fixed icon size to prevent extreme scaling
    icon_component = Icon(icon, size=icon_size or 24, color=color)
    value_component = Text(value, font="medium", bold=True, color=value_color)
    label_component = Text(label.upper(), font="small", color=label_color)

    # Use Adaptive to auto-switch between layouts
    return Adaptive(
        children=[
            icon_component,
            Column(
                align="center",
                justify="center",
                gap=2,
                children=[value_component, label_component],
            ),
        ],
        gap=6,
        padding=4,
    )


def CenteredValue(
    value: str,
    label: str | None = None,
    value_color: Color = COLOR_WHITE,
    label_color: Color = COLOR_GRAY,
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
        gap=6,
        children=children,
    )


def LabelValue(
    label: str,
    value: str,
    label_color: Color = COLOR_GRAY,
    value_color: Color = COLOR_WHITE,
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
        gap=4,
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
        gap=8,
        align="center",
        justify="space-between",
        children=[
            Row(
                gap=6,
                children=[
                    # Status indicator icon - larger for visibility on small display
                    Icon("check" if is_on else "warning", size=12, color=color),
                    Text(label, font="small", color=COLOR_WHITE),
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
        header_children.append(Icon(icon, color=color))
    header_children.extend(
        [
            Text(label.upper(), font="tiny", color=COLOR_GRAY),
            Spacer(),
            Text(value, font="small", color=COLOR_WHITE),
        ]
    )

    return Column(
        gap=2,
        children=[
            Row(
                gap=4,
                justify="space-between",
                children=[c for c in header_children if c is not None],
            ),
            Row(
                gap=4,
                children=[
                    Bar(percent=percent, color=color, height=6),
                    Text(f"{percent:.0f}%", font="tiny", color=COLOR_WHITE),
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
