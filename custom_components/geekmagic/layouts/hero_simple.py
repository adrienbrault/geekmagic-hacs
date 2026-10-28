"""Hero Simple layout — large hero (top 2/3) and a single footer (bottom 1/3).

Equivalent to ``HeroLayout(footer_slots=1)`` with a slightly smaller default
hero_ratio (0.66 vs 0.7); kept as its own class for the coordinator's layout
registry.
"""

from __future__ import annotations

from .hero import HeroLayout


class HeroSimpleLayout(HeroLayout):
    """Hero (slot 0) + single footer (slot 1)."""

    def __init__(
        self,
        hero_ratio: float = 0.66,
        padding: int | None = None,
        gap: int | None = None,
    ) -> None:
        super().__init__(footer_slots=1, hero_ratio=hero_ratio, padding=padding, gap=gap)
