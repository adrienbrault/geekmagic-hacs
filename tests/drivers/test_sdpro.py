"""Tests for SDProDriver (SD_PRO community firmware)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.const import (
    BRIGHTNESS_RANGE_SDPRO,
    MODEL_SDPRO,
    THEME_CUSTOM_IMAGE_SDPRO,
)
from custom_components.geekmagic.drivers.sdpro import SDProDriver


class FakeSession:
    """Tiny session double that returns a queued response per URL prefix."""

    def __init__(self):
        self.get_log: list[str] = []
        self.post_log: list[str] = []
        self._get_handlers: list[tuple[str, dict]] = []
        self._post_handlers: list[tuple[str, dict]] = []

    def queue_get(
        self,
        url_contains: str,
        json: dict | None = None,
        status: int = 200,
        raise_for_status_error: Exception | None = None,
    ) -> None:
        self._get_handlers.append(
            (url_contains, {"json": json, "status": status, "error": raise_for_status_error})
        )

    def queue_post(self, url_contains: str, status: int = 200) -> None:
        self._post_handlers.append((url_contains, {"status": status}))

    def _build_response(self, spec: dict):
        response = MagicMock()
        response.status = spec.get("status", 200)
        if spec.get("error"):
            response.raise_for_status = MagicMock(side_effect=spec["error"])
        else:
            response.raise_for_status = MagicMock()
        if spec.get("json") is not None:
            response.json = AsyncMock(return_value=spec["json"])
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)
        return response

    def get(self, url, **_kwargs):
        self.get_log.append(url)
        for needle, spec in self._get_handlers:
            if needle in url:
                return self._build_response(spec)
        return self._build_response({"json": {}})

    def post(self, url, **_kwargs):
        self.post_log.append(url)
        for needle, spec in self._post_handlers:
            if needle in url:
                return self._build_response(spec)
        return self._build_response({})


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def driver(session):
    return SDProDriver("http://192.168.1.100", session)


def test_capabilities(driver):
    assert driver.model == MODEL_SDPRO
    assert driver.custom_image_theme == THEME_CUSTOM_IMAGE_SDPRO
    assert driver.brightness_range == BRIGHTNESS_RANGE_SDPRO
    assert driver.supports_navigation is False
    assert driver.supports_on_demand_image is False


def test_is_custom_image_theme(driver):
    assert driver.is_custom_image_theme(2) is True
    assert driver.is_custom_image_theme(3) is False


@pytest.mark.asyncio
async def test_get_state(driver, session):
    session.queue_get("/config", json={"theme": 2, "brightness": 50, "freespace": 1024})
    state = await driver.get_state()
    assert state.theme == 2
    assert state.brightness == 50
    assert state.current_image is None


@pytest.mark.asyncio
async def test_get_brightness(driver, session):
    session.queue_get("/config", json={"brightness": 33})
    assert await driver.get_brightness() == 33


@pytest.mark.asyncio
async def test_set_brightness_uses_api_set(driver, session):
    await driver.set_brightness(50)
    assert any("/api/set?key=lcd_brightness&value=50" in url for url in session.get_log)


@pytest.mark.asyncio
async def test_set_brightness_clamps_to_sdpro_range(driver, session):
    await driver.set_brightness(150)
    assert any("value=99" in url for url in session.get_log)
    await driver.set_brightness(-5)
    assert any("value=2" in url for url in session.get_log)


@pytest.mark.asyncio
async def test_set_theme_uses_api_set(driver, session):
    await driver.set_theme(2)
    assert any("/api/set?key=theme&value=2" in url for url in session.get_log)


@pytest.mark.asyncio
async def test_set_image_not_supported(driver):
    with pytest.raises(NotImplementedError):
        await driver.set_image("dashboard.jpg")


@pytest.mark.asyncio
async def test_upload_uses_photo_upload(driver, session):
    await driver.upload(b"\xff\xd8\xff\xe0" + b"x" * 100, "dashboard.jpg")
    assert any("/photo/upload" in url for url in session.post_log)


@pytest.mark.asyncio
async def test_upload_and_display_workaround(driver, session):
    """Upload, disable other photos, enable ours, switch to Photo theme."""
    session.queue_get(
        "/photo/list",
        json={
            "files": [
                {"name": "dashboard.jpg", "enabled": False, "size": 1000},
                {"name": "vacation.jpg", "enabled": True, "size": 5000},
                {"name": "cat.gif", "enabled": True, "size": 3000},
            ],
            "total": 1_000_000,
            "used": 9000,
            "interval": 10,
        },
    )
    session.queue_get("/config", json={"theme": 0})

    await driver.upload_and_display(b"x" * 64, "dashboard.jpg")

    # Uploaded as canonical dashboard.jpg
    assert any("/photo/upload" in url for url in session.post_log)
    # Disabled the two other enabled photos
    assert any(
        "/photo/toggle" in u and "vacation.jpg" in u and "state=0" in u for u in session.get_log
    )
    assert any("/photo/toggle" in u and "cat.gif" in u and "state=0" in u for u in session.get_log)
    # Enabled dashboard.jpg
    assert any(
        "/photo/toggle" in u and "dashboard.jpg" in u and "state=1" in u for u in session.get_log
    )
    # Switched to Photo theme (2)
    assert any("/api/set?key=theme&value=2" in u for u in session.get_log)


@pytest.mark.asyncio
async def test_upload_and_display_skips_theme_when_already_set(driver, session):
    session.queue_get(
        "/photo/list",
        json={
            "files": [{"name": "dashboard.jpg", "enabled": True}],
            "total": 0,
            "used": 0,
            "interval": 10,
        },
    )
    session.queue_get("/config", json={"theme": 2})

    await driver.upload_and_display(b"x" * 64, "dashboard.jpg")

    # No theme write because device is already on theme 2
    assert not any("/api/set?key=theme" in u for u in session.get_log)


@pytest.mark.asyncio
async def test_delete_file_extracts_basename(driver, session):
    await driver.delete_file("/photo/vacation.jpg")
    assert any("/photo/delete?name=vacation.jpg" in u for u in session.get_log)
    await driver.delete_file("plainname.jpg")
    assert any("/photo/delete?name=plainname.jpg" in u for u in session.get_log)


@pytest.mark.asyncio
async def test_clear_images_deletes_each(driver, session):
    session.queue_get(
        "/photo/list",
        json={"files": [{"name": "a.jpg"}, {"name": "b.jpg"}]},
    )
    await driver.clear_images()
    assert any("/photo/delete?name=a.jpg" in u for u in session.get_log)
    assert any("/photo/delete?name=b.jpg" in u for u in session.get_log)


@pytest.mark.asyncio
async def test_reboot_swallows_connection_drop(driver, session):
    session.queue_get(
        "/restart",
        raise_for_status_error=aiohttp.ClientError("connection reset"),
    )
    # Must not raise.
    await driver.reboot()


@pytest.mark.asyncio
async def test_list_themes(driver, session):
    session.queue_get(
        "/theme/list",
        json={
            "interval": 10,
            "themes": [
                {"id": 0, "name": "Classic", "enabled": True},
                {"id": 1, "name": "Weather", "enabled": False},
                {"id": 2, "name": "Photo", "enabled": True},
            ],
        },
    )
    themes = await driver.list_themes()
    assert len(themes) == 3
    assert themes[0]["name"] == "Classic"


@pytest.mark.asyncio
async def test_disable_other_themes(driver, session):
    session.queue_get(
        "/theme/list",
        json={
            "themes": [
                {"id": 0, "name": "Classic", "enabled": True},
                {"id": 1, "name": "Weather", "enabled": True},
                {"id": 2, "name": "Photo", "enabled": True},
                {"id": 3, "name": "Dial", "enabled": False},
            ],
        },
    )

    disabled = await driver.disable_other_themes()

    # Photo (id=2, custom_image_theme) is kept enabled; Dial was already off
    assert sorted(disabled) == ["Classic", "Weather"]
    # Verify the toggle calls were the right ones
    assert any("/theme/toggle?id=0&state=0" in url for url in session.get_log)
    assert any("/theme/toggle?id=1&state=0" in url for url in session.get_log)
    # Photo theme was NOT touched
    assert not any("/theme/toggle?id=2" in url for url in session.get_log)


@pytest.mark.asyncio
async def test_disable_other_themes_handles_missing_endpoint(driver, session):
    session.queue_get(
        "/theme/list",
        raise_for_status_error=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=404, message="not found"
        ),
    )
    # Should not raise; returns empty list.
    disabled = await driver.disable_other_themes()
    assert disabled == []


@pytest.mark.asyncio
async def test_test_connection_success(driver, session):
    session.queue_get("/config", json={"brightness": 50, "freespace": 1024})
    result = await driver.test_connection()
    assert result.success is True


@pytest.mark.asyncio
async def test_test_connection_404(driver, session):
    session.queue_get(
        "/config",
        raise_for_status_error=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=404, message="not found"
        ),
    )
    result = await driver.test_connection()
    assert result.success is False
    assert result.error == "http_error"
