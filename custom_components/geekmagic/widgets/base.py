"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


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
    """Base class for all widgets."""

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
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the widget using the provided render context.

        Args:
            ctx: RenderContext providing local coordinate system and drawing methods.
                 Use ctx.width and ctx.height for container dimensions.
                 All drawing coordinates are relative to widget origin (0, 0).
            hass: Home Assistant instance for entity states
        """

    def get_entity_state(self, hass: HomeAssistant | None, entity_id: str | None = None) -> Any:
        """Get the state of an entity.

        Args:
            hass: Home Assistant instance
            entity_id: Entity ID to get state for (defaults to self.entity_id)

        Returns:
            Entity state object or None
        """
        if hass is None:
            return None

        eid = entity_id or self.config.entity_id
        if eid is None:
            return None

        return hass.states.get(eid)
