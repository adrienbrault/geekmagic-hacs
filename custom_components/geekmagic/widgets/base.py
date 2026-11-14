"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import EntityState, WidgetState

_TEMPLATE_MARKERS = ("{{", "{%")

# What a cell shows when its widget can't be built or rendered: one bad
# widget costs its own cell, never the rest of the screen.
WIDGET_ERROR_HTML = '<div class="cell"><div class="t-label">WIDGET ERROR</div></div>'


def is_template(text: str | None) -> bool:
    """Whether ``text`` contains Jinja syntax worth rendering (issue #73)."""
    return bool(text) and any(marker in text for marker in _TEMPLATE_MARKERS)


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

    def hero_hint(self, ctx: CellContext, state: WidgetState) -> tuple[str, float] | None:
        """``(kind, px)`` of the hero this widget would fit into ``ctx``.

        Layouts use it to harmonise sibling cells: equal-sized cells
        whose heroes are of the same ``kind`` ("num" / "word") are all
        capped to the smallest fitted size, so a grid of readings shares
        one type size instead of each cell fitting its own. Widgets
        without a hero return None (the default) and are left alone.
        """
        return None

    def template_sources(self) -> list[str]:
        """Configured strings that are Jinja templates (issue #73).

        Home Assistant templates may only render in the event loop, while
        widgets render in an executor thread. So the coordinator and the
        websocket preview render these sources up front (see
        ``templating.WidgetTemplates``) and hand the results over in
        ``WidgetState.templates``. The base widget templates its label;
        widgets with other templated options extend the list.
        """
        return [self.config.label] if self.config.label and is_template(self.config.label) else []

    def resolved_label(self, state: WidgetState) -> str | None:
        """``config.label`` with its template, if any, evaluated.

        A template that rendered to nothing reads as an unset label, so
        caption bands hide. A template without a rendered result (it
        failed, or the render path has no Home Assistant to evaluate it)
        shows its raw source, which keeps the mistake visible.
        """
        label = self.config.label
        if not label:
            return None
        if label in state.templates:
            return state.templates[label] or None
        return label

    def label_for(
        self,
        entity: EntityState | None,
        *,
        state: WidgetState,
        fallback: str = "",
    ) -> str:
        """Resolve display label: ``config.label`` > ``entity.friendly_name`` > ``fallback``.

        Pretty much every widget that renders a name needs this chain.
        ``EntityState.friendly_name`` already falls back to ``entity_id``
        when no friendly name attribute is set, so widgets that previously
        wrote ``entity.friendly_name or entity.entity_id`` collapse to
        a single ``self.label_for(entity, state=state, fallback=...)``.
        The label goes through ``resolved_label``, so templates apply.
        """
        label = self.resolved_label(state)
        if label:
            return label
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


class BrokenWidget(Widget):
    """Stands in for a widget whose stored config could not be built."""

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Paint the error cell."""
        return WIDGET_ERROR_HTML

    def get_entities(self) -> list[str]:
        """A broken widget depends on nothing."""
        return []
