"""Driver for the SD_PRO community firmware.

The SD_PRO firmware (https://github.com/JUZIPi-tech/SD_PRO) exposes a
completely different HTTP surface from stock GeekMagic firmware:

  - all settings live in `GET /config`
  - writes go through `GET /api/set?key=&value=`
  - photos are uploaded to `POST /photo/upload` (multipart field `file`)
  - photos can be enabled/disabled in the slideshow individually
  - there is *no* "display this image now" endpoint

To approximate the integration's "render and display" pipeline we upload
the rendered image as `dashboard.jpg`, disable every other photo in the
slideshow, and switch the device to the Photo theme (id=2). Re-uploading
the same filename overwrites the previous frame.

Caveats (see docs/devices/new-ultra-sdpro/report.md):

  - Other user-uploaded photos in the slideshow will be disabled.
  - Other built-in themes (Classic, Weather, Clock, ...) should also be
    disabled out-of-band so the device doesn't rotate away from Photo.
  - The reboot endpoint drops the HTTP connection before responding;
    treat any connection error as success.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import aiohttp

from ..const import (
    BRIGHTNESS_RANGE_SDPRO,
    MODEL_SDPRO,
    THEME_CUSTOM_IMAGE_SDPRO,
)
from .base import ConnectionResult, DeviceDriver, DeviceState, SpaceInfo

_LOGGER = logging.getLogger(__name__)

DASHBOARD_FILENAME = "dashboard.jpg"


class SDProDriver(DeviceDriver):
    """HTTP driver for SD_PRO community firmware."""

    model = MODEL_SDPRO
    custom_image_theme = THEME_CUSTOM_IMAGE_SDPRO
    brightness_range = BRIGHTNESS_RANGE_SDPRO
    supports_navigation = False
    supports_on_demand_image = False

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        sw_version: str | None = "SD_PRO",
    ) -> None:
        super().__init__(base_url, session)
        self.sw_version = sw_version
        self._cached_total: int | None = None

    async def _get_config(self) -> dict:
        async with self._session.get(f"{self.base_url}/config") as r:
            r.raise_for_status()
            return await r.json(content_type=None)

    async def _api_set(self, key: str, value: str | int) -> None:
        url = f"{self.base_url}/api/set?key={quote(str(key))}&value={quote(str(value))}"
        async with self._session.get(url) as r:
            r.raise_for_status()

    async def get_state(self) -> DeviceState:
        config = await self._get_config()
        return DeviceState(
            theme=int(config.get("theme", 0)),
            brightness=int(config["brightness"]) if "brightness" in config else None,
            current_image=None,  # no on-demand image concept
        )

    async def get_space(self) -> SpaceInfo:
        config = await self._get_config()
        free = int(config.get("freespace", 0))
        if self._cached_total is None:
            try:
                async with self._session.get(f"{self.base_url}/photo/list") as r:
                    r.raise_for_status()
                    data = await r.json(content_type=None)
                    self._cached_total = int(data.get("total", 0))
            except Exception as err:
                _LOGGER.debug("SD_PRO /photo/list unavailable: %s", err)
                self._cached_total = 0
        return SpaceInfo(total=self._cached_total or 0, free=free)

    async def get_brightness(self) -> int:
        config = await self._get_config()
        return int(config.get("brightness", 0))

    async def set_brightness(self, value: int) -> None:
        value = self.clamp_brightness(value)
        await self._api_set("lcd_brightness", value)

    async def set_theme(self, theme: int) -> None:
        await self._api_set("theme", int(theme))

    async def set_image(self, filename: str) -> None:
        # The SD_PRO firmware has no "show this image" endpoint. The only way
        # to display a specific image is the photo-slideshow workaround in
        # `upload_and_display`. Calling `set_image` directly without an upload
        # is not meaningful here.
        raise NotImplementedError(
            "SD_PRO firmware does not support on-demand image display; "
            "use upload_and_display() instead."
        )

    async def upload(self, image_data: bytes, filename: str) -> None:
        form = aiohttp.FormData()
        form.add_field("file", image_data, filename=filename, content_type="image/jpeg")
        async with self._session.post(f"{self.base_url}/photo/upload", data=form) as r:
            r.raise_for_status()

    async def upload_and_display(self, image_data: bytes, filename: str) -> None:
        # Force the canonical filename so re-uploads overwrite the same slot.
        name = DASHBOARD_FILENAME
        await self.upload(image_data, name)
        await self._ensure_only_photo_enabled(name)
        await self._ensure_photo_theme()

    async def list_themes(self) -> list[dict]:
        """Return the device's built-in theme list.

        Each entry has `{id: int, name: str, enabled: bool}`. Used by the
        config flow to show the user which themes will be disabled.
        """
        async with self._session.get(f"{self.base_url}/theme/list") as r:
            r.raise_for_status()
            data = await r.json(content_type=None)
            return list(data.get("themes", []))

    async def disable_other_themes(self) -> list[str]:
        """Disable every built-in theme except Photo (the integration's slot).

        Returns the list of theme names that were toggled off, so the caller
        can confirm to the user what changed. Idempotent — themes already
        disabled are left alone.
        """
        disabled: list[str] = []
        try:
            themes = await self.list_themes()
        except Exception as err:
            _LOGGER.warning("SD_PRO /theme/list failed: %s", err)
            return disabled
        for theme in themes:
            theme_id = theme.get("id")
            if theme_id is None or int(theme_id) == self.custom_image_theme:
                continue
            if not theme.get("enabled"):
                continue
            try:
                await self._theme_toggle(int(theme_id), False)
                disabled.append(str(theme.get("name", f"theme {theme_id}")))
            except Exception as err:
                _LOGGER.debug("SD_PRO disable theme %s failed: %s", theme_id, err)
        return disabled

    async def _theme_toggle(self, theme_id: int, enabled: bool) -> None:
        state = 1 if enabled else 0
        url = f"{self.base_url}/theme/toggle?id={theme_id}&state={state}"
        async with self._session.get(url) as r:
            r.raise_for_status()

    async def _ensure_only_photo_enabled(self, keep_name: str) -> None:
        try:
            async with self._session.get(f"{self.base_url}/photo/list") as r:
                r.raise_for_status()
                data = await r.json(content_type=None)
        except Exception as err:
            _LOGGER.debug("SD_PRO /photo/list failed: %s", err)
            return

        for entry in data.get("files", []):
            name = entry.get("name")
            enabled = bool(entry.get("enabled"))
            if name == keep_name:
                if not enabled:
                    await self._photo_toggle(name, True)
            elif enabled:
                await self._photo_toggle(name, False)

    async def _photo_toggle(self, name: str, enabled: bool) -> None:
        state = 1 if enabled else 0
        url = f"{self.base_url}/photo/toggle?name={quote(name)}&state={state}"
        async with self._session.get(url) as r:
            r.raise_for_status()

    async def _ensure_photo_theme(self) -> None:
        try:
            config = await self._get_config()
        except Exception as err:
            _LOGGER.debug("SD_PRO /config failed during theme check: %s", err)
            await self.set_theme(self.custom_image_theme)
            return
        if int(config.get("theme", -1)) != self.custom_image_theme:
            await self.set_theme(self.custom_image_theme)

    async def delete_file(self, path: str) -> None:
        # Accept either "name" or "/photo/name"; the firmware wants basename.
        name = path.rsplit("/", 1)[-1]
        async with self._session.get(f"{self.base_url}/photo/delete?name={quote(name)}") as r:
            r.raise_for_status()

    async def clear_images(self) -> None:
        try:
            async with self._session.get(f"{self.base_url}/photo/list") as r:
                r.raise_for_status()
                data = await r.json(content_type=None)
        except Exception as err:
            _LOGGER.debug("SD_PRO /photo/list failed during clear: %s", err)
            return
        for entry in data.get("files", []):
            name = entry.get("name")
            if name:
                try:
                    await self.delete_file(name)
                except Exception as err:
                    _LOGGER.debug("SD_PRO delete %s failed: %s", name, err)

    async def reboot(self) -> None:
        # /restart drops the connection before responding; treat connection
        # errors as success.
        try:
            async with self._session.get(f"{self.base_url}/restart") as r:
                r.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.debug("SD_PRO reboot connection dropped (expected): %s", err)

    async def test_connection(self) -> ConnectionResult:
        try:
            await self._get_config()
        except TimeoutError:
            return ConnectionResult(
                success=False,
                error="timeout",
                message="Connection timed out after 30 seconds",
            )
        except aiohttp.ClientConnectorDNSError as e:
            return ConnectionResult(
                success=False,
                error="dns_error",
                message=f"Could not resolve hostname: {e}",
            )
        except aiohttp.ClientConnectorError as e:
            return ConnectionResult(success=False, error="connection_refused", message=str(e))
        except aiohttp.ClientResponseError as e:
            return ConnectionResult(
                success=False,
                error="http_error",
                message=f"HTTP error {e.status}: {e.message}",
            )
        except Exception as e:
            return ConnectionResult(success=False, error="unknown", message=str(e))
        return ConnectionResult(success=True)
