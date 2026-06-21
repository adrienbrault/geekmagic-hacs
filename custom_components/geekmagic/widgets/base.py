"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .components import Component
    from .state import EntityState, WidgetState


@dataclass
class WidgetConfig:
    """Configuration for a widget."""

    widget_type: str
    slot: int = 0
    entity_id: str | None = None
    label: str | None = None
    color: tuple[int, int, int] | None = None
    text_scale: float = 1.0
    options: dict[str, Any] = field(default_factory=dict)


class Widget(ABC):
    """Base class for all widgets.

    Widgets render by returning a Component tree. All state needed for
    rendering is passed via the WidgetState parameter, enabling pure
    functional rendering.
    """

    WIDGET_TYPE: ClassVar[str] = ""
    SCHEMA: ClassVar[dict[str, Any]] = {}

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

    def label_for(self, entity: EntityState | None, *, fallback: str = "") -> str:
        """Resolve display label: ``config.label`` > ``entity.friendly_name`` > ``fallback``.

        Pretty much every widget that renders a name needs this chain.
        ``EntityState.friendly_name`` already falls back to ``entity_id``
        when no friendly name attribute is set, so widgets that previously
        wrote ``entity.friendly_name or entity.entity_id`` collapse to
        a single ``self.label_for(entity, fallback=...)``.
        """
        if self.config.label:
            return self.config.label
        if entity is not None:
            return entity.friendly_name
        return fallback

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
