"""Corner hero layouts — 2x2 hero in one corner, surrounded by 5 smaller cells.

The four corner variants share the same geometry; they differ only in which
corner holds the hero and how the slot indices map onto the rects.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from .base import Layout, Slot

Corner = Literal["tl", "tr", "bl", "br"]


class _CornerHeroLayout(Layout):
    """2x2 hero in one corner, 2-cell side column, 3-cell row on the opposite edge.

    Subclasses set ``CORNER`` and ``SLOT_ORDER``: a 6-tuple mapping the rect
    role → public slot index. Roles, in calculation order:

      0. hero (2x2 in the named corner)
      1. side-near (top of the 2-cell side column)
      2. side-far (bottom of the 2-cell side column)
      3. row-0 (leftmost of the 3-cell row on the opposite edge)
      4. row-1 (middle)
      5. row-2 (rightmost)
    """

    CORNER: ClassVar[Corner]
    SLOT_ORDER: ClassVar[tuple[int, int, int, int, int, int]]

    def _calculate_slots(self) -> None:
        self.slots = []
        aw, ah = self._available_space()

        hero_w = int((aw - self.gap) * 0.67)
        hero_h = int((ah - self.gap) * 0.67)
        side_w = aw - hero_w - self.gap
        side_h_cell = (hero_h - self.gap) // 2
        row_h = ah - hero_h - self.gap
        row_w_cell = (aw - 2 * self.gap) // 3

        is_top = self.CORNER in ("tl", "tr")
        is_left = self.CORNER in ("tl", "bl")

        # Vertical bands
        if is_top:
            hero_y_top = self.padding
            hero_y_bot = self.padding + hero_h
            row_y_top = self.padding + hero_h + self.gap
            row_y_bot = self.height - self.padding
        else:
            row_y_top = self.padding
            row_y_bot = self.padding + row_h
            hero_y_top = self.padding + row_h + self.gap
            hero_y_bot = self.height - self.padding

        # Horizontal bands within the hero band
        if is_left:
            hero_x_left = self.padding
            hero_x_right = self.padding + hero_w
            side_x_left = self.padding + hero_w + self.gap
            side_x_right = self.width - self.padding
        else:
            side_x_left = self.padding
            side_x_right = self.padding + side_w
            hero_x_left = self.padding + side_w + self.gap
            hero_x_right = self.width - self.padding

        rects: list[tuple[int, int, int, int]] = []
        # 0 hero
        rects.append((hero_x_left, hero_y_top, hero_x_right, hero_y_bot))
        # 1 side-near (upper of 2-cell side column)
        rects.append((side_x_left, hero_y_top, side_x_right, hero_y_top + side_h_cell))
        # 2 side-far (lower of 2-cell side column)
        rects.append((side_x_left, hero_y_top + side_h_cell + self.gap, side_x_right, hero_y_bot))
        # 3,4,5 row across opposite edge
        for i in range(3):
            x = self.padding + i * (row_w_cell + self.gap)
            rects.append((x, row_y_top, x + row_w_cell, row_y_bot))

        # Map roles → public indices
        for role_idx, public_idx in enumerate(self.SLOT_ORDER):
            self.slots.append(Slot(index=public_idx, rect=rects[role_idx]))
        self.slots.sort(key=lambda s: s.index)


class HeroCornerTL(_CornerHeroLayout):
    """2x2 hero in top-left corner.

    ┌──────┬───┐
    │      │ 1 │
    │  0   ├───┤
    │      │ 2 │
    ├──┬──┬┴───┤
    │3 │4 │ 5  │
    └──┴──┴────┘
    """

    CORNER = "tl"
    SLOT_ORDER = (0, 1, 2, 3, 4, 5)


class HeroCornerTR(_CornerHeroLayout):
    """2x2 hero in top-right corner.

    ┌───┬──────┐
    │ 0 │      │
    ├───┤  1   │
    │ 2 │      │
    ├───┴┬──┬──┤
    │ 3  │4 │5 │
    └────┴──┴──┘
    """

    CORNER = "tr"
    SLOT_ORDER = (1, 0, 2, 3, 4, 5)


class HeroCornerBL(_CornerHeroLayout):
    """2x2 hero in bottom-left corner.

    ┌───┬──┬───┐
    │ 0 │1 │ 2 │
    ├───┴┬─┴───┤
    │    │  3  │
    │ 4  ├─────┤
    │    │  5  │
    └────┴─────┘
    """

    CORNER = "bl"
    SLOT_ORDER = (4, 3, 5, 0, 1, 2)


class HeroCornerBR(_CornerHeroLayout):
    """2x2 hero in bottom-right corner.

    ┌───┬──┬───┐
    │ 0 │1 │ 2 │
    ├───┴─┬────┤
    │  3  │    │
    ├─────┤ 4  │
    │  5  │    │
    └─────┴────┘
    """

    CORNER = "br"
    SLOT_ORDER = (4, 3, 5, 0, 1, 2)
