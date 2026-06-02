"""Tests for the GeekMagicDevice facade.

Endpoint-level behaviour for each firmware family lives in
`tests/drivers/test_stock.py` and `tests/drivers/test_sdpro.py`. This file
covers facade concerns: URL parsing, session lifecycle, driver detection
wiring, and delegation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.const import (
    MODEL_PRO,
    MODEL_SDPRO,
    MODEL_ULTRA,
    MODEL_UNKNOWN,
)
from custom_components.geekmagic.device import (
    DeviceState,
    GeekMagicDevice,
    SpaceInfo,
)


def _make_response(*, status=200, json_data=None):
    response = MagicMock()
    response.status = status
    response.raise_for_status = MagicMock()
    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _make_session(handlers=None):
    """`handlers` maps URL substring -> a pre-built response (MagicMock)."""
    handlers = handlers or {}
    session = MagicMock()

    def _get(url, **_kwargs):
        for needle, response in handlers.items():
            if needle in url:
                return response
        return _make_response(status=404)

    def _post(url, **_kwargs):
        return _make_response()

    session.get = _get
    session.post = _post
    session.close = AsyncMock()
    return session


class TestDeviceState:
    def test_create(self):
        state = DeviceState(theme=3, brightness=50, current_image="/image/x.jpg")
        assert state.theme == 3
        assert state.brightness == 50
        assert state.current_image == "/image/x.jpg"

    def test_with_none(self):
        state = DeviceState(theme=0, brightness=None, current_image=None)
        assert state.brightness is None
        assert state.current_image is None


class TestSpaceInfo:
    def test_create(self):
        info = SpaceInfo(total=1024, free=512)
        assert info.total == 1024
        assert info.free == 512


class TestGeekMagicDeviceInit:
    def test_bare_ip(self):
        device = GeekMagicDevice("192.168.1.100")
        assert device.host == "192.168.1.100"
        assert device.base_url == "http://192.168.1.100"

    def test_http_url(self):
        device = GeekMagicDevice("http://192.168.1.100")
        assert device.host == "192.168.1.100"
        assert device.base_url == "http://192.168.1.100"

    def test_https_url_preserved(self):
        device = GeekMagicDevice("https://192.168.1.100")
        assert device.base_url == "https://192.168.1.100"

    def test_port(self):
        device = GeekMagicDevice("http://192.168.1.100:8080")
        assert device.host == "192.168.1.100:8080"
        assert device.base_url == "http://192.168.1.100:8080"

    def test_hostname(self):
        device = GeekMagicDevice("geekmagic.local")
        assert device.host == "geekmagic.local"
        assert device.base_url == "http://geekmagic.local"

    def test_default_model_unknown(self):
        assert GeekMagicDevice("192.168.1.100").model == MODEL_UNKNOWN

    def test_external_session(self):
        sess = _make_session()
        device = GeekMagicDevice("192.168.1.100", session=sess)
        assert device._session is sess
        assert device._owns_session is False

    def test_driver_property_raises_before_detection(self):
        device = GeekMagicDevice("192.168.1.100")
        with pytest.raises(RuntimeError):
            _ = device.driver


class TestSessionLifecycle:
    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            session.close = AsyncMock()
            mock_cls.return_value = session
            device = GeekMagicDevice("192.168.1.100")
            device._session = session
            await device.close()
            session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_external_session(self):
        sess = _make_session()
        device = GeekMagicDevice("192.168.1.100", session=sess)
        await device.close()
        sess.close.assert_not_called()


class TestDetection:
    @pytest.mark.asyncio
    async def test_detect_stock_pro(self):
        session = _make_session(
            {"/v.json": _make_response(json_data={"m": "GeekMagic SmallTV-PRO", "v": "V3"})}
        )
        device = GeekMagicDevice("192.168.1.100", session=session)
        assert await device.detect_model() == MODEL_PRO
        assert device.sw_version == "V3"
        assert device.supports_navigation is True

    @pytest.mark.asyncio
    async def test_detect_stock_ultra(self):
        session = _make_session(
            {"/v.json": _make_response(json_data={"m": "SmallTV-Ultra", "v": "Ultra-V9"})}
        )
        device = GeekMagicDevice("192.168.1.100", session=session)
        assert await device.detect_model() == MODEL_ULTRA
        assert device.sw_version == "Ultra-V9"
        assert device.supports_navigation is False

    @pytest.mark.asyncio
    async def test_detect_sdpro(self):
        session = _make_session(
            {"/config": _make_response(json_data={"brightness": 50, "freespace": 1024})}
        )
        device = GeekMagicDevice("192.168.1.100", session=session)
        assert await device.detect_model() == MODEL_SDPRO

    @pytest.mark.asyncio
    async def test_detect_returns_unknown_when_all_fail(self):
        session = _make_session({})
        device = GeekMagicDevice("192.168.1.100", session=session)
        assert await device.detect_model() == MODEL_UNKNOWN
        assert device.sw_version is None


class TestConnectionTest:
    @pytest.mark.asyncio
    async def test_success_runs_detection(self):
        session = _make_session(
            {
                "/v.json": _make_response(json_data={"m": "SmallTV-Ultra", "v": "Ultra-V9.0.40"}),
                "/space.json": _make_response(json_data={"total": 1024, "free": 512}),
            }
        )
        device = GeekMagicDevice("192.168.1.100", session=session)
        result = await device.test_connection()
        assert result.success is True
        assert device.model == MODEL_ULTRA

    @pytest.mark.asyncio
    async def test_failure_when_undetectable(self):
        session = _make_session({})
        device = GeekMagicDevice("192.168.1.100", session=session)
        result = await device.test_connection()
        assert result.success is False
        assert result.error == "http_error"


class TestDelegation:
    """The facade must forward calls to the underlying driver."""

    @pytest.fixture
    def detected_device(self):
        session = _make_session(
            {"/v.json": _make_response(json_data={"m": "SmallTV-Ultra", "v": "Ultra-V9.0.40"})}
        )
        return GeekMagicDevice("192.168.1.100", session=session)

    @pytest.mark.asyncio
    async def test_each_method_calls_driver(self, detected_device):
        device = detected_device
        await device.detect_model()
        driver = device.driver
        driver.get_state = AsyncMock(return_value="STATE")
        driver.get_space = AsyncMock(return_value="SPACE")
        driver.get_brightness = AsyncMock(return_value=42)
        driver.set_brightness = AsyncMock()
        driver.set_theme = AsyncMock()
        driver.set_theme_custom = AsyncMock()
        driver.set_image = AsyncMock()
        driver.upload = AsyncMock()
        driver.upload_and_display = AsyncMock()
        driver.delete_file = AsyncMock()
        driver.clear_images = AsyncMock()
        driver.reboot = AsyncMock()
        driver.navigate_next = AsyncMock()
        driver.navigate_previous = AsyncMock()
        driver.navigate_enter = AsyncMock()

        assert await device.get_state() == "STATE"
        assert await device.get_space() == "SPACE"
        assert await device.get_brightness() == 42
        await device.set_brightness(50)
        await device.set_theme(3)
        await device.set_theme_custom()
        await device.set_image("x.jpg")
        await device.upload(b"x", "x.jpg")
        await device.upload_and_display(b"x", "x.jpg")
        await device.delete_file("/image/x.jpg")
        await device.clear_images()
        await device.reboot()
        await device.navigate_next()
        await device.navigate_previous()
        await device.navigate_enter()

        driver.set_brightness.assert_awaited_once_with(50)
        driver.set_theme.assert_awaited_once_with(3)
        driver.set_theme_custom.assert_awaited_once()
        driver.set_image.assert_awaited_once_with("x.jpg")
        driver.upload.assert_awaited_once_with(b"x", "x.jpg")
        driver.upload_and_display.assert_awaited_once_with(b"x", "x.jpg")
        driver.delete_file.assert_awaited_once_with("/image/x.jpg")
        driver.clear_images.assert_awaited_once()
        driver.reboot.assert_awaited_once()
        driver.navigate_next.assert_awaited_once()
        driver.navigate_previous.assert_awaited_once()
        driver.navigate_enter.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_custom_image_theme_before_detection(self):
        device = GeekMagicDevice("192.168.1.100")
        # Conservative pre-detection fallback (Ultra: theme 3).
        assert device.is_custom_image_theme(3) is True
        assert device.is_custom_image_theme(4) is False
