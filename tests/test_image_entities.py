"""The camera widget shows ``image`` entities (Frigate detections, issue #87).

An ``image.*`` entity's picture is read in-process from the entity — what
HA's own ``/api/image_proxy`` view does — so it needs no base URL. It goes
through the shared image cache: refetched when the entity publishes a new
picture (its state is ``image_last_updated``), not on every render tick,
and decoded under the same byte / pixel caps as Image-widget sources.
"""

import logging
from datetime import timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import websocket_api
from homeassistant.components.camera import Image as CameraImage
from homeassistant.components.image import ImageEntity
from homeassistant.helpers.network import NoURLAvailableError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from PIL import Image
from pytest_homeassistant_custom_component.common import setup_test_component_platform

from custom_components.geekmagic import image_source
from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.websocket import ws_preview_render
from custom_components.geekmagic.widgets import WIDGET_TYPE_SCHEMAS
from custom_components.geekmagic.widgets.camera import CameraWidget

from .test_preview_parity import _device_frame, _preview_frame

IMAGE_ENTITY = "image.front_camera_person"
CAMERA_ENTITY = "camera.front_door"


def png_bytes(color=(255, 0, 0), size=(8, 8)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    fake = FakeClock()
    with patch("custom_components.geekmagic.image_source.time.monotonic", fake):
        yield fake


@pytest.fixture(autouse=True)
def no_base_url(monkeypatch):
    """HA can't reach itself over HTTP: the picture must be read in-process."""

    def _raise(_hass, **_kwargs):
        raise NoURLAvailableError

    monkeypatch.setattr("custom_components.geekmagic.entity_images.get_url", _raise)


class _Detection(ImageEntity):
    """An image entity like Frigate's latest-detection snapshot."""

    def __init__(self, hass, data: bytes | None = None, exc: Exception | None = None) -> None:
        super().__init__(hass)
        self._attr_name = "front_camera_person"
        self._data = png_bytes() if data is None and exc is None else data
        self._exc = exc
        self._attr_image_last_updated = dt_util.utcnow()
        self.image_calls = 0

    async def async_image(self) -> bytes | None:
        self.image_calls += 1
        if self._exc is not None:
            raise self._exc
        return self._data

    def publish(self, data: bytes) -> None:
        """A new detection: new bytes and a new ``image_last_updated``."""
        self._data = data
        self._attr_image_last_updated = dt_util.utcnow() + timedelta(seconds=self.image_calls + 1)
        self.async_write_ha_state()


async def _setup_image(hass, entity: _Detection) -> None:
    setup_test_component_platform(hass, "image", [entity])
    assert await async_setup_component(hass, "image", {"image": {"platform": "test"}})
    await hass.async_block_till_done()
    assert hass.states.get(IMAGE_ENTITY) is not None


def _coordinator(hass, entity_id: str = IMAGE_ENTITY) -> GeekMagicCoordinator:
    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_SCREENS: [
            {
                "name": "Detections",
                CONF_LAYOUT: LAYOUT_FULLSCREEN,
                CONF_WIDGETS: [{"type": "camera", "slot": 0, "entity_id": entity_id}],
            }
        ],
    }
    device = MagicMock()
    device.set_theme_custom = AsyncMock()
    return GeekMagicCoordinator(hass, device, options)


async def _device_image(coord: GeekMagicCoordinator) -> Image.Image | None:
    """One render tick of the device path: gather inputs, then build states."""
    await coord._async_gather_inputs(0)
    return coord._build_widget_states(coord._layouts[0])[0].image


def _warnings(caplog) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.levelno >= logging.WARNING and r.name.startswith("custom_components.geekmagic")
    ]


# --- panel ------------------------------------------------------------------


def test_camera_widget_offers_image_entities():
    """The panel's entity picker filters on ``entity_domains``."""
    assert WIDGET_TYPE_SCHEMAS["camera"]["entity_domains"] == ["camera", "image"]


async def test_preview_shows_image_entity_like_the_device(hass, hass_ws_client, freezer, clock):
    """The editor preview draws the entity's picture, byte-identical to the device frame."""
    entity = _Detection(hass, png_bytes((0, 0, 255)))
    await _setup_image(hass, entity)
    websocket_api.async_register_command(hass, ws_preview_render)
    client = await hass_ws_client(hass)
    view_config = {
        "layout": LAYOUT_FULLSCREEN,
        "theme": "watchos",
        "widgets": [{"type": "camera", "slot": 0, "entity_id": IMAGE_ENTITY}],
    }

    device_png = await _device_frame(hass, view_config)
    preview_png = await _preview_frame(client, view_config)

    assert entity.image_calls >= 1
    center = Image.open(BytesIO(preview_png)).convert("RGB").getpixel((120, 120))
    assert center == (0, 0, 255), "the preview shows a placeholder, not the picture"
    assert preview_png == device_png


# --- device path --------------------------------------------------------------


async def test_device_shows_image_entity(hass, clock, aioclient_mock):
    entity = _Detection(hass, png_bytes((0, 0, 255)))
    await _setup_image(hass, entity)

    image = await _device_image(_coordinator(hass))

    assert image is not None
    assert image.getpixel((0, 0)) == (0, 0, 255)
    assert entity.image_calls == 1
    assert aioclient_mock.call_count == 0


async def test_image_entity_not_refetched_every_tick(hass, clock):
    entity = _Detection(hass)
    await _setup_image(hass, entity)
    coord = _coordinator(hass)

    for _ in range(5):
        assert await _device_image(coord) is not None
        clock.now += 10  # render ticks

    assert entity.image_calls == 1


async def test_new_detection_is_fetched(hass, clock):
    entity = _Detection(hass, png_bytes((255, 0, 0)))
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    await _device_image(coord)

    entity.publish(png_bytes((0, 255, 0)))
    clock.now += 10
    image = await _device_image(coord)

    assert entity.image_calls == 2
    assert image is not None
    assert image.getpixel((0, 0)) == (0, 255, 0)


async def test_unchanged_entity_refetched_after_max_age(hass, clock):
    """An entity that never bumps ``image_last_updated`` still refreshes."""
    entity = _Detection(hass)
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    await _device_image(coord)

    clock.now += image_source.ENTITY_MAX_AGE
    await _device_image(coord)

    assert entity.image_calls == 2


async def test_manual_refresh_refetches_image_entity(hass, clock):
    entity = _Detection(hass)
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    await _device_image(coord)

    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.async_refresh_display()
    await _device_image(coord)

    assert entity.image_calls == 2


@pytest.mark.parametrize(
    "entity_kwargs",
    [{"exc": RuntimeError("frigate offline")}, {"data": b""}],
    ids=["raises", "empty"],
)
async def test_fetch_failure_shows_placeholder_and_warns_once(hass, clock, caplog, entity_kwargs):
    entity = _Detection(hass, **entity_kwargs)
    await _setup_image(hass, entity)
    coord = _coordinator(hass)

    assert await _device_image(coord) is None
    assert len(_warnings(caplog)) == 1

    caplog.clear()
    clock.now += image_source.IMAGE_SOURCE_RETRY
    assert await _device_image(coord) is None
    assert entity.image_calls == 2  # retried after the back-off...
    assert _warnings(caplog) == []  # ...without another warning


async def test_new_detection_skips_the_failure_back_off(hass, clock):
    """A picture published after a failed read shows on the next tick."""
    entity = _Detection(hass, exc=RuntimeError("no detection yet"))
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    assert await _device_image(coord) is None

    entity._exc = None
    entity.publish(png_bytes((0, 255, 0)))
    clock.now += 10  # well inside IMAGE_SOURCE_RETRY
    image = await _device_image(coord)

    assert image is not None
    assert image.getpixel((0, 0)) == (0, 255, 0)


async def test_failed_refresh_keeps_last_picture(hass, clock):
    entity = _Detection(hass, png_bytes((0, 0, 255)))
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    await _device_image(coord)

    entity._exc = RuntimeError("frigate offline")
    entity.publish(b"")
    image = await _device_image(coord)

    assert image is not None
    assert image.getpixel((0, 0)) == (0, 0, 255)


async def test_missing_image_entity_shows_placeholder(hass, clock):
    assert await _device_image(_coordinator(hass)) is None


async def test_oversized_image_entity_rejected(hass, clock, caplog):
    await _setup_image(hass, _Detection(hass))

    with patch.object(image_source, "MAX_SOURCE_BYTES", 16):
        assert await _device_image(_coordinator(hass)) is None

    assert "larger than 16 bytes" in caplog.text


async def test_pixel_bomb_image_entity_rejected(hass, clock, caplog):
    await _setup_image(hass, _Detection(hass, png_bytes(size=(64, 64))))

    with patch.object(image_source, "MAX_DECODE_PIXELS", 1000):
        assert await _device_image(_coordinator(hass)) is None

    assert "too large to decode" in caplog.text


async def test_large_image_entity_downscaled(hass, clock):
    await _setup_image(hass, _Detection(hass, png_bytes(size=(2000, 1500))))

    image = await _device_image(_coordinator(hass))

    assert image is not None
    assert min(image.size) == image_source.MAX_SHORT_SIDE


async def test_notification_image_entity_read_in_process(hass, clock, aioclient_mock):
    entity = _Detection(hass, png_bytes((0, 0, 255)))
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    coord._notification_data = {"image": IMAGE_ENTITY, "message": "Person"}

    await coord._async_gather_inputs(0)
    layout = coord._create_notification_layout(coord._notification_data)
    image = coord._build_widget_states(layout)[0].image

    assert isinstance(layout.slots[0].widget, CameraWidget)
    assert image is not None
    assert image.getpixel((0, 0)) == (0, 0, 255)
    assert aioclient_mock.call_count == 0


async def test_new_notification_rereads_image_entity(hass, clock):
    """Each notification reads the entity afresh, as a notify URL is refetched."""
    entity = _Detection(hass)
    await _setup_image(hass, entity)
    coord = _coordinator(hass)
    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.trigger_notification({"image": IMAGE_ENTITY})
        await coord._async_gather_inputs(0)
        clock.now += 5
        await coord.trigger_notification({"image": IMAGE_ENTITY})
        await coord._async_gather_inputs(0)
    if coord._notification_clear_handle is not None:
        coord._notification_clear_handle.cancel()

    assert entity.image_calls == 2


# --- camera entities are unchanged ------------------------------------------------


async def test_camera_snapshot_still_fetched_every_tick(hass, clock):
    snapshot = CameraImage("image/png", png_bytes((0, 255, 0)))
    coord = _coordinator(hass, CAMERA_ENTITY)

    with patch(
        "homeassistant.components.camera.async_get_image", AsyncMock(return_value=snapshot)
    ) as get_image:
        first = await _device_image(coord)
        await _device_image(coord)

    assert get_image.await_count == 2
    assert coord._inputs.camera_images[CAMERA_ENTITY] == snapshot.content
    assert first is not None
    assert first.convert("RGB").getpixel((0, 0)) == (0, 255, 0)
