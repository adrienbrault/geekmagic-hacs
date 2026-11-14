"""Coordinator wiring for image widgets and notify URL/path images.

The coordinator loads every image widget's source through the HA-wide
image cache before rendering, so a static picture is downloaded once per
refresh interval, not on every 10 s render tick.
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.widgets.camera import CameraWidget
from custom_components.geekmagic.widgets.image import ImageWidget

URL = "https://example.com/logo.png"


def png_bytes(color=(255, 0, 0)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
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


def _coordinator(hass, widgets=None) -> GeekMagicCoordinator:
    options = {
        CONF_REFRESH_INTERVAL: 10,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_SCREENS: [
            {
                "name": "Picture",
                CONF_LAYOUT: LAYOUT_FULLSCREEN,
                CONF_WIDGETS: widgets
                if widgets is not None
                else [{"type": "image", "slot": 0, "options": {"source": URL}}],
            }
        ],
    }
    device = MagicMock()
    device.set_theme_custom = AsyncMock()
    return GeekMagicCoordinator(hass, device, options)


async def test_image_widget_gets_its_picture(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass)

    await coord._async_gather_inputs(0)
    states = coord._build_widget_states(coord._layouts[0])

    assert states[0].image is not None
    assert states[0].image.getpixel((0, 0)) == (255, 0, 0)


async def test_picture_not_redownloaded_every_tick(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass)

    for _ in range(5):
        await coord._async_gather_inputs(0)
        clock.now += 10  # render ticks

    assert aioclient_mock.call_count == 1


async def test_widget_refresh_interval_honoured(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(
        hass, [{"type": "image", "slot": 0, "options": {"source": URL, "refresh": "5 min"}}]
    )

    await coord._async_gather_inputs(0)
    clock.now += 300
    await coord._async_gather_inputs(0)

    assert aioclient_mock.call_count == 2


async def test_manual_refresh_refetches(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass)
    await coord._async_gather_inputs(0)

    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.async_refresh_display()
    await coord._async_gather_inputs(0)

    assert aioclient_mock.call_count == 2


async def test_failed_load_shows_placeholder(hass, aioclient_mock, clock):
    aioclient_mock.get(URL, status=404)
    coord = _coordinator(hass)

    await coord._async_gather_inputs(0)
    states = coord._build_widget_states(coord._layouts[0])

    assert states[0].image is None


async def test_widget_without_source_fetches_nothing(hass, aioclient_mock, clock):
    coord = _coordinator(hass, [{"type": "image", "slot": 0, "options": {}}])
    await coord._async_gather_inputs(0)
    assert aioclient_mock.call_count == 0


async def test_local_file_source(hass, clock, tmp_path):
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "www").mkdir()
    hass.config.allowlist_external_dirs = {str((tmp_path / "www").resolve())}
    (tmp_path / "www" / "logo.png").write_bytes(png_bytes((0, 0, 255)))
    coord = _coordinator(
        hass, [{"type": "image", "slot": 0, "options": {"source": "/local/logo.png"}}]
    )

    await coord._async_gather_inputs(0)
    states = coord._build_widget_states(coord._layouts[0])

    assert states[0].image is not None
    assert states[0].image.getpixel((0, 0)) == (0, 0, 255)


# --- notify ------------------------------------------------------------------


@pytest.mark.parametrize("message", [None, "Alarm!"])
async def test_notify_url_uses_image_widget(hass, aioclient_mock, clock, message):
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass, [])
    coord._notification_data = {"image": URL, "message": message}

    await coord._async_gather_inputs(0)  # must not treat the URL as an entity
    await coord._async_gather_inputs(0)
    layout = coord._create_notification_layout(coord._notification_data)
    hero = layout.slots[0].widget
    states = coord._build_widget_states(layout)

    assert isinstance(hero, ImageWidget)
    assert hero.source == URL
    assert hero.fit == "contain"
    assert states[0].image is not None
    assert aioclient_mock.call_count == 1
    assert URL not in coord._inputs.camera_images


async def test_notify_image_url_field_wins_over_entity(hass, aioclient_mock, clock):
    """``image_url`` (the UI's free-text field) beats the ``image`` entity."""
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass, [])
    coord._notification_data = {"image_url": URL, "image": "camera.front_door"}

    with patch("homeassistant.components.camera.async_get_image", AsyncMock()) as get_image:
        await coord._async_gather_inputs(0)
    await coord._async_gather_inputs(0)
    hero = coord._create_notification_layout(coord._notification_data).slots[0].widget

    get_image.assert_not_called()
    assert isinstance(hero, ImageWidget)
    assert URL in coord._inputs.source_images


async def test_notify_image_url_is_always_a_source(hass, clock):
    """``image_url: alarm.png`` is a (rejected) path, never a camera entity."""
    coord = _coordinator(hass, [])
    hero = coord._create_notification_layout({"image_url": "alarm.png"}).slots[0].widget
    assert isinstance(hero, ImageWidget)
    assert hero.source == "alarm.png"


async def test_new_notification_refetches_its_picture(hass, aioclient_mock, clock):
    """A snapshot behind a fixed URL is fetched fresh for every notification."""
    aioclient_mock.get(URL, content=png_bytes())
    coord = _coordinator(hass, [])
    with patch.object(coord, "async_request_refresh", AsyncMock()):
        await coord.trigger_notification({"image_url": URL})
        await coord._async_gather_inputs(0)
        clock.now += 5
        await coord.trigger_notification({"image_url": URL})
        await coord._async_gather_inputs(0)
    if coord._notification_clear_handle is not None:
        coord._notification_clear_handle.cancel()

    assert aioclient_mock.call_count == 2


async def test_notify_entity_still_uses_camera_widget(hass, clock):
    coord = _coordinator(hass, [])
    layout = coord._create_notification_layout({"image": "camera.front_door"})
    hero = layout.slots[0].widget
    assert isinstance(hero, CameraWidget)
    assert hero.config.entity_id == "camera.front_door"


async def test_notify_without_image_uses_icon(hass, clock):
    coord = _coordinator(hass, [])
    layout = coord._create_notification_layout({"message": "Hi"})
    assert not isinstance(layout.slots[0].widget, (ImageWidget, CameraWidget))
