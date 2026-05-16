"""Data update coordinator for GeekMagic integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .connection_backoff import ConnectionBackoff
from .const import (
    BACKOFF_LOG_INTERVAL,
    CONF_DISPLAY_ROTATION,
    CONF_JPEG_QUALITY,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    DEFAULT_DISPLAY_ROTATION,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    MAX_BACKOFF_MULTIPLIER,
    MODEL_PRO,
    THEME_WATCHOS,
)
from .device import DeviceState, GeekMagicDevice, SpaceInfo
from .history_fetcher import HistoryFetcher, extract_numeric_values
from .layouts.fullscreen import FullscreenLayout
from .layouts.hero import HeroLayout
from .layouts.hero_simple import HeroSimpleLayout
from .renderer import Renderer
from .screen_builder import (
    CONF_ASSIGNED_VIEWS,
    LAYOUT_CLASSES,
    build_screens,
    migrate_options,
    screen_name_at,
)
from .widget_state_builder import PrefetchedData, build_widget_states
from .widgets.base import WidgetConfig
from .widgets.camera import CameraWidget
from .widgets.candlestick import CandlestickWidget
from .widgets.chart import ChartWidget
from .widgets.clock import ClockWidget
from .widgets.icon import IconWidget
from .widgets.media import MediaWidget
from .widgets.state import WidgetState
from .widgets.text import TextWidget
from .widgets.theme import get_theme
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from .layouts.base import Layout
    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)

# Re-exported for backwards compatibility (websocket and tests import these
# names from coordinator). New code should import from screen_builder /
# history_fetcher directly.
__all__ = [
    "CONF_ASSIGNED_VIEWS",
    "LAYOUT_CLASSES",
    "GeekMagicCoordinator",
    "extract_numeric_values",
]


class GeekMagicCoordinator(DataUpdateCoordinator):
    """Coordinator for GeekMagic display updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: GeekMagicDevice,
        options: dict[str, Any],
        config_entry: Any = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            device: GeekMagic device client
            options: Integration options
            config_entry: Config entry reference for entity registration
        """
        self.device = device
        self.options = migrate_options(options)
        self.renderer = Renderer()
        self._layouts: list = []  # List of layouts for each screen
        self._layout_names: list[str] = []  # Names parallel to self._layouts
        self._current_screen: int = 0
        self._last_screen_change: float = time.time()
        self._last_image: bytes | None = None  # PNG bytes for camera preview
        self._last_update_success: bool = False
        self._last_update_time: float | None = None
        self.config_entry = config_entry
        self._camera_images: dict[str, bytes] = {}  # Pre-fetched camera images
        self._media_images: dict[str, bytes] = {}  # Pre-fetched media player album art
        self._chart_history: dict[str, list[float]] = {}  # Pre-fetched chart history
        self._candlestick_data: dict[str, list[tuple[float, float, float, float]]] = {}
        self._weather_forecasts: dict[str, list[dict[str, Any]]] = {}  # Pre-fetched forecasts
        self._update_preview: bool = True  # Update preview on next refresh
        self._preview_just_updated: bool = False  # True if preview was updated in last refresh

        # Device state (updated on refresh)
        self._device_state: DeviceState | None = None
        self._space_info: SpaceInfo | None = None
        self._device_brightness: int | None = None
        self._last_brightness_poll: float = 0  # Timestamp of last brightness poll
        self._brightness_poll_interval: float = 600  # 10 minutes

        # Notification state
        self._notification_expiry: float = 0
        self._notification_data: dict[str, Any] | None = None
        self._notification_clear_handle: asyncio.TimerHandle | None = None

        # Display mode tracking
        # "custom" = integration renders views, "builtin" = device shows built-in mode
        self._display_mode: str = "custom"
        self._builtin_theme: int = 0  # Device theme when in builtin mode (0-2)

        # Sleep/wake state — when paused, the render/upload cycle is skipped entirely
        self._paused: bool = False
        self._pre_pause_brightness: int | None = None

        # Backoff state for handling offline devices
        interval = int(self.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL))
        self._backoff = ConnectionBackoff(
            logger=_LOGGER,
            base_interval_seconds=interval,
            max_multiplier=MAX_BACKOFF_MULTIPLIER,
            log_interval=BACKOFF_LOG_INTERVAL,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

        _LOGGER.debug(
            "Initialized GeekMagic coordinator for %s with refresh interval %ds",
            device.host,
            interval,
        )

        # Initialize screens
        self._setup_screens()

        # Create welcome layout for when no screens are configured
        self._welcome_layout: Layout | None = None

    def _setup_screens(self) -> None:
        """(Re)build all screens from current options, delegating to screen_builder."""
        pairs = build_screens(self.options, self._get_store())
        self._layout_names = [name for name, _ in pairs]
        self._layouts = [layout for _, layout in pairs]

        if self._current_screen >= len(self._layouts):
            _LOGGER.debug(
                "Current screen %d out of range, resetting to 0",
                self._current_screen,
            )
            self._current_screen = 0

    def _get_store(self) -> GeekMagicStore | None:
        """Get the global view store.

        Returns:
            Store instance or None if not available
        """
        return self.hass.data.get(DOMAIN, {}).get("store")

    def _create_welcome_layout(self) -> Layout:
        """Create a welcome layout showcasing widgets with HA info.

        Returns:
            A HeroLayout with clock, HA version, and entity stats.
        """
        layout = HeroLayout(footer_slots=3, hero_ratio=0.65, padding=8, gap=8)

        # Hero: Clock widget showing current time. No explicit color — the
        # widget defaults to theme.text_primary so the welcome screen reads
        # correctly under light themes too.
        clock = ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=0,
                options={"show_date": True, "show_seconds": False},
            )
        )
        layout.set_widget(0, clock)

        # Footer: HA version, entity count, setup hint — uniform
        # text_primary values under text_secondary captions, in the
        # watchOS three-band style.
        for slot, label, text in (
            (1, "HA", self._get_ha_version()),
            (2, "Entities", str(self._get_entity_count())),
            (3, "Setup", "Ready"),
        ):
            layout.set_widget(
                slot,
                TextWidget(
                    WidgetConfig(
                        widget_type="text",
                        slot=slot,
                        label=label,
                        options={"text": text, "size": "small", "align": "center"},
                    )
                ),
            )

        return layout

    def _get_ha_version(self) -> str:
        """Get Home Assistant version string."""
        return ha_version

    def _get_entity_count(self) -> int:
        """Get total number of entities in Home Assistant."""
        try:
            return len(self.hass.states.async_all())
        except Exception:
            return 0

    @property
    def current_screen(self) -> int:
        """Get current screen index."""
        return self._current_screen

    @property
    def screen_count(self) -> int:
        """Get total number of screens."""
        return len(self._layouts)

    @property
    def current_screen_name(self) -> str:
        """Get current screen name."""
        return screen_name_at(self.options, self._current_screen, self._get_store())

    async def async_set_screen(self, screen_index: int) -> None:
        """Switch to a specific screen.

        Args:
            screen_index: Screen index (0-based)
        """
        if 0 <= screen_index < len(self._layouts):
            self._current_screen = screen_index
            self._last_screen_change = time.time()

            # If in builtin mode, switch to custom mode so the screen change is rendered
            if self._display_mode == "builtin":
                _LOGGER.debug("Switching from builtin to custom mode for screen change")
                self._display_mode = "custom"
                await self.device.set_theme_custom()

            await self.async_request_refresh()

    async def async_next_screen(self) -> None:
        """Switch to the next screen."""
        if len(self._layouts) > 0:
            next_screen = (self._current_screen + 1) % len(self._layouts)
            await self.async_set_screen(next_screen)

            # For Pro devices, also trigger device navigation to help refresh
            if self.device.model == MODEL_PRO:
                try:
                    await self.device.navigate_next()
                except Exception as err:
                    _LOGGER.debug("Pro navigate_next failed (non-fatal): %s", err)

    async def async_previous_screen(self) -> None:
        """Switch to the previous screen."""
        if len(self._layouts) > 0:
            prev_screen = (self._current_screen - 1) % len(self._layouts)
            await self.async_set_screen(prev_screen)

            # For Pro devices, also trigger device navigation to help refresh
            if self.device.model == MODEL_PRO:
                try:
                    await self.device.navigate_previous()
                except Exception as err:
                    _LOGGER.debug("Pro navigate_previous failed (non-fatal): %s", err)

    def update_options(self, options: dict[str, Any]) -> None:
        """Update coordinator options.

        Args:
            options: New options dictionary
        """
        self.options = migrate_options(options)

        # Update refresh interval
        interval = int(self.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL))
        self._backoff.base_interval = interval
        self.update_interval = timedelta(seconds=interval)

        # Rebuild all screens
        self._setup_screens()

        # Update preview on next refresh (config changed)
        self._update_preview = True

    def _build_widget_states(self, layout: Layout) -> dict[int, WidgetState]:
        """Build WidgetState for every populated slot in `layout`."""
        return build_widget_states(
            layout,
            self.hass,
            PrefetchedData(
                camera_images=self._camera_images,
                media_images=self._media_images,
                chart_history=self._chart_history,
                candlestick_data=self._candlestick_data,
                weather_forecasts=self._weather_forecasts,
            ),
        )

    def _render_display(self) -> tuple[bytes, bytes]:
        """Render the display image (runs in executor thread).

        Returns:
            Tuple of (jpeg_data, png_data)
        """
        # Create canvas using the active layout's theme background, so
        # non-black themes (light, candy, ocean) render the correct base.
        active_layout = (
            self._layouts[self._current_screen]
            if self._layouts and 0 <= self._current_screen < len(self._layouts)
            else None
        )
        canvas_bg = active_layout.theme.background if active_layout else (0, 0, 0)
        img, draw = self.renderer.create_canvas(background=canvas_bg)

        # Render current screen's layout
        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]

            # Check for active notification
            if time.time() < self._notification_expiry and self._notification_data:
                _LOGGER.debug("Rendering active notification")
                layout = self._create_notification_layout(self._notification_data)

            _LOGGER.debug(
                "Rendering layout %s with %d widgets",
                type(layout).__name__,
                sum(1 for s in layout.slots if s.widget is not None),
            )
            # Build widget states
            widget_states = self._build_widget_states(layout)
            layout.render(self.renderer, draw, widget_states)
        else:
            # No screens configured - show welcome screen with live data
            _LOGGER.debug("No screens configured, rendering welcome screen")
            # Recreate welcome layout each time to get fresh HA stats
            welcome_layout = self._create_welcome_layout()
            widget_states = self._build_widget_states(welcome_layout)
            welcome_layout.render(self.renderer, draw, widget_states)

        # Encode to both formats
        jpeg_quality = self.options.get(CONF_JPEG_QUALITY, DEFAULT_JPEG_QUALITY)
        rotation = self.options.get(CONF_DISPLAY_ROTATION, DEFAULT_DISPLAY_ROTATION)
        jpeg_data = self.renderer.to_jpeg(img, quality=jpeg_quality, rotation=rotation)
        png_data = self.renderer.to_png(img, rotation=rotation)

        return jpeg_data, png_data

    async def trigger_notification(self, data: dict[str, Any]) -> None:
        """Trigger a notification on this device.

        Args:
            data: Notification data (message, title, icon, duration, etc.)
        """
        duration = data.get("duration", 10)
        self._notification_data = data
        self._notification_expiry = time.time() + duration

        # Cancel any pending clear callback to prevent race conditions
        if self._notification_clear_handle is not None:
            self._notification_clear_handle.cancel()

        # Schedule cleanup and store handle for potential cancellation
        self._notification_clear_handle = self.hass.loop.call_later(
            duration, self._clear_notification
        )

        # Force immediate refresh
        await self.async_request_refresh()

    def _clear_notification(self) -> None:
        """Clear the active notification and refresh."""
        self._notification_expiry = 0
        self._notification_data = None
        self._notification_clear_handle = None
        # Use fire-and-forget for the refresh since this is a callback
        self.hass.async_create_task(self.async_request_refresh())

    def _create_notification_layout(self, data: dict[str, Any]) -> Layout:
        """Create a layout for a notification.

        Args:
            data: Notification data

        Returns:
            Layout: HeroSimpleLayout (with message) or FullscreenLayout (image only)
        """
        message = data.get("message")

        # Scenario 1: No message -> Fullscreen Layout (Image/Icon only)
        if not message:
            layout = FullscreenLayout()
            # Apply theme if specified
            theme_name = data.get("theme", THEME_WATCHOS)
            layout.theme = get_theme(theme_name)

            hero_widget = None
            image_url = data.get("image")

            if image_url:
                hero_widget = CameraWidget(
                    WidgetConfig(
                        widget_type="camera",
                        slot=0,
                        entity_id=image_url,
                        options={
                            # contain ensures full image visible, cover fills screen
                            "fit": "contain",
                        },
                    )
                )

            if not hero_widget:
                # Default to Icon — IconWidget falls back to the active
                # theme's accent color (matches whatever theme the user
                # picked for the notification).
                icon = data.get("icon", "mdi:bell-ring")
                hero_widget = IconWidget(
                    WidgetConfig(
                        widget_type="icon",
                        slot=0,
                        options={
                            "icon": icon,
                            "size": "huge",  # This option is now supported by IconWidget
                            "show_panel": False,  # Clean fullscreen look
                        },
                    )
                )
            layout.set_widget(0, hero_widget)
            return layout

        # Scenario 2: Message exists -> Hero Simple Layout
        layout = HeroSimpleLayout()

        # Apply theme if specified
        theme_name = data.get("theme", THEME_WATCHOS)
        layout.theme = get_theme(theme_name)

        # Slot 0 (Hero): Icon or Image
        hero_widget = None
        image_url = data.get("image")
        if image_url:
            hero_widget = CameraWidget(
                WidgetConfig(
                    widget_type="camera", slot=0, entity_id=image_url, options={"fit": "contain"}
                )
            )

        if not hero_widget:
            # Default to Icon — falls back to the active theme's accent color.
            icon = data.get("icon", "mdi:bell-ring")
            hero_widget = IconWidget(
                WidgetConfig(
                    widget_type="icon",
                    slot=0,
                    options={
                        "icon": icon,
                        "size": "huge",  # Force huge icon
                    },
                )
            )
        layout.set_widget(0, hero_widget)

        # Slot 1 (Footer): Message — defaults to theme.text_primary.
        text_widget = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=1,
                options={
                    "text": message,
                    "size": "medium",
                    "align": "center",
                },
            )
        )
        layout.set_widget(1, text_widget)

        return layout

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data and update display.

        Implements exponential backoff when device is offline to reduce
        log spam and resource usage. When the device comes back online,
        the update interval is restored to normal.

        Returns:
            Dictionary with update status
        """
        try:
            if self._paused:
                return {"success": True, "paused": True}

            # If device was offline, do a lightweight connectivity check first
            # to avoid expensive rendering operations
            if self._backoff.is_offline:
                try:
                    result = await self.device.test_connection()
                except Exception as conn_err:
                    self.update_interval = self._backoff.record_failure()
                    self._backoff.log_failure(
                        self.device.host,
                        str(conn_err),
                        int(self.update_interval.total_seconds()),
                    )
                    raise UpdateFailed(f"Device offline: {conn_err}") from conn_err

                if not result.success:
                    self.update_interval = self._backoff.record_failure()
                    error_msg = result.message or "Connection failed"
                    self._backoff.log_failure(
                        self.device.host,
                        error_msg,
                        int(self.update_interval.total_seconds()),
                    )
                    raise UpdateFailed(f"Device offline: {error_msg}")  # noqa: TRY301

                _LOGGER.info(
                    "GeekMagic device %s is back online after %d failed attempts",
                    self.device.host,
                    self._backoff.failure_count,
                )
                self.update_interval = self._backoff.record_success()

            _LOGGER.debug(
                "Starting display update for screen %d/%d (%s)",
                self._current_screen + 1,
                len(self._layouts),
                self.current_screen_name,
            )

            # Check for auto-cycling
            cycle_interval = self.options.get(
                CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL
            )
            if cycle_interval > 0 and len(self._layouts) > 1:
                now = time.time()
                if now - self._last_screen_change >= cycle_interval:
                    old_screen = self._current_screen
                    self._current_screen = (self._current_screen + 1) % len(self._layouts)
                    self._last_screen_change = now
                    _LOGGER.debug(
                        "Auto-cycled screen from %d to %d",
                        old_screen,
                        self._current_screen,
                    )

            # Poll device brightness on first update and every 10 minutes
            now = time.time()
            if (
                self._device_brightness is None
                or now - self._last_brightness_poll >= self._brightness_poll_interval
            ):
                try:
                    self._device_brightness = await self.device.get_brightness()
                    self._last_brightness_poll = now
                    _LOGGER.debug("Polled device brightness: %d", self._device_brightness)
                except Exception as e:
                    _LOGGER.debug("Failed to poll device brightness: %s", e)

            # Fetch device state and storage info
            try:
                self._device_state = await self.device.get_state()
                self._space_info = await self.device.get_space()

                # Sync display mode with device state on first poll
                # If device is in a built-in theme, respect that
                if self._device_state and self._device_state.theme is not None:
                    device_theme = self._device_state.theme
                    if device_theme < 3 and self._display_mode == "custom":
                        # Device is in built-in mode but we thought we were in custom
                        # This can happen on startup - sync to device state
                        _LOGGER.debug(
                            "Syncing display mode from device: builtin (theme=%d)",
                            device_theme,
                        )
                        self._display_mode = "builtin"
                        self._builtin_theme = device_theme
            except Exception as e:
                _LOGGER.debug("Failed to fetch device state: %s", e)

            # Skip rendering when in built-in mode
            # The device handles display in built-in modes (Clock, Weather, System Info)
            if self._display_mode == "builtin":
                _LOGGER.debug(
                    "Skipping render - device in built-in mode (theme=%d)",
                    self._builtin_theme,
                )
                return {
                    "success": True,
                    "builtin_mode": True,
                    "theme": self._builtin_theme,
                }

            # Pre-fetch async data (camera images, media art, chart history, weather forecasts)
            # (must be done in async context)
            await self._async_fetch_camera_images()
            await self._async_fetch_media_images()
            await self._async_fetch_chart_history()
            await self._async_fetch_candlestick_history()
            await self._async_fetch_weather_forecasts()

            # Render image in executor to avoid blocking the event loop
            # (Pillow image operations are CPU-intensive)
            jpeg_data, png_data = await self.hass.async_add_executor_job(self._render_display)

            # Only update preview image on config changes or manual refresh
            # (prevents HA UI from refreshing during periodic updates)
            self._preview_just_updated = self._update_preview
            if self._update_preview:
                self._last_image = png_data
                self._update_preview = False

            _LOGGER.debug(
                "Rendered image: JPEG=%d bytes, PNG=%d bytes",
                len(jpeg_data),
                len(png_data),
            )

            await self.device.upload_and_display(jpeg_data, "dashboard.jpg")

            # Track success status
            self._last_update_success = True
            self._last_update_time = time.time()

            _LOGGER.debug(
                "Display update completed: screen=%s, size=%.1fKB",
                self.current_screen_name,
                len(jpeg_data) / 1024,
            )

            return {
                "success": True,
                "size_kb": len(jpeg_data) / 1024,
                "current_screen": self._current_screen,
                "screen_name": self.current_screen_name,
            }

        except UpdateFailed:
            # Re-raise UpdateFailed without additional logging (already logged)
            self._last_update_success = False
            raise
        except Exception as err:
            self._last_update_success = False
            self.update_interval = self._backoff.record_failure()
            self._backoff.log_connection_error(
                self.device.host, err, int(self.update_interval.total_seconds())
            )
            raise UpdateFailed(f"Error updating display: {err}") from err

    @property
    def last_image(self) -> bytes | None:
        """Get the last rendered image as PNG bytes."""
        return self._last_image

    @property
    def preview_just_updated(self) -> bool:
        """Check if preview was updated in the last refresh cycle."""
        return self._preview_just_updated

    @property
    def device_name(self) -> str:
        """Get device display name."""
        if self.config_entry and self.config_entry.title:
            return self.config_entry.title
        return f"GeekMagic {self.device.host}"

    @property
    def device_version(self) -> str | None:
        """Get device firmware version."""
        # Could be fetched from device if supported
        return None

    @property
    def last_update_success(self) -> bool:
        """Check if last update was successful."""
        return self._last_update_success

    @last_update_success.setter
    def last_update_success(self, value: bool) -> None:
        """Set last update success status."""
        self._last_update_success = value

    @property
    def last_update_time(self) -> float | None:
        """Get timestamp of last successful update."""
        return self._last_update_time

    @property
    def brightness(self) -> int:
        """Get current brightness setting."""
        return self.options.get("brightness", 50)

    @property
    def entry(self):
        """Get config entry (alias for config_entry)."""
        return self.config_entry

    @property
    def device_state(self) -> DeviceState | None:
        """Get current device state."""
        return self._device_state

    @property
    def device_brightness(self) -> int | None:
        """Get device brightness from /brt.json endpoint."""
        return self._device_brightness

    @device_brightness.setter
    def device_brightness(self, value: int) -> None:
        """Set device brightness cache."""
        self._device_brightness = value

    @property
    def is_active(self) -> bool:
        """Return True when the display is active (not paused/sleeping)."""
        return not self._paused

    @property
    def space_info(self) -> SpaceInfo | None:
        """Get device storage info."""
        return self._space_info

    def get_store(self) -> GeekMagicStore | None:
        """Get global views store."""
        return self._get_store()

    def set_current_screen(self, index: int) -> None:
        """Set current screen index."""
        self._current_screen = index

    @property
    def display_mode(self) -> str:
        """Get current display mode ('custom' or 'builtin')."""
        return self._display_mode

    @property
    def builtin_theme(self) -> int:
        """Get current builtin theme number (0-2) when in builtin mode."""
        return self._builtin_theme

    def set_display_mode(self, mode: str, value: int = 0) -> None:
        """Set display mode.

        Args:
            mode: Either 'custom' or 'builtin'
            value: For 'custom', the view index. For 'builtin', the theme number.
        """
        self._display_mode = mode
        if mode == "builtin":
            self._builtin_theme = value
        else:
            # Custom mode - value is view index
            self._current_screen = value
            self._last_screen_change = time.time()

    async def async_set_brightness(self, brightness: int) -> None:
        """Set display brightness.

        Args:
            brightness: Brightness level 0-100
        """
        await self.device.set_brightness(brightness)

    async def async_set_active(self, active: bool) -> None:
        """Pause or resume the render/upload cycle.

        When paused: stores current brightness, dims screen to 0, and skips
        all rendering and uploading until resumed. Intended for presence-based
        automation (turn off when room is empty).

        When resumed: restores brightness and triggers an immediate refresh.

        Args:
            active: True to resume, False to pause/sleep
        """
        if active:
            self._paused = False
            if self._pre_pause_brightness is not None:
                await self.device.set_brightness(self._pre_pause_brightness)
                self._device_brightness = self._pre_pause_brightness
                self._pre_pause_brightness = None
            _LOGGER.debug("Display activated, triggering refresh")
            await self.async_request_refresh()
        else:
            if not self._paused:
                self._pre_pause_brightness = self._device_brightness
            await self.device.set_brightness(0)
            self._device_brightness = 0
            self._paused = True
            _LOGGER.debug("Display paused (pre-pause brightness: %s)", self._pre_pause_brightness)
            self.async_update_listeners()

    async def async_refresh_display(self) -> None:
        """Force an immediate display refresh.

        If we were in builtin mode, this switches back to custom mode
        and ensures the device is in custom image mode.
        """
        # If switching from builtin to custom, ensure device is in custom image mode
        if self._display_mode == "builtin":
            _LOGGER.debug("Switching from builtin to custom mode")
            self._display_mode = "custom"

        # Ensure device is in custom image mode
        await self.device.set_theme_custom()

        self._update_preview = True  # Update preview on manual refresh
        await self.async_request_refresh()

    async def async_reload_views(self) -> None:
        """Reload views from store and refresh display.

        Call this when a global view's content has been updated.
        """
        self._setup_screens()
        self._update_preview = True
        await self.async_request_refresh()

    async def _async_fetch_camera_images(self) -> None:
        """Pre-fetch camera images for all camera widgets.

        This must be called from the async context before rendering,
        since camera.async_get_image() is async.
        """
        from homeassistant.components.camera import async_get_image

        # Find all camera/image widgets in current layout
        camera_entity_ids: set[str] = set()
        other_entity_ids: set[str] = set()

        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            for slot in layout.slots:
                if slot.widget and isinstance(slot.widget, CameraWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        if entity_id.startswith("camera."):
                            camera_entity_ids.add(entity_id)
                        else:
                            other_entity_ids.add(entity_id)

        # Also collect entities from notification
        if self._notification_data:
            image_source = self._notification_data.get("image")
            if image_source:
                if image_source.startswith("camera."):
                    camera_entity_ids.add(image_source)
                else:
                    other_entity_ids.add(image_source)

        # Fetch non-camera entities first (they populate the same cache)
        for entity_id in other_entity_ids:
            await self._async_fetch_url_image_to_cache(entity_id)

        # Fetch images for each camera
        for entity_id in camera_entity_ids:
            try:
                image = await async_get_image(self.hass, entity_id)
                if image and image.content:
                    self._camera_images[entity_id] = image.content
                    _LOGGER.debug(
                        "Fetched camera image for %s: %d bytes",
                        entity_id,
                        len(image.content),
                    )
            except Exception as e:
                _LOGGER.debug("Failed to fetch camera image for %s: %s", entity_id, e)

    async def _async_fetch_url_image_to_cache(self, source: str) -> None:
        """Fetch image from entity_picture and save to camera image cache.

        Args:
            source: Entity ID
        """
        # Get state for the entity
        image_url = None
        state = self.hass.states.get(source)
        if state:
            image_url = state.attributes.get("entity_picture")

        # Only allow internal Home Assistant URLs (starting with /)
        if not image_url or not image_url.startswith("/"):
            return

        try:
            base_url = get_url(self.hass)
        except NoURLAvailableError:
            _LOGGER.debug("No base URL available for entity picture fetch")
            return

        # Ensure base_url doesn't have trailing slash and image_url has leading slash
        full_url = f"{base_url.rstrip('/')}/{image_url.lstrip('/')}"

        try:
            # Use Home Assistant's managed session for proper SSL/auth handling
            session = async_get_clientsession(self.hass)
            async with session.get(full_url, timeout=10) as response:
                if response.status == 200:
                    image_data = await response.read()
                    self._camera_images[source] = image_data
                    _LOGGER.debug(
                        "Fetched image for notification from %s: %d bytes",
                        source,
                        len(image_data),
                    )
                else:
                    _LOGGER.debug(
                        "Failed to fetch notification image from %s: HTTP %d",
                        source,
                        response.status,
                    )
        except Exception as e:
            _LOGGER.debug("Failed to fetch notification image from %s: %s", source, e)

    def get_camera_image(self, entity_id: str) -> bytes | None:
        """Get pre-fetched camera image.

        Args:
            entity_id: Camera entity ID

        Returns:
            Image bytes or None if not available
        """
        return self._camera_images.get(entity_id)

    async def _async_fetch_media_images(self) -> None:
        """Pre-fetch album art images for all media player widgets.

        Fetches entity_picture URLs from media player entities and downloads
        the album art images for display.
        """
        # Find all media widgets in current layout
        media_entity_ids: set[str] = set()

        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            for slot in layout.slots:
                if slot.widget and isinstance(slot.widget, MediaWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        media_entity_ids.add(entity_id)

        if not media_entity_ids:
            return

        # Fetch album art for each media player
        for entity_id in media_entity_ids:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue

            # Get entity_picture from attributes
            entity_picture = state.attributes.get("entity_picture")
            if not entity_picture or not entity_picture.startswith("/"):
                # Clear any cached image if no internal picture available
                self._media_images.pop(entity_id, None)
                continue

            try:
                base_url = get_url(self.hass)
            except NoURLAvailableError:
                continue

            # Ensure base_url doesn't have trailing slash and entity_picture has leading slash
            image_url = f"{base_url.rstrip('/')}/{entity_picture.lstrip('/')}"

            try:
                # Use Home Assistant's managed session so media proxy requests
                # carry the right auth/cookies.
                session = async_get_clientsession(self.hass)
                async with session.get(image_url, timeout=10) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        self._media_images[entity_id] = image_data
                        _LOGGER.debug(
                            "Fetched album art for %s: %d bytes",
                            entity_id,
                            len(image_data),
                        )
                    else:
                        _LOGGER.debug(
                            "Failed to fetch album art for %s: HTTP %d",
                            entity_id,
                            response.status,
                        )
            except Exception as e:
                _LOGGER.debug("Failed to fetch album art for %s: %s", entity_id, e)

    async def _async_fetch_chart_history(self) -> None:
        """Pre-fetch numeric history for all chart widgets on the active screen."""
        chart_widgets: list[tuple[str, ChartWidget]] = []
        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            for slot in self._layouts[self._current_screen].slots:
                if slot.widget and isinstance(slot.widget, ChartWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        chart_widgets.append((entity_id, slot.widget))

        if not chart_widgets:
            return

        fetcher = HistoryFetcher(self.hass)
        if not fetcher.available:
            return

        for entity_id, widget in chart_widgets:
            values = await fetcher.fetch_numeric(entity_id, widget.hours)
            if values:
                self._chart_history[entity_id] = values
                _LOGGER.debug("Fetched %d history points for %s", len(values), entity_id)

    async def _async_fetch_candlestick_history(self) -> None:
        """Pre-fetch and aggregate OHLC data for all candlestick widgets."""
        candlestick_widgets: list[tuple[str, CandlestickWidget]] = []
        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            for slot in self._layouts[self._current_screen].slots:
                if slot.widget and isinstance(slot.widget, CandlestickWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        candlestick_widgets.append((entity_id, slot.widget))

        if not candlestick_widgets:
            return

        fetcher = HistoryFetcher(self.hass)
        if not fetcher.available:
            return

        for entity_id, widget in candlestick_widgets:
            candles = await fetcher.fetch_ohlc(
                entity_id, widget.hours, widget.interval_seconds, widget.candle_count
            )
            if candles:
                self._candlestick_data[entity_id] = candles
                _LOGGER.debug("Aggregated %d candles for %s", len(candles), entity_id)

    async def _async_fetch_weather_forecasts(self) -> None:
        """Pre-fetch forecast data for all weather widgets.

        This must be called from the async context before rendering,
        since weather.get_forecasts is a service call that requires async.

        Uses the weather.get_forecasts service introduced in Home Assistant 2023.9,
        since the forecast attribute was removed from weather entities in 2024.3.
        """
        # Find all weather widgets in current layout
        weather_entity_ids: set[str] = set()

        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            for slot in layout.slots:
                if slot.widget and isinstance(slot.widget, WeatherWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        weather_entity_ids.add(entity_id)

        if not weather_entity_ids:
            return

        # Fetch forecast for each weather entity
        for entity_id in weather_entity_ids:
            try:
                # Use daily forecast type (most common for weather displays)
                response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"type": "daily"},
                    target={"entity_id": entity_id},
                    blocking=True,
                    return_response=True,
                )

                forecast_response = response.get(entity_id) if isinstance(response, dict) else None
                if isinstance(forecast_response, dict):
                    forecast = forecast_response.get("forecast", [])
                    self._weather_forecasts[entity_id] = forecast
                    _LOGGER.debug(
                        "Fetched %d forecast days for %s",
                        len(forecast),
                        entity_id,
                    )
            except Exception as e:
                _LOGGER.debug("Failed to fetch forecast for %s: %s", entity_id, e)
