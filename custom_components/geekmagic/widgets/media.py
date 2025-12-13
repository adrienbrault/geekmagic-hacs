"""Media player widget for GeekMagic displays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..const import COLOR_CYAN, COLOR_GRAY, COLOR_WHITE
from .base import Widget, WidgetConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..render_context import RenderContext


class MediaWidget(Widget):
    """Widget that displays media player information."""

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the media widget."""
        super().__init__(config)
        self.show_artist = config.options.get("show_artist", True)
        self.show_album = config.options.get("show_album", False)
        self.show_progress = config.options.get("show_progress", True)

    def render(
        self,
        ctx: RenderContext,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Render the media player widget.

        Args:
            ctx: RenderContext for drawing
            hass: Home Assistant instance
        """
        center_x = ctx.width // 2

        # Get scaled fonts based on container height
        font_label = ctx.get_font("small")
        font_title = ctx.get_font("regular")
        font_small = ctx.get_font("small")

        # Calculate relative padding
        padding = int(ctx.width * 0.05)

        # Get entity state
        state = self.get_entity_state(hass)

        if state is None or state.state in ("off", "unavailable", "unknown", "idle"):
            # Not playing - show paused state
            self._render_idle(ctx)
            return

        # Get media info
        attrs = state.attributes
        title = attrs.get("media_title", "Unknown")
        artist = attrs.get("media_artist", "")
        album = attrs.get("media_album_name", "")
        position = attrs.get("media_position", 0)
        duration = attrs.get("media_duration", 0)

        # Truncate text if needed
        max_chars = (ctx.width - padding * 2) // 8
        if len(title) > max_chars:
            title = title[: max_chars - 2] + ".."
        if len(artist) > max_chars:
            artist = artist[: max_chars - 2] + ".."

        # Calculate positions relative to container
        current_y = int(ctx.height * 0.12)

        # Draw "NOW PLAYING" label
        ctx.draw_text(
            "NOW PLAYING",
            (center_x, current_y),
            font=font_label,
            color=COLOR_GRAY,
            anchor="mm",
        )
        current_y += int(ctx.height * 0.20)

        # Draw title
        ctx.draw_text(
            title,
            (center_x, current_y),
            font=font_title,
            color=COLOR_WHITE,
            anchor="mm",
        )
        current_y += int(ctx.height * 0.17)

        # Draw artist
        if self.show_artist and artist:
            ctx.draw_text(
                artist,
                (center_x, current_y),
                font=font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )
            current_y += int(ctx.height * 0.15)

        # Draw album
        if self.show_album and album:
            if len(album) > max_chars:
                album = album[: max_chars - 2] + ".."
            ctx.draw_text(
                album,
                (center_x, current_y),
                font=font_small,
                color=COLOR_GRAY,
                anchor="mm",
            )

        # Draw progress bar
        if self.show_progress and duration > 0:
            bar_height = max(4, int(ctx.height * 0.05))
            bar_y = ctx.height - int(ctx.height * 0.21)
            bar_rect = (padding, bar_y, ctx.width - padding, bar_y + bar_height)
            progress = min(100, (position / duration) * 100)
            ctx.draw_bar(
                bar_rect,
                progress,
                color=self.config.color or COLOR_CYAN,
            )

            # Draw time
            pos_str = self._format_time(position)
            dur_str = self._format_time(duration)
            time_y = bar_y + int(ctx.height * 0.12)

            ctx.draw_text(
                pos_str,
                (padding, time_y),
                font=font_small,
                color=COLOR_GRAY,
                anchor="lm",
            )
            ctx.draw_text(
                dur_str,
                (ctx.width - padding, time_y),
                font=font_small,
                color=COLOR_GRAY,
                anchor="rm",
            )

    def _render_idle(self, ctx: RenderContext) -> None:
        """Render idle/paused state."""
        center_x = ctx.width // 2
        center_y = ctx.height // 2

        # Get scaled font
        font_label = ctx.get_font("small")

        # Draw pause icon (two vertical bars) - scaled to container
        bar_width = max(4, int(ctx.width * 0.04))
        bar_height = max(15, int(ctx.height * 0.25))
        gap = max(5, int(ctx.width * 0.05))

        left_bar = (
            center_x - gap - bar_width,
            center_y - bar_height // 2,
            center_x - gap,
            center_y + bar_height // 2,
        )
        right_bar = (
            center_x + gap,
            center_y - bar_height // 2,
            center_x + gap + bar_width,
            center_y + bar_height // 2,
        )

        ctx.draw_rect(left_bar, fill=COLOR_GRAY)
        ctx.draw_rect(right_bar, fill=COLOR_GRAY)

        # Draw label
        ctx.draw_text(
            "PAUSED",
            (center_x, center_y + int(ctx.height * 0.29)),
            font=font_label,
            color=COLOR_GRAY,
            anchor="mm",
        )

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        seconds = int(seconds)
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
