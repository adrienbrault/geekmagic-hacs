"""Tests for preview entity resolution matching production rendering.

The websocket preview and the coordinator both snapshot widget entity
dependencies through ``build_entity_states``; these tests pin that
shared contract so the editor preview and the deployed dashboard can't
drift apart again.
"""

import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.preview import MockHass
from custom_components.geekmagic.websocket import _build_preview_widget_states
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.state import build_entity_states
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)


def make_hass() -> Any:
    """Mock hass with a few entities the widgets below depend on.

    Duck-types the two attributes the preview state builder touches
    (``states.get`` and ``config``), same shape as ``hass``.
    """
    hass = cast("Any", MockHass())
    hass.states.set("sensor.temp", "21.5", {"friendly_name": "Room", "unit_of_measurement": "°C"})
    hass.states.set("sensor.other", "42", {"friendly_name": "Other"})
    hass.states.set("light.kitchen", "on", {"friendly_name": "Kitchen"})
    return hass


class TestBuildEntityStates:
    """The shared production/preview entity snapshot helper."""

    def test_primary_from_config_entity_id(self):
        widget = TextWidget(WidgetConfig(widget_type="text", slot=0, entity_id="sensor.temp"))
        primary, additional = build_entity_states(make_hass().states.get, widget)
        assert primary is not None
        assert primary.entity_id == "sensor.temp"
        assert primary.state == "21.5"
        assert primary.attributes["friendly_name"] == "Room"
        assert additional == {}

    def test_options_entity_id_in_additional(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"entity_id": "sensor.temp", "html": "{{ state }}"},
            )
        )
        primary, additional = build_entity_states(make_hass().states.get, widget)
        assert primary is None
        assert set(additional) == {"sensor.temp"}
        assert additional["sensor.temp"].state == "21.5"

    def test_template_references_in_additional(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={
                    "html": ("{{ states('sensor.other') }}{{ is_state('light.kitchen', 'on') }}")
                },
            )
        )
        _, additional = build_entity_states(make_hass().states.get, widget)
        assert set(additional) == {"sensor.other", "light.kitchen"}

    def test_missing_entity_skipped(self):
        widget = HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                options={"entity_id": "sensor.gone", "html": "{{ states('sensor.also_gone') }}"},
            )
        )
        primary, additional = build_entity_states(make_hass().states.get, widget)
        assert primary is None
        assert additional == {}


class TestPreviewWidgetStates:
    """Preview builds states from the instantiated widgets."""

    def _html_widget(self, html: str, **options) -> HtmlWidget:
        return HtmlWidget(
            WidgetConfig(widget_type="html", slot=0, options={"html": html, **options})
        )

    def test_options_entity_feeds_template_variables(self):
        widget = self._html_widget("{{ name }}|{{ state }}|{{ unit }}", entity_id="sensor.temp")
        states = _build_preview_widget_states(make_hass(), {0: widget}, {}, {}, {})
        state = states[0]
        assert "sensor.temp" in state.entities
        assert widget.render_html(CTX, state) == "Room|21.5|°C"

    def test_states_and_is_state_dependencies_loaded(self):
        widget = self._html_widget(
            "{{ states('sensor.other') }}|{% if is_state('light.kitchen', 'on') %}ON{% endif %}"
        )
        states = _build_preview_widget_states(make_hass(), {0: widget}, {}, {}, {})
        state = states[0]
        assert set(state.entities) == {"sensor.other", "light.kitchen"}
        assert widget.render_html(CTX, state) == "42|ON"

    def test_missing_entity_renders_unknown_fallback(self):
        widget = self._html_widget("{{ states('sensor.gone') }}")
        states = _build_preview_widget_states(make_hass(), {0: widget}, {}, {}, {})
        assert states[0].entities == {}
        assert widget.render_html(CTX, states[0]) == "unknown"

    def test_primary_entity_matches_production_shape(self):
        widget = TextWidget(WidgetConfig(widget_type="text", slot=2, entity_id="sensor.temp"))
        states = _build_preview_widget_states(make_hass(), {2: widget}, {}, {}, {})
        assert states[2].entity is not None
        assert states[2].entity.entity_id == "sensor.temp"
        assert states[2].entities == {}
