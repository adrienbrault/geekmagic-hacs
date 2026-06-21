"""Hero layout for GeekMagic displays."""

from __future__ import annotations

from .base import Layout, Slot


class HeroLayout(Layout):
    """Layout with large hero widget and footer widgets.

    Structure:
    +------------------------+
    |                        |
    |         HERO           |
    |        (slot 0)        |
    |                        |
    +-------+-------+--------+
    | slot1 | slot2 | slot3  |
    +-------+-------+--------+
    """

    def __init__(
        self,
        footer_slots: int = 3,
        hero_ratio: float = 0.7,
        padding: int | None = None,
        gap: int | None = None,
        background_image: str | None = None,
        background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0,
    ) -> None:
        """Initialize hero layout.

        Args:
            footer_slots: Number of footer widgets
            hero_ratio: Ratio of hero height to total height
            padding: Padding around edges
            gap: Gap between widgets
            background_image: Optional path to a local background image
            background_mode: How to fit the image: stretch, contain, cover
        """
        self.footer_slots = footer_slots
        self.hero_ratio = hero_ratio
        super().__init__(padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)

    def _calculate_slots(self) -> None:
        """Calculate hero and footer rectangles."""
        self.slots = []

        # Available dimensions
        available_width = self.width - (2 * self.padding)
        available_height = self.height - (2 * self.padding) - self.gap

        # Hero section
        hero_height = int(available_height * self.hero_ratio)

        # Hero slot (index 0)
        self.slots.append(
            Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.width - self.padding,
                    self.padding + hero_height,
                ),
            )
        )

        # Footer slots
        footer_width = (available_width - (self.footer_slots - 1) * self.gap) // self.footer_slots
        footer_y = self.padding + hero_height + self.gap

        for i in range(self.footer_slots):
            x1 = self.padding + i * (footer_width + self.gap)
            x2 = x1 + footer_width
            y1 = footer_y
            y2 = self.height - self.padding

            self.slots.append(Slot(index=i + 1, rect=(x1, y1, x2, y2)))
