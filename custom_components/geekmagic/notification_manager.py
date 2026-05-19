"""Active notification subsystem for the GeekMagic display.

Owns the entire lifecycle of a transient on-screen notification:
- trigger / retrigger (with auto-cancel of any in-flight expiry timer)
- expiry via HA's event loop (`call_later`) and explicit clear
- the layout-override decision used by the render loop
- the message-vs-image-vs-icon layout construction

Single instance per coordinator. Callers (the notify service handler, the
render loop, the pre-fetch pipeline) ask this module rather than reaching
into coordinator state.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .const import THEME_WATCHOS
from .layouts.fullscreen import FullscreenLayout
from .layouts.hero_simple import HeroSimpleLayout
from .widgets.base import WidgetConfig
from .widgets.camera import CameraWidget
from .widgets.icon import IconWidget
from .widgets.text import TextWidget
from .widgets.theme import get_theme

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable, Coroutine

    from homeassistant.core import HomeAssistant

    from .layouts.base import Layout


DEFAULT_DURATION_SECONDS = 10
DEFAULT_ICON = "mdi:bell-ring"


class NotificationManager:
    """Holds the active notification (if any) and owns its lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        request_refresh: Callable[[], Coroutine[None, None, None]],
    ) -> None:
        """Build a manager bound to a coordinator's `async_request_refresh`.

        `request_refresh` is invoked on trigger and on auto-expiry so the
        display picks up the appearance and the disappearance of the
        notification on the next render cycle.
        """
        self._hass = hass
        self._request_refresh = request_refresh
        self._data: dict[str, Any] | None = None
        self._expiry: float = 0
        self._clear_handle: asyncio.TimerHandle | None = None

    @property
    def is_active(self) -> bool:
        """True when a notification should currently be shown."""
        return self._data is not None and time.time() < self._expiry

    @property
    def image_source(self) -> str | None:
        """The image entity/URL the active notification wants displayed.

        Returned so the pre-fetch pipeline knows to download it before
        the next render cycle. None when there's no notification or the
        notification has no image.
        """
        if not self.is_active or self._data is None:
            return None
        source = self._data.get("image")
        return source if isinstance(source, str) and source else None

    async def trigger(self, data: dict[str, Any]) -> None:
        """Show a new notification, replacing any in-flight one.

        Cancels and reschedules the auto-clear timer so retriggering
        before expiry doesn't fire the previous timer mid-way.
        """
        duration = data.get("duration", DEFAULT_DURATION_SECONDS)
        self._data = data
        self._expiry = time.time() + duration

        if self._clear_handle is not None:
            self._clear_handle.cancel()

        self._clear_handle = self._hass.loop.call_later(duration, self._on_expiry)

        await self._request_refresh()

    def _on_expiry(self) -> None:
        """Auto-clear callback fired by the HA event loop."""
        self._expiry = 0
        self._data = None
        self._clear_handle = None
        # Fire-and-forget — we're inside a sync callback on the loop.
        self._hass.async_create_task(self._request_refresh())

    def build_layout(self) -> Layout | None:
        """Return the layout to render right now, or None to use the screen.

        Two shapes:
          - message present → `HeroSimpleLayout` (hero icon/image, footer text)
          - message absent → `FullscreenLayout` (icon/image only)
        """
        if not self.is_active or self._data is None:
            return None
        data = self._data
        message = data.get("message")
        theme = get_theme(data.get("theme", THEME_WATCHOS))
        image_url = data.get("image")
        icon = data.get("icon", DEFAULT_ICON)

        if not message:
            layout = FullscreenLayout()
            layout.theme = theme
            layout.set_widget(0, _hero_visual(image_url, icon, show_panel=False))
            return layout

        layout = HeroSimpleLayout()
        layout.theme = theme
        layout.set_widget(0, _hero_visual(image_url, icon, show_panel=True))
        layout.set_widget(
            1,
            TextWidget(
                WidgetConfig(
                    widget_type="text",
                    slot=1,
                    options={"text": message, "size": "medium", "align": "center"},
                )
            ),
        )
        return layout


def _hero_visual(image_url: str | None, icon: str, *, show_panel: bool):
    """Hero slot widget: image if provided, otherwise the icon."""
    if image_url:
        return CameraWidget(
            WidgetConfig(
                widget_type="camera",
                slot=0,
                entity_id=image_url,
                options={"fit": "contain"},
            )
        )
    options: dict[str, Any] = {"icon": icon, "size": "huge"}
    if not show_panel:
        options["show_panel"] = False
    return IconWidget(WidgetConfig(widget_type="icon", slot=0, options=options))
