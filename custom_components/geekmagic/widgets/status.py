"""Status widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..const import COLOR_LIME, COLOR_RED, PLACEHOLDER_NAME
from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
    Column,
    Component,
    Icon,
    Row,
    Spacer,
    Text,
)
from .helpers import ON_STATES, estimate_max_chars, parse_color, truncate_text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState


def _is_entity_on(entity: EntityState | None) -> bool:
    """Check if entity is in 'on' state."""
    if entity is None:
        return False
    return entity.state.lower() in ON_STATES


@dataclass
class StatusIndicator(Component):
    """Status indicator with dot, label, and status text."""

    name: str
    is_on: bool = False
    on_color: Color = COLOR_LIME
    off_color: Color = COLOR_RED
    on_text: str = "ON"
    off_text: str = "OFF"
    icon: str | None = None
    show_status_text: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render status indicator using component primitives."""
        size = get_size_category(height)
        color = self.on_color if self.is_on else self.off_color
        status_text = self.on_text if self.is_on else self.off_text

        # Use vertical layout with prominent icon for larger cells
        if size in (SizeCategory.MEDIUM, SizeCategory.LARGE) and self.icon:
            self._render_vertical(ctx, x, y, width, height, color, status_text)
        else:
            self._render_horizontal(ctx, x, y, width, height, color, status_text)

    def _render_vertical(
        self,
        ctx: RenderContext,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Color,
        status_text: str,
    ) -> None:
        """Render vertical layout with prominent icon for larger cells."""
        # Guard: this method requires an icon (caller checks, but type checker needs this)
        if not self.icon:
            return

        padding = int(width * 0.08)
        icon_size = max(32, min(64, int(height * 0.40)))

        # Truncate name for display
        max_name_len = estimate_max_chars(width, char_width=8, padding=padding * 2)
        name = truncate_text(self.name, max_name_len, style="middle")

        children: list[Component] = [
            Icon(name=self.icon, size=icon_size, color=color),
            Text(text=name, font="small", color=THEME_TEXT_PRIMARY),
        ]

        if self.show_status_text:
            children.append(Text(text=status_text, font="medium", color=color, bold=True))

        Column(
            children=children,
            gap=int(height * 0.05),
            padding=padding,
            align="center",
            justify="center",
        ).render(ctx, x, y, width, height)

    def _render_horizontal(
        self,
        ctx: RenderContext,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Color,
        status_text: str,
    ) -> None:
        """Render horizontal layout for compact cells."""
        padding = int(width * 0.06)
        icon_size = max(12, min(24, int(height * 0.35)))

        # Truncate name
        max_name_len = estimate_max_chars(width, char_width=7, padding=20)
        name = truncate_text(self.name, max_name_len, style="middle")

        # Build component tree
        children: list[Component] = []

        # Add icon if provided
        if self.icon:
            children.append(Icon(name=self.icon, size=icon_size, color=color))

        # Add name text
        children.append(Text(text=name, font="small", color=THEME_TEXT_PRIMARY, align="start"))

        # Add spacer to push status text to the right
        if self.show_status_text:
            children.append(Spacer())
            children.append(Text(text=status_text, font="small", color=color, align="end"))

        # Render as a row
        Row(
            children=children,
            gap=6,
            padding=padding,
            align="center",
            justify="start",
        ).render(ctx, x, y, width, height)


class StatusWidget(Widget):
    """Widget that displays a binary sensor status with colored indicator."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status widget."""
        super().__init__(config)
        self.on_color = parse_color(config.options.get("on_color"), COLOR_LIME)
        self.off_color = parse_color(config.options.get("off_color"), COLOR_RED)
        self.on_text = config.options.get("on_text", "ON")
        self.off_text = config.options.get("off_text", "OFF")
        self.icon = config.options.get("icon")
        self.show_status_text = config.options.get("show_status_text", True)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the status widget."""
        entity = state.entity
        is_on = _is_entity_on(entity)

        name = self.config.label
        if not name and entity:
            name = entity.friendly_name
        name = name or PLACEHOLDER_NAME

        return StatusIndicator(
            name=name,
            is_on=is_on,
            on_color=self.on_color,
            off_color=self.off_color,
            on_text=self.on_text,
            off_text=self.off_text,
            icon=self.icon,
            show_status_text=self.show_status_text,
        )


@dataclass
class StatusListDisplay(Component):
    """Status list display component."""

    items: list[tuple[str, bool, Color, Color, str | None]] = field(
        default_factory=list
    )  # (label, is_on, on_color, off_color, icon)
    title: str | None = None
    on_text: str | None = None
    off_text: str | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render status list using component primitives."""
        padding = int(width * 0.05)

        # Build list of rows
        rows: list[Component] = []

        # Add title if provided
        if self.title:
            rows.append(
                Text(
                    text=self.title.upper(),
                    font="small",
                    color=THEME_TEXT_SECONDARY,
                    align="start",
                )
            )

        # Calculate dimensions for items
        available_height = height - padding * 2
        if self.title:
            available_height -= int(height * 0.15)

        row_count = len(self.items) or 1
        row_height = min(int(height * 0.17), available_height // row_count)
        icon_size = max(10, min(16, int(row_height * 0.7)))
        max_len = estimate_max_chars(width, char_width=7, padding=30)

        # Build each item row
        for label, is_on, on_color, off_color, icon in self.items:
            color = on_color if is_on else off_color
            display_label = truncate_text(label, max_len, style="middle")

            # Build row children
            row_children = []

            # Add icon if provided
            if icon:
                row_children.append(Icon(name=icon, size=icon_size, color=color))

            # Add label
            row_children.append(
                Text(text=display_label, font="tiny", color=THEME_TEXT_PRIMARY, align="start")
            )

            # Add status text if configured
            if self.on_text or self.off_text:
                status_text = self.on_text if is_on else self.off_text
                if status_text:
                    row_children.append(Spacer())
                    row_children.append(
                        Text(text=status_text, font="tiny", color=color, align="end")
                    )

            # Create row component
            rows.append(
                Row(
                    children=row_children,
                    gap=6,
                    align="center",
                    justify="start",
                )
            )

        # Render all rows in a column
        Column(
            children=rows,
            gap=4 if self.title else 2,
            padding=padding,
            align="stretch",
            justify="start",
        ).render(ctx, x, y, width, height)


class StatusListWidget(Widget):
    """Widget that displays a list of binary sensors with status indicators."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status list widget."""
        super().__init__(config)
        self.entities = config.options.get("entities", [])
        self.on_color = parse_color(config.options.get("on_color"), COLOR_LIME)
        self.off_color = parse_color(config.options.get("off_color"), COLOR_RED)
        self.on_text = config.options.get("on_text")
        self.off_text = config.options.get("off_text")
        self.title = config.options.get("title")

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on."""
        return [e[0] if isinstance(e, list | tuple) else e for e in self.entities]

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the status list widget."""
        items = []
        for entry in self.entities:
            if isinstance(entry, list | tuple):
                entity_id, label = entry[0], entry[1]
            else:
                entity_id = entry
                label = None

            entity = state.get_entity(entity_id)
            is_on = _is_entity_on(entity)
            if entity and not label:
                label = entity.friendly_name
            label = label or entity_id

            # Get icon from entity
            icon = entity.icon if entity else None

            items.append((label, is_on, self.on_color, self.off_color, icon))

        return StatusListDisplay(
            items=items,
            title=self.title,
            on_text=self.on_text,
            off_text=self.off_text,
        )
