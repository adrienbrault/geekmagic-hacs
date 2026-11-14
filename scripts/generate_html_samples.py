#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate HTML widget sample images (requires blitz-py).

Run from the repo root:

    uv run python scripts/generate_html_samples.py

Prefer ``scripts/update_samples.py``, which runs every generator and
prunes stale files.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import MAX_IMAGE_SIZE
from custom_components.geekmagic.htmldoc import HAS_BLITZ
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid3x3
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import HtmlWidget, WidgetConfig
from custom_components.geekmagic.widgets.state import EntityState, WidgetState
from scripts.sample_io import save_gif_sample, save_sample

NOW = datetime(2026, 8, 6, 19, 42, 24, tzinfo=UTC)

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


# Entities for the gallery in docs/html-widget.md (scripts/html_examples/).
EXAMPLE_ENTITIES = {
    "sensor.car_battery": ("78", {"friendly_name": "Car", "unit_of_measurement": "%"}),
    "binary_sensor.car_charging": ("on", {"friendly_name": "Car charging"}),
    "sensor.car_charge_power": ("7.4", {"friendly_name": "Charge power"}),
    "sensor.car_range": ("312", {"friendly_name": "Range", "unit_of_measurement": "km"}),
    "sensor.solar_power": ("3.2", {"friendly_name": "Solar", "unit_of_measurement": "kW"}),
    "sensor.home_power": ("1.4", {"friendly_name": "Home", "unit_of_measurement": "kW"}),
    "sensor.grid_power": ("-1.8", {"friendly_name": "Grid", "unit_of_measurement": "kW"}),
    "sensor.next_trains": (
        "4",
        {
            "friendly_name": "Gare de Lyon",
            "departures": [
                {"line": "A", "destination": "Marne-la-Vallée", "minutes": 4, "delay": 0},
                {"line": "D", "destination": "Melun", "minutes": 9, "delay": 3},
                {"line": "R", "destination": "Montargis", "minutes": 16, "delay": 0},
                {"line": "A", "destination": "Boissy-St-Léger", "minutes": 21, "delay": 0},
                {"line": "D", "destination": "Corbeil", "minutes": 27, "delay": 0},
            ],
        },
    ),
    "sensor.living_temp": ("21.5", {"friendly_name": "Living", "unit_of_measurement": "°C"}),
    "sensor.bedroom_temp": ("18.6", {"friendly_name": "Bedroom", "unit_of_measurement": "°C"}),
    "sensor.office_temp": ("23.8", {"friendly_name": "Office", "unit_of_measurement": "°C"}),
    "sensor.kids_temp": ("20.2", {"friendly_name": "Kids", "unit_of_measurement": "°C"}),
    "sensor.bathroom_temp": ("24.6", {"friendly_name": "Bath", "unit_of_measurement": "°C"}),
    "person.alice": ("home", {"friendly_name": "Alice"}),
    "person.bob": ("not_home", {"friendly_name": "Bob"}),
    "person.chloe": ("home", {"friendly_name": "Chloé"}),
    "person.dan": ("Work", {"friendly_name": "Dan"}),
    "sensor.home_power_now": ("3.9", {"friendly_name": "Power now", "unit_of_measurement": "kW"}),
    "sensor.living_humidity": ("46", {"friendly_name": "Humidity", "unit_of_measurement": "%"}),
    "sensor.phone_battery": ("64", {"friendly_name": "Phone", "unit_of_measurement": "%"}),
    "climate.living_room": (
        "heat",
        {
            "friendly_name": "Living Room",
            "current_temperature": 19.5,
            "temperature": 21.5,
            "hvac_action": "heating",
        },
    ),
    "sensor.uv_index": ("6", {"friendly_name": "UV"}),
    "weather.nice": (
        "sunny",
        {
            "friendly_name": "Nice",
            "temperature": 27.6,
            "apparent_temperature": 29.2,
            "humidity": 54,
            "wind_speed": 11.0,
        },
    ),
    "sensor.move_calories": ("486", {"friendly_name": "Move", "unit_of_measurement": "kcal"}),
    "sensor.exercise_minutes": ("24", {"friendly_name": "Exercise", "unit_of_measurement": "min"}),
    "sensor.stand_hours": ("9", {"friendly_name": "Stand", "unit_of_measurement": "h"}),
    "sensor.home_battery": ("68", {"friendly_name": "Battery", "unit_of_measurement": "%"}),
    "sensor.home_battery_power": (
        "0.9",
        {"friendly_name": "Battery power", "unit_of_measurement": "kW"},
    ),
    "media_player.living_room": (
        "playing",
        {"friendly_name": "Living Room", "media_title": "Midnight City", "media_artist": "M83"},
    ),
    "weather.london": (
        "rainy",
        {"friendly_name": "London", "temperature": 12.6, "precipitation_probability": 80},
    ),
    "binary_sensor.doorbell": ("on", {"friendly_name": "Doorbell"}),
    "sensor.washer_remaining": ("38", {"friendly_name": "Washer", "unit_of_measurement": "min"}),
    "sensor.washer_progress": (
        "62",
        {"friendly_name": "Washer progress", "unit_of_measurement": "%"},
    ),
    "sensor.washer_phase": ("Rinse", {"friendly_name": "Washer phase"}),
    "sensor.wind_turbine_power": (
        "2.4",
        {"friendly_name": "Wind turbine", "unit_of_measurement": "kW"},
    ),
    "sensor.nordpool": (
        "0.31",
        {
            "friendly_name": "Electricity price",
            "unit_of_measurement": "EUR/kWh",
            "today": [
                0.14,
                0.12,
                0.11,
                0.09,
                0.08,
                0.09,
                0.13,
                0.21,
                0.27,
                0.24,
                0.19,
                0.16,
                0.15,
                0.14,
                0.16,
                0.18,
                0.22,
                0.29,
                0.34,
                0.31,
                0.26,
                0.21,
                0.18,
                0.15,
            ],
        },
    ),
    "sun.sun": (
        "above_horizon",
        {
            "friendly_name": "Sun",
            "next_rising": "2026-08-07T06:41:00+02:00",
            "next_setting": "2026-08-06T21:05:00+02:00",
        },
    ),
    "sensor.office_co2": ("912", {"friendly_name": "Office CO2", "unit_of_measurement": "ppm"}),
}

# (template file stem, the widget's entity, animated) — rendered fullscreen
# to samples/html/<stem>.png, or <stem>.gif for animated ones (2 s loop,
# Animate on). docs/html-widget.md embeds each file verbatim
# (tests/test_html_examples.py keeps them in sync).
EXAMPLES = [
    ("ev_charge", "sensor.car_battery", False),
    ("power_dial", "sensor.home_power_now", False),
    ("departures", "sensor.next_trains", False),
    ("room_bars", "sensor.living_temp", False),
    ("presence", "person.alice", False),
    ("air_quality", "sensor.office_co2", False),
    ("watch_face", "sensor.phone_battery", False),
    ("thermostat_dial", "climate.living_room", False),
    ("weather_glass", "weather.nice", False),
    ("energy_orbit", "sensor.solar_power", False),
    ("activity_rings", "sensor.move_calories", False),
    ("price_chart", "sensor.nordpool", False),
    ("sun_arc", "sun.sun", False),
    ("anim_radar", "person.alice", True),
    ("anim_vinyl", "media_player.living_room", True),
    ("anim_rain", "weather.london", True),
    ("anim_doorbell", "binary_sensor.doorbell", True),
    ("anim_washer", "sensor.washer_remaining", True),
    ("anim_lava", "sensor.living_temp", True),
    ("anim_turbine", "sensor.wind_turbine_power", True),
]
ANIMATION_LOOP_SECONDS = 2.0
EXAMPLES_DIR = Path(__file__).parent / "html_examples"


def entity_state(entity_id: str) -> EntityState:
    state, attrs = {**ENTITIES, **EXAMPLE_ENTITIES}[entity_id]
    return EntityState(entity_id, state, attrs)


def widget_state(primary: str) -> WidgetState:
    return WidgetState(
        entity=entity_state(primary),
        entities={eid: entity_state(eid) for eid in {**ENTITIES, **EXAMPLE_ENTITIES}},
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
    save_sample(renderer.finalize(img), path)


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

    # Template gallery (docs/html-widget.md)
    gallery = out / "html"
    gallery.mkdir(exist_ok=True)
    for stem, entity_id, animated in EXAMPLES:
        layout = FullscreenLayout()
        options: dict[str, object] = {"html": (EXAMPLES_DIR / f"{stem}.html").read_text()}
        if animated:
            options |= {"animate": True, "loop_seconds": ANIMATION_LOOP_SECONDS}
        layout.set_widget(
            0,
            HtmlWidget(
                WidgetConfig(widget_type="html", slot=0, entity_id=entity_id, options=options)
            ),
        )
        states = {0: widget_state(entity_id)}
        if not animated:
            render_layout(renderer, layout, states, gallery / f"{stem}.png")
            continue
        # Same frame timing as the coordinator's animated path
        # (ANIMATION_FPS = 10 for loops up to 2 s).
        fps = 10
        times = [i / fps for i in range(round(ANIMATION_LOOP_SECONDS * fps))]
        frames = layout.render_animation(renderer, states, times)
        if not frames:
            print(f"Animation render failed for {stem}")
            sys.exit(1)
        gif = renderer.to_gif(frames, fps=fps)
        # Over budget, the coordinator uploads a still instead: a sample
        # that big would show an animation the panel never plays.
        if len(gif) > MAX_IMAGE_SIZE:
            print(f"{stem}.gif is {len(gif)} bytes, over the {MAX_IMAGE_SIZE} upload budget")
            sys.exit(1)
        save_gif_sample(gif, gallery / f"{stem}.gif")


if __name__ == "__main__":
    main()
