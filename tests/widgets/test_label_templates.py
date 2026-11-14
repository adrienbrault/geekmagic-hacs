"""Tests for Home Assistant templates in widget labels and text content.

Regression tests for issue #73. Templates render in the event loop
(``templating.WidgetTemplates``) before the executor render, and reach
the widgets as ``WidgetState.templates``; both the device render and
the websocket preview go through that same step.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from homeassistant.components import websocket_api
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from custom_components.geekmagic import websocket as ws
from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.templating import WidgetTemplates
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.icon import IconWidget
from custom_components.geekmagic.widgets.media import MediaWidget
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from custom_components.geekmagic.widgets.text import TextWidget
from custom_components.geekmagic.widgets.theme import DEFAULT_THEME

BIRD_SENSOR = "sensor.birdnet_go_last_detection"
BIRD_LABEL = "{{ states('" + BIRD_SENSOR + "') }}"
WEEKDAY_LABEL = (
    "{% set days = ['ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС'] %}"  # noqa: RUF001
    "{{ days[now().weekday()] }}"
)
CTX = CellContext(width=240, height=240, slot_index=0, theme=DEFAULT_THEME)
CAMERA = EntityState(
    entity_id="camera.birdnet_vogelbild", state="idle", attributes={"friendly_name": "Bird Cam"}
)


def make_camera(label: str | None) -> CameraWidget:
    return CameraWidget(
        WidgetConfig(
            widget_type="camera", slot=0, entity_id="camera.birdnet_vogelbild", label=label
        )
    )


def text_widget(text: str, **config) -> TextWidget:
    return TextWidget(WidgetConfig(widget_type="text", slot=0, options={"text": text}, **config))


class TestTemplateSources:
    """Which configured strings a widget asks to have rendered."""

    def test_static_label_is_not_a_source(self):
        assert make_camera("Birds").template_sources() == []

    def test_no_label(self):
        assert make_camera(None).template_sources() == []

    def test_templated_label(self):
        assert make_camera(BIRD_LABEL).template_sources() == [BIRD_LABEL]

    def test_text_widget_adds_its_content(self):
        widget = text_widget("{{ 1 + 1 }}", label=BIRD_LABEL)
        assert widget.template_sources() == [BIRD_LABEL, "{{ 1 + 1 }}"]

    def test_text_widget_static_content(self):
        assert text_widget("Hello").template_sources() == []


class TestResolvedLabel:
    """Widget.resolved_label reads the rendered result from the state."""

    def test_static_label_passthrough(self):
        assert make_camera("Birds").resolved_label(WidgetState()) == "Birds"

    def test_no_label_returns_none(self):
        assert make_camera(None).resolved_label(WidgetState()) is None

    def test_rendered_template(self):
        state = WidgetState(templates={BIRD_LABEL: "Great Tit"})
        assert make_camera(BIRD_LABEL).resolved_label(state) == "Great Tit"

    def test_empty_result_hides_label(self):
        """A template rendering to nothing behaves like no label."""
        state = WidgetState(templates={BIRD_LABEL: ""})
        assert make_camera(BIRD_LABEL).resolved_label(state) is None

    def test_unrendered_template_shows_raw_source(self):
        """No result (failed, or no hass) keeps the mistake visible."""
        assert make_camera(BIRD_LABEL).resolved_label(WidgetState()) == BIRD_LABEL


class TestLabelForChain:
    """label_for keeps its fallback chain with templates in the mix."""

    def test_template_label_wins(self):
        state = WidgetState(entity=CAMERA, templates={BIRD_LABEL: "Great Tit"})
        assert make_camera(BIRD_LABEL).label_for(CAMERA, state=state) == "Great Tit"

    def test_empty_template_falls_back_to_friendly_name(self):
        state = WidgetState(entity=CAMERA, templates={BIRD_LABEL: ""})
        assert make_camera(BIRD_LABEL).label_for(CAMERA, state=state) == "Bird Cam"

    def test_fallback_when_nothing_resolves(self):
        state = WidgetState(templates={BIRD_LABEL: ""})
        widget = make_camera(BIRD_LABEL)
        assert widget.label_for(None, state=state, fallback="Camera") == "Camera"


class TestRenderedFragments:
    """Rendered results reach the widget fragments."""

    def test_entity_widget_label(self):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="camera.birdnet_vogelbild",
                label=BIRD_LABEL,
            )
        )
        html = widget.render_html(CTX, WidgetState(entity=CAMERA, templates={BIRD_LABEL: "Wren"}))
        assert "wren" in html.lower()
        assert "states(" not in html

    def test_icon_widget_caption(self):
        widget = IconWidget(
            WidgetConfig(widget_type="icon", slot=0, label=BIRD_LABEL, options={"icon": "mdi:bird"})
        )
        html = widget.render_html(CTX, WidgetState(templates={BIRD_LABEL: "Wren"}))
        assert "wren" in html.lower()

    def test_idle_media_player_label(self):
        """The idle card captions the player with the rendered label."""
        player = EntityState(
            entity_id="media_player.den", state="off", attributes={"friendly_name": "Den"}
        )
        widget = MediaWidget(
            WidgetConfig(
                widget_type="media", slot=0, entity_id="media_player.den", label=BIRD_LABEL
            )
        )
        html = widget.render_html(CTX, WidgetState(entity=player, templates={BIRD_LABEL: "Wren"}))
        assert "wren" in html.lower()

    def test_text_widget_label(self):
        widget = text_widget("Hello", label=BIRD_LABEL)
        html = widget.render_html(CTX, WidgetState(templates={BIRD_LABEL: "Wren"}))
        assert "wren" in html.lower()
        assert "states(" not in html

    def test_templated_text_content(self):
        source = "{{ 20 + 1 }}"
        html = text_widget(source).render_html(CTX, WidgetState(templates={source: "21"}))
        assert "21" in html
        assert "{{" not in html

    def test_unrendered_text_template_shows_source(self):
        html = text_widget("{{ bad(").render_html(CTX, WidgetState())
        assert "bad(" in html

    def test_entity_state_beats_text_template(self):
        """An entity-driven text widget keeps showing the entity state."""
        widget = text_widget(BIRD_LABEL, entity_id="camera.birdnet_vogelbild")
        html = widget.render_html(CTX, WidgetState(entity=CAMERA, templates={BIRD_LABEL: "Wren"}))
        assert "idle" in html
        assert "wren" not in html.lower()


def _warnings(caplog) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.name == "custom_components.geekmagic.templating" and r.levelno >= logging.WARNING
    ]


class TestWidgetTemplates:
    """The event-loop renderer, against a real Home Assistant."""

    async def test_issue_73_states_template(self, hass):
        hass.states.async_set(BIRD_SENSOR, "Great Tit")
        rendered = WidgetTemplates(hass).async_render(make_camera(BIRD_LABEL))
        assert rendered == {BIRD_LABEL: "Great Tit"}

    async def test_weekday_set_block_template(self, hass):
        """The abbreviated-weekday template from the issue thread."""
        rendered = WidgetTemplates(hass).async_render(make_camera(WEEKDAY_LABEL))
        days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]  # noqa: RUF001
        assert rendered[WEEKDAY_LABEL] == days[dt_util.now().weekday()]

    async def test_ha_filters_work(self, hass):
        hass.states.async_set("sensor.power", "1234.567")
        source = "{{ states('sensor.power') | float | round(1) }} W"
        rendered = WidgetTemplates(hass).async_render(make_camera(source))
        assert rendered[source] == "1234.6 W"

    async def test_own_entity_variables(self, hass):
        hass.states.async_set(CAMERA.entity_id, "idle", {"friendly_name": "Bird Cam"})
        source = "{{ name }} ({{ state }})"
        rendered = WidgetTemplates(hass).async_render(make_camera(source))
        assert rendered[source] == "Bird Cam (idle)"

    async def test_whitespace_result_is_empty(self, hass):
        source = "{% if false %}x{% endif %}  "
        rendered = WidgetTemplates(hass).async_render(make_camera(source))
        assert rendered == {source: ""}

    async def test_static_label_not_rendered(self, hass):
        assert WidgetTemplates(hass).async_render(make_camera("Birds")) == {}

    async def test_syntax_error_left_out_and_logged_once(self, hass, caplog):
        templates = WidgetTemplates(hass)
        widget = make_camera("{{ nope(")
        with caplog.at_level(logging.WARNING, logger="custom_components.geekmagic.templating"):
            assert templates.async_render(widget) == {}
            assert templates.async_render(widget) == {}
        assert len(_warnings(caplog)) == 1
        # ...so the widget shows the raw source rather than crashing
        assert widget.resolved_label(WidgetState()) == "{{ nope("

    async def test_undefined_variable_warns_once(self, hass, caplog):
        """HA's per-render undefined-variable warning is logged once, not
        on every refresh; the undefined part renders blank."""
        templates = WidgetTemplates(hass)
        source = "A{{ foo }}B"
        widget = make_camera(source)
        with caplog.at_level(logging.WARNING):
            assert templates.async_render(widget) == {source: "AB"}
            assert templates.async_render(widget) == {source: "AB"}
        assert len(_warnings(caplog)) == 1
        assert not [
            r for r in caplog.records if r.levelno >= logging.WARNING and "foo" in r.getMessage()
        ][1:]

    async def test_render_error_left_out(self, hass):
        source = "{{ states('sensor.missing') | float }}"
        assert WidgetTemplates(hass).async_render(make_camera(source)) == {}

    async def test_compiled_once(self, hass):
        """Refreshes reuse the compiled template instead of re-parsing."""
        templates = WidgetTemplates(hass)
        widget = make_camera(BIRD_LABEL)
        with patch(
            "custom_components.geekmagic.templating.Template", wraps=Template
        ) as template_cls:
            templates.async_render(widget)
            templates.async_render(widget)
            assert template_cls.call_count == 1
            templates.clear()
            templates.async_render(widget)
            assert template_cls.call_count == 2


def _device() -> MagicMock:
    device = MagicMock()
    device.host = "192.168.1.100"
    device.model = "unknown"
    device.capabilities.brightness_range = (0, 100)
    device.display_rendered_dashboard = AsyncMock()
    device.get_brightness = AsyncMock(return_value=50)
    device.get_state = AsyncMock(return_value=None)
    device.get_space = AsyncMock(return_value=None)
    device.is_builtin_theme = MagicMock(return_value=False)
    return device


async def test_device_render_receives_rendered_templates(hass):
    """The coordinator renders templates in the loop, before the executor job."""
    hass.states.async_set(BIRD_SENSOR, "Great Tit")
    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREENS: [
            {
                "name": "Birds",
                CONF_LAYOUT: LAYOUT_GRID_2X2,
                CONF_WIDGETS: [
                    {"type": "text", "slot": 0, "label": BIRD_LABEL, "options": {"text": "x"}}
                ],
            }
        ],
    }
    coordinator = GeekMagicCoordinator(hass, _device(), options)
    seen: dict[int, WidgetState] = {}

    def fake_render(screen=None):
        seen.update(coordinator._build_widget_states(coordinator._layouts[0]))
        return b"jpeg", b"png", "dashboard.jpg"

    with patch.object(coordinator, "_render_display", side_effect=fake_render):
        await coordinator._async_update_data()

    assert seen[0].templates == {BIRD_LABEL: "Great Tit"}


async def test_device_render_uses_the_screen_whose_templates_rendered(hass):
    """A screen change landing after the templates render must not make the
    executor render the other screen's widgets with no rendered templates
    (they would show their raw ``{{ ... }}`` source for a frame)."""
    other_sensor = "sensor.other"
    other_label = "{{ states('" + other_sensor + "') }}"
    hass.states.async_set(BIRD_SENSOR, "Great Tit")
    hass.states.async_set(other_sensor, "Robin")

    def screen(name: str, label: str) -> dict:
        return {
            "name": name,
            CONF_LAYOUT: LAYOUT_GRID_2X2,
            CONF_WIDGETS: [{"type": "text", "slot": 0, "label": label, "options": {"text": "x"}}],
        }

    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREENS: [screen("Birds", BIRD_LABEL), screen("Other", other_label)],
    }
    coordinator = GeekMagicCoordinator(hass, _device(), options)
    real_render_templates = coordinator._inputs.async_render_templates

    def render_templates_then_switch(widgets) -> None:
        real_render_templates(widgets)
        coordinator._current_screen = 1  # e.g. the Next Screen button

    captured: dict = {}

    def fake_render(screen: int | None = None):
        captured["screen"] = screen
        assert screen is not None
        layout = coordinator._layouts[screen]
        captured["states"] = coordinator._build_widget_states(layout)
        return b"jpeg", b"png", "dashboard.jpg"

    with (
        patch.object(
            coordinator._inputs,
            "async_render_templates",
            side_effect=render_templates_then_switch,
        ),
        patch.object(coordinator, "_render_display", side_effect=fake_render),
    ):
        await coordinator._async_update_data()

    assert captured["screen"] == 0
    assert captured["states"][0].templates == {BIRD_LABEL: "Great Tit"}


async def test_websocket_preview_receives_rendered_templates(hass, hass_ws_client):
    """The panel preview renders templates the same way as the device."""
    hass.states.async_set(BIRD_SENSOR, "Great Tit")
    websocket_api.async_register_command(hass, ws.ws_preview_render)
    client = await hass_ws_client(hass)
    captured: dict[int, WidgetState] = {}
    real_build = ws._build_preview_widget_states

    def spy(*args, **kwargs):
        states = real_build(*args, **kwargs)
        captured.update(states)
        return states

    with patch.object(ws, "_build_preview_widget_states", side_effect=spy):
        await client.send_json(
            {
                "id": 1,
                "type": "geekmagic/preview/render",
                "view_config": {
                    "layout": LAYOUT_GRID_2X2,
                    "widgets": [
                        {"type": "text", "slot": 0, "label": BIRD_LABEL, "options": {"text": "x"}}
                    ],
                },
            }
        )
        msg = await client.receive_json()

    assert msg["success"], msg
    assert captured[0].templates == {BIRD_LABEL: "Great Tit"}


@pytest.mark.parametrize("source", ["{{ nope(", "{{ states('sensor.missing') | float }}"])
async def test_broken_template_never_breaks_the_preview(hass, hass_ws_client, source):
    websocket_api.async_register_command(hass, ws.ws_preview_render)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/preview/render",
            "view_config": {
                "layout": LAYOUT_GRID_2X2,
                "widgets": [{"type": "text", "slot": 0, "label": source, "options": {"text": "x"}}],
            },
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
