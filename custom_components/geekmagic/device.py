"""GeekMagic device HTTP API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import aiohttp

from .const import MODEL_PRO, MODEL_ULTRA, MODEL_UNKNOWN

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass
class ConnectionResult:
    """Result of a connection test."""

    success: bool
    error: Literal[
        "none", "timeout", "connection_refused", "dns_error", "http_error", "unknown"
    ] = "none"
    message: str | None = None

    def __bool__(self) -> bool:
        """Allow using ConnectionResult in boolean context."""
        return self.success


@dataclass
class DeviceState:
    """Represents the current device state."""

    theme: int
    brightness: int | None
    current_image: str | None


@dataclass
class SpaceInfo:
    """Represents device storage info."""

    total: int
    free: int


class GeekMagicDevice:
    """HTTP client for GeekMagic display devices."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession | None = None,
        model: str = MODEL_UNKNOWN,
    ) -> None:
        """Initialize the device client.

        Args:
            host: IP address, hostname, or URL of the device
            session: Optional aiohttp session (created if not provided)
            model: Device model (MODEL_PRO, MODEL_ULTRA, or MODEL_UNKNOWN)
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
        self.model = model

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def get_state(self) -> DeviceState:
        """Get current device state.

        Returns:
            DeviceState with theme, brightness, and current image
        """
        _LOGGER.debug("Getting device state from %s", self.host)
        session = await self._get_session()
        async with session.get(f"{self.base_url}/app.json") as response:
            response.raise_for_status()
            # Device returns text/plain content type, so we need to accept any
            data = await response.json(content_type=None)
            state = DeviceState(
                theme=data.get("theme", 0),
                brightness=data.get("brt"),
                current_image=data.get("img"),
            )
            _LOGGER.debug(
                "Device state: theme=%d, brightness=%s, image=%s",
                state.theme,
                state.brightness,
                state.current_image,
            )
            return state

    async def get_space(self) -> SpaceInfo:
        """Get device storage information.

        Returns:
            SpaceInfo with total and free bytes
        """
        _LOGGER.debug("Getting storage info from %s", self.host)
        session = await self._get_session()
        async with session.get(f"{self.base_url}/space.json") as response:
            response.raise_for_status()
            # Device returns text/plain content type, so we need to accept any
            data = await response.json(content_type=None)
            space = SpaceInfo(
                total=data.get("total", 0),
                free=data.get("free", 0),
            )
            _LOGGER.debug(
                "Storage info: total=%d, free=%d (%.1f%% free)",
                space.total,
                space.free,
                (space.free / space.total * 100) if space.total > 0 else 0,
            )
            return space

    async def get_brightness(self) -> int:
        """Get current brightness from device.

        Returns:
            Brightness level 0-100
        """
        _LOGGER.debug("Getting brightness from %s", self.host)
        session = await self._get_session()
        async with session.get(f"{self.base_url}/brt.json") as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
            # API returns brightness as string: {"brt": "71"}
            brightness = int(data.get("brt", 0))
            _LOGGER.debug("Device brightness: %d", brightness)
            return brightness

    async def set_brightness(self, value: int) -> None:
        """Set display brightness.

        Args:
            value: Brightness level 0-100
        """
        value = max(0, min(100, value))
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?brt={value}") as response:
            response.raise_for_status()
        _LOGGER.debug("Set brightness to %d", value)

    async def set_theme(self, theme: int) -> None:
        """Set device theme.

        Args:
            theme: Theme number (3 = custom image on Ultra, 4 = custom image on Pro)
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?theme={theme}") as response:
            response.raise_for_status()
        _LOGGER.debug("Set theme to %d", theme)

    async def set_theme_custom(self) -> None:
        """Set device to custom image mode with the correct theme number.

        Ultra devices use theme 3, Pro devices use theme 4.
        Uses the model detected at startup via detect_model().
        """
        theme = 4 if self.model == MODEL_PRO else 3
        await self.set_theme(theme)

    async def set_image(self, filename: str) -> None:
        """Set the displayed image.

        Args:
            filename: Image filename (without path)
        """
        # Ensure we're in custom image mode
        await self.set_theme_custom()
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?img=/image/{filename}") as response:
            response.raise_for_status()
        _LOGGER.debug("Set image to %s", filename)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to the device.

        Args:
            image_data: Raw image bytes (JPEG or PNG)
            filename: Filename to save as
        """
        # Determine content type from filename
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
        else:
            content_type = "image/jpeg"

        # Create multipart form data
        form = aiohttp.FormData()
        form.add_field(
            "file",
            image_data,
            filename=filename,
            content_type=content_type,
        )

        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/doUpload?dir=/image/",
                data=form,
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientResponseError as e:
            # Device firmware returns malformed HTTP responses, but upload succeeds.
            # Known issues:
            # - SmallTV-Ultra: Duplicate Content-Length headers
            # - SmallTV-Pro: "Data after Connection: close" (sends OK + new response)
            if e.status == 400:
                msg = str(e.message) if e.message else ""
                if "Duplicate Content-Length" in msg or "Data after" in msg:
                    _LOGGER.debug("Ignoring malformed HTTP response from device: %s", msg)
                    return
            raise

        _LOGGER.debug("Uploaded %s (%d bytes)", filename, len(image_data))

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Upload an image and immediately display it.

        Args:
            image_data: Raw image bytes
            filename: Filename to save as
        """
        _LOGGER.debug(
            "Uploading and displaying %s (%d bytes) to %s",
            filename,
            len(image_data),
            self.host,
        )
        await self.upload(image_data, filename)
        await self.set_image(filename)
        _LOGGER.debug("Upload and display completed for %s", filename)

    async def delete_file(self, path: str) -> None:
        """Delete a file from the device.

        Args:
            path: Full path to the file
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/delete?file={path}") as response:
            response.raise_for_status()
        _LOGGER.debug("Deleted %s", path)

    async def clear_images(self) -> None:
        """Clear all images from the device."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?clear=image") as response:
            response.raise_for_status()
        _LOGGER.debug("Cleared all images")

    async def test_connection(self) -> ConnectionResult:
        """Test if the device is reachable.

        Returns:
            ConnectionResult with success status and error details if failed.
            Can be used in boolean context (truthy if successful).
        """
        _LOGGER.debug("Testing connection to %s", self.host)
        try:
            # use space.json as it's more widely supported across firmware versions
            await self.get_space()
        except TimeoutError:
            _LOGGER.warning("Connection test timed out for %s", self.host)
            return ConnectionResult(
                success=False,
                error="timeout",
                message="Connection timed out after 30 seconds",
            )
        except aiohttp.ClientConnectorDNSError as e:
            _LOGGER.warning("DNS resolution failed for %s: %s", self.host, e)
            return ConnectionResult(
                success=False,
                error="dns_error",
                message=f"Could not resolve hostname: {self.host}",
            )
        except aiohttp.ClientConnectorError as e:
            _LOGGER.warning("Connection failed for %s: %s", self.host, e)
            return ConnectionResult(
                success=False,
                error="connection_refused",
                message=str(e),
            )
        except aiohttp.ClientResponseError as e:
            _LOGGER.warning("HTTP error for %s: %s", self.host, e)
            return ConnectionResult(
                success=False,
                error="http_error",
                message=f"HTTP error {e.status}: {e.message}",
            )
        except Exception as e:
            _LOGGER.warning("Connection test failed for %s: %s", self.host, e)
            return ConnectionResult(
                success=False,
                error="unknown",
                message=str(e),
            )
        else:
            _LOGGER.debug("Connection test successful for %s", self.host)
            return ConnectionResult(success=True)

    # Pro-specific navigation methods
    # These simulate the physical button presses on SmallTV Pro devices

    async def navigate_next(self) -> None:
        """Navigate to next page (Pro devices).

        Simulates pressing the right/next button on the device.
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?page=1") as response:
            response.raise_for_status()
        _LOGGER.debug("Navigated to next page")

    async def navigate_previous(self) -> None:
        """Navigate to previous page (Pro devices).

        Simulates pressing the left/previous button on the device.
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?page=-1") as response:
            response.raise_for_status()
        _LOGGER.debug("Navigated to previous page")

    async def navigate_enter(self) -> None:
        """Press enter/exit button (Pro devices).

        Simulates pressing the enter/menu button on the device.
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?enter=-1") as response:
            response.raise_for_status()
        _LOGGER.debug("Pressed enter button")

    async def reboot(self) -> None:
        """Reboot the device (Pro devices)."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?reboot=1") as response:
            response.raise_for_status()
        _LOGGER.debug("Rebooting device")

    async def detect_model(self) -> str:
        """Attempt to detect the device model.

        Pro devices use /.sys/ paths, Ultra devices use root paths.
        Returns MODEL_PRO, MODEL_ULTRA, or MODEL_UNKNOWN.
        """
        session = await self._get_session()

        # Try Pro-specific path first (/.sys/app.json)
        try:
            async with session.get(
                f"{self.base_url}/.sys/app.json", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self.model = MODEL_PRO
                    _LOGGER.info("Detected device model: SmallTV Pro")
                    return self.model
        except Exception as err:
            _LOGGER.debug("Pro path /.sys/app.json not available: %s", err)

        # Fall back to Ultra (standard path works)
        try:
            async with session.get(
                f"{self.base_url}/app.json", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self.model = MODEL_ULTRA
                    _LOGGER.info("Detected device model: SmallTV Ultra")
                    return self.model
        except Exception as err:
            _LOGGER.debug("Ultra path /app.json not available: %s", err)

        _LOGGER.warning("Could not detect device model for %s", self.host)
        return MODEL_UNKNOWN
