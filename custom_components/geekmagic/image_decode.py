"""Decode a picture for the panel: bounded, upright, downscaled once.

Shared by every picture a frame shows (Image widget sources, image
entities, camera snapshots, album art) and by tools that render views
without Home Assistant, so it stays HA-free (Pillow only).
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

from .const import DISPLAY_HEIGHT, DISPLAY_WIDTH, SUPERSAMPLE_SCALE

# Refuse anything larger: a picture for a 240px panel has no business
# being tens of megabytes, and the bytes are held in memory to decode.
MAX_SOURCE_BYTES = 10 * 1024 * 1024
# Refuse to decode more pixels than this. The byte cap alone doesn't bound
# memory: a 10 MB PNG can declare 16k x 16k pixels and decode to ~1 GB
# before the downscale below runs, enough to take a Raspberry Pi's Home
# Assistant down. 25 MP (100 MB as RGBA) covers any real photo or logo;
# JPEGs are checked after libjpeg's reduced-scale draft, so large phone
# photos still load.
MAX_DECODE_PIXELS = 25_000_000
# Decoded pictures are downscaled so their SHORT side is at most the
# supersampled panel size (``cover`` in a full-screen cell stays sharp)
# and their long side is bounded (a panorama can't pin megabytes).
MAX_SHORT_SIDE = max(DISPLAY_WIDTH, DISPLAY_HEIGHT) * SUPERSAMPLE_SCALE
MAX_LONG_SIDE = 2 * MAX_SHORT_SIDE


class ImageSourceError(Exception):
    """A source that cannot be loaded (rejected path, HTTP error, ...)."""


def decode_image(data: bytes) -> Image.Image:
    """Decode a picture for display (blocking — run in the executor).

    Animated GIF/WebP/APNG show their FIRST frame: the device's animated
    path renders the whole screen at a fixed rate from a per-layer CSS
    clock, which has no way to step through a picture's own frames.

    EXIF orientation is applied (phone photos would otherwise lie on their
    side). Transparency is kept (logos sit on the theme background);
    everything else becomes RGB. The result is downscaled once here so
    renders never re-encode a full-size photo.

    Also decodes camera snapshots and album art (``frame``), whose bytes
    arrive without passing through this module's download cap.
    """
    if len(data) > MAX_SOURCE_BYTES:
        raise ImageSourceError(f"larger than {MAX_SOURCE_BYTES} bytes")
    image = Image.open(BytesIO(data))
    if image.format == "JPEG":
        # Let libjpeg decode at a reduced scale (still >= the target).
        image.draft("RGB", (MAX_SHORT_SIDE, MAX_SHORT_SIDE))
    # The header declares the size before any pixel is decoded.
    width, height = image.size
    if width * height > MAX_DECODE_PIXELS:
        raise ImageSourceError(
            f"{width}x{height} picture is too large to decode "
            f"(limit {MAX_DECODE_PIXELS // 1_000_000} megapixels)"
        )
    image.load()
    ImageOps.exif_transpose(image, in_place=True)
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA" if has_alpha else "RGB")
    width, height = image.size
    scale = min(1.0, MAX_SHORT_SIDE / min(width, height), MAX_LONG_SIDE / max(width, height))
    if scale < 1.0:
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image
