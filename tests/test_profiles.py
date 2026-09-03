"""Tests for firmware profile adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.geekmagic.const import (
    MODEL_PRO,
    MODEL_SD_PRO,
    MODEL_ULTRA,
    MODEL_WEATHER_CLOCK_LEGACY,
)
from custom_components.geekmagic.models import RenderedDashboardRequest
from custom_components.geekmagic.profiles import (
    SdProProfile,
    StockProProfile,
    StockUltraProfile,
    WeatherClockLegacyProfile,
    detect_firmware_profile,
)
from custom_components.geekmagic.transport import DeviceTransport


class FakeTransport(DeviceTransport):
    """Minimal transport fake for profile adapter tests."""

    def __init__(
        self,
        json_by_path: dict[str, dict[str, object]] | None = None,
        text_by_path: dict[str, str] | None = None,
    ) -> None:
        """Initialize fake transport responses."""
        self.host = "192.168.1.100"
        self.base_url = "http://192.168.1.100"
        self._session = None
        self._owns_session = True
        self.json_by_path = json_by_path or {}
        self.text_by_path = text_by_path or {}
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

    async def get_text(
        self,
        path: str,
        request_timeout: aiohttp.ClientTimeout | None = None,
    ) -> str:
        """Return configured text or raise 404."""
        if path not in self.text_by_path:
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=404,
                message="Not Found",
            )
        return self.text_by_path[path]

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
        ("/set?i_i=1&gif_loop=1&autoplay=1", "album display update"),
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
        "/set?i_i=1&gif_loop=1&autoplay=1",
        "/set?theme=4",
        "/set?enter=-1",
        "/set?page=1",
        "/set?enter=-1",
    ]


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


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_reads_state_and_pushes_to_photo_slot_1() -> None:
    """Legacy Weather Clock profile polls /home?num= and drives Photo mode + slot 1.

    Photo mode as the gate for slot visibility was confirmed against real
    hardware: setting the GIF selector alone did nothing until themeselect
    was also switched to Photo (2).
    """
    transport = FakeTransport(
        text_by_path={
            "/home?num=1": "2",
            "/home?num=8": "71",
        }
    )
    profile = WeatherClockLegacyProfile(transport)

    assert profile.capabilities.profile_id == MODEL_WEATHER_CLOCK_LEGACY
    assert profile.capabilities.custom_image_theme == 2
    assert profile.capabilities.brightness_range == (2, 99)

    state = await profile.get_state()
    assert state.theme == 2
    assert state.brightness == 71
    assert state.current_image is None
    assert await profile.get_brightness() == 71

    space = await profile.get_space()
    assert space.total == 0
    assert space.free == 0

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    # Uploads always go to slot 1 (file1.jpg) regardless of the caller's
    # filename, matching the device's own client-side JS per slot. The
    # slots are pinned on the first push even though the readback already
    # reported Photo mode; the mode switch itself is skipped because of it.
    assert transport.uploads == [("/upload", "imageFile", b"jpeg", "file1.jpg", "image/jpeg")]
    assert transport.checked == [
        ("/file1-switch?getstate=1", "enable photo slot 1"),
        ("/file2-switch?getstate=0", "disable file2"),
        ("/file3-switch?getstate=0", "disable file3"),
        ("/file4-switch?getstate=0", "disable file4"),
        ("/file5-switch?getstate=0", "disable file5"),
    ]


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_switches_to_photo_mode_on_first_push() -> None:
    """With no readback yet, the first push pins the slots and selects Photo mode."""
    transport = FakeTransport()
    profile = WeatherClockLegacyProfile(transport)

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    assert transport.checked == [
        ("/file1-switch?getstate=1", "enable photo slot 1"),
        ("/file2-switch?getstate=0", "disable file2"),
        ("/file3-switch?getstate=0", "disable file3"),
        ("/file4-switch?getstate=0", "disable file4"),
        ("/file5-switch?getstate=0", "disable file5"),
        ("/themeselect?getstate=2", "theme update"),
    ]
    assert profile.last_theme == 2
    assert profile.last_image == "file1.jpg"


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_skips_redundant_setup_once_in_photo_mode() -> None:
    """Second and later pushes skip the slot-isolation round-trips.

    The coordinator calls set_image() on every refresh cycle (as often as
    every few seconds); once already in Photo mode, only the upload itself
    is needed -- re-running the 5 extra HTTP calls every cycle would add
    real, avoidable latency on real hardware.
    """
    transport = FakeTransport()
    profile = WeatherClockLegacyProfile(transport)

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )
    first_push_calls = list(transport.checked)
    assert first_push_calls  # slots pinned + Photo mode selected

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    assert transport.uploads == [("/upload", "imageFile", b"jpeg", "file1.jpg", "image/jpeg")] * 2
    assert transport.checked == first_push_calls


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_reenters_photo_mode_after_readback() -> None:
    """A state poll that finds the device outside Photo mode re-arms the setup.

    The skip in set_image() trusts the cached theme. Without refreshing it
    from the device, a reboot or a manual mode change on the web UI would
    leave the integration uploading into a slot nobody can see.
    """
    transport = FakeTransport(text_by_path={"/home?num=1": "0", "/home?num=8": "50"})
    profile = WeatherClockLegacyProfile(transport)
    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )
    assert profile.last_theme == 2
    transport.checked.clear()

    # The device rebooted into Classic (or someone changed the mode by hand).
    state = await profile.get_state()
    assert state.theme == 0
    assert profile.last_theme == 0

    await profile.display_rendered_dashboard(
        RenderedDashboardRequest(image_data=b"jpeg", filename="dashboard.jpg")
    )

    # Slots stay pinned from the first push; only the mode switch is redone.
    assert transport.checked == [("/themeselect?getstate=2", "theme update")]
    assert profile.last_theme == 2


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_uses_own_brightness_and_reboot_paths() -> None:
    """Legacy Weather Clock brightness/reboot use its own non-/set paths."""
    transport = FakeTransport()
    profile = WeatherClockLegacyProfile(transport)

    await profile.set_brightness(150)
    await profile.reboot()

    assert transport.checked == [
        ("/updateLEDBrightness?ledBrightness=99", "brightness update"),
        ("/restart", "reboot"),
    ]


@pytest.mark.asyncio
async def test_weather_clock_legacy_profile_rejects_unsupported_operations() -> None:
    """Operations with no known endpoint on this firmware fail loudly, not silently."""
    transport = FakeTransport()
    profile = WeatherClockLegacyProfile(transport)

    with pytest.raises(NotImplementedError):
        await profile.navigate_next()
    with pytest.raises(NotImplementedError):
        await profile.get_album_settings()
    with pytest.raises(NotImplementedError):
        await profile.get_image_files()


@pytest.mark.asyncio
async def test_detects_weather_clock_legacy_profile_from_root_page_fingerprint() -> None:
    """Detection falls through to the legacy Weather Clock profile as a last resort."""
    transport = FakeTransport(
        text_by_path={
            "/": (
                '<select id="giflist" name="option">...</select>'
                "<form method='get' action='/connect'></form>"
            )
        }
    )

    profile = await detect_firmware_profile(transport)

    assert profile.capabilities.profile_id == MODEL_WEATHER_CLOCK_LEGACY


@pytest.mark.asyncio
async def test_detection_falls_back_to_unknown_when_no_fingerprint_matches() -> None:
    """Detection still falls back to unknown when nothing, including the root page, matches."""
    transport = FakeTransport(text_by_path={"/": "<html>not a recognized device</html>"})

    profile = await detect_firmware_profile(transport)

    assert profile.capabilities.profile_id == "unknown"
