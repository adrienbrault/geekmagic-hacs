"""Shared file handling for the sample generators.

Every sample PNG goes through :func:`save_sample`, which

* skips rewriting a file whose existing pixels match the new render within
  :data:`NOISE_TOLERANCE`, so only real visual changes produce git diffs, and
* records the path in :data:`PRODUCED`, so ``update_samples.py`` can prune
  any file under ``samples/`` that no generator produced.

Pillow-only on purpose: tests import it without loading the generators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageChops

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

# Max per-channel delta treated as "the same image". Rendering the committed
# (macOS) samples on linux/amd64 with the same blitz-py changed 33 of 194
# files, every one by at most 1 per channel (worst: 1.28% of pixels at
# delta 1) — float rounding noise across platforms. Real changes (text
# moving, colours changing) are far above 2.
NOISE_TOLERANCE = 2

# Every sample path written or confirmed unchanged during this process.
PRODUCED: set[Path] = set()


def max_channel_delta(a: Image.Image, b: Image.Image) -> int | None:
    """Largest per-channel absolute difference, or None if sizes differ."""
    if a.size != b.size:
        return None
    b = b.convert(a.mode)
    extrema = ImageChops.difference(a, b).getextrema()
    # Single-band images return (min, max); multi-band a tuple of pairs.
    if isinstance(extrema[0], tuple):
        return max(int(hi) for _, hi in extrema)
    return int(extrema[1])


def images_match(a: Image.Image, b: Image.Image, tolerance: int = NOISE_TOLERANCE) -> bool:
    """True when ``b`` is ``a`` up to cross-platform rounding noise."""
    delta = max_channel_delta(a, b)
    return delta is not None and delta <= tolerance


def save_sample(img: Image.Image, path: Path) -> None:
    """Write ``img`` to ``path`` unless the file already shows it."""
    PRODUCED.add(path.resolve())
    if path.exists():
        with Image.open(path) as existing:
            existing.load()
            if images_match(img, existing):
                print(f"Unchanged: {path}")
                return
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"Generated: {path}")


def gif_frames(data: bytes | Path) -> list[Image.Image]:
    """Decode every frame of a GIF (bytes or file) to RGB."""
    from io import BytesIO

    source = BytesIO(data) if isinstance(data, bytes) else data
    frames = []
    with Image.open(source) as gif:
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            frames.append(gif.convert("RGB"))
    return frames


def save_gif_sample(data: bytes, path: Path) -> None:
    """Write GIF ``data`` to ``path`` unless every frame already matches."""
    PRODUCED.add(path.resolve())
    if path.exists():
        new, old = gif_frames(data), gif_frames(path)
        if len(new) == len(old) and all(images_match(a, b) for a, b in zip(new, old, strict=True)):
            print(f"Unchanged: {path}")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"Generated: {path}")


def find_orphans(root: Path, produced: Iterable[Path]) -> list[Path]:
    """Files under ``root`` that are not in ``produced``, sorted."""
    keep = {p.resolve() for p in produced}
    return sorted(p for p in root.rglob("*") if p.is_file() and p.resolve() not in keep)


def prune(root: Path, produced: Iterable[Path]) -> list[Path]:
    """Delete orphan files and then any directories left empty."""
    orphans = find_orphans(root, produced)
    for path in orphans:
        path.unlink()
        print(f"Removed: {path}")
    for directory in sorted((d for d in root.rglob("*") if d.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    return orphans
