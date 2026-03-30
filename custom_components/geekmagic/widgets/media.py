"""Media player widget for GeekMagic displays."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from PIL import Image

from ..const import COLOR_CYAN
from ..render_context import SizeCategory, get_size_category
from .base import Widget, WidgetConfig
from .components import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Bar,
    Color,
    Column,
    Component,
    Icon,
    Row,
    Spacer,
    Text,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState


def _calculate_media_position(
    entity: EntityState | None,
    now: datetime | None,
) -> float:
    """Calculate current media position accounting for elapsed playback time.

    Home Assistant's media_position only updates on state changes (play/pause/seek).
    To get the actual current position, we need to add elapsed time since the
    last update when the player is actively playing.

    Args:
        entity: Media player entity state
        now: Current datetime (timezone-aware)

    Returns:
        Current position in seconds
    """
    if entity is None:
        return 0.0

    # Get base position
    position = float(entity.get("media_position", 0) or 0)

    # Only calculate elapsed time if playing and we have timing info
    if entity.state != "playing" or now is None:
        return position

    # Get the timestamp when position was last updated
    updated_at = entity.get("media_position_updated_at")
    if updated_at is None:
        return position

    # Parse the datetime if it's a string (HA stores as ISO format)
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at)
        except (ValueError, TypeError):
            return position

    # Calculate elapsed time since last update
    if hasattr(updated_at, "timestamp"):
        elapsed = now.timestamp() - updated_at.timestamp()
        if elapsed > 0:
            # Add elapsed time, but cap at duration if available
            duration = float(entity.get("media_duration", 0) or 0)
            new_position = position + elapsed
            return min(new_position, duration) if duration > 0 else new_position

    return position


def _format_time(seconds: float) -> str:
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


@dataclass
class ImageFill(Component):
    """Component that fills its area with an image."""

    image: Image.Image
    fit: str = "cover"  # "cover", "contain", "fill"

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        ctx.draw_image(self.image, rect=(x, y, x + width, y + height), fit_mode=self.fit)


@dataclass
class DarkOverlay(Component):
    """Dark overlay that sits at the bottom portion of its container."""

    height_ratio: float = 0.35  # Portion of height to cover
    color: Color = (10, 10, 10)

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        overlay_height = int(height * self.height_ratio)
        overlay_y = y + height - overlay_height
        ctx.draw_rect((x, overlay_y, x + width, y + height), fill=self.color)


@dataclass
class AlbumArt(Component):
    """Album art display with overlay showing track info.

    Uses Stack to layer: image -> dark overlay -> text info -> progress bar.
    Inspired by Spotify/Apple Music now playing screens.
    """

    image: Image.Image
    title: str = ""
    artist: str = ""
    position: float = 0
    duration: float = 0
    color: Color = COLOR_CYAN
    show_progress: bool = True
    show_overlay: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render album art with overlay using component composition."""
        # Layer 1: Album art background
        ImageFill(image=self.image, fit="cover").render(ctx, x, y, width, height)

        if not self.show_overlay:
            return

        # Determine sizing based on available space using standard size categories
        size = get_size_category(height)
        is_micro = size == SizeCategory.MICRO
        is_compact = size in (SizeCategory.MICRO, SizeCategory.TINY, SizeCategory.SMALL)
        show_artist = size in (SizeCategory.MEDIUM, SizeCategory.LARGE)
        show_time = size == SizeCategory.LARGE

        # Overlay ratio varies by size - smaller for small cells
        if is_micro:
            overlay_ratio = 0.28  # Minimal overlay for micro
        elif is_compact:
            overlay_ratio = 0.30
        else:
            overlay_ratio = 0.28

        # Layer 2: Dark overlay at bottom
        DarkOverlay(height_ratio=overlay_ratio).render(ctx, x, y, width, height)

        # Layer 3: Text content positioned at bottom
        overlay_height = int(height * overlay_ratio)
        text_area_y = y + height - overlay_height
        # Smaller padding for micro cells to fit more text
        padding = max(2, int(width * 0.02)) if is_micro else max(4, int(width * 0.04))

        # Build text components
        text_children: list[Component] = []

        # Title - always show, smaller font for compact cells
        if self.title:
            if is_micro:
                title_font = "tiny"
                title_bold = False
            elif is_compact:
                title_font = "tiny"
                title_bold = True
            else:
                title_font = "small"
                title_bold = True

            text_children.append(
                Text(
                    self.title,
                    font=title_font,
                    color=(255, 255, 255),
                    bold=title_bold,
                    align="start",
                )
            )

        # Artist - show only when there's room (MEDIUM, LARGE)
        if self.artist and show_artist:
            text_children.append(
                Text(
                    self.artist,
                    font="tiny",
                    color=(160, 160, 160),
                    align="start",
                )
            )

        # Time display for large cells only
        if self.duration > 0 and show_time:
            pos_str = _format_time(self.position)
            dur_str = _format_time(self.duration)
            time_str = f"{pos_str} / {dur_str}"
            text_children.append(
                Text(
                    time_str,
                    font="tiny",
                    color=(120, 120, 120),
                    align="start",
                )
            )

        # Render text column in overlay area
        if text_children:
            text_column = Column(
                children=text_children,
                align="start",
                justify="end",  # Stack from bottom up
                padding=padding,
                gap=1,  # Minimal gap between items
            )
            # Position text in overlay area (leaving room for progress bar)
            bar_height = max(2, int(height * 0.015)) if self.show_progress else 0
            text_height = overlay_height - bar_height - padding
            text_column.render(ctx, x, text_area_y, width, text_height)

        # Layer 4: Progress bar at very bottom
        if self.show_progress and self.duration > 0:
            progress = min(100, (self.position / self.duration) * 100)
            bar_height = max(2, int(height * 0.015))
            bar_y = y + height - bar_height

            # Use Bar component
            Bar(
                percent=progress,
                color=self.color,
                background=(40, 40, 40),
                height=bar_height,
            ).render(ctx, x, bar_y, width, bar_height)


@dataclass
class NowPlaying(Component):
    """Now playing display component (text-only version)."""

    title: str
    artist: str = ""
    album: str = ""
    position: float = 0
    duration: float = 0
    color: Color = COLOR_CYAN
    show_artist: bool = True
    show_album: bool = False
    show_progress: bool = True

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render now playing info."""
        padding = int(width * 0.05)

        # Truncate text
        max_chars = (width - padding * 2) // 8
        title = self.title[: max_chars - 2] + ".." if len(self.title) > max_chars else self.title
        artist = (
            self.artist[: max_chars - 2] + ".." if len(self.artist) > max_chars else self.artist
        )
        album = self.album[: max_chars - 2] + ".." if len(self.album) > max_chars else self.album

        # Build component tree
        children = [
            Text("NOW PLAYING", font="small", color=THEME_TEXT_SECONDARY),
            Spacer(min_size=int(height * 0.03)),
            Text(title, font="regular", color=THEME_TEXT_PRIMARY),
        ]

        if self.show_artist and artist:
            children.append(Spacer(min_size=int(height * 0.02)))
            children.append(Text(artist, font="small", color=THEME_TEXT_SECONDARY))

        if self.show_album and self.album:
            children.append(Spacer(min_size=int(height * 0.02)))
            children.append(Text(album, font="small", color=THEME_TEXT_SECONDARY))

        # Add spacer before progress section
        children.append(Spacer())

        # Progress bar and time labels
        if self.show_progress and self.duration > 0:
            progress = min(100, (self.position / self.duration) * 100)
            pos_str = _format_time(self.position)
            dur_str = _format_time(self.duration)

            children.extend(
                [
                    Bar(
                        percent=progress,
                        color=self.color,
                        height=max(4, int(height * 0.05)),
                    ),
                    Spacer(min_size=int(height * 0.02)),
                    Row(
                        children=[
                            Text(pos_str, font="small", color=THEME_TEXT_SECONDARY, align="start"),
                            Spacer(),
                            Text(dur_str, font="small", color=THEME_TEXT_SECONDARY, align="end"),
                        ]
                    ),
                ]
            )

        # Render the column
        Column(children=children, padding=padding, align="center").render(ctx, x, y, width, height)


@dataclass
class MediaIdle(Component):
    """Idle/paused state display."""

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        """Render paused state."""
        # Calculate icon size - larger for better visibility
        icon_size = max(32, int(height * 0.3))

        # Build component tree - use gap instead of Spacer to keep elements grouped
        Column(
            children=[
                Icon("pause", size=icon_size, color=THEME_TEXT_SECONDARY),
                Text("PAUSED", font="regular", color=THEME_TEXT_SECONDARY),
            ],
            align="center",
            justify="center",
            gap=int(height * 0.06),
        ).render(ctx, x, y, width, height)


class MediaWidget(Widget):
    """Widget that displays media player information."""

    WIDGET_TYPE: ClassVar[str] = "media"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Media Player",
        "needs_entity": True,
        "entity_domains": ["media_player"],
        "options": [
            {"key": "show_artist", "type": "boolean", "label": "Show Artist", "default": True},
            {"key": "show_album", "type": "boolean", "label": "Show Album", "default": False},
            {"key": "show_progress", "type": "boolean", "label": "Show Progress", "default": True},
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the media widget."""
        super().__init__(config)
        self.show_artist = config.options.get("show_artist", True)
        self.show_album = config.options.get("show_album", False)
        self.show_progress = config.options.get("show_progress", True)
        self.show_album_art = config.options.get("show_album_art", True)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the media player widget.

        Args:
            ctx: RenderContext for drawing
            state: Widget state with entity data
        """
        entity = state.entity

        if entity is None or entity.state in ("off", "unavailable", "unknown", "idle", "paused"):
            return MediaIdle()

        # Calculate current position (accounts for elapsed playback time)
        position = _calculate_media_position(entity, state.now)
        duration = entity.get("media_duration", 0) or 0

        # Use album art if available and enabled
        if self.show_album_art and state.image is not None:
            return AlbumArt(
                image=state.image.convert("RGB") if state.image.mode != "RGB" else state.image,
                title=entity.get("media_title", ""),
                artist=entity.get("media_artist", ""),
                position=position,
                duration=duration,
                color=self.config.color or ctx.theme.get_accent_color(self.config.slot),
                show_progress=self.show_progress,
                show_overlay=True,
            )

        return NowPlaying(
            title=entity.get("media_title", "Unknown"),
            artist=entity.get("media_artist", ""),
            album=entity.get("media_album_name", ""),
            position=position,
            duration=duration,
            color=self.config.color or ctx.theme.get_accent_color(self.config.slot),
            show_artist=self.show_artist,
            show_album=self.show_album,
            show_progress=self.show_progress,
        )
