"""Live-device mutation backup and restore helpers."""

from __future__ import annotations

import logging

from .const import MODEL_PRO, MODEL_SD_PRO
from .device import GeekMagicDevice
from .models import DeviceSettingsBackup, DeviceState

_LOGGER = logging.getLogger(__name__)


async def backup_settings(device: GeekMagicDevice) -> DeviceSettingsBackup:
    """Take a best-effort snapshot of settings changed by live smoke tests."""
    state: DeviceState | None = None
    brightness: int | None = None
    album = None
    sdpro_photos = None
    sdpro_themes = None
    sdpro_active_theme: int | None = None

    try:
        state = await device.get_state()
        if device.profile_id == MODEL_SD_PRO:
            sdpro_active_theme = state.theme
    except Exception as err:
        _LOGGER.debug("Could not back up device state: %s", err)

    try:
        brightness = await device.get_brightness()
    except Exception as err:
        _LOGGER.debug("Could not back up brightness: %s", err)

    if device.profile_id == MODEL_PRO:
        try:
            album = await device.get_album_settings()
        except Exception as err:
            _LOGGER.debug("Could not back up album settings: %s", err)

    if device.profile_id == MODEL_SD_PRO:
        try:
            sdpro_photos = await device.get_sdpro_photo_settings()
        except Exception as err:
            _LOGGER.debug("Could not back up SD_PRO photo settings: %s", err)
        try:
            sdpro_themes = await device.get_sdpro_theme_settings()
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


async def restore_settings(device: GeekMagicDevice, backup: DeviceSettingsBackup) -> None:
    """Restore settings captured before a live smoke test."""
    if backup.brightness is not None:
        await device.set_brightness(backup.brightness)

    if device.profile_id == MODEL_PRO and backup.pro_album_files is not None:
        await device.restore_pro_album_files(backup.pro_album_files)

    if device.profile_id == MODEL_PRO and backup.album is not None:
        await device.set_album_display(
            interval=backup.album.interval,
            gif_loop=backup.album.gif_loop,
            autoplay=backup.album.autoplay,
        )

    if device.profile_id == MODEL_SD_PRO:
        if backup.sdpro_photos is not None:
            for photo in backup.sdpro_photos.files:
                await device.set_sdpro_photo_enabled(photo.name, photo.enabled)
            if backup.sdpro_photos.interval is not None:
                await device.set_sdpro_photo_interval(backup.sdpro_photos.interval)

        if backup.sdpro_themes is not None:
            for theme in backup.sdpro_themes.themes:
                await device.set_sdpro_theme_enabled(theme.id, theme.enabled)
            if backup.sdpro_themes.interval is not None:
                await device.set_sdpro_theme_interval(backup.sdpro_themes.interval)

        if backup.sdpro_active_theme is not None:
            await device.set_theme(backup.sdpro_active_theme)
            return

    if backup.state is None or backup.state.theme is None:
        return

    if (
        device.profile_id != MODEL_PRO
        and backup.state.current_image
        and device.is_custom_theme(backup.state.theme)
    ):
        await device.set_theme(backup.state.theme)
        await device.select_image_path(backup.state.current_image)
        return

    await device.set_theme(backup.state.theme)


async def backup_and_clear_album(
    device: GeekMagicDevice,
    backup: DeviceSettingsBackup,
) -> int | None:
    """Back up and clear images for firmware profiles that support it."""
    if device.profile_id == MODEL_PRO:
        backup.pro_album_files = await device.backup_pro_album_files()
        await device.clear_pro_album_files()
        return len(backup.pro_album_files)

    if device.profile_id == MODEL_SD_PRO:
        return None

    try:
        await device.clear_images()
    except NotImplementedError as err:
        # Profiles with fixed photo slots (legacy Weather Clock) have no
        # bulk clear; the test upload simply overwrites the managed slot.
        _LOGGER.debug("Skipping album clear: %s", err)
        return None
    return 0


async def cleanup_uploaded_sdpro_photo(
    device: GeekMagicDevice,
    backup: DeviceSettingsBackup,
    filename: str,
) -> bool:
    """Remove an uploaded SD_PRO test photo when it was not present before."""
    if device.profile_id != MODEL_SD_PRO:
        return False

    names = (
        {photo.name for photo in backup.sdpro_photos.files}
        if backup.sdpro_photos is not None
        else set()
    )
    if filename in names:
        return False

    await device.delete_sdpro_photo(filename)
    return True
