"""Data update coordinator for GeekMagic integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_REFRESH_INTERVAL,
    CONF_LAYOUT,
    CONF_WIDGETS,
    DEFAULT_REFRESH_INTERVAL,
    LAYOUT_GRID_2X2,
    LAYOUT_GRID_2X3,
    LAYOUT_HERO,
    LAYOUT_SPLIT,
)
from .device import GeekMagicDevice
from .renderer import Renderer
from .layouts.grid import Grid2x2, Grid2x3
from .layouts.hero import HeroLayout
from .layouts.split import SplitLayout
from .widgets.base import WidgetConfig
from .widgets.clock import ClockWidget
from .widgets.entity import EntityWidget
from .widgets.media import MediaWidget
from .widgets.chart import ChartWidget
from .widgets.text import TextWidget

_LOGGER = logging.getLogger(__name__)

LAYOUT_CLASSES = {
    LAYOUT_GRID_2X2: Grid2x2,
    LAYOUT_GRID_2X3: Grid2x3,
    LAYOUT_HERO: HeroLayout,
    LAYOUT_SPLIT: SplitLayout,
}

WIDGET_CLASSES = {
    "clock": ClockWidget,
    "entity": EntityWidget,
    "media": MediaWidget,
    "chart": ChartWidget,
    "text": TextWidget,
}


class GeekMagicCoordinator(DataUpdateCoordinator):
    """Coordinator for GeekMagic display updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: GeekMagicDevice,
        options: dict[str, Any],
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            device: GeekMagic device client
            options: Integration options
        """
        self.device = device
        self.options = options
        self.renderer = Renderer()
        self._layout = None
        self._widgets_config: list[dict] = []

        # Get refresh interval from options
        interval = options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

        # Initialize layout and widgets
        self._setup_layout()

    def _setup_layout(self) -> None:
        """Set up the layout and widgets based on configuration."""
        layout_type = self.options.get(CONF_LAYOUT, LAYOUT_GRID_2X2)
        layout_class = LAYOUT_CLASSES.get(layout_type, Grid2x2)
        self._layout = layout_class()

        # Get widget configuration
        widgets_config = self.options.get(CONF_WIDGETS, [])

        # If no widgets configured, add default clock widget
        if not widgets_config:
            widgets_config = [
                {"type": "clock", "slot": 0},
            ]

        # Create and assign widgets
        for widget_config in widgets_config:
            widget_type = widget_config.get("type", "text")
            slot = widget_config.get("slot", 0)

            if slot >= self._layout.get_slot_count():
                continue

            widget_class = WIDGET_CLASSES.get(widget_type)
            if widget_class is None:
                continue

            config = WidgetConfig(
                widget_type=widget_type,
                slot=slot,
                entity_id=widget_config.get("entity_id"),
                label=widget_config.get("label"),
                color=widget_config.get("color"),
                options=widget_config.get("options", {}),
            )

            widget = widget_class(config)
            self._layout.set_widget(slot, widget)

        self._widgets_config = widgets_config

    def update_options(self, options: dict[str, Any]) -> None:
        """Update coordinator options.

        Args:
            options: New options dictionary
        """
        self.options = options

        # Update refresh interval
        interval = options.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        self.update_interval = timedelta(seconds=interval)

        # Rebuild layout
        self._setup_layout()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data and update display.

        Returns:
            Dictionary with update status
        """
        try:
            # Create canvas
            img, draw = self.renderer.create_canvas()

            # Render layout with all widgets
            if self._layout:
                self._layout.render(self.renderer, draw, self.hass)

            # Convert to JPEG and upload
            jpeg_data = self.renderer.to_jpeg(img)
            await self.device.upload_and_display(jpeg_data, "dashboard.jpg")

            return {
                "success": True,
                "size_kb": len(jpeg_data) / 1024,
            }

        except Exception as err:
            _LOGGER.error("Error updating GeekMagic display: %s", err)
            raise UpdateFailed(f"Error updating display: {err}") from err

    async def async_set_brightness(self, brightness: int) -> None:
        """Set display brightness.

        Args:
            brightness: Brightness level 0-100
        """
        await self.device.set_brightness(brightness)

    async def async_refresh_display(self) -> None:
        """Force an immediate display refresh."""
        await self.async_request_refresh()
