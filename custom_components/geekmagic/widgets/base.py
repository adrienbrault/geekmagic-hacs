"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .components import Component
    from .state import WidgetState


@dataclass
class WidgetConfig:
    """Configuration for a widget."""

    widget_type: str
    slot: int = 0
    entity_id: str | None = None
    label: str | None = None
    color: tuple[int, int, int] | None = None
    options: dict[str, Any] = field(default_factory=dict)


class Widget(ABC):
    """Base class for all widgets.

    Widgets render by returning a Component tree. All state needed for
    rendering is passed via the WidgetState parameter, enabling pure
    functional rendering.
    """

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the widget.

        Args:
            config: Widget configuration
        """
        self.config = config

    @property
    def entity_id(self) -> str | None:
        """Get the entity ID this widget tracks."""
        return self.config.entity_id

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on.

        Override in subclasses that track entities.
        """
        if self.config.entity_id:
            return [self.config.entity_id]
        return []

    @abstractmethod
    def render(
        self,
        ctx: RenderContext,
        state: WidgetState,
    ) -> Component:
        """Render the widget as a Component tree.

        Pure function: given the same ctx and state, returns the same Component.
        All state needed for rendering is provided via the state parameter.

        Args:
            ctx: RenderContext providing local coordinate system and drawing methods.
                 Use ctx.width and ctx.height for container dimensions.
                 All drawing coordinates are relative to widget origin (0, 0).
            state: Pre-fetched state including entity data, history, images, time.

        Returns:
            Component tree to render
        """
