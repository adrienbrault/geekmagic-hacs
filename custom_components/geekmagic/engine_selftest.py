"""Engine self-test: one representative frame, in a throwaway process.

``engine_probe`` runs :func:`main` in a child Python before the engine
may load into Home Assistant (issue #262: a native crash in blitz-py
killed Core on every boot). It goes through the integration's real
pipeline — the engine accessor, process-wide font registration, the
``_textfit`` measurer (``measure_text`` + ``ellipsize``), and
``Layout.render`` (one ``render_layers`` call) and the preview's cell
checks (a reused ``Template`` and its ``boxes()``) — so the self-test
exercises the code a display runs, not a copy of it. The frame is
deliberately busy: the neon theme (gradient backdrop, overlay, a blurred
glow underlay per cell), text, an inline-SVG ring gauge and an embedded
image data URI.

Home-Assistant-free on purpose: the child imports the package's
submodules without its ``__init__`` (see ``engine_probe._BOOTSTRAP``).
Each stage is announced on stderr before it runs, and the child runs
with ``faulthandler`` on, so a native crash leaves the last stage and a
Python traceback in the output the parent logs.
"""

from __future__ import annotations

import logging
import math
import sys
from datetime import UTC, datetime

# Exit codes the parent reads. Anything else (including death by a
# signal) is a failure.
EXIT_OK = 0
# blitz-py is missing or below the pipeline floor: nothing native ran.
# Core keeps today's behaviour (the install-hint screen), no repair issue.
EXIT_NO_ENGINE = 3

_DISTINCT_COLORS_MIN = 64


def _stage(name: str) -> None:
    print(f"geekmagic engine self-test: {name}", file=sys.stderr, flush=True)


def render_frame() -> bytes:
    """Render the self-test frame through the real pipeline; return the JPEG.

    Raises when the engine answers but produced no real frame (the
    pipeline paints the bare background when a render fails).
    """
    from PIL import Image  # noqa: PLC0415

    from .htmldoc import font_param  # noqa: PLC0415
    from .layouts.grid import Grid2x2  # noqa: PLC0415
    from .renderer import Renderer  # noqa: PLC0415
    from .widgets import ClockWidget, EntityWidget, GaugeWidget, WidgetConfig  # noqa: PLC0415
    from .widgets._textfit import metrics_for  # noqa: PLC0415
    from .widgets.image import ImageWidget  # noqa: PLC0415
    from .widgets.state import EntityState, WidgetState  # noqa: PLC0415
    from .widgets.theme import THEMES  # noqa: PLC0415

    theme = THEMES["neon"]

    _stage("registering fonts")
    font_param()

    _stage("measuring text")
    metrics = metrics_for(theme)
    width = metrics.width("Living room 23.5°C", 20, "bold")
    if not math.isfinite(width) or width <= 0:
        raise RuntimeError(f"measure_text returned a degenerate width: {width!r}")
    fitted = metrics.truncate("A very long sensor name that cannot fit", 20, 80)
    if not fitted.endswith("…"):
        raise RuntimeError(f"ellipsize did not shorten the text: {fitted!r}")

    _stage("rendering a frame")
    gauge = EntityState("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    entity = EntityState(
        "sensor.living_room_temperature",
        "23.5",
        {"unit_of_measurement": "°C", "friendly_name": "Living room temperature sensor"},
    )
    picture = Image.linear_gradient("L").resize((48, 48)).convert("RGB")
    layout = Grid2x2()
    layout.theme = theme
    layout.set_widget(0, ClockWidget(WidgetConfig("clock", slot=0)))
    layout.set_widget(
        1,
        GaugeWidget(
            WidgetConfig("gauge", slot=1, entity_id=gauge.entity_id, options={"style": "ring"})
        ),
    )
    layout.set_widget(2, EntityWidget(WidgetConfig("entity", slot=2, entity_id=entity.entity_id)))
    layout.set_widget(3, ImageWidget(WidgetConfig("image", slot=3)))
    now = datetime(2026, 1, 1, 12, 34, tzinfo=UTC)
    states = {
        0: WidgetState(now=now),
        1: WidgetState(entity=gauge, now=now),
        2: WidgetState(entity=entity, now=now),
        3: WidgetState(image=picture, now=now),
    }
    renderer = Renderer()
    canvas, draw = renderer.create_canvas(background=theme.background)
    layout.render(renderer, draw, states)
    colors = canvas.getcolors(maxcolors=_DISTINCT_COLORS_MIN)
    if colors is not None:  # None: more colours than the cap — a real frame
        raise RuntimeError(f"the engine rendered a near-empty frame ({len(colors)} colours)")

    _stage("laying out a cell for the preview checks")
    from .cellcheck import text_overflow  # noqa: PLC0415

    if text_overflow(
        '<div style="white-space: nowrap; font-size: 80px">overflow</div>', 120, 120
    ) != ["overflow"]:
        raise RuntimeError("Template.boxes() did not report text past the cell")

    _stage("encoding")
    return renderer.to_jpeg(canvas)


def main() -> int:
    """Run the self-test; the exit code is the verdict."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    _stage("loading blitz_py")
    from .engine import engine_available, engine_version, get_engine  # noqa: PLC0415

    if get_engine() is None or not engine_available():
        _stage(f"no usable engine (installed version: {engine_version()})")
        return EXIT_NO_ENGINE

    jpeg = render_frame()
    _stage(f"ok ({len(jpeg)} bytes)")
    return EXIT_OK
