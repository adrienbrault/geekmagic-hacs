"""GeekMagic device HTTP API client.

``GeekMagicDevice`` is a thin facade. It owns the aiohttp session and the
host/URL parsing, then delegates every operation to a :class:`FirmwareDriver`
chosen by :func:`detect_driver`. The public method surface is unchanged so the
coordinator and entities need not know which firmware is in use.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import aiohttp

from .const import MODEL_UNKNOWN
from .drivers import (
    ConnectionResult,
    DeviceState,
    DriverCapabilities,
    FirmwareDriver,
    SpaceInfo,
    detect_driver,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)

# Re-exported for backward compatibility (``from .device import DeviceState``).
__all__ = [
    "ConnectionResult",
    "DeviceState",
    "GeekMagicDevice",
    "SpaceInfo",
]


class GeekMagicDevice:
    """HTTP client facade for GeekMagic display devices."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the device client.

        Args:
            host: IP address, hostname, or URL of the device.
            session: Optional aiohttp session (created if not provided).
            model: Deprecated/ignored — the model is determined by firmware
                detection (:meth:`detect_model`). Accepted for compatibility.
        """
        # Parse and normalize the host input to handle URLs
        if host.startswith(("http://", "https://")):
            parsed = urlparse(host)
            self.host = parsed.netloc  # e.g., "192.168.1.1" or "192.168.1.1:8080"
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.host = host
            self.base_url = f"http://{host}"
        self._session = session
        self._owns_session = session is None
        self._driver: FirmwareDriver | None = None

    @property
    def model(self) -> str:
        """Return the detected model, or MODEL_UNKNOWN before detection."""
        return self._driver.model if self._driver else MODEL_UNKNOWN

    @property
    def model_name(self) -> str:
        """Return the human-readable model name for the detected firmware."""
        return self._driver.model_name if self._driver else "SmallTV"

    @property
    def capabilities(self) -> DriverCapabilities:
        """Return the detected firmware's capabilities.

        Before detection, returns conservative defaults (no navigation, no
        builtin-theme sync) so callers never crash on an undetected device.
        """
        if self._driver:
            return self._driver.capabilities
        return DriverCapabilities(
            supports_navigation=False,
            supports_on_demand_image=False,
            custom_theme=None,
            builtin_modes={},
        )

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version string, if known."""
        return self._driver.firmware_version if self._driver else None

    # ``sw_version`` is the Home Assistant DeviceInfo field name.
    sw_version = firmware_version

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self._session

    async def _require_driver(self) -> FirmwareDriver:
        """Return the driver, detecting it on first use."""
        if self._driver is None:
            await self.detect_model()
        assert self._driver is not None
        return self._driver

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def detect_model(self) -> str:
        """Detect the firmware and bind the matching driver.

        Returns the detected model string (MODEL_PRO/MODEL_ULTRA/MODEL_SDPRO).
        """
        self._driver = await detect_driver(self.host, self.base_url, self._get_session)
        return self._driver.model

    # -- delegated API surface ------------------------------------------------

    async def test_connection(self) -> ConnectionResult:
        """Test if the device is reachable (detects firmware if needed)."""
        driver = await self._require_driver()
        return await driver.test_connection()

    async def get_state(self) -> DeviceState:
        """Get current device state."""
        driver = await self._require_driver()
        return await driver.get_state()

    async def get_space(self) -> SpaceInfo:
        """Get device storage information."""
        driver = await self._require_driver()
        return await driver.get_space()

    async def get_brightness(self) -> int | None:
        """Get current brightness from device."""
        driver = await self._require_driver()
        return await driver.get_brightness()

    async def set_brightness(self, value: int) -> None:
        """Set display brightness."""
        driver = await self._require_driver()
        await driver.set_brightness(value)

    async def set_theme(self, theme: int) -> None:
        """Set device theme."""
        driver = await self._require_driver()
        await driver.set_theme(theme)

    async def set_theme_custom(self) -> None:
        """Set device to custom-image / dashboard mode."""
        driver = await self._require_driver()
        await driver.set_theme_custom()

    async def set_image(self, filename: str) -> None:
        """Set the displayed image."""
        driver = await self._require_driver()
        await driver.set_image(filename)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to the device."""
        driver = await self._require_driver()
        await driver.upload(image_data, filename)

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Upload an image and immediately display it."""
        driver = await self._require_driver()
        await driver.upload_and_display(image_data, filename)

    async def delete_file(self, path: str) -> None:
        """Delete a file from the device."""
        driver = await self._require_driver()
        await driver.delete_file(path)

    async def clear_images(self) -> None:
        """Clear all images from the device."""
        driver = await self._require_driver()
        await driver.clear_images()

    async def navigate_next(self) -> None:
        """Navigate to next page (Pro devices)."""
        driver = await self._require_driver()
        await driver.navigate_next()

    async def navigate_previous(self) -> None:
        """Navigate to previous page (Pro devices)."""
        driver = await self._require_driver()
        await driver.navigate_previous()

    async def navigate_enter(self) -> None:
        """Press enter/exit button (Pro devices)."""
        driver = await self._require_driver()
        await driver.navigate_enter()

    async def reboot(self) -> None:
        """Reboot the device."""
        driver = await self._require_driver()
        await driver.reboot()
