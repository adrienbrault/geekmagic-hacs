"""Fetch and decode the pictures widgets draw (media-player album art).

Shared by the coordinator (the image uploaded to the device) and the
panel's websocket preview, so both resolve a player's ``entity_picture``
through the exact same rules and can't drift apart.
"""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url
from PIL import Image

if TYPE_CHECKING:
    from homeassistant.components.media_player import MediaPlayerEntity
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Path of HA's media-player image proxy (``MediaPlayerImageView``); the
# ``entity_picture`` of a player whose art isn't remotely accessible.
MEDIA_PROXY_PREFIX = "/api/media_player_proxy/"
# Upper bound, in seconds, for one picture fetch (in-process or over HTTP).
IMAGE_FETCH_TIMEOUT = 10


class PictureFetchError(Exception):
    """A picture could not be fetched.

    ``url`` is what was tried — the picture itself for an in-process
    read, the full URL for an HTTP fetch — and ``reason`` says why.
    """

    def __init__(self, url: str, reason: str) -> None:
        """Initialize with the URL that was tried and the failure reason."""
        super().__init__(reason)
        self.url = url
        self.reason = reason


def media_proxy_player(hass: HomeAssistant, picture: str) -> MediaPlayerEntity | None:
    """Return the player behind a ``/api/media_player_proxy/<id>`` picture.

    The player is taken from the path, not from the widget's entity: a
    wrapper (universal / group player) republishes its child's proxy
    path, and only the child can serve that art. Returns None for any
    other picture (browse-media proxy paths included), or when the
    media_player component or the entity isn't loaded — callers then
    fall back to fetching the picture over HTTP.
    """
    # Lazy, like the camera fetch: media_player loads only when used.
    from homeassistant.components.media_player import DATA_COMPONENT  # noqa: PLC0415

    path = urlsplit(picture).path
    if not path.startswith(MEDIA_PROXY_PREFIX):
        return None
    player_id = path.removeprefix(MEDIA_PROXY_PREFIX)
    if not player_id or "/" in player_id:
        return None
    if (component := hass.data.get(DATA_COMPONENT)) is None:
        return None
    return component.get_entity(player_id)


async def async_read_player_art(player: MediaPlayerEntity) -> bytes | None:
    """Read a player's current art the way HA's media-player proxy does."""
    async with asyncio.timeout(IMAGE_FETCH_TIMEOUT):
        image_data, _content_type = await player.async_get_media_image()
    return image_data


async def async_fetch_media_art(hass: HomeAssistant, picture: str) -> bytes:
    """Fetch the album art a media player publishes as ``entity_picture``.

    - HA's own media-player proxy path is read in-process from the player
      entity, exactly as the proxy view does. Going over HTTP instead
      needs a base URL HA can reach itself on, which ``get_url()`` cannot
      always provide (issue #98).
    - Absolute ``http(s)://`` pictures (Music Assistant, certain
      Spotify/Sonos configs) are fetched directly.
    - Other internal paths are joined with HA's base URL and fetched.

    Raises ``NoURLAvailableError`` when an internal path has no base URL
    to join, and ``PictureFetchError`` for every other failure.
    """
    if (player := media_proxy_player(hass, picture)) is not None:
        try:
            image_data = await async_read_player_art(player)
        except Exception as e:
            raise PictureFetchError(picture, str(e) or type(e).__name__) from e
        if not image_data:
            raise PictureFetchError(picture, "player returned no image")
        _LOGGER.debug(
            "Read album art in-process from %s: %d bytes", player.entity_id, len(image_data)
        )
        return image_data

    if picture.startswith(("http://", "https://")):
        image_url = picture
    elif picture.startswith("/"):
        image_url = f"{get_url(hass).rstrip('/')}/{picture.lstrip('/')}"
    else:
        raise PictureFetchError(picture, f"unsupported entity_picture scheme: {picture[:40]!r}")

    try:
        # HA's managed session, so media proxy requests carry the right
        # auth/cookies and SSL handling.
        session = async_get_clientsession(hass)
        async with session.get(
            image_url, timeout=ClientTimeout(total=IMAGE_FETCH_TIMEOUT)
        ) as response:
            status = response.status
            image_data = await response.read() if status == 200 else None
    except Exception as e:
        raise PictureFetchError(image_url, str(e) or type(e).__name__) from e
    if image_data is None:
        raise PictureFetchError(image_url, f"HTTP {status}")
    return image_data


def decode_image(image_bytes: bytes) -> Image.Image:
    """Decode fetched image bytes eagerly.

    ``Image.open`` is lazy and only reads the header — the actual decode
    would otherwise happen later in widget render code, where there is no
    logging hook and a corrupt image silently downgrades to a text
    fallback. ``.load()`` forces the decode so errors raise here.
    """
    decoded = Image.open(BytesIO(image_bytes))
    decoded.load()
    return decoded
