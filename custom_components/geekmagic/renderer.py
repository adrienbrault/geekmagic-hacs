"""Canvas and image encoding for the Blitz rendering pipeline.

All drawing happens in the Blitz engine (see ``htmldoc.py`` and
``layouts/base.py``); this module only provides the composite canvas
and JPEG/PNG encoding for the device upload.

The canvas is supersampled (``SUPERSAMPLE_SCALE``); Blitz renders each
pass at the matching device-pixel ratio, so the final downscale keeps
edges crisp.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from .const import (
    COLOR_BLACK,
    DEFAULT_JPEG_QUALITY,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    SUPERSAMPLE_SCALE,
)


class Renderer:
    """Provides the composite canvas and encodes the final image."""

    def __init__(self) -> None:
        """Initialize the renderer."""
        self.width = DISPLAY_WIDTH
        self.height = DISPLAY_HEIGHT
        self._scale = SUPERSAMPLE_SCALE
        self._scaled_width = self.width * self._scale
        self._scaled_height = self.height * self._scale

    @property
    def scale(self) -> int:
        """Return the supersampling scale factor."""
        return self._scale

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

    def to_gif(
        self,
        frames: list[Image.Image],
        fps: int = 10,
        rotation: int = 0,
    ) -> bytes:
        """Encode supersampled canvases as a looping animated GIF.

        Each frame is downscaled to display resolution and quantized to
        an adaptive palette without dithering (dither speckle shimmers
        between GIF frames and bloats the file).
        """
        if not frames:
            raise ValueError("to_gif needs at least one frame")
        finals = []
        for frame in frames:
            final = self.finalize(frame)
            if rotation:
                final = final.rotate(-rotation, expand=False)
            finals.append(final)
        # One palette for the whole loop: per-frame adaptive palettes
        # bloat the file and shimmer between frames. Sample a handful of
        # frames spread across the loop so animated hues are represented.
        sample_idx = sorted({0, len(finals) // 3, 2 * len(finals) // 3, len(finals) - 1})
        sampler = Image.new("RGB", (self.width, self.height * len(sample_idx)))
        for row, idx in enumerate(sample_idx):
            sampler.paste(finals[idx], (0, row * self.height))
        palette = sampler.quantize(colors=256, dither=Image.Dither.NONE)
        processed = [
            final.quantize(colors=256, palette=palette, dither=Image.Dither.NONE)
            for final in finals
        ]
        buffer = BytesIO()
        processed[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=processed[1:],
            duration=max(20, round(1000 / fps)),
            loop=0,
            optimize=True,
        )
        return buffer.getvalue()

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
