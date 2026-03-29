"""Progress widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import COLOR_CYAN, COLOR_DARK_GRAY
from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Bar,
    Color,
    Column,
    Component,
    Icon,
    Row,
    Spacer,
    Text,
)
from .helpers import format_number

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState


def _extract_numeric(entity: EntityState | None) -> float:
    """Extract numeric value from entity state."""
    if entity is None:
        return 0.0
    try:
        return float(entity.state)
    except (ValueError, TypeError):
        return 0.0


@dataclass
class ProgressDisplay(Component):
    """Progress bar display component."""

    value: float
    target: float = 100
    label: str = "Progress"
    unit: str = ""
    color: Color = COLOR_CYAN
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
        """Render progress display."""
        padding = int(width * 0.05)
        bar_height_mult = self.BAR_HEIGHT_MULTIPLIERS.get(self.bar_height_style, 0.17)
        bar_height = max(4, int(height * bar_height_mult))

        # Format numbers with abbreviations for large values
        display_value = format_number(self.value)
        target = self.target or 100
        display_target = format_number(target)
        percent = min(100, (self.value / target) * 100) if target > 0 else 0

        value_text = f"{display_value}/{display_target}" if self.show_target else display_value
        if self.unit:
            value_text += f" {self.unit}"
        label_text = self.label.upper()

        # Adaptive layout based on size using standard size categories
        # Compact: MICRO cells in dense grids
        # Standard: TINY/SMALL cells, horizontal layout
        # Expanded: MEDIUM/LARGE cells, vertical layout with icon/label separate from value
        size = get_size_category(height)
        is_compact = size == SizeCategory.MICRO
        is_expanded = size in (SizeCategory.MEDIUM, SizeCategory.LARGE)

        if is_expanded:
            # Expanded: icon + label on top, value below, bar + percent at bottom
            icon_size = max(16, int(height * 0.18))

            # Row 1: Icon + Label (centered)
            header_children: list[Component] = []
            if self.icon:
                header_children.append(Icon(name=self.icon, size=icon_size, color=self.color))
            header_children.append(
                Text(text=label_text, font="small", color=THEME_TEXT_SECONDARY, align="center")
            )

            # Row 2: Value (centered, larger)
            value_row = Row(
                children=[
                    Text(text=value_text, font="large", color=THEME_TEXT_PRIMARY, align="center")
                ],
                justify="center",
                padding=padding,
            )

            # Row 3: Bar + Percent
            bar_row = Row(
                children=[
                    Bar(
                        percent=percent,
                        color=self.color,
                        background=COLOR_DARK_GRAY,
                        height=bar_height,
                    ),
                    Text(
                        text=f"{percent:.0f}%", font="small", color=THEME_TEXT_PRIMARY, align="end"
                    ),
                ],
                gap=8,
                align="center",
                padding=padding,
            )

            Column(
                children=[
                    Row(children=header_children, gap=6, justify="center", padding=padding),
                    value_row,
                    bar_row,
                ],
                gap=int(height * 0.06),
                justify="center",
                align="stretch",
            ).render(ctx, x, y, width, height)

        elif is_compact:
            # Compact: icon + value on first line, bar + percent on second
            icon_size = max(10, int(height * 0.20))

            row1_children: list[Component] = []
            if self.icon:
                row1_children.append(Icon(name=self.icon, size=icon_size, color=self.color))
            row1_children.append(
                Text(text=value_text, font="small", color=THEME_TEXT_PRIMARY, align="start")
            )

            row2_children: list[Component] = [
                Bar(
                    percent=percent,
                    color=self.color,
                    background=COLOR_DARK_GRAY,
                    height=bar_height,
                ),
                Text(text=f"{percent:.0f}%", font="tiny", color=THEME_TEXT_PRIMARY, align="end"),
            ]

            Column(
                children=[
                    Row(children=row1_children, gap=4, align="center", padding=padding),
                    Row(children=row2_children, gap=8, align="center", padding=padding),
                ],
                gap=int(height * 0.10),
                justify="center",
                align="stretch",
            ).render(ctx, x, y, width, height)

        else:
            # Standard: icon + label + value on first line, bar + percent on second
            icon_size = max(10, int(height * 0.20))

            top_row_children: list[Component] = []
            if self.icon:
                top_row_children.append(Icon(name=self.icon, size=icon_size, color=self.color))

            # Check if label fits by measuring
            font_label = ctx.get_font("small")
            font_value = ctx.get_font("regular")
            label_width, _ = ctx.get_text_size(label_text, font_label)
            value_width, _ = ctx.get_text_size(value_text, font_value)
            icon_width = icon_size + 4 if self.icon else 0
            available_for_label = width - padding * 2 - icon_width - value_width - 8

            if available_for_label >= label_width:
                top_row_children.extend(
                    [
                        Text(
                            text=label_text, font="small", color=THEME_TEXT_SECONDARY, align="start"
                        ),
                        Spacer(),
                        Text(
                            text=value_text, font="regular", color=THEME_TEXT_PRIMARY, align="end"
                        ),
                    ]
                )
            else:
                top_row_children.append(
                    Text(text=value_text, font="regular", color=THEME_TEXT_PRIMARY, align="start")
                )

            bottom_row_children: list[Component] = [
                Bar(
                    percent=percent,
                    color=self.color,
                    background=COLOR_DARK_GRAY,
                    height=bar_height,
                ),
                Text(text=f"{percent:.0f}%", font="small", color=THEME_TEXT_PRIMARY, align="end"),
            ]

            Column(
                children=[
                    Row(children=top_row_children, gap=4, align="center", padding=padding),
                    Row(children=bottom_row_children, gap=8, align="center", padding=padding),
                ],
                gap=int(height * 0.10),
                justify="center",
                align="stretch",
            ).render(ctx, x, y, width, height)


class ProgressWidget(Widget):
    """Widget that displays progress with label."""

    WIDGET_TYPE: ClassVar[str] = "progress"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Progress",
        "needs_entity": True,
        "entity_domains": None,
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
        self.icon = config.options.get("icon")
        self.bar_height_style = config.options.get("bar_height", "normal")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the progress widget."""
        entity = state.entity
        value = _extract_numeric(entity)

        unit = self.unit
        if not unit and entity:
            unit = entity.unit or ""

        label = self.config.label
        if not label and entity:
            label = entity.friendly_name
        label = label or "Progress"

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
        row_count = len(self.items) or 1

        # Calculate sizes
        title_height = int(height * 0.14) if self.title else 0
        available_height = height - title_height - padding * 2
        row_height = min(int(height * 0.35), available_height // row_count)
        bar_height = max(4, int(height * 0.06))
        icon_size = max(8, int(height * 0.09))

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
                        text=label.upper(), font="tiny", color=THEME_TEXT_SECONDARY, align="start"
                    ),
                    Spacer(),
                    Text(text=value_text, font="tiny", color=THEME_TEXT_PRIMARY, align="end"),
                ]
            )

            # Bottom row: Bar + Percent
            bottom_row_children = [
                Bar(percent=percent, color=color, background=COLOR_DARK_GRAY, height=bar_height),
                Text(text=f"{percent:.0f}%", font="tiny", color=THEME_TEXT_PRIMARY, align="end"),
            ]

            # Combine into a column for this item
            item_column = Column(
                children=[
                    Row(children=top_row_children, gap=4, align="center", padding=padding),
                    Row(children=bottom_row_children, gap=8, align="center", padding=padding),
                ],
                gap=int(row_height * 0.15),
                justify="center",
                align="stretch",  # Stretch rows to full width for Spacer to work
            )
            children.append(item_column)

        # Render the entire column
        Column(
            children=children,
            gap=int(height * 0.02),
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
            value = _extract_numeric(entity)

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
