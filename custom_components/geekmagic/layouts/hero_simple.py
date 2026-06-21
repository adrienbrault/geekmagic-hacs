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
        background_image: str | None = None,
        background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0,
    ) -> None:
        """Initialize simple hero layout.

        Args:
            hero_ratio: Ratio of hero height to total height
            padding: Padding around edges
            gap: Gap between widgets
            background_image: Optional path to a local background image
            background_mode: How to fit the image: stretch, contain, cover
        """
        super().__init__(footer_slots=1, hero_ratio=hero_ratio, padding=padding, gap=gap, background_image=background_image, background_mode=background_mode, widget_contrast=widget_contrast, text_scale=text_scale, text_opacity=text_opacity)
