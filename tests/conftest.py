"""Test fixtures for GeekMagic integration."""

import sys
from pathlib import Path

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image


@pytest.fixture
def mock_device():
    """Create a mock GeekMagic device."""
    from custom_components.geekmagic.device import GeekMagicDevice

    device = MagicMock(spec=GeekMagicDevice)
    device.host = "192.168.1.100"
    device.get_state = AsyncMock(
        return_value={"theme": 3, "brt": 50, "img": "/image/dashboard.jpg"}
    )
    device.get_space = AsyncMock(return_value={"total": 1048576, "free": 524288})
    device.upload = AsyncMock()
    device.set_image = AsyncMock()
    device.set_brightness = AsyncMock()
    device.upload_and_display = AsyncMock()
    return device


@pytest.fixture
def renderer():
    """Create a Renderer instance."""
    from custom_components.geekmagic.renderer import Renderer

    return Renderer()


@pytest.fixture
def sample_image():
    """Create a sample 240x240 test image."""
    return Image.new("RGB", (240, 240), (0, 0, 0))


@pytest.fixture
def mock_aiohttp_session():
    """Create a mock aiohttp session."""
    with patch("aiohttp.ClientSession") as mock:
        session = MagicMock()
        session.get = AsyncMock()
        session.post = AsyncMock()
        session.close = AsyncMock()
        mock.return_value.__aenter__ = AsyncMock(return_value=session)
        mock.return_value.__aexit__ = AsyncMock()
        yield session
