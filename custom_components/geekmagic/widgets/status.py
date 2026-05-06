"""Status widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ..const import PLACEHOLDER_NAME
from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_ERROR,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
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
    on_color: Color = THEME_SUCCESS
    off_color: Color = THEME_ERROR
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

        # Vertical layout when there's enough vertical room — either because
        # the cell is naturally tall (MEDIUM/LARGE) or because the cell is
        # narrow-but-tall, where horizontal would crush icon + label + state.
        prefer_vertical = size in (SizeCategory.MEDIUM, SizeCategory.LARGE) or (
            width < 90 and height >= 80
        )
        if prefer_vertical and self.icon:
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

        # Decide whether the on/off status text fits alongside name + icon.
        # If the name + status couldn't fit even as truncated 3-char
        # words, drop the status: the icon's color already conveys the
        # state and a readable name is more useful than a truncated state.
        font_bold = ctx.get_font("small", bold=True)
        icon_w = (icon_size + 6) if self.icon else 0
        inner_w = width - padding * 2 - icon_w
        status_w, _ = ctx.get_text_size(status_text, font_bold)
        # 24px ≈ "name…" minimum readable width for the name on the left.
        show_status = self.show_status_text and status_w + 24 <= inner_w

        children: list[Component] = []
        if self.icon:
            children.append(Icon(name=self.icon, size=icon_size, color=color))
        children.append(
            Text(
                text=self.name,
                font="small",
                color=THEME_TEXT_PRIMARY,
                align="start",
                truncate=True,
            )
        )
        if show_status:
            children.append(Spacer())
            children.append(
                Text(
                    text=status_text,
                    font="small",
                    color=color,
                    align="end",
                    bold=True,
                )
            )

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

    WIDGET_TYPE: ClassVar[str] = "status"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Status",
        "needs_entity": True,
        "entity_domains": None,  # Any entity (interprets state as on/off)
        "options": [
            {"key": "on_text", "type": "text", "label": "On Text", "default": "On"},
            {"key": "off_text", "type": "text", "label": "Off Text", "default": "Off"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [102, 166, 30],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [231, 76, 60],
            },
            {"key": "icon", "type": "icon", "label": "Icon"},
            {
                "key": "show_status_text",
                "type": "boolean",
                "label": "Show Status Text",
                "default": True,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status widget."""
        super().__init__(config)
        self.on_color = parse_color(config.options.get("on_color"), THEME_SUCCESS)
        self.off_color = parse_color(config.options.get("off_color"), THEME_ERROR)
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
        """Render status list (watchOS list pattern: caps-tracked title,
        tinted dot per row, semibold name, status state as a tinted accent
        on the right; thin separator lines between rows).
        """
        padding = int(width * 0.05)
        row_count = len(self.items) or 1
        title_h = int(height * 0.15) if self.title else 0
        available_height = height - padding * 2 - title_h
        row_height = max(14, available_height // row_count)
        icon_size = max(10, min(18, int(row_height * 0.68)))
        max_len = estimate_max_chars(width, char_width=7, padding=30)

        # Caps-tracked title at the top
        if self.title:
            ctx.draw_label(
                self.title,
                (x + padding, y + padding),
                color=ctx.theme.text_secondary,
                anchor="lt",
                size="tertiary",
            )

        # Render items, drawing a 1px separator line above each (except first).
        sep_color = ctx.theme.border
        list_top = y + padding + title_h
        for i, (label, is_on, on_color, off_color, icon) in enumerate(self.items):
            color = on_color if is_on else off_color
            display_label = truncate_text(label, max_len, style="middle")
            row_y = list_top + i * row_height

            # Separator before all rows except the first
            if i > 0:
                ctx.draw_line(
                    [(x + padding, row_y), (x + width - padding, row_y)],
                    fill=sep_color,
                    width=1,
                )

            row_children: list[Component] = []
            if icon:
                row_children.append(Icon(name=icon, size=icon_size, color=color))
            row_children.append(
                Text(text=display_label, font="tiny", color=THEME_TEXT_PRIMARY, align="start")
            )

            if self.on_text or self.off_text:
                status_text = self.on_text if is_on else self.off_text
                if status_text:
                    row_children.append(Spacer())
                    row_children.append(
                        Text(text=status_text, font="tiny", bold=True, color=color, align="end")
                    )

            Row(
                children=row_children,
                gap=6,
                align="center",
                justify="start",
                padding=2,
            ).render(ctx, x + padding, row_y, width - padding * 2, row_height)


class StatusListWidget(Widget):
    """Widget that displays a list of binary sensors with status indicators."""

    WIDGET_TYPE: ClassVar[str] = "status_list"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Status List",
        "needs_entity": False,
        "options": [
            {"key": "title", "type": "text", "label": "Title"},
            {"key": "entities", "type": "status_entities", "label": "Status Entities"},
            {
                "key": "on_color",
                "type": "color",
                "label": "On Color",
                "default": [102, 166, 30],
            },
            {
                "key": "off_color",
                "type": "color",
                "label": "Off Color",
                "default": [231, 76, 60],
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status list widget."""
        super().__init__(config)
        self.entities = config.options.get("entities", [])
        self.on_color = parse_color(config.options.get("on_color"), THEME_SUCCESS)
        self.off_color = parse_color(config.options.get("off_color"), THEME_ERROR)
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
