"""Base layout class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..const import DISPLAY_WIDTH, DISPLAY_HEIGHT

if TYPE_CHECKING:
    from PIL import ImageDraw
    from homeassistant.core import HomeAssistant

    from ..renderer import Renderer
    from ..widgets.base import Widget


@dataclass
class Slot:
    """Represents a widget slot in a layout."""

    index: int
    rect: tuple[int, int, int, int]  # x1, y1, x2, y2
    widget: Widget | None = None


class Layout(ABC):
    """Base class for display layouts."""

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize the layout.

        Args:
            padding: Padding around the edges
            gap: Gap between widgets
        """
        self.padding = padding
        self.gap = gap
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self.slots: list[Slot] = []
        self._calculate_slots()

    @abstractmethod
    def _calculate_slots(self) -> None:
        """Calculate the slot rectangles. Override in subclasses."""
        pass

    def get_slot_count(self) -> int:
        """Return the number of widget slots."""
        return len(self.slots)

    def get_slot(self, index: int) -> Slot | None:
        """Get a slot by index."""
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def set_widget(self, index: int, widget: Widget) -> None:
        """Set a widget in a slot.

        Args:
            index: Slot index
            widget: Widget to place
        """
        if 0 <= index < len(self.slots):
            self.slots[index].widget = widget

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render all widgets in the layout.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            hass: Home Assistant instance
        """
        for slot in self.slots:
            if slot.widget is not None:
                slot.widget.render(renderer, draw, slot.rect, hass)

    def get_all_entities(self) -> list[str]:
        """Get all entity IDs from all widgets."""
        entities = []
        for slot in self.slots:
            if slot.widget is not None:
                entities.extend(slot.widget.get_entities())
        return entities
