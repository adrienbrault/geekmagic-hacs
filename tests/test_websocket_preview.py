"""Tests for preview entity resolution matching production rendering.

The websocket preview and the coordinator now share one state builder:
``WidgetDataResolver.build_states``, over a layout built by the same
``build_layout`` adapter. These tests pin that shared contract — the
editor preview and the deployed dashboard resolve identical entity
dependencies for a widget — so the two can't drift apart again.
"""

import base64
import io
import sys
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_WIDGETS,
    DOMAIN,
    LAYOUT_GRID_2X2,
    THEME_CLASSIC,
)
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.views import build_layout
from custom_components.geekmagic.websocket import (
    _PREVIEW_RESOLVER_KEY,
    _preview_resolver,
    async_register_websocket_commands,
)
from custom_components.geekmagic.widget_data import WidgetDataResolver
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.html import HtmlWidget
from custom_components.geekmagic.widgets.state import build_entity_states
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME
from tests.helpers import MockHass

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


def preview_states(hass, widgets: list[dict]):
    """Build a preview layout and its states the way ``ws_preview_render`` does."""
    layout = build_layout(
        {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: widgets},
        default_theme=THEME_CLASSIC,
    )
    return layout, WidgetDataResolver(hass).build_states(layout)


class TestPreviewWidgetStates:
    """The preview builds states from the instantiated widgets."""

    def test_options_entity_feeds_template_variables(self):
        layout, states = preview_states(
            make_hass(),
            [
                {
                    "type": "html",
                    "slot": 0,
                    "options": {
                        "html": "{{ name }}|{{ state }}|{{ unit }}",
                        "entity_id": "sensor.temp",
                    },
                }
            ],
        )
        widget = layout.get_slot(0).widget
        state = states[0]
        assert "sensor.temp" in state.entities
        assert widget.render_html(CTX, state) == "Room|21.5|°C"

    def test_states_and_is_state_dependencies_loaded(self):
        layout, states = preview_states(
            make_hass(),
            [
                {
                    "type": "html",
                    "slot": 0,
                    "options": {
                        "html": (
                            "{{ states('sensor.other') }}|"
                            "{% if is_state('light.kitchen', 'on') %}ON{% endif %}"
                        )
                    },
                }
            ],
        )
        state = states[0]
        assert set(state.entities) == {"sensor.other", "light.kitchen"}
        assert layout.get_slot(0).widget.render_html(CTX, state) == "42|ON"

    def test_missing_entity_renders_unknown_fallback(self):
        layout, states = preview_states(
            make_hass(),
            [{"type": "html", "slot": 0, "options": {"html": "{{ states('sensor.gone') }}"}}],
        )
        assert states[0].entities == {}
        assert layout.get_slot(0).widget.render_html(CTX, states[0]) == "unknown"

    def test_primary_entity_matches_production_shape(self):
        _layout, states = preview_states(
            make_hass(), [{"type": "text", "slot": 2, "entity_id": "sensor.temp"}]
        )
        assert states[2].entity is not None
        assert states[2].entity.entity_id == "sensor.temp"
        assert states[2].entities == {}

    def test_every_placed_widget_gets_a_state(self):
        """One state per occupied slot, whatever the widget type."""
        _layout, states = preview_states(
            make_hass(),
            [
                {"type": "clock", "slot": 0},
                {"type": "text", "slot": 1, "entity_id": "sensor.temp"},
                {"type": "chart", "slot": 3, "entity_id": "sensor.temp"},
            ],
        )
        assert set(states) == {0, 1, 3}
        assert states[3].history == []  # nothing prefetched for this preview


class TestSharedPreviewResolver:
    """One resolver per Home Assistant instance, not one per request."""

    async def test_same_instance_is_returned(self, hass):
        assert _preview_resolver(hass) is _preview_resolver(hass)

    async def test_it_is_stored_under_a_non_entry_key(self, hass):
        """The resolver lives in ``hass.data[DOMAIN]`` beside the store.

        Everything that walks that mapping is looking for coordinators
        and filters on their duck-type, so the resolver must not answer
        to ``device``/``config_entry``.
        """
        resolver = _preview_resolver(hass)
        assert hass.data[DOMAIN][_PREVIEW_RESOLVER_KEY] is resolver
        assert not hasattr(resolver, "device")
        assert not hasattr(resolver, "config_entry")


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


async def _preview(client, view_config: dict, msg_id: int = 1) -> dict:
    """Send one ``geekmagic/preview/render`` and return the raw reply."""
    await client.send_json(
        {"id": msg_id, "type": "geekmagic/preview/render", "view_config": view_config}
    )
    return await client.receive_json()


class TestPreviewRenderCommand:
    """The shipped websocket handler, end to end over a real connection."""

    @pytest.fixture
    def ws(self, hass, hass_ws_client):
        """A websocket client with the GeekMagic commands registered."""
        async_register_websocket_commands(hass)
        return hass_ws_client(hass)

    async def test_a_view_comes_back_as_a_240px_png(self, ws):
        client = await ws
        msg = await _preview(
            client,
            {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: [{"type": "clock", "slot": 0}]},
        )

        assert msg["success"]
        result = msg["result"]
        assert result["content_type"] == "image/png"
        assert (result["width"], result["height"]) == (240, 240)

        png = base64.b64decode(result["image"])
        assert png.startswith(PNG_MAGIC)
        with Image.open(io.BytesIO(png)) as image:
            assert image.size == (240, 240)

    async def test_an_unusable_slot_costs_its_widget_not_the_render(self, ws):
        """``slot: "abc"`` is skipped by ``build_layout``; the view still renders."""
        client = await ws
        msg = await _preview(
            client,
            {
                CONF_LAYOUT: LAYOUT_GRID_2X2,
                CONF_WIDGETS: [{"type": "clock", "slot": "abc"}, {"type": "clock", "slot": 1}],
            },
        )

        assert msg["success"]
        assert base64.b64decode(msg["result"]["image"]).startswith(PNG_MAGIC)

    async def test_a_malformed_view_config_reports_render_error(self, ws):
        """Whatever the panel sends, the failure the panel gets is ``render_error``.

        A widget list that isn't a list of dicts blows up inside
        ``build_layout``, before the prefetch and the render — the reply
        still has to be the one error code the panel knows.
        """
        client = await ws
        msg = await _preview(client, {CONF_LAYOUT: LAYOUT_GRID_2X2, CONF_WIDGETS: "not-a-list"})

        assert not msg["success"]
        assert msg["error"]["code"] == "render_error"
