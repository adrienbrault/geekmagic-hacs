"""HTML widget — user-authored HTML/CSS with Jinja templating.

The whole rendering pipeline is Blitz-based; this widget simply passes
the user's (Jinja-rendered) markup through as the cell fragment. The
pipeline wraps it with the theme's CSS variables, the fluid kit, and
theme chrome, so user templates can use ``var(--text-primary)``,
``.cell`` / ``.t-hero`` / ``.hide-short`` etc. directly.

Templates read the same data as the built-in widgets (``forecast()``,
``history()``, ``picture()``) and draw with their helpers (``ring()``,
``sparkline()``, ``icon()``, ... from ``_htmlkit``). ``FrameInputs``
fetches the data ahead of the render for every call whose entity id (and
``hours``) is a quoted literal, and hands it over in ``WidgetState``.
"""

from __future__ import annotations

import logging
import re
from html import escape
from typing import TYPE_CHECKING, Any, ClassVar

from jinja2.sandbox import SandboxedEnvironment

from ..history import CHART_RESAMPLE_BUCKETS
from ..htmldoc import CellContext, mdi_span
from ._htmlkit import template_helpers
from .base import Widget, WidgetConfig
from .weather import _condition_visual, _parse_forecast_day_name

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .state import WidgetState

_LOGGER = logging.getLogger(__name__)

# Entity references inside the Jinja template, e.g. states('sensor.temp'),
# state_attr("climate.living", "current_temperature") or
# is_state('light.kitchen', 'on'). Used to declare entity dependencies so
# the coordinator pre-fetches them into WidgetState.
_ENTITY_REF_RE = re.compile(r"""\b(?:states|state_attr|is_state)\(\s*['"]([^'"]+)['"]""")

# Data functions, fetched ahead of the render when their arguments are
# literals: forecast('weather.home'), picture('camera.door'),
# history('sensor.power'), history('sensor.power', 6) and
# history('sensor.power', hours=0.5).
_FORECAST_REF_RE = re.compile(r"""\bforecast\(\s*['"]([^'"]+)['"]\s*\)""")
_PICTURE_REF_RE = re.compile(r"""\bpicture\(\s*['"]([^'"]+)['"]\s*\)""")
_HISTORY_REF_RE = re.compile(
    r"""\bhistory\(\s*['"]([^'"]+)['"]\s*"""
    r"""(?:,\s*(?:hours\s*=\s*)?(\d+(?:\.\d*)?|\.\d+)\s*)?\)"""
)

# history(): the window when no ``hours`` is given, and the longest one.
# The recorder is queried on every refresh, so the cap is the Chart
# widget's longest period.
HISTORY_DEFAULT_HOURS = 24.0
HISTORY_MAX_HOURS = 24.0
# Most points history() returns: the Chart widget's resampling (evenly
# spaced, time-weighted averages, oldest first; fewer when the entity's
# history starts inside the window).
HISTORY_POINTS = CHART_RESAMPLE_BUCKETS


def history_hours(value: Any) -> float | None:
    """A history() window as the float that keys its series; None if out of range."""
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return None
    # NaN fails both comparisons
    if not 0 < hours <= HISTORY_MAX_HOURS:
        return None
    return hours


def _unique(items: Iterable[Any]) -> list[Any]:
    """``items`` without repeats, in first-seen order."""
    return list(dict.fromkeys(items))


def _forecast_days(days: list[dict[str, Any]], state: WidgetState) -> list[dict[str, Any]]:
    """Copies of forecast entries, plus what a template can't derive itself.

    ``day`` is the weekday (``Mon``) in Home Assistant's timezone, as the
    Weather widget shows it; ``icon`` and ``color`` are the Weather
    widget's glyph and theme role for the entry's condition. The cached
    entries are shared by every display, so they are never handed out.
    """
    tz = state.now.tzinfo if state.now else None
    result = []
    for index, day in enumerate(days):
        if not isinstance(day, dict):
            continue
        # The Weather widget's visual: a day it can't depict (no condition,
        # unknown, a provider's own string) gets the muted no-data glyph
        icon, color = _condition_visual(day.get("condition"))
        result.append(
            {
                **day,
                "day": _parse_forecast_day_name(day.get("datetime", ""), f"D{index + 1}", tz),
                "icon": "mdi:" + icon,
                "color": color,
            }
        )
    return result


def _build_template_context(
    state: WidgetState,
    primary_entity_id: str | None = None,
    ctx: CellContext | None = None,
) -> dict[str, Any]:
    """Build the Jinja context exposed to the user's HTML template.

    The convenience variables (``state``/``name``/``unit``/...) come from
    ``primary_entity_id`` when given (the widget's "Entity (template
    data)" selector, delivered by the coordinator in
    ``WidgetState.entities``), falling back to ``state.entity``. The
    drawing helpers resolve colours against ``ctx``'s theme.
    """

    def states(entity_id: str) -> str:
        entity = state.get_entity(entity_id)
        return entity.state if entity else "unknown"

    def state_attr(entity_id: str, attribute: str) -> Any:
        entity = state.get_entity(entity_id)
        return entity.get(attribute) if entity else None

    def is_state(entity_id: str, value: str) -> bool:
        return states(entity_id) == value

    def forecast(entity_id: str) -> list[dict[str, Any]]:
        return _forecast_days(state.forecasts.get(entity_id, []), state)

    def history(entity_id: str, hours: Any = HISTORY_DEFAULT_HOURS) -> list[float]:
        window = history_hours(hours)
        if window is None:
            return []
        return list(state.histories.get((entity_id, window), []))

    def picture(entity_id: str) -> str:
        return state.pictures.get(entity_id, "")

    entity = state.get_entity(primary_entity_id) if primary_entity_id else None
    if entity is None:
        entity = state.entity
    return {
        "entity": entity,
        "state": entity.state if entity else "",
        "name": entity.friendly_name if entity else "",
        "unit": entity.unit if entity else "",
        "attributes": entity.attributes if entity else {},
        "now": state.now,
        "states": states,
        "state_attr": state_attr,
        "is_state": is_state,
        "forecast": forecast,
        "history": history,
        "picture": picture,
        **template_helpers(ctx or CellContext(width=240, height=240)),
    }


def _render_template(
    source: str,
    state: WidgetState,
    primary_entity_id: str | None = None,
    ctx: CellContext | None = None,
) -> str:
    """Render the user's Jinja template against widget state.

    Uses a sandboxed environment: templates come from the user's own HA
    config, but sandboxing is cheap insurance against accidental access
    to Python internals.
    """
    env = SandboxedEnvironment(autoescape=False)
    context = _build_template_context(state, primary_entity_id, ctx)
    return env.from_string(source).render(**context)


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
    - ``forecast('weather.x')``, ``history('sensor.x', hours=24)``,
      ``picture('camera.x')`` — the data the Weather, Chart and Camera /
      Media widgets draw, fetched ahead for literal arguments
    - ``ring()``, ``arc()``, ``bar()``, ``sparkline()``, ``icon()``,
      ``color()`` — the built-ins' drawing helpers (``_htmlkit``)

    Theme colours are available in CSS as ``var(--text-primary)``,
    ``var(--primary)``, ``var(--success)``, etc., and the fluid kit
    classes (``.cell``, ``.t-hero``, ``.hide-short``, ...) work out of
    the box.
    """

    WIDGET_TYPE: ClassVar[str] = "html"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "HTML",
        "icon": "mdi:language-html5",
        "category": "custom",
        "description": "Your own HTML and CSS, with templates",
        "uses_label": False,
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
                "visible_when": {"animate": [True]},
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the HTML widget."""
        super().__init__(config)
        html = config.options.get("html", "")
        self.html = html if isinstance(html, str) else ""
        self.dynamic_entity_id = config.options.get("entity_id")
        self.animate = bool(config.options.get("animate", False))
        try:
            self.loop_seconds = float(config.options.get("loop_seconds") or 0) or None
        except (TypeError, ValueError):
            self.loop_seconds = None
        # What the template's data functions read, for FrameInputs to fetch
        self.forecast_entities: list[str] = _unique(_FORECAST_REF_RE.findall(self.html))
        self.picture_entities: list[str] = _unique(_PICTURE_REF_RE.findall(self.html))
        self.history_series: list[tuple[str, float]] = _unique(
            (entity_id, hours)
            for entity_id, raw_hours in _HISTORY_REF_RE.findall(self.html)
            if (hours := history_hours(raw_hours or HISTORY_DEFAULT_HOURS)) is not None
        )

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
            return _render_template(self.html, state, self.dynamic_entity_id, ctx)
        except Exception:
            _LOGGER.exception("Invalid Jinja template in HTML widget")
            return _placeholder("Template error", icon="alert-circle-outline")

    def get_entities(self) -> list[str]:
        """Return entity IDs this widget depends on.

        Includes the configured entity plus every entity referenced via
        ``states()`` / ``state_attr()`` / ``is_state()`` or a data function
        in the template, so the coordinator pre-fetches them into
        ``WidgetState.entities``.
        """
        entities: list[str] = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.dynamic_entity_id and self.dynamic_entity_id not in entities:
            entities.append(self.dynamic_entity_id)
        referenced = [
            *_ENTITY_REF_RE.findall(self.html),
            *self.forecast_entities,
            *(entity_id for entity_id, _ in self.history_series),
            *self.picture_entities,
        ]
        for entity_id in referenced:
            if entity_id not in entities:
                entities.append(entity_id)
        return entities
