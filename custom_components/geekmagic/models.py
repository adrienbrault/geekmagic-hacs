"""Shared models for GeekMagic devices and firmware profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


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
    # False when the state was synthesized from the integration's own last
    # commands (e.g. Pro firmware without a readable app.json) rather than
    # read back from the device.
    is_live: bool = True


@dataclass
class AlbumSettings:
    """Represents stock firmware photo album settings."""

    interval: int | None
    gif_loop: int | None
    autoplay: int | None


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


@dataclass(frozen=True)
class FirmwareCapabilities:
    """Capabilities exposed by a detected firmware profile."""

    profile_id: str
    display_name: str
    firmware_version: str | None = None
    supports_rendered_dashboard: bool = True
    builtin_modes: dict[str, int] = field(default_factory=dict)
    custom_image_theme: int | None = None
    display_mechanism: str = "direct_image"
    brightness_range: tuple[int, int] = (0, 100)
    user_warnings: tuple[str, ...] = ()
    requires_managed_album: bool = False
    supports_reboot: bool = True


@dataclass(frozen=True)
class RenderedDashboardRequest:
    """Request to upload and make a rendered dashboard visible."""

    image_data: bytes
    filename: str
    allow_destructive_album_management: bool = False
    try_menu_navigation: bool = False
