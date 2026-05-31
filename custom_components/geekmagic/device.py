"""GeekMagic device facade."""

from __future__ import annotations

import logging

import aiohttp

from .const import MODEL_UNKNOWN
from .models import (
    AlbumSettings,
    ConnectionResult,
    DeviceFile,
    DeviceFileBackup,
    DeviceSettingsBackup,
    DeviceState,
    FirmwareCapabilities,
    RenderedDashboardRequest,
    SdProPhoto,
    SdProPhotoSettings,
    SdProTheme,
    SdProThemeSettings,
    SpaceInfo,
)
from .profiles import (
    PRO_BUILTIN_MODES,
    SD_PRO_BUILTIN_MODES,
    ULTRA_BUILTIN_MODES,
    FirmwareProfile,
    detect_firmware_profile,
    optional_int,
    profile_for_model,
    state_from_stock_data,
)
from .transport import TIMEOUT, DeviceTransport

_LOGGER = logging.getLogger(__name__)


class GeekMagicDevice:
    """Public facade for GeekMagic display devices.

    Firmware-specific behavior lives behind profile adapters; callers keep using
    this class as the stable Home Assistant and script interface.
    """

    PRO_BUILTIN_MODES = PRO_BUILTIN_MODES
    ULTRA_BUILTIN_MODES = ULTRA_BUILTIN_MODES
    SD_PRO_BUILTIN_MODES = SD_PRO_BUILTIN_MODES

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession | None = None,
        model: str = MODEL_UNKNOWN,
        *,
        source_address: str | None = None,
    ) -> None:
        """Initialize the device facade."""
        self.transport = DeviceTransport(host, session=session, source_address=source_address)
        self.profile: FirmwareProfile = profile_for_model(model, self.transport)

    @property
    def host(self) -> str:
        """Return normalized host."""
        return self.transport.host

    @property
    def base_url(self) -> str:
        """Return base URL."""
        return self.transport.base_url

    @property
    def _session(self) -> aiohttp.ClientSession | None:
        """Compatibility access to the transport session."""
        return self.transport.session

    @_session.setter
    def _session(self, value: aiohttp.ClientSession | None) -> None:
        self.transport.session = value

    @property
    def _owns_session(self) -> bool:
        """Compatibility access to session ownership."""
        return self.transport.owns_session

    @_owns_session.setter
    def _owns_session(self, value: bool) -> None:
        self.transport.owns_session = value

    @property
    def _last_theme(self) -> int | None:
        """Compatibility access to the profile's last known theme."""
        return self.profile.last_theme

    @_last_theme.setter
    def _last_theme(self, value: int | None) -> None:
        self.profile.last_theme = value

    @property
    def _last_image(self) -> str | None:
        """Compatibility access to the profile's last known image."""
        return self.profile.last_image

    @_last_image.setter
    def _last_image(self, value: str | None) -> None:
        self.profile.last_image = value

    @property
    def model(self) -> str:
        """Return detected firmware profile id."""
        return self.profile.capabilities.profile_id

    @model.setter
    def model(self, value: str) -> None:
        old = self.profile
        self.profile = profile_for_model(
            value,
            self.transport,
            model_name=old.model_name,
            firmware_version=old.firmware_version,
        )

    @property
    def profile_id(self) -> str:
        """Return detected firmware profile id."""
        return self.model

    @property
    def model_name(self) -> str | None:
        """Return detected model name."""
        return self.profile.model_name or self.profile.capabilities.display_name

    @model_name.setter
    def model_name(self, value: str | None) -> None:
        self.profile.model_name = value

    @property
    def firmware_version(self) -> str | None:
        """Return detected firmware version."""
        return self.profile.firmware_version

    @firmware_version.setter
    def firmware_version(self, value: str | None) -> None:
        self.profile.firmware_version = value

    @property
    def capabilities(self) -> FirmwareCapabilities:
        """Return firmware profile capabilities."""
        return self.profile.capabilities

    @property
    def custom_theme(self) -> int:
        """Return theme used for custom uploaded images."""
        return self.capabilities.custom_image_theme or 3

    @property
    def builtin_modes(self) -> dict[str, int]:
        """Return built-in display modes for the active firmware profile."""
        return self.capabilities.builtin_modes

    def is_custom_theme(self, theme: int | None) -> bool:
        """Return whether a device theme is the custom image mode."""
        return theme == self.capabilities.custom_image_theme

    def is_builtin_theme(self, theme: int | None) -> bool:
        """Return whether a device theme is handled by device firmware."""
        return theme is not None and not self.is_custom_theme(theme)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Compatibility helper for tests and older callers."""
        return await self.transport.get_session()

    async def _check_device_response(
        self,
        response: aiohttp.ClientResponse,
        action: str,
    ) -> None:
        """Compatibility helper for tests and older callers."""
        await self.transport.check_device_response(response, action)

    async def _get_json(self, path: str) -> dict[str, object]:
        """Compatibility helper for tests and older callers."""
        return await self.transport.get_json(path)

    async def _get_text(self, path: str) -> str:
        """Compatibility helper for tests and older callers."""
        return await self.transport.get_text(path)

    async def _get_bytes(self, path: str) -> bytes:
        """Compatibility helper for tests and older callers."""
        return await self.transport.get_bytes(path)

    @staticmethod
    def _optional_int(value: object) -> int | None:
        """Parse an optional integer value returned by device JSON."""
        return optional_int(value)

    @staticmethod
    def _state_from_data(data: dict[str, object]) -> DeviceState:
        """Build DeviceState from a stock firmware state payload."""
        return state_from_stock_data(data)

    async def close(self) -> None:
        """Close the session if this device owns it."""
        await self.transport.close()

    async def detect_model(self) -> str:
        """Detect and activate the firmware profile."""
        self.profile = await detect_firmware_profile(self.transport)
        _LOGGER.info(
            "Detected device profile: %s (%s)",
            self.model_name,
            self.firmware_version,
        )
        return self.model

    async def get_state(self) -> DeviceState:
        """Get current device state."""
        return await self.profile.get_state()

    async def get_space(self) -> SpaceInfo:
        """Get storage information."""
        return await self.profile.get_space()

    async def get_brightness(self) -> int:
        """Get current brightness."""
        return await self.profile.get_brightness()

    async def set_brightness(self, value: int) -> None:
        """Set brightness."""
        await self.profile.set_brightness(value)

    async def set_theme(self, theme: int) -> None:
        """Set firmware theme."""
        await self.profile.set_theme(theme)

    async def set_theme_custom(self) -> None:
        """Set the firmware's custom image theme."""
        await self.profile.set_theme_custom()

    async def get_album_settings(self) -> AlbumSettings:
        """Get photo album settings."""
        return await self.profile.get_album_settings()

    async def set_album_display(
        self,
        interval: int | None = 1,
        gif_loop: int | None = 1,
        autoplay: int | None = 1,
    ) -> None:
        """Set photo album display settings."""
        await self.profile.set_album_display(
            interval=interval,
            gif_loop=gif_loop,
            autoplay=autoplay,
        )

    async def get_pro_image_files(self) -> list[DeviceFile]:
        """List files in the stock firmware image album."""
        return await self.profile.get_image_files()

    async def backup_pro_album_files(self) -> list[DeviceFileBackup]:
        """Download the current stock firmware image album."""
        return await self.profile.backup_image_files()

    async def restore_pro_album_files(self, backups: list[DeviceFileBackup]) -> None:
        """Restore a previously backed-up stock firmware image album."""
        await self.profile.restore_image_files(backups)

    async def clear_pro_album_files(self) -> None:
        """Clear the stock firmware image album."""
        await self.profile.clear_album_files()

    async def pro_image_exists(self, filename: str) -> bool:
        """Return whether the stock firmware image album contains filename."""
        return await self.profile.image_exists(filename)

    async def keep_only_pro_image(self, filename: str) -> None:
        """Delete every Pro album file except filename."""
        await self.profile.keep_only_image(filename)

    async def get_sdpro_photo_settings(self) -> SdProPhotoSettings:
        """Read SD_PRO photo slideshow settings."""
        return await self.profile.get_sdpro_photo_settings()

    async def get_sdpro_theme_settings(self) -> SdProThemeSettings:
        """Read SD_PRO theme rotation settings."""
        return await self.profile.get_sdpro_theme_settings()

    async def set_sdpro_photo_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a photo in the SD_PRO slideshow."""
        await self.profile.set_sdpro_photo_enabled(name, enabled)

    async def set_sdpro_photo_interval(self, interval: int) -> None:
        """Set SD_PRO photo slideshow interval."""
        await self.profile.set_sdpro_photo_interval(interval)

    async def set_sdpro_theme_enabled(self, theme_id: int, enabled: bool) -> None:
        """Enable or disable a theme in the SD_PRO rotation."""
        await self.profile.set_sdpro_theme_enabled(theme_id, enabled)

    async def set_sdpro_theme_interval(self, interval: int) -> None:
        """Set SD_PRO theme rotation interval."""
        await self.profile.set_sdpro_theme_interval(interval)

    async def delete_sdpro_photo(self, name: str) -> None:
        """Delete a photo from the SD_PRO slideshow."""
        await self.profile.delete_sdpro_photo(name)

    async def upload_sdpro_photo(self, image_data: bytes, filename: str) -> None:
        """Upload a photo to the SD_PRO slideshow."""
        await self.profile.upload(image_data, filename)

    async def prepare_sdpro_exclusive_photo(self, filename: str) -> None:
        """Make one SD_PRO photo and the Photo theme active."""
        await self.profile.prepare_exclusive_photo(filename)

    async def set_image(self, filename: str, enter_picture: bool = False) -> None:
        """Set the displayed image."""
        await self.profile.set_image(filename, try_menu_navigation=enter_picture)

    async def upload(self, image_data: bytes, filename: str) -> None:
        """Upload an image to the device."""
        await self.profile.upload(image_data, filename)

    async def display_rendered_dashboard(self, request: RenderedDashboardRequest) -> None:
        """Upload and make a rendered dashboard visible."""
        await self.profile.display_rendered_dashboard(request)

    async def upload_and_display(
        self,
        image_data: bytes,
        filename: str,
        manage_album: bool = False,
        enter_picture: bool = False,
    ) -> None:
        """Upload an image and immediately display it."""
        await self.display_rendered_dashboard(
            RenderedDashboardRequest(
                image_data=image_data,
                filename=filename,
                allow_destructive_album_management=manage_album,
                try_menu_navigation=enter_picture,
            )
        )

    async def _select_image_path(self, image_path: str) -> None:
        """Select an uploaded image path on firmware that supports it."""
        await self.select_image_path(image_path)

    async def select_image_path(self, image_path: str) -> None:
        """Select an uploaded image path on firmware that supports it."""
        await self.profile.select_image_path(image_path)

    async def delete_file(self, path: str) -> None:
        """Delete a file from the device."""
        await self.profile.delete_file(path)

    async def clear_images(self) -> None:
        """Clear all images from the device."""
        await self.profile.clear_images()

    async def test_connection(self) -> ConnectionResult:  # noqa: PLR0911
        """Test if the device is reachable."""
        _LOGGER.debug("Testing connection to %s", self.host)
        try:
            await self.get_space()
        except TimeoutError:
            _LOGGER.warning("Connection test timed out for %s", self.host)
            return ConnectionResult(
                success=False,
                error="timeout",
                message="Connection timed out after 30 seconds",
            )
        except aiohttp.ClientConnectorDNSError as err:
            _LOGGER.warning("DNS resolution failed for %s: %s", self.host, err)
            return ConnectionResult(
                success=False,
                error="dns_error",
                message=f"Could not resolve hostname: {self.host}",
            )
        except aiohttp.ClientConnectorError as err:
            _LOGGER.warning("Connection failed for %s: %s", self.host, err)
            return ConnectionResult(
                success=False,
                error="connection_refused",
                message=str(err),
            )
        except aiohttp.ClientResponseError as err:
            if err.status == 404 and self.model == MODEL_UNKNOWN:
                await self.detect_model()
                try:
                    await self.get_space()
                except Exception as retry_err:
                    _LOGGER.warning(
                        "Connection retry failed for %s: %s",
                        self.host,
                        retry_err,
                    )
                else:
                    return ConnectionResult(success=True)
            _LOGGER.warning("HTTP error for %s: %s", self.host, err)
            return ConnectionResult(
                success=False,
                error="http_error",
                message=f"HTTP error {err.status}: {err.message}",
            )
        except Exception as err:
            _LOGGER.warning("Connection test failed for %s: %s", self.host, err)
            return ConnectionResult(
                success=False,
                error="unknown",
                message=str(err),
            )
        else:
            _LOGGER.debug("Connection test successful for %s", self.host)
            return ConnectionResult(success=True)

    async def navigate_next(self) -> None:
        """Navigate to next page."""
        await self.profile.navigate_next()

    async def navigate_previous(self) -> None:
        """Navigate to previous page."""
        await self.profile.navigate_previous()

    async def navigate_enter(self) -> None:
        """Press enter/exit button."""
        await self.profile.navigate_enter()

    async def reboot(self) -> None:
        """Reboot the device."""
        await self.profile.reboot()


__all__ = [
    "TIMEOUT",
    "AlbumSettings",
    "ConnectionResult",
    "DeviceFile",
    "DeviceFileBackup",
    "DeviceSettingsBackup",
    "DeviceState",
    "FirmwareCapabilities",
    "GeekMagicDevice",
    "RenderedDashboardRequest",
    "SdProPhoto",
    "SdProPhotoSettings",
    "SdProTheme",
    "SdProThemeSettings",
    "SpaceInfo",
]
