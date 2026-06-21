"""Grid layout for GeekMagic displays."""

from __future__ import annotations

from .base import Layout, Slot


class GridLayout(Layout):
    """Grid layout with configurable rows and columns."""

    def __init__(
        self,
        rows: int = 2,
        cols: int = 2,
        padding: int | None = None,
        gap: int | None = None,
        background_image: str | None = None,
        background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0,
    ) -> None:
        """Initialize the grid layout.

        Args:
            rows: Number of rows
            cols: Number of columns
            padding: Padding around edges
            gap: Gap between cells
            background_image: Optional path to a local background image
            background_mode: How to fit the image: stretch, contain, cover
        """
        self.rows = rows
        self.cols = cols
        super().__init__(padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)

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

    def __init__(self, padding: int | None = None, gap: int | None = None, background_image: str | None = None, background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0) -> None:
        super().__init__(rows=2, cols=2, padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)


class Grid2x3(GridLayout):
    """2x3 grid layout (6 slots) - 2 rows, 3 columns."""

    def __init__(self, padding: int | None = None, gap: int | None = None, background_image: str | None = None, background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0) -> None:
        super().__init__(rows=2, cols=3, padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)


class Grid3x2(GridLayout):
    """3x2 grid layout (6 slots) - 3 rows, 2 columns."""

    def __init__(self, padding: int | None = None, gap: int | None = None, background_image: str | None = None, background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0) -> None:
        super().__init__(rows=3, cols=2, padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)


class Grid3x3(GridLayout):
    """3x3 grid layout (9 slots)."""

    def __init__(self, padding: int | None = None, gap: int | None = None, background_image: str | None = None, background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0) -> None:
        super().__init__(rows=3, cols=3, padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)
