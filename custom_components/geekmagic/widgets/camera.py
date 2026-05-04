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
        """Render camera image, optionally with a floating label chip."""
        # Image fills the entire widget — no reserved space.
        ctx.draw_image(self.image, rect=(x, y, x + width, y + height), fit_mode=self.fit)

        if not self.label:
            return

        # Floating label chip: caps text on a soft dark capsule, top-left.
        # Mimics watchOS "Now Playing"-style metadata chips that float over
        # photo content.
        font = ctx.get_font("tertiary")
        text = self.label.upper()
        text_w, text_h = ctx.get_text_size(text, font)
        chip_pad_x = max(6, int(width * 0.04))
        chip_pad_y = max(3, int(height * 0.02))
        margin = max(6, int(width * 0.04))
        chip_x = x + margin
        chip_y = y + margin
        chip_w = text_w + chip_pad_x * 2
        chip_h = text_h + chip_pad_y * 2

        ctx.draw_rounded_rect(
            (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
            radius=chip_h // 2,
            fill=(0, 0, 0),
        )
        ctx.draw_text(
            text,
            (chip_x + chip_w // 2, chip_y + chip_h // 2),
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
