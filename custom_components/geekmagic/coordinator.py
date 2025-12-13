"""Data update coordinator for GeekMagic integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
    LAYOUT_HERO,
    LAYOUT_SPLIT,
    LAYOUT_THREE_COLUMN,
    THEME_CLASSIC,
)
from .device import GeekMagicDevice
from .layouts.grid import Grid2x2, Grid2x3, Grid3x2
from .layouts.hero import HeroLayout
from .layouts.split import SplitLayout, ThreeColumnLayout
from .renderer import Renderer
from .widgets.base import WidgetConfig
from .widgets.camera import CameraWidget
from .widgets.chart import ChartWidget
from .widgets.clock import ClockWidget
from .widgets.entity import EntityWidget
from .widgets.gauge import GaugeWidget
from .widgets.media import MediaWidget
from .widgets.progress import MultiProgressWidget, ProgressWidget
from .widgets.status import StatusListWidget, StatusWidget
from .widgets.text import TextWidget
from .widgets.theme import get_theme
from .widgets.weather import WeatherWidget

if TYPE_CHECKING:
    from .layouts.base import Layout

_LOGGER = logging.getLogger(__name__)

LAYOUT_CLASSES = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_GRID_3X2: Grid3x2,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT: SplitLayout,
    LAYOUT_THREE_COLUMN: ThreeColumnLayout,
}

WIDGET_CLASSES = {
    "camera": CameraWidget,
    "clock": ClockWidget,
    "entity": EntityWidget,
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
        """Set up all screens with their layouts and widgets."""
        self._layouts = []
        screens = self.options.get(CONF_SCREENS, [])

        _LOGGER.debug("Setting up %d screen(s)", len(screens))

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

        # Ensure current screen is valid
        if self._current_screen >= len(self._layouts):
            _LOGGER.debug(
                "Current screen %d out of range, resetting to 0",
                self._current_screen,
            )
            self._current_screen = 0

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

            # Pre-fetch camera images (must be done in async context)
            await self._async_fetch_camera_images()

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
