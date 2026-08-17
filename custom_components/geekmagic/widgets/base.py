"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from .state import DataNeeds

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import EntityState, WidgetState


@dataclass
class WidgetConfig:
    """Configuration for a widget."""

    widget_type: str
    slot: int = 0
    entity_id: str | None = None
    label: str | None = None
    color: tuple[int, int, int] | None = None
    options: dict[str, Any] = field(default_factory=dict)


class Widget(ABC):
    """Base class for all widgets.

    Widgets render by returning an HTML fragment, rasterized by the
    Blitz engine at the cell size. All state needed for rendering is
    passed via the WidgetState parameter, enabling pure functional
    rendering. Prefer the fluid kit classes (``.cell``, ``.t-hero``,
    ``.hide-short``, ...) so one fragment adapts to every cell size.
    """

    WIDGET_TYPE: ClassVar[str] = ""
    SCHEMA: ClassVar[dict[str, Any]] = {}

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the widget.

        Args:
            config: Widget configuration
        """
        self.config = config

    @property
    def entity_id(self) -> str | None:
        """Get the entity ID this widget tracks."""
        return self.config.entity_id

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on.

        Override in subclasses that track entities.
        """
        if self.config.entity_id:
            return [self.config.entity_id]
        return []

    def data_needs(self) -> DataNeeds:
        """Declare what this widget needs fetched beyond entity states.

        ``get_entities`` covers everything readable straight off
        ``hass.states``; this covers the rest — recorder history, camera
        frames, album art, weather forecasts — which has to be fetched
        in the event loop before the render runs in the executor.

        Override in widgets that need any of it. The default declares
        nothing, so a screen made of clocks and text costs no fetches at
        all.
        """
        return DataNeeds()

    def is_animated(self) -> bool:
        """Whether this widget's fragment carries CSS animations.

        When True — and the device's Animations switch is on — the
        pipeline renders the view as an animated GIF: this widget's cell
        is rasterized at several animation timestamps while static cells
        render once. Keep it False for fragments without animations; a
        GIF costs upload size and device decode time.
        """
        return False

    def animation_seconds(self) -> float | None:
        """Length of this widget's animation loop, in seconds.

        None means the pipeline default. Ambient animations (breathing
        glows, gradient drift) read best at 2-4s; the view's GIF loop is
        the longest requested by its animated widgets, so CSS durations
        should equal or evenly divide it for a seamless loop.
        """
        return None

    def label_for(self, entity: EntityState | None, *, fallback: str = "") -> str:
        """Resolve display label: ``config.label`` > ``entity.friendly_name`` > ``fallback``.

        Pretty much every widget that renders a name needs this chain.
        ``EntityState.friendly_name`` already falls back to ``entity_id``
        when no friendly name attribute is set, so widgets that previously
        wrote ``entity.friendly_name or entity.entity_id`` collapse to
        a single ``self.label_for(entity, fallback=...)``.
        """
        if self.config.label:
            return self.config.label
        if entity is not None:
            return entity.friendly_name
        return fallback

    @abstractmethod
    def render_html(
        self,
        ctx: CellContext,
        state: WidgetState,
    ) -> str:
        """Render the widget as an HTML fragment.

        Pure function: given the same ctx and state, returns the same
        fragment. The fragment is wrapped with the theme's CSS (palette
        variables, fluid kit, chrome) and rasterized at the cell size,
        so viewport units and media queries respond to the cell.

        Args:
            ctx: Cell geometry (width/height/slot_index) and theme.
            state: Pre-fetched state including entity data, history,
                images, and time.

        Returns:
            HTML fragment (no <html>/<body> wrapper).
        """
