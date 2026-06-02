"""GeekMagic device HTTP client — thin facade over a firmware-specific driver."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import aiohttp

from .const import MODEL_UNKNOWN
from .drivers import (
    ConnectionResult,
    DeviceDriver,
    DeviceState,
    SpaceInfo,
    detect_driver,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)

__all__ = [
    "ConnectionResult",
    "DeviceState",
    "GeekMagicDevice",
    "SpaceInfo",
]


class GeekMagicDevice:
    """HTTP facade for a GeekMagic display.

    Detects the firmware (Stock Pro, Stock Ultra, SD_PRO) at setup time and
    delegates every call to the corresponding `DeviceDriver`. Public method
    names are preserved so callers in `coordinator.py`, `config_flow.py`,
    `__init__.py`, and the entity modules don't need to know about drivers.
    """

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession | None = None,
        model: str = MODEL_UNKNOWN,
    ) -> None:
        if host.startswith(("http://", "https://")):
            parsed = urlparse(host)
            self.host = parsed.netloc
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.host = host
            self.base_url = f"http://{host}"

        self._session = session
        self._owns_session = session is None
        self.model = model
        self.sw_version: str | None = None
        self._driver: DeviceDriver | None = None

    # ----- driver wiring -----

    @property
    def driver(self) -> DeviceDriver:
        if self._driver is None:
            raise RuntimeError(
                "GeekMagicDevice driver not initialised; "
                "call detect_model() or test_connection() first"
            )
        return self._driver

    @property
    def supports_navigation(self) -> bool:
        """True if the device's firmware honours `/set?page=`/`/set?enter=`."""
        return bool(self._driver and self._driver.supports_navigation)

    def is_custom_image_theme(self, theme: int) -> bool:
        """True if `theme` is the firmware's custom-image display mode."""
        if self._driver is None:
            # Conservative default: stock Ultra (3). Used only before detection.
            return theme == 3
        return self._driver.is_custom_image_theme(theme)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def detect_model(self) -> str:
        """Probe the device and pick the right driver."""
        session = await self._get_session()
        driver = await detect_driver(self.base_url, session)
        if driver is None:
            self.model = MODEL_UNKNOWN
            self.sw_version = None
            self._driver = None
            return self.model
        self._driver = driver
        self.model = driver.model
        self.sw_version = driver.sw_version
        return self.model

    # ----- delegated device API -----

    async def get_state(self) -> DeviceState:
        return await self.driver.get_state()

    async def get_space(self) -> SpaceInfo:
        return await self.driver.get_space()

    async def get_brightness(self) -> int:
        return await self.driver.get_brightness()

    async def set_brightness(self, value: int) -> None:
        await self.driver.set_brightness(value)

    async def set_theme(self, theme: int) -> None:
        await self.driver.set_theme(theme)

    async def set_theme_custom(self) -> None:
        await self.driver.set_theme_custom()

    async def set_image(self, filename: str) -> None:
        await self.driver.set_image(filename)

    async def upload(self, image_data: bytes, filename: str) -> None:
        await self.driver.upload(image_data, filename)

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        _LOGGER.debug(
            "Uploading and displaying %s (%d bytes) to %s",
            filename,
            len(image_data),
            self.host,
        )
        await self.driver.upload_and_display(image_data, filename)

    async def delete_file(self, path: str) -> None:
        await self.driver.delete_file(path)

    async def clear_images(self) -> None:
        await self.driver.clear_images()

    async def reboot(self) -> None:
        await self.driver.reboot()

    async def navigate_next(self) -> None:
        await self.driver.navigate_next()

    async def navigate_previous(self) -> None:
        await self.driver.navigate_previous()

    async def navigate_enter(self) -> None:
        await self.driver.navigate_enter()

    async def list_themes(self) -> list[dict]:
        """Return the device's built-in themes (SD_PRO only)."""
        driver = self.driver
        if not hasattr(driver, "list_themes"):
            return []
        return await driver.list_themes()

    async def disable_other_themes(self) -> list[str]:
        """Disable every built-in theme except the one we render into.

        Currently only meaningful for SD_PRO firmware, whose device-side
        theme rotation would otherwise switch away from the integration's
        rendered photo. Returns the list of disabled theme names; an empty
        list means nothing needed changing (or the firmware doesn't support
        this concept).
        """
        driver = self.driver
        if not hasattr(driver, "disable_other_themes"):
            return []
        return await driver.disable_other_themes()

    async def test_connection(self) -> ConnectionResult:  # noqa: PLR0911
        """Confirm the device is reachable and pick its firmware driver.

        Pings the device once first so we can return precise network-level
        errors (timeout, DNS, connection refused). If the ping succeeds,
        detection runs to wire the right driver — failure there becomes a
        generic `http_error` because the device responded but didn't match
        any known firmware.
        """
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/v.json",
                timeout=aiohttp.ClientTimeout(total=10),
            ):
                pass
        except TimeoutError:
            return ConnectionResult(
                success=False,
                error="timeout",
                message="Connection timed out after 10 seconds",
            )
        except aiohttp.ClientConnectorDNSError as err:
            return ConnectionResult(
                success=False,
                error="dns_error",
                message=f"Could not resolve hostname: {err}",
            )
        except aiohttp.ClientConnectorError as err:
            return ConnectionResult(success=False, error="connection_refused", message=str(err))
        except aiohttp.ClientResponseError:
            # An HTTP-level error here is fine — the device responded.
            pass
        except aiohttp.ClientError as err:
            return ConnectionResult(success=False, error="unknown", message=str(err))
        except Exception as err:
            # Bare OSError, etc. — surface so the user sees something.
            return ConnectionResult(success=False, error="unknown", message=str(err))

        try:
            await self.detect_model()
        except Exception as err:
            _LOGGER.warning("Detection failed for %s: %s", self.host, err)
            return ConnectionResult(success=False, error="unknown", message=str(err))

        if self._driver is None:
            return ConnectionResult(
                success=False,
                error="http_error",
                message=(
                    "Device did not respond to firmware-detection probes "
                    "(/v.json, /config, /app.json)."
                ),
            )
        return await self._driver.test_connection()
