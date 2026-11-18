"""A view, built and painted: the Home-Assistant-free half of a frame.

``frame.py`` fetches what a frame reads from Home Assistant (pictures,
history, forecasts, templates); everything here works on what was
fetched, so tools without Home Assistant (the offline view renderer)
build, assemble and paint a view through the same code as the device:

- ``build_layout``: a view config to a layout with its theme and widgets
- ``assemble_widget_states``: each placed widget's ``WidgetState`` from
  entity states and a ``FrameData`` (``frame.FrameInputs`` is one)
- ``render_still``: the painted frame
- ``render_animated``: the looping GIF of a view with animated widgets

HA-free on purpose, like everything the engine self-test child reaches:
no ``homeassistant`` import, and the engine only through
``engine.get_engine()`` (never at import time).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from PIL import Image as PILImage

from .animation import frame_timing
from .const import (
    CONF_LAYOUT,
    CONF_SCREEN_THEME,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
    LAYOUT_GRID_3X3,
    LAYOUT_HERO,
    LAYOUT_HERO_BL,
    LAYOUT_HERO_BR,
    LAYOUT_HERO_SIMPLE,
    LAYOUT_HERO_TL,
    LAYOUT_HERO_TR,
    LAYOUT_SIDEBAR_LEFT,
    LAYOUT_SIDEBAR_RIGHT,
    LAYOUT_SPLIT_H,
    LAYOUT_SPLIT_H_1_2,
    LAYOUT_SPLIT_H_2_1,
    LAYOUT_SPLIT_V,
    LAYOUT_THREE_COLUMN,
    LAYOUT_THREE_ROW,
    MAX_IMAGE_SIZE,
    SUPERSAMPLE_SCALE,
    THEME_WATCHOS,
)
from .htmldoc import image_data_uri
from .layouts.corner_hero import HeroCornerBL, HeroCornerBR, HeroCornerTL, HeroCornerTR
from .layouts.fullscreen import FullscreenLayout
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from .layouts.hero import HeroLayout
from .layouts.hero_simple import HeroSimpleLayout
from .layouts.sidebar import SidebarLeft, SidebarRight
from .layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from .widgets import build_widget, stored_slot
from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget
from .widgets.chart import ChartWidget
from .widgets.html import HtmlWidget
from .widgets.image import ImageWidget
from .widgets.media import MediaWidget
from .widgets.state import WidgetState, build_entity_states
from .widgets.theme import get_theme
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime

    from PIL import Image

    from .layouts.base import Layout
    from .renderer import Renderer
    from .widgets.base import Widget

LAYOUT_CLASSES: dict[str, type[Layout]] = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT_H: SplitHorizontal,
    LAYOUT_SPLIT_V: SplitVertical,
    LAYOUT_SPLIT_H_1_2: SplitHorizontal1To2,
    LAYOUT_SPLIT_H_2_1: SplitHorizontal2To1,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
    LAYOUT_THREE_ROW: ThreeRowLayout,
    LAYOUT_FULLSCREEN: FullscreenLayout,
    LAYOUT_HERO_SIMPLE: HeroSimpleLayout,
    LAYOUT_SIDEBAR_LEFT: SidebarLeft,
    LAYOUT_SIDEBAR_RIGHT: SidebarRight,
    LAYOUT_HERO_TL: HeroCornerTL,
    LAYOUT_HERO_TR: HeroCornerTR,
    LAYOUT_HERO_BL: HeroCornerBL,
    LAYOUT_HERO_BR: HeroCornerBR,
}

PictureKind = Literal["camera", "media"]


def build_layout(view_config: dict[str, Any]) -> Layout:
    """Build a view's layout, theme and widgets.

    An unknown layout falls back to a 2x2 grid, a view without a theme gets
    the default one, a view without widgets shows a clock, and widgets
    beyond the layout's slots (or of an unknown type) are left out.
    """
    layout_class = LAYOUT_CLASSES.get(view_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2), Grid2x2)
    layout = layout_class()
    layout.theme = get_theme(view_config.get(CONF_SCREEN_THEME, THEME_WATCHOS))

    widgets_config = view_config.get(CONF_WIDGETS, [])
    if not widgets_config:
        widgets_config = [{"type": "clock", "slot": 0}]

    for widget_config in widgets_config:
        slot = stored_slot(widget_config)
        # Unreadable, negative or beyond the layout: not shown (a negative
        # index would land in the LAST slot)
        if slot is None or not 0 <= slot < layout.get_slot_count():
            continue
        widget = build_widget(widget_config)
        if widget is not None:
            layout.set_widget(slot, widget)

    return layout


def layout_widgets(layout: Layout) -> list[Widget]:
    """The widgets placed in a layout, in slot order."""
    return [slot.widget for slot in layout.slots if slot.widget is not None]


def fit_picture(image: Image.Image, rect: tuple[int, int, int, int]) -> Image.Image:
    """A copy of ``image`` no larger than covering the cell ``rect`` needs.

    The cell renders at ``SUPERSAMPLE_SCALE``; the picture keeps enough
    pixels to fill it edge to edge (``object-fit: cover``) at that scale,
    so it never looks softer than a Camera widget's, and nothing more.
    Always a copy: the source may be shared with another widget's state.
    """
    x1, y1, x2, y2 = rect
    width = max(1, x2 - x1) * SUPERSAMPLE_SCALE
    height = max(1, y2 - y1) * SUPERSAMPLE_SCALE
    scale = max(width / image.width, height / image.height)
    if scale >= 1.0:
        return image.copy()
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, PILImage.Resampling.LANCZOS)


def render_still(
    renderer: Renderer, layout: Layout, widget_states: dict[int, WidgetState]
) -> Image.Image:
    """Paint a layout's still frame (blocking: run in the executor)."""
    img, draw = renderer.create_canvas(background=layout.theme.background)
    layout.render(renderer, draw, widget_states)
    return img


@dataclass(frozen=True)
class Animation:
    """A view's animation loop: its supersampled frames and their GIF."""

    frames: list[Image.Image]
    gif: bytes

    @property
    def fits_upload(self) -> bool:
        """Whether the GIF fits the device's upload budget.

        The frame cap bounds typical output but not the encoded byte size:
        high-entropy content can still blow it. Over budget, the first
        frame goes out as a still instead.
        """
        return len(self.gif) <= MAX_IMAGE_SIZE


def render_animated(
    renderer: Renderer,
    layout: Layout,
    widget_states: dict[int, WidgetState],
    rotation: int = 0,
) -> Animation | None:
    """Render a view's animation loop (blocking: run in the executor).

    ``frames[0]`` is the animation at t=0. None when the
    engine failed a frame: callers fall back to the still.
    """
    # The loop is the longest any animated widget asks for (ambient
    # animations want 2-4s; a short loop would visibly jump).
    requested = [
        slot.widget.animation_seconds()
        for slot in layout.slots
        if slot.widget is not None and slot.widget.is_animated()
    ]
    timing = frame_timing(max((s for s in requested if s), default=None))
    frames = layout.render_animation(renderer, widget_states, list(timing.times))
    if not frames:
        return None
    return Animation(frames, renderer.to_gif(frames, fps=timing.fps, rotation=rotation))


class FrameData(Protocol):
    """What a frame's widgets read besides entity states, already fetched.

    ``frame.FrameInputs`` gathers it from Home Assistant; anything else
    (a states file) can provide the same shape.
    """

    @property
    def chart_history(self) -> Mapping[tuple[str, float], list[float]]:
        """(entity_id, hours) -> resampled history (charts, HTML ``history()``)."""
        ...

    @property
    def candlestick_data(
        self,
    ) -> Mapping[tuple[str, int, int], list[tuple[float, float, float, float]]]:
        """(entity_id, interval seconds, candle count) -> OHLC candles."""
        ...

    @property
    def weather_forecasts(self) -> Mapping[str, list[dict[str, Any]]]:
        """entity_id -> daily forecast (weather widgets, HTML ``forecast()``)."""
        ...

    @property
    def source_images(self) -> Mapping[str, Image.Image]:
        """Image widget source -> picture."""
        ...

    @property
    def templates(self) -> Mapping[Widget, dict[str, str]]:
        """Widget -> its rendered label / text templates."""
        ...

    def picture(self, entity_id: str, kind: PictureKind) -> Image.Image | None:
        """An entity's picture: ``media`` is album art, ``camera`` anything else."""
        ...


def is_media_player(entity_id: str) -> bool:
    return entity_id.startswith("media_player.")


def assemble_widget_states(
    layout: Layout,
    get_state: Callable[[str], Any],
    data: FrameData,
    now: datetime,
) -> dict[int, WidgetState]:
    """Each placed widget's ``WidgetState`` (blocking: run in the executor).

    Entities come from ``get_state`` (``hass.states.get`` or a lookalike),
    everything else from ``data``. ``now`` is the frame's one instant,
    shared by every widget.
    """
    states: dict[int, WidgetState] = {}

    for slot in layout.slots:
        widget = slot.widget
        if widget is None:
            continue

        # Snapshot primary + additional entity dependencies
        primary_entity, additional = build_entity_states(get_state, widget)
        entity_id = widget.config.entity_id

        history: list[float] = []
        if isinstance(widget, ChartWidget) and entity_id:
            history = data.chart_history.get((entity_id, widget.hours), [])

        candlestick_data: list[tuple[float, float, float, float]] = []
        if isinstance(widget, CandlestickWidget) and entity_id:
            candlestick_data = data.candlestick_data.get(
                (entity_id, widget.interval_seconds, widget.candle_count), []
            )

        image = None
        if isinstance(widget, CameraWidget) and entity_id:
            image = data.picture(entity_id, "camera")
        elif isinstance(widget, MediaWidget) and entity_id:
            image = data.picture(entity_id, "media")
        elif isinstance(widget, ImageWidget):
            image = data.source_images.get(widget.source)

        forecast: list[dict[str, Any]] = []
        if isinstance(widget, WeatherWidget) and entity_id:
            forecast = data.weather_forecasts.get(entity_id, [])

        html_data: dict[str, Any] = {}
        if isinstance(widget, HtmlWidget):
            html_data = _html_data(widget, slot.rect, data)

        states[slot.index] = WidgetState(
            entity=primary_entity,
            entities=additional,
            history=history,
            candlestick_data=candlestick_data,
            image=image,
            forecast=forecast,
            now=now,
            templates=data.templates.get(widget, {}),
            **html_data,
        )

    return states


def _html_data(
    widget: HtmlWidget, rect: tuple[int, int, int, int], data: FrameData
) -> dict[str, Any]:
    """What an HTML widget's ``forecast()`` / ``history()`` / ``picture()`` read.

    Pictures become data: URIs here, in the executor, fitted to the
    cell (``fit_picture``) so the cell document stays small.
    """
    pictures: dict[str, str] = {}
    for entity_id in widget.picture_entities:
        kind: PictureKind = "media" if is_media_player(entity_id) else "camera"
        if (image := data.picture(entity_id, kind)) is not None:
            pictures[entity_id] = image_data_uri(fit_picture(image, rect))
    return {
        "forecasts": {
            entity_id: data.weather_forecasts[entity_id]
            for entity_id in widget.forecast_entities
            if entity_id in data.weather_forecasts
        },
        "histories": {
            series: data.chart_history[series]
            for series in widget.history_series
            if series in data.chart_history
        },
        "pictures": pictures,
    }
