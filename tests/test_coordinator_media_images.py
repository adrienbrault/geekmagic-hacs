"""Tests for the media-player album-art fetch path on the coordinator.

Covers _async_fetch_media_images and _decode_cached_image (the helper that
forces eager PIL decode so format errors surface where we can log them).

The fetch path had zero coverage before — a regression in URL handling
shipped to production as issue #98.
"""

import logging
from unittest.mock import AsyncMock, MagicMock

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

MEDIA_ENTITY = "media_player.test_player"
INTERNAL_PICTURE = "/api/media_player_proxy/media_player.test_player?token=abc"
EXTERNAL_HTTPS_PICTURE = "https://i.scdn.co/image/test.jpg"
EXTERNAL_HTTP_PICTURE = "http://example.com/cover.jpg"
BASE_URL = "https://example.com"
INTERNAL_FULL_URL = f"{BASE_URL}/api/media_player_proxy/media_player.test_player?token=abc"

COORDINATOR_LOGGER = "custom_components.geekmagic.coordinator"


@pytest.fixture
def device():
    """Mock GeekMagic device — coordinator only uses it for upload/brightness."""
    d = MagicMock()
    d.display_rendered_dashboard = AsyncMock()
    d.set_brightness = AsyncMock()
    return d


@pytest.fixture
async def coordinator(hass, device):
    """Coordinator with one media-player widget on a fullscreen layout."""
    # Use FULLSCREEN (1 slot) — simplest layout with one widget
    options = {
        CONF_REFRESH_INTERVAL: 30,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_SCREENS: [
            {
                "name": "Media",
                CONF_LAYOUT: LAYOUT_FULLSCREEN,
                CONF_WIDGETS: [
                    {"type": "media", "slot": 0, "entity_id": MEDIA_ENTITY},
                ],
            }
        ],
    }
    coord = GeekMagicCoordinator(hass, device, options)
    # Pin a deterministic base URL so get_url() returns BASE_URL
    hass.config.internal_url = BASE_URL
    hass.config.external_url = None
    return coord


def _set_media_state(hass, entity_picture: str | None) -> None:
    """Set the media player state with the given entity_picture attribute."""
    attrs = {}
    if entity_picture is not None:
        attrs["entity_picture"] = entity_picture
    hass.states.async_set(MEDIA_ENTITY, "playing", attrs)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """All WARNING-level records from the coordinator logger."""
    return [
        r for r in caplog.records if r.name == COORDINATOR_LOGGER and r.levelno == logging.WARNING
    ]


async def test_fetch_internal_path_succeeds(hass, coordinator, aioclient_mock, caplog):
    """Internal /api/... entity_picture is joined with get_url() and fetched."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, INTERNAL_PICTURE)
    aioclient_mock.get(INTERNAL_FULL_URL, content=b"PNG\x00data", status=200)

    await coordinator._async_fetch_media_images()

    assert coordinator._media_images[MEDIA_ENTITY] == b"PNG\x00data"
    assert MEDIA_ENTITY not in coordinator._media_image_warned
    assert _warnings(caplog) == []


async def test_fetch_absolute_https_succeeds(hass, coordinator, aioclient_mock, caplog):
    """https:// entity_picture is fetched directly without prepending base_url."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, EXTERNAL_HTTPS_PICTURE)
    aioclient_mock.get(EXTERNAL_HTTPS_PICTURE, content=b"jpeg-bytes", status=200)

    await coordinator._async_fetch_media_images()

    assert coordinator._media_images[MEDIA_ENTITY] == b"jpeg-bytes"
    assert _warnings(caplog) == []


async def test_fetch_absolute_http_succeeds(hass, coordinator, aioclient_mock, caplog):
    """http:// entity_picture is also fetched directly."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, EXTERNAL_HTTP_PICTURE)
    aioclient_mock.get(EXTERNAL_HTTP_PICTURE, content=b"png-bytes", status=200)

    await coordinator._async_fetch_media_images()

    assert coordinator._media_images[MEDIA_ENTITY] == b"png-bytes"
    assert _warnings(caplog) == []


async def test_http_404_drops_cache_and_warns_once(hass, coordinator, aioclient_mock, caplog):
    """A 404 evicts cached bytes and logs WARNING; a second 404 logs only DEBUG."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    coordinator._media_images[MEDIA_ENTITY] = b"stale"
    _set_media_state(hass, INTERNAL_PICTURE)
    aioclient_mock.get(INTERNAL_FULL_URL, status=404)

    await coordinator._async_fetch_media_images()

    assert MEDIA_ENTITY not in coordinator._media_images
    assert MEDIA_ENTITY in coordinator._media_image_warned
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "HTTP 404" in warnings[0].message
    assert INTERNAL_FULL_URL in warnings[0].message

    caplog.clear()
    await coordinator._async_fetch_media_images()
    assert _warnings(caplog) == []


async def test_http_401_warns_once(hass, coordinator, aioclient_mock, caplog):
    """A 401 produces one WARNING containing the status and URL."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, INTERNAL_PICTURE)
    aioclient_mock.get(INTERNAL_FULL_URL, status=401)

    await coordinator._async_fetch_media_images()

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "HTTP 401" in warnings[0].message
    assert INTERNAL_FULL_URL in warnings[0].message


async def test_no_url_available_skipped_silently(
    hass, coordinator, aioclient_mock, caplog, monkeypatch
):
    """When get_url() raises NoURLAvailableError, the entity is skipped quietly."""
    from homeassistant.helpers.network import NoURLAvailableError

    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, INTERNAL_PICTURE)

    def _raise(_hass):
        raise NoURLAvailableError

    # Patch the symbol as imported into coordinator's module namespace
    monkeypatch.setattr("custom_components.geekmagic.coordinator.get_url", _raise)

    await coordinator._async_fetch_media_images()

    assert MEDIA_ENTITY not in coordinator._media_images
    assert _warnings(caplog) == []


async def test_missing_entity_picture_clears_cache(hass, coordinator, caplog):
    """No entity_picture attribute → cache + warned-set both cleared, no WARNING."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    coordinator._media_images[MEDIA_ENTITY] = b"stale"
    coordinator._media_image_warned.add(MEDIA_ENTITY)
    _set_media_state(hass, None)

    await coordinator._async_fetch_media_images()

    assert MEDIA_ENTITY not in coordinator._media_images
    assert MEDIA_ENTITY not in coordinator._media_image_warned
    assert _warnings(caplog) == []


async def test_unsupported_scheme_warns_once(hass, coordinator, caplog):
    """data: URLs and other unrecognised schemes produce a single WARNING."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, "data:image/png;base64,iVBORw0KGgo=")

    await coordinator._async_fetch_media_images()

    assert MEDIA_ENTITY not in coordinator._media_images
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "unsupported entity_picture scheme" in warnings[0].message


async def test_recovery_after_failure_rearms_warning(hass, coordinator, aioclient_mock, caplog):
    """A successful fetch clears the warned-flag so the next failure warns again."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, INTERNAL_PICTURE)

    # First call: fails → WARNING
    aioclient_mock.get(INTERNAL_FULL_URL, status=500)
    await coordinator._async_fetch_media_images()
    assert len(_warnings(caplog)) == 1
    assert MEDIA_ENTITY in coordinator._media_image_warned

    # Second call: succeeds → re-arms the warning
    aioclient_mock.clear_requests()
    aioclient_mock.get(INTERNAL_FULL_URL, content=b"ok", status=200)
    caplog.clear()
    await coordinator._async_fetch_media_images()
    assert _warnings(caplog) == []
    assert MEDIA_ENTITY not in coordinator._media_image_warned
    assert coordinator._media_images[MEDIA_ENTITY] == b"ok"

    # Third call: fails again → fresh WARNING (not silenced)
    aioclient_mock.clear_requests()
    aioclient_mock.get(INTERNAL_FULL_URL, status=500)
    caplog.clear()
    await coordinator._async_fetch_media_images()
    assert len(_warnings(caplog)) == 1


async def test_network_exception_warns_once(hass, coordinator, aioclient_mock, caplog):
    """Network-level exceptions (timeouts etc.) take the same warn-once path."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    _set_media_state(hass, INTERNAL_PICTURE)
    aioclient_mock.get(INTERNAL_FULL_URL, exc=TimeoutError("slow"))

    await coordinator._async_fetch_media_images()
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    # Message should reference the entity and URL; exception text or class name appears
    assert MEDIA_ENTITY in warnings[0].message
    assert INTERNAL_FULL_URL in warnings[0].message

    # Second failure is silenced
    caplog.clear()
    await coordinator._async_fetch_media_images()
    assert _warnings(caplog) == []


async def test_no_media_widgets_is_noop(hass, device, aioclient_mock, caplog):
    """A coordinator with no media widgets makes no HTTP calls."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    options = {
        CONF_REFRESH_INTERVAL: 30,
        CONF_SCREEN_CYCLE_INTERVAL: 0,
        CONF_SCREENS: [
            {
                "name": "Clock",
                CONF_LAYOUT: LAYOUT_FULLSCREEN,
                CONF_WIDGETS: [{"type": "clock", "slot": 0}],
            }
        ],
    }
    coord = GeekMagicCoordinator(hass, device, options)

    await coord._async_fetch_media_images()

    assert aioclient_mock.call_count == 0
    assert coord._media_images == {}


async def test_decode_failure_logs_and_evicts(coordinator, caplog):
    """_decode_cached_image returns None, logs WARNING, evicts bad bytes."""
    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    coordinator._media_images[MEDIA_ENTITY] = b"not an image"

    result = coordinator._decode_cached_image(
        MEDIA_ENTITY, coordinator._media_images[MEDIA_ENTITY], "media"
    )

    assert result is None
    assert MEDIA_ENTITY not in coordinator._media_images
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "Failed to decode media image" in warnings[0].message


async def test_decode_success_returns_image(coordinator, caplog):
    """_decode_cached_image returns a PIL Image with valid PNG bytes; no log."""
    import io

    caplog.set_level(logging.DEBUG, logger=COORDINATOR_LOGGER)
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    result = coordinator._decode_cached_image(MEDIA_ENTITY, png_bytes, "media")

    assert result is not None
    assert result.size == (10, 10)
    assert _warnings(caplog) == []
