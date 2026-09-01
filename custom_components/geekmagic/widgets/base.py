"""Base widget class and configuration."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from ._template import _render_template, is_template

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import EntityState, WidgetState

_LOGGER = logging.getLogger(__name__)


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

    def resolved_label(self, state: WidgetState | None) -> str | None:
        """``config.label`` with Jinja templates evaluated (issue #73).

        Labels support the same sandboxed template subset as the HTML
        widget — ``states()`` / ``state_attr()`` / ``is_state()`` /
        ``now()`` plus the primary-entity convenience variables — so
        ``{{ states('sensor.birdnet_go_last_detection') }}`` captions a
        Camera widget with live data. Referenced entities are
        pre-fetched automatically (see ``build_entity_states``).

        A broken template falls back to the raw label text: showing the
        literal source is the legacy behavior and makes the mistake
        visible on the panel. Returns None when no label is configured
        or the template evaluates to whitespace (so caption bands hide
        exactly like an unset label).
        """
        label = self.config.label
        if not label:
            return None
        if state is None or not is_template(label):
            return label
        try:
            rendered = _render_template(label, state, self.config.entity_id).strip()
        except Exception:
            _LOGGER.warning(
                "Invalid Jinja template in %s widget label: %s",
                self.config.widget_type,
                label,
                exc_info=True,
            )
            return label
        return rendered or None

    def label_for(
        self,
        entity: EntityState | None,
        *,
        state: WidgetState | None = None,
        fallback: str = "",
    ) -> str:
        """Resolve display label: ``config.label`` > ``entity.friendly_name`` > ``fallback``.

        Pretty much every widget that renders a name needs this chain.
        ``EntityState.friendly_name`` already falls back to ``entity_id``
        when no friendly name attribute is set, so widgets that previously
        wrote ``entity.friendly_name or entity.entity_id`` collapse to
        a single ``self.label_for(entity, fallback=...)``.

        Pass ``state`` so a label containing a Jinja template is
        evaluated (``resolved_label``); render paths always have it.
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
