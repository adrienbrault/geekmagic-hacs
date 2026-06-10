"""Tests for firmware profile adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.geekmagic.const import MODEL_PRO, MODEL_SD_PRO, MODEL_ULTRA
from custom_components.geekmagic.models import RenderedDashboardRequest
from custom_components.geekmagic.profiles import (
    SdProProfile,
    StockProProfile,
    StockUltraProfile,
    detect_firmware_profile,
)
from custom_components.geekmagic.transport import DeviceTransport


class FakeTransport(DeviceTransport):
    """Minimal transport fake for profile adapter tests."""

    def __init__(self, json_by_path: dict[str, dict[str, object]] | None = None) -> None:
        """Initialize fake transport responses."""
        self.host = "192.168.1.100"
        self.base_url = "http://192.168.1.100"
        self._session = None
        self._owns_session = True
        self.json_by_path = json_by_path or {}
        self.checked: list[tuple[str, str]] = []
        self.uploads: list[tuple[str, str, bytes, str, str]] = []

    async def get_json(
        self,
        path: str,
        request_timeout: aiohttp.ClientTimeout | None = None,
    ) -> dict[str, object]:
        """Return configured JSON or raise 404."""
        if path not in self.json_by_path:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=404,
                message="Not Found",
            )
        return self.json_by_path[path]

    async def get_checked(self, path: str, action: str) -> None:
        """Record checked GET requests."""
        self.checked.append((path, action))

    async def post_file(
        self,
        path: str,
        field_name: str,
        image_data: bytes,
        filename: str,
        content_type: str,
    ) -> None:
        """Record multipart uploads."""
        self.uploads.append((path, field_name, image_data, filename, content_type))


@pytest.mark.asyncio
async def test_ultra_profile_uploads_and_selects_direct_image() -> None:
    """Ultra stock profile uses theme 3 and direct image selection."""
    transport = FakeTransport(
        {
            "/app.json": {"theme": "3", "brt": "71", "img": "/image/old.jpg"},
            "/space.json": {"total": 1000, "free": 400},
            "/brt.json": {"brt": "71"},
        }
    )
    profile = StockUltraProfile(transport)

    assert profile.capabilities.profile_id == MODEL_ULTRA
    assert profile.capabilities.custom_image_theme == 3
    assert profile.capabilities.display_mechanism == "direct_image"

    state = await profile.get_state()
    assert state.theme == 3
    assert state.brightness == 71
    assert state.current_image == "/image/old.jpg"
    assert await profile.get_brightness() == 71

    space = await profile.get_space()
    assert space.total == 1000
    assert space.free == 400

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    assert transport.uploads == [
        ("/doUpload?dir=/image/", "file", b"jpeg", "dashboard.jpg", "image/jpeg")
    ]
    assert transport.checked == [
        ("/set?theme=3", "theme update"),
        ("/set?img=/image/dashboard.jpg", "image selection for /image/dashboard.jpg"),
    ]


@pytest.mark.asyncio
async def test_pro_profile_uses_picture_theme_without_buttons_by_default() -> None:
    """Pro stock profile uses theme 4 and does not press menu buttons by default."""
    transport = FakeTransport(
        {
            "/.sys/brt.json": {"brt": "85"},
            "/.sys/album.json": {"i_i": "5", "gif_loop": "2", "autoplay": "1"},
        }
    )
    profile = StockProProfile(transport)

    assert profile.capabilities.profile_id == MODEL_PRO
    assert profile.capabilities.custom_image_theme == 4
    assert profile.capabilities.display_mechanism == "picture_album"
    assert profile.capabilities.requires_managed_album is True
    assert await profile.get_brightness() == 85

    album = await profile.get_album_settings()
    assert album.interval == 5
    assert album.gif_loop == 2
    assert album.autoplay == 1

    await profile.set_image("dashboard.jpg")
    assert transport.checked == [
        ("/set?i_i=1&gif_loop=1&autoplay=0", "album display update"),
        ("/set?theme=4", "theme update"),
    ]


@pytest.mark.asyncio
async def test_pro_profile_menu_navigation_is_explicit() -> None:
    """Pro stock profile only presses buttons when the request opts in."""
    transport = FakeTransport()
    profile = StockProProfile(transport)

    with patch("custom_components.geekmagic.profiles.asyncio.sleep", new_callable=AsyncMock):
        await profile.set_image("dashboard.jpg", try_menu_navigation=True)

    assert [path for path, _action in transport.checked] == [
        "/set?i_i=1&gif_loop=1&autoplay=0",
        "/set?theme=4",
        "/set?enter=-1",
        "/set?page=1",
        "/set?enter=-1",
    ]


@pytest.mark.asyncio
async def test_pro_set_image_does_not_reenable_autoplay() -> None:
    """Regression test for issue #158: dashboard refresh must keep autoplay off.

    Each dashboard refresh calls set_image, which updates the album display
    settings. The integration manages the album with a single dashboard
    image, so it must send autoplay=0; sending autoplay=1 re-enabled the
    photo slideshow the user had disabled on the device (confirmed by the
    issue reporter's workaround on V3.4.82EN firmware).
    """
    transport = FakeTransport()
    profile = StockProProfile(transport)

    await profile.set_image("dashboard.jpg")

    assert ("/set?i_i=1&gif_loop=1&autoplay=0", "album display update") in transport.checked
    assert all("autoplay=1" not in path for path, _action in transport.checked)


@pytest.mark.asyncio
async def test_sdpro_profile_uses_photo_slideshow_operations() -> None:
    """SD_PRO profile owns config, upload, and slideshow toggles."""
    transport = FakeTransport(
        {
            "/config": {"theme": 1, "brightness": 100},
            "/photo/list": {
                "total": 10,
                "used": 2,
                "interval": 7,
                "files": [
                    {"name": "old.jpg", "size": 123, "enabled": True},
                    {"name": "dashboard.jpg", "size": 456, "enabled": False},
                ],
            },
            "/theme/list": {
                "interval": 30,
                "themes": [
                    {"id": 1, "name": "Weather", "enabled": True},
                    {"id": 2, "name": "Photo", "enabled": False},
                ],
            },
        }
    )
    profile = SdProProfile(transport)

    assert profile.capabilities.profile_id == MODEL_SD_PRO
    assert profile.capabilities.custom_image_theme == 2
    assert profile.capabilities.display_mechanism == "photo_slideshow"

    state = await profile.get_state()
    assert state.theme == 1
    assert state.brightness == 100

    await profile.set_brightness(150)
    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    assert transport.uploads == [("/photo/upload", "file", b"jpeg", "dashboard.jpg", "image/jpeg")]
    assert [path for path, _action in transport.checked] == [
        "/api/set?key=lcd_brightness&value=99",
        "/photo/toggle?name=old.jpg&state=0",
        "/photo/toggle?name=dashboard.jpg&state=1",
        "/theme/toggle?id=1&state=0",
        "/theme/toggle?id=2&state=1",
        "/photo/interval?val=1",
        "/api/set?key=theme&value=2",
    ]


@pytest.mark.asyncio
async def test_detects_sdpro_profile_from_theme_list() -> None:
    """Detection falls through to SD_PRO when stock paths are absent."""
    transport = FakeTransport({"/theme/list": {"themes": [{"id": 2, "name": "Photo"}]}})

    profile = await detect_firmware_profile(transport)

    assert profile.capabilities.profile_id == MODEL_SD_PRO
