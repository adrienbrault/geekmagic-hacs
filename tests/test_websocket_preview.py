"""Tests for preview entity resolution matching production rendering.

The websocket preview and the coordinator both snapshot widget entity
dependencies through ``build_entity_states``, and both fetch album art
through ``entity_images.async_fetch_media_art``; these tests pin that
shared contract so the editor preview and the deployed dashboard can't
drift apart again.
"""

import asyncio
import base64
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerState
from homeassistant.setup import async_setup_component
from PIL import Image
from pytest_homeassistant_custom_component.common import setup_test_component_platform

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import LAYOUT_FULLSCREEN, THEME_WATCHOS
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.htmldoc import CellContext
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.preview import MockHass
from custom_components.geekmagic.websocket import (
    _build_preview_widget_states,
    async_register_websocket_commands,
)
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


class _BrokenEntitiesWidget(TextWidget):
    """A widget whose dependency list is not a list of entity ids."""

    def __init__(self, config: WidgetConfig, entities: Any) -> None:
        super().__init__(config)
        self._entities = entities

    def get_entities(self) -> list[str]:
        if isinstance(self._entities, Exception):
            raise self._entities
        return self._entities


class TestBuildEntityStatesGuard:
    """One widget's broken entity list never fails the whole frame (issue #183)."""

    @pytest.mark.parametrize(
        "entities",
        [
            [{"entity_id": "sensor.other"}],  # unhashable id
            RuntimeError("boom"),
        ],
    )
    def test_broken_entity_list_is_contained(self, entities, caplog):
        widget = _BrokenEntitiesWidget(
            WidgetConfig(widget_type="text", slot=0, entity_id="sensor.temp"), entities
        )
        primary, additional = build_entity_states(make_hass().states.get, widget)
        assert primary is not None
        assert primary.entity_id == "sensor.temp"
        assert additional == {}
        assert "failed to resolve its entities" in caplog.text

    def test_ids_before_the_bad_one_are_kept(self):
        widget = _BrokenEntitiesWidget(
            WidgetConfig(widget_type="text", slot=0), ["sensor.other", {"entity_id": "x"}]
        )
        _, additional = build_entity_states(make_hass().states.get, widget)
        assert set(additional) == {"sensor.other"}

    async def test_device_frame_survives_a_broken_widget(self, hass):
        """The coordinator still builds the frame: the other cells keep updating."""
        hass.states.async_set("sensor.temp", "21.5", {"friendly_name": "Room"})
        layout = Grid2x2()
        layout.set_widget(
            0, _BrokenEntitiesWidget(WidgetConfig(widget_type="text", slot=0), [{"x": 1}])
        )
        layout.set_widget(
            1, TextWidget(WidgetConfig(widget_type="text", slot=1, entity_id="sensor.temp"))
        )
        coordinator = GeekMagicCoordinator(hass, MagicMock(), {})
        states = await hass.async_add_executor_job(coordinator._build_widget_states, layout)
        assert states[0].entities == {}
        assert states[1].entity is not None
        assert states[1].entity.state == "21.5"


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


# --- Album art in the View Editor preview -----------------------------------
#
# The preview render (``geekmagic/preview/render``) resolves a media widget's
# art through ``entity_images.async_fetch_media_art`` — the coordinator's own
# path — so proxied art is read in-process from the player entity and other
# pictures go over HTTP, each bounded by ``PREVIEW_IMAGE_TIMEOUT``.

PREVIEW_PLAYER = "media_player.preview_player"
ART_RGB = (220, 30, 30)
EXTERNAL_ART_URL = "https://art.example/cover.png"


def _png(color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


ART_PNG = _png(ART_RGB)


class _PreviewArtPlayer(MediaPlayerEntity):
    """Player whose art HA serves only through its media_player proxy."""

    _attr_state = MediaPlayerState.PLAYING
    _attr_media_title = "Song"
    _attr_media_artist = "Artist"
    _attr_media_image_url = "http://art.invalid/cover.jpg"

    def __init__(self, *, art: bytes | None = ART_PNG, hang: bool = False) -> None:
        self._attr_name = "preview_player"
        self._art = art
        self._hang = hang
        self.image_calls = 0

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        self.image_calls += 1
        if self._hang:
            await asyncio.Event().wait()
        if self._art is None:
            return None, None
        return self._art, "image/png"


async def _setup_player(hass, player: _PreviewArtPlayer) -> None:
    setup_test_component_platform(hass, "media_player", [player])
    assert await async_setup_component(hass, "media_player", {"media_player": {"platform": "test"}})
    await hass.async_block_till_done()


async def _render_media_preview(hass, hass_ws_client) -> Image.Image:
    """Render a one-widget fullscreen media view through the websocket API."""
    async_register_websocket_commands(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "geekmagic/preview/render",
            "view_config": {
                "layout": LAYOUT_FULLSCREEN,
                "theme": THEME_WATCHOS,
                "widgets": [{"type": "media", "slot": 0, "entity_id": PREVIEW_PLAYER}],
            },
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    png = base64.b64decode(msg["result"]["image"])
    return Image.open(BytesIO(png)).convert("RGB")


def _shows_art(image: Image.Image) -> bool:
    """The art is full-bleed and the top of the cell stays unobstructed."""
    r, g, b = cast("tuple[int, int, int]", image.getpixel((120, 40)))
    return r > 150 and g < 80 and b < 80


async def test_preview_renders_proxied_album_art(hass, hass_ws_client, aioclient_mock):
    """Proxy art is read in-process from the player — no HTTP, no base URL."""
    player = _PreviewArtPlayer()
    await _setup_player(hass, player)
    state = hass.states.get(PREVIEW_PLAYER)
    assert state is not None
    assert state.attributes["entity_picture"].startswith(
        f"/api/media_player_proxy/{PREVIEW_PLAYER}?token="
    )

    image = await _render_media_preview(hass, hass_ws_client)

    assert _shows_art(image)
    assert player.image_calls == 1
    assert aioclient_mock.call_count == 0


async def test_preview_renders_external_album_art(hass, hass_ws_client, aioclient_mock):
    """An absolute entity_picture is fetched over HTTP, as on the device."""
    hass.states.async_set(
        PREVIEW_PLAYER,
        "playing",
        {"media_title": "Song", "media_artist": "Artist", "entity_picture": EXTERNAL_ART_URL},
    )
    aioclient_mock.get(EXTERNAL_ART_URL, content=ART_PNG)

    image = await _render_media_preview(hass, hass_ws_client)

    assert _shows_art(image)
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize(
    "player_kwargs",
    [
        pytest.param({"hang": True}, id="hangs"),
        pytest.param({"art": None}, id="no-image"),
        pytest.param({"art": b"not an image"}, id="undecodable"),
    ],
)
async def test_preview_falls_back_to_text_without_art(
    hass, hass_ws_client, aioclient_mock, monkeypatch, player_kwargs
):
    """A slow, missing or corrupt picture still renders — without the art."""
    monkeypatch.setattr("custom_components.geekmagic.websocket.PREVIEW_IMAGE_TIMEOUT", 0.05)
    player = _PreviewArtPlayer(**player_kwargs)
    await _setup_player(hass, player)

    started = time.monotonic()
    image = await _render_media_preview(hass, hass_ws_client)

    # The preview's own bound ends a hang, well before the fetch helper's 10s.
    assert time.monotonic() - started < 5
    assert not _shows_art(image)
    assert player.image_calls == 1
    assert aioclient_mock.call_count == 0
