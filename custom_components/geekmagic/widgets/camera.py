"""Camera widget for GeekMagic displays."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from ..const import COLOR_GRAY, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext

_LOGGER = logging.getLogger(__name__)


class CameraWidget(Widget):
    """Widget that displays a camera snapshot."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the camera widget.

        Options:
            show_label: Show camera name label (default: False)
            fit: How to fit image - "contain" (preserve aspect) or "cover" (fill)
        """
        super().__init__(config)
        self.show_label = config.options.get("show_label", False)
        self.fit = config.options.get("fit", "contain")
        self._cached_image: Image.Image | None = None
        self._last_entity_id: str | None = None

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the camera widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        # Get camera image
        camera_image = self._get_camera_image(hass)

        if camera_image is None:
            self._render_no_camera(ctx)
            return

        # Calculate image rect (leave room for label if showing)
        if self.show_label:
            label_height = int(ctx.height * 0.15)
            image_rect = (0, 0, ctx.width, ctx.height - label_height)
            label_y = ctx.height - label_height // 2
        else:
            image_rect = None  # Full widget area
            label_y = None

        # Draw the camera image
        preserve_aspect = self.fit == "contain"
        ctx.draw_image(camera_image, rect=image_rect, preserve_aspect=preserve_aspect)

        # Draw label if enabled
        if self.show_label and label_y is not None:
            label = self.config.label or self._get_camera_name(hass)
            font = ctx.get_font("small")
            ctx.draw_text(
                label,
                (ctx.width // 2, label_y),
                font=font,
                color=self.config.color or COLOR_WHITE,
                anchor="mm",
            )

    def _get_camera_image(self, hass: HomeAssistant | None) -> Image.Image | None:
        """Get camera image from Home Assistant.

        The coordinator pre-fetches camera images asynchronously before rendering.
        We look for the pre-fetched image in the coordinator's cache.

        Args:
            hass: Home Assistant instance

        Returns:
            PIL Image or None if not available
        """
        if hass is None or not self.config.entity_id:
            return self._cached_image

        entity_id = self.config.entity_id

        # Check if entity exists and is available
        state = hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            return self._cached_image

        try:
            # Get pre-fetched image from coordinator
            from ..const import DOMAIN

            # Find the coordinator that has this camera image
            for coordinator in hass.data.get(DOMAIN, {}).values():
                if hasattr(coordinator, "get_camera_image"):
                    image_bytes = coordinator.get_camera_image(entity_id)
                    if image_bytes:
                        self._cached_image = Image.open(BytesIO(image_bytes))
                        self._cached_image = self._cached_image.convert("RGB")
                        self._last_entity_id = entity_id
                        return self._cached_image

        except Exception as e:
            _LOGGER.debug("Error getting camera image for %s: %s", entity_id, e)

        return self._cached_image

    def _get_camera_name(self, hass: HomeAssistant | None) -> str:
        """Get camera friendly name."""
        if hass is None or not self.config.entity_id:
            return "Camera"

        state = hass.states.get(self.config.entity_id)
        if state is None:
            return "Camera"

        return state.attributes.get("friendly_name", "Camera")

    def _render_no_camera(self, ctx: RenderContext) -> None:
        """Render placeholder when no camera image available."""
        center_x = ctx.width // 2
        center_y = ctx.height // 2

        font = ctx.get_font("small")

        # Draw camera icon (simple rectangle with lens circle)
        icon_size = min(ctx.width, ctx.height) // 3
        half = icon_size // 2

        # Camera body
        body_rect = (
            center_x - half,
            center_y - half // 2,
            center_x + half,
            center_y + half // 2,
        )
        ctx.draw_rounded_rect(body_rect, radius=4, fill=COLOR_GRAY)

        # Lens circle
        lens_radius = half // 3
        ctx.draw_ellipse(
            (
                center_x - lens_radius,
                center_y - lens_radius,
                center_x + lens_radius,
                center_y + lens_radius,
            ),
            outline=COLOR_WHITE,
            width=2,
        )

        # Label
        label = self.config.label or "No Image"
        ctx.draw_text(
            label,
            (center_x, center_y + half + int(ctx.height * 0.1)),
            font=font,
            color=COLOR_GRAY,
            anchor="mm",
        )
