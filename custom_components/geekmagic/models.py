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


def brightness_to_percent(raw: int, brightness_range: tuple[int, int]) -> int:
    """Convert a raw firmware brightness value to a 0-100 percentage.

    Only firmware whose range goes past 100 (the Ultra's 0-255) is scaled.
    Ranges inside 0-100 already are percentages, some floored a little
    above 0 (2-99), and pass through unchanged so their readings and
    automations keep their meaning.
    """
    low, high = brightness_range
    if high <= 100:
        return max(0, min(100, raw))
    raw = max(low, min(high, raw))
    return round((raw - low) * 100 / (high - low))


def brightness_from_percent(percent: float, brightness_range: tuple[int, int]) -> int:
    """Convert a 0-100 percentage to the raw firmware brightness value."""
    low, high = brightness_range
    percent = max(0.0, min(100.0, percent))
    if high <= 100:
        return max(low, min(high, round(percent)))
    return round(low + percent * (high - low) / 100)


@dataclass(frozen=True)
class RenderedDashboardRequest:
    """Request to upload and make a rendered dashboard visible."""

    image_data: bytes
    filename: str
    allow_destructive_album_management: bool = False
    try_menu_navigation: bool = False
