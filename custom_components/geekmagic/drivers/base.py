"""Driver base class and shared dataclasses for GeekMagic firmwares."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import aiohttp

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)
DETECT_TIMEOUT = aiohttp.ClientTimeout(total=5)


@dataclass
class ConnectionResult:
    """Result of a connection test."""

    success: bool
    error: Literal[
        "none", "timeout", "connection_refused", "dns_error", "http_error", "unknown"
    ] = "none"
    message: str | None = None

    def __bool__(self) -> bool:
        return self.success


@dataclass
class DeviceState:
    """Current device display state."""

    theme: int
    brightness: int | None
    current_image: str | None


@dataclass
class SpaceInfo:
    """Device storage info, bytes."""

    total: int
    free: int


class DeviceDriver(ABC):
    """Firmware-specific HTTP behaviour for a GeekMagic device.

    Subclasses implement endpoint URLs and quirks. Capability flags
    (`supports_navigation`, `supports_on_demand_image`, `brightness_range`,
    `custom_image_theme`) let the coordinator branch without sniffing the
    model name.
    """

    model: str
    sw_version: str | None = None
    custom_image_theme: int
    brightness_range: tuple[int, int] = (0, 100)
    supports_navigation: bool = False
    supports_on_demand_image: bool = True

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self.base_url = base_url
        self._session = session

    def is_custom_image_theme(self, theme: int) -> bool:
        """Return True when `theme` is this firmware's custom-image mode."""
        return theme == self.custom_image_theme

    def clamp_brightness(self, value: int) -> int:
        lo, hi = self.brightness_range
        return max(lo, min(hi, value))

    @abstractmethod
    async def get_state(self) -> DeviceState: ...

    @abstractmethod
    async def get_space(self) -> SpaceInfo: ...

    @abstractmethod
    async def get_brightness(self) -> int: ...

    @abstractmethod
    async def set_brightness(self, value: int) -> None: ...

    @abstractmethod
    async def set_theme(self, theme: int) -> None: ...

    async def set_theme_custom(self) -> None:
        """Switch the device to its custom-image display mode."""
        await self.set_theme(self.custom_image_theme)

    @abstractmethod
    async def set_image(self, filename: str) -> None: ...

    @abstractmethod
    async def upload(self, image_data: bytes, filename: str) -> None: ...

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Upload `image_data` then make the device display it."""
        await self.upload(image_data, filename)
        await self.set_image(filename)

    @abstractmethod
    async def delete_file(self, path: str) -> None: ...

    @abstractmethod
    async def clear_images(self) -> None: ...

    @abstractmethod
    async def reboot(self) -> None: ...

    async def navigate_next(self) -> None:
        _LOGGER.debug("navigate_next not supported on %s", self.model)

    async def navigate_previous(self) -> None:
        _LOGGER.debug("navigate_previous not supported on %s", self.model)

    async def navigate_enter(self) -> None:
        _LOGGER.debug("navigate_enter not supported on %s", self.model)

    async def test_connection(self) -> ConnectionResult:
        """Probe the device with a cheap GET to confirm reachability."""
        try:
            await self.get_space()
        except TimeoutError:
            return ConnectionResult(
                success=False,
                error="timeout",
                message="Connection timed out after 30 seconds",
            )
        except aiohttp.ClientConnectorDNSError as e:
            return ConnectionResult(
                success=False,
                error="dns_error",
                message=f"Could not resolve hostname: {e}",
            )
        except aiohttp.ClientConnectorError as e:
            return ConnectionResult(success=False, error="connection_refused", message=str(e))
        except aiohttp.ClientResponseError as e:
            return ConnectionResult(
                success=False,
                error="http_error",
                message=f"HTTP error {e.status}: {e.message}",
            )
        except Exception as e:
            return ConnectionResult(success=False, error="unknown", message=str(e))
        return ConnectionResult(success=True)
