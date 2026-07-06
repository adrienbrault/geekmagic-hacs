"""Progress widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from .base import SIZE_ADJUST_OPTION, Widget, WidgetConfig
from .components import (
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Bar,
    Color,
    Column,
    Component,
    Flex,
    Icon,
    Row,
    Spacer,
    Text,
)
from .data_card import Chip, DataCard
from .helpers import format_number

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


@dataclass
class ProgressDisplay(Component):
    """Progress bar display — caption + percent hero + value/target chip + bar.

    Maps onto ``DataCard``: the bar lives in the indicator slot, the
    raw value/target reads as a supporting chip, and the percent
    becomes the hero. Bar height honours the legacy
    ``thin``/``normal``/``thick`` style options.
    """

    value: float
    target: float = 100
    label: str = "Progress"
    unit: str = ""
    color: Color = THEME_PRIMARY
    icon: str | None = None
    show_target: bool = True
    bar_height_style: str = "normal"

    BAR_HEIGHT_MULTIPLIERS: ClassVar[dict[str, float]] = {
        "thin": 0.10,
        "normal": 0.17,
        "thick": 0.25,
    }

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        target = self.target or 100
        percent = min(100, (self.value / target) * 100) if target > 0 else 0
        bar_h_ratio = self.BAR_HEIGHT_MULTIPLIERS.get(self.bar_height_style, 0.17)
        bar_height = max(4, int(height * bar_h_ratio))

        # Supporting strip: "{value}/{target} {unit}" — the raw value
        # reads as a small caption beside the bar. ``format_number``
        # abbreviates large values (e.g. 1.5k).
        value_str = format_number(self.value)
        if self.show_target:
            value_str = f"{value_str}/{format_number(target)}"
        if self.unit:
            value_str = f"{value_str} {self.unit}"

        DataCard(
            caption=self.label,
            icon=self.icon,
            icon_color=self.color,
            icon_role="feature",
            hero=f"{percent:.0f}%",
            supporting=[Chip(value_str)] if value_str else [],
            indicator=Bar(percent=percent, color=self.color, height=bar_height),
        ).render(ctx, x, y, width, height)


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
            SIZE_ADJUST_OPTION,
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the progress widget."""
        super().__init__(config)
        self.target = config.options.get("target", 100)
        self.unit = config.options.get("unit", "")
        self.show_target = config.options.get("show_target", True)
        self.icon = config.options.get("icon")
        self.bar_height_style = config.options.get("bar_height", "normal")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the progress widget."""
        entity = state.entity
        value = entity.numeric() if entity is not None else 0.0

        unit = self.unit
        if not unit and entity:
            unit = entity.unit or ""

        label = self.label_for(entity, fallback="Progress")

        return ProgressDisplay(
            value=value,
            target=self.target,
            label=label,
            unit=unit,
            color=self.config.color or ctx.theme.get_accent_color(self.config.slot),
            icon=self.icon,
            show_target=self.show_target,
            bar_height_style=self.bar_height_style,
        )


@dataclass
class MultiProgressDisplay(Component):
    """Multi-progress list display component."""

    items: list[dict] = field(default_factory=list)
    title: str | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render multi-progress list."""
        padding = int(width * 0.05)

        # Calculate sizes
        bar_height = max(4, int(height * 0.06))
        # Bumped from 0.09 -> 0.13: at 240 px the icon is 31 px (was
        # 21), big enough to actually read at a glance instead of
        # registering as a tiny dot beside the label.
        icon_size = max(12, int(height * 0.13))

        # Build component tree
        children = []

        # Add title if present
        if self.title:
            children.append(
                Row(
                    children=[
                        Text(
                            text=self.title.upper(),
                            font="small",
                            color=THEME_TEXT_SECONDARY,
                            align="start",
                        )
                    ],
                    padding=padding,
                )
            )

        # Build each progress item row
        for i, item in enumerate(self.items):
            label = item.get("label", "Item")
            value = item.get("value", 0)
            target = item.get("target", 100)
            color = item.get("color", ctx.theme.get_accent_color(i))
            icon = item.get("icon")
            unit = item.get("unit", "")

            percent = min(100, (value / target) * 100) if target > 0 else 0
            value_text = f"{value:.0f}/{target:.0f}"
            if unit:
                value_text += f" {unit}"

            # Top row: Icon + Label + Spacer + Value
            top_row_children = []
            if icon:
                top_row_children.append(Icon(name=icon, size=icon_size, color=color))
            top_row_children.extend(
                [
                    Text(
                        text=label.upper(),
                        font="small",
                        color=THEME_TEXT_SECONDARY,
                        align="start",
                    ),
                    Spacer(),
                    Text(text=value_text, font="small", color=THEME_TEXT_PRIMARY, align="end"),
                ]
            )

            # Bottom row: Bar + Percent
            bottom_row_children: list[Component] = [
                Flex(Bar(percent=percent, color=color, height=bar_height)),
                Text(text=f"{percent:.0f}%", font="small", color=THEME_TEXT_PRIMARY, align="end"),
            ]

            # Combine label-row and bar-row into a column for this item.
            # Use a tight intra-item gap so the bar reads as part of the
            # same activity as its label/value, not a separate band.
            item_column = Column(
                children=[
                    Row(children=top_row_children, gap=4, align="center", padding=padding),
                    Row(children=bottom_row_children, gap=8, align="center", padding=padding),
                ],
                gap=2,
                justify="center",
                align="stretch",  # Stretch rows to full width for Spacer to work
            )
            children.append(item_column)

        # Render the entire column. Inter-item gap is larger than the
        # intra-item gap so each (label / bar) pair groups visually
        # while distinct activities stay separated.
        Column(
            children=children,
            gap=max(8, int(height * 0.05)),
            justify="start",
            align="stretch",  # Stretch to full width
            padding=0,
        ).render(ctx, x, y, width, height)


class MultiProgressWidget(Widget):
    """Widget that displays multiple progress items."""

    WIDGET_TYPE: ClassVar[str] = "multi_progress"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Multi Progress",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "items", "type": "progress_items", "label": "Progress Items"},
            SIZE_ADJUST_OPTION,
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

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the multi-progress widget."""
        display_items = []
        for i, item in enumerate(self.items):
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

            display_items.append(
                {
                    "label": label,
                    "value": value,
                    "target": item.get("target", 100),
                    "color": item.get("color", ctx.theme.get_accent_color(i)),
                    "icon": item.get("icon"),
                    "unit": unit,
                }
            )

        return MultiProgressDisplay(items=display_items, title=self.title)
