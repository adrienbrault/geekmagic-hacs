"""Layout systems for GeekMagic displays."""

from .base import Layout
from .corner_hero import HeroCornerBL, HeroCornerBR, HeroCornerTL, HeroCornerTR
from .fullscreen import FullscreenLayout
from .grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3, GridLayout
from .hero import HeroLayout
from .hero_simple import HeroSimpleLayout
from .sidebar import SidebarLeft, SidebarRight
from .split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitLayout,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)

_ALL_LAYOUTS: list[type[Layout]] = [
    Grid2x2,
    Grid2x3,
    Grid3x2,
    Grid3x3,
    HeroLayout,
    HeroSimpleLayout,
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
    SidebarLeft,
    SidebarRight,
    HeroCornerTL,
    HeroCornerTR,
    HeroCornerBL,
    HeroCornerBR,
    FullscreenLayout,
]

# Built from each layout class's LAYOUT_TYPE attribute
LAYOUT_CLASSES: dict[str, type[Layout]] = {
    cls.LAYOUT_TYPE: cls for cls in _ALL_LAYOUTS if cls.LAYOUT_TYPE
}

# Built from each layout class's SLOT_COUNT attribute
LAYOUT_SLOT_COUNTS: dict[str, int] = {
    cls.LAYOUT_TYPE: cls.SLOT_COUNT for cls in _ALL_LAYOUTS if cls.LAYOUT_TYPE
}

__all__ = [
    "LAYOUT_CLASSES",
    "LAYOUT_SLOT_COUNTS",
    "FullscreenLayout",
    "Grid2x2",
    "Grid2x3",
    "Grid3x2",
    "Grid3x3",
    "GridLayout",
    "HeroCornerBL",
    "HeroCornerBR",
    "HeroCornerTL",
    "HeroCornerTR",
    "HeroLayout",
    "HeroSimpleLayout",
    "Layout",
    "SidebarLeft",
    "SidebarRight",
    "SplitHorizontal",
    "SplitHorizontal1To2",
    "SplitHorizontal2To1",
    "SplitLayout",
    "SplitVertical",
    "ThreeColumnLayout",
    "ThreeRowLayout",
]
