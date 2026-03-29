"""Test fixtures for GeekMagic integration."""

import sys
from pathlib import Path

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

# Import pytest-homeassistant-custom-component fixtures
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.geekmagic.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


def _init_pycares_thread():
    """Pre-initialize pycares daemon thread before any tests run.

    The pycares library (used by aiodns for DNS resolution) creates a daemon thread
    named '_run_safe_shutdown_loop' that persists for the process lifetime. HA's test
    harness asserts no new threads are left after a test. Pre-initializing ensures
    the thread exists in the 'before' snapshot.
    """
    try:
        import pycares

        # Create a channel to trigger thread creation
        pycares.Channel()
    except ImportError:
        pass


_init_pycares_thread()


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for GeekMagic."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Display",
        data={"host": "192.168.1.100", "name": "Test Display"},
        options={},
        entry_id="test_entry_123",
    )


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
