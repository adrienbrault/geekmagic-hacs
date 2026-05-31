"""Firmware driver abstraction for GeekMagic displays.

Different GeekMagic firmwares expose very different HTTP APIs. Rather than
branching on ``device.model`` throughout the codebase, each firmware is
implemented as a :class:`FirmwareDriver`. ``GeekMagicDevice`` is a thin facade
that detects the firmware once and delegates every call to the matching driver.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Shared HTTP timeout for normal requests. Detection uses a shorter timeout.
TIMEOUT = aiohttp.ClientTimeout(total=30)

# Async callable returning the shared aiohttp session. The facade owns the
# session lifecycle; drivers never create or close sessions themselves.
SessionProvider = Callable[[], Awaitable[aiohttp.ClientSession]]


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
    """Represents the current device state.

    ``theme`` is ``None`` when the firmware does not expose the active theme
    (e.g. SmallTV-PRO V3.3.76 has no ``/app.json``).
    """

    theme: int | None
    brightness: int | None
    current_image: str | None


@dataclass
class SpaceInfo:
    """Represents device storage info."""

    total: int
    free: int


@dataclass(frozen=True)
class DriverCapabilities:
    """Feature flags describing what a firmware supports.

    These let the coordinator and entities adapt behaviour without knowing the
    concrete firmware.
    """

    # Device supports /set?page= and /set?enter= navigation (Pro only).
    supports_navigation: bool = False
    # Device can be told to display a specific named image on demand. False for
    # firmwares whose display is a device-managed slideshow (SD_PRO).
    supports_on_demand_image: bool = True
    # The theme number that means "show the integration's rendered image"
    # (Ultra 3 = Photo Album, Pro 4 = Picture). None when the firmware has no
    # such concept (SD_PRO, where the dashboard is faked via the slideshow).
    custom_theme: int | None = None
    # Selectable device built-in modes, mapped display-name -> theme number.
    # Firmware-specific: Ultra and Pro number their themes differently, so this
    # cannot be a single global table. Empty means "no built-in modes to offer".
    builtin_modes: dict[str, int] = field(default_factory=dict)


async def classify_connection(
    host: str, probe: Callable[[], Awaitable[object]]
) -> ConnectionResult:
    """Run ``probe`` and translate exceptions into a :class:`ConnectionResult`.

    Shared by all drivers so connection-test error handling stays consistent.
    """
    try:
        await probe()
    except TimeoutError:
        _LOGGER.warning("Connection test timed out for %s", host)
        return ConnectionResult(
            success=False, error="timeout", message="Connection timed out after 30 seconds"
        )
    except aiohttp.ClientConnectorDNSError as e:
        _LOGGER.warning("DNS resolution failed for %s: %s", host, e)
        return ConnectionResult(
            success=False, error="dns_error", message=f"Could not resolve hostname: {host}"
        )
    except aiohttp.ClientConnectorError as e:
        _LOGGER.warning("Connection failed for %s: %s", host, e)
        return ConnectionResult(success=False, error="connection_refused", message=str(e))
    except aiohttp.ClientResponseError as e:
        _LOGGER.warning("HTTP error for %s: %s", host, e)
        return ConnectionResult(
            success=False, error="http_error", message=f"HTTP error {e.status}: {e.message}"
        )
    except Exception as e:
        _LOGGER.warning("Connection test failed for %s: %s", host, e)
        return ConnectionResult(success=False, error="unknown", message=str(e))
    else:
        _LOGGER.debug("Connection test successful for %s", host)
        return ConnectionResult(success=True)


class FirmwareDriver(ABC):
    """Abstract HTTP driver for a specific GeekMagic firmware family."""

    # Subclasses set these (instances may override firmware_version at detection).
    model: str = "unknown"
    model_name: str = "SmallTV"
    capabilities: DriverCapabilities = DriverCapabilities()

    def __init__(
        self,
        host: str,
        base_url: str,
        session_provider: SessionProvider,
        firmware_version: str | None = None,
    ) -> None:
        """Initialize the driver.

        Args:
            host: Device host (``ip`` or ``ip:port``).
            base_url: Fully-qualified base URL (e.g. ``http://192.168.1.5``).
            session_provider: Async callable returning the shared session.
            firmware_version: Firmware version string, if known from detection.
        """
        self.host = host
        self.base_url = base_url
        self._session_provider = session_provider
        self.firmware_version = firmware_version

    async def _session(self) -> aiohttp.ClientSession:
        """Return the shared aiohttp session."""
        return await self._session_provider()

    # -- abstract API surface (mirrors what the coordinator/entities call) ----

    @abstractmethod
    async def test_connection(self) -> ConnectionResult:
        """Test whether the device is reachable and speaks this firmware."""

    @abstractmethod
    async def get_state(self) -> DeviceState:
        """Return current theme / brightness / image."""

    @abstractmethod
    async def get_space(self) -> SpaceInfo:
        """Return storage info in bytes."""

    @abstractmethod
    async def get_brightness(self) -> int | None:
        """Return current brightness (0-100), or None if unavailable."""

    @abstractmethod
    async def set_brightness(self, value: int) -> None:
        """Set display brightness."""

    @abstractmethod
    async def set_theme(self, theme: int) -> None:
        """Switch to a specific theme number."""

    @abstractmethod
    async def set_theme_custom(self) -> None:
        """Switch to the firmware's custom-image / dashboard mode."""

    @abstractmethod
    async def set_image(self, filename: str) -> None:
        """Display a previously uploaded image by name."""

    @abstractmethod
    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to the device."""

    @abstractmethod
    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Upload an image and immediately display it."""

    @abstractmethod
    async def delete_file(self, path: str) -> None:
        """Delete a file from the device."""

    @abstractmethod
    async def clear_images(self) -> None:
        """Remove all uploaded images."""

    @abstractmethod
    async def reboot(self) -> None:
        """Reboot the device."""

    # Navigation defaults to no-op so non-Pro firmwares inherit it for free.

    async def navigate_next(self) -> None:
        """Navigate to next page (Pro devices)."""
        return

    async def navigate_previous(self) -> None:
        """Navigate to previous page (Pro devices)."""
        return

    async def navigate_enter(self) -> None:
        """Press enter/menu (Pro devices)."""
        return

    # -- shared helpers -------------------------------------------------------

    async def _get_json(self, path: str) -> dict:
        """GET ``path`` and parse the JSON body (device sends text/plain)."""
        session = await self._session()
        async with session.get(f"{self.base_url}{path}") as response:
            response.raise_for_status()
            return await response.json(content_type=None)

    async def _get(self, path: str) -> None:
        """GET ``path`` expecting no body, raising on HTTP error."""
        session = await self._session()
        async with session.get(f"{self.base_url}{path}") as response:
            response.raise_for_status()

    async def _post_multipart_image(
        self, path: str, image_data: bytes, filename: str, field: str = "file"
    ) -> None:
        """POST a multipart image upload, tolerating known malformed responses.

        GeekMagic firmwares return malformed HTTP responses on a successful
        upload:
          - SmallTV-Ultra: duplicate Content-Length headers
          - SmallTV-Pro: "Data after Connection: close" (OK + a new response)
        These are swallowed because the upload itself succeeds.
        """
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
        else:
            content_type = "image/jpeg"

        form = aiohttp.FormData()
        form.add_field(field, image_data, filename=filename, content_type=content_type)

        session = await self._session()
        try:
            async with session.post(f"{self.base_url}{path}", data=form) as response:
                response.raise_for_status()
        except aiohttp.ClientResponseError as e:
            if e.status == 400:
                msg = str(e.message) if e.message else ""
                if "Duplicate Content-Length" in msg or "Data after" in msg:
                    _LOGGER.debug("Ignoring malformed HTTP response from device: %s", msg)
                    return
            raise
