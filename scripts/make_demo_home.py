#!/usr/bin/env python3
"""Write the demo home the offline view renderer draws views against.

One coherent fake home covering every widget type: realistic states and
units, chart history, candles, a weather forecast, album art and a camera
picture. Output: ``skills/geekmagic-views/demo/`` (``home.json``, a states
file, plus the two pictures it names).

    uv run python scripts/make_demo_home.py [OUTPUT_DIR]

``tests/test_render_view.py`` checks the committed ``home.json`` matches.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_samples import create_fake_album_art, create_fake_camera_snapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

DEMO_DIR = Path(__file__).parent.parent / "skills" / "geekmagic-views" / "demo"
HOURS = 24


def wave(base: float, amp: float, *, phase: float = 0.0, digits: int = 1) -> list[float]:
    """One value per hour over a day: a sine around ``base``."""
    return [
        round(base + amp * math.sin(i / HOURS * 2 * math.pi + phase), digits) for i in range(HOURS)
    ]


def entity(state: Any, unit: str | None = None, name: str | None = None, **attrs: Any) -> dict:
    """An entity's state and attributes."""
    attributes: dict[str, Any] = {}
    if name:
        attributes["friendly_name"] = name
    if unit:
        attributes["unit_of_measurement"] = unit
    attributes.update(attrs)
    return {"state": str(state), "attributes": attributes}


def with_history(data: dict, history: Sequence[float]) -> dict:
    """An entity with a day of history (for charts and ``history()``)."""
    return {**data, "history": history}


def demo_home() -> dict[str, Any]:
    """The demo home as a states file."""
    solar = (
        [0] * 7 + [round(3200 * math.sin((i - 7) / 12 * math.pi)) for i in range(7, 19)] + [0] * 5
    )
    price = [0.14, 0.13, 0.12, 0.12, 0.13, 0.16, 0.22, 0.27, 0.25, 0.2, 0.17, 0.15]
    price += [0.14, 0.14, 0.15, 0.17, 0.21, 0.29, 0.31, 0.26, 0.21, 0.18, 0.16, 0.15]
    house = [
        round(0.4 + max(0, 3.4 * math.sin((i - 16) / 8 * math.pi)) + (1.2 if i in {7, 8} else 0), 2)
        for i in range(HOURS)
    ]
    candles, close = [], 94100.0
    for i in range(16):
        open_ = close
        close = round(open_ + 900 * math.sin(i * 0.9) + 250, 0)
        candles.append([open_, max(open_, close) + 420, min(open_, close) - 380, close])
    forecast = [
        ("sunny", 11, 3, 0),
        ("cloudy", 9, 4, 20),
        ("rainy", 8, 5, 80),
        ("partlycloudy", 10, 4, 10),
        ("sunny", 12, 2, 0),
    ]

    entities = {
        # Climate and air
        "sensor.living_room_temperature": with_history(
            entity(
                21.4, "°C", "Living room", device_class="temperature", state_class="measurement"
            ),
            wave(21, 0.8, phase=-1),
        ),
        "sensor.bedroom_temperature": entity(19.2, "°C", "Bedroom", device_class="temperature"),
        "sensor.kitchen_temperature": entity(22.1, "°C", "Kitchen", device_class="temperature"),
        "sensor.outdoor_temperature": with_history(
            entity(8.6, "°C", "Outdoor", device_class="temperature"), wave(7, 3.5, phase=-1.6)
        ),
        "sensor.living_room_humidity": entity(
            48, "%", "Living room humidity", device_class="humidity"
        ),
        "sensor.co2": with_history(
            entity(612, "ppm", "CO₂", device_class="carbon_dioxide"), wave(650, 180, digits=0)
        ),
        "sensor.air_quality_index": entity(34, None, "Air quality", device_class="aqi"),
        "climate.living_room": entity(
            "heat",
            None,
            "Living room",
            current_temperature=21.4,
            temperature=22,
            humidity=48,
            hvac_action="heating",
            hvac_modes=["off", "heat", "auto"],
        ),
        "climate.bedroom": entity(
            "off", None, "Bedroom", current_temperature=19.2, temperature=18, hvac_action="off"
        ),
        # Energy
        "sensor.power_consumption": with_history(
            entity(412, "W", "House power", device_class="power"),
            wave(520, 260, phase=2, digits=0),
        ),
        "sensor.house_power": with_history(entity(2.4, "kW", "House", device_class="power"), house),
        "sensor.solar_power": with_history(entity(2340, "W", "Solar", device_class="power"), solar),
        "sensor.energy_today": entity(7.8, "kWh", "Energy today", device_class="energy"),
        "sensor.home_battery": entity(81, "%", "Home battery", device_class="battery"),
        "sensor.electricity_price": with_history(entity(0.18, "€/kWh", "Electricity price"), price),
        "sensor.ev_charge": entity(72, "%", "EV battery", device_class="battery"),
        "binary_sensor.ev_charging": entity(
            "on", None, "EV charging", device_class="battery_charging"
        ),
        # Computer / network
        "sensor.cpu_load": with_history(entity(37, "%", "CPU"), wave(35, 20, phase=0.5, digits=0)),
        "sensor.memory_use": entity(62, "%", "Memory"),
        "sensor.disk_use": entity(71, "%", "Disk"),
        "sensor.download_speed": with_history(
            entity(48.2, "Mbit/s", "Download", device_class="data_rate"), wave(60, 30, phase=1.1)
        ),
        "sensor.phone_battery": entity(64, "%", "Phone", device_class="battery"),
        # Markets
        "sensor.btc_usd": {
            **entity(int(close), "USD", "Bitcoin"),
            "candles": candles,
            "history": [c[3] for c in candles],
        },
        # Lights, switches, covers, locks
        "light.living_room": entity(
            "on", None, "Living room", brightness=180, color_mode="brightness"
        ),
        "light.kitchen": entity("off", None, "Kitchen"),
        "light.bedroom": entity("on", None, "Bedroom", brightness=60),
        "switch.coffee_machine": entity("off", None, "Coffee machine"),
        "input_boolean.guest_mode": entity("off", None, "Guest mode"),
        "lock.front_door": entity("locked", None, "Front door"),
        "cover.garage_door": entity("closed", None, "Garage door", device_class="garage"),
        # Sensors
        "binary_sensor.front_door": entity("off", None, "Front door", device_class="door"),
        "binary_sensor.back_window": entity("on", None, "Back window", device_class="window"),
        "binary_sensor.hallway_motion": entity("on", None, "Hallway motion", device_class="motion"),
        "binary_sensor.kitchen_leak": entity("off", None, "Kitchen leak", device_class="moisture"),
        "binary_sensor.smoke": entity("off", None, "Smoke", device_class="smoke"),
        # People
        "person.alex": entity("home", None, "Alex"),
        "person.sam": entity("not_home", None, "Sam"),
        "device_tracker.alex_phone": entity("home", None, "Alex's phone"),
        # Weather, sun
        "weather.home": {
            **entity(
                "partlycloudy",
                None,
                "Home",
                temperature=8.6,
                temperature_unit="°C",
                humidity=71,
                wind_speed=14,
                wind_speed_unit="km/h",
                pressure=1016,
            ),
            "forecast": [
                {
                    "datetime": f"+{i}",
                    "condition": condition,
                    "temperature": high,
                    "templow": low,
                    "precipitation_probability": rain,
                }
                for i, (condition, high, low, rain) in enumerate(forecast)
            ],
        },
        "sun.sun": entity(
            "above_horizon",
            None,
            "Sun",
            next_rising="2026-11-17T07:12:00+00:00",
            next_setting="2026-11-16T16:04:00+00:00",
            elevation=18.4,
        ),
        # Media, camera
        "media_player.living_room": {
            **entity(
                "playing",
                None,
                "Living room speaker",
                media_title="Take Five",
                media_artist="Dave Brubeck",
                media_album_name="Time Out",
                media_duration=324,
                media_position=102,
                volume_level=0.4,
            ),
            "picture": "album.jpg",
        },
        "media_player.kitchen": entity(
            "paused",
            None,
            "Kitchen speaker",
            media_title="Imagine",
            media_artist="John Lennon",
            media_duration=183,
            media_position=78,
        ),
        "camera.front_door": {
            **entity("idle", None, "Front door camera"),
            "picture": "front_door.jpg",
        },
        # Transit, chores
        "sensor.next_bus": entity(
            "5 min",
            None,
            "Bus 42",
            route="42",
            destination="Downtown",
            departure="08:35",
            icon="mdi:bus",
        ),
        "sensor.next_train": entity(
            "18 min",
            None,
            "Express",
            route="EX",
            destination="Coast",
            departure="08:48",
            icon="mdi:train",
        ),
        "sensor.steps": entity(8432, "steps", "Steps"),
        "sensor.washing_machine_remaining": entity(
            23, "min", "Washing machine", device_class="duration"
        ),
    }
    return {"version": 1, "entities": entities}


def home_json() -> str:
    """``home.json`` exactly as committed."""
    return json.dumps(demo_home(), indent=1, ensure_ascii=False) + "\n"


def main() -> None:
    """Write the demo home and its pictures."""
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "home.json").write_text(home_json(), encoding="utf-8")
    create_fake_album_art(300).save(out / "album.jpg", quality=85)
    create_fake_camera_snapshot(320, 240).save(out / "front_door.jpg", quality=85)
    print(f"wrote {out} ({len(demo_home()['entities'])} entities)")


if __name__ == "__main__":
    main()
