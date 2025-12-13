"""GeekMagic device HTTP API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


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

    def __init__(self, host: str, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the device client.

        Args:
            host: IP address or hostname of the device
            session: Optional aiohttp session (created if not provided)
        """
        self.host = host
        self.base_url = f"http://{host}"
        self._session = session
        self._owns_session = session is None

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
            theme: Theme number (3 = custom image)
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?theme={theme}") as response:
            response.raise_for_status()
        _LOGGER.debug("Set theme to %d", theme)

    async def set_image(self, filename: str) -> None:
        """Set the displayed image.

        Args:
            filename: Image filename (without path)
        """
        # Ensure we're in custom image mode
        await self.set_theme(3)
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
            # Device returns malformed HTTP (duplicate Content-Length headers)
            # but upload still succeeds, so ignore 400 errors from parsing
            if e.status != 400 or "Duplicate Content-Length" not in str(e.message):
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

    async def test_connection(self) -> bool:
        """Test if the device is reachable.

        Returns:
            True if connection successful, False otherwise
        """
        _LOGGER.debug("Testing connection to %s", self.host)
        try:
            await self.get_state()
        except Exception as e:
            _LOGGER.debug("Connection test failed for %s: %s", self.host, e)
            return False
        else:
            _LOGGER.debug("Connection test successful for %s", self.host)
            return True
