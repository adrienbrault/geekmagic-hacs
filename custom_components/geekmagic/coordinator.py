"""Data update coordinator for GeekMagic integration."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ANIMATION_FPS,
    ANIMATION_SECONDS,
    BACKOFF_LOG_INTERVAL,
    CONF_DISPLAY_ROTATION,
    CONF_ENABLE_ANIMATIONS,
    CONF_JPEG_QUALITY,
    CONF_LAYOUT,
    CONF_MANAGE_PRO_ALBUM,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_DISPLAY_ROTATION,
    DEFAULT_ENABLE_ANIMATIONS,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    FORCED_REPUSH_INTERVAL,
    LAYOUT_GRID_2X2,
    MAX_BACKOFF_MULTIPLIER,
    MAX_IMAGE_SIZE,
    REBOOT_GRACE_SECONDS,
    THEME_WATCHOS,
)
from .device import DeviceState, GeekMagicDevice, RenderedDashboardRequest, SpaceInfo
from .frame import FrameInputs, build_layout, get_forecast_cache, layout_widgets, render_still
from .htmldoc import HAS_ENGINE
from .image_source import get_image_cache, is_image_source
from .layouts.fullscreen import FullscreenLayout
from .layouts.hero import HeroLayout
from .layouts.hero_simple import HeroSimpleLayout
from .models import brightness_from_percent, brightness_to_percent
from .renderer import Renderer
from .widgets.base import Widget, WidgetConfig
from .widgets.camera import CameraWidget
from .widgets.clock import ClockWidget
from .widgets.icon import IconWidget
from .widgets.image import ImageWidget
from .widgets.text import TextWidget
from .widgets.theme import get_theme

if TYPE_CHECKING:
    from .layouts.base import Layout
    from .store import GeekMagicStore
    from .widgets.state import WidgetState

_LOGGER = logging.getLogger(__name__)

# Config key for new global views format
CONF_ASSIGNED_VIEWS = "assigned_views"

# Raw brightness applied on resume when the pause state was restored after an
# HA restart, which wipes the remembered pre-pause value (issue #177). Clamped
# to the firmware maximum where it is applied. Deliberately raw rather than a
# percentage: on the Ultra this is the stock web UI's maximum, not the 255
# backlight peak, so a presence automation resuming at night isn't blinding.
DEFAULT_RESUME_BRIGHTNESS = 100

# Slack on the View Cycling deadline. When the cycle interval drives the
# updates, each update lands one interval after the previous one, and the
# view change it should make must not hinge on a few milliseconds of jitter
# between the two wall-clock readings: missing it doubles the interval.
CYCLE_DEADLINE_SLACK = 0.5  # seconds


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
        self.options = self._migrate_options(options)
        self.renderer = Renderer()
        self._layouts: list = []  # List of layouts for each screen
        self._current_screen: int = 0
        self._last_screen_change: float = time.time()
        self._last_image: bytes | None = None  # PNG bytes for camera preview
        self._last_update_success: bool = False
        self._last_update_time: float | None = None
        self.config_entry = config_entry
        # Camera snapshots, album art, pictures, history, forecasts and
        # templates: gathered before each render, kept between them
        self._inputs = FrameInputs(hass)
        # True only when the last cycle rendered a PNG that differs from the
        # previous preview; the preview image entity bumps its state on it.
        self._preview_just_updated: bool = False

        # Device state (updated on refresh)
        self._device_state: DeviceState | None = None
        self._space_info: SpaceInfo | None = None
        self._device_brightness: int | None = None
        self._last_brightness_poll: float = 0  # Timestamp of last brightness poll
        self._brightness_poll_interval: float = 600  # 10 minutes

        # Upload dedup (issue #96): what the device was last pushed, and when
        # (monotonic). None forces the next push; every invalidation also
        # bumps the epoch so a push already in flight cannot re-arm the skip.
        self._last_push: tuple[tuple[bytes, str, bool, str], float] | None = None
        self._push_epoch: int = 0

        # Notification state
        self._notification_expiry: float = 0
        self._notification_data: dict[str, Any] | None = None
        self._notification_clear_handle: asyncio.TimerHandle | None = None

        # Display mode tracking
        # "custom" = integration renders views, "builtin" = device shows built-in mode
        self._display_mode: str = "custom"
        # Bumped whenever a view is shown on request (select entity, panel),
        # so the display select writes its state for explicit changes but
        # not for cycling (see GeekMagicDisplaySelect).
        self.view_selection_serial: int = 0
        self._builtin_theme: int = 0  # Device theme when in builtin mode
        self._custom_display_requested: bool = bool(self.options.get(CONF_ASSIGNED_VIEWS))

        # Sleep/wake state — when paused, the render/upload cycle is skipped entirely
        self._paused: bool = False
        self._pre_pause_brightness: int | None = None
        # Set when the paused state was restored after an HA restart: the
        # pre-pause brightness is unknown, so the next resume falls back to
        # DEFAULT_RESUME_BRIGHTNESS instead of leaving the screen dark.
        self._needs_resume_heal: bool = False

        # Backoff state for handling offline devices
        # When device is unreachable, increase update interval exponentially
        # to reduce log spam and resource usage
        self._consecutive_failures: int = 0
        self._device_offline: bool = False
        # Monotonic deadline of the outage a requested reboot causes
        self._reboot_deadline: float | None = None
        self._base_update_interval: int = int(
            options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        )

        # Get refresh interval from options
        interval = self.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)

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
        self._apply_update_interval()

        # Create welcome layout for when no screens are configured
        self._welcome_layout: Layout | None = None

    def _migrate_options(self, options: dict[str, Any]) -> dict[str, Any]:
        """Migrate old single-screen options to new multi-screen format.

        Args:
            options: Original options dictionary

        Returns:
            Migrated options with screens structure
        """
        if CONF_SCREENS in options:
            return options  # Already in new format

        # Convert old format to new format
        return {
            CONF_REFRESH_INTERVAL: options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            CONF_SCREEN_CYCLE_INTERVAL: DEFAULT_SCREEN_CYCLE_INTERVAL,
            CONF_SCREENS: [
                {
                    "name": "Screen 1",
                    CONF_LAYOUT: options.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
                    CONF_WIDGETS: options.get(CONF_WIDGETS, [{"type": "clock", "slot": 0}]),
                }
            ],
        }

    def _setup_screens(self) -> None:
        """Set up all screens with their layouts and widgets.

        Supports two config formats:
        - New format: assigned_views list referencing global views in store
        - Legacy format: screens list with inline config (for backward compatibility)
        """
        self._layouts = []
        # New widgets, new template sources: drop the compiled ones
        self._inputs.widget_templates.clear()

        # Check for new format first (global views)
        assigned_views = self.options.get(CONF_ASSIGNED_VIEWS, [])
        if assigned_views:
            self._setup_from_global_views(assigned_views)
        else:
            # Fall back to legacy format
            self._setup_from_legacy_screens()

        # Ensure current screen is valid
        if self._current_screen >= len(self._layouts):
            _LOGGER.debug(
                "Current screen %d out of range, resetting to 0",
                self._current_screen,
            )
            self._current_screen = 0

    def _setup_from_global_views(self, view_ids: list[str]) -> None:
        """Set up layouts from global views in store.

        Args:
            view_ids: List of view IDs to load
        """
        store = self._get_store()
        if not store:
            _LOGGER.warning("Store not available, falling back to legacy config")
            self._setup_from_legacy_screens()
            return

        _LOGGER.debug("Setting up %d view(s) from global store", len(view_ids))

        for i, view_id in enumerate(view_ids):
            view_config = store.get_view(view_id)
            if not view_config:
                _LOGGER.warning("View %s not found in store, skipping", view_id)
                continue

            view_name = view_config.get("name", f"View {i + 1}")
            layout = build_layout(view_config)
            self._layouts.append(layout)
            _LOGGER.debug(
                "Created view %d '%s' with layout %s (%d slots)",
                i,
                view_name,
                view_config.get("layout", LAYOUT_GRID_2X2),
                layout.get_slot_count(),
            )

    def _setup_from_legacy_screens(self) -> None:
        """Set up layouts from legacy screens config (backward compatibility)."""
        screens = self.options.get(CONF_SCREENS, [])
        _LOGGER.debug("Setting up %d screen(s) from legacy config", len(screens))

        for i, screen_config in enumerate(screens):
            screen_name = screen_config.get("name", f"Screen {i + 1}")
            layout = build_layout(screen_config)
            self._layouts.append(layout)
            _LOGGER.debug(
                "Created screen %d '%s' with layout %s (%d slots)",
                i,
                screen_name,
                screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2),
                layout.get_slot_count(),
            )

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
        # Check for new format first
        assigned_views = self.options.get(CONF_ASSIGNED_VIEWS, [])
        if assigned_views:
            if 0 <= self._current_screen < len(assigned_views):
                store = self._get_store()
                if store:
                    view = store.get_view(assigned_views[self._current_screen])
                    if view:
                        return view.get("name", f"View {self._current_screen + 1}")
            return "Unknown"

        # Legacy format
        screens = self.options.get(CONF_SCREENS, [])
        if 0 <= self._current_screen < len(screens):
            return screens[self._current_screen].get("name", f"Screen {self._current_screen + 1}")
        return "Unknown"

    async def async_set_screen(self, screen_index: int) -> None:
        """Switch to a specific screen.

        Args:
            screen_index: Screen index (0-based)
        """
        if 0 <= screen_index < len(self._layouts):
            self._current_screen = screen_index
            self._last_screen_change = time.time()
            self._custom_display_requested = True

            # If in builtin mode, switch to custom mode so the screen change is rendered
            if self._display_mode == "builtin":
                _LOGGER.debug("Switching from builtin to custom mode for screen change")
                await self._async_leave_builtin_mode()

            await self.async_request_refresh()

    async def _async_leave_builtin_mode(self) -> None:
        """Hand the screen back from a firmware built-in mode to HA renders.

        The device keeps showing its built-in theme until told to show the
        custom image again, so the theme switch goes first: if it fails,
        the coordinator stays in builtin mode rather than believing it
        renders to a screen nobody sees.
        """
        await self.device.set_theme_custom()
        self._display_mode = "custom"
        # The built-in theme replaced the frame on screen behind our back:
        # re-upload even if the next render matches the last push.
        self._invalidate_push()
        # Keeps the device-state sync from flipping straight back to
        # builtin while the device still reports its built-in theme.
        self._custom_display_requested = True

    @property
    def current_view_id(self) -> str | None:
        """Id of the assigned view on screen, or None in a built-in mode."""
        if self._display_mode != "custom":
            return None
        assigned = self.options.get(CONF_ASSIGNED_VIEWS, [])
        if 0 <= self._current_screen < len(assigned):
            return assigned[self._current_screen]
        return None

    async def async_show_view_index(self, index: int) -> None:
        """Show the assigned view at ``index`` now (leaves any built-in mode).

        The one path for an explicit choice of view, shared by the display
        select and the panel.
        """
        self.set_display_mode("custom", index)
        self.view_selection_serial += 1
        # Entities (the display select) reflect the choice now, not after
        # the debounced refresh renders it.
        self.async_update_listeners()
        await self.async_refresh_display()

    async def async_show_view(self, view_id: str) -> None:
        """Show an assigned view by id (names are ambiguous, ids are not)."""
        assigned = list(self.options.get(CONF_ASSIGNED_VIEWS, []))
        if view_id not in assigned:
            raise ValueError(f"View {view_id} is not assigned to this display")
        await self.async_show_view_index(assigned.index(view_id))

    async def async_next_screen(self) -> None:
        """Switch to the next screen."""
        if len(self._layouts) > 0:
            next_screen = (self._current_screen + 1) % len(self._layouts)
            await self.async_set_screen(next_screen)

    async def async_previous_screen(self) -> None:
        """Switch to the previous screen."""
        if len(self._layouts) > 0:
            prev_screen = (self._current_screen - 1) % len(self._layouts)
            await self.async_set_screen(prev_screen)

    def update_options(self, options: dict[str, Any]) -> None:
        """Update coordinator options.

        Args:
            options: New options dictionary
        """
        old_assigned_views = list(self.options.get(CONF_ASSIGNED_VIEWS, []))
        self.options = self._migrate_options(options)
        new_assigned_views = list(self.options.get(CONF_ASSIGNED_VIEWS, []))

        if new_assigned_views and new_assigned_views != old_assigned_views:
            _LOGGER.debug("Assigned views changed; switching device to custom render mode")
            self._display_mode = "custom"
            self._custom_display_requested = True
            shown = (
                old_assigned_views[self._current_screen]
                if 0 <= self._current_screen < len(old_assigned_views)
                else None
            )
            if shown in new_assigned_views:
                # Reordering (or adding around it) keeps the view on screen.
                self._current_screen = new_assigned_views.index(shown)
            else:
                self._current_screen = min(self._current_screen, len(new_assigned_views) - 1)
                self._last_screen_change = time.time()

        # Rebuild all screens, then derive the update interval from them
        self._setup_screens()
        self._apply_update_interval()

        # Config changed: fetch forecasts and pictures afresh on the next render
        get_forecast_cache(self.hass).invalidate()
        get_image_cache(self.hass).invalidate()
        self._invalidate_push()

    def _tick_interval(self) -> int:
        """Return the seconds between two updates.

        View Cycling is evaluated on each update, so it can never change
        views faster than updates run. A cycle interval shorter than the
        refresh interval therefore sets the update pace itself (issue
        #218); a longer one changes views on the first update after it
        has elapsed.
        """
        refresh = int(self.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL))
        cycle = int(self.options.get(CONF_SCREEN_CYCLE_INTERVAL, DEFAULT_SCREEN_CYCLE_INTERVAL))
        if 0 < cycle < refresh and len(self._layouts) > 1:
            return cycle
        return refresh

    def _apply_update_interval(self) -> None:
        """Set the update interval (and the backoff base) from the options."""
        self._base_update_interval = self._tick_interval()
        self.update_interval = timedelta(seconds=self._base_update_interval)

    def _build_widget_states(self, layout: Layout) -> dict[int, WidgetState]:
        """Build each widget's state from the gathered inputs (executor)."""
        return self._inputs.widget_states(layout)

    async def _async_gather_inputs(self, screen: int) -> None:
        """Gather everything a frame of ``screen`` reads, templates last."""
        await self._inputs.async_gather(self._frame_widgets(screen))

    def _frame_widgets(self, screen: int) -> list[Widget]:
        """The widgets a frame of ``screen`` can draw.

        The screen's own widgets, plus an active notification's picture:
        ``_render_display`` decides in the executor whether the
        notification still shows, so its inputs are gathered too.
        """
        widgets = layout_widgets(self._layouts[screen]) if 0 <= screen < len(self._layouts) else []
        if self._notification_data:
            notify_widget = self._notification_image_widget(self._notification_data)
            if notify_widget is not None:
                widgets.append(notify_widget)
        return widgets

    def _render_display(self, screen: int | None = None) -> tuple[bytes, bytes, str]:
        """Render the display image (runs in executor thread).

        Args:
            screen: Screen index to render, pinned by the caller in the
                event loop (defaults to the current screen).

        Returns:
            Tuple of (payload_bytes, png_preview, filename). The payload
            is a JPEG for still screens, or an animated GIF when the
            Animations switch is on and the current view contains
            animated widgets.
        """
        # Resolve the layout to render (current screen, notification
        # override, or the welcome screen).
        if screen is None:
            screen = self._current_screen
        if self._layouts and 0 <= screen < len(self._layouts):
            layout = self._layouts[screen]
            if time.time() < self._notification_expiry and self._notification_data:
                _LOGGER.debug("Rendering active notification")
                layout = self._create_notification_layout(self._notification_data)
        else:
            _LOGGER.debug("No screens configured, rendering welcome screen")
            layout = self._create_welcome_layout()

        _LOGGER.debug(
            "Rendering layout %s with %d widgets",
            type(layout).__name__,
            sum(1 for s in layout.slots if s.widget is not None),
        )
        widget_states = self._build_widget_states(layout)
        rotation = self.options.get(CONF_DISPLAY_ROTATION, DEFAULT_DISPLAY_ROTATION)

        # Animated path (opt-in): render CSS animations to a looping GIF.
        if (
            self.options.get(CONF_ENABLE_ANIMATIONS, DEFAULT_ENABLE_ANIMATIONS)
            and HAS_ENGINE
            and layout.has_animated_widgets()
        ):
            # The loop is the longest any animated widget asks for
            # (ambient animations want 2-4s; a short loop would visibly
            # jump). Frame count is capped to bound GIF size.
            requested = [
                slot.widget.animation_seconds()
                for slot in layout.slots
                if slot.widget is not None and slot.widget.is_animated()
            ]
            loop = max((s for s in requested if s), default=ANIMATION_SECONDS)
            loop = min(4.0, max(0.8, loop))
            # Slow ambient loops don't need full temporal resolution —
            # drop the rate so long loops stay within the size budget.
            fps = ANIMATION_FPS if loop <= 2.0 else 7
            frame_count = min(32, round(loop * fps))
            times = [i / fps for i in range(frame_count)]
            frames = layout.render_animation(self.renderer, widget_states, times)
            if frames:
                gif_data = self.renderer.to_gif(frames, fps=fps, rotation=rotation)
                png_data = self.renderer.to_png(frames[0], rotation=rotation)
                if len(gif_data) <= MAX_IMAGE_SIZE:
                    return gif_data, png_data, "dashboard.gif"
                # The frame cap bounds typical output but not the encoded
                # byte size — high-entropy content can still blow the
                # device's upload budget. Ship the first frame as a still
                # instead of an upload the device would reject.
                _LOGGER.warning(
                    "Animated GIF is %d bytes (budget %d); uploading a still frame instead",
                    len(gif_data),
                    MAX_IMAGE_SIZE,
                )
                jpeg_quality = self.options.get(CONF_JPEG_QUALITY, DEFAULT_JPEG_QUALITY)
                jpeg_data = self.renderer.to_jpeg(
                    frames[0], quality=jpeg_quality, rotation=rotation
                )
                return jpeg_data, png_data, "dashboard.jpg"
            _LOGGER.warning("Animated render failed; falling back to a still frame")

        img = render_still(self.renderer, layout, widget_states)

        jpeg_quality = self.options.get(CONF_JPEG_QUALITY, DEFAULT_JPEG_QUALITY)
        jpeg_data = self.renderer.to_jpeg(img, quality=jpeg_quality, rotation=rotation)
        png_data = self.renderer.to_png(img, rotation=rotation)

        return jpeg_data, png_data, "dashboard.jpg"

    async def trigger_notification(self, data: dict[str, Any]) -> None:
        """Trigger a notification on this device.

        Args:
            data: Notification data (message, title, icon, duration, etc.)
        """
        duration = data.get("duration", 10)
        self._notification_data = data
        self._notification_expiry = time.time() + duration
        self._invalidate_push()

        # A notification picture is often a fresh snapshot behind a fixed
        # URL: fetch it now rather than show a cached earlier one.
        notify_widget = self._notification_image_widget(data)
        if isinstance(notify_widget, ImageWidget) and notify_widget.source:
            get_image_cache(self.hass).invalidate(notify_widget.source)
        elif isinstance(notify_widget, CameraWidget) and notify_widget.config.entity_id:
            # An image entity is read afresh too (camera snapshots always are)
            get_image_cache(self.hass).invalidate_entity(notify_widget.config.entity_id)

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
        self._invalidate_push()
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

            hero_widget = self._notification_image_widget(data)

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
        hero_widget = self._notification_image_widget(data)

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

    @staticmethod
    def _notification_image_widget(data: dict[str, Any]) -> CameraWidget | ImageWidget | None:
        """The hero widget for a notification's picture, if it has one.

        ``image_url`` (a URL or local path) wins over ``image``; ``image``
        takes an entity, but a URL or path given there (YAML) works too.
        ``contain`` keeps the whole picture visible in the hero slot.
        """
        image_url = data.get("image_url")
        image = image_url or data.get("image")
        if not image or not isinstance(image, str):
            return None
        if image_url or is_image_source(image):
            return ImageWidget(
                WidgetConfig(
                    widget_type="image",
                    slot=0,
                    options={"source": image, "fit": "contain", "refresh": "1 min"},
                )
            )
        return CameraWidget(
            WidgetConfig(widget_type="camera", slot=0, entity_id=image, options={"fit": "contain"})
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data and update display.

        Implements exponential backoff when device is offline to reduce
        log spam and resource usage. When the device comes back online,
        the update interval is restored to normal.

        Returns:
            Dictionary with update status
        """
        # Listeners read this flag after every cycle; only a cycle that
        # renders new content raises it again below.
        self._preview_just_updated = False
        try:
            if self._paused:
                return {"success": True, "paused": True}

            # If device was offline, do a lightweight connectivity check first
            # to avoid expensive rendering operations
            if self._device_offline:
                try:
                    result = await self.device.test_connection()
                except Exception as conn_err:
                    if self._reboot_in_progress():
                        return self._rebooting_status(conn_err)
                    # test_connection itself failed - treat as still offline
                    self._consecutive_failures += 1
                    self._apply_backoff()
                    self._log_offline_status(str(conn_err))
                    raise UpdateFailed(f"Device offline: {conn_err}") from conn_err

                if not result.success:
                    if self._reboot_in_progress():
                        return self._rebooting_status(result.message)
                    # Still offline - update backoff and raise
                    self._consecutive_failures += 1
                    self._apply_backoff()
                    error_msg = result.message or "Connection failed"
                    self._log_offline_status(error_msg)
                    raise UpdateFailed(f"Device offline: {error_msg}")  # noqa: TRY301

                # Device is back online! (A reboot logs its own return
                # once the dashboard is pushed again.)
                _LOGGER.log(
                    logging.DEBUG if self._reboot_deadline is not None else logging.INFO,
                    "GeekMagic device %s is back online after %d failed attempts",
                    self.device.host,
                    self._consecutive_failures,
                )
                self._reset_backoff()
                # Whatever it shows after the outage, it is not ours to trust
                self._invalidate_push()

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
                if now - self._last_screen_change >= cycle_interval - CYCLE_DEADLINE_SLACK:
                    if self._display_mode == "builtin":
                        # A built-in mode is one stop of the rotation, not
                        # its end: View Cycling reads On, so once the
                        # built-in has had its interval the rotation moves
                        # on to the next view (issue #126).
                        _LOGGER.debug(
                            "Auto-cycling out of built-in mode (theme=%d)",
                            self._builtin_theme,
                        )
                        await self._async_leave_builtin_mode()
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

            # Fetch device state and storage info. A state read that succeeds
            # THIS cycle is also what proves the device is still reachable
            # when an unchanged frame is not re-uploaded.
            state_read = False
            try:
                self._device_state = await self.device.get_state()
                state_read = True
                self._space_info = await self.device.get_space()

                # Sync display mode with device state on first poll
                # If device is in a built-in theme, respect that
                if self._device_state and self._device_state.theme is not None:
                    device_theme = self._device_state.theme
                    if (
                        self.device.is_builtin_theme(device_theme)
                        and self._display_mode == "custom"
                        and not self._custom_display_requested
                    ):
                        # Device is in built-in mode but we thought we were in custom
                        # This can happen on startup - sync to device state
                        _LOGGER.debug(
                            "Syncing display mode from device: builtin (theme=%d)",
                            device_theme,
                        )
                        self._display_mode = "builtin"
                        self._builtin_theme = device_theme
                        self._invalidate_push()
            except Exception as e:
                _LOGGER.debug("Failed to fetch device state: %s", e)

            # Skip rendering when in built-in mode
            # The device handles display in built-in modes (Clock, Weather, System Info)
            if self._display_mode == "builtin":
                _LOGGER.debug(
                    "Skipping render - device in built-in mode (theme=%d)",
                    self._builtin_theme,
                )
                self._end_reboot_window()
                return {
                    "success": True,
                    "builtin_mode": True,
                    "theme": self._builtin_theme,
                }

            # Pin the screen in the loop: its inputs are gathered (templates
            # last, with no await after them) and the executor renders
            # exactly that screen.
            render_screen = self._current_screen
            await self._async_gather_inputs(render_screen)

            # Render image in executor to avoid blocking the event loop
            # (Pillow image operations are CPU-intensive)
            payload, png_data, filename = await self.hass.async_add_executor_job(
                self._render_display, render_screen
            )

            _LOGGER.debug(
                "Rendered %s: %d bytes (PNG preview %d bytes)",
                filename,
                len(payload),
                len(png_data),
            )

            uploaded = await self._async_push_frame(payload, filename, state_read)

            # The preview mirrors what the device shows, so it only takes a
            # render the device accepted, and only signals when the pixels
            # changed: renders are deterministic, so an unchanged screen
            # yields identical PNG bytes and causes no entity churn.
            if png_data != self._last_image:
                self._last_image = png_data
                self._preview_just_updated = True

            # Track success status
            self._last_update_success = True
            self._last_update_time = time.time()
            if uploaded:
                # Only a push proves the dashboard is back on screen.
                self._end_reboot_window()

            _LOGGER.debug(
                "Display update completed: screen=%s, size=%.1fKB",
                self.current_screen_name,
                len(payload) / 1024,
            )

            return {
                "success": True,
                "uploaded": uploaded,
                "size_kb": len(payload) / 1024,
                "current_screen": self._current_screen,
                "screen_name": self.current_screen_name,
            }

        except UpdateFailed:
            # Re-raise UpdateFailed without additional logging (already logged)
            self._last_update_success = False
            self._invalidate_push()
            raise
        except Exception as err:
            if self._reboot_in_progress():
                # Reached the device just before it went down, or just
                # after it came back but before it was ready: probe again.
                self._device_offline = True
                return self._rebooting_status(err)
            self._last_update_success = False
            self._invalidate_push()
            self._consecutive_failures += 1
            self._device_offline = True
            self._apply_backoff()
            self._log_connection_error(err)
            raise UpdateFailed(f"Error updating display: {err}") from err

    def _invalidate_push(self) -> None:
        """Make the next cycle push its frame even if it is unchanged."""
        self._last_push = None
        self._push_epoch += 1

    async def _async_push_frame(self, payload: bytes, filename: str, state_read: bool) -> bool:
        """Upload and display a frame unless the device already shows it.

        Every upload is a flash write on the device (issue #96), and renders
        are deterministic, so a frame byte-identical to the last successful
        push is skipped when all of these hold:

        - the push key matches: payload digest (rotation and quality are
          baked into the bytes), filename (JPEG vs GIF), Pro album
          management and the firmware profile, which decides where the
          frame is written and how it is selected;
        - that push is younger than FORCED_REPUSH_INTERVAL;
        - the device answered a state read this cycle (``state_read``), so
          a device that went offline is still caught by the push failing;
        - that state does not report a non-custom theme (a built-in mode
          picked on the device itself gets our frame back right away).

        Returns whether the frame was pushed. The record is cleared before
        the upload and set only after it succeeds, unless something
        invalidated it meanwhile.
        """
        manage_album = bool(self.options.get(CONF_MANAGE_PRO_ALBUM, False))
        key = (
            hashlib.blake2b(payload, digest_size=16).digest(),
            filename,
            manage_album,
            str(self.device.model),
        )
        last = self._last_push
        if (
            state_read
            and last is not None
            and last[0] == key
            and time.monotonic() - last[1] < FORCED_REPUSH_INTERVAL
            and not self._device_in_builtin_theme()
        ):
            _LOGGER.debug("Frame unchanged and still displayed; skipping upload")
            return False

        epoch = self._push_epoch
        self._last_push = None
        await self.device.display_rendered_dashboard(
            RenderedDashboardRequest(
                image_data=payload,
                filename=filename,
                allow_destructive_album_management=manage_album,
                try_menu_navigation=False,
            )
        )
        if epoch == self._push_epoch:
            self._last_push = (key, time.monotonic())
        return True

    def _device_in_builtin_theme(self) -> bool:
        """Return True when this cycle's device state reports a non-custom theme.

        The reported image is deliberately not compared with ours: the Pro
        shows uploads through its album without ever selecting them, and
        some firmware refuses ``/set?img=``, so that path need not name our
        file even while our frame is on screen. Firmware that reports no
        theme gives no evidence either way; only the forced re-push
        interval protects it.
        """
        state = self._device_state
        return (
            state is not None
            and state.theme is not None
            and not self.device.is_custom_theme(state.theme)
        )

    async def async_reboot(self) -> None:
        """Reboot the device and ride out the outage it causes.

        The next cycles only probe the device (no render into a device that
        is restarting), without backing off or warning, until it answers
        and takes a full push again, which restores the dashboard. A device
        still gone after ``REBOOT_GRACE_SECONDS`` is handled as offline.
        """
        # Open the window first: a cycle running during the request may
        # already hit the restarting device.
        self._reboot_deadline = time.monotonic() + REBOOT_GRACE_SECONDS
        try:
            await self.device.reboot()
        except Exception as err:
            self._reboot_deadline = None
            raise HomeAssistantError(
                f"Could not reboot GeekMagic device {self.device.host}: {err}"
            ) from err

        _LOGGER.info("Rebooting GeekMagic device %s", self.device.host)
        # The device took the request, so backoff from earlier failures is
        # stale. The refresh already scheduled still fires on its old
        # timer; the base interval applies from the one after it.
        self._reset_backoff()
        self._device_offline = True
        # The device reboots into whatever its firmware shows first, so an
        # unchanged frame must still be uploaded once it is back.
        self._invalidate_push()
        # Firmware may boot into a built-in mode. While rendering, that
        # must not read as the user switching to it on the device.
        if self._display_mode == "custom":
            self._custom_display_requested = True

    def _reboot_in_progress(self) -> bool:
        """Return whether a failure belongs to the outage of a requested reboot."""
        if self._reboot_deadline is None:
            return False
        if time.monotonic() < self._reboot_deadline:
            return True
        _LOGGER.debug(
            "GeekMagic device %s did not return within the reboot window", self.device.host
        )
        self._reboot_deadline = None
        return False

    def _end_reboot_window(self) -> None:
        """Close the reboot window once a full cycle reached the device."""
        if self._reboot_deadline is not None:
            _LOGGER.info("GeekMagic device %s is back after reboot", self.device.host)
            self._reboot_deadline = None

    def _rebooting_status(self, reason: object) -> dict[str, Any]:
        """Log a failure expected while the device reboots and report it."""
        _LOGGER.debug("GeekMagic device %s still rebooting: %s", self.device.host, reason)
        # Like any failed cycle: what the device shows next is not ours.
        self._invalidate_push()
        return {"success": False, "rebooting": True}

    def _apply_backoff(self) -> None:
        """Apply exponential backoff to update interval.

        Increases the update interval based on consecutive failures,
        capped at MAX_BACKOFF_MULTIPLIER times the base interval.
        """
        # Calculate backoff: 1, 2, 4, 8, ... up to MAX_BACKOFF_MULTIPLIER
        multiplier = min(2 ** min(self._consecutive_failures, 10), MAX_BACKOFF_MULTIPLIER)
        new_interval = self._base_update_interval * multiplier
        self.update_interval = timedelta(seconds=new_interval)
        _LOGGER.debug(
            "Applied backoff: interval=%ds (multiplier=%dx, failures=%d)",
            new_interval,
            multiplier,
            self._consecutive_failures,
        )

    def _reset_backoff(self) -> None:
        """Reset backoff state after successful connection."""
        self._consecutive_failures = 0
        self._device_offline = False
        self.update_interval = timedelta(seconds=self._base_update_interval)

    def _log_offline_status(self, message: str) -> None:
        """Log device offline status with smart verbosity.

        Logs at warning level on first failure and periodically,
        debug level otherwise to reduce log spam.

        Args:
            message: Error message to include
        """
        if self._consecutive_failures == 1:
            # First failure - log at warning level with full details
            _LOGGER.warning(
                "GeekMagic device %s is offline: %s. Will retry with exponential backoff.",
                self.device.host,
                message,
            )
        elif self._consecutive_failures % BACKOFF_LOG_INTERVAL == 0:
            # Periodic summary - log at warning level
            interval = (
                int(self.update_interval.total_seconds())
                if self.update_interval
                else self._base_update_interval
            )
            _LOGGER.warning(
                "GeekMagic device %s still offline after %d attempts (retry interval: %ds)",
                self.device.host,
                self._consecutive_failures,
                interval,
            )
        else:
            # Subsequent failures - log at debug level only
            _LOGGER.debug(
                "GeekMagic device %s offline (attempt %d): %s",
                self.device.host,
                self._consecutive_failures,
                message,
            )

    def _log_connection_error(self, err: Exception) -> None:
        """Log connection error with smart verbosity.

        Logs full exception on first failure and periodically,
        abbreviated message otherwise to reduce log spam.

        Args:
            err: The exception that occurred
        """
        if self._consecutive_failures == 1:
            # First failure - log at warning level with exception info
            _LOGGER.warning(
                "GeekMagic device %s connection failed: %s. Will retry with exponential backoff.",
                self.device.host,
                err,
            )
        elif self._consecutive_failures % BACKOFF_LOG_INTERVAL == 0:
            # Periodic summary - log at warning level
            interval = (
                int(self.update_interval.total_seconds())
                if self.update_interval
                else self._base_update_interval
            )
            _LOGGER.warning(
                "GeekMagic device %s still failing after %d attempts: %s (retry interval: %ds)",
                self.device.host,
                self._consecutive_failures,
                err,
                interval,
            )
        else:
            # Subsequent failures - log at debug level only
            _LOGGER.debug(
                "GeekMagic update failed (attempt %d): %s",
                self._consecutive_failures,
                err,
            )

    @property
    def last_image(self) -> bytes | None:
        """Get the last rendered image as PNG bytes."""
        return self._last_image

    @property
    def preview_just_updated(self) -> bool:
        """Check if the last refresh cycle rendered a new preview image."""
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
        return self.device.firmware_version

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
    def device_brightness_percent(self) -> int | None:
        """Get device brightness as a 0-100 percentage of the firmware range."""
        if self._device_brightness is None:
            return None
        return brightness_to_percent(self._device_brightness, self._brightness_range)

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
        """Get current builtin theme number when in builtin mode."""
        return self._builtin_theme

    def set_display_mode(self, mode: str, value: int = 0) -> None:
        """Set display mode.

        Args:
            mode: Either 'custom' or 'builtin'
            value: For 'custom', the view index. For 'builtin', the theme number.
        """
        self._display_mode = mode
        self._invalidate_push()
        if mode == "builtin":
            self._builtin_theme = value
            self._custom_display_requested = False
            # The built-in gets a full cycle interval before View Cycling
            # moves on, not whatever was left of the previous view's.
            self._last_screen_change = time.time()
        else:
            # Custom mode - value is view index
            self._current_screen = value
            self._last_screen_change = time.time()
            self._custom_display_requested = True

    async def async_set_brightness(self, brightness: float) -> None:
        """Set display brightness.

        Args:
            brightness: Brightness percentage 0-100, scaled up on firmware whose
                range goes past 100 (see ``brightness_from_percent``)
        """
        raw = brightness_from_percent(brightness, self._brightness_range)
        await self.device.set_brightness(raw)
        self._device_brightness = raw

    @property
    def _brightness_range(self) -> tuple[int, int]:
        """Raw brightness range accepted by the firmware."""
        try:
            low, high = self.device.capabilities.brightness_range
            return int(low), int(high)
        except (AttributeError, TypeError, ValueError):
            return 0, 100

    @property
    def _brightness_floor(self) -> int:
        """Lowest brightness the firmware accepts (screen effectively dark)."""
        return self._brightness_range[0]

    @property
    def _resume_heal_brightness(self) -> int:
        """Raw brightness applied by the resume fallback, clamped to the firmware max."""
        return min(DEFAULT_RESUME_BRIGHTNESS, self._brightness_range[1])

    async def async_set_active(self, active: bool) -> None:
        """Pause or resume the render/upload cycle.

        When paused: stores current brightness, dims screen to 0, and skips
        all rendering and uploading until resumed. Intended for presence-based
        automation (turn off when room is empty).

        When resumed: restores brightness and triggers an immediate refresh.
        If the pause state was restored after an HA restart (which wipes the
        remembered pre-pause brightness), falls back to
        DEFAULT_RESUME_BRIGHTNESS so the display never stays dark while
        reporting itself active.

        Args:
            active: True to resume, False to pause/sleep
        """
        if active:
            self._paused = False
            self._invalidate_push()
            restore = self._pre_pause_brightness
            self._pre_pause_brightness = None
            if restore is None and self._needs_resume_heal:
                current = self._device_brightness
                if current is None or current <= self._brightness_floor:
                    restore = self._resume_heal_brightness
            self._needs_resume_heal = False
            if restore is not None:
                await self.device.set_brightness(restore)
                self._device_brightness = restore
            _LOGGER.debug("Display activated, triggering refresh")
            await self.async_request_refresh()
        else:
            if not self._paused:
                current = self._device_brightness
                # Only remember a brightness the screen was actually visible
                # at; a floor-level reading is either our own dimmed state or
                # already the lowest the firmware allows, so resuming without
                # a stored value simply leaves it untouched.
                if current is not None and current > self._brightness_floor:
                    self._pre_pause_brightness = current
            await self.device.set_brightness(0)
            self._device_brightness = self._brightness_floor
            self._paused = True
            _LOGGER.debug("Display paused (pre-pause brightness: %s)", self._pre_pause_brightness)
            # Out-of-cycle notification: the preview has not changed, so
            # clear the flag left over from the last render first.
            self._preview_just_updated = False
            self.async_update_listeners()

    async def _async_dim_restored_display(self) -> None:
        """Best-effort dim of a display whose paused state was just restored."""
        try:
            await self.device.set_brightness(0)
            self._device_brightness = self._brightness_floor
        except Exception as err:
            _LOGGER.debug("Could not dim display while restoring paused state: %s", err)

    @callback
    def async_restore_paused(self) -> None:
        """Re-enter the paused state after a Home Assistant restart.

        Called by the Active switch when it restores an "off" state. The
        pre-restart brightness is unknown, so the next resume is flagged to
        fall back to DEFAULT_RESUME_BRIGHTNESS. The dim runs as a background
        task so entity setup never blocks on an unreachable device.
        """
        self._paused = True
        self._needs_resume_heal = True
        self.hass.async_create_task(self._async_dim_restored_display())
        self._preview_just_updated = False  # Out-of-cycle: the preview has not changed
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
        self._custom_display_requested = True
        # A manual refresh always re-pushes the frame, even if the theme
        # switch below fails
        self._invalidate_push()

        # Ensure device is in custom image mode
        await self.device.set_theme_custom()

        # A manual refresh bypasses the forecast and picture caches
        get_forecast_cache(self.hass).invalidate()
        get_image_cache(self.hass).invalidate()
        await self.async_request_refresh()

    async def async_reload_views(self) -> None:
        """Reload views from store and refresh display.

        Call this when a global view's content has been updated.
        """
        self._setup_screens()
        if self.options.get(CONF_ASSIGNED_VIEWS):
            self._display_mode = "custom"
            self._custom_display_requested = True
        self._invalidate_push()
        await self.async_request_refresh()
