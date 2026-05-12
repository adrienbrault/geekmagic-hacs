"""Icon widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .base import Widget, WidgetConfig
from .components import Center, Component, Icon, Panel

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class IconWidget(Widget):
    """Widget that displays a static icon."""

    WIDGET_TYPE: ClassVar[str] = "icon"

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the icon widget."""
        super().__init__(config)
        # ``"mdi:help"`` is the new-widget default; an empty string (user
        # cleared the picker) is honoured as "no icon — render nothing".
        self.icon = config.options.get("icon", "mdi:help")
        self.show_panel = config.options.get("show_panel", False)
        # "size" option: "regular" (default) or "huge" (fills container)
        self.size_mode = config.options.get("size", "regular")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the icon widget."""
        # In "huge" mode the Icon clamps to the cell; an arbitrary 240
        # ceiling lets it grow to the full 240x240 panel.
        max_size = 240 if self.size_mode == "huge" else 32

        # Honour an explicit per-widget colour, otherwise let the active
        # theme tint the icon via the slot's accent.
        color = self.config.color or ctx.theme.get_accent_color(self.config.slot)

        content = Center(child=Icon(self.icon, max_size=max_size, color=color))

        # Wrap in panel if enabled
        if self.show_panel:
            return Panel(child=content)

        return content
