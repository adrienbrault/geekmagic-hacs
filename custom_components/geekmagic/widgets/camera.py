"""Camera widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from PIL import Image

from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
    Column,
    Component,
    Icon,
    Text,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


@dataclass
class CameraImage(Component):
    """Camera image display component."""

    image: Image.Image
    label: str | None = None
    color: Color = THEME_TEXT_PRIMARY
    fit: str = "contain"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render camera image."""
        # Calculate image rect
        if self.label:
            label_height = int(height * 0.15)
            image_rect = (x, y, x + width, y + height - label_height)
            label_y = y + height - label_height // 2
        else:
            image_rect = (x, y, x + width, y + height)
            label_y = None

        # Draw the camera image
        ctx.draw_image(self.image, rect=image_rect, fit_mode=self.fit)

        # Draw label if enabled
        if self.label and label_y is not None:
            font = ctx.get_font("small")
            ctx.draw_text(
                self.label,
                (x + width // 2, label_y),
                font=font,
                color=self.color,
                anchor="mm",
            )


def _camera_placeholder(label: str = "No Image") -> Component:
    """Create placeholder component when no camera image available."""
    return Column(
        children=[
            Icon("camera", color=THEME_TEXT_SECONDARY, max_size=48),
            Text(label, font="small", color=THEME_TEXT_SECONDARY),
        ],
        gap=8,
        align="center",
        justify="center",
    )


class CameraWidget(Widget):
    """Widget that displays a camera snapshot."""

    WIDGET_TYPE: ClassVar[str] = "camera"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Camera",
        "needs_entity": True,
        "entity_domains": ["camera"],
        "options": [
            {
                "key": "fit",
                "type": "select",
                "label": "Fit Mode",
                "options": ["cover", "contain"],
                "default": "cover",
            },
            {"key": "show_label", "type": "boolean", "label": "Show Label", "default": False},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the camera widget."""
        super().__init__(config)
        self.show_label = config.options.get("show_label", False)
        self.fit = config.options.get("fit", "contain")

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the camera widget.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with camera image
        """
        if state.image is None:
            return _camera_placeholder(label=self.config.label or "No Image")

        label = None
        if self.show_label:
            label = self.config.label
            if not label and state.entity:
                label = state.entity.friendly_name
            label = label or "Camera"

        return CameraImage(
            image=state.image.convert("RGB") if state.image.mode != "RGB" else state.image,
            label=label,
            color=self.config.color or THEME_TEXT_PRIMARY,
            fit=self.fit,
        )
