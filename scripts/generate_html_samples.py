#!/usr/bin/env python3
# ruff: noqa: E501, SLF001
"""Generate HTML widget sample images (requires the optional blitz-py package).

Run from the repo root:

    uv run python scripts/generate_html_samples.py

Kept separate from generate_samples.py because blitz-py is an optional
dependency — without it the HTML widget renders an install placeholder
and these samples would be meaningless.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.htmldoc import HAS_BLITZ
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid3x3
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import HtmlWidget, WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState

NOW = datetime(2026, 8, 6, 19, 42, tzinfo=UTC)

ENTITIES = {
    "sensor.living_room_temperature": (
        "21.5",
        {"friendly_name": "Living Room", "unit_of_measurement": "°C"},
    ),
    "sensor.humidity": ("48", {"friendly_name": "Humidity", "unit_of_measurement": "%"}),
    "sensor.co2": ("612", {"friendly_name": "CO2", "unit_of_measurement": "ppm"}),
    "sensor.power": ("1.2", {"friendly_name": "Power", "unit_of_measurement": "kW"}),
    "climate.living_room": ("heat", {"friendly_name": "HVAC"}),
    "sensor.pm25": ("8", {"friendly_name": "PM2.5", "unit_of_measurement": "µg"}),
    "sensor.pressure": ("1013", {"friendly_name": "Pressure", "unit_of_measurement": "hPa"}),
    "sensor.wind": ("14", {"friendly_name": "Wind", "unit_of_measurement": "km/h"}),
    "sensor.uv": ("3", {"friendly_name": "UV Index", "unit_of_measurement": ""}),
}


def entity_state(entity_id: str) -> EntityState:
    state, attrs = ENTITIES[entity_id]
    return EntityState(entity_id, state, attrs)


def widget_state(primary: str) -> WidgetState:
    return WidgetState(
        entity=entity_state(primary),
        entities={eid: entity_state(eid) for eid in ENTITIES},
        now=NOW,
    )


# Modern fullscreen: radial backdrop, glowing hero card, translucent chips.
FULLSCREEN_HTML = """
<style>
body { background: radial-gradient(circle at 50% -20%, #1d2836, #0a0c10 65%); }
.wrap { height: 100%; display: flex; flex-direction: column;
        justify-content: space-between; padding: 10px; box-sizing: border-box; }
.top { display: flex; justify-content: space-between; align-items: baseline;
       white-space: nowrap; line-height: 1; }
.top .name { font-size: 17px; font-weight: 600; letter-spacing: 0.08em;
             color: var(--text-secondary); }
.top .time { font-size: 17px; font-weight: 600; color: var(--text-tertiary); }
.hero-card { margin: 0 4px; border-radius: 22px; text-align: center;
             padding: 12px 0 14px;
             background: rgba(255, 159, 10, 0.10);
             border: 1px solid rgba(255, 159, 10, 0.25);
             box-shadow: 0 0 36px rgba(255, 159, 10, 0.30); }
.hero-card .v { font-size: 68px; font-weight: 700; line-height: 1;
                letter-spacing: -0.03em; color: var(--warning); }
.hero-card .u { font-size: 26px; font-weight: 600; color: var(--text-secondary); }
.chips { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 7px; }
.chip { border-radius: 14px; padding: 8px 2px 9px; text-align: center;
        line-height: 1; background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.10); }
.chip .l { display: block; font-size: 12px; font-weight: 600; letter-spacing: 0.08em;
           color: var(--text-tertiary); }
/* 20px keeps "HEAT" inside a ~72px grid column — Blitz doesn't clip,
   so an oversized value bleeds off the panel edge. */
.chip .n { display: block; font-size: 20px; font-weight: 700; margin-top: 6px; }
.ok { color: var(--success); } .warn { color: var(--warning); } .info { color: var(--info); }
</style>
<div class="wrap">
  <div class="top"><span class="name">{{ name | upper }}</span><span class="time">{{ now.strftime('%H:%M') }}</span></div>
  <div class="hero-card"><span class="v">{{ state }}&deg;</span><span class="u">C</span></div>
  <div class="chips">
    <div class="chip"><div class="l">HUM</div><div class="n info">{{ states('sensor.humidity') }}%</div></div>
    <div class="chip"><div class="l">CO2</div><div class="n warn">{{ states('sensor.co2') }}</div></div>
    <div class="chip"><div class="l">HVAC</div><div class="n ok">{{ states('climate.living_room') | upper }}</div></div>
  </div>
</div>
"""

# One fluid template reused at every size: the fluid kit scales the hero
# with the cell (vmin/clamp) and sheds the caption/unit bands as the
# cell shrinks (hide-short / hide-small).
FLUID_CELL_HTML = """
<style>
.card { height: 100%; box-sizing: border-box; border-radius: 16px;
        background: linear-gradient(160deg, rgba(255,255,255,0.09), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.10); }
.hero { color: ACCENT; }
</style>
<div class="card cell">
  <div class="t-label hide-short">{{ name | upper }}</div>
  <div class="t-hero hero">{{ state }}SUFFIX</div>
  <div class="t-unit hide-small">EXTRA</div>
</div>
"""

FLUID_CELLS = [
    ("sensor.living_room_temperature", "var(--warning)", "&deg;", "feels 20&deg;"),
    ("sensor.humidity", "var(--info)", "%", "dew 10&deg;"),
    ("climate.living_room", "var(--success)", "", "target 21&deg;"),
    ("sensor.co2", "var(--text-primary)", "", "ppm"),
    ("sensor.power", "var(--warning)", "", "kW"),
    ("sensor.pm25", "var(--success)", "", "µg/m3"),
    ("sensor.pressure", "var(--info)", "", "hPa"),
    ("sensor.wind", "var(--text-primary)", "", "km/h"),
    ("sensor.uv", "var(--warning)", "", "index"),
]


def fluid_widget(slot: int, spec: tuple[str, str, str, str]) -> HtmlWidget:
    entity_id, accent, suffix, extra = spec
    template = (
        FLUID_CELL_HTML.replace("ACCENT", accent).replace("SUFFIX", suffix).replace("EXTRA", extra)
    )
    if entity_id == "climate.living_room":
        template = template.replace("{{ state }}", "{{ state | upper }}")
    return HtmlWidget(
        WidgetConfig(widget_type="html", slot=slot, entity_id=entity_id, options={"html": template})
    )


def render_layout(renderer: Renderer, layout, states: dict[int, WidgetState], path: Path) -> None:
    img, draw = renderer.create_canvas()
    layout.render(renderer, draw, states)
    renderer._downscale(img).save(path)
    print(f"  {path.name}")


def main() -> None:
    if not HAS_BLITZ:
        print("blitz-py is not installed - cannot generate HTML widget samples")
        sys.exit(1)

    out = Path(__file__).parent.parent / "samples"
    out.mkdir(exist_ok=True)
    renderer = Renderer()

    fullscreen = FullscreenLayout()
    fullscreen.set_widget(
        0,
        HtmlWidget(
            WidgetConfig(
                widget_type="html",
                slot=0,
                entity_id="sensor.living_room_temperature",
                options={"html": FULLSCREEN_HTML},
            )
        ),
    )
    render_layout(
        renderer,
        fullscreen,
        {0: widget_state("sensor.living_room_temperature")},
        out / "html_widget_fullscreen.png",
    )

    # Same fluid template at three densities
    single = FullscreenLayout()
    single.set_widget(0, fluid_widget(0, FLUID_CELLS[0]))
    render_layout(
        renderer,
        single,
        {0: widget_state(FLUID_CELLS[0][0])},
        out / "html_widget_fluid_1x1.png",
    )

    grid4 = Grid2x2()
    states4: dict[int, WidgetState] = {}
    for i in range(4):
        grid4.set_widget(i, fluid_widget(i, FLUID_CELLS[i]))
        states4[i] = widget_state(FLUID_CELLS[i][0])
    render_layout(renderer, grid4, states4, out / "html_widget_grid.png")

    grid9 = Grid3x3()
    states9: dict[int, WidgetState] = {}
    for i in range(9):
        grid9.set_widget(i, fluid_widget(i, FLUID_CELLS[i]))
        states9[i] = widget_state(FLUID_CELLS[i][0])
    render_layout(renderer, grid9, states9, out / "html_widget_fluid_3x3.png")


if __name__ == "__main__":
    main()
