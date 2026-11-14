"""The panel preview renders image widgets with their real picture."""

import base64
from io import BytesIO
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.setup import async_setup_component
from PIL import Image

from custom_components.geekmagic.websocket import ws_preview_render

IMAGE_URL = "https://example.com/preview.png"


def _png(color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16, 16), color).save(buf, format="PNG")
    return buf.getvalue()


def _image_view() -> dict[str, Any]:
    return {
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [
            {"type": "image", "slot": 0, "options": {"source": IMAGE_URL, "fit": "stretch"}}
        ],
    }


async def _ws_client(hass, hass_ws_client, token=None):
    assert await async_setup_component(hass, "websocket_api", {})
    websocket_api.async_register_command(hass, ws_preview_render)
    return await hass_ws_client(hass, token) if token else await hass_ws_client(hass)


async def test_preview_renders_image_widget_picture(hass, hass_ws_client, aioclient_mock):
    """The preview loads the picture instead of showing a placeholder."""
    aioclient_mock.get(IMAGE_URL, content=_png((0, 200, 0)))
    client = await _ws_client(hass, hass_ws_client)

    await client.send_json(
        {"id": 1, "type": "geekmagic/preview/render", "view_config": _image_view()}
    )
    msg = await client.receive_json()

    assert msg["success"], msg
    png = Image.open(BytesIO(base64.b64decode(msg["result"]["image"]))).convert("RGB")
    r, g, b = png.getpixel((120, 120))  # ty: ignore[not-iterable]
    assert g > 150
    assert r < 60
    assert b < 60
    assert aioclient_mock.call_count == 1


async def test_preview_requires_admin(
    hass, hass_ws_client, hass_read_only_access_token, aioclient_mock
):
    """A non-admin can't make HA fetch arbitrary URLs through the preview."""
    aioclient_mock.get(IMAGE_URL, content=_png((0, 200, 0)))
    client = await _ws_client(hass, hass_ws_client, hass_read_only_access_token)

    await client.send_json(
        {"id": 1, "type": "geekmagic/preview/render", "view_config": _image_view()}
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"
    assert aioclient_mock.call_count == 0
