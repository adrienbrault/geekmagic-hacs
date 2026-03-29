"""Corner hero layouts for GeekMagic displays."""

from __future__ import annotations

from typing import ClassVar

from .base import Layout, Slot


class HeroCornerTL(Layout):
    """2x2 hero in top-left corner.

    ┌──────┬───┐
    │      │ 1 │
    │  0   ├───┤
    │      │ 2 │
    ├──┬──┬┴───┤
    │3 │4 │ 5  │
    └──┴──┴────┘

    Slot 0: Hero (top-left, 2x2)
    Slots 1-2: Stacked right column
    Slots 3-5: Bottom row (3 equal)
    """

    LAYOUT_TYPE: ClassVar[str] = "hero_corner_tl"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize corner hero top-left layout."""
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate slot rectangles."""
        self.slots = []

        available_width, available_height = self._available_space()

        # Hero takes 2/3 width, 2/3 height
        hero_width = int((available_width - self.gap) * 0.67)
        hero_height = int((available_height - self.gap) * 0.67)

        # Side column height
        side_height = (hero_height - self.gap) // 2

        # Bottom row
        bottom_y = self.padding + hero_height + self.gap
        bottom_cell_width = (available_width - 2 * self.gap) // 3

        # Slot 0: Hero (top-left)
        self.slots.append(
            Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.padding + hero_width,
                    self.padding + hero_height,
                ),
            )
        )

        # Slot 1: Top-right
        side_x = self.padding + hero_width + self.gap
        self.slots.append(
            Slot(
                index=1,
                rect=(
                    side_x,
                    self.padding,
                    self.width - self.padding,
                    self.padding + side_height,
                ),
            )
        )

        # Slot 2: Mid-right
        self.slots.append(
            Slot(
                index=2,
                rect=(
                    side_x,
                    self.padding + side_height + self.gap,
                    self.width - self.padding,
                    self.padding + hero_height,
                ),
            )
        )

        # Slots 3-5: Bottom row
        for i in range(3):
            x = self.padding + i * (bottom_cell_width + self.gap)
            self.slots.append(
                Slot(
                    index=i + 3,
                    rect=(
                        x,
                        bottom_y,
                        x + bottom_cell_width,
                        self.height - self.padding,
                    ),
                )
            )


class HeroCornerTR(Layout):
    """2x2 hero in top-right corner.

    ┌───┬──────┐
    │ 0 │      │
    ├───┤  1   │
    │ 2 │      │
    ├───┴┬──┬──┤
    │ 3  │4 │5 │
    └────┴──┴──┘

    Slots 0, 2: Stacked left column
    Slot 1: Hero (top-right, 2x2)
    Slots 3-5: Bottom row (3 equal)
    """

    LAYOUT_TYPE: ClassVar[str] = "hero_corner_tr"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize corner hero top-right layout."""
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate slot rectangles."""
        self.slots = []

        available_width, available_height = self._available_space()

        # Hero takes 2/3 width, 2/3 height
        hero_width = int((available_width - self.gap) * 0.67)
        hero_height = int((available_height - self.gap) * 0.67)

        # Side column
        side_width = available_width - hero_width - self.gap
        side_height = (hero_height - self.gap) // 2

        # Bottom row
        bottom_y = self.padding + hero_height + self.gap
        bottom_cell_width = (available_width - 2 * self.gap) // 3

        # Slot 0: Top-left
        self.slots.append(
            Slot(
                index=0,
                rect=(
                    self.padding,
                    self.padding,
                    self.padding + side_width,
                    self.padding + side_height,
                ),
            )
        )

        # Slot 1: Hero (top-right)
        hero_x = self.padding + side_width + self.gap
        self.slots.append(
            Slot(
                index=1,
                rect=(
                    hero_x,
                    self.padding,
                    self.width - self.padding,
                    self.padding + hero_height,
                ),
            )
        )

        # Slot 2: Mid-left
        self.slots.append(
            Slot(
                index=2,
                rect=(
                    self.padding,
                    self.padding + side_height + self.gap,
                    self.padding + side_width,
                    self.padding + hero_height,
                ),
            )
        )

        # Slots 3-5: Bottom row
        for i in range(3):
            x = self.padding + i * (bottom_cell_width + self.gap)
            self.slots.append(
                Slot(
                    index=i + 3,
                    rect=(
                        x,
                        bottom_y,
                        x + bottom_cell_width,
                        self.height - self.padding,
                    ),
                )
            )


class HeroCornerBL(Layout):
    """2x2 hero in bottom-left corner.

    ┌───┬──┬───┐
    │ 0 │1 │ 2 │
    ├───┴┬─┴───┤
    │    │  3  │
    │ 4  ├─────┤
    │    │  5  │
    └────┴─────┘

    Slots 0-2: Top row (3 equal)
    Slots 3, 5: Stacked right column
    Slot 4: Hero (bottom-left, 2x2)
    """

    LAYOUT_TYPE: ClassVar[str] = "hero_corner_bl"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize corner hero bottom-left layout."""
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate slot rectangles."""
        self.slots = []

        available_width, available_height = self._available_space()

        # Hero takes 2/3 width, 2/3 height
        hero_width = int((available_width - self.gap) * 0.67)
        hero_height = int((available_height - self.gap) * 0.67)

        # Top row
        top_height = available_height - hero_height - self.gap
        top_cell_width = (available_width - 2 * self.gap) // 3

        # Side column height
        side_height = (hero_height - self.gap) // 2

        hero_y = self.padding + top_height + self.gap

        # Slots 0-2: Top row
        for i in range(3):
            x = self.padding + i * (top_cell_width + self.gap)
            self.slots.append(
                Slot(
                    index=i,
                    rect=(
                        x,
                        self.padding,
                        x + top_cell_width,
                        self.padding + top_height,
                    ),
                )
            )

        # Slot 3: Top-right of bottom section
        side_x = self.padding + hero_width + self.gap
        self.slots.append(
            Slot(
                index=3,
                rect=(
                    side_x,
                    hero_y,
                    self.width - self.padding,
                    hero_y + side_height,
                ),
            )
        )

        # Slot 4: Hero (bottom-left)
        self.slots.append(
            Slot(
                index=4,
                rect=(
                    self.padding,
                    hero_y,
                    self.padding + hero_width,
                    self.height - self.padding,
                ),
            )
        )

        # Slot 5: Bottom-right of bottom section
        self.slots.append(
            Slot(
                index=5,
                rect=(
                    side_x,
                    hero_y + side_height + self.gap,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            )
        )


class HeroCornerBR(Layout):
    """2x2 hero in bottom-right corner.

    ┌───┬──┬───┐
    │ 0 │1 │ 2 │
    ├───┴─┬────┤
    │  3  │    │
    ├─────┤ 4  │
    │  5  │    │
    └─────┴────┘

    Slots 0-2: Top row (3 equal)
    Slots 3, 5: Stacked left column
    Slot 4: Hero (bottom-right, 2x2)
    """

    LAYOUT_TYPE: ClassVar[str] = "hero_corner_br"
    SLOT_COUNT: ClassVar[int] = 6

    def __init__(self, padding: int = 8, gap: int = 8) -> None:
        """Initialize corner hero bottom-right layout."""
        super().__init__(padding=padding, gap=gap)

    def _calculate_slots(self) -> None:
        """Calculate slot rectangles."""
        self.slots = []

        available_width, available_height = self._available_space()

        # Hero takes 2/3 width, 2/3 height
        hero_width = int((available_width - self.gap) * 0.67)
        hero_height = int((available_height - self.gap) * 0.67)

        # Top row
        top_height = available_height - hero_height - self.gap
        top_cell_width = (available_width - 2 * self.gap) // 3

        # Side column
        side_width = available_width - hero_width - self.gap
        side_height = (hero_height - self.gap) // 2

        hero_y = self.padding + top_height + self.gap
        hero_x = self.padding + side_width + self.gap

        # Slots 0-2: Top row
        for i in range(3):
            x = self.padding + i * (top_cell_width + self.gap)
            self.slots.append(
                Slot(
                    index=i,
                    rect=(
                        x,
                        self.padding,
                        x + top_cell_width,
                        self.padding + top_height,
                    ),
                )
            )

        # Slot 3: Top-left of bottom section
        self.slots.append(
            Slot(
                index=3,
                rect=(
                    self.padding,
                    hero_y,
                    self.padding + side_width,
                    hero_y + side_height,
                ),
            )
        )

        # Slot 4: Hero (bottom-right)
        self.slots.append(
            Slot(
                index=4,
                rect=(
                    hero_x,
                    hero_y,
                    self.width - self.padding,
                    self.height - self.padding,
                ),
            )
        )

        # Slot 5: Bottom-left of bottom section
        self.slots.append(
            Slot(
                index=5,
                rect=(
                    self.padding,
                    hero_y + side_height + self.gap,
                    self.padding + side_width,
                    self.height - self.padding,
                ),
            )
        )
