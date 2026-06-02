"""Driver for stock GeekMagic firmware (SmallTV Pro and Ultra families).

The Pro and Ultra share the same `/set?...` write surface and the same
upload endpoint; they only differ in:

- the path that returns current brightness (`/.sys/brt.json` vs `/brt.json`)
- the theme number used for custom-image display (4=Picture vs 3=Photo Album)
- whether `/app.json` is exposed (Ultra: yes, returns only `{theme}`; Pro: 404)
- whether navigation endpoints (`/set?page=`, `/set?enter=`) are honoured

These are captured in `StockProfile` so a single class handles both.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

from ..const import (
    MODEL_PRO,
    MODEL_ULTRA,
    THEME_CUSTOM_IMAGE_PRO,
    THEME_CUSTOM_IMAGE_ULTRA,
)
from .base import DeviceDriver, DeviceState, SpaceInfo

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StockProfile:
    """Per-firmware configuration for `StockDriver`."""

    model: str
    brightness_path: str
    custom_image_theme: int
    has_app_json: bool
    supports_navigation: bool


STOCK_PRO_PROFILE = StockProfile(
    model=MODEL_PRO,
    brightness_path="/.sys/brt.json",
    custom_image_theme=THEME_CUSTOM_IMAGE_PRO,
    has_app_json=False,
    supports_navigation=True,
)

STOCK_ULTRA_PROFILE = StockProfile(
    model=MODEL_ULTRA,
    brightness_path="/brt.json",
    custom_image_theme=THEME_CUSTOM_IMAGE_ULTRA,
    has_app_json=True,
    supports_navigation=False,
)


class StockDriver(DeviceDriver):
    """HTTP driver for stock GeekMagic firmwares (Pro + Ultra)."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        profile: StockProfile,
        sw_version: str | None = None,
    ) -> None:
        super().__init__(base_url, session)
        self._profile = profile
        self.model = profile.model
        self.custom_image_theme = profile.custom_image_theme
        self.supports_navigation = profile.supports_navigation
        self.sw_version = sw_version
        # Cache last theme written by the integration; used as a fallback when
        # the firmware doesn't expose /app.json (Pro).
        self._last_known_theme: int = profile.custom_image_theme

    async def get_state(self) -> DeviceState:
        if not self._profile.has_app_json:
            # Pro firmware: no /app.json — return our best guess.
            return DeviceState(theme=self._last_known_theme, brightness=None, current_image=None)
        async with self._session.get(f"{self.base_url}/app.json") as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
            theme = data.get("theme", 0)
            self._last_known_theme = theme
            return DeviceState(
                theme=theme,
                brightness=data.get("brt"),
                current_image=data.get("img"),
            )

    async def get_space(self) -> SpaceInfo:
        async with self._session.get(f"{self.base_url}/space.json") as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
            return SpaceInfo(total=data.get("total", 0), free=data.get("free", 0))

    async def get_brightness(self) -> int:
        async with self._session.get(f"{self.base_url}{self._profile.brightness_path}") as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
            # Firmware returns brightness as a string: {"brt": "71"}
            return int(data.get("brt", 0))

    async def set_brightness(self, value: int) -> None:
        value = self.clamp_brightness(value)
        async with self._session.get(f"{self.base_url}/set?brt={value}") as r:
            r.raise_for_status()

    async def set_theme(self, theme: int) -> None:
        async with self._session.get(f"{self.base_url}/set?theme={theme}") as r:
            r.raise_for_status()
        self._last_known_theme = theme

    async def set_image(self, filename: str) -> None:
        await self.set_theme_custom()
        async with self._session.get(f"{self.base_url}/set?img=/image/{filename}") as r:
            r.raise_for_status()

    async def upload(self, image_data: bytes, filename: str) -> None:
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
        else:
            content_type = "image/jpeg"

        form = aiohttp.FormData()
        form.add_field("file", image_data, filename=filename, content_type=content_type)

        try:
            async with self._session.post(f"{self.base_url}/doUpload?dir=/image/", data=form) as r:
                r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            # Stock firmware returns malformed HTTP responses after a successful
            # upload — swallow the known signatures.
            # Ultra: "Duplicate Content-Length header"
            # Pro:   "Data after `Connection: close`"
            if e.status == 400:
                msg = str(e.message) if e.message else ""
                if "Duplicate Content-Length" in msg or "Data after" in msg:
                    _LOGGER.debug("Ignoring malformed HTTP response from device: %s", msg)
                    return
            raise

    async def delete_file(self, path: str) -> None:
        async with self._session.get(f"{self.base_url}/delete?file={path}") as r:
            r.raise_for_status()

    async def clear_images(self) -> None:
        async with self._session.get(f"{self.base_url}/set?clear=image") as r:
            r.raise_for_status()

    async def reboot(self) -> None:
        async with self._session.get(f"{self.base_url}/set?reboot=1") as r:
            r.raise_for_status()

    async def navigate_next(self) -> None:
        if not self._profile.supports_navigation:
            await super().navigate_next()
            return
        async with self._session.get(f"{self.base_url}/set?page=1") as r:
            r.raise_for_status()

    async def navigate_previous(self) -> None:
        if not self._profile.supports_navigation:
            await super().navigate_previous()
            return
        async with self._session.get(f"{self.base_url}/set?page=-1") as r:
            r.raise_for_status()

    async def navigate_enter(self) -> None:
        if not self._profile.supports_navigation:
            await super().navigate_enter()
            return
        async with self._session.get(f"{self.base_url}/set?enter=-1") as r:
            r.raise_for_status()
