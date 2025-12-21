"""Status widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..const import COLOR_GRAY, COLOR_LIME, COLOR_RED, COLOR_WHITE, PLACEHOLDER_NAME
from .base import Widget, WidgetConfig
from .components import Color, Component
from .helpers import estimate_max_chars, truncate_text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState


def _is_entity_on(entity: EntityState | None) -> bool:
    """Check if entity is in 'on' state."""
    if entity is None:
        return False
    return entity.state.lower() in ("on", "true", "1", "home", "open", "unlocked")


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
        """Render status indicator."""
        center_y = y + height // 2
        font_name = ctx.get_font("small")
        font_status = ctx.get_font("small")
        padding = int(width * 0.06)
        icon_size = max(12, min(24, int(height * 0.35)))

        color = self.on_color if self.is_on else self.off_color
        status_text = self.on_text if self.is_on else self.off_text

        # Truncate name
        max_name_len = estimate_max_chars(width, char_width=7, padding=20)
        name = truncate_text(self.name, max_name_len, style="middle")

        # Draw icon (colored by state) - no separate dot
        text_x = x + padding
        if self.icon:
            ctx.draw_icon(
                self.icon, (text_x, center_y - icon_size // 2), size=icon_size, color=color
            )
            text_x += icon_size + 6

        # Draw name
        ctx.draw_text(name, (text_x, center_y), font=font_name, color=COLOR_WHITE, anchor="lm")

        # Draw status text
        if self.show_status_text:
            ctx.draw_text(
                status_text,
                (x + width - padding, center_y),
                font=font_status,
                color=color,
                anchor="rm",
            )


class StatusWidget(Widget):
    """Widget that displays a binary sensor status with colored indicator."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status widget."""
        super().__init__(config)
        self.on_color = config.options.get("on_color", COLOR_LIME)
        self.off_color = config.options.get("off_color", COLOR_RED)
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
        """Render status list."""
        font_title = ctx.get_font("small")
        font_label = ctx.get_font("tiny")
        padding = int(width * 0.05)
        current_y = y + padding

        if self.title:
            ctx.draw_text(
                self.title.upper(),
                (x + padding, current_y),
                font=font_title,
                color=COLOR_GRAY,
                anchor="lm",
            )
            current_y += int(height * 0.15)

        available_height = y + height - current_y - padding
        row_count = len(self.items) or 1
        row_height = min(int(height * 0.17), available_height // row_count)
        icon_size = max(10, min(16, int(row_height * 0.7)))
        max_len = estimate_max_chars(width, char_width=7, padding=30)

        for label, is_on, on_color, off_color, icon in self.items:
            color = on_color if is_on else off_color
            display_label = truncate_text(label, max_len, style="middle")

            row_y = current_y + row_height // 2
            text_x = x + padding

            # Draw icon colored by state (instead of dot)
            if icon:
                ctx.draw_icon(icon, (text_x, row_y - icon_size // 2), size=icon_size, color=color)
                text_x += icon_size + 6

            ctx.draw_text(
                display_label,
                (text_x, row_y),
                font=font_label,
                color=COLOR_WHITE,
                anchor="lm",
            )

            if self.on_text or self.off_text:
                status_text = self.on_text if is_on else self.off_text
                if status_text:
                    ctx.draw_text(
                        status_text,
                        (x + width - padding, row_y),
                        font=font_label,
                        color=color,
                        anchor="rm",
                    )

            current_y += row_height


class StatusListWidget(Widget):
    """Widget that displays a list of binary sensors with status indicators."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the status list widget."""
        super().__init__(config)
        self.entities = config.options.get("entities", [])
        self.on_color = config.options.get("on_color", COLOR_LIME)
        self.off_color = config.options.get("off_color", COLOR_RED)
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
