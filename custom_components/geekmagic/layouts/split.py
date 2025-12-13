"""Split layout for GeekMagic displays."""

from __future__ import annotations

from .base import Layout, Slot


class SplitLayout(Layout):
    """Layout with vertical or horizontal split panels.

    Vertical split:
    +----------+----------+
    |          |          |
    |  LEFT    |  RIGHT   |
    | (slot 0) | (slot 1) |
    |          |          |
    +----------+----------+

    Horizontal split:
    +---------------------+
    |        TOP          |
    |      (slot 0)       |
    +---------------------+
    |       BOTTOM        |
    |      (slot 1)       |
    +---------------------+
    """

    def __init__(
        self,
        horizontal: bool = False,
        ratio: float = 0.5,
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize split layout.

        Args:
            horizontal: If True, split horizontally (top/bottom)
            ratio: Ratio of first panel (0.0-1.0)
            padding: Padding around edges
            gap: Gap between panels
        """
        self.horizontal = horizontal
        self.ratio = max(0.2, min(0.8, ratio))  # Clamp to reasonable range
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate split panel rectangles."""
        self.slots = []

        available_width = self.width - (2 * self.padding) - self.gap
        available_height = self.height - (2 * self.padding) - self.gap

        if self.horizontal:
            # Top/bottom split
            top_height = int((available_height + self.gap) * self.ratio) - self.gap // 2
            bottom_height = available_height - top_height

            # Top slot
            self.slots.append(Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.width - self.padding,
                    self.padding + top_height,
                ),
            ))

            # Bottom slot
            self.slots.append(Slot(
                index=1,
                rect=(
                    self.padding,
                    self.padding + top_height + self.gap,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            ))
        else:
            # Left/right split
            left_width = int((available_width + self.gap) * self.ratio) - self.gap // 2
            right_width = available_width - left_width

            # Left slot
            self.slots.append(Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.padding + left_width,
                    self.height - self.padding,
                ),
            ))

            # Right slot
            self.slots.append(Slot(
                index=1,
                rect=(
                    self.padding + left_width + self.gap,
                    self.padding,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            ))


class ThreeColumnLayout(Layout):
    """Three column layout.

    +-------+-------+-------+
    |       |       |       |
    |  L    |   M   |   R   |
    |       |       |       |
    +-------+-------+-------+
    """

    def __init__(
        self,
        ratios: tuple[float, float, float] = (0.33, 0.34, 0.33),
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize three-column layout.

        Args:
            ratios: Width ratios for each column (should sum to ~1.0)
            padding: Padding around edges
            gap: Gap between columns
        """
        self.ratios = ratios
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate column rectangles."""
        self.slots = []

        available_width = self.width - (2 * self.padding) - (2 * self.gap)
        total_ratio = sum(self.ratios)

        x = self.padding
        for i, ratio in enumerate(self.ratios):
            col_width = int(available_width * (ratio / total_ratio))

            self.slots.append(Slot(
                index=i,
                rect=(
                    x,
                    self.padding,
                    x + col_width,
                    self.height - self.padding,
                ),
            ))

            x += col_width + self.gap
