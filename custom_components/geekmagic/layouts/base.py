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
    rect: tuple[int, int, int]  # x1, y1, x2, y2
    widget: Widget | None = None


class Layout(ABC):
    """Base class for display layouts."""

    def __init__(
        self,
        padding: int | None = None,
        gap: int | None = None,
        background_image: str | None = None,
        background_mode: str = "stretch",
        widget_contrast: float = 0.0,
        text_scale: float = 1.0,
        text_opacity: float = 1.0,
    ) -> None:
        """Initialize the layout.

        Args:
            padding: Padding around the edges. When ``None`` (default),
                ``self.padding`` resolves to the active theme's
                ``layout_padding`` at access time, so changing the theme
                via ``layout.theme = ...`` automatically updates spacing.
                Passing an explicit value pins it and ignores the theme.
            gap: Gap between widgets. Same semantics as ``padding``.
            background_image: Optional path to a local background image.
            background_mode: How to fit the image: "stretch", "contain", "cover".
            widget_contrast: Opacity of a dark contrast panel behind each widget
                (0.0 = transparent, 1.0 = solid). Improves readability on
                busy background images.
            text_scale: Extra scaling factor for text and icons.
            text_opacity: Opacity multiplier for text/icon colors (0..1).
        """
        self._padding_override = padding
        self._gap_override = gap
        self.background_image = background_image
        self.background_mode = background_mode
        self.widget_contrast = widget_contrast
        self.text_scale = text_scale
        self.text_opacity = text_opacity
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

    def _render_background_image(
        self,
        canvas_size: tuple[int, int],
    ) -> Image.Image | None:
        """Load and fit the configured background image into an RGBA canvas.

        Returns None when no image is configured or loading fails.
        """
        if not self.background_image:
            return None
        try:
            bg = Image.open(self.background_image).convert("RGBA")
            canvas_width, canvas_height = canvas_size
            src_ratio = bg.width / bg.height
            dest_ratio = canvas_width / canvas_height

            if self.background_mode == "contain":
                if src_ratio > dest_ratio:
                    new_width = canvas_width
                    new_height = int(canvas_width / src_ratio)
                else:
                    new_height = canvas_height
                    new_width = int(canvas_height * src_ratio)
                bg = bg.resize((new_width, new_height), Image.Resampling.LANCZOS)
                paste_x = (canvas_width - new_width) // 2
                paste_y = (canvas_height - new_height) // 2
                target = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 255))
                target.paste(bg, (paste_x, paste_y), bg)
                return target

            if self.background_mode == "cover":
                if src_ratio > dest_ratio:
                    new_height = canvas_height
                    new_width = int(canvas_height * src_ratio)
                else:
                    new_width = canvas_width
                    new_height = int(canvas_width * src_ratio)
                bg = bg.resize((new_width, new_height), Image.Resampling.LANCZOS)
                left = (new_width - canvas_width) // 2
                top = (new_height - canvas_height) // 2
                cropped = bg.crop((left, top, left + canvas_width, top + canvas_height))
                target = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 255))
                target.paste(cropped, (0, 0), cropped)
                return target

            # stretch (default)
            bg = bg.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            return bg
        except Exception:
            return None

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

        # Prepare the background. When a background image is configured and
        # loads successfully, widgets will be composited transparently on top.
        rgba_canvas = self._render_background_image(canvas.size)
        use_background_image = rgba_canvas is not None

        if not use_background_image:
            draw.rectangle((0, 0, canvas.width, canvas.height), fill=self.theme.background)

        # Default empty states dict
        if widget_states is None:
            widget_states = {}

        if use_background_image:
            # Use an internal transparent composition canvas. The widgets are
            # rendered here with alpha and then flattened onto the caller's RGB
            # canvas, so the caller still sees a normal RGB image.
            for slot in self.slots:
                widget = slot.widget
                if widget is None:
                    continue

                x1, y1, x2, y2 = slot.rect
                slot_width = (x2 - x1) * scale
                slot_height = (y2 - y1) * scale

                temp_img = Image.new("RGBA", (slot_width, slot_height), (0, 0, 0, 0))
                temp_draw = PILImageDraw.Draw(temp_img)

                paste_x = x1 * scale
                paste_y = y1 * scale

                # Optionally draw a semi-transparent contrast backdrop behind
                # the widget content to keep text readable on busy photos.
                contrast = max(0.0, min(1.0, self.widget_contrast))
                if contrast > 0:
                    bg_color = self.theme.background
                    overlay = Image.new(
                        "RGBA",
                        (slot_width, slot_height),
                        (bg_color[0], bg_color[1], bg_color[2], int(255 * contrast)),
                    )
                    temp_img = Image.alpha_composite(temp_img, overlay)
                    temp_draw = PILImageDraw.Draw(temp_img)

                local_rect = (0, 0, x2 - x1, y2 - y1)
                widget_text_scale = getattr(slot.widget.config, "text_scale", 1.0) or 1.0
                ctx = RenderContext(
                    temp_draw,
                    local_rect,
                    renderer,
                    theme=self.theme,
                    transparent_background=True,
                    text_scale=self.text_scale * widget_text_scale,
                    text_opacity=self.text_opacity,
                )

                state = widget_states.get(slot.index, WidgetState())
                result = widget.render(ctx, state)
                if isinstance(result, Component):
                    result.render(ctx, 0, 0, x2 - x1, y2 - y1)

                rgba_canvas.paste(temp_img, (paste_x, paste_y), temp_img)

            # Flatten the composited RGBA result back onto the original RGB canvas.
            canvas.paste(rgba_canvas.convert("RGB"), (0, 0))
        else:
            for slot in self.slots:
                widget = slot.widget
                if widget is None:
                    continue

                x1, y1, x2, y2 = slot.rect
                slot_width = (x2 - x1) * scale
                slot_height = (y2 - y1) * scale

                temp_img = Image.new("RGB", (slot_width, slot_height), self.theme.background)
                temp_draw = PILImageDraw.Draw(temp_img)
                if self.theme.surface_chrome:
                    radius = max(0, self.theme.corner_radius * scale)
                    outline = self.theme.border if self.theme.border_width > 0 else None
                    temp_draw.rounded_rectangle(
                        (0, 0, slot_width - 1, slot_height - 1),
                        radius=radius,
                        fill=self.theme.surface,
                        outline=outline,
                        width=max(1, self.theme.border_width * scale) if outline else 1,
                    )

                local_rect = (0, 0, x2 - x1, y2 - y1)
                widget_text_scale = getattr(slot.widget.config, "text_scale", 1.0) or 1.0
                ctx = RenderContext(
                    temp_draw,
                    local_rect,
                    renderer,
                    theme=self.theme,
                    transparent_background=False,
                    text_scale=self.text_scale * widget_text_scale,
                    text_opacity=self.text_opacity,
                )

                state = widget_states.get(slot.index, WidgetState())
                result = widget.render(ctx, state)
                if isinstance(result, Component):
                    result.render(ctx, 0, 0, x2 - x1, y2 - y1)

                paste_x = x1 * scale
                paste_y = y1 * scale
                canvas.paste(temp_img, (paste_x, paste_y))

        # Apply theme visual effects after all widgets are rendered
        self._apply_theme_effects(canvas, scale)

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
