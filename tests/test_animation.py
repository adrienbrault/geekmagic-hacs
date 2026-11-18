"""``animation.frame_timing``: the one frame grid of the animated (GIF) path."""

from __future__ import annotations

import pytest

from custom_components.geekmagic.animation import frame_timing
from custom_components.geekmagic.const import ANIMATION_FPS, ANIMATION_SECONDS


def test_default_loop():
    timing = frame_timing(1.6)
    assert timing.fps == ANIMATION_FPS == 10
    assert timing.frame_count == 16
    assert timing.times[:3] == (0.0, 0.1, 0.2)


def test_long_loops_drop_to_seven_fps():
    timing = frame_timing(4.0)
    assert timing.fps == 7
    assert timing.frame_count == 28
    assert timing.times[-1] == pytest.approx(27 / 7)


def test_two_seconds_is_still_full_rate():
    timing = frame_timing(2.0)
    assert (timing.fps, timing.frame_count) == (10, 20)


@pytest.mark.parametrize(
    ("requested", "loop", "frames"),
    [(0.1, 0.8, 8), (60.0, 4.0, 28), (None, ANIMATION_SECONDS, 16), (0, ANIMATION_SECONDS, 16)],
)
def test_clamps_and_defaults(requested, loop, frames):
    timing = frame_timing(requested)
    assert timing.loop_seconds == loop
    assert timing.frame_count == frames


def test_a_long_loop_stays_at_28_frames():
    # The 4 s clamp at the slow 7 fps rate is what bounds the GIF: no loop,
    # however long it is asked to be, gets more frames than that.
    assert frame_timing(60.0).frame_count == 28
    assert max(frame_timing(s / 10).frame_count for s in range(1, 60)) == 28
