"""Icon widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_CYAN
from .base import Widget, WidgetConfig
from .components import Center, Component, Icon, Panel

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class IconWidget(Widget):
    """Widget that displays a static icon."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the icon widget."""
        super().__init__(config)
        self.icon = config.options.get("icon", "mdi:help")
        self.color = config.options.get("color")
        self.show_panel = config.options.get("show_panel", False)
        # "size" option: "regular" (default) or "huge" (fills container)
        self.size_mode = config.options.get("size", "regular")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the icon widget."""
        
        # Handle "huge" mode
        max_size = 32
        if self.size_mode == "huge":
            # Arbitrary large number to allow filling the container,
            # Icon component will clamp to available space.
            max_size = 240 

        # Resolve color
        color = self.color or self.config.color or COLOR_CYAN

        # Create icon component
        content = Center(child=Icon(self.icon, max_size=max_size, color=color))

        # Wrap in panel if enabled
        if self.show_panel:
            return Panel(child=content)

        return content
