"""Base layout class.

Layouts compute slot rectangles (pure geometry); rendering happens
engine-side in one ``render_layers`` call per screen (or per animation
frame):

1. fullscreen theme backdrop
2. per-slot widget cells (transparent background, clipped to their rects)
3. optional fullscreen theme overlay (scanlines, vignettes)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..const import DISPLAY_HEIGHT, DISPLAY_WIDTH
from ..htmldoc import (
    HAS_ENGINE,
    CellContext,
    build_cell_document,
    build_fullscreen_document,
    render_layers_image,
)
from ..widgets.state import WidgetState
from ..widgets.theme import DEFAULT_THEME, Theme

if TYPE_CHECKING:
    from PIL import Image, ImageDraw

    from ..renderer import Renderer
    from ..widgets.base import Widget

_LOGGER = logging.getLogger(__name__)

_ERROR_FRAGMENT = '<div class="cell"><div class="t-label">WIDGET ERROR</div></div>'

# Glow underlay for themes that opt in (neon): each cell is painted
# once blurred beneath its sharp pass, the classic phosphor-bloom look.
# Blur is in device px at scale 1 (multiplied by the render scale).
_GLOW_BLUR_PX = 3.5
_GLOW_OPACITY = 0.55

# Sibling harmony: a cell keeps at least this share of its own fitted
# hero size when a smaller sibling asks it to shrink (see _hero_caps).
_HARMONY_FLOOR = 0.5
# In groups of three or more, a smallest fit under this share of the
# next one is an outlier and exempt from harmony.
_HARMONY_OUTLIER = 0.8


def _css_hex(color: tuple[int, int, int]) -> str:
    """RGB tuple as a #rrggbb hex string (render_layers background)."""
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


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

    def _hero_caps(self, widget_states: dict[int, WidgetState]) -> dict[int, float]:
        """Per-slot hero size caps that make sibling cells agree.

        Equal-sized cells whose widgets report a hero of the same kind
        are capped to the smallest size among them, so "On" beside
        "Locked" and "23.5°C" beside "58%" render at one size — the
        consistency a designed grid has and per-cell fitting lacks. A
        cell never gives up more than half its own size to a sibling: one
        very long value must not shrink the whole row to a whisper.
        """
        theme = self.theme
        groups: dict[tuple[int, int, str], list[tuple[int, float]]] = {}
        for slot in self.slots:
            widget = slot.widget
            if widget is None:
                continue
            x1, y1, x2, y2 = slot.rect
            ctx = CellContext(width=x2 - x1, height=y2 - y1, slot_index=slot.index, theme=theme)
            try:
                hint = widget.hero_hint(ctx, widget_states.get(slot.index, WidgetState()))
            except Exception:  # pragma: no cover - a broken widget renders its error later
                hint = None
            if hint is None:
                continue
            kind, px = hint
            groups.setdefault((x2 - x1, y2 - y1, kind), []).append((slot.index, px))
        caps: dict[int, float] = {}
        for members in groups.values():
            if len(members) < 2:
                continue
            sizes = sorted(px for _, px in members)
            # One outlier is allowed: a single value much wider than its
            # siblings ("18.5kWh" beside "2.4kW") keeps its own size
            # rather than shrinking the whole grid to it. The rest agree
            # on the next-smallest fit.
            common = sizes[0]
            if len(sizes) >= 3 and sizes[0] < _HARMONY_OUTLIER * sizes[1]:
                common = sizes[1]
            for index, px in members:
                if px < common:
                    continue  # the outlier fits its own size
                caps[index] = max(common, _HARMONY_FLOOR * px)
        return caps

    def _cell_documents(
        self, widget_states: dict[int, WidgetState]
    ) -> list[tuple[Slot, str, bool]]:
        """(slot, cell document, animated) for every placed widget."""
        theme = self.theme
        caps = self._hero_caps(widget_states)
        cells: list[tuple[Slot, str, bool]] = []
        for slot in self.slots:
            widget = slot.widget
            if widget is None:
                continue
            x1, y1, x2, y2 = slot.rect
            ctx = CellContext(width=x2 - x1, height=y2 - y1, slot_index=slot.index, theme=theme)
            if slot.index in caps:
                ctx.extra["hero_px_cap"] = caps[slot.index]
            state = widget_states.get(slot.index, WidgetState())
            try:
                fragment = widget.render_html(ctx, state)
            except Exception:
                _LOGGER.exception("Widget %s failed to render", type(widget).__name__)
                fragment = _ERROR_FRAGMENT
            cells.append((slot, build_cell_document(fragment, theme), widget.is_animated()))
        return cells

    def _layer_specs(
        self,
        cells: list[tuple[Slot, str, bool]],
        scale: float,
        *,
        with_overlay: bool = True,
    ) -> list[dict]:
        """Layer list for ``render_layers``: backdrop, cells, overlay.

        Cell layers are clipped to their rects by the engine — the same
        containment the per-cell rasters used to provide. Glow themes
        paint each cell once blurred beneath its sharp pass.
        ``with_overlay=False`` leaves the theme overlay off (the animated
        path composites it above per-frame cells instead).
        """
        theme = self.theme
        backdrop_css = theme.backdrop_css or "body { background: var(--bg); }"
        layers: list[dict] = [
            {
                "html": build_fullscreen_document(theme, backdrop_css),
                "width": self.width,
                "height": self.height,
                "scale": scale,
            }
        ]
        for slot, document, animated in cells:
            x1, y1, x2, y2 = slot.rect
            # "_animated" marks layers render_animation must clock per
            # frame; it is stripped before reaching the engine.
            spec = {
                "html": document,
                "width": x2 - x1,
                "height": y2 - y1,
                "x": x1 * scale,
                "y": y1 * scale,
                "scale": scale,
                "_animated": animated,
            }
            if theme.glow_effect:
                layers.append({**spec, "blur": _GLOW_BLUR_PX * scale, "opacity": _GLOW_OPACITY})
            layers.append(spec)
        if with_overlay and theme.overlay_css:
            layers.append(
                {
                    "html": build_fullscreen_document(theme, theme.overlay_css),
                    "width": self.width,
                    "height": self.height,
                    "scale": scale,
                }
            )
        return layers

    def render(
        self,
        renderer: Renderer,
        draw: ImageDraw.ImageDraw,
        widget_states: dict[int, WidgetState] | None = None,
    ) -> None:
        """Render the screen through the Blitz pipeline.

        The whole screen — theme backdrop, widget cells at their slot
        rects, optional overlay — is composited engine-side in one
        ``render_layers`` call. A missing or too-old engine paints the
        install-hint screen instead (manifest.json pins the version, so
        this only happens on broken installs).

        Args:
            renderer: Renderer instance (canvas scale + encoding)
            draw: ImageDraw whose underlying image is the target canvas
            widget_states: Dict mapping slot index to WidgetState
        """
        canvas = draw._image  # noqa: SLF001
        scale = renderer.scale
        theme = self.theme

        if not HAS_ENGINE:
            self._render_missing_blitz(canvas, draw)
            return

        if widget_states is None:
            widget_states = {}
        cells = self._cell_documents(widget_states)

        layers = [
            {k: v for k, v in spec.items() if not k.startswith("_")}
            for spec in self._layer_specs(cells, scale)
        ]
        surface = render_layers_image(
            layers,
            self.width * scale,
            self.height * scale,
            background=_css_hex(theme.background),
        )
        if surface is not None:
            canvas.paste(surface, (0, 0))
        else:
            # Engine failure is logged by render_layers_image; keep the
            # canvas on the theme background rather than uploading noise.
            draw.rectangle((0, 0, canvas.width, canvas.height), fill=theme.background)

    def has_animated_widgets(self) -> bool:
        """True when any placed widget opted into animation."""
        return any(slot.widget is not None and slot.widget.is_animated() for slot in self.slots)

    def render_animation(
        self,
        renderer: Renderer,
        widget_states: dict[int, WidgetState] | None = None,
        times: list[float] | None = None,
    ) -> list[Image.Image] | None:
        """Render the screen at several animation timestamps.

        Static passes (backdrop, non-animated cells) render once and are
        shared across frames engine-side. Returns one supersampled RGB
        canvas per timestamp (encode with :meth:`Renderer.to_gif`), or
        None when the engine is unavailable or a frame fails — callers
        fall back to the still pipeline.
        """
        if not HAS_ENGINE or not times:
            return None
        if widget_states is None:
            widget_states = {}
        scale = renderer.scale
        theme = self.theme
        cells = self._cell_documents(widget_states)

        # One layered call per frame: animated layers (and their glow
        # underlays) get the frame's clock, static layers render
        # identically each time, and the overlay composites in the same
        # call.
        specs = self._layer_specs(cells, scale)
        canvases: list[Image.Image] = []
        for t in times:
            layers = []
            for spec in specs:
                layer = {k: v for k, v in spec.items() if not k.startswith("_")}
                if spec.get("_animated"):
                    layer["time"] = t
                layers.append(layer)
            surface = render_layers_image(
                layers,
                self.width * scale,
                self.height * scale,
                background=_css_hex(theme.background),
            )
            if surface is None:
                return None
            canvases.append(surface)
        return canvases

    def _render_missing_blitz(self, canvas: Image.Image, draw: ImageDraw.ImageDraw) -> None:
        """Paint an instructive error screen when blitz-py is missing/old."""
        draw.rectangle((0, 0, canvas.width, canvas.height), fill=(0, 0, 0))
        message = "blitz-py >= 0.4.2 required\npip install -U blitz-py"
        draw.text(
            (canvas.width // 2, canvas.height // 2),
            message,
            fill=(255, 159, 10),
            anchor="mm",
            align="center",
        )

    def get_all_entities(self) -> list[str]:
        """Get all entity IDs from all widgets."""
        entities = []
        for slot in self.slots:
            if slot.widget is not None:
                entities.extend(slot.widget.get_entities())
        return entities
