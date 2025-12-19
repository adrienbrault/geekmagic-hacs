"""Data update coordinator for GeekMagic integration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_LIME,
    COLOR_WHITE,
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREEN_CYCLE_INTERVAL,
    CONF_SCREEN_THEME,
    CONF_SCREENS,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SCREEN_CYCLE_INTERVAL,
    DOMAIN,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_GRID_3X2,
    LAYOUT_GRID_3X3,
    LAYOUT_HERO,
    LAYOUT_HERO_BL,
    LAYOUT_HERO_BR,
    LAYOUT_HERO_TL,
    LAYOUT_HERO_TR,
    LAYOUT_SIDEBAR_LEFT,
    LAYOUT_SIDEBAR_RIGHT,
    LAYOUT_SPLIT_H,
    LAYOUT_SPLIT_H_1_2,
    LAYOUT_SPLIT_H_2_1,
    LAYOUT_SPLIT_V,
    LAYOUT_THREE_COLUMN,
    LAYOUT_THREE_ROW,
    THEME_CLASSIC,
)
from .device import DeviceState, GeekMagicDevice, SpaceInfo
from .layouts.corner_hero import HeroCornerBL, HeroCornerBR, HeroCornerTL, HeroCornerTR
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from .layouts.hero import HeroLayout
from .layouts.sidebar import SidebarLeft, SidebarRight
from .layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from .renderer import Renderer
from .widgets.base import WidgetConfig
from .widgets.camera import CameraWidget
from .widgets.chart import ChartWidget
from .widgets.clock import ClockWidget
from .widgets.entity import EntityWidget
from .widgets.fullscreen import FullscreenWidget
from .widgets.gauge import GaugeWidget
from .widgets.media import MediaWidget
from .widgets.progress import MultiProgressWidget, ProgressWidget
from .widgets.status import StatusListWidget, StatusWidget
from .widgets.text import TextWidget
from .widgets.theme import get_theme
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from .layouts.base import Layout
    from .store import GeekMagicStore

_LOGGER = logging.getLogger(__name__)

# Config key for new global views format
CONF_ASSIGNED_VIEWS = "assigned_views"

LAYOUT_CLASSES = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_GRID_3X3: Grid3x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT_H: SplitHorizontal,
    LAYOUT_SPLIT_H_1_2: SplitHorizontal1To2,
    LAYOUT_SPLIT_H_2_1: SplitHorizontal2To1,
    LAYOUT_SPLIT_V: SplitVertical,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
    LAYOUT_THREE_ROW: ThreeRowLayout,
    LAYOUT_SIDEBAR_LEFT: SidebarLeft,
    LAYOUT_SIDEBAR_RIGHT: SidebarRight,
    LAYOUT_HERO_TL: HeroCornerTL,
    LAYOUT_HERO_TR: HeroCornerTR,
    LAYOUT_HERO_BL: HeroCornerBL,
    LAYOUT_HERO_BR: HeroCornerBR,
}

WIDGET_CLASSES = {
    "camera": CameraWidget,
    "clock": ClockWidget,
    "entity": EntityWidget,
    "fullscreen": FullscreenWidget,
    "media": MediaWidget,
    "chart": ChartWidget,
    "text": TextWidget,
    "gauge": GaugeWidget,
    "progress": ProgressWidget,
    "multi_progress": MultiProgressWidget,
    "status": StatusWidget,
    "status_list": StatusListWidget,
    "weather": WeatherWidget,
}


# Binary states that should be converted to 1.0 (on/true)
BINARY_ON_STATES = frozenset({"on", "true", "open", "home", "unlocked", "playing", "active"})
# Binary states that should be converted to 0.0 (off/false)
BINARY_OFF_STATES = frozenset(
    {"off", "false", "closed", "not_home", "locked", "paused", "idle", "standby"}
)


def extract_numeric_values(history_states: list) -> list[float]:
    """Extract numeric values from recorder history states.

    Handles both State objects (with .state attribute) and
    dictionaries (from minimal_response=True format).

    Also converts binary states (on/off, open/closed, etc.) to 1.0/0.0
    for charting binary_sensor entities.

    Args:
        history_states: List of State objects or dicts from recorder

    Returns:
        List of numeric float values, non-numeric states are skipped
    """
    values: list[float] = []
    for state in history_states:
        try:
            # Handle both State objects and minimal_response dicts
            state_value = state.state if hasattr(state, "state") else state.get("state")
            if state_value is None:
                continue

            # Try numeric conversion first
            try:
                values.append(float(state_value))
            except (ValueError, TypeError):
                # Check for binary states
                state_lower = str(state_value).lower()
                if state_lower in BINARY_ON_STATES:
                    values.append(1.0)
                elif state_lower in BINARY_OFF_STATES:
                    values.append(0.0)
                # Skip other non-numeric states (unavailable, unknown, etc.)
        except AttributeError:
            continue
    return values


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
        self._camera_images: dict[str, bytes] = {}  # Pre-fetched camera images
        self._update_preview: bool = True  # Update preview on next refresh
        self._preview_just_updated: bool = False  # True if preview was updated in last refresh

        # Device state (updated on refresh)
        self._device_state: DeviceState | None = None
        self._space_info: SpaceInfo | None = None
        self._device_brightness: int | None = None
        self._last_brightness_poll: float = 0  # Timestamp of last brightness poll
        self._brightness_poll_interval: float = 600  # 10 minutes

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
            layout = self._create_layout(view_config)
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
            layout = self._create_layout(screen_config)
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

        # Hero: Clock widget showing current time
        clock = ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=0,
                color=COLOR_WHITE,
                options={"show_date": True, "show_seconds": False},
            )
        )
        layout.set_widget(0, clock)

        # Footer slot 1: HA version
        ha_version = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=1,
                label="HA",
                color=COLOR_CYAN,
                options={
                    "text": self._get_ha_version(),
                    "size": "small",
                    "align": "center",
                },
            )
        )
        layout.set_widget(1, ha_version)

        # Footer slot 2: Entity count
        entity_count = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=2,
                label="Entities",
                color=COLOR_LIME,
                options={
                    "text": str(self._get_entity_count()),
                    "size": "small",
                    "align": "center",
                },
            )
        )
        layout.set_widget(2, entity_count)

        # Footer slot 3: Setup hint
        setup_hint = TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=3,
                color=COLOR_GRAY,
                options={
                    "text": "Configure →",
                    "size": "small",
                    "align": "center",
                },
            )
        )
        layout.set_widget(3, setup_hint)

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

    def _create_layout(self, screen_config: dict[str, Any]):
        """Create a layout from screen configuration.

        Args:
            screen_config: Screen configuration dictionary

        Returns:
            Configured layout instance
        """
        layout_type = screen_config.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
        layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)
        layout = layout_class()

        # Set theme on layout
        theme_name = screen_config.get(CONF_SCREEN_THEME, THEME_CLASSIC)
        layout.theme = get_theme(theme_name)

        widgets_config = screen_config.get(CONF_WIDGETS, [])

        # If no widgets configured, add default clock widget
        if not widgets_config:
            widgets_config = [{"type": "clock", "slot": 0}]

        for widget_config in widgets_config:
            widget_type = str(widget_config.get("type", "text"))
            slot = int(widget_config.get("slot", 0))

            if slot >= layout.get_slot_count():
                continue

            widget_class = WIDGET_CLASSES.get(widget_type)
            if widget_class is None:
                continue

            entity_id = widget_config.get("entity_id")
            label = widget_config.get("label")
            raw_color = widget_config.get("color")
            widget_options = widget_config.get("options") or {}

            # Parse color - can be tuple/list of RGB values
            parsed_color: tuple[int, int, int] | None = None
            if isinstance(raw_color, list | tuple) and len(raw_color) == 3:
                parsed_color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))

            config = WidgetConfig(
                widget_type=widget_type,
                slot=slot,
                entity_id=str(entity_id) if entity_id is not None else None,
                label=str(label) if label is not None else None,
                color=parsed_color,
                options=cast("dict[str, Any]", widget_options),
            )

            widget = widget_class(config)
            layout.set_widget(slot, widget)

        return layout

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
            await self.async_request_refresh()

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
        self.options = self._migrate_options(options)

        # Update refresh interval
        interval = self.options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        self.update_interval = timedelta(seconds=interval)

        # Rebuild all screens
        self._setup_screens()

        # Update preview on next refresh (config changed)
        self._update_preview = True

    def _render_display(self) -> tuple[bytes, bytes]:
        """Render the display image (runs in executor thread).

        Returns:
            Tuple of (jpeg_data, png_data)
        """
        # Create canvas
        img, draw = self.renderer.create_canvas()

        # Render current screen's layout
        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            _LOGGER.debug(
                "Rendering layout %s with %d widgets",
                type(layout).__name__,
                sum(1 for s in layout.slots if s.widget is not None),
            )
            layout.render(self.renderer, draw, self.hass)
        else:
            # No screens configured - show welcome screen with live data
            _LOGGER.debug("No screens configured, rendering welcome screen")
            # Recreate welcome layout each time to get fresh HA stats
            welcome_layout = self._create_welcome_layout()
            welcome_layout.render(self.renderer, draw, self.hass)

        # Encode to both formats
        jpeg_data = self.renderer.to_jpeg(img)
        png_data = self.renderer.to_png(img)

        return jpeg_data, png_data

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data and update display.

        Returns:
            Dictionary with update status
        """
        try:
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
            except Exception as e:
                _LOGGER.debug("Failed to fetch device state: %s", e)

            # Pre-fetch camera images and chart history (must be done in async context)
            await self._async_fetch_camera_images()
            await self._async_fetch_chart_history()

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

        except Exception as err:
            self._last_update_success = False
            _LOGGER.exception("Error updating GeekMagic display")
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
    def space_info(self) -> SpaceInfo | None:
        """Get device storage info."""
        return self._space_info

    def get_store(self) -> GeekMagicStore | None:
        """Get global views store."""
        return self._get_store()

    def set_current_screen(self, index: int) -> None:
        """Set current screen index."""
        self._current_screen = index

    async def async_set_brightness(self, brightness: int) -> None:
        """Set display brightness.

        Args:
            brightness: Brightness level 0-100
        """
        await self.device.set_brightness(brightness)

    async def async_refresh_display(self) -> None:
        """Force an immediate display refresh."""
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

        # Find all camera widgets in current layout
        camera_entity_ids: set[str] = set()

        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            for slot in layout.slots:
                if slot.widget and isinstance(slot.widget, CameraWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        camera_entity_ids.add(entity_id)

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

    def get_camera_image(self, entity_id: str) -> bytes | None:
        """Get pre-fetched camera image.

        Args:
            entity_id: Camera entity ID

        Returns:
            Image bytes or None if not available
        """
        return self._camera_images.get(entity_id)

    def _fetch_entity_history(self, entity_id: str, start: datetime, end: datetime) -> list:
        """Fetch history for an entity (sync, runs in executor).

        Uses keyword arguments for state_changes_during_period since
        async_add_executor_job passes positional args and the function
        has many optional parameters with defaults.

        Args:
            entity_id: Entity ID to fetch history for
            start: Start time (datetime)
            end: End time (datetime)

        Returns:
            List of State objects for the entity
        """
        from homeassistant.components.recorder import history

        # state_changes_during_period returns dict[entity_id, list[State]]
        # We need keyword arguments here since the function has many optional params
        result = history.state_changes_during_period(
            self.hass,
            start,
            end,
            entity_id,
            include_start_time_state=True,
            no_attributes=True,
        )
        return result.get(entity_id, [])

    async def _async_fetch_chart_history(self) -> None:
        """Pre-fetch history data for all chart widgets.

        This must be called from the async context before rendering,
        since recorder queries are async.
        """
        # Find all chart widgets in current layout
        chart_widgets: list[tuple[str, ChartWidget]] = []

        if self._layouts and 0 <= self._current_screen < len(self._layouts):
            layout = self._layouts[self._current_screen]
            for slot in layout.slots:
                if slot.widget and isinstance(slot.widget, ChartWidget):
                    entity_id = slot.widget.config.entity_id
                    if entity_id:
                        chart_widgets.append((entity_id, slot.widget))

        if not chart_widgets:
            return

        # Get recorder instance
        try:
            from homeassistant.components.recorder import get_instance
        except ImportError:
            _LOGGER.debug("Recorder not available, charts will show no data")
            return

        # get_instance() raises KeyError if recorder not available
        try:
            recorder = get_instance(self.hass)
        except KeyError:
            _LOGGER.debug("Recorder instance not available")
            return

        now = dt_util.utcnow()

        for entity_id, widget in chart_widgets:
            try:
                hours = widget.hours
                start_time = now - timedelta(hours=hours)

                # Use wrapper method to fetch history with keyword arguments
                # (async_add_executor_job only supports positional args, but
                # state_changes_during_period needs keyword args for its many optional params)
                history_states = await recorder.async_add_executor_job(
                    self._fetch_entity_history,
                    entity_id,
                    start_time,
                    now,
                )

                if history_states:
                    values = extract_numeric_values(history_states)

                    if values:
                        widget.set_history(values)
                        _LOGGER.debug(
                            "Fetched %d history points for %s",
                            len(values),
                            entity_id,
                        )
                    else:
                        _LOGGER.debug(
                            "No numeric values in history for %s",
                            entity_id,
                        )
                else:
                    _LOGGER.debug("No history returned for %s", entity_id)
            except Exception as e:
                _LOGGER.warning("Failed to fetch history for %s: %s", entity_id, e)
