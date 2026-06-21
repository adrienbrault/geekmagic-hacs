"""Fullscreen layout for GeekMagic displays."""

from __future__ import annotations

from .base import Layout, Slot


class FullscreenLayout(Layout):
    """Single widget taking full 240x240 display with no padding.

    +---------------------+
    |                     |
    |                     |
    |      FULLSCREEN     |
    |       (slot 0)      |
    |                     |
    |                     |
    +---------------------+
    """

    def __init__(self, padding: int = 0, gap: int = 0, background_image: str | None = None, background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0) -> None:
        """Initialize fullscreen layout.

        Args:
            padding: Ignored, always 0 for edge-to-edge display
            gap: Ignored, only one slot
            background_image: Optional path to a local background image
            background_mode: How to fit the image: stretch, contain, cover
        """
        # Force 0 padding for true edge-to-edge display
        super().__init__(padding=0, gap=0, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)

    def _calculate_slots(self) -> None:
        """Calculate single fullscreen slot."""
        self.slots = [
            Slot(
                index=0,
                rect=(0, 0, self.width, self.height),
            )
        ]
