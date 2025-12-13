"""Tests for GeekMagic device client."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.geekmagic.device import (
    DeviceState,
    GeekMagicDevice,
    SpaceInfo,
)


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock()
    return response


@pytest.fixture
def mock_session(mock_response):
    """Create a mock aiohttp session."""
    session = MagicMock()
    session.get = MagicMock(return_value=mock_response)
    session.post = MagicMock(return_value=mock_response)
    session.close = AsyncMock()
    return session


class TestDeviceState:
    """Tests for DeviceState dataclass."""

    def test_create_state(self):
        """Test creating a device state."""
        state = DeviceState(theme=3, brightness=50, current_image="/image/test.jpg")
        assert state.theme == 3
        assert state.brightness == 50
        assert state.current_image == "/image/test.jpg"

    def test_state_with_none_values(self):
        """Test creating a state with None values."""
        state = DeviceState(theme=0, brightness=None, current_image=None)
        assert state.theme == 0
        assert state.brightness is None
        assert state.current_image is None


class TestSpaceInfo:
    """Tests for SpaceInfo dataclass."""

    def test_create_space_info(self):
        """Test creating space info."""
        info = SpaceInfo(total=1048576, free=524288)
        assert info.total == 1048576
        assert info.free == 524288


class TestGeekMagicDevice:
    """Tests for GeekMagicDevice client."""

    def test_init(self):
        """Test device initialization."""
        device = GeekMagicDevice("192.168.1.100")
        assert device.host == "192.168.1.100"
        assert device.base_url == "http://192.168.1.100"

    def test_init_with_session(self, mock_session):
        """Test device initialization with provided session."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        assert device._session == mock_session
        assert device._owns_session is False

    @pytest.mark.asyncio
    async def test_get_state(self, mock_session, mock_response):
        """Test getting device state."""
        mock_response.json = AsyncMock(
            return_value={"theme": 3, "brt": 75, "img": "/image/dashboard.jpg"}
        )

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        state = await device.get_state()

        assert state.theme == 3
        assert state.brightness == 75
        assert state.current_image == "/image/dashboard.jpg"
        mock_session.get.assert_called_once_with("http://192.168.1.100/app.json")

    @pytest.mark.asyncio
    async def test_get_space(self, mock_session, mock_response):
        """Test getting storage info."""
        mock_response.json = AsyncMock(return_value={"total": 1048576, "free": 524288})

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        space = await device.get_space()

        assert space.total == 1048576
        assert space.free == 524288

    @pytest.mark.asyncio
    async def test_set_brightness(self, mock_session, mock_response):
        """Test setting brightness."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.set_brightness(80)

        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=80")

    @pytest.mark.asyncio
    async def test_set_brightness_clamps_values(self, mock_session, mock_response):
        """Test brightness values are clamped to 0-100."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)

        await device.set_brightness(150)
        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=100")

        await device.set_brightness(-10)
        mock_session.get.assert_called_with("http://192.168.1.100/set?brt=0")

    @pytest.mark.asyncio
    async def test_set_theme(self, mock_session, mock_response):
        """Test setting theme."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.set_theme(3)

        mock_session.get.assert_called_with("http://192.168.1.100/set?theme=3")

    @pytest.mark.asyncio
    async def test_set_image(self, mock_session, mock_response):
        """Test setting displayed image."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.set_image("dashboard.jpg")

        # Should set theme first, then image
        calls = mock_session.get.call_args_list
        assert len(calls) == 2
        assert "theme=3" in str(calls[0])
        assert "img=/image/dashboard.jpg" in str(calls[1])

    @pytest.mark.asyncio
    async def test_upload(self, mock_session, mock_response):
        """Test uploading an image."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # Fake JPEG

        await device.upload(image_data, "test.jpg")

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "doUpload" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_upload_png(self, mock_session, mock_response):
        """Test uploading a PNG image."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        await device.upload(image_data, "test.png")

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_and_display(self, mock_session, mock_response):
        """Test uploading and displaying an image."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        await device.upload_and_display(image_data, "dashboard.jpg")

        # Should call post for upload, then get for set_image
        assert mock_session.post.called
        assert mock_session.get.called

    @pytest.mark.asyncio
    async def test_delete_file(self, mock_session, mock_response):
        """Test deleting a file."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.delete_file("/image/old.jpg")

        mock_session.get.assert_called_with("http://192.168.1.100/delete?file=/image/old.jpg")

    @pytest.mark.asyncio
    async def test_clear_images(self, mock_session, mock_response):
        """Test clearing all images."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.clear_images()

        mock_session.get.assert_called_with("http://192.168.1.100/set?clear=image")

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_session, mock_response):
        """Test connection test succeeds."""
        mock_response.json = AsyncMock(return_value={"theme": 3})

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_session, mock_response):
        """Test connection test fails gracefully."""
        mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        """Test closing owned session."""
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_cls.return_value = mock_session

            device = GeekMagicDevice("192.168.1.100")
            device._session = mock_session
            await device.close()

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_external_session(self, mock_session):
        """Test not closing external session."""
        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.close()

        mock_session.close.assert_not_called()
