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

    def test_init_with_http_url(self):
        """Test device initialization with http:// URL."""
        device = GeekMagicDevice("http://192.168.1.100")
        assert device.host == "192.168.1.100"
        assert device.base_url == "http://192.168.1.100"

    def test_init_with_https_url(self):
        """Test device initialization with https:// URL preserves scheme."""
        device = GeekMagicDevice("https://192.168.1.100")
        assert device.host == "192.168.1.100"
        assert device.base_url == "https://192.168.1.100"

    def test_init_with_port(self):
        """Test device initialization with port number."""
        device = GeekMagicDevice("http://192.168.1.100:8080")
        assert device.host == "192.168.1.100:8080"
        assert device.base_url == "http://192.168.1.100:8080"

    def test_init_with_hostname(self):
        """Test device initialization with hostname."""
        device = GeekMagicDevice("geekmagic.local")
        assert device.host == "geekmagic.local"
        assert device.base_url == "http://geekmagic.local"

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
    async def test_get_brightness(self, mock_session, mock_response):
        """Test getting brightness."""
        # API returns brightness as string
        mock_response.json = AsyncMock(return_value={"brt": "71"})

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        brightness = await device.get_brightness()

        assert brightness == 71
        mock_session.get.assert_called_once_with("http://192.168.1.100/brt.json")

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
    async def test_upload_ignores_duplicate_content_length_error(self, mock_session):
        """Test upload ignores malformed HTTP with duplicate Content-Length."""
        import aiohttp

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        # Simulate the error from SmallTV-Ultra firmware
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Duplicate Content-Length header",
        )
        mock_session.post.return_value.__aenter__.side_effect = error

        # Should not raise - error is ignored
        await device.upload(image_data, "test.jpg")

    @pytest.mark.asyncio
    async def test_upload_ignores_data_after_close_error(self, mock_session):
        """Test upload ignores malformed HTTP with data after Connection: close."""
        import aiohttp

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        # Simulate the error from SmallTV-Pro firmware
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Data after `Connection: close`",
        )
        mock_session.post.return_value.__aenter__.side_effect = error

        # Should not raise - error is ignored
        await device.upload(image_data, "test.jpg")

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
        # Connection test uses /space.json endpoint (wider firmware support)
        mock_response.json = AsyncMock(return_value={"total": 1048576, "free": 524288})

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result.success is True
        assert result.error == "none"
        # ConnectionResult should be truthy when successful
        assert result
        mock_session.get.assert_called_once_with("http://192.168.1.100/space.json")

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_session, mock_response):
        """Test connection test fails gracefully with generic error."""
        mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result.success is False
        # ClientError (base class) maps to unknown
        assert result.error == "unknown"
        # ConnectionResult should be falsy when failed
        assert not result

    @pytest.mark.asyncio
    async def test_test_connection_timeout(self, mock_session, mock_response):
        """Test connection test returns timeout error."""
        mock_session.get.side_effect = TimeoutError()

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result.success is False
        assert result.error == "timeout"
        assert result.message is not None
        assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_test_connection_dns_error(self, mock_session, mock_response):
        """Test connection test returns DNS error."""
        # Create a DNS error with proper arguments
        mock_session.get.side_effect = aiohttp.ClientConnectorDNSError(
            MagicMock(), OSError("DNS lookup failed")
        )

        device = GeekMagicDevice("invalid.hostname.local", session=mock_session)
        result = await device.test_connection()

        assert result.success is False
        assert result.error == "dns_error"
        assert result.message is not None
        assert "resolve" in result.message.lower()

    @pytest.mark.asyncio
    async def test_test_connection_refused(self, mock_session, mock_response):
        """Test connection test returns connection refused error."""
        mock_session.get.side_effect = aiohttp.ClientConnectorError(
            MagicMock(), OSError("Connection refused")
        )

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result.success is False
        assert result.error == "connection_refused"

    @pytest.mark.asyncio
    async def test_test_connection_http_error(self, mock_session, mock_response):
        """Test connection test returns HTTP error."""
        mock_session.get.side_effect = aiohttp.ClientResponseError(
            MagicMock(), (), status=500, message="Internal Server Error"
        )

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.test_connection()

        assert result.success is False
        assert result.error == "http_error"
        assert result.message is not None
        assert "500" in result.message

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


class TestDeviceModelDetection:
    """Tests for device model detection."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        session = MagicMock()
        session.close = AsyncMock()
        return session

    def test_init_with_model(self):
        """Test device initialization with explicit model."""
        from custom_components.geekmagic.const import MODEL_PRO

        device = GeekMagicDevice("192.168.1.100", model=MODEL_PRO)
        assert device.model == MODEL_PRO

    def test_init_default_model(self):
        """Test device initialization has unknown model by default."""
        from custom_components.geekmagic.const import MODEL_UNKNOWN

        device = GeekMagicDevice("192.168.1.100")
        assert device.model == MODEL_UNKNOWN

    @pytest.mark.asyncio
    async def test_detect_model_pro(self, mock_session):
        """Test detecting Pro model via /.sys/app.json."""
        from custom_components.geekmagic.const import MODEL_PRO

        # Create mock response for Pro path
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.detect_model()

        assert result == MODEL_PRO
        assert device.model == MODEL_PRO
        # Should have tried Pro path first
        mock_session.get.assert_called()
        call_url = mock_session.get.call_args[0][0]
        assert "/.sys/app.json" in call_url

    @pytest.mark.asyncio
    async def test_detect_model_ultra(self, mock_session):
        """Test detecting Ultra model when Pro path fails."""
        from custom_components.geekmagic.const import MODEL_ULTRA

        # First call (Pro path) fails, second call (Ultra path) succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status = 404
        mock_response_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
        mock_response_fail.__aexit__ = AsyncMock()

        mock_response_ok = MagicMock()
        mock_response_ok.status = 200
        mock_response_ok.__aenter__ = AsyncMock(return_value=mock_response_ok)
        mock_response_ok.__aexit__ = AsyncMock()

        mock_session.get = MagicMock(side_effect=[mock_response_fail, mock_response_ok])

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        result = await device.detect_model()

        assert result == MODEL_ULTRA
        assert device.model == MODEL_ULTRA

    @pytest.mark.asyncio
    async def test_navigate_next(self, mock_session):
        """Test Pro navigate next."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.navigate_next()

        mock_session.get.assert_called_with("http://192.168.1.100/set?page=1")

    @pytest.mark.asyncio
    async def test_navigate_previous(self, mock_session):
        """Test Pro navigate previous."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.navigate_previous()

        mock_session.get.assert_called_with("http://192.168.1.100/set?page=-1")

    @pytest.mark.asyncio
    async def test_navigate_enter(self, mock_session):
        """Test Pro navigate enter."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.navigate_enter()

        mock_session.get.assert_called_with("http://192.168.1.100/set?enter=-1")

    @pytest.mark.asyncio
    async def test_reboot(self, mock_session):
        """Test Pro reboot."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        device = GeekMagicDevice("192.168.1.100", session=mock_session)
        await device.reboot()

        mock_session.get.assert_called_with("http://192.168.1.100/set?reboot=1")
