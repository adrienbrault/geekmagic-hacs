"""Frame timing of the animated (GIF) path, shared by every caller.

The coordinator, the sample generators and widgets that align their CSS
keyframes to the GIF's frames (the Rain Radar) all derive the frame grid
from here, so they can't drift apart. HA-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import ANIMATION_FPS, ANIMATION_SECONDS

# Loop bounds: shorter loops visibly jump, longer ones cost GIF size.
MIN_LOOP_SECONDS = 0.8
MAX_LOOP_SECONDS = 4.0
# Loops longer than this drop to SLOW_FPS (ambient animations don't need
# full temporal resolution, and the GIF stays within the upload budget).
FULL_RATE_MAX_SECONDS = 2.0
SLOW_FPS = 7


@dataclass(frozen=True)
class FrameTiming:
    """When a loop's GIF frames are sampled."""

    loop_seconds: float
    fps: int
    times: tuple[float, ...]

    @property
    def frame_count(self) -> int:
        """How many frames the GIF holds (the loop's "ticks")."""
        return len(self.times)


def frame_timing(loop_seconds: float | None = None) -> FrameTiming:
    """The frame grid of a loop of ``loop_seconds`` (None: the default loop).

    The loop is clamped to 0.8-4 s; up to 2 s it is sampled at
    ``ANIMATION_FPS``, longer loops at 7 fps. The clamp and the slow rate
    bound the GIF to 28 frames. Frame ``i`` shows the animation at
    ``i / fps`` seconds.
    """
    loop = loop_seconds or ANIMATION_SECONDS
    loop = min(MAX_LOOP_SECONDS, max(MIN_LOOP_SECONDS, loop))
    fps = ANIMATION_FPS if loop <= FULL_RATE_MAX_SECONDS else SLOW_FPS
    count = round(loop * fps)
    return FrameTiming(loop_seconds=loop, fps=fps, times=tuple(i / fps for i in range(count)))
