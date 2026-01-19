"""PIL-based image renderer for GeekMagic displays.

Uses 2x supersampling for anti-aliased output.
"""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from .const import (
    COLOR_BLACK,
    COLOR_CYAN,
    COLOR_DARK_GRAY,
    COLOR_GRAY,
    COLOR_PANEL,
    COLOR_WHITE,
    DEFAULT_JPEG_QUALITY,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
)
from .icons import get_mdi_char

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont


# Supersampling scale for anti-aliasing
SUPERSAMPLE_SCALE = 2

# Bundled font directory (relative to this file)
_FONTS_DIR = Path(__file__).parent / "fonts"


def _load_font(size: int, bold: bool = False) -> FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font or fall back to default.

    Prefers bundled DejaVu Sans for consistent Unicode support across platforms.

    Args:
        size: Font size in pixels
        bold: Whether to load bold variant

    Returns:
        Loaded font or default font
    """
    if bold:
        font_paths = [
            # Bundled font (best Unicode support, works in HA Docker)
            _FONTS_DIR / "DejaVuSans-Bold.ttf",
            # System fonts as fallback
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            ("/System/Library/Fonts/Helvetica.ttc", 1),  # macOS (index 1 = bold)
            "C:/Windows/Fonts/arialbd.ttf",  # Windows
        ]
    else:
        font_paths = [
            # Bundled font (best Unicode support, works in HA Docker)
            _FONTS_DIR / "DejaVuSans.ttf",
            # System fonts as fallback
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            ("/System/Library/Fonts/Helvetica.ttc", 0),  # macOS (index 0 = regular)
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]

    for path_entry in font_paths:
        try:
            if isinstance(path_entry, tuple):
                path, index = path_entry
                return ImageFont.truetype(path, size, index=index)
            return ImageFont.truetype(str(path_entry), size)
        except OSError:
            continue

    return ImageFont.load_default()


# MDI icon font path
_MDI_FONT = _FONTS_DIR / "materialdesignicons-webfont.ttf"

# Noto Emoji font path (for Unicode emoji support)
_EMOJI_FONT = _FONTS_DIR / "NotoEmoji.ttf"


def _is_emoji(char: str) -> bool:
    """Check if a character is an emoji that needs the emoji font.

    Args:
        char: A single character

    Returns:
        True if the character should be rendered with the emoji font
    """
    code = ord(char)
    # Common emoji ranges that DejaVu Sans doesn't support well
    emoji_ranges = [
        (0x1F300, 0x1F9FF),  # Misc Symbols, Emoticons, Dingbats, etc.
        (0x1FA00, 0x1FAFF),  # Chess, Extended-A
        (0x2600, 0x26FF),  # Misc Symbols (weather, zodiac, chess, etc.)
        (0x2700, 0x27BF),  # Dingbats
        (0x231A, 0x231B),  # Watch, Hourglass
        (0x23E9, 0x23F3),  # Media control symbols
        (0x23F8, 0x23FA),  # Media control symbols
        (0x25AA, 0x25AB),  # Small squares
        (0x25B6, 0x25B6),  # Play button
        (0x25C0, 0x25C0),  # Reverse button
        (0x25FB, 0x25FE),  # Medium squares
        (0x2614, 0x2615),  # Umbrella, Hot beverage
        (0x2648, 0x2653),  # Zodiac signs
        (0x267F, 0x267F),  # Wheelchair
        (0x2693, 0x2693),  # Anchor
        (0x26A1, 0x26A1),  # High voltage
        (0x26AA, 0x26AB),  # Medium circles
        (0x26BD, 0x26BE),  # Soccer, Baseball
        (0x26C4, 0x26C5),  # Snowman, Sun behind cloud
        (0x26CE, 0x26CE),  # Ophiuchus
        (0x26D4, 0x26D4),  # No entry
        (0x26EA, 0x26EA),  # Church
        (0x26F2, 0x26F3),  # Fountain, Golf
        (0x26F5, 0x26F5),  # Sailboat
        (0x26FA, 0x26FA),  # Tent
        (0x26FD, 0x26FD),  # Fuel pump
        (0x2702, 0x2702),  # Scissors
        (0x2705, 0x2705),  # Check mark
        (0x2708, 0x270D),  # Airplane, Envelope, etc.
        (0x270F, 0x270F),  # Pencil
        (0x2712, 0x2712),  # Black nib
        (0x2714, 0x2714),  # Check mark
        (0x2716, 0x2716),  # X mark
        (0x271D, 0x271D),  # Latin cross
        (0x2721, 0x2721),  # Star of David
        (0x2728, 0x2728),  # Sparkles
        (0x2733, 0x2734),  # Eight spoked asterisk
        (0x2744, 0x2744),  # Snowflake
        (0x2747, 0x2747),  # Sparkle
        (0x274C, 0x274C),  # Cross mark
        (0x274E, 0x274E),  # Cross mark
        (0x2753, 0x2755),  # Question marks
        (0x2757, 0x2757),  # Exclamation mark
        (0x2763, 0x2764),  # Heart exclamation, Red heart
        (0x2795, 0x2797),  # Plus, Minus, Division
        (0x27A1, 0x27A1),  # Right arrow
        (0x27B0, 0x27B0),  # Curly loop
        (0x27BF, 0x27BF),  # Double curly loop
        (0x2934, 0x2935),  # Arrows
        (0x2B05, 0x2B07),  # Arrows
        (0x2B1B, 0x2B1C),  # Large squares
        (0x2B50, 0x2B50),  # Star
        (0x2B55, 0x2B55),  # Circle
        (0x3030, 0x3030),  # Wavy dash
        (0x303D, 0x303D),  # Part alternation mark
        (0x3297, 0x3297),  # Circled Ideograph Congratulation
        (0x3299, 0x3299),  # Circled Ideograph Secret
        (0x1F004, 0x1F004),  # Mahjong
        (0x1F0CF, 0x1F0CF),  # Playing card
        (0x1F170, 0x1F171),  # A/B buttons
        (0x1F17E, 0x1F17F),  # O/P buttons
        (0x1F18E, 0x1F18E),  # AB button
        (0x1F191, 0x1F19A),  # Squared words
        (0x1F1E0, 0x1F1FF),  # Regional indicators (flags)
        (0x1F201, 0x1F202),  # Squared Katakana
        (0x1F21A, 0x1F21A),  # Squared CJK
        (0x1F22F, 0x1F22F),  # Squared CJK
        (0x1F232, 0x1F23A),  # Squared CJK
        (0x1F250, 0x1F251),  # Circled Ideograph
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F680, 0x1F6FF),  # Transport and Map Symbols
        (0x1F7E0, 0x1F7EB),  # Large colored circles and squares
        (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
        (0x1FAD0, 0x1FAFF),  # Food, animals, etc.
        (0xE000, 0xF8FF),  # Private Use Area (often used for custom emoji)
    ]
    return any(start <= code <= end for start, end in emoji_ranges)


def _load_emoji_font(size: int) -> FreeTypeFont | ImageFont.ImageFont:
    """Load Noto Emoji font at specified size.

    Args:
        size: Font size in pixels

    Returns:
        Loaded emoji font or default font
    """
    try:
        return ImageFont.truetype(str(_EMOJI_FONT), size)
    except OSError:
        return ImageFont.load_default()


def _load_mdi_font(size: int) -> FreeTypeFont | ImageFont.ImageFont:
    """Load MDI icon font at specified size.

    Args:
        size: Font size in pixels

    Returns:
        Loaded MDI font or default font
    """
    try:
        return ImageFont.truetype(str(_MDI_FONT), size)
    except OSError:
        return ImageFont.load_default()


class Renderer:
    """Renders widgets and layouts to images using PIL with supersampling."""

    def __init__(self) -> None:
        """Initialize the renderer with fonts."""
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self._scale = SUPERSAMPLE_SCALE
        self._scaled_width = self.width * self._scale
        self._scaled_height = self.height * self._scale

        # Load fonts at scaled sizes (min 13px for readability on 240x240 display)
        # Tiny font increased from 11px to 13px for better readability
        self.font_tiny = _load_font(13 * self._scale)
        self.font_small = _load_font(14 * self._scale)
        self.font_regular = _load_font(15 * self._scale)
        self.font_medium = _load_font(18 * self._scale)
        self.font_large = _load_font(24 * self._scale)
        self.font_xlarge = _load_font(36 * self._scale)
        self.font_huge = _load_font(52 * self._scale)

        # Bold font variants for emphasis
        self.font_small_bold = _load_font(13 * self._scale, bold=True)
        self.font_regular_bold = _load_font(15 * self._scale, bold=True)
        self.font_medium_bold = _load_font(18 * self._scale, bold=True)

        # Font cache for dynamically sized fonts (avoid repeated disk I/O)
        self._font_cache: dict[tuple[int, bool], FreeTypeFont | ImageFont.ImageFont] = {}

        # MDI icon font cache (keyed by scaled size)
        self._mdi_font_cache: dict[int, FreeTypeFont | ImageFont.ImageFont] = {}

        # Emoji font cache (keyed by size)
        self._emoji_font_cache: dict[int, FreeTypeFont | ImageFont.ImageFont] = {}

    @property
    def scale(self) -> int:
        """Return the supersampling scale factor."""
        return self._scale

    def _s(self, value: float) -> int:
        """Scale a value for supersampling."""
        return int(value * self._scale)

    def get_scaled_font(
        self,
        size_name: str,
        rect_height: int,
        bold: bool = False,
        adjust: int = 0,
    ) -> FreeTypeFont | ImageFont.ImageFont:
        """Get a font scaled relative to container height.

        This enables widgets to render correctly at any size by scaling
        fonts proportionally to their container.

        Args:
            size_name: Font size category. Supports two naming systems:
                - Legacy: "tiny", "small", "regular", "medium", "large", "xlarge", "huge"
                - Semantic: "primary", "secondary", "tertiary"
            rect_height: Height of the container rect (already scaled for supersample)
            bold: Whether to use bold variant
            adjust: Relative size adjustment (-2 to +2). Each step is ~15% size change.

        Returns:
            Font scaled appropriately for the container size
        """
        # Semantic sizes as ratios of container height
        # These map to approximate proportions for readable text
        semantic_ratios = {
            "primary": 0.35,  # Main value - 35% of container height
            "secondary": 0.20,  # Supporting info - 20%
            "tertiary": 0.12,  # Labels, captions - 12%
        }

        # Legacy font config: (base_size, min_size) per category
        # Base sizes are for full 240px height at 2x scale = 480px
        # Min sizes ensure readability even in small containers
        legacy_config = {
            "tiny": (13, 22),
            "small": (14, 24),
            "regular": (15, 24),
            "medium": (18, 28),
            "large": (24, 34),
            "xlarge": (36, 44),
            "huge": (52, 52),
        }

        # Calculate scale factor based on container height vs reference
        reference_height = self._scaled_height
        scale_factor = rect_height / reference_height

        # Adjustment factor: each step is ~15% change
        adjust_factor = 1.15**adjust

        if size_name in semantic_ratios:
            # Semantic sizing: ratio-based
            ratio = semantic_ratios[size_name] * adjust_factor
            # Calculate pixel size from ratio and container height
            scaled_size = max(22, int(rect_height * ratio))
        else:
            # Legacy sizing: base size with scale factor
            base_size, min_size = legacy_config.get(size_name, (15, 24))
            scaled_size = max(min_size, int(base_size * self._scale * scale_factor * adjust_factor))

        # Check cache first to avoid repeated disk I/O
        cache_key = (scaled_size, bold)
        if cache_key not in self._font_cache:
            self._font_cache[cache_key] = _load_font(scaled_size, bold=bold)
        return self._font_cache[cache_key]

    def _measure_mixed_text(
        self, text: str, font: FreeTypeFont | ImageFont.ImageFont, font_size: int
    ) -> tuple[int, int]:
        """Measure text that may contain emoji.

        Args:
            text: Text to measure
            font: Font for regular text
            font_size: Font size (for loading matching emoji font)

        Returns:
            (width, height) tuple in scaled pixels
        """
        if not any(_is_emoji(char) for char in text):
            bbox = font.getbbox(text)
            if bbox:
                return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
            return 0, 0

        segments = self._segment_text_by_font(text)
        emoji_font = _load_emoji_font(font_size)

        total_width = 0
        max_height = 0

        for segment_text, is_emoji in segments:
            segment_font = emoji_font if is_emoji else font
            bbox = segment_font.getbbox(segment_text)
            if bbox:
                total_width += int(bbox[2] - bbox[0])
                max_height = max(max_height, int(bbox[3] - bbox[1]))

        return total_width, max_height

    def fit_text_font(
        self,
        text: str,
        max_width: int,
        max_height: int,
        bold: bool = False,
        min_size: int = 20,
        max_size: int = 200,
    ) -> FreeTypeFont | ImageFont.ImageFont:
        """Find the largest font size that fits text within bounds.

        Uses binary search to efficiently find the optimal size.
        All dimensions should be in scaled coordinates.
        Handles text containing emoji by measuring with appropriate fonts.

        Args:
            text: Text to fit (can include emoji)
            max_width: Maximum width in scaled pixels
            max_height: Maximum height in scaled pixels
            bold: Whether to use bold variant
            min_size: Minimum font size to consider
            max_size: Maximum font size to consider

        Returns:
            Font at the largest size that fits within bounds
        """
        has_emoji = any(_is_emoji(char) for char in text)

        # Binary search for optimal font size
        low, high = min_size, max_size
        best_font = _load_font(min_size, bold=bold)

        while low <= high:
            mid = (low + high) // 2
            font = _load_font(mid, bold=bold)

            if has_emoji:
                text_width, text_height = self._measure_mixed_text(text, font, mid)
            else:
                bbox = font.getbbox(text)
                if bbox:
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                else:
                    high = mid - 1
                    continue

            if text_width <= max_width and text_height <= max_height:
                best_font = font
                low = mid + 1  # Try larger
            else:
                high = mid - 1  # Try smaller

        # Cache the result
        bbox = best_font.getbbox(text)
        if bbox:
            size = int(bbox[3] - bbox[1])  # Approximate from height
            cache_key = (size, bold)
            if cache_key not in self._font_cache:
                self._font_cache[cache_key] = best_font

        return best_font

    def get_mdi_font(self, size: int) -> FreeTypeFont | ImageFont.ImageFont:
        """Get MDI icon font at specified size (cached).

        Args:
            size: Font size in pixels (will be scaled for supersampling)

        Returns:
            MDI font at requested size
        """
        scaled_size = self._s(size)
        if scaled_size not in self._mdi_font_cache:
            self._mdi_font_cache[scaled_size] = _load_mdi_font(scaled_size)
        return self._mdi_font_cache[scaled_size]

    def get_emoji_font(self, size: int) -> FreeTypeFont | ImageFont.ImageFont:
        """Get emoji font at specified size (cached).

        Args:
            size: Font size in pixels (already scaled for supersampling)

        Returns:
            Emoji font at requested size
        """
        if size not in self._emoji_font_cache:
            self._emoji_font_cache[size] = _load_emoji_font(size)
        return self._emoji_font_cache[size]

    def _scale_rect(self, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Scale a rectangle for supersampling."""
        return (self._s(rect[0]), self._s(rect[1]), self._s(rect[2]), self._s(rect[3]))

    def _scale_point(self, point: tuple[int, int]) -> tuple[int, int]:
        """Scale a point for supersampling."""
        return (self._s(point[0]), self._s(point[1]))

    def create_canvas(
        self, background: tuple[int, int, int] = COLOR_BLACK
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create a new image canvas at supersampled resolution.

        Args:
            background: RGB background color tuple

        Returns:
            Tuple of (Image, ImageDraw)
        """
        img = Image.new("RGB", (self._scaled_width, self._scaled_height), background)
        draw = ImageDraw.Draw(img)
        return img, draw

    def _downscale(self, img: Image.Image) -> Image.Image:
        """Downscale supersampled image to final resolution with anti-aliasing."""
        return img.resize((self.width, self.height), Image.Resampling.LANCZOS)

    def draw_image(
        self,
        draw: ImageDraw.ImageDraw,
        source: Image.Image,
        rect: tuple[int, int, int, int],
        preserve_aspect: bool = True,
        fit_mode: str | None = None,
    ) -> None:
        """Draw/paste an image onto the canvas.

        Args:
            draw: ImageDraw instance (used to get underlying image)
            source: Source PIL Image to paste
            rect: (x1, y1, x2, y2) destination rectangle (will be scaled)
            preserve_aspect: If True, preserve aspect ratio and center (legacy param)
            fit_mode: "contain" (letterbox), "cover" (crop), or "stretch".
                      If specified, overrides preserve_aspect.
        """
        # Get the underlying image from the draw object
        canvas = draw._image  # noqa: SLF001

        # Scale the destination rect
        x1, y1, x2, y2 = self._scale_rect(rect)
        dest_width = x2 - x1
        dest_height = y2 - y1

        # Determine fit mode
        if fit_mode is None:
            fit_mode = "contain" if preserve_aspect else "stretch"

        src_ratio = source.width / source.height
        dest_ratio = dest_width / dest_height

        if fit_mode == "contain":
            # Fit inside destination, preserving aspect ratio (may letterbox)
            if src_ratio > dest_ratio:
                # Source is wider - fit to width
                new_width = dest_width
                new_height = int(dest_width / src_ratio)
            else:
                # Source is taller - fit to height
                new_height = dest_height
                new_width = int(dest_height * src_ratio)

            # Center the image
            offset_x = (dest_width - new_width) // 2
            offset_y = (dest_height - new_height) // 2

            # Resize and paste
            resized = source.resize((new_width, new_height), Image.Resampling.LANCZOS)
            canvas.paste(resized, (x1 + offset_x, y1 + offset_y))

        elif fit_mode == "cover":
            # Fill destination, cropping excess (no distortion)
            if src_ratio > dest_ratio:
                # Source is wider - fit to height, crop width
                new_height = dest_height
                new_width = int(dest_height * src_ratio)
            else:
                # Source is taller - fit to width, crop height
                new_width = dest_width
                new_height = int(dest_width / src_ratio)

            # Resize first
            resized = source.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Crop to center
            crop_x = (new_width - dest_width) // 2
            crop_y = (new_height - dest_height) // 2
            cropped = resized.crop((crop_x, crop_y, crop_x + dest_width, crop_y + dest_height))

            canvas.paste(cropped, (x1, y1))

        else:  # stretch
            # Stretch to fill (may distort)
            resized = source.resize((dest_width, dest_height), Image.Resampling.LANCZOS)
            canvas.paste(resized, (x1, y1))

    def _segment_text_by_font(self, text: str) -> list[tuple[str, bool]]:
        """Segment text into runs of regular text and emoji.

        Args:
            text: Text to segment

        Returns:
            List of (text_segment, is_emoji) tuples
        """
        if not text:
            return []

        segments: list[tuple[str, bool]] = []
        current_segment = ""
        current_is_emoji = _is_emoji(text[0])

        for char in text:
            char_is_emoji = _is_emoji(char)
            if char_is_emoji == current_is_emoji:
                current_segment += char
            else:
                if current_segment:
                    segments.append((current_segment, current_is_emoji))
                current_segment = char
                current_is_emoji = char_is_emoji

        if current_segment:
            segments.append((current_segment, current_is_emoji))

        return segments

    def _get_font_size(self, font: FreeTypeFont | ImageFont.ImageFont) -> int:
        """Extract font size from a font object.

        Args:
            font: Font to get size from

        Returns:
            Font size in pixels
        """
        # FreeTypeFont has a .size attribute
        if hasattr(font, "size"):
            return int(getattr(font, "size"))  # noqa: B009
        # Fallback: measure a standard character
        bbox = font.getbbox("M")
        if bbox:
            return int(bbox[3] - bbox[1])
        return 24  # Default fallback

    def _has_emoji(self, text: str) -> bool:
        """Check if text contains any emoji characters.

        Args:
            text: Text to check

        Returns:
            True if text contains emoji
        """
        return any(_is_emoji(char) for char in text)

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font: FreeTypeFont | ImageFont.ImageFont | None = None,
        color: tuple[int, int, int] = COLOR_WHITE,
        anchor: str | None = None,
    ) -> None:
        """Draw text on the canvas with automatic emoji fallback.

        Automatically detects emoji characters and renders them using the
        Noto Emoji font while using the regular font for other text.

        Args:
            draw: ImageDraw instance
            text: Text to draw (can include emoji)
            position: (x, y) position (will be scaled)
            font: Font to use for regular text (default: regular)
            color: RGB color tuple
            anchor: Text anchor (e.g., "mm" for center)
        """
        if font is None:
            font = self.font_regular

        # Fast path: if no emoji in text, use simple rendering
        if not self._has_emoji(text):
            scaled_pos = self._scale_point(position)
            draw.text(scaled_pos, text, font=font, fill=color, anchor=anchor)
            return

        # Segment text into regular and emoji runs
        segments = self._segment_text_by_font(text)
        if not segments:
            return

        # Get font size for emoji font (match the main font size)
        font_size = self._get_font_size(font)
        emoji_font = self.get_emoji_font(font_size)

        # Calculate total width for anchor handling
        total_width = 0
        max_height = 0
        segment_widths: list[int] = []

        for segment_text, is_emoji in segments:
            segment_font = emoji_font if is_emoji else font
            bbox = segment_font.getbbox(segment_text)
            if bbox:
                width = int(bbox[2] - bbox[0])
                height = int(bbox[3] - bbox[1])
                segment_widths.append(width)
                total_width += width
                max_height = max(max_height, height)
            else:
                segment_widths.append(0)

        # Calculate starting position based on anchor
        scaled_pos = self._scale_point(position)
        x, y = scaled_pos

        # Handle horizontal anchor
        if anchor:
            h_anchor = anchor[0] if len(anchor) >= 1 else "l"
            v_anchor = anchor[1] if len(anchor) >= 2 else "t"

            if h_anchor == "m":  # Middle
                x -= total_width // 2
            elif h_anchor == "r":  # Right
                x -= total_width

            if v_anchor == "m":  # Middle
                y -= max_height // 2
            elif v_anchor in ("d", "b"):  # Descender/Bottom
                y -= max_height

        # Draw each segment
        current_x = x
        for i, (segment_text, is_emoji) in enumerate(segments):
            segment_font = emoji_font if is_emoji else font
            # Use "lt" anchor for individual segments since we're managing position
            draw.text((current_x, y), segment_text, font=segment_font, fill=color, anchor="lt")
            current_x += segment_widths[i]

    def draw_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.rectangle(scaled_rect, fill=fill, outline=outline, width=self._s(width))

    def draw_rounded_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        radius: int = 4,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rounded rectangle.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            radius: Corner radius
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.rounded_rectangle(
            scaled_rect,
            radius=self._s(radius),
            fill=fill,
            outline=outline,
            width=self._s(width),
        )

    def draw_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
    ) -> None:
        """Draw a horizontal progress bar.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            percent: Fill percentage (0-100)
            color: Bar fill color
            background: Background color
        """
        x1, y1, x2, y2 = rect
        width = x2 - x1
        fill_width = int(width * (percent / 100))

        # Draw background
        self.draw_rounded_rect(draw, rect, radius=2, fill=background)

        # Draw fill
        if fill_width > 0:
            self.draw_rounded_rect(draw, (x1, y1, x1 + fill_width, y2), radius=2, fill=color)

    def _interpolate_catmull_rom(
        self, points: list[tuple[float, float]], num_points: int = 100
    ) -> list[tuple[float, float]]:
        """Interpolate points using Catmull-Rom spline for smooth curves.

        Args:
            points: List of (x, y) control points
            num_points: Number of output points

        Returns:
            Smoothly interpolated points
        """
        if len(points) < 2:
            return points
        if len(points) == 2:
            result = []
            for i in range(num_points):
                t = i / (num_points - 1)
                x = points[0][0] + t * (points[1][0] - points[0][0])
                y = points[0][1] + t * (points[1][1] - points[0][1])
                result.append((x, y))
            return result

        # Add phantom points at start and end for Catmull-Rom
        pts = [points[0], *points, points[-1]]
        result = []

        segments = len(pts) - 3
        points_per_segment = max(1, num_points // segments)

        for i in range(segments):
            p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]

            for j in range(points_per_segment):
                t = j / points_per_segment
                t2 = t * t
                t3 = t2 * t

                x = 0.5 * (
                    (2 * p1[0])
                    + (-p0[0] + p2[0]) * t
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    (2 * p1[1])
                    + (-p0[1] + p2[1]) * t
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                result.append((x, y))

        result.append(pts[-2])
        return result

    def draw_sparkline(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        fill: bool = True,
        smooth: bool = True,
        gradient: bool = False,
    ) -> None:
        """Draw a sparkline chart with optional smoothing.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of data points
            color: Line color
            fill: Whether to fill area under the line
            smooth: Whether to use spline interpolation for smooth curves
            gradient: Whether to use gradient coloring (cool to warm based on value)
        """
        if not data or len(data) < 2:
            return

        x1, y1, x2, y2 = rect
        # Scale coordinates
        x1, y1, x2, y2 = self._s(x1), self._s(y1), self._s(x2), self._s(y2)
        width = x2 - x1
        height = y2 - y1

        # Normalize data
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate control points
        control_points: list[tuple[float, float]] = []
        for i, value in enumerate(data):
            x = x1 + (i / (len(data) - 1)) * width
            y = y2 - ((value - min_val) / range_val) * height
            control_points.append((x, y))

        # Interpolate for smooth curves
        if smooth and len(control_points) >= 3:
            num_points = max(50, width // 2)
            points = self._interpolate_catmull_rom(control_points, num_points)
        else:
            points = control_points

        # Convert to integer tuples
        int_points = [(int(p[0]), int(p[1])) for p in points]

        # Draw filled area
        if fill:
            fill_points = [(x1, y2), *int_points, (x2, y2)]
            if gradient:
                # Gradient: blend between cool (blue) for low values and warm (orange) for high
                # Use the average normalized value to pick a blend
                avg_normalized = sum((v - min_val) / range_val for v in data) / len(data)
                # Cool: (70, 130, 180) - Steel blue
                # Warm: (255, 140, 0) - Dark orange
                fill_color = (
                    int(70 + (255 - 70) * avg_normalized) // 3,
                    int(130 + (140 - 130) * avg_normalized) // 3,
                    int(180 + (0 - 180) * avg_normalized) // 3,
                )
            else:
                # Fill with ~35% opacity of line color for visible but subtle effect
                fill_color = (color[0] // 3, color[1] // 3, color[2] // 3)
            draw.polygon(fill_points, fill=fill_color)

        # Draw line
        if len(int_points) >= 2:
            draw.line(int_points, fill=color, width=self._s(2))

    def draw_timeline_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        on_color: tuple[int, int, int] = COLOR_CYAN,
        off_color: tuple[int, int, int] = COLOR_GRAY,
    ) -> None:
        """Draw a timeline bar showing state changes over time.

        Used for binary sensors where data is 0.0 (off) or 1.0 (on).
        Each segment is colored based on the state at that time.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of data points (0.0 for off, 1.0 for on)
            on_color: Color for "on" state (1.0)
            off_color: Color for "off" state (0.0)
        """
        if not data:
            return

        x1, y1, x2, y2 = rect
        # Scale coordinates
        x1, y1, x2, y2 = self._s(x1), self._s(y1), self._s(x2), self._s(y2)
        width = x2 - x1

        # Calculate segment width (each data point gets equal width)
        segment_width = width / len(data)

        # Draw each segment
        for i, value in enumerate(data):
            seg_x1 = x1 + i * segment_width
            seg_x2 = x1 + (i + 1) * segment_width

            # Choose color based on value (1.0 = on, 0.0 = off)
            color = on_color if value >= 0.5 else off_color

            # Draw the segment as a filled rectangle
            draw.rectangle(
                [int(seg_x1), y1, int(seg_x2), y2],
                fill=color,
            )

    def draw_arc(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_GRAY,
        width: int = 8,
    ) -> None:
        """Draw a circular arc gauge.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            percent: Fill percentage (0-100)
            color: Arc color
            background: Background arc color
            width: Arc line width
        """
        scaled_rect = self._scale_rect(rect)
        scaled_width = self._s(width)

        # Draw background arc (270 degree sweep from bottom-left)
        draw.arc(scaled_rect, start=135, end=405, fill=background, width=scaled_width)

        # Draw progress arc
        if percent > 0:
            end_angle = 135 + (percent / 100) * 270
            draw.arc(scaled_rect, start=135, end=end_angle, fill=color, width=scaled_width)

    def draw_ring_gauge(
        self,
        draw: ImageDraw.ImageDraw,
        center: tuple[int, int],
        radius: int,
        percent: float,
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        width: int = 6,
    ) -> None:
        """Draw a full circular ring gauge (360 degrees).

        Args:
            draw: ImageDraw instance
            center: (x, y) center point
            radius: Ring radius
            percent: Fill percentage (0-100)
            color: Ring color
            background: Background ring color
            width: Ring thickness
        """
        cx, cy = self._scale_point(center)
        r = self._s(radius)
        w = self._s(width)

        bbox = (cx - r, cy - r, cx + r, cy + r)

        # Draw background ring (full circle)
        draw.arc(bbox, start=0, end=360, fill=background, width=w)

        # Draw progress ring (starting from top, -90 degrees)
        if percent > 0:
            # PIL arc starts at 3 o'clock and goes clockwise
            # We want to start at 12 o'clock (-90 degrees)
            start = -90
            end = start + (percent / 100) * 360
            draw.arc(bbox, start=start, end=end, fill=color, width=w)

    def draw_segmented_bar(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        segments: list[tuple[float, tuple[int, int, int]]],
        background: tuple[int, int, int] = COLOR_DARK_GRAY,
        radius: int = 2,
    ) -> None:
        """Draw a segmented horizontal bar with multiple colored sections.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            segments: List of (percentage, color) tuples, should sum to <= 100
            background: Background color
            radius: Corner radius
        """
        x1, y1, x2, y2 = rect
        total_width = x2 - x1

        # Draw background
        self.draw_rounded_rect(draw, rect, radius=radius, fill=background)

        # Draw segments
        current_x = x1
        for seg_percent, seg_color in segments:
            seg_width = int(total_width * (seg_percent / 100))
            if seg_width > 0 and current_x < x2:
                seg_rect = (current_x, y1, min(current_x + seg_width, x2), y2)
                self.draw_rect(draw, seg_rect, fill=seg_color)
                current_x += seg_width

    def draw_mini_bars(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        data: list[float],
        color: tuple[int, int, int] = COLOR_CYAN,
        background: tuple[int, int, int] | None = None,
        bar_width: int = 3,
        gap: int = 1,
    ) -> None:
        """Draw a mini bar chart (vertical bars).

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            data: List of values
            color: Bar color
            background: Optional background color for empty space
            bar_width: Width of each bar
            gap: Gap between bars
        """
        if not data:
            return

        x1, y1, x2, y2 = self._scale_rect(rect)
        height = y2 - y1
        bw = self._s(bar_width)
        g = self._s(gap)

        # Normalize data
        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)
        range_val = max_val - min_val if max_val != min_val else 1

        # Calculate how many bars fit
        available_width = x2 - x1
        num_bars = min(len(data), available_width // (bw + g))

        # Use last N data points if we have more data than space
        if len(data) > num_bars:
            data = data[-num_bars:]

        # Draw bars from right to left (most recent on right)
        for i, value in enumerate(reversed(data)):
            bar_x = x2 - (i + 1) * (bw + g)
            if bar_x < x1:
                break

            bar_height = int(((value - min_val) / range_val) * height * 0.9)
            bar_height = max(bar_height, self._s(2))

            bar_y = y2 - bar_height
            draw.rectangle((bar_x, bar_y, bar_x + bw, y2), fill=color)

    def draw_panel(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        background: tuple[int, int, int] = COLOR_PANEL,
        border_color: tuple[int, int, int] | None = None,
        radius: int = 4,
    ) -> None:
        """Draw a panel/card background with rounded corners.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) coordinates
            background: Panel background color
            border_color: Optional border color
            radius: Corner radius
        """
        self.draw_rounded_rect(draw, rect, radius=radius, fill=background, outline=border_color)

    def draw_ellipse(
        self,
        draw: ImageDraw.ImageDraw,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw an ellipse.

        Args:
            draw: ImageDraw instance
            rect: (x1, y1, x2, y2) bounding box
            fill: Fill color
            outline: Outline color
            width: Outline width
        """
        scaled_rect = self._scale_rect(rect)
        draw.ellipse(scaled_rect, fill=fill, outline=outline, width=self._s(width))

    def draw_line(
        self,
        draw: ImageDraw.ImageDraw,
        xy: list[tuple[int, int]],
        fill: tuple[int, int, int] | None = None,
        width: int = 1,
    ) -> None:
        """Draw lines.

        Args:
            draw: ImageDraw instance
            xy: List of (x, y) points
            fill: Line color
            width: Line width
        """
        if not xy or len(xy) < 2:
            return

        scaled_xy = [self._scale_point(p) for p in xy]
        draw.line(scaled_xy, fill=fill, width=self._s(width))

    def draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        icon: str,
        position: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = COLOR_WHITE,
    ) -> None:
        """Draw a Material Design Icon.

        Uses the bundled MDI font to render icons as text characters.
        Supports legacy icon names, HA MDI format (mdi:xxx), and bare MDI names.

        Args:
            draw: ImageDraw instance
            icon: Icon name in any supported format:
                - Legacy: "temp", "cpu", "drop"
                - HA format: "mdi:thermometer"
                - Bare MDI: "thermometer"
            position: (x, y) top-left corner
            size: Icon size in pixels
            color: Icon color (RGB tuple)
        """
        # Get the MDI character for this icon
        mdi_char = get_mdi_char(icon)

        # Get appropriately sized MDI font
        font = self.get_mdi_font(size)

        # Scale position for supersampling
        x, y = self._scale_point(position)
        scaled_size = self._s(size)

        # Center icon in bounding box
        bbox = font.getbbox(mdi_char)
        if bbox:
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1]
            offset_x = (scaled_size - char_width) // 2 - bbox[0]
            offset_y = (scaled_size - char_height) // 2 - bbox[1]
            x += offset_x
            y += offset_y

        # Draw the icon character
        draw.text((x, y), mdi_char, font=font, fill=color)

    def dim_color(self, color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
        """Dim a color by a factor.

        Args:
            color: RGB color tuple
            factor: Dimming factor (0-1, lower = dimmer)

        Returns:
            Dimmed RGB color
        """
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor),
        )

    def blend_color(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        factor: float = 0.5,
    ) -> tuple[int, int, int]:
        """Blend two colors.

        Args:
            color1: First RGB color
            color2: Second RGB color
            factor: Blend factor (0 = color1, 1 = color2)

        Returns:
            Blended RGB color
        """
        return (
            int(color1[0] + (color2[0] - color1[0]) * factor),
            int(color1[1] + (color2[1] - color1[1]) * factor),
            int(color1[2] + (color2[2] - color1[2]) * factor),
        )

    def get_text_size(
        self,
        text: str,
        font: FreeTypeFont | ImageFont.ImageFont | None = None,
    ) -> tuple[int, int]:
        """Get the size of rendered text including emoji.

        Args:
            text: Text to measure (can include emoji)
            font: Font to use for regular text

        Returns:
            (width, height) tuple (in final resolution)
        """
        if font is None:
            font = self.font_regular

        # Fast path: if no emoji, use simple measurement
        if not self._has_emoji(text):
            bbox = font.getbbox(text)
            if bbox:
                return int((bbox[2] - bbox[0]) / self._scale), int(
                    (bbox[3] - bbox[1]) / self._scale
                )
            return 0, 0

        # For mixed text, measure each segment
        segments = self._segment_text_by_font(text)
        if not segments:
            return 0, 0

        font_size = self._get_font_size(font)
        emoji_font = self.get_emoji_font(font_size)

        total_width = 0
        max_height = 0

        for segment_text, is_emoji in segments:
            segment_font = emoji_font if is_emoji else font
            bbox = segment_font.getbbox(segment_text)
            if bbox:
                total_width += bbox[2] - bbox[0]
                max_height = max(max_height, bbox[3] - bbox[1])

        return int(total_width / self._scale), int(max_height / self._scale)

    def finalize(self, img: Image.Image) -> Image.Image:
        """Finalize rendering by downscaling supersampled image.

        Args:
            img: PIL Image at supersampled resolution

        Returns:
            Final anti-aliased image at display resolution
        """
        return self._downscale(img)

    def to_jpeg(
        self,
        img: Image.Image,
        quality: int = DEFAULT_JPEG_QUALITY,
        max_size: int | None = None,
        rotation: int = 0,
    ) -> bytes:
        """Convert image to JPEG bytes with optional size cap.

        Args:
            img: PIL Image
            quality: JPEG quality (0-100)
            max_size: Maximum size in bytes (reduces quality if exceeded)
            rotation: Rotation in degrees (0, 90, 180, 270)

        Returns:
            JPEG image bytes
        """
        from .const import MAX_IMAGE_SIZE

        if max_size is None:
            max_size = MAX_IMAGE_SIZE

        # Finalize (downscale) before export
        final_img = self.finalize(img)

        # Apply rotation if specified
        if rotation:
            final_img = final_img.rotate(-rotation, expand=False)

        # Try at requested quality first
        buffer = BytesIO()
        final_img.save(buffer, format="JPEG", quality=quality)
        result = buffer.getvalue()

        # Reduce quality if size exceeds max
        current_quality = quality
        while len(result) > max_size and current_quality > 20:
            current_quality -= 10
            buffer = BytesIO()
            final_img.save(buffer, format="JPEG", quality=current_quality)
            result = buffer.getvalue()

        return result

    def to_png(self, img: Image.Image, rotation: int = 0) -> bytes:
        """Convert image to PNG bytes.

        Args:
            img: PIL Image
            rotation: Rotation in degrees (0, 90, 180, 270)

        Returns:
            PNG image bytes
        """
        # Finalize (downscale) before export
        final_img = self.finalize(img)

        # Apply rotation if specified
        if rotation:
            final_img = final_img.rotate(-rotation, expand=False)

        buffer = BytesIO()
        final_img.save(buffer, format="PNG")
        return buffer.getvalue()

    def draw_welcome_screen(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw a welcome screen when no configuration is set.

        Args:
            draw: ImageDraw instance
        """
        center_x = self.width // 2
        center_y = self.height // 2

        # Draw a subtle gradient-like background with concentric rounded rects
        for i in range(3):
            offset = i * 15
            shade = 30 - i * 8
            self.draw_rounded_rect(
                draw,
                (offset, offset, self.width - offset, self.height - offset),
                radius=20 - i * 5,
                fill=(shade, shade, shade + 5),
            )

        # Draw a decorative icon (gear/settings)
        icon_y = center_y - 50
        icon_size = 40
        gear_color = COLOR_CYAN

        # Draw gear circle
        self.draw_ellipse(
            draw,
            (
                center_x - icon_size // 2,
                icon_y - icon_size // 2,
                center_x + icon_size // 2,
                icon_y + icon_size // 2,
            ),
            outline=gear_color,
        )
        # Inner circle
        inner_size = icon_size // 3
        self.draw_ellipse(
            draw,
            (
                center_x - inner_size // 2,
                icon_y - inner_size // 2,
                center_x + inner_size // 2,
                icon_y + inner_size // 2,
            ),
            fill=gear_color,
        )

        # Draw gear teeth (8 small rectangles around the circle)
        tooth_len = 8
        tooth_width = 6

        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            # Tooth position (outside the circle)
            tx = center_x + int((icon_size // 2 + 2) * math.cos(rad))
            ty = icon_y + int((icon_size // 2 + 2) * math.sin(rad))
            # Draw small rectangle as tooth
            self.draw_rect(
                draw,
                (
                    tx - tooth_width // 2,
                    ty - tooth_len // 2,
                    tx + tooth_width // 2,
                    ty + tooth_len // 2,
                ),
                fill=gear_color,
            )

        # Title text
        self.draw_text(
            draw,
            "GeekMagic",
            (center_x, center_y + 10),
            font=self.font_large,
            color=COLOR_WHITE,
            anchor="mm",
        )

        # Subtitle
        self.draw_text(
            draw,
            "Home Assistant",
            (center_x, center_y + 35),
            font=self.font_small,
            color=COLOR_CYAN,
            anchor="mm",
        )

        # Instructions
        self.draw_text(
            draw,
            "Configure in",
            (center_x, center_y + 65),
            font=self.font_tiny,
            color=COLOR_GRAY,
            anchor="mm",
        )
        self.draw_text(
            draw,
            "Settings → Integrations",
            (center_x, center_y + 80),
            font=self.font_tiny,
            color=COLOR_GRAY,
            anchor="mm",
        )
