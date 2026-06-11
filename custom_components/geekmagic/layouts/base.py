"""Base layout class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image
from PIL import ImageDraw as PILImageDraw

from ..const import DISPLAY_HEIGHT, DISPLAY_WIDTH
from ..render_context import RenderContext
from ..widgets.components import Component
from ..widgets.state import WidgetState
from ..widgets.theme import DEFAULT_THEME, Theme

if TYPE_CHECKING:
    from PIL import ImageDraw

    from ..renderer import Renderer
    from ..widgets.base import Widget


@dataclass
class Slot:
    """Represents a widget slot in a layout."""

    index: int
    rect: tuple[int, int, int, int]  # x1, y1, x2, y2
    widget: Widget | None = None


class Layout(ABC):
    """Base class for display layouts."""

    def __init__(self, padding: int | None = None, gap: int | None = None) -> None:
        """Initialize the layout.

        Args:
            padding: Padding around the edges. When ``None`` (default),
                ``self.padding`` resolves to the active theme's
                ``layout_padding`` at access time, so changing the theme
                via ``layout.theme = ...`` automatically updates spacing.
                Passing an explicit value pins it and ignores the theme.
            gap: Gap between widgets. Same semantics as ``padding``.
        """
        self._padding_override = padding
        self._gap_override = gap
        self._theme: Theme = DEFAULT_THEME
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self.slots: list[Slot] = []
        self._calculate_slots()

    @property
    def padding(self) -> int:
        """Outer padding — explicit override or theme default."""
        return (
            self._padding_override
            if self._padding_override is not None
            else self._theme.layout_padding
        )

    @property
    def gap(self) -> int:
        """Inter-widget gap — explicit override or theme default."""
        return self._gap_override if self._gap_override is not None else self._theme.gap

    @property
    def theme(self) -> Theme:
        """Active theme."""
        return self._theme

    @theme.setter
    def theme(self, value: Theme) -> None:
        """Set the active theme and rebuild slots so theme-driven padding/gap
        actually take effect (e.g. retro/soft/candy ship larger padding=8)."""
        self._theme = value
        # Recompute slot rectangles with the new theme's padding/gap, but
        # preserve any widgets already placed in those slots.
        existing_widgets = [slot.widget for slot in self.slots]
        self._calculate_slots()
        for i, widget in enumerate(existing_widgets):
            if widget is not None and i < len(self.slots):
                self.slots[i].widget = widget

    @abstractmethod
    def _calculate_slots(self) -> None:
        """Calculate the slot rectangles. Override in subclasses."""

    def _available_space(self) -> tuple[int, int]:
        """Calculate available width and height after padding.

        Returns:
            Tuple of (available_width, available_height)
        """
        return (
            self.width - 2 * self.padding,
            self.height - 2 * self.padding,
        )

    def _grid_cell_size(self, rows: int, cols: int) -> tuple[int, int]:
        """Calculate cell size for a grid layout.

        Args:
            rows: Number of rows
            cols: Number of columns

        Returns:
            Tuple of (cell_width, cell_height)
        """
        aw, ah = self._available_space()
        return (
            (aw - (cols - 1) * self.gap) // cols,
            (ah - (rows - 1) * self.gap) // rows,
        )

    def _split_dimension(self, total: int, ratio: float) -> tuple[int, int]:
        """Split a dimension by ratio, accounting for gap.

        Args:
            total: Total available dimension (excluding gap)
            ratio: Ratio for first section (0.0-1.0)

        Returns:
            Tuple of (first_size, second_size)
        """
        content = total - self.gap
        first = int(content * ratio)
        second = content - first
        return first, second

    def get_slot_count(self) -> int:
        """Return the number of widget slots."""
        return len(self.slots)

    def get_slot(self, index: int) -> Slot | None:
        """Get a slot by index."""
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def set_widget(self, index: int, widget: Widget) -> None:
        """Set a widget in a slot.

        Args:
            index: Slot index
            widget: Widget to place
        """
        if 0 <= index < len(self.slots):
            self.slots[index].widget = widget

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        widget_states: dict[int, WidgetState] | None = None,
    ) -> None:
        """Render all widgets in the layout with clipping.

        Each widget is rendered to a temporary image first, then pasted
        onto the main canvas. This ensures widgets cannot overflow their
        slot boundaries.

        Args:
            renderer: Renderer instance
            draw: ImageDraw instance
            widget_states: Dict mapping slot index to WidgetState for each widget
        """
        # Get the main canvas from the draw object
        canvas = draw._image  # noqa: SLF001
        scale = renderer.scale

        # Paint the canvas with the theme background so widgets gaps and
        # uncovered areas use the correct color (not black-by-default).
        draw.rectangle((0, 0, canvas.width, canvas.height), fill=self.theme.background)

        # Default empty states dict
        if widget_states is None:
            widget_states = {}

        # Pass 1: render every slot, recording the size each hero value
        # actually used (continuous_fit Texts report through the ctx).
        rendered: dict[int, Image.Image] = {}
        hero_sizes: dict[int, int] = {}
        groups: dict[tuple[str, int, int], list[Slot]] = {}
        for slot in self.slots:
            widget = slot.widget
            if widget is None:
                continue
            state = widget_states.get(slot.index, WidgetState())
            recorder: list[int] = []
            rendered[slot.index] = self._render_slot(renderer, slot, widget, state, recorder)
            if recorder:
                hero_sizes[slot.index] = min(recorder)
                x1, y1, x2, y2 = slot.rect
                widget_type = getattr(getattr(widget, "config", None), "widget_type", None)
                if widget_type:
                    groups.setdefault((widget_type, x2 - x1, y2 - y1), []).append(slot)

        # Pass 2: same-type widgets in identically sized cells share one
        # hero size — re-render the larger ones capped to the group
        # minimum so "22°C" doesn't tower over a neighbouring "23.5°C".
        for slots in groups.values():
            if len(slots) < 2:
                continue
            cap = min(hero_sizes[s.index] for s in slots)
            for slot in slots:
                own = hero_sizes[slot.index]
                if own <= cap or slot.widget is None:
                    continue
                # Guard against extreme spreads: matching "10:30" to a
                # neighbouring "10:30:00 AM" would shrink it to a sliver.
                # Below 60% of its natural size, a hero keeps its own scale.
                if cap < own * 0.6:
                    continue
                state = widget_states.get(slot.index, WidgetState())
                rendered[slot.index] = self._render_slot(
                    renderer, slot, slot.widget, state, hero_cap=cap
                )

        for slot in self.slots:
            temp_img = rendered.get(slot.index)
            if temp_img is None:
                continue
            x1, y1, _x2, _y2 = slot.rect
            canvas.paste(temp_img, (x1 * scale, y1 * scale))

        # Apply theme visual effects after all widgets are rendered
        self._apply_theme_effects(canvas, scale)

    def _render_slot(
        self,
        renderer: Renderer,
        slot: Slot,
        widget: Widget,
        state: WidgetState,
        hero_recorder: list[int] | None = None,
        hero_cap: int | None = None,
    ) -> Image.Image:
        """Render one widget into a fresh slot-sized image (clipping)."""
        scale = renderer.scale
        x1, y1, x2, y2 = slot.rect
        slot_width = (x2 - x1) * scale
        slot_height = (y2 - y1) * scale

        # When the theme uses surface chrome, paint the slot with a
        # rounded card on top of the canvas background. Otherwise the
        # slot background matches the canvas — widgets float on the
        # background (watchOS deference principle).
        temp_img = Image.new("RGB", (slot_width, slot_height), self.theme.background)
        temp_draw = PILImageDraw.Draw(temp_img)
        if self.theme.surface_chrome:
            # Draw the rounded card chrome first; widgets render on top.
            radius = max(0, self.theme.corner_radius * scale)
            outline = self.theme.border if self.theme.border_width > 0 else None
            temp_draw.rounded_rectangle(
                (0, 0, slot_width - 1, slot_height - 1),
                radius=radius,
                fill=self.theme.surface,
                outline=outline,
                width=max(1, self.theme.border_width * scale) if outline else 1,
            )

        # Create render context with local coordinates (0, 0 to width, height)
        # The rect is relative to the temp image, not the main canvas
        local_rect = (0, 0, x2 - x1, y2 - y1)
        ctx = RenderContext(
            temp_draw,
            local_rect,
            renderer,
            theme=self.theme,
            # Per-widget "Text Size" option (issue #31). getattr keeps
            # widget test doubles without the attribute working.
            font_adjust=getattr(widget, "size_adjust", 0),
        )
        ctx.hero_size_recorder = hero_recorder
        ctx.hero_size_cap = hero_cap

        # Call widget render - returns Component tree
        result = widget.render(ctx, state)

        # Render the Component tree
        if isinstance(result, Component):
            result.render(ctx, 0, 0, x2 - x1, y2 - y1)

        return temp_img

    def _apply_theme_effects(self, canvas: Image.Image, scale: int) -> None:
        """Apply theme-specific visual effects to the rendered canvas.

        Args:
            canvas: The rendered canvas image
            scale: Supersampling scale factor
        """
        if self.theme.scanlines:
            self._apply_scanlines(canvas, scale)

    def _apply_scanlines(self, canvas: Image.Image, scale: int) -> None:
        """Apply retro scanline effect to the canvas.

        Creates horizontal lines that darken every Nth row for a CRT-like effect.

        Args:
            canvas: The canvas image to modify (in-place)
            scale: Supersampling scale factor
        """
        # Scanlines every 3 scaled pixels (6 pixels at 2x scale)
        line_spacing = 3 * scale
        darkness_factor = 0.7

        # Use PIL pixel access for in-place modification
        pixels = canvas.load()
        if pixels is None:
            return

        for y in range(0, canvas.height, line_spacing):
            for x in range(canvas.width):
                pixel = pixels[x, y]
                if isinstance(pixel, tuple) and len(pixel) >= 3:
                    r, g, b = pixel[0], pixel[1], pixel[2]
                    pixels[x, y] = (
                        int(r * darkness_factor),
                        int(g * darkness_factor),
                        int(b * darkness_factor),
                    )

    def get_all_entities(self) -> list[str]:
        """Get all entity IDs from all widgets."""
        entities = []
        for slot in self.slots:
            if slot.widget is not None:
                entities.extend(slot.widget.get_entities())
        return entities
