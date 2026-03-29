"""Split layout for GeekMagic displays."""

from __future__ import annotations

from typing import ClassVar

from .base import Layout, Slot


class SplitHorizontal(Layout):
    """Horizontal split layout - side by side (left/right).

    +----------+----------+
    |          |          |
    |  LEFT    |  RIGHT   |
    | (slot 0) | (slot 1) |
    |          |          |
    +----------+----------+
    """

    LAYOUT_TYPE: ClassVar[str] = "split_horizontal"
    SLOT_COUNT: ClassVar[int] = 2

    def __init__(
        self,
        ratio: float = 0.5,
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize horizontal split layout.

        Args:
            ratio: Ratio of left panel width (0.0-1.0)
            padding: Padding around edges
            gap: Gap between panels
        """
        self.ratio = max(0.2, min(0.8, ratio))
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate left/right panel rectangles."""
        self.slots = []

        available_width, _ = self._available_space()
        content_width = available_width - self.gap
        left_width = int(content_width * self.ratio)

        # Left slot
        self.slots.append(
            Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.padding + left_width,
                    self.height - self.padding,
                ),
            )
        )

        # Right slot
        self.slots.append(
            Slot(
                index=1,
                rect=(
                    self.padding + left_width + self.gap,
                    self.padding,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            )
        )


class SplitVertical(Layout):
    """Vertical split layout - stacked (top/bottom).

    +---------------------+
    |        TOP          |
    |      (slot 0)       |
    +---------------------+
    |       BOTTOM        |
    |      (slot 1)       |
    +---------------------+
    """

    LAYOUT_TYPE: ClassVar[str] = "split_vertical"
    SLOT_COUNT: ClassVar[int] = 2

    def __init__(
        self,
        ratio: float = 0.5,
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize vertical split layout.

        Args:
            ratio: Ratio of top panel height (0.0-1.0)
            padding: Padding around edges
            gap: Gap between panels
        """
        self.ratio = max(0.2, min(0.8, ratio))
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate top/bottom panel rectangles."""
        self.slots = []

        _, available_height = self._available_space()
        content_height = available_height - self.gap
        top_height = int(content_height * self.ratio)

        # Top slot
        self.slots.append(
            Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.width - self.padding,
                    self.padding + top_height,
                ),
            )
        )

        # Bottom slot
        self.slots.append(
            Slot(
                index=1,
                rect=(
                    self.padding,
                    self.padding + top_height + self.gap,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            )
        )


# Keep for backwards compatibility
SplitLayout = SplitHorizontal


class ThreeColumnLayout(Layout):
    """Three column layout.

    +-------+-------+-------+
    |       |       |       |
    |  L    |   M   |   R   |
    |       |       |       |
    +-------+-------+-------+
    """

    LAYOUT_TYPE: ClassVar[str] = "three_column"
    SLOT_COUNT: ClassVar[int] = 3

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

            self.slots.append(
                Slot(
                    index=i,
                    rect=(
                        x,
                        self.padding,
                        x + col_width,
                        self.height - self.padding,
                    ),
                )
            )

            x += col_width + self.gap


class ThreeRowLayout(Layout):
    """Three row layout - stacked horizontally.

    +---------------------+
    |        TOP          |
    |      (slot 0)       |
    +---------------------+
    |       MIDDLE        |
    |      (slot 1)       |
    +---------------------+
    |       BOTTOM        |
    |      (slot 2)       |
    +---------------------+
    """

    LAYOUT_TYPE: ClassVar[str] = "three_row"
    SLOT_COUNT: ClassVar[int] = 3

    def __init__(
        self,
        ratios: tuple[float, float, float] = (0.33, 0.34, 0.33),
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize three-row layout.

        Args:
            ratios: Height ratios for each row (should sum to ~1.0)
            padding: Padding around edges
            gap: Gap between rows
        """
        self.ratios = ratios
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate row rectangles."""
        self.slots = []

        available_height = self.height - (2 * self.padding) - (2 * self.gap)
        total_ratio = sum(self.ratios)

        y = self.padding
        for i, ratio in enumerate(self.ratios):
            row_height = int(available_height * (ratio / total_ratio))

            self.slots.append(
                Slot(
                    index=i,
                    rect=(
                        self.padding,
                        y,
                        self.width - self.padding,
                        y + row_height,
                    ),
                )
            )

            y += row_height + self.gap


class SplitHorizontal1To2(SplitHorizontal):
    """Horizontal split - narrow left (1/3), wide right (2/3).

    +------+-------------+
    |      |             |
    | LEFT |    RIGHT    |
    | 1/3  |     2/3     |
    |      |             |
    +------+-------------+
    """

    LAYOUT_TYPE: ClassVar[str] = "split_h_1_2"
    SLOT_COUNT: ClassVar[int] = 2

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize 1:2 horizontal split."""
        super().__init__(ratio=0.33, padding=padding, gap=gap)


class SplitHorizontal2To1(SplitHorizontal):
    """Horizontal split - wide left (2/3), narrow right (1/3).

    +-------------+------+
    |             |      |
    |    LEFT     | RIGHT|
    |     2/3     |  1/3 |
    |             |      |
    +-------------+------+
    """

    LAYOUT_TYPE: ClassVar[str] = "split_h_2_1"
    SLOT_COUNT: ClassVar[int] = 2

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize 2:1 horizontal split."""
        super().__init__(ratio=0.67, padding=padding, gap=gap)
