"""The panel preview plays an animated view on request.

``geekmagic/preview/render`` with ``animate`` returns the GIF a device with
its Animations switch on is sent (``test_preview_parity`` checks the bytes
against the device's upload); these tests pin the option's contract.
"""

import base64
from io import BytesIO
from itertools import count
from typing import Any, cast
from unittest.mock import patch

from homeassistant.components import websocket_api
from homeassistant.setup import async_setup_component
from PIL import Image, ImageChops

from custom_components.geekmagic.const import MAX_IMAGE_SIZE
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.websocket import ws_preview_render

# A red square fading in and out: a few flat colours, so GIF quantization
# barely moves a pixel.
PULSE_HTML = (
    "<style>@keyframes pulse { from { opacity: 1 } to { opacity: 0.2 } }</style>"
    '<div style="position: absolute; inset: 40px; background: #f00;'
    ' animation: pulse 1s linear infinite alternate"></div>'
)


def _view(*, animate: bool) -> dict[str, Any]:
    return {
        # One flat-colour cell: no antialiased text for the palette to shift
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [
            {"type": "html", "slot": 0, "options": {"html": PULSE_HTML, "animate": animate}},
        ],
    }


async def _client(hass, hass_ws_client):
    assert await async_setup_component(hass, "websocket_api", {})
    websocket_api.async_register_command(hass, ws_preview_render)
    return await hass_ws_client(hass)


_ids = count(1)


async def _render(client, view: dict[str, Any], **extra: Any) -> dict[str, Any]:
    await client.send_json(
        {"id": next(_ids), "type": "geekmagic/preview/render", "view_config": view, **extra}
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]


def _frames(result: dict[str, Any]) -> list[Image.Image]:
    image = Image.open(BytesIO(base64.b64decode(result["image"])))
    frames = []
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        frames.append(image.convert("RGB"))
    return frames


async def test_still_preview_says_the_view_can_animate(hass, hass_ws_client):
    """Without ``animate`` an animated view is still the PNG, flagged animatable."""
    client = await _client(hass, hass_ws_client)

    result = await _render(client, _view(animate=True))

    assert result["content_type"] == "image/png"
    assert result["animatable"] is True
    assert result["animated"] is False
    assert result["too_large"] is False
    assert result["gif_bytes"] is None
    assert base64.b64decode(result["image"])[:8] == b"\x89PNG\r\n\x1a\n"


async def test_animate_returns_a_gif_starting_on_the_still(hass, hass_ws_client):
    """The GIF loops through moving frames, the first one the still preview."""
    client = await _client(hass, hass_ws_client)
    view = _view(animate=True)
    still = await _render(client, view)

    result = await _render(client, view, animate=True)

    assert result["content_type"] == "image/gif"
    assert result["animated"] is True
    assert result["animatable"] is True
    assert result["too_large"] is False
    assert result["gif_bytes"] == len(base64.b64decode(result["image"]))
    assert result["max_bytes"] == MAX_IMAGE_SIZE
    # Same geometry as the still, so click-to-select keeps working
    assert result["slots"] == still["slots"]
    assert (result["width"], result["height"]) == (240, 240)
    frames = _frames(result)
    assert len(frames) > 1
    assert ImageChops.difference(frames[0], frames[-1]).getbbox() is not None, "nothing moves"
    # Frame 0 is the still, give or take the GIF palette (one per loop)
    (first_still,) = _frames(still)
    extrema = cast(
        "tuple[tuple[int, int], ...]", ImageChops.difference(frames[0], first_still).getextrema()
    )
    assert max(high for _, high in extrema) <= 8


async def test_animate_on_a_still_view_returns_the_png(hass, hass_ws_client):
    """A view with nothing animated answers ``animate`` with its PNG."""
    client = await _client(hass, hass_ws_client)
    view = _view(animate=False)
    still = await _render(client, view)

    result = await _render(client, view, animate=True)

    assert result["content_type"] == "image/png"
    assert result["animatable"] is False
    assert result["animated"] is False
    assert result["too_large"] is False
    assert result["image"] == still["image"]


async def test_animation_over_the_upload_budget_falls_back_to_the_still(hass, hass_ws_client):
    """Like the device: a GIF it would refuse becomes its first frame."""
    client = await _client(hass, hass_ws_client)
    view = _view(animate=True)
    still = await _render(client, view)

    with patch.object(Renderer, "to_gif", return_value=b"G" * (MAX_IMAGE_SIZE + 1)):
        result = await _render(client, view, animate=True)

    assert result["content_type"] == "image/png"
    assert result["animated"] is False
    assert result["too_large"] is True
    assert result["gif_bytes"] == MAX_IMAGE_SIZE + 1
    assert result["max_bytes"] == MAX_IMAGE_SIZE
    # The first frame of the animation is the still preview, byte for byte
    assert result["image"] == still["image"]


async def test_failed_animation_falls_back_to_the_still(hass, hass_ws_client):
    """An engine failure mid-loop still shows the view."""
    client = await _client(hass, hass_ws_client)
    view = _view(animate=True)
    still = await _render(client, view)

    with patch(
        "custom_components.geekmagic.layouts.base.Layout.render_animation", return_value=None
    ):
        result = await _render(client, view, animate=True)

    assert result["content_type"] == "image/png"
    assert result["animated"] is False
    assert result["too_large"] is False
    assert result["gif_bytes"] is None
    assert result["image"] == still["image"]
