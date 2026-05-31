"""Driver for stock GeekMagic firmware (SmallTV Pro and Ultra).

Pro and Ultra share ~90% of the same root HTTP API; the differences are
captured in a small per-variant table:

  - custom-image theme number (Ultra 3 "Photo Album", Pro 4 "Picture")
  - brightness read path (Ultra ``/brt.json``, Pro ``/.sys/brt.json``)
  - whether ``/app.json`` exists (Ultra yes, Pro no)
  - device navigation support (Pro only)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..const import MODEL_PRO, MODEL_ULTRA
from .base import (
    ConnectionResult,
    DeviceState,
    DriverCapabilities,
    FirmwareDriver,
    SessionProvider,
    SpaceInfo,
    classify_connection,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StockVariant:
    """Per-model configuration for the stock firmware driver."""

    model: str
    model_name: str
    custom_theme_number: int
    brightness_path: str
    # Path returning {"theme": N}, or None if the firmware has no such endpoint.
    state_path: str | None
    capabilities: DriverCapabilities


# Ultra V9 theme map (from docs/devices/old-ultra): 1=Weather Clock Today,
# 2=Weather Forecast, 3=Photo Album (custom image), 4-6=Time styles,
# 7=Simple Weather Clock. Theme 3 is the custom slot, so it is excluded here.
_ULTRA_BUILTIN_MODES = {
    "Weather Clock Today": 1,
    "Weather Forecast": 2,
    "Time Style 1": 4,
    "Time Style 2": 5,
    "Time Style 3": 6,
    "Simple Weather Clock": 7,
}

# Pro V3.3.76 theme map (from docs/devices/new-pro): 0=Bitcoin, 1=CoinGecko,
# 2=Stocks, 3=Weather, 4=Picture (custom image), 5=Monitor, 6=Clock, 7=Ideas.
# Theme 4 is the custom slot, so it is excluded here.
_PRO_BUILTIN_MODES = {
    "Bitcoin": 0,
    "CoinGecko": 1,
    "Stocks": 2,
    "Weather": 3,
    "Monitor": 5,
    "Clock": 6,
    "Ideas": 7,
}

ULTRA = StockVariant(
    model=MODEL_ULTRA,
    model_name="SmallTV Ultra",
    custom_theme_number=3,
    brightness_path="/brt.json",
    state_path="/app.json",
    capabilities=DriverCapabilities(
        supports_navigation=False,
        custom_theme=3,
        builtin_modes=_ULTRA_BUILTIN_MODES,
    ),
)

PRO = StockVariant(
    model=MODEL_PRO,
    model_name="SmallTV Pro",
    custom_theme_number=4,
    # V3.3.76EN exposes brightness under /.sys/, and has no /app.json.
    brightness_path="/.sys/brt.json",
    state_path=None,
    capabilities=DriverCapabilities(
        supports_navigation=True,
        custom_theme=4,
        builtin_modes=_PRO_BUILTIN_MODES,
    ),
)


class StockDriver(FirmwareDriver):
    """HTTP driver for stock GeekMagic firmware."""

    def __init__(
        self,
        variant: StockVariant,
        host: str,
        base_url: str,
        session_provider: SessionProvider,
        firmware_version: str | None = None,
    ) -> None:
        """Initialize from a :class:`StockVariant`."""
        super().__init__(host, base_url, session_provider, firmware_version)
        self._variant = variant
        self.model = variant.model
        self.model_name = variant.model_name
        self.capabilities = variant.capabilities

    async def test_connection(self) -> ConnectionResult:
        """Probe ``/space.json`` (supported across stock firmware versions)."""
        return await classify_connection(self.host, self.get_space)

    async def get_state(self) -> DeviceState:
        """Return device state, degrading gracefully when /app.json is absent."""
        if self._variant.state_path is None:
            # Pro V3.3.76 has no state endpoint; avoid a guaranteed 404.
            return DeviceState(theme=None, brightness=None, current_image=None)
        data = await self._get_json(self._variant.state_path)
        return DeviceState(
            theme=data.get("theme", 0),
            brightness=data.get("brt"),
            current_image=data.get("img"),
        )

    async def get_space(self) -> SpaceInfo:
        """Return storage info from ``/space.json``."""
        data = await self._get_json("/space.json")
        return SpaceInfo(total=data.get("total", 0), free=data.get("free", 0))

    async def get_brightness(self) -> int | None:
        """Return brightness from the variant's brightness path."""
        data = await self._get_json(self._variant.brightness_path)
        return int(data.get("brt", 0))

    async def set_brightness(self, value: int) -> None:
        """Set brightness (clamped 0-100)."""
        value = max(0, min(100, value))
        await self._get(f"/set?brt={value}")
        _LOGGER.debug("Set brightness to %d", value)

    async def set_theme(self, theme: int) -> None:
        """Switch to a specific theme number."""
        await self._get(f"/set?theme={theme}")
        _LOGGER.debug("Set theme to %d", theme)

    async def set_theme_custom(self) -> None:
        """Switch to the variant's custom-image theme (Ultra 3, Pro 4)."""
        await self.set_theme(self._variant.custom_theme_number)

    async def set_image(self, filename: str) -> None:
        """Switch to custom mode and display the named image."""
        await self.set_theme_custom()
        await self._get(f"/set?img=/image/{filename}")
        _LOGGER.debug("Set image to %s", filename)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to ``/image/``."""
        await self._post_multipart_image("/doUpload?dir=/image/", image_data, filename)
        _LOGGER.debug("Uploaded %s (%d bytes)", filename, len(image_data))

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Upload an image and immediately display it."""
        await self.upload(image_data, filename)
        await self.set_image(filename)
        _LOGGER.debug("Upload and display completed for %s", filename)

    async def delete_file(self, path: str) -> None:
        """Delete a file by full path."""
        await self._get(f"/delete?file={path}")
        _LOGGER.debug("Deleted %s", path)

    async def clear_images(self) -> None:
        """Clear all images."""
        await self._get("/set?clear=image")
        _LOGGER.debug("Cleared all images")

    async def navigate_next(self) -> None:
        """Navigate to next page (Pro devices)."""
        await self._get("/set?page=1")
        _LOGGER.debug("Navigated to next page")

    async def navigate_previous(self) -> None:
        """Navigate to previous page (Pro devices)."""
        await self._get("/set?page=-1")
        _LOGGER.debug("Navigated to previous page")

    async def navigate_enter(self) -> None:
        """Press enter/menu button (Pro devices)."""
        await self._get("/set?enter=-1")
        _LOGGER.debug("Pressed enter button")

    async def reboot(self) -> None:
        """Reboot the device."""
        await self._get("/set?reboot=1")
        _LOGGER.debug("Rebooting device")
