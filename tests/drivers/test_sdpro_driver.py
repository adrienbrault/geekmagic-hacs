"""Tests for the SD_PRO community firmware driver."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.drivers.sdpro import (
    DASHBOARD_INTERVAL_SECONDS,
    PHOTO_THEME,
    SdProDriver,
)

BASE_URL = "http://192.168.1.50"
HOST = "192.168.1.50"


@pytest.fixture
def response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock()
    return resp


@pytest.fixture
def session(response):
    sess = MagicMock()
    sess.get = MagicMock(return_value=response)
    sess.post = MagicMock(return_value=response)
    return sess


@pytest.fixture
def driver(session):
    return SdProDriver(HOST, BASE_URL, AsyncMock(return_value=session))


def _urls(session):
    return [call.args[0] for call in session.get.call_args_list]


@pytest.mark.asyncio
async def test_get_brightness_from_config(driver, session, response):
    response.json = AsyncMock(return_value={"theme": 2, "brightness": 60})
    assert await driver.get_brightness() == 60
    session.get.assert_called_once_with(f"{BASE_URL}/config")


@pytest.mark.asyncio
async def test_set_brightness_clamps_and_uses_lcd_key(driver, session):
    await driver.set_brightness(150)
    session.get.assert_called_with(f"{BASE_URL}/api/set?key=lcd_brightness&value=99")
    await driver.set_brightness(0)
    session.get.assert_called_with(f"{BASE_URL}/api/set?key=lcd_brightness&value=2")


@pytest.mark.asyncio
async def test_set_theme_custom_selects_photo(driver, session):
    await driver.set_theme_custom()
    session.get.assert_called_with(f"{BASE_URL}/api/set?key=theme&value={PHOTO_THEME}")


@pytest.mark.asyncio
async def test_upload_and_display_slideshow_sequence(driver, session):
    """First frame: upload, set Photo theme, enable it, set interval; no delete."""
    await driver.upload_and_display(b"jpegdata", "dashboard.jpg")

    session.post.assert_called_once()
    assert "/photo/upload" in session.post.call_args.args[0]

    urls = _urls(session)
    assert f"{BASE_URL}/api/set?key=theme&value={PHOTO_THEME}" in urls
    assert f"{BASE_URL}/photo/toggle?name=dashboard_a.jpg&state=1" in urls
    assert f"{BASE_URL}/photo/interval?val={DASHBOARD_INTERVAL_SECONDS}" in urls
    # No previous frame to retire yet.
    assert not any("delete" in url for url in urls)


@pytest.mark.asyncio
async def test_upload_and_display_alternates_and_retires(driver, session):
    """Second frame uses the alternate name and retires the first."""
    await driver.upload_and_display(b"frame1", "dashboard.jpg")
    session.get.reset_mock()
    await driver.upload_and_display(b"frame2", "dashboard.jpg")

    urls = _urls(session)
    assert f"{BASE_URL}/photo/toggle?name=dashboard_b.jpg&state=1" in urls
    # The first frame is disabled and deleted.
    assert f"{BASE_URL}/photo/toggle?name=dashboard_a.jpg&state=0" in urls
    assert f"{BASE_URL}/photo/delete?name=dashboard_a.jpg" in urls


@pytest.mark.asyncio
async def test_reboot_swallows_connection_error(driver, session):
    """The device drops the connection on /restart; that is treated as success."""
    session.get.return_value.__aenter__.side_effect = aiohttp.ClientError("dropped")
    await driver.reboot()  # must not raise


@pytest.mark.asyncio
async def test_capabilities(driver):
    caps = driver.capabilities
    assert caps.supports_navigation is False
    assert caps.supports_on_demand_image is False
    assert caps.supports_builtin_themes is False
    assert caps.builtin_theme_threshold is None
