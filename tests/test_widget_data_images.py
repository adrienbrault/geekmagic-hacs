"""Image fetching through the widget-data resolver.

Camera frames and album art are one need (``DataNeeds.image_source``)
and one fetcher. The rules it has to get right are all about failure:
what survives a bad fetch, what gets evicted, and how loudly. A
regression in URL handling shipped to production as issue #98, so the
matrix below is deliberately exhaustive.

Everything is asserted through the resolver's own interface —
``async_prefetch`` then ``build_states`` — rather than its caches, so
the tests describe what a widget ends up rendering.
"""

import io
import logging
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_WIDGETS,
    LAYOUT_FULLSCREEN,
    THEME_WATCHOS,
)
from custom_components.geekmagic.views import build_layout
from custom_components.geekmagic.widget_data import WidgetDataResolver

MEDIA_ENTITY = "media_player.test_player"
CAMERA_ENTITY = "camera.front_door"
PICTURE_ENTITY = "image.doorbell"
INTERNAL_PICTURE = "/api/media_player_proxy/media_player.test_player?token=abc"
EXTERNAL_HTTPS_PICTURE = "https://i.scdn.co/image/test.jpg"
EXTERNAL_HTTP_PICTURE = "http://example.com/cover.jpg"
BASE_URL = "https://example.com"
INTERNAL_FULL_URL = f"{BASE_URL}/api/media_player_proxy/media_player.test_player?token=abc"

RESOLVER_LOGGER = "custom_components.geekmagic.widget_data"


def png_bytes(size: tuple[int, int] = (10, 10)) -> bytes:
    """Valid PNG bytes — what a successful fetch returns."""
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


PNG = png_bytes()


def image_layout(widget_type: str, entity_id: str):
    """A one-slot screen holding a single image-bearing widget."""
    return build_layout(
        {
            CONF_LAYOUT: LAYOUT_FULLSCREEN,
            CONF_WIDGETS: [{"type": widget_type, "slot": 0, "entity_id": entity_id}],
        },
        default_theme=THEME_WATCHOS,
    )


@pytest.fixture
def layout():
    """The default subject: one media player widget."""
    return image_layout("media", MEDIA_ENTITY)


@pytest.fixture
def resolver(hass):
    """A resolver with a deterministic base URL for internal picture paths."""
    hass.config.internal_url = BASE_URL
    hass.config.external_url = None
    return WidgetDataResolver(hass)


def _set_media_state(hass, entity_picture: str | None, entity_id: str = MEDIA_ENTITY) -> None:
    """Set the entity state with the given entity_picture attribute."""
    attrs = {}
    if entity_picture is not None:
        attrs["entity_picture"] = entity_picture
    hass.states.async_set(entity_id, "playing", attrs)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """All WARNING-level records from the resolver logger."""
    return [r for r in caplog.records if r.name == RESOLVER_LOGGER and r.levelno == logging.WARNING]


def _image(resolver, layout):
    """The image the single widget on ``layout`` would render."""
    return resolver.build_states(layout)[0].image


@pytest.fixture(autouse=True)
def _debug_logging(caplog: pytest.LogCaptureFixture):
    """Capture the resolver's DEBUG output so silence is provable."""
    caplog.set_level(logging.DEBUG, logger=RESOLVER_LOGGER)


class TestPictureSources:
    """Where the bytes come from."""

    async def test_internal_path_is_joined_with_the_base_url(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """Internal /api/... entity_picture is joined with get_url() and fetched."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)

        await resolver.async_prefetch(layout)

        assert _image(resolver, layout).size == (10, 10)
        assert _warnings(caplog) == []

    async def test_absolute_https_is_fetched_directly(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """https:// entity_picture is fetched without prepending base_url."""
        _set_media_state(hass, EXTERNAL_HTTPS_PICTURE)
        aioclient_mock.get(EXTERNAL_HTTPS_PICTURE, content=PNG, status=200)

        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is not None
        assert _warnings(caplog) == []

    async def test_absolute_http_is_fetched_directly(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """http:// entity_picture is also fetched directly."""
        _set_media_state(hass, EXTERNAL_HTTP_PICTURE)
        aioclient_mock.get(EXTERNAL_HTTP_PICTURE, content=PNG, status=200)

        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is not None
        assert _warnings(caplog) == []

    async def test_camera_entity_goes_through_the_camera_api(self, resolver, aioclient_mock):
        """A ``camera.*`` source is a frame grab, not an HTTP fetch."""
        camera_layout = image_layout("camera", CAMERA_ENTITY)
        frame = MagicMock(content=PNG)

        with patch(
            "homeassistant.components.camera.async_get_image", return_value=frame
        ) as get_image:
            await resolver.async_prefetch(camera_layout)

        get_image.assert_called_once()
        assert _image(resolver, camera_layout).size == (10, 10)
        assert aioclient_mock.call_count == 0

    async def test_camera_widget_accepts_a_non_camera_picture_source(
        self, hass, resolver, aioclient_mock, caplog
    ):
        """One fetcher for both widgets: a camera cell can show any picture entity.

        The camera widget used to accept internal paths only; it now
        follows the same (wider) rules as album art.
        """
        picture_layout = image_layout("camera", PICTURE_ENTITY)
        _set_media_state(hass, EXTERNAL_HTTPS_PICTURE, entity_id=PICTURE_ENTITY)
        aioclient_mock.get(EXTERNAL_HTTPS_PICTURE, content=PNG, status=200)

        await resolver.async_prefetch(picture_layout)

        assert _image(resolver, picture_layout) is not None
        assert _warnings(caplog) == []


class TestFetchFailures:
    """What survives a bad fetch, and how loudly."""

    async def test_http_404_drops_the_image_and_warns_once(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """A 404 evicts cached bytes and logs WARNING; a second 404 logs only DEBUG."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)
        await resolver.async_prefetch(layout)
        assert _image(resolver, layout) is not None

        aioclient_mock.clear_requests()
        aioclient_mock.get(INTERNAL_FULL_URL, status=404)
        caplog.clear()
        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is None
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert "HTTP 404" in warnings[0].message
        assert INTERNAL_FULL_URL in warnings[0].message

        caplog.clear()
        await resolver.async_prefetch(layout)
        assert _warnings(caplog) == []

    async def test_http_401_warns_once(self, hass, resolver, layout, aioclient_mock, caplog):
        """A 401 produces one WARNING containing the status and URL."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, status=401)

        await resolver.async_prefetch(layout)

        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert "HTTP 401" in warnings[0].message
        assert INTERNAL_FULL_URL in warnings[0].message

    async def test_no_url_available_is_skipped_silently(
        self, hass, resolver, layout, aioclient_mock, caplog, monkeypatch
    ):
        """When get_url() raises, the entity is skipped and the last image stands."""
        from homeassistant.helpers.network import NoURLAvailableError

        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)
        await resolver.async_prefetch(layout)

        def _raise(_hass):
            raise NoURLAvailableError

        monkeypatch.setattr("custom_components.geekmagic.widget_data.get_url", _raise)
        caplog.clear()
        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is not None  # stale image kept
        assert _warnings(caplog) == []

    async def test_unsupported_scheme_warns_once(self, hass, resolver, layout, caplog):
        """data: URLs and other unrecognised schemes produce a single WARNING."""
        _set_media_state(hass, "data:image/png;base64,iVBORw0KGgo=")

        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is None
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert "unsupported entity_picture scheme" in warnings[0].message

        caplog.clear()
        await resolver.async_prefetch(layout)
        assert _warnings(caplog) == []

    async def test_network_exception_warns_once(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """Network-level exceptions (timeouts etc.) take the same warn-once path."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, exc=TimeoutError("slow"))

        await resolver.async_prefetch(layout)

        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert MEDIA_ENTITY in warnings[0].message
        assert INTERNAL_FULL_URL in warnings[0].message

        caplog.clear()
        await resolver.async_prefetch(layout)
        assert _warnings(caplog) == []

    async def test_success_rearms_the_warning(self, hass, resolver, layout, aioclient_mock, caplog):
        """A successful fetch clears the warned flag so the next failure warns again."""
        _set_media_state(hass, INTERNAL_PICTURE)

        aioclient_mock.get(INTERNAL_FULL_URL, status=500)
        await resolver.async_prefetch(layout)
        assert len(_warnings(caplog)) == 1

        aioclient_mock.clear_requests()
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)
        caplog.clear()
        await resolver.async_prefetch(layout)
        assert _warnings(caplog) == []
        assert _image(resolver, layout) is not None

        aioclient_mock.clear_requests()
        aioclient_mock.get(INTERNAL_FULL_URL, status=500)
        caplog.clear()
        await resolver.async_prefetch(layout)
        assert len(_warnings(caplog)) == 1

    async def test_missing_entity_picture_clears_the_image(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """No entity_picture → genuinely no art: clear the image, no WARNING."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)
        await resolver.async_prefetch(layout)

        _set_media_state(hass, None)
        caplog.clear()
        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is None
        assert _warnings(caplog) == []

    async def test_missing_entity_picture_rearms_the_warning(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """Losing the picture resets the warn-once flag, like a success does."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, status=500)
        await resolver.async_prefetch(layout)
        assert len(_warnings(caplog)) == 1

        _set_media_state(hass, None)
        await resolver.async_prefetch(layout)

        _set_media_state(hass, INTERNAL_PICTURE)
        caplog.clear()
        await resolver.async_prefetch(layout)
        assert len(_warnings(caplog)) == 1

    async def test_unknown_entity_keeps_the_last_image(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """An entity that has gone missing is a hiccup, not a decision."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=PNG, status=200)
        await resolver.async_prefetch(layout)

        hass.states.async_remove(MEDIA_ENTITY)
        caplog.clear()
        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is not None
        assert _warnings(caplog) == []

    async def test_camera_failure_keeps_the_last_frame(self, resolver, caplog):
        """A camera that fails to answer costs freshness, not the cell."""
        camera_layout = image_layout("camera", CAMERA_ENTITY)
        with patch(
            "homeassistant.components.camera.async_get_image", return_value=MagicMock(content=PNG)
        ):
            await resolver.async_prefetch(camera_layout)

        caplog.clear()
        with patch(
            "homeassistant.components.camera.async_get_image", side_effect=RuntimeError("no camera")
        ):
            await resolver.async_prefetch(camera_layout)

        assert _image(resolver, camera_layout) is not None
        assert _warnings(caplog) == []


class TestNoNeeds:
    """A screen that declares no image need pays nothing."""

    async def test_layout_without_image_widgets_makes_no_requests(
        self, resolver, aioclient_mock, caplog
    ):
        clock_layout = build_layout(
            {CONF_LAYOUT: LAYOUT_FULLSCREEN, CONF_WIDGETS: [{"type": "clock", "slot": 0}]},
            default_theme=THEME_WATCHOS,
        )

        await resolver.async_prefetch(clock_layout)

        assert aioclient_mock.call_count == 0
        assert resolver.build_states(clock_layout)[0].image is None
        assert _warnings(caplog) == []


class TestDecode:
    """Bytes are decoded where the failure can still be logged."""

    async def test_undecodable_bytes_are_logged_and_evicted(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        """``Image.open`` is lazy, so the decode is forced here rather than in a cell."""
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=b"not an image", status=200)
        await resolver.async_prefetch(layout)

        assert _image(resolver, layout) is None
        warnings = _warnings(caplog)
        assert len(warnings) == 1
        assert "Failed to decode image" in warnings[0].message

        # Evicted: a second build does not re-decode the same bad bytes.
        caplog.clear()
        assert _image(resolver, layout) is None
        assert _warnings(caplog) == []

    async def test_valid_bytes_decode_to_an_image(
        self, hass, resolver, layout, aioclient_mock, caplog
    ):
        _set_media_state(hass, INTERNAL_PICTURE)
        aioclient_mock.get(INTERNAL_FULL_URL, content=png_bytes((24, 18)), status=200)
        await resolver.async_prefetch(layout)

        image = _image(resolver, layout)

        assert image is not None
        assert image.size == (24, 18)
        assert _warnings(caplog) == []
