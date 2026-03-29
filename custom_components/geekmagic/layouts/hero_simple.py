"""Hero Simple layout for GeekMagic displays."""

from __future__ import annotations

from typing import ClassVar

from .base import Layout, Slot


class HeroSimpleLayout(Layout):
    """Layout with one large hero widget (top 2/3) and one footer widget (bottom 1/3).

    Structure:
    +------------------------+
    |                        |
    |         HERO           |
    |        (slot 0)        |
    |                        |
    +------------------------+
    |         FOOTER         |
    |        (slot 1)        |
    +------------------------+
    """

    LAYOUT_TYPE: ClassVar[str] = "hero_simple"
    SLOT_COUNT: ClassVar[int] = 2

    def __init__(
        self,
        hero_ratio: float = 0.66,
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize hero simple layout.

        Args:
            hero_ratio: Ratio of hero height to total height
            padding: Padding around edges
            gap: Gap between widgets
        """
        self.hero_ratio = hero_ratio
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate hero and footer rectangles."""
        self.slots = []

        # Available dimensions

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

        # Footer slot (index 1)
        # Starts after hero + gap
        footer_y = self.padding + hero_height + self.gap

        self.slots.append(
            Slot(
                index=1,
                rect=(
                    self.padding,
                    footer_y,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            )
        )
