"""Firmware profile adapters for GeekMagic devices."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import quote

import aiohttp

from .const import MODEL_PRO, MODEL_SD_PRO, MODEL_ULTRA, MODEL_UNKNOWN
from .models import (
    AlbumSettings,
    DeviceFile,
    DeviceFileBackup,
    DeviceState,
    FirmwareCapabilities,
    RenderedDashboardRequest,
    SdProPhoto,
    SdProPhotoSettings,
    SdProTheme,
    SdProThemeSettings,
    SpaceInfo,
)
from .transport import DeviceRejectedError, DeviceTransport

_LOGGER = logging.getLogger(__name__)

PRO_BUILTIN_MODES: dict[str, int] = {
    "Bitcoin": 0,
    "CoinGecko": 1,
    "Stocks": 2,
    "Weather": 3,
    "Monitor": 5,
    "Clock": 6,
    "Ideas": 7,
}

ULTRA_BUILTIN_MODES: dict[str, int] = {
    "Weather Clock Today": 1,
    "Weather Forecast": 2,
    "Time Style 1": 4,
    "Time Style 2": 5,
    "Time Style 3": 6,
    "Simple Weather Clock": 7,
}

SD_PRO_BUILTIN_MODES: dict[str, int] = {
    "Classic": 0,
    "Weather": 1,
    "Photo": 2,
    "Dial": 3,
    "Simple": 4,
    "Weather Forecast": 5,
    "Flip Clock": 6,
}

PRO_PICTURE_WARNING = (
    "SmallTV Pro Picture mode is a slideshow. Manually select the Picture app "
    "on the device; the integration will not press menu buttons automatically."
)


def optional_int(value: object) -> int | None:
    """Parse an optional integer value returned by device JSON."""
    if value is None:
        return None
    if isinstance(value, str) and value == "":
        return None
    try:
        return int(cast("Any", value))
    except (TypeError, ValueError):
        return None


def content_type_for_filename(filename: str) -> str:
    """Return a multipart content type for an uploaded file."""
    if filename.lower().endswith(".png"):
        return "image/png"
    if filename.lower().endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def state_from_stock_data(data: dict[str, object]) -> DeviceState:
    """Build DeviceState from a stock firmware state payload."""
    return DeviceState(
        theme=optional_int(data.get("theme")),
        brightness=optional_int(data.get("brt")),
        current_image=str(data["img"]) if data.get("img") else None,
    )


class FirmwareProfile:
    """Base adapter for a GeekMagic firmware profile."""

    profile_id = MODEL_UNKNOWN
    default_display_name = "SmallTV"
    default_builtin_modes: dict[str, int] = ULTRA_BUILTIN_MODES
    custom_image_theme: int | None = 3
    display_mechanism = "direct_image"
    brightness_range = (0, 100)
    user_warnings: tuple[str, ...] = ()
    supports_rendered_dashboard = False
    requires_managed_album = False
    supports_reboot = True

    def __init__(
        self,
        transport: DeviceTransport,
        *,
        profile_id: str | None = None,
        model_name: str | None = None,
        firmware_version: str | None = None,
    ) -> None:
        """Initialize the firmware profile adapter."""
        self.transport = transport
        self._profile_id = profile_id or self.profile_id
        self.model_name = model_name
        self.firmware_version = firmware_version
        self._last_theme: int | None = None
        self._last_image: str | None = None
        self._image_select_rejected = False

    @property
    def capabilities(self) -> FirmwareCapabilities:
        """Return firmware capabilities for runtime/UI callers."""
        return FirmwareCapabilities(
            profile_id=self._profile_id,
            display_name=self.model_name or self.default_display_name,
            firmware_version=self.firmware_version,
            supports_rendered_dashboard=self.supports_rendered_dashboard,
            builtin_modes=dict(self.default_builtin_modes),
            custom_image_theme=self.custom_image_theme,
            display_mechanism=self.display_mechanism,
            brightness_range=self.brightness_range,
            user_warnings=self.user_warnings,
            requires_managed_album=self.requires_managed_album,
            supports_reboot=self.supports_reboot,
        )

    @property
    def last_theme(self) -> int | None:
        """Return the last theme selected by this profile adapter."""
        return self._last_theme

    @last_theme.setter
    def last_theme(self, value: int | None) -> None:
        self._last_theme = value

    @property
    def last_image(self) -> str | None:
        """Return the last image selected by this profile adapter."""
        return self._last_image

    @last_image.setter
    def last_image(self, value: str | None) -> None:
        self._last_image = value

    @property
    def builtin_modes(self) -> dict[str, int]:
        """Return built-in display modes."""
        return self.capabilities.builtin_modes

    async def get_state(self) -> DeviceState:
        """Get current device state."""
        data = await self.transport.get_json("/app.json")
        state = state_from_stock_data(data)
        _LOGGER.debug(
            "Device state: theme=%s, brightness=%s, image=%s",
            state.theme,
            state.brightness,
            state.current_image,
        )
        return state

    async def get_space(self) -> SpaceInfo:
        """Get device storage information."""
        data = await self.transport.get_json("/space.json")
        space = SpaceInfo(
            total=optional_int(data.get("total")) or 0,
            free=optional_int(data.get("free")) or 0,
        )
        _LOGGER.debug(
            "Storage info: total=%d, free=%d (%.1f%% free)",
            space.total,
            space.free,
            (space.free / space.total * 100) if space.total > 0 else 0,
        )
        return space

    async def get_brightness(self) -> int:
        """Get current brightness from device."""
        data = await self.transport.get_json("/brt.json")
        brightness = optional_int(data.get("brt")) or 0
        _LOGGER.debug("Device brightness: %d", brightness)
        return brightness

    async def set_brightness(self, value: int) -> None:
        """Set display brightness."""
        low, high = self.brightness_range
        value = max(low, min(high, value))
        await self.transport.get_checked(f"/set?brt={value}", "brightness update")
        _LOGGER.debug("Set brightness to %d", value)

    async def set_theme(self, theme: int) -> None:
        """Set device theme."""
        await self.transport.get_checked(f"/set?theme={theme}", "theme update")
        self._last_theme = theme
        _LOGGER.debug("Set theme to %d", theme)

    async def set_theme_custom(self) -> None:
        """Set device to custom image mode."""
        if self.custom_image_theme is None:
            raise RuntimeError("Firmware profile has no custom image theme")
        await self.set_theme(self.custom_image_theme)

    async def get_album_settings(self) -> AlbumSettings:
        """Get photo album settings when exposed by stock firmware."""
        data = await self.transport.get_json("/album.json")
        return AlbumSettings(
            interval=optional_int(data.get("i_i")),
            gif_loop=optional_int(data.get("gif_loop")),
            autoplay=optional_int(data.get("autoplay")),
        )

    async def set_album_display(
        self,
        interval: int | None = 1,
        gif_loop: int | None = 1,
        autoplay: int | None = 0,
    ) -> None:
        """Enable album display behavior used for uploaded images.

        autoplay defaults to 0 because the integration manages the album
        exclusively (one dashboard image); autoplay=1 would re-enable the
        device's photo slideshow on every refresh (issue #158).
        """
        query_parts: list[str] = []
        if interval is not None:
            query_parts.append(f"i_i={max(1, interval)}")
        if gif_loop is not None:
            query_parts.append(f"gif_loop={max(1, gif_loop)}")
        if autoplay is not None:
            query_parts.append(f"autoplay={1 if autoplay else 0}")
        if not query_parts:
            return

        await self.transport.get_checked(
            f"/set?{'&'.join(query_parts)}",
            "album display update",
        )
        _LOGGER.debug(
            "Updated album display interval=%s gif_loop=%s autoplay=%s",
            interval,
            gif_loop,
            autoplay,
        )

    async def get_image_files(self) -> list[DeviceFile]:
        """List files in the stock firmware image album."""
        html = await self.transport.get_text("/filelist?dir=/image/")
        pattern = re.compile(
            r"<a href='(?P<path>[^']+)'>(?P<name>[^<]+)</a></td><td>(?P<size>[^<]+)</td>"
        )
        return [
            DeviceFile(
                name=match.group("name"),
                path=match.group("path"),
                size_kb=optional_int(match.group("size")),
            )
            for match in pattern.finditer(html)
        ]

    async def backup_image_files(self) -> list[DeviceFileBackup]:
        """Download the current stock firmware image album for later restore."""
        return [
            DeviceFileBackup(file=file, data=await self.transport.get_bytes(file.path))
            for file in await self.get_image_files()
        ]

    async def restore_image_files(self, backups: list[DeviceFileBackup]) -> None:
        """Restore a previously backed-up stock firmware image album."""
        await self.clear_images()
        for backup in backups:
            await self.upload(backup.data, backup.file.name)

    async def clear_album_files(self) -> None:
        """Clear stock firmware images, including files clear=image leaves behind."""
        await self.clear_images()
        for file in await self.get_image_files():
            await self.delete_file(file.path)

    async def image_exists(self, filename: str) -> bool:
        """Return whether the stock firmware image album contains filename."""
        return any(file.name == filename for file in await self.get_image_files())

    async def keep_only_image(self, filename: str) -> None:
        """Delete every album file except filename."""
        kept = False
        for file in await self.get_image_files():
            if file.name == filename:
                kept = True
                continue
            await self.delete_file(file.path)

        if not kept:
            raise RuntimeError(f"Uploaded image {filename} was not found in the album")

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to stock firmware storage."""
        await self._stock_upload(image_data, filename)

    async def _stock_upload(self, image_data: bytes, filename: str) -> None:
        """Upload through the stock /doUpload endpoint."""
        try:
            await self.transport.post_file(
                "/doUpload?dir=/image/",
                "file",
                image_data,
                filename,
                content_type_for_filename(filename),
            )
        except aiohttp.ClientResponseError as err:
            if self.transport.is_malformed_firmware_response(err):
                _LOGGER.debug("Ignoring malformed HTTP response from device: %s", err.message)
                return
            raise

        _LOGGER.debug("Uploaded %s (%d bytes)", filename, len(image_data))

    async def set_image(self, filename: str, try_menu_navigation: bool = False) -> None:
        """Set the displayed image."""
        await self.set_theme_custom()
        await self.select_image_path(f"/image/{filename}")
        _LOGGER.debug("Set image to %s", filename)

    async def select_image_path(self, image_path: str) -> None:
        """Select an uploaded image path on firmware that supports it."""
        try:
            await self.transport.get_checked(
                f"/set?img={image_path}",
                f"image selection for {image_path}",
            )
        except DeviceRejectedError as err:
            # Some firmwares (e.g. SmallTV-PRO V3.4.82EN) answer FAIL to
            # /set?img= even in custom image mode, where uploading to the
            # same filename already refreshes the display. Keep the update
            # loop alive instead of failing setup (issue #155).
            _LOGGER.log(
                logging.DEBUG if self._image_select_rejected else logging.WARNING,
                "%s; continuing because the upload already replaced the displayed image",
                err,
            )
            self._image_select_rejected = True
        self._last_image = image_path
        _LOGGER.debug("Set image path to %s", image_path)

    async def display_rendered_dashboard(self, request: RenderedDashboardRequest) -> None:
        """Upload and display a rendered dashboard."""
        await self.upload(request.image_data, request.filename)
        await self.set_image(request.filename, try_menu_navigation=request.try_menu_navigation)
        _LOGGER.debug("Upload and display completed for %s", request.filename)

    async def delete_file(self, path: str) -> None:
        """Delete a file from the device."""
        await self.transport.get_checked(f"/delete?file={path}", f"delete {path}")
        _LOGGER.debug("Deleted %s", path)

    async def clear_images(self) -> None:
        """Clear all images from the device."""
        await self.transport.get_checked("/set?clear=image", "clear images")
        _LOGGER.debug("Cleared all images")

    async def navigate_next(self) -> None:
        """Navigate to next page."""
        await self.transport.get_checked("/set?page=1", "navigate next")
        _LOGGER.debug("Navigated to next page")

    async def navigate_previous(self) -> None:
        """Navigate to previous page."""
        await self.transport.get_checked("/set?page=-1", "navigate previous")
        _LOGGER.debug("Navigated to previous page")

    async def navigate_enter(self) -> None:
        """Press enter/exit button."""
        await self.transport.get_checked("/set?enter=-1", "navigate enter")
        _LOGGER.debug("Pressed enter button")

    async def reboot(self) -> None:
        """Reboot the device."""
        await self.transport.get_checked("/set?reboot=1", "reboot")
        _LOGGER.debug("Rebooting device")

    async def get_sdpro_photo_settings(self) -> SdProPhotoSettings:
        """Read SD_PRO photo slideshow settings."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO photo settings")

    async def get_sdpro_theme_settings(self) -> SdProThemeSettings:
        """Read SD_PRO theme rotation settings."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO theme settings")

    async def set_sdpro_photo_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a SD_PRO photo."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO photo settings")

    async def set_sdpro_photo_interval(self, interval: int) -> None:
        """Set SD_PRO photo interval."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO photo settings")

    async def set_sdpro_theme_enabled(self, theme_id: int, enabled: bool) -> None:
        """Enable or disable a SD_PRO theme."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO theme settings")

    async def set_sdpro_theme_interval(self, interval: int) -> None:
        """Set SD_PRO theme interval."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO theme settings")

    async def delete_sdpro_photo(self, name: str) -> None:
        """Delete a SD_PRO photo."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO photo settings")

    async def prepare_exclusive_photo(self, filename: str) -> None:
        """Make one photo active on firmware that exposes slideshow settings."""
        raise NotImplementedError("Firmware profile does not expose SD_PRO photo settings")


class UnknownStockProfile(FirmwareProfile):
    """Ultra-compatible fallback used before detection."""

    profile_id = MODEL_UNKNOWN
    default_display_name = "SmallTV"
    supports_rendered_dashboard = False


class StockUltraProfile(FirmwareProfile):
    """Adapter for stock SmallTV Ultra firmware."""

    profile_id = MODEL_ULTRA
    default_display_name = "SmallTV Ultra"
    default_builtin_modes = ULTRA_BUILTIN_MODES
    custom_image_theme = 3
    display_mechanism = "direct_image"
    supports_rendered_dashboard = True


class StockProProfile(FirmwareProfile):
    """Adapter for stock SmallTV-PRO firmware."""

    profile_id = MODEL_PRO
    default_display_name = "SmallTV Pro"
    default_builtin_modes = PRO_BUILTIN_MODES
    custom_image_theme = 4
    display_mechanism = "picture_album"
    supports_rendered_dashboard = True
    requires_managed_album = True
    user_warnings = (PRO_PICTURE_WARNING,)

    async def get_state(self) -> DeviceState:
        """Get current Pro state, tolerating missing app state paths."""
        last_404: aiohttp.ClientResponseError | None = None
        for path in ("/.sys/app.json", "/app.json"):
            try:
                data = await self.transport.get_json(path)
            except aiohttp.ClientResponseError as err:
                if err.status == 404:
                    last_404 = err
                    continue
                raise
            else:
                state = state_from_stock_data(data)
                _LOGGER.debug(
                    "Device state: theme=%s, brightness=%s, image=%s",
                    state.theme,
                    state.brightness,
                    state.current_image,
                )
                return state

        if last_404 is not None:
            _LOGGER.debug("Pro firmware has no state path; using last known state")
            return DeviceState(
                theme=self._last_theme,
                brightness=None,
                current_image=self._last_image,
                is_live=False,
            )

        raise RuntimeError("Device state was not read")

    async def get_brightness(self) -> int:
        """Get Pro brightness from /.sys."""
        data = await self.transport.get_json("/.sys/brt.json")
        brightness = optional_int(data.get("brt")) or 0
        _LOGGER.debug("Device brightness: %d", brightness)
        return brightness

    async def get_album_settings(self) -> AlbumSettings:
        """Get Pro photo album settings."""
        data = await self.transport.get_json("/.sys/album.json")
        return AlbumSettings(
            interval=optional_int(data.get("i_i")),
            gif_loop=optional_int(data.get("gif_loop")),
            autoplay=optional_int(data.get("autoplay")),
        )

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload to Pro, tolerating connection errors after a successful write."""
        try:
            await self._stock_upload(image_data, filename)
        except aiohttp.ClientError as err:
            try:
                if await self.image_exists(filename):
                    _LOGGER.debug(
                        "Treating Pro upload connection error as success; %s is present: %s",
                        filename,
                        err,
                    )
                    return
            except Exception as verify_err:
                _LOGGER.debug("Could not verify Pro upload after error: %s", verify_err)
            raise

    async def set_image(self, filename: str, try_menu_navigation: bool = False) -> None:
        """Prepare Pro Picture album mode for the uploaded image."""
        await self.set_album_display(autoplay=0)
        await self.set_theme_custom()
        if try_menu_navigation:
            await self.navigate_enter()
            await asyncio.sleep(0.5)
            await self.navigate_next()
            await asyncio.sleep(0.5)
            await self.navigate_enter()
        self._last_image = f"/image/{filename}"
        _LOGGER.debug("Set Pro album image mode for %s", filename)

    async def display_rendered_dashboard(self, request: RenderedDashboardRequest) -> None:
        """Upload and display a Pro rendered dashboard."""
        await self.upload(request.image_data, request.filename)
        if request.allow_destructive_album_management:
            await self.keep_only_image(request.filename)
        await self.set_image(request.filename, try_menu_navigation=request.try_menu_navigation)
        _LOGGER.debug("Upload and display completed for %s", request.filename)


class SdProProfile(FirmwareProfile):
    """Adapter for SD_PRO community-style firmware."""

    profile_id = MODEL_SD_PRO
    default_display_name = "SD_PRO Community Firmware"
    default_builtin_modes = SD_PRO_BUILTIN_MODES
    custom_image_theme = 2
    display_mechanism = "photo_slideshow"
    brightness_range = (2, 99)
    supports_rendered_dashboard = True
    supports_reboot = False
    user_warnings = ("This firmware displays rendered dashboards through the Photo slideshow.",)

    async def get_state(self) -> DeviceState:
        """Get current SD_PRO state from /config."""
        data = await self.transport.get_json("/config")
        return DeviceState(
            theme=optional_int(data.get("theme")),
            brightness=optional_int(data.get("brightness")),
            current_image=None,
        )

    async def get_space(self) -> SpaceInfo:
        """Get SD_PRO photo storage information."""
        photos = await self.get_sdpro_photo_settings()
        return SpaceInfo(total=photos.total, free=max(0, photos.total - photos.used))

    async def get_brightness(self) -> int:
        """Get SD_PRO brightness from /config."""
        data = await self.transport.get_json("/config")
        brightness = optional_int(data.get("brightness"))
        return brightness or 0

    async def set_brightness(self, value: int) -> None:
        """Set SD_PRO brightness."""
        low, high = self.brightness_range
        value = max(low, min(high, value))
        await self.transport.get_checked(
            f"/api/set?key=lcd_brightness&value={value}",
            "brightness update",
        )
        _LOGGER.debug("Set SD_PRO brightness to %d", value)

    async def reboot(self) -> None:
        """Reboot is not available on SD_PRO firmware."""
        raise NotImplementedError("SD_PRO firmware does not expose a reboot endpoint")

    async def set_theme(self, theme: int) -> None:
        """Set SD_PRO active theme."""
        await self.transport.get_checked(
            f"/api/set?key=theme&value={theme}",
            "theme update",
        )
        self._last_theme = theme
        _LOGGER.debug("Set SD_PRO theme to %d", theme)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload a photo to the SD_PRO slideshow."""
        await self.transport.post_file(
            "/photo/upload",
            "file",
            image_data,
            filename,
            content_type_for_filename(filename),
        )
        _LOGGER.debug("Uploaded SD_PRO photo %s (%d bytes)", filename, len(image_data))

    async def set_image(self, filename: str, try_menu_navigation: bool = False) -> None:
        """Make one SD_PRO photo and the Photo theme active."""
        await self.prepare_exclusive_photo(filename)
        self._last_image = f"/photo/{filename}"
        _LOGGER.debug("Set SD_PRO photo slideshow mode for %s", filename)

    async def prepare_exclusive_photo(self, filename: str) -> None:
        """Make one SD_PRO photo and the Photo theme active for visual testing."""
        photos = await self.get_sdpro_photo_settings()
        for photo in photos.files:
            await self.set_sdpro_photo_enabled(photo.name, photo.name == filename)

        themes = await self.get_sdpro_theme_settings()
        for theme in themes.themes:
            await self.set_sdpro_theme_enabled(theme.id, theme.id == self.custom_image_theme)

        await self.set_sdpro_photo_interval(1)
        await self.set_theme(self.custom_image_theme or 2)

    async def get_sdpro_photo_settings(self) -> SdProPhotoSettings:
        """Read SD_PRO photo slideshow settings."""
        data = await self.transport.get_json("/photo/list")
        files_data = data.get("files", [])
        files: list[SdProPhoto] = []
        if isinstance(files_data, list):
            for item in files_data:
                if isinstance(item, Mapping):
                    item_data = cast("Mapping[str, object]", item)
                    name = item_data.get("name")
                    if name is not None:
                        files.append(
                            SdProPhoto(
                                name=str(name),
                                size=optional_int(item_data.get("size")) or 0,
                                enabled=bool(item_data.get("enabled")),
                            )
                        )
        return SdProPhotoSettings(
            files=files,
            total=optional_int(data.get("total")) or 0,
            used=optional_int(data.get("used")) or 0,
            interval=optional_int(data.get("interval")),
        )

    async def get_sdpro_theme_settings(self) -> SdProThemeSettings:
        """Read SD_PRO theme rotation settings."""
        data = await self.transport.get_json("/theme/list")
        themes_data = data.get("themes", [])
        themes: list[SdProTheme] = []
        if isinstance(themes_data, list):
            for item in themes_data:
                if isinstance(item, Mapping):
                    item_data = cast("Mapping[str, object]", item)
                    theme_id = optional_int(item_data.get("id"))
                    if theme_id is not None:
                        themes.append(
                            SdProTheme(
                                id=theme_id,
                                name=str(item_data.get("name", theme_id)),
                                enabled=bool(item_data.get("enabled")),
                            )
                        )
        return SdProThemeSettings(
            themes=themes,
            interval=optional_int(data.get("interval")),
        )

    async def set_sdpro_photo_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a photo in the SD_PRO slideshow."""
        await self.transport.get_checked(
            f"/photo/toggle?name={quote(name)}&state={1 if enabled else 0}",
            f"photo toggle {name}",
        )

    async def set_sdpro_photo_interval(self, interval: int) -> None:
        """Set SD_PRO photo slideshow interval."""
        await self.transport.get_checked(
            f"/photo/interval?val={max(1, interval)}",
            "photo interval update",
        )

    async def set_sdpro_theme_enabled(self, theme_id: int, enabled: bool) -> None:
        """Enable or disable a theme in the SD_PRO rotation."""
        await self.transport.get_checked(
            f"/theme/toggle?id={theme_id}&state={1 if enabled else 0}",
            f"theme toggle {theme_id}",
        )

    async def set_sdpro_theme_interval(self, interval: int) -> None:
        """Set SD_PRO theme rotation interval."""
        await self.transport.get_checked(
            f"/theme/interval?val={max(0, interval)}",
            "theme interval update",
        )

    async def delete_sdpro_photo(self, name: str) -> None:
        """Delete a photo from the SD_PRO slideshow."""
        await self.transport.get_checked(
            f"/photo/delete?name={quote(name)}",
            f"photo delete {name}",
        )


def profile_for_model(
    model: str,
    transport: DeviceTransport,
    *,
    model_name: str | None = None,
    firmware_version: str | None = None,
) -> FirmwareProfile:
    """Create a profile adapter for a model/profile id."""
    if model == MODEL_PRO:
        return StockProProfile(
            transport,
            model_name=model_name,
            firmware_version=firmware_version,
        )
    if model == MODEL_SD_PRO:
        return SdProProfile(
            transport,
            model_name=model_name,
            firmware_version=firmware_version,
        )
    if model == MODEL_ULTRA:
        return StockUltraProfile(
            transport,
            model_name=model_name,
            firmware_version=firmware_version,
        )
    return UnknownStockProfile(
        transport,
        profile_id=MODEL_UNKNOWN,
        model_name=model_name,
        firmware_version=firmware_version,
    )


async def detect_firmware_profile(transport: DeviceTransport) -> FirmwareProfile:
    """Detect the firmware profile exposed by a device."""
    timeout = aiohttp.ClientTimeout(total=5)

    try:
        data = await transport.get_json("/v.json", request_timeout=timeout)
        model_name = str(data.get("m", ""))
        firmware_value = data.get("v")
        firmware_version = str(firmware_value) if firmware_value is not None else None
        model_key = model_name.lower()
        if "pro" in model_key:
            return StockProProfile(
                transport,
                model_name=model_name or None,
                firmware_version=firmware_version,
            )
        if "ultra" in model_key:
            return StockUltraProfile(
                transport,
                model_name=model_name or None,
                firmware_version=firmware_version,
            )
    except Exception as err:
        _LOGGER.debug("Identity path /v.json not available: %s", err)

    try:
        await transport.get_json("/.sys/app.json", request_timeout=timeout)
        return StockProProfile(transport, model_name="SmallTV Pro")
    except Exception as err:
        _LOGGER.debug("Pro path /.sys/app.json not available: %s", err)

    try:
        await transport.get_json("/app.json", request_timeout=timeout)
        return StockUltraProfile(transport, model_name="SmallTV Ultra")
    except Exception as err:
        _LOGGER.debug("Ultra path /app.json not available: %s", err)

    try:
        data = await transport.get_json("/theme/list", request_timeout=timeout)
        if isinstance(data.get("themes"), list):
            return SdProProfile(transport, model_name="SD_PRO Community Firmware")
    except Exception as err:
        _LOGGER.debug("SD_PRO path /theme/list not available: %s", err)

    _LOGGER.warning("Could not detect device model for %s", transport.host)
    return UnknownStockProfile(transport)
