"""Tests for the StockDriver (Pro + Ultra families)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.drivers.stock import (
    STOCK_PRO_PROFILE,
    STOCK_ULTRA_PROFILE,
    StockDriver,
)


@pytest.fixture
def mock_response():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.status = 200
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


@pytest.fixture
def mock_session(mock_response):
    session = MagicMock()
    session.get = MagicMock(return_value=mock_response)
    session.post = MagicMock(return_value=mock_response)
    session.close = AsyncMock()
    return session


def _ultra(session):
    return StockDriver(
        "http://192.168.1.100", session, STOCK_ULTRA_PROFILE, sw_version="Ultra-V9.0.40"
    )


def _pro(session):
    return StockDriver("http://192.168.1.100", session, STOCK_PRO_PROFILE, sw_version="V3.3.76EN")


class TestStockUltra:
    """Ultra firmware behaviour — regression coverage for the historical default."""

    @pytest.mark.asyncio
    async def test_get_state(self, mock_session, mock_response):
        mock_response.json = AsyncMock(
            return_value={"theme": 3, "brt": 75, "img": "/image/dashboard.jpg"}
        )
        driver = _ultra(mock_session)
        state = await driver.get_state()
        assert state.theme == 3
        assert state.brightness == 75
        assert state.current_image == "/image/dashboard.jpg"
        mock_session.get.assert_called_once_with("http://192.168.1.100/app.json")

    @pytest.mark.asyncio
    async def test_get_state_partial(self, mock_session, mock_response):
        """Old-ultra firmware returns only {theme}; brightness/image stay None."""
        mock_response.json = AsyncMock(return_value={"theme": 3})
        driver = _ultra(mock_session)
        state = await driver.get_state()
        assert state.theme == 3
        assert state.brightness is None
        assert state.current_image is None

    @pytest.mark.asyncio
    async def test_get_space(self, mock_session, mock_response):
        mock_response.json = AsyncMock(return_value={"total": 1048576, "free": 524288})
        driver = _ultra(mock_session)
        space = await driver.get_space()
        assert space.total == 1048576
        assert space.free == 524288
        mock_session.get.assert_called_once_with("http://192.168.1.100/space.json")

    @pytest.mark.asyncio
    async def test_get_brightness(self, mock_session, mock_response):
        mock_response.json = AsyncMock(return_value={"brt": "71"})
        driver = _ultra(mock_session)
        assert await driver.get_brightness() == 71
        mock_session.get.assert_called_once_with("http://192.168.1.100/brt.json")

    @pytest.mark.asyncio
    async def test_set_brightness(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.set_brightness(80)
        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=80")

    @pytest.mark.asyncio
    async def test_set_brightness_clamps(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.set_brightness(150)
        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=100")
        await driver.set_brightness(-10)
        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=0")

    @pytest.mark.asyncio
    async def test_set_theme(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.set_theme(3)
        mock_session.get.assert_called_with("http://192.168.1.100/set?theme=3")

    @pytest.mark.asyncio
    async def test_set_theme_custom_uses_3_for_ultra(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.set_theme_custom()
        mock_session.get.assert_called_with("http://192.168.1.100/set?theme=3")

    @pytest.mark.asyncio
    async def test_set_image_sets_theme_then_image(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.set_image("dashboard.jpg")
        calls = mock_session.get.call_args_list
        assert len(calls) == 2
        assert "theme=3" in str(calls[0])
        assert "img=/image/dashboard.jpg" in str(calls[1])

    @pytest.mark.asyncio
    async def test_upload_jpeg(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.upload(b"\xff\xd8\xff\xe0" + b"\x00" * 100, "test.jpg")
        mock_session.post.assert_called_once()
        url = mock_session.post.call_args[0][0]
        assert "doUpload" in url
        assert "dir=/image/" in url

    @pytest.mark.asyncio
    async def test_upload_png(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.upload(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "test.png")
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_swallows_duplicate_content_length(self, mock_session):
        driver = _ultra(mock_session)
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Duplicate Content-Length header",
        )
        mock_session.post.return_value.__aenter__.side_effect = error
        # Must not raise.
        await driver.upload(b"x" * 64, "test.jpg")

    @pytest.mark.asyncio
    async def test_upload_swallows_data_after_close(self, mock_session):
        driver = _ultra(mock_session)
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Data after `Connection: close`",
        )
        mock_session.post.return_value.__aenter__.side_effect = error
        await driver.upload(b"x" * 64, "test.jpg")

    @pytest.mark.asyncio
    async def test_delete_file(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.delete_file("/image/old.jpg")
        mock_session.get.assert_called_with("http://192.168.1.100/delete?file=/image/old.jpg")

    @pytest.mark.asyncio
    async def test_clear_images(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.clear_images()
        mock_session.get.assert_called_with("http://192.168.1.100/set?clear=image")

    @pytest.mark.asyncio
    async def test_reboot(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.reboot()
        mock_session.get.assert_called_with("http://192.168.1.100/set?reboot=1")

    @pytest.mark.asyncio
    async def test_navigation_is_noop_on_ultra(self, mock_session, mock_response):
        driver = _ultra(mock_session)
        await driver.navigate_next()
        await driver.navigate_previous()
        await driver.navigate_enter()
        # No HTTP calls because Ultra firmware doesn't have these endpoints.
        assert not mock_session.get.called

    def test_is_custom_image_theme(self, mock_session):
        driver = _ultra(mock_session)
        assert driver.is_custom_image_theme(3) is True
        assert driver.is_custom_image_theme(4) is False

    def test_supports_navigation_false(self, mock_session):
        assert _ultra(mock_session).supports_navigation is False


class TestStockPro:
    """Pro firmware differences: brightness path, custom-image theme=4, navigation."""

    @pytest.mark.asyncio
    async def test_get_state_no_app_json(self, mock_session, mock_response):
        """Pro firmware has no /app.json; return cached theme without hitting HTTP."""
        driver = _pro(mock_session)
        state = await driver.get_state()
        assert state.theme == 4  # default cache = custom_image_theme
        assert state.brightness is None
        assert state.current_image is None
        # Importantly, no request was made.
        assert not mock_session.get.called

    @pytest.mark.asyncio
    async def test_set_theme_updates_cached_theme(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.set_theme(6)
        state = await driver.get_state()
        assert state.theme == 6

    @pytest.mark.asyncio
    async def test_get_brightness_uses_sys_path(self, mock_session, mock_response):
        mock_response.json = AsyncMock(return_value={"brt": "85"})
        driver = _pro(mock_session)
        assert await driver.get_brightness() == 85
        mock_session.get.assert_called_once_with("http://192.168.1.100/.sys/brt.json")

    @pytest.mark.asyncio
    async def test_set_theme_custom_uses_4_for_pro(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.set_theme_custom()
        mock_session.get.assert_called_with("http://192.168.1.100/set?theme=4")

    @pytest.mark.asyncio
    async def test_set_image_uses_picture_theme(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.set_image("dashboard.jpg")
        calls = mock_session.get.call_args_list
        assert "theme=4" in str(calls[0])
        assert "img=/image/dashboard.jpg" in str(calls[1])

    @pytest.mark.asyncio
    async def test_navigate_next(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.navigate_next()
        mock_session.get.assert_called_with("http://192.168.1.100/set?page=1")

    @pytest.mark.asyncio
    async def test_navigate_previous(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.navigate_previous()
        mock_session.get.assert_called_with("http://192.168.1.100/set?page=-1")

    @pytest.mark.asyncio
    async def test_navigate_enter(self, mock_session, mock_response):
        driver = _pro(mock_session)
        await driver.navigate_enter()
        mock_session.get.assert_called_with("http://192.168.1.100/set?enter=-1")

    def test_is_custom_image_theme(self, mock_session):
        driver = _pro(mock_session)
        assert driver.is_custom_image_theme(4) is True
        assert driver.is_custom_image_theme(3) is False

    def test_supports_navigation_true(self, mock_session):
        assert _pro(mock_session).supports_navigation is True
