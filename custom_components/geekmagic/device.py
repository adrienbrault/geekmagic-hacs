"""GeekMagic device HTTP API client."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import ClassVar, Literal
from urllib.parse import quote, urlparse

import aiohttp

from .const import MODEL_PRO, MODEL_SD_PRO, MODEL_ULTRA, MODEL_UNKNOWN

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

    theme: int | None
    brightness: int | None
    current_image: str | None


@dataclass
class AlbumSettings:
    """Represents stock firmware photo album settings."""

    interval: int | None
    gif_loop: int | None
    autoplay: int | None


@dataclass
class DeviceSettingsBackup:
    """Best-effort snapshot of mutable device settings."""

    state: DeviceState | None
    brightness: int | None
    album: AlbumSettings | None
    pro_album_files: list[DeviceFileBackup] | None = None
    sdpro_photos: SdProPhotoSettings | None = None
    sdpro_themes: SdProThemeSettings | None = None
    sdpro_active_theme: int | None = None


@dataclass
class DeviceFile:
    """Represents a file stored on stock firmware."""

    name: str
    path: str
    size_kb: int | None = None


@dataclass
class DeviceFileBackup:
    """Represents a backed-up device file."""

    file: DeviceFile
    data: bytes


@dataclass
class SdProPhoto:
    """Represents one SD_PRO slideshow file."""

    name: str
    size: int
    enabled: bool


@dataclass
class SdProPhotoSettings:
    """Represents SD_PRO photo slideshow settings."""

    files: list[SdProPhoto]
    total: int
    used: int
    interval: int | None


@dataclass
class SdProTheme:
    """Represents one SD_PRO firmware theme."""

    id: int
    name: str
    enabled: bool


@dataclass
class SdProThemeSettings:
    """Represents SD_PRO theme rotation settings."""

    themes: list[SdProTheme]
    interval: int | None


@dataclass
class SpaceInfo:
    """Represents device storage info."""

    total: int
    free: int


class GeekMagicDevice:
    """HTTP client for GeekMagic display devices."""

    PRO_BUILTIN_MODES: ClassVar[dict[str, int]] = {
        "Bitcoin": 0,
        "CoinGecko": 1,
        "Stocks": 2,
        "Weather": 3,
        "Monitor": 5,
        "Clock": 6,
        "Ideas": 7,
    }
    ULTRA_BUILTIN_MODES: ClassVar[dict[str, int]] = {
        "Weather Clock Today": 1,
        "Weather Forecast": 2,
        "Time Style 1": 4,
        "Time Style 2": 5,
        "Time Style 3": 6,
        "Simple Weather Clock": 7,
    }
    SD_PRO_BUILTIN_MODES: ClassVar[dict[str, int]] = {
        "Classic": 0,
        "Weather": 1,
        "Photo": 2,
        "Dial": 3,
        "Simple": 4,
        "Weather Forecast": 5,
        "Flip Clock": 6,
    }

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
        self.model_name: str | None = None
        self.firmware_version: str | None = None
        self._last_theme: int | None = None
        self._last_image: str | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self._session

    async def _check_device_response(self, response: aiohttp.ClientResponse, action: str) -> None:
        """Raise for HTTP errors and firmware-level FAIL responses."""
        response.raise_for_status()
        try:
            text = (await response.text()).strip()
        except Exception:
            return

        if text.upper() == "FAIL":
            raise RuntimeError(f"Device rejected {action}: {text}")

    async def _get_json(self, path: str) -> dict[str, object]:
        """Fetch a JSON object from the device."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}{path}") as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
            if not isinstance(data, dict):
                raise TypeError(f"Expected JSON object from {path}")
            return data

    async def _get_text(self, path: str) -> str:
        """Fetch text from the device."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}{path}") as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as err:
            if self._is_malformed_firmware_response(err):
                return (await self._raw_http_get(path)).decode(errors="replace")
            raise

    async def _get_bytes(self, path: str) -> bytes:
        """Fetch bytes from the device."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}{path}") as response:
                response.raise_for_status()
                return await response.read()
        except aiohttp.ClientResponseError as err:
            if self._is_malformed_firmware_response(err):
                return await self._raw_http_get(path)
            raise

    @staticmethod
    def _is_malformed_firmware_response(err: aiohttp.ClientResponseError) -> bool:
        """Return whether aiohttp rejected a known malformed device response."""
        message = str(err.message) if err.message else ""
        return err.status == 400 and (
            "Duplicate Content-Length" in message or "Data after" in message
        )

    async def _raw_http_get(self, path: str) -> bytes:
        """Fallback HTTP/1.0 GET for firmware responses aiohttp refuses to parse."""
        parsed = urlparse(self.base_url)
        host = parsed.hostname or self.host
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "https":
            raise RuntimeError("Raw fallback only supports HTTP devices")

        reader, writer = await asyncio.open_connection(host, port)
        try:
            request = f"GET {path} HTTP/1.0\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
            writer.write(request.encode("ascii"))
            await writer.drain()
            raw = await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()

        header, _, body = raw.partition(b"\r\n\r\n")
        status_line = header.splitlines()[0] if header else b""
        if not status_line.startswith(b"HTTP/") or b" 200 " not in status_line:
            raise RuntimeError(f"Raw HTTP GET failed for {path}: {status_line!r}")
        return body

    @staticmethod
    def _optional_int(value: object) -> int | None:
        """Parse an optional integer value returned by device JSON."""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _state_from_data(data: dict[str, object]) -> DeviceState:
        """Build DeviceState from a stock firmware state payload."""
        return DeviceState(
            theme=GeekMagicDevice._optional_int(data.get("theme")),
            brightness=GeekMagicDevice._optional_int(data.get("brt")),
            current_image=str(data["img"]) if data.get("img") else None,
        )

    @property
    def custom_theme(self) -> int:
        """Return the device theme used for custom uploaded images."""
        if self.model == MODEL_SD_PRO:
            return 2
        return 4 if self.model == MODEL_PRO else 3

    @property
    def builtin_modes(self) -> dict[str, int]:
        """Return built-in display modes for the detected model."""
        if self.model == MODEL_PRO:
            return self.PRO_BUILTIN_MODES
        if self.model == MODEL_SD_PRO:
            return self.SD_PRO_BUILTIN_MODES
        return self.ULTRA_BUILTIN_MODES

    def is_custom_theme(self, theme: int | None) -> bool:
        """Return whether a device theme is the custom image mode."""
        return theme == self.custom_theme

    def is_builtin_theme(self, theme: int | None) -> bool:
        """Return whether a device theme is handled by device firmware."""
        return theme is not None and not self.is_custom_theme(theme)

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
        if self.model == MODEL_SD_PRO:
            data = await self._get_json("/config")
            return DeviceState(
                theme=self._optional_int(data.get("theme")),
                brightness=self._optional_int(data.get("brightness")),
                current_image=None,
            )

        session = await self._get_session()
        paths = ["/.sys/app.json", "/app.json"] if self.model == MODEL_PRO else ["/app.json"]
        last_404: aiohttp.ClientResponseError | None = None
        for path in paths:
            try:
                async with session.get(f"{self.base_url}{path}") as response:
                    response.raise_for_status()
                    # Device returns text/plain content type, so we need to accept any
                    data = await response.json(content_type=None)
                    state = self._state_from_data(data)
                    _LOGGER.debug(
                        "Device state: theme=%s, brightness=%s, image=%s",
                        state.theme,
                        state.brightness,
                        state.current_image,
                    )
                    return state
            except aiohttp.ClientResponseError as err:
                if self.model == MODEL_PRO and err.status == 404:
                    last_404 = err
                    continue
                raise

        if self.model == MODEL_PRO and last_404 is not None:
            _LOGGER.debug("Pro firmware has no state path; using last known state")
            return DeviceState(
                theme=self._last_theme,
                brightness=None,
                current_image=self._last_image,
            )

        raise RuntimeError("Device state was not read")

    async def get_space(self) -> SpaceInfo:
        """Get device storage information.

        Returns:
            SpaceInfo with total and free bytes
        """
        _LOGGER.debug("Getting storage info from %s", self.host)
        if self.model == MODEL_SD_PRO:
            photos = await self.get_sdpro_photo_settings()
            return SpaceInfo(total=photos.total, free=max(0, photos.total - photos.used))

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
        if self.model == MODEL_SD_PRO:
            data = await self._get_json("/config")
            brightness = self._optional_int(data.get("brightness"))
            return brightness or 0

        session = await self._get_session()
        path = "/.sys/brt.json" if self.model == MODEL_PRO else "/brt.json"
        async with session.get(f"{self.base_url}{path}") as response:
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
        if self.model == MODEL_SD_PRO:
            value = max(2, min(99, value))
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/set?key=lcd_brightness&value={value}"
            ) as response:
                await self._check_device_response(response, "brightness update")
            _LOGGER.debug("Set SD_PRO brightness to %d", value)
            return

        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?brt={value}") as response:
            await self._check_device_response(response, "brightness update")
        _LOGGER.debug("Set brightness to %d", value)

    async def set_theme(self, theme: int) -> None:
        """Set device theme.

        Args:
            theme: Theme number (3 = custom image on Ultra, 4 = custom image on Pro)
        """
        if self.model == MODEL_SD_PRO:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/set?key=theme&value={theme}") as response:
                await self._check_device_response(response, "theme update")
            self._last_theme = theme
            _LOGGER.debug("Set SD_PRO theme to %d", theme)
            return

        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?theme={theme}") as response:
            await self._check_device_response(response, "theme update")
        self._last_theme = theme
        _LOGGER.debug("Set theme to %d", theme)

    async def get_album_settings(self) -> AlbumSettings:
        """Get photo album settings when exposed by stock firmware."""
        session = await self._get_session()
        path = "/.sys/album.json" if self.model == MODEL_PRO else "/album.json"
        async with session.get(f"{self.base_url}{path}") as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
            return AlbumSettings(
                interval=self._optional_int(data.get("i_i")),
                gif_loop=self._optional_int(data.get("gif_loop")),
                autoplay=self._optional_int(data.get("autoplay")),
            )

    async def set_album_display(
        self,
        interval: int | None = 1,
        gif_loop: int | None = 1,
        autoplay: int | None = 1,
    ) -> None:
        """Enable the Pro Picture album mode used for uploaded images."""
        query_parts: list[str] = []
        if interval is not None:
            query_parts.append(f"i_i={max(1, interval)}")
        if gif_loop is not None:
            query_parts.append(f"gif_loop={max(1, gif_loop)}")
        if autoplay is not None:
            query_parts.append(f"autoplay={1 if autoplay else 0}")
        if not query_parts:
            return

        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?{'&'.join(query_parts)}") as response:
            await self._check_device_response(response, "album display update")
        _LOGGER.debug(
            "Updated album display interval=%s gif_loop=%s autoplay=%s",
            interval,
            gif_loop,
            autoplay,
        )

    async def get_pro_image_files(self) -> list[DeviceFile]:
        """List files in the stock firmware image album."""
        html = await self._get_text("/filelist?dir=/image/")

        files: list[DeviceFile] = []
        pattern = re.compile(
            r"<a href='(?P<path>[^']+)'>(?P<name>[^<]+)</a></td><td>(?P<size>[^<]+)</td>"
        )
        for match in pattern.finditer(html):
            size = self._optional_int(match.group("size"))
            files.append(
                DeviceFile(
                    name=match.group("name"),
                    path=match.group("path"),
                    size_kb=size,
                )
            )
        return files

    async def backup_pro_album_files(self) -> list[DeviceFileBackup]:
        """Download the current stock firmware image album for later restore."""
        return [
            DeviceFileBackup(file=file, data=await self._get_bytes(file.path))
            for file in await self.get_pro_image_files()
        ]

    async def restore_pro_album_files(self, backups: list[DeviceFileBackup]) -> None:
        """Restore a previously backed-up stock firmware image album."""
        await self.clear_pro_album_files()
        for backup in backups:
            await self.upload(backup.data, backup.file.name)

    async def clear_pro_album_files(self) -> None:
        """Clear the stock firmware image album, including files clear=image leaves behind."""
        await self.clear_images()
        for file in await self.get_pro_image_files():
            await self.delete_file(file.path)

    async def pro_image_exists(self, filename: str) -> bool:
        """Return whether a stock firmware image album contains filename."""
        return any(file.name == filename for file in await self.get_pro_image_files())

    async def keep_only_pro_image(self, filename: str) -> None:
        """Delete every Pro album file except filename."""
        kept = False
        for file in await self.get_pro_image_files():
            if file.name == filename:
                kept = True
                continue
            await self.delete_file(file.path)

        if not kept:
            raise RuntimeError(f"Uploaded image {filename} was not found in the Pro album")

    async def get_sdpro_photo_settings(self) -> SdProPhotoSettings:
        """Read SD_PRO photo slideshow settings."""
        data = await self._get_json("/photo/list")
        files_data = data.get("files", [])
        files: list[SdProPhoto] = []
        if isinstance(files_data, list):
            for item in files_data:
                if isinstance(item, dict):
                    name = item.get("name")
                    if name is not None:
                        files.append(
                            SdProPhoto(
                                name=str(name),
                                size=self._optional_int(item.get("size")) or 0,
                                enabled=bool(item.get("enabled")),
                            )
                        )
        return SdProPhotoSettings(
            files=files,
            total=self._optional_int(data.get("total")) or 0,
            used=self._optional_int(data.get("used")) or 0,
            interval=self._optional_int(data.get("interval")),
        )

    async def get_sdpro_theme_settings(self) -> SdProThemeSettings:
        """Read SD_PRO theme rotation settings."""
        data = await self._get_json("/theme/list")
        themes_data = data.get("themes", [])
        themes: list[SdProTheme] = []
        if isinstance(themes_data, list):
            for item in themes_data:
                if isinstance(item, dict):
                    theme_id = self._optional_int(item.get("id"))
                    if theme_id is not None:
                        themes.append(
                            SdProTheme(
                                id=theme_id,
                                name=str(item.get("name", theme_id)),
                                enabled=bool(item.get("enabled")),
                            )
                        )
        return SdProThemeSettings(
            themes=themes,
            interval=self._optional_int(data.get("interval")),
        )

    async def set_sdpro_photo_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a photo in the SD_PRO slideshow."""
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/photo/toggle?name={quote(name)}&state={1 if enabled else 0}"
        ) as response:
            await self._check_device_response(response, f"photo toggle {name}")

    async def set_sdpro_photo_interval(self, interval: int) -> None:
        """Set SD_PRO photo slideshow interval."""
        interval = max(1, interval)
        session = await self._get_session()
        async with session.get(f"{self.base_url}/photo/interval?val={interval}") as response:
            await self._check_device_response(response, "photo interval update")

    async def set_sdpro_theme_enabled(self, theme_id: int, enabled: bool) -> None:
        """Enable or disable a theme in the SD_PRO rotation."""
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/theme/toggle?id={theme_id}&state={1 if enabled else 0}"
        ) as response:
            await self._check_device_response(response, f"theme toggle {theme_id}")

    async def set_sdpro_theme_interval(self, interval: int) -> None:
        """Set SD_PRO theme rotation interval."""
        interval = max(0, interval)
        session = await self._get_session()
        async with session.get(f"{self.base_url}/theme/interval?val={interval}") as response:
            await self._check_device_response(response, "theme interval update")

    async def delete_sdpro_photo(self, name: str) -> None:
        """Delete a photo from the SD_PRO slideshow."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/photo/delete?name={quote(name)}") as response:
            await self._check_device_response(response, f"photo delete {name}")

    async def upload_sdpro_photo(self, image_data: bytes, filename: str) -> None:
        """Upload a photo to the SD_PRO slideshow."""
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
        else:
            content_type = "image/jpeg"

        form = aiohttp.FormData()
        form.add_field("file", image_data, filename=filename, content_type=content_type)
        session = await self._get_session()
        async with session.post(f"{self.base_url}/photo/upload", data=form) as response:
            response.raise_for_status()

    async def prepare_sdpro_exclusive_photo(self, filename: str) -> None:
        """Make one SD_PRO photo and the Photo theme active for visual testing."""
        photos = await self.get_sdpro_photo_settings()
        for photo in photos.files:
            await self.set_sdpro_photo_enabled(photo.name, photo.name == filename)

        themes = await self.get_sdpro_theme_settings()
        for theme in themes.themes:
            await self.set_sdpro_theme_enabled(theme.id, theme.id == self.custom_theme)

        await self.set_sdpro_photo_interval(1)
        await self.set_theme(self.custom_theme)

    async def set_theme_custom(self) -> None:
        """Set device to custom image mode with the correct theme number.

        Ultra devices use theme 3, Pro devices use theme 4.
        Uses the model detected at startup via detect_model().
        """
        await self.set_theme(self.custom_theme)

    async def set_image(self, filename: str, enter_picture: bool = False) -> None:
        """Set the displayed image.

        Args:
            filename: Image filename (without path)
            enter_picture: For Pro diagnostics, press buttons to enter Picture mode
        """
        if self.model == MODEL_SD_PRO:
            await self.prepare_sdpro_exclusive_photo(filename)
            self._last_image = f"/photo/{filename}"
            _LOGGER.debug("Set SD_PRO photo slideshow mode for %s", filename)
            return

        if self.model == MODEL_PRO:
            # This Pro firmware accepts uploads but returns body "FAIL" for
            # /set?img=... JPG selection. Its Picture mode is album-based.
            # Optional button navigation is kept for explicit live diagnostics,
            # but HA does not use it because the Pro menu state is not exposed.
            await self.set_album_display()
            await self.set_theme_custom()
            if enter_picture:
                await self.navigate_enter()
                await asyncio.sleep(0.5)
                await self.navigate_next()
                await asyncio.sleep(0.5)
                await self.navigate_enter()
            self._last_image = f"/image/{filename}"
            _LOGGER.debug("Set Pro album image mode for %s", filename)
            return

        # Ensure we're in custom image mode
        await self.set_theme_custom()
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?img=/image/{filename}") as response:
            await self._check_device_response(response, f"image selection for {filename}")
        self._last_image = f"/image/{filename}"
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

        if self.model == MODEL_SD_PRO:
            await self.upload_sdpro_photo(image_data, filename)
            _LOGGER.debug("Uploaded SD_PRO photo %s (%d bytes)", filename, len(image_data))
            return

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
        except aiohttp.ClientError as err:
            if self.model == MODEL_PRO:
                try:
                    if await self.pro_image_exists(filename):
                        _LOGGER.debug(
                            "Treating Pro upload connection error as success; %s is present: %s",
                            filename,
                            err,
                        )
                        return
                except Exception as verify_err:
                    _LOGGER.debug("Could not verify Pro upload after error: %s", verify_err)
            raise

        _LOGGER.debug("Uploaded %s (%d bytes)", filename, len(image_data))

    async def upload_and_display(
        self,
        image_data: bytes,
        filename: str,
        manage_album: bool = False,
        enter_picture: bool = False,
    ) -> None:
        """Upload an image and immediately display it.

        Args:
            image_data: Raw image bytes
            filename: Filename to save as
            manage_album: For Pro, delete all other album files after upload
            enter_picture: For Pro diagnostics, press buttons to enter Picture mode
        """
        _LOGGER.debug(
            "Uploading and displaying %s (%d bytes) to %s",
            filename,
            len(image_data),
            self.host,
        )
        await self.upload(image_data, filename)
        if self.model == MODEL_PRO and manage_album:
            await self.keep_only_pro_image(filename)
        await self.set_image(filename, enter_picture=enter_picture)
        _LOGGER.debug("Upload and display completed for %s", filename)

    async def backup_settings(self) -> DeviceSettingsBackup:
        """Take a best-effort snapshot of settings changed by smoke tests."""
        state: DeviceState | None = None
        brightness: int | None = None
        album: AlbumSettings | None = None
        sdpro_photos: SdProPhotoSettings | None = None
        sdpro_themes: SdProThemeSettings | None = None
        sdpro_active_theme: int | None = None

        try:
            state = await self.get_state()
            if self.model == MODEL_SD_PRO:
                sdpro_active_theme = state.theme
        except Exception as err:
            _LOGGER.debug("Could not back up device state: %s", err)

        try:
            brightness = await self.get_brightness()
        except Exception as err:
            _LOGGER.debug("Could not back up brightness: %s", err)

        if self.model == MODEL_PRO:
            try:
                album = await self.get_album_settings()
            except Exception as err:
                _LOGGER.debug("Could not back up album settings: %s", err)

        if self.model == MODEL_SD_PRO:
            try:
                sdpro_photos = await self.get_sdpro_photo_settings()
            except Exception as err:
                _LOGGER.debug("Could not back up SD_PRO photo settings: %s", err)
            try:
                sdpro_themes = await self.get_sdpro_theme_settings()
            except Exception as err:
                _LOGGER.debug("Could not back up SD_PRO theme settings: %s", err)

        return DeviceSettingsBackup(
            state=state,
            brightness=brightness,
            album=album,
            sdpro_photos=sdpro_photos,
            sdpro_themes=sdpro_themes,
            sdpro_active_theme=sdpro_active_theme,
        )

    async def restore_settings(self, backup: DeviceSettingsBackup) -> None:
        """Restore settings captured by backup_settings()."""
        if backup.brightness is not None:
            await self.set_brightness(backup.brightness)

        if self.model == MODEL_PRO and backup.pro_album_files is not None:
            await self.restore_pro_album_files(backup.pro_album_files)

        if self.model == MODEL_PRO and backup.album is not None:
            await self.set_album_display(
                interval=backup.album.interval,
                gif_loop=backup.album.gif_loop,
                autoplay=backup.album.autoplay,
            )

        if self.model == MODEL_SD_PRO:
            if backup.sdpro_photos is not None:
                for photo in backup.sdpro_photos.files:
                    await self.set_sdpro_photo_enabled(photo.name, photo.enabled)
                if backup.sdpro_photos.interval is not None:
                    await self.set_sdpro_photo_interval(backup.sdpro_photos.interval)

            if backup.sdpro_themes is not None:
                for theme in backup.sdpro_themes.themes:
                    await self.set_sdpro_theme_enabled(theme.id, theme.enabled)
                if backup.sdpro_themes.interval is not None:
                    await self.set_sdpro_theme_interval(backup.sdpro_themes.interval)

            if backup.sdpro_active_theme is not None:
                await self.set_theme(backup.sdpro_active_theme)
                return

        if backup.state is None or backup.state.theme is None:
            return

        if (
            self.model != MODEL_PRO
            and backup.state.current_image
            and self.is_custom_theme(backup.state.theme)
        ):
            await self.set_theme(backup.state.theme)
            await self._select_image_path(backup.state.current_image)
            return

        await self.set_theme(backup.state.theme)

    async def _select_image_path(self, image_path: str) -> None:
        """Select an uploaded image path on firmware that supports it."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?img={image_path}") as response:
            await self._check_device_response(response, f"image selection for {image_path}")
        self._last_image = image_path
        _LOGGER.debug("Set image path to %s", image_path)

    async def delete_file(self, path: str) -> None:
        """Delete a file from the device.

        Args:
            path: Full path to the file
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/delete?file={path}") as response:
            await self._check_device_response(response, f"delete {path}")
        _LOGGER.debug("Deleted %s", path)

    async def clear_images(self) -> None:
        """Clear all images from the device."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?clear=image") as response:
            await self._check_device_response(response, "clear images")
        _LOGGER.debug("Cleared all images")

    async def test_connection(self) -> ConnectionResult:  # noqa: PLR0911
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
            if e.status == 404 and self.model == MODEL_UNKNOWN:
                await self.detect_model()
                if self.model == MODEL_SD_PRO:
                    try:
                        await self.get_space()
                    except Exception as retry_err:
                        _LOGGER.warning(
                            "SD_PRO connection retry failed for %s: %s",
                            self.host,
                            retry_err,
                        )
                    else:
                        return ConnectionResult(success=True)
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
            await self._check_device_response(response, "navigate next")
        _LOGGER.debug("Navigated to next page")

    async def navigate_previous(self) -> None:
        """Navigate to previous page (Pro devices).

        Simulates pressing the left/previous button on the device.
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?page=-1") as response:
            await self._check_device_response(response, "navigate previous")
        _LOGGER.debug("Navigated to previous page")

    async def navigate_enter(self) -> None:
        """Press enter/exit button (Pro devices).

        Simulates pressing the enter/menu button on the device.
        """
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?enter=-1") as response:
            await self._check_device_response(response, "navigate enter")
        _LOGGER.debug("Pressed enter button")

    async def reboot(self) -> None:
        """Reboot the device (Pro devices)."""
        session = await self._get_session()
        async with session.get(f"{self.base_url}/set?reboot=1") as response:
            await self._check_device_response(response, "reboot")
        _LOGGER.debug("Rebooting device")

    async def detect_model(self) -> str:
        """Attempt to detect the device model.

        Newer stock firmware exposes identity through /v.json. Older firmware
        may only expose model-specific state paths.
        Returns MODEL_PRO, MODEL_ULTRA, or MODEL_UNKNOWN.
        """
        session = await self._get_session()

        # Current stock firmware exposes a reliable model/version endpoint.
        try:
            async with session.get(
                f"{self.base_url}/v.json", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    model_name = str(data.get("m", ""))
                    firmware_version = data.get("v")
                    self.model_name = model_name or None
                    self.firmware_version = (
                        str(firmware_version) if firmware_version is not None else None
                    )

                    model_key = model_name.lower()
                    if "pro" in model_key:
                        self.model = MODEL_PRO
                        _LOGGER.info(
                            "Detected device model: %s (%s)",
                            self.model_name,
                            self.firmware_version,
                        )
                        return self.model
                    if "ultra" in model_key:
                        self.model = MODEL_ULTRA
                        _LOGGER.info(
                            "Detected device model: %s (%s)",
                            self.model_name,
                            self.firmware_version,
                        )
                        return self.model
        except Exception as err:
            _LOGGER.debug("Identity path /v.json not available: %s", err)

        # Try Pro-specific path first (/.sys/app.json)
        try:
            async with session.get(
                f"{self.base_url}/.sys/app.json", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self.model = MODEL_PRO
                    self.model_name = "SmallTV Pro"
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
                    self.model_name = "SmallTV Ultra"
                    _LOGGER.info("Detected device model: SmallTV Ultra")
                    return self.model
        except Exception as err:
            _LOGGER.debug("Ultra path /app.json not available: %s", err)

        # SD_PRO community firmware exposes /theme/list and /photo/list instead.
        try:
            async with session.get(
                f"{self.base_url}/theme/list", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    if isinstance(data.get("themes"), list):
                        self.model = MODEL_SD_PRO
                        self.model_name = "SD_PRO Community Firmware"
                        _LOGGER.info("Detected device model: SD_PRO Community Firmware")
                        return self.model
        except Exception as err:
            _LOGGER.debug("SD_PRO path /theme/list not available: %s", err)

        _LOGGER.warning("Could not detect device model for %s", self.host)
        return MODEL_UNKNOWN
