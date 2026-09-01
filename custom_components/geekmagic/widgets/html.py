"""HTML widget — user-authored HTML/CSS with Jinja templating.

The whole rendering pipeline is Blitz-based; this widget simply passes
the user's (Jinja-rendered) markup through as the cell fragment. The
pipeline wraps it with the theme's CSS variables, the fluid kit, and
theme chrome, so user templates can use ``var(--text-primary)``,
``.cell`` / ``.t-hero`` / ``.hide-short`` etc. directly.
"""

from __future__ import annotations

import logging
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from ..htmldoc import mdi_span
from ._template import _render_template, template_entity_refs
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from ..htmldoc import CellContext
    from .state import WidgetState

_LOGGER = logging.getLogger(__name__)


def _placeholder(message: str, icon: str = "code-tags") -> str:
    """Placeholder fragment for empty or broken templates.

    ``.t-label`` is nowrap and Blitz neither clips nor ellipsizes, so an
    unmeasured caption bleeds past the panel edges — keep the words
    short and let them wrap per-word instead (one nowrap span per word;
    the flex column stacks what doesn't fit on one line).
    """
    words = "".join(
        f'<span style="white-space: nowrap">{escape(word)}</span>'
        for word in message.upper().split()
    )
    glyph = mdi_span(icon, "icon i-md", "color: var(--text-tertiary)")
    return (
        '<div class="cell" style="justify-content: center; gap: 2.5vmin">'
        f"{glyph}"
        '<div class="t-label" style="display: flex; flex-wrap: wrap; '
        f'justify-content: center; gap: 0.35em; max-width: 100%">{words}</div>'
        "</div>"
    )


class HtmlWidget(Widget):
    """Widget that renders arbitrary HTML/CSS.

    The ``html`` option is a Jinja template with access to:

    - ``state``, ``name``, ``unit``, ``attributes`` — the primary entity
    - ``states('sensor.x')``, ``state_attr('sensor.x', 'attr')``,
      ``is_state('sensor.x', 'on')`` — any entity referenced is
      pre-fetched by the coordinator automatically
    - ``now`` — timezone-aware current datetime

    Theme colours are available in CSS as ``var(--text-primary)``,
    ``var(--primary)``, ``var(--success)``, etc., and the fluid kit
    classes (``.cell``, ``.t-hero``, ``.hide-short``, ...) work out of
    the box.
    """

    WIDGET_TYPE: ClassVar[str] = "html"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "HTML",
        "needs_entity": False,
        "options": [
            {
                "key": "html",
                "type": "textarea",
                "label": "HTML Template",
                "placeholder": (
                    '<div class="cell"><div class="t-hero">{{ state }}{{ unit }}</div></div>'
                ),
            },
            {"key": "entity_id", "type": "entity", "label": "Entity (template data)"},
            {
                "key": "animate",
                "type": "boolean",
                "label": "Animate (render CSS animations as GIF)",
                "default": False,
            },
            {
                "key": "loop_seconds",
                "type": "number",
                "label": "Animation Loop (seconds)",
                "min": 0.8,
                "max": 4,
                "default": 1.6,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the HTML widget."""
        super().__init__(config)
        self.html = config.options.get("html", "")
        self.dynamic_entity_id = config.options.get("entity_id")
        self.animate = bool(config.options.get("animate", False))
        try:
            self.loop_seconds = float(config.options.get("loop_seconds") or 0) or None
        except (TypeError, ValueError):
            self.loop_seconds = None

    def is_animated(self) -> bool:
        """Animated when the user opted this widget in."""
        return self.animate

    def animation_seconds(self) -> float | None:
        """User-tuned loop length (slow ambient loops read best)."""
        return self.loop_seconds if self.animate else None

    def render_html(self, ctx: CellContext, state: WidgetState) -> str:
        """Render the HTML widget fragment."""
        if not self.html.strip():
            return _placeholder("No HTML configured")

        try:
            return _render_template(self.html, state, self.dynamic_entity_id)
        except Exception:
            _LOGGER.exception("Invalid Jinja template in HTML widget")
            return _placeholder("Template error", icon="alert-circle-outline")

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on.

        Includes the configured entity plus every entity referenced via
        ``states()`` / ``state_attr()`` / ``is_state()`` in the template,
        so the coordinator pre-fetches them into ``WidgetState.entities``.
        """
        entities: list[str] = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.dynamic_entity_id and self.dynamic_entity_id not in entities:
            entities.append(self.dynamic_entity_id)
        for entity_id in template_entity_refs(self.html):
            if entity_id not in entities:
                entities.append(entity_id)
        return entities
