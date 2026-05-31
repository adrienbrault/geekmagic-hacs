"""Driver for the SD_PRO community firmware (JUZIPi-tech).

This firmware (web title "Smart Weather Clock") shares no endpoints with stock
GeekMagic firmware. It exposes a unified ``GET /config`` for reads and
``GET /api/set?key=&value=`` for writes, plus a device-managed photo slideshow
(``/photo/*``) and built-in theme rotation (``/theme/*``).

Critically, there is **no** "display this named image now" endpoint. To drive a
live dashboard we use a slideshow workaround: upload each rendered frame as a
photo, keep only that photo enabled, force the Photo theme, and delete the
previous frame. Two alternating filenames are used so the new frame always
exists before the old one is deleted (no blank frame).

Several details could not be confirmed without hardware and are flagged inline:
the ``/api/set`` response format, the brightness write key (``lcd_brightness``),
the ``/photo/upload`` field name, and valid ``/photo/interval`` values.
"""

from __future__ import annotations

import logging

import aiohttp

from ..const import MODEL_SDPRO
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

# Built-in theme index whose mode renders the photo slideshow.
PHOTO_THEME = 2
# Slideshow rotation while we drive a live dashboard. Kept short so a new frame
# shows promptly; the exact set of allowed values is firmware-specific.
DASHBOARD_INTERVAL_SECONDS = 5
# Alternating filenames so the new frame exists before the old is deleted.
_FRAME_NAMES = ("dashboard_a.jpg", "dashboard_b.jpg")


class SdProDriver(FirmwareDriver):
    """HTTP driver for the SD_PRO community firmware."""

    model = MODEL_SDPRO
    model_name = "SmallTV Ultra (SD_PRO)"
    capabilities = DriverCapabilities(
        supports_navigation=False,
        supports_on_demand_image=False,
        supports_builtin_themes=False,
        builtin_theme_threshold=None,
    )

    def __init__(
        self,
        host: str,
        base_url: str,
        session_provider: SessionProvider,
        firmware_version: str | None = None,
    ) -> None:
        """Initialize the SD_PRO driver."""
        super().__init__(host, base_url, session_provider, firmware_version)
        # Name of the frame currently shown, so we can delete it next cycle.
        self._last_frame: str | None = None

    async def test_connection(self) -> ConnectionResult:
        """Probe ``/config`` (the firmware's single read endpoint)."""
        return await classify_connection(self.host, self.get_state)

    async def get_state(self) -> DeviceState:
        """Read theme and brightness from ``/config``."""
        config = await self._get_json("/config")
        return DeviceState(
            theme=config.get("theme"),
            brightness=config.get("brightness"),
            current_image=None,
        )

    async def get_space(self) -> SpaceInfo:
        """Return photo-partition storage from ``/photo/list``.

        ``total``/``used`` here describe the photo partition, not the whole
        device. Falls back to ``/config.freespace`` (free only) if unavailable.
        """
        try:
            data = await self._get_json("/photo/list")
            total = int(data.get("total", 0))
            used = int(data.get("used", 0))
            return SpaceInfo(total=total, free=max(total - used, 0))
        except aiohttp.ClientError:
            config = await self._get_json("/config")
            return SpaceInfo(total=0, free=int(config.get("freespace", 0)))

    async def get_brightness(self) -> int | None:
        """Return brightness from ``/config`` (device range 2-99)."""
        config = await self._get_json("/config")
        brightness = config.get("brightness")
        return int(brightness) if brightness is not None else None

    async def set_brightness(self, value: int) -> None:
        """Set brightness via ``/api/set`` (clamped to the device's 2-99 range).

        The config read key is ``brightness`` but the write key is
        ``lcd_brightness`` (per the firmware JS) — verify on hardware.
        """
        value = max(2, min(99, value))
        await self._get(f"/api/set?key=lcd_brightness&value={value}")
        _LOGGER.debug("Set brightness to %d", value)

    async def set_theme(self, theme: int) -> None:
        """Switch theme via ``/api/set?key=theme``."""
        await self._get(f"/api/set?key=theme&value={theme}")
        _LOGGER.debug("Set theme to %d", theme)

    async def set_theme_custom(self) -> None:
        """Switch to the Photo theme used for the slideshow dashboard."""
        await self.set_theme(PHOTO_THEME)

    async def set_image(self, filename: str) -> None:
        """Enable only ``filename`` in the slideshow (no direct display API)."""
        await self._get(f"/photo/toggle?name={filename}&state=1")
        _LOGGER.debug("Enabled photo %s", filename)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload a photo via ``POST /photo/upload`` (multipart field ``file``)."""
        await self._post_multipart_image("/photo/upload", image_data, filename)
        _LOGGER.debug("Uploaded photo %s (%d bytes)", filename, len(image_data))

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        """Render a live dashboard frame via the slideshow workaround.

        ``filename`` from the coordinator is ignored; we alternate between two
        internal names so the new frame exists before the old is removed.
        """
        new_frame = self._next_frame_name()

        # 1. Upload the new frame.
        await self.upload(image_data, new_frame)
        # 2. Ensure the device is showing the photo slideshow.
        await self.set_theme(PHOTO_THEME)
        # 3. Enable only the new frame and keep rotation short.
        await self.set_image(new_frame)
        try:
            await self._get(f"/photo/interval?val={DASHBOARD_INTERVAL_SECONDS}")
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to set photo interval (non-fatal): %s", err)
        # 4. Retire the previous frame.
        if self._last_frame and self._last_frame != new_frame:
            await self._retire_frame(self._last_frame)
        self._last_frame = new_frame
        _LOGGER.debug("Displayed dashboard frame %s", new_frame)

    async def delete_file(self, path: str) -> None:
        """Delete a photo by name (``/photo/delete``)."""
        name = path.rsplit("/", 1)[-1]
        await self._get(f"/photo/delete?name={name}")
        _LOGGER.debug("Deleted photo %s", name)

    async def clear_images(self) -> None:
        """Delete every photo from the slideshow pool."""
        data = await self._get_json("/photo/list")
        for entry in data.get("files", []):
            name = entry.get("name")
            if name:
                await self._get(f"/photo/delete?name={name}")
        self._last_frame = None
        _LOGGER.debug("Cleared all photos")

    async def reboot(self) -> None:
        """Reboot via ``/restart``; the device may drop the connection first."""
        try:
            await self._get("/restart")
        except (aiohttp.ClientError, TimeoutError) as err:
            # The device reboots before responding; treat any error as success.
            _LOGGER.debug("Restart request errored as expected (device rebooting): %s", err)
        _LOGGER.debug("Rebooting device")

    def _next_frame_name(self) -> str:
        """Return the alternate frame name to the one currently shown."""
        if self._last_frame == _FRAME_NAMES[0]:
            return _FRAME_NAMES[1]
        return _FRAME_NAMES[0]

    async def _retire_frame(self, name: str) -> None:
        """Disable and delete a previous frame, tolerating errors."""
        try:
            await self._get(f"/photo/toggle?name={name}&state=0")
            await self._get(f"/photo/delete?name={name}")
        except aiohttp.ClientError as err:
            _LOGGER.debug("Failed to retire frame %s (non-fatal): %s", name, err)
