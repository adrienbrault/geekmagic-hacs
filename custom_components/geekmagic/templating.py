"""Home Assistant templates in widget labels and text content (issue #73).

Widgets render in an executor thread, but Home Assistant templates must
render in the event loop. So every render path — the coordinator's
device render and the panel's websocket preview — runs
``WidgetTemplates.async_render`` in the loop first and hands the results
to the widgets through ``WidgetState.templates``.

Templates are full Home Assistant templates: ``states()``,
``state_attr()``, ``is_state()``, ``now()``, filters, and so on. The
widget's own entity is also exposed as ``entity_id`` / ``state`` /
``name`` / ``unit`` / ``attributes``.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

if TYPE_CHECKING:
    from collections.abc import Callable

    from .widgets.base import Widget

_LOGGER = logging.getLogger(__name__)


class WidgetTemplates:
    """Renders widget templates, keeping one compiled ``Template`` per source.

    Compiling is the expensive part, and a dashboard re-renders the same
    labels every refresh, so templates are compiled once and reused. A
    source that fails to compile is remembered and skipped. Problems —
    errors, and the undefined-variable warnings Home Assistant would
    otherwise log on every render — are logged once per source until
    the screens are rebuilt, not on every refresh. A failing source is
    then shown raw by the widget.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize with an empty cache."""
        self._hass = hass
        # source -> (template, its log_fn), or None when it does not compile
        self._templates: dict[str, tuple[Template, Callable[[int, str], None]] | None] = {}
        self._reported: set[str] = set()

    def clear(self) -> None:
        """Forget compiled templates (call when the configuration changes)."""
        self._templates.clear()
        self._reported.clear()

    def _log_once(self, source: str, level: int, message: str) -> None:
        if source in self._reported:
            _LOGGER.debug("Widget template %r: %s", source, message)
            return
        self._reported.add(source)
        _LOGGER.log(level, "Widget template %r: %s", source, message)

    def _report(self, source: str, err: Exception) -> None:
        self._log_once(source, logging.WARNING, f"invalid, showing it as text ({err})")

    def _template(self, source: str) -> tuple[Template, Callable[[int, str], None]] | None:
        if source in self._templates:
            return self._templates[source]
        template = Template(source, self._hass)
        try:
            template.ensure_valid()
        except TemplateError as err:
            self._report(source, err)
            self._templates[source] = None
            return None
        # The template binds its log_fn when first rendered, so keep one
        # per source rather than a fresh closure per render.
        entry = (template, partial(self._log_once, source))
        self._templates[source] = entry
        return entry

    def _variables(self, widget: Widget) -> dict[str, Any]:
        entity_id = widget.config.entity_id
        ha_state = self._hass.states.get(entity_id) if entity_id else None
        attributes = dict(ha_state.attributes) if ha_state else {}
        return {
            "entity_id": entity_id or "",
            "state": ha_state.state if ha_state else "",
            "name": attributes.get("friendly_name", entity_id or ""),
            "unit": attributes.get("unit_of_measurement", ""),
            "attributes": attributes,
        }

    @callback
    def async_render(self, widget: Widget) -> dict[str, str]:
        """Render a widget's templates: source -> output.

        Must run in the event loop. Never raises: a source that fails is
        left out, so the widget falls back to showing it raw.
        """
        sources = widget.template_sources()
        if not sources:
            return {}
        variables = self._variables(widget)
        rendered: dict[str, str] = {}
        for source in sources:
            entry = self._template(source)
            if entry is None:
                continue
            template, log_fn = entry
            try:
                output = template.async_render(variables, parse_result=False, log_fn=log_fn)
            except Exception as err:  # a label must never break a render
                self._report(source, err)
            else:
                rendered[source] = str(output)
        return rendered
