"""Grid layout for GeekMagic displays."""

from __future__ import annotations

from typing import ClassVar

from .base import Layout, Slot


class GridLayout(Layout):
    """Grid layout with configurable rows and columns."""

    def __init__(
        self,
        rows: int = 2,
        cols: int = 2,
        padding: int = 8,
        gap: int = 8,
    ) -> None:
        """Initialize the grid layout.

        Args:
            rows: Number of rows
            cols: Number of columns
            padding: Padding around edges
            gap: Gap between cells
        """
        self.rows = rows
        self.cols = cols
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate grid cell rectangles."""
        self.slots = []

        # Available space after padding
        available_width = self.width - (2 * self.padding) - ((self.cols - 1) * self.gap)
        available_height = self.height - (2 * self.padding) - ((self.rows - 1) * self.gap)

        # Cell dimensions
        cell_width = available_width // self.cols
        cell_height = available_height // self.rows

        slot_index = 0
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = self.padding + col * (cell_width + self.gap)
                y1 = self.padding + row * (cell_height + self.gap)
                x2 = x1 + cell_width
                y2 = y1 + cell_height

                self.slots.append(Slot(index=slot_index, rect=(x1, y1, x2, y2)))
                slot_index += 1


class Grid2x2(GridLayout):
    """2x2 grid layout (4 slots)."""

    LAYOUT_TYPE: ClassVar[str] = "grid_2x2"
    SLOT_COUNT: ClassVar[int] = 4

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        super().__init__(rows=2, cols=2, padding=padding, gap=gap)


class Grid2x3(GridLayout):
    """2x3 grid layout (6 slots) - 2 rows, 3 columns."""

    LAYOUT_TYPE: ClassVar[str] = "grid_2x3"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        super().__init__(rows=2, cols=3, padding=padding, gap=gap)


class Grid3x2(GridLayout):
    """3x2 grid layout (6 slots) - 3 rows, 2 columns."""

    LAYOUT_TYPE: ClassVar[str] = "grid_3x2"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        super().__init__(rows=3, cols=2, padding=padding, gap=gap)


class Grid3x3(GridLayout):
    """3x3 grid layout (9 slots)."""

    LAYOUT_TYPE: ClassVar[str] = "grid_3x3"
    SLOT_COUNT: ClassVar[int] = 9

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        super().__init__(rows=3, cols=3, padding=padding, gap=gap)
