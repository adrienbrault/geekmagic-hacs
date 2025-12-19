"""Fullscreen widget for GeekMagic displays.

Displays a single image that fills the entire widget area.
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from PIL import Image

from ..const import COLOR_GRAY, DOMAIN
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext

_LOGGER = logging.getLogger(__name__)


class FullscreenWidget(Widget):
    """Widget that displays an image in fullscreen mode.

    This widget is designed to fill the entire display with a single image,
    ideal for displaying artwork, photos, or custom graphics.

    Options:
        image_url: URL of the image to display
        image_path: Local file path to the image (on HA server)
        fit: How to fit image - "contain" (letterbox), "cover" (crop to fill),
             or "stretch" (distort to fill). Default: "cover"
        background: Background color for letterboxing (default: black)
    """

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the fullscreen widget.

        Args:
            config: Widget configuration
        """
        super().__init__(config)
        self.image_url = config.options.get("image_url")
        self.image_path = config.options.get("image_path")
        self.fit = config.options.get("fit", "cover")
        self.background = config.options.get("background")  # RGB tuple or None
        self._cached_image: Image.Image | None = None
        self._last_source: str | None = None

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the fullscreen widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Try to load the image from configured source
        image = self._get_image(hass)

        if image is None:
            self._render_placeholder(ctx)
            return

        # Draw background if using contain mode with letterboxing
        if self.background and self.fit == "contain":
            bg = self.background
            bg_color = tuple(bg) if isinstance(bg, list) else bg
            ctx.draw_rect((0, 0, ctx.width, ctx.height), fill=bg_color)

        # Draw the image to fill the widget area
        ctx.draw_image(image, fit_mode=self.fit)

    def _get_image(self, hass: HomeAssistant | None) -> Image.Image | None:
        """Get image from configured source.

        Priority:
        1. Entity with entity_picture attribute
        2. image_url option
        3. image_path option

        Args:
            hass: Home Assistant instance

        Returns:
            PIL Image or None if not available
        """
        # Check entity for entity_picture first
        if self.config.entity_id and hass:
            state = hass.states.get(self.config.entity_id)
            if state:
                entity_picture = state.attributes.get("entity_picture")
                if entity_picture:
                    return self._load_from_url(entity_picture, hass)

        # Try image URL
        if self.image_url:
            source_key = f"url:{self.image_url}"
            if source_key != self._last_source:
                self._cached_image = self._load_from_url(self.image_url, hass)
                self._last_source = source_key
            return self._cached_image

        # Try local file path
        if self.image_path:
            source_key = f"path:{self.image_path}"
            if source_key != self._last_source:
                self._cached_image = self._load_from_file(self.image_path)
                self._last_source = source_key
            return self._cached_image

        return self._cached_image

    def _load_from_url(self, url: str, hass: HomeAssistant | None) -> Image.Image | None:
        """Load image from URL.

        Args:
            url: Image URL (can be relative for HA internal URLs)
            hass: Home Assistant instance

        Returns:
            PIL Image or None if failed
        """
        # For relative URLs, we need to handle them specially
        parsed = urlparse(url)
        if not parsed.scheme:
            # Relative URL - this would need HA's internal API
            # For now, skip relative URLs as they're handled async
            _LOGGER.debug("Relative URLs not supported in sync context: %s", url)
            return None

        # Try to fetch from cache if coordinator has it
        if hass:
            for coordinator in hass.data.get(DOMAIN, {}).values():
                if hasattr(coordinator, "get_fullscreen_image"):
                    try:
                        image_bytes = coordinator.get_fullscreen_image(url)
                        if image_bytes:
                            img = Image.open(BytesIO(image_bytes))
                            return img.convert("RGB")
                    except Exception as e:
                        _LOGGER.debug("Error loading image from cache: %s", e)

        _LOGGER.debug("Image URL will be fetched async: %s", url)
        return None

    def _load_from_file(self, path: str) -> Image.Image | None:
        """Load image from local file path.

        Args:
            path: File path on HA server

        Returns:
            PIL Image or None if failed
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                _LOGGER.debug("Image file not found: %s", path)
                return None

            if not file_path.is_file():
                _LOGGER.debug("Path is not a file: %s", path)
                return None

            # Validate it's an image file
            valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            if file_path.suffix.lower() not in valid_extensions:
                _LOGGER.debug("Unsupported image format: %s", path)
                return None

            img = Image.open(file_path)
            return img.convert("RGB")

        except Exception as e:
            _LOGGER.debug("Error loading image from file %s: %s", path, e)
            return None

    def _render_placeholder(self, ctx: RenderContext) -> None:
        """Render placeholder when no image is available.

        Args:
            ctx: RenderContext for drawing
        """
        center_x = ctx.width // 2
        center_y = ctx.height // 2

        # Draw image icon placeholder
        icon_size = min(ctx.width, ctx.height) // 3
        half = icon_size // 2

        # Image frame
        frame_rect = (
            center_x - half,
            center_y - half,
            center_x + half,
            center_y + half,
        )
        ctx.draw_rounded_rect(frame_rect, radius=4, outline=COLOR_GRAY, width=2)

        # Mountain/sun icon inside (simple image representation)
        # Sun circle
        sun_radius = half // 4
        sun_x = center_x - half // 3
        sun_y = center_y - half // 3
        ctx.draw_ellipse(
            (
                sun_x - sun_radius,
                sun_y - sun_radius,
                sun_x + sun_radius,
                sun_y + sun_radius,
            ),
            fill=COLOR_GRAY,
        )

        # Mountain triangle (simplified)
        mountain_base_y = center_y + half // 2
        mountain_peak_y = center_y
        ctx.draw_line(
            [
                (center_x - half // 2, mountain_base_y),
                (center_x, mountain_peak_y),
                (center_x + half // 2, mountain_base_y),
            ],
            fill=COLOR_GRAY,
            width=2,
        )

        # Label
        font = ctx.get_font("small")
        label = self.config.label or "No Image"
        ctx.draw_text(
            label,
            (center_x, center_y + half + int(ctx.height * 0.1)),
            font=font,
            color=COLOR_GRAY,
            anchor="mm",
        )
