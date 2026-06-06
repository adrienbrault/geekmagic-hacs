#!/usr/bin/env python3
"""Generate sample dashboard images using the layout system and widgets.

This script generates sample images that represent what the integration
will actually render, using real layouts and widgets with mock Home Assistant data.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageChops

from custom_components.geekmagic.widgets.state import EntityState, WidgetState

if TYPE_CHECKING:
    from custom_components.geekmagic.layouts.base import Layout

from custom_components.geekmagic.const import (
    COLOR_CYAN,
    COLOR_GOLD,
    COLOR_GRAY,
    COLOR_LIME,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
    COLOR_YELLOW,
)
from custom_components.geekmagic.layouts.corner_hero import (
    HeroCornerBL,
    HeroCornerBR,
    HeroCornerTL,
    HeroCornerTR,
)
from custom_components.geekmagic.layouts.fullscreen import FullscreenLayout
from custom_components.geekmagic.layouts.grid import Grid2x2, Grid2x3, Grid3x2, Grid3x3
from custom_components.geekmagic.layouts.hero import HeroLayout
from custom_components.geekmagic.layouts.hero_simple import HeroSimpleLayout
from custom_components.geekmagic.layouts.sidebar import SidebarLeft, SidebarRight
from custom_components.geekmagic.layouts.split import (
    SplitHorizontal,
    SplitHorizontal1To2,
    SplitHorizontal2To1,
    SplitVertical,
    ThreeColumnLayout,
    ThreeRowLayout,
)
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import (
    CandlestickWidget,
    ChartWidget,
    ClockWidget,
    EntityWidget,
    GaugeWidget,
    MediaWidget,
    MultiProgressWidget,
    ProgressWidget,
    StatusListWidget,
    StatusWidget,
    WeatherWidget,
    WidgetConfig,
)
from custom_components.geekmagic.widgets.attribute_list import AttributeListWidget
from custom_components.geekmagic.widgets.climate import ClimateWidget
from custom_components.geekmagic.widgets.theme import THEMES
from scripts.mock_hass import (
    MockHass,
    create_battery_states,
    create_clock_states,
    create_energy_states,
    create_fitness_states,
    create_media_player_paused_states,
    create_media_player_states,
    create_network_states,
    create_security_states,
    create_server_stats_states,
    create_smart_home_states,
    create_system_monitor_states,
    create_thermostat_states,
    create_weather_states,
)

# Fixed sample time for reproducible clock displays (Wed Jan 15, 2025 10:30 AM)
SAMPLE_TIME = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


def build_widget_states(
    layout: Layout,
    hass: MockHass,
    chart_history: dict[int, list[float]] | None = None,
    images: dict[int, Image.Image] | None = None,
    now: datetime | None = None,
    candlestick_data: dict[int, list[tuple[float, float, float, float]]] | None = None,
) -> dict[int, WidgetState]:
    """Build WidgetState dict for all widgets in a layout.

    Args:
        layout: Layout with widgets assigned
        hass: MockHass with entity states
        chart_history: Optional dict mapping slot index to history data
        images: Optional dict mapping slot index to PIL images
        now: Optional fixed datetime for reproducible samples (defaults to current time)
        candlestick_data: Optional dict mapping slot index to OHLC candle data

    Returns:
        Dict mapping slot index to WidgetState
    """
    widget_states: dict[int, WidgetState] = {}
    chart_history = chart_history or {}
    images = images or {}
    candlestick_data = candlestick_data or {}

    # Use fixed time for reproducible samples (default to SAMPLE_TIME)
    sample_time = now if now is not None else SAMPLE_TIME

    for slot in layout.slots:
        if slot.widget is None:
            continue

        widget = slot.widget

        # Get primary entity
        entity_id = widget.config.entity_id
        entity: EntityState | None = None
        if entity_id:
            state = hass.states.get(entity_id)
            if state:
                entity = EntityState(
                    entity_id=entity_id,
                    state=state.state,
                    attributes=state.attributes,
                )

        # Get additional entities for multi-entity widgets
        entities: dict[str, EntityState] = {}
        try:
            entity_ids = widget.get_entities()
            for eid in entity_ids:
                if eid and eid != entity_id:
                    state = hass.states.get(eid)
                    if state:
                        entities[eid] = EntityState(
                            entity_id=eid,
                            state=state.state,
                            attributes=state.attributes,
                        )
        except AttributeError:
            pass

        # Get chart history for chart widgets
        history: list[float] = chart_history.get(slot.index, [])

        # Get forecast for weather widgets (from entity attributes for mock data)
        forecast: list[dict] = []
        if entity and widget.config.widget_type == "weather":
            forecast = entity.attributes.get("forecast", [])

        # Get image for this slot (for media/camera widgets)
        image = images.get(slot.index)

        # Get candlestick data
        candles: list[tuple[float, float, float, float]] = candlestick_data.get(slot.index, [])

        widget_states[slot.index] = WidgetState(
            entity=entity,
            entities=entities,
            history=history,
            candlestick_data=candles,
            forecast=forecast,
            image=image,
            now=sample_time,
        )

    return widget_states


def save_image(renderer: Renderer, img: Image.Image, name: str, output_dir: Path) -> None:
    """Save the rendered image to disk."""
    final = renderer.finalize(img)
    output_path = output_dir / f"{name}.png"
    if output_path.exists():
        with Image.open(output_path) as existing_img:
            existing = existing_img.convert(final.mode)
            if (
                existing.size == final.size
                and ImageChops.difference(existing, final).getbbox() is None
            ):
                print(f"Unchanged: {output_path}")
                return
    final.save(output_path)
    print(f"Generated: {output_path}")


def create_fake_album_art(size: int = 300) -> Image.Image:
    """Create a fake album art image with elegant abstract design.

    Generates a visually appealing image that looks like modern album artwork
    with smooth gradients, geometric shapes, and artistic composition.

    Args:
        size: Image size (square)

    Returns:
        PIL Image
    """
    from PIL import ImageDraw, ImageFilter

    # Create image
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)

    # Rich gradient colors (deep blue to magenta to warm coral)
    colors = [
        (15, 23, 42),  # Slate 900
        (88, 28, 135),  # Purple 900
        (157, 23, 77),  # Pink 900
        (194, 65, 12),  # Orange 800
        (251, 146, 60),  # Orange 400
    ]

    # Draw diagonal gradient for more visual interest
    for y in range(size):
        for x in range(size):
            # Diagonal position (0 to 1)
            diag_pos = (x + y) / (size * 2)

            # Map to color array
            pos = diag_pos * (len(colors) - 1)
            idx = min(int(pos), len(colors) - 2)
            t = pos - idx

            # Smooth interpolation
            c1, c2 = colors[idx], colors[idx + 1]
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            img.putpixel((x, y), (r, g, b))

    # Large soft circle (like a sun/moon)
    circle_radius = int(size * 0.35)
    circle_x = int(size * 0.55)
    circle_y = int(size * 0.45)

    # Draw circle with gradient fill
    for radius in range(circle_radius, 0, -1):
        # Fade from bright to background
        t = radius / circle_radius
        # Warm highlight color
        color = (
            int(255 * t + 194 * (1 - t)),
            int(200 * t + 65 * (1 - t)),
            int(150 * t + 12 * (1 - t)),
        )
        draw.ellipse(
            [circle_x - radius, circle_y - radius, circle_x + radius, circle_y + radius],
            fill=color,
        )

    # Add subtle arc lines for texture
    for i in range(3):
        arc_radius = int(size * (0.6 + i * 0.15))
        arc_center_x = int(size * 0.2)
        arc_center_y = int(size * 0.8)
        draw.arc(
            [
                arc_center_x - arc_radius,
                arc_center_y - arc_radius,
                arc_center_x + arc_radius,
                arc_center_y + arc_radius,
            ],
            start=-60,
            end=30,
            fill=(255, 255, 255),
            width=2,
        )

    # Apply slight blur for softness
    return img.filter(ImageFilter.GaussianBlur(radius=1))


def generate_widget_sizes(renderer: Renderer, output_dir: Path) -> None:
    """Generate full 240x240 layouts showing each widget type in different grid sizes."""
    from custom_components.geekmagic.layouts.grid import Grid3x3
    from custom_components.geekmagic.widgets.chart import ChartWidget
    from custom_components.geekmagic.widgets.clock import ClockWidget
    from custom_components.geekmagic.widgets.progress import ProgressWidget
    from custom_components.geekmagic.widgets.status import StatusWidget
    from custom_components.geekmagic.widgets.text import TextWidget
    from custom_components.geekmagic.widgets.weather import WeatherWidget

    widgets_dir = output_dir / "widgets"
    widgets_dir.mkdir(exist_ok=True)

    hass = MockHass()

    # Gauge entities (percentage-based system metrics)
    gauge_states = [
        ("sensor.cpu", "73", "CPU Usage"),
        ("sensor.memory", "62", "Memory"),
        ("sensor.disk", "45", "Disk"),
        ("sensor.gpu", "81", "GPU"),
        ("sensor.battery_phone", "92", "Battery"),
        ("sensor.network", "38", "Network"),
        ("sensor.fan", "65", "Fan"),
        ("sensor.power", "54", "Power"),
        ("sensor.brightness", "70", "Brightness"),
    ]
    for eid, state, name in gauge_states:
        hass.states.set(eid, state, {"unit_of_measurement": "%", "friendly_name": name})

    # Entity / chart sensor entities (varied units + icons). The icon is
    # stored on the entity so entity_plain (which has no icon override) shows
    # varied icons via _get_entity_icon falling back to the entity attribute.
    sensor_states = [
        ("sensor.temp", "23.5", "°C", "Temperature", "mdi:thermometer"),
        ("sensor.humidity", "48", "%", "Humidity", "mdi:water-percent"),
        ("sensor.pressure", "1013", "hPa", "Pressure", "mdi:gauge"),
        ("sensor.wind", "12", "km/h", "Wind", "mdi:weather-windy"),
        ("sensor.uv", "6", "UV", "UV Index", "mdi:weather-sunny"),
        ("sensor.aqi", "42", "AQI", "Air Quality", "mdi:leaf"),
        ("sensor.co2", "780", "ppm", "CO2", "mdi:molecule-co2"),
        ("sensor.lux", "320", "lx", "Light", "mdi:white-balance-sunny"),
        ("sensor.noise", "55", "dB", "Noise", "mdi:volume-high"),
    ]
    for eid, state, unit, name, icon in sensor_states:
        hass.states.set(
            eid,
            state,
            {"unit_of_measurement": unit, "friendly_name": name, "icon": icon},
        )

    # Progress goal entities
    progress_states = [
        ("sensor.steps", "8542", "steps", "Steps"),
        ("sensor.calories", "1840", "kcal", "Calories"),
        ("sensor.water", "6", "glass", "Water"),
        ("sensor.sleep", "7.2", "h", "Sleep"),
        ("sensor.distance", "5.4", "km", "Distance"),
        ("sensor.active_min", "47", "min", "Active"),
        ("sensor.floors", "12", "fl", "Floors"),
        ("sensor.workouts", "3", "x", "Workouts"),
        ("sensor.read_pages", "78", "pg", "Reading"),
    ]
    for eid, state, unit, name in progress_states:
        hass.states.set(eid, state, {"unit_of_measurement": unit, "friendly_name": name})

    # Binary sensor entities for status / chart_binary
    status_states = [
        ("binary_sensor.door", "on", "Front Door", "door"),
        ("binary_sensor.window", "off", "Window", "window"),
        ("binary_sensor.motion", "on", "Motion", "motion"),
        ("binary_sensor.lock", "off", "Lock", "lock"),
        ("binary_sensor.garage", "on", "Garage", "garage_door"),
        ("binary_sensor.smoke", "off", "Smoke", "smoke"),
        ("binary_sensor.leak", "off", "Leak", "moisture"),
        ("binary_sensor.presence", "on", "Presence", "presence"),
        ("binary_sensor.gas", "off", "Gas", "gas"),
    ]
    for eid, state, name, dc in status_states:
        hass.states.set(eid, state, {"friendly_name": name, "device_class": dc})

    # Weather entities (different cities + conditions). Temperatures are
    # floats like a real weather integration reports them: current temps
    # carry a sensor-style decimal, while daily forecast hi/lo are a natural
    # mix of whole (26.0) and fractional (23.5) values. Only the hero temp
    # keeps decimals; every secondary number is rounded to a whole integer.
    weather_variants = [
        (
            "weather.home",
            "sunny",
            "Paris",
            24.3,
            45,
            [("sunny", 26.0, 17.0), ("cloudy", 23.7, 15.0), ("rainy", 19.0, 12.3)],
        ),
        (
            "weather.london",
            "rainy",
            "London",
            13.8,
            82,
            [("rainy", 15.0, 9.0), ("cloudy", 16.8, 10.0), ("partlycloudy", 18.0, 11.2)],
        ),
        (
            "weather.tokyo",
            "cloudy",
            "Tokyo",
            19.1,
            60,
            [("cloudy", 20.0, 14.0), ("sunny", 22.6, 15.0), ("sunny", 24.0, 16.2)],
        ),
        (
            "weather.sydney",
            "partlycloudy",
            "Sydney",
            27.4,
            55,
            [("partlycloudy", 28.0, 20.0), ("sunny", 30.7, 21.0), ("sunny", 31.0, 22.3)],
        ),
        (
            "weather.nyc",
            "snowy",
            "New York",
            -2.2,
            70,
            [("snowy", -1.0, -6.0), ("snowy", 0.0, -4.3), ("cloudy", 3.0, -2.0)],
        ),
        (
            "weather.dubai",
            "sunny",
            "Dubai",
            38.6,
            20,
            [("sunny", 39.0, 28.0), ("sunny", 40.6, 29.0), ("sunny", 38.0, 27.4)],
        ),
        (
            "weather.berlin",
            "fog",
            "Berlin",
            8.4,
            88,
            [("fog", 9.0, 4.0), ("cloudy", 11.8, 5.0), ("rainy", 10.0, 6.2)],
        ),
        (
            "weather.rio",
            "lightning-rainy",
            "Rio",
            29.2,
            75,
            [("lightning-rainy", 30.0, 23.0), ("rainy", 28.6, 22.0), ("partlycloudy", 27.0, 21.3)],
        ),
        (
            "weather.oslo",
            "partlycloudy",
            "Oslo",
            3.1,
            65,
            [("partlycloudy", 4.0, -1.0), ("snowy", 1.7, -3.0), ("snowy", -1.0, -5.3)],
        ),
    ]
    base_dates = [f"2024-01-{day:02d}" for day in (15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26)]
    for eid, condition, name, temp, humidity, forecast in weather_variants:
        hass.states.set(
            eid,
            condition,
            {
                "friendly_name": name,
                "temperature": temp,
                "temperature_unit": "°C",
                "humidity": humidity,
                "forecast": [
                    {
                        "datetime": base_dates[i],
                        "condition": c,
                        "temperature": t,
                        "templow": tl,
                    }
                    for i, (c, t, tl) in enumerate(forecast)
                ],
            },
        )

    # Media player entities (different songs)
    media_variants = [
        ("media_player.spotify", "Bohemian Rhapsody", "Queen", "A Night at the Opera", 145, 354),
        ("media_player.kitchen", "Take Five", "Dave Brubeck", "Time Out", 102, 324),
        ("media_player.bedroom", "Imagine", "John Lennon", "Imagine", 78, 183),
        ("media_player.office", "Hotel California", "Eagles", "Hotel California", 210, 391),
        ("media_player.living", "Billie Jean", "Michael Jackson", "Thriller", 65, 294),
        ("media_player.studio", "Smells Like Teen Spirit", "Nirvana", "Nevermind", 188, 301),
        ("media_player.den", "Rolling in the Deep", "Adele", "21", 95, 228),
        ("media_player.patio", "Lose Yourself", "Eminem", "8 Mile", 142, 326),
        ("media_player.car", "Shape of You", "Ed Sheeran", "Divide", 50, 234),
    ]
    for eid, title, artist, album, pos, dur in media_variants:
        hass.states.set(
            eid,
            "playing",
            {
                "friendly_name": album,
                "media_title": title,
                "media_artist": artist,
                "media_album_name": album,
                "media_position": pos,
                "media_duration": dur,
            },
        )

    # Climate entities (different rooms)
    climate_variants = [
        ("climate.living", "Living Room", "heat", 21.5, 22, 58, "heating"),
        ("climate.bedroom", "Bedroom", "heat", 19.0, 20, 55, "heating"),
        ("climate.office", "Office", "cool", 24.5, 23, 50, "cooling"),
        ("climate.kitchen", "Kitchen", "off", 22.0, 22, 60, "off"),
        ("climate.bathroom", "Bathroom", "heat", 23.5, 24, 70, "idle"),
        ("climate.guest", "Guest Room", "heat_cool", 21.0, 22, 52, "idle"),
        ("climate.basement", "Basement", "cool", 18.5, 18, 65, "cooling"),
        ("climate.garage", "Garage", "off", 14.0, 16, 48, "off"),
        ("climate.attic", "Attic", "heat", 17.5, 19, 45, "heating"),
    ]
    for eid, name, state, current, target, hum, action in climate_variants:
        hass.states.set(
            eid,
            state,
            {
                "friendly_name": name,
                "current_temperature": current,
                "temperature": target,
                "humidity": hum,
                "hvac_action": action,
            },
        )

    # Attribute list entities (different bus / transit info)
    transit_variants = [
        ("sensor.bus_42", "5 min", "Bus 42", "42", "Downtown", "10:15", "mdi:bus"),
        ("sensor.bus_15", "12 min", "Bus 15", "15", "Airport", "10:22", "mdi:bus"),
        ("sensor.tram_3", "2 min", "Tram 3", "T3", "Central", "10:12", "mdi:tram"),
        ("sensor.metro_a", "8 min", "Metro A", "A", "North End", "10:18", "mdi:subway"),
        ("sensor.train_express", "18 min", "Express", "EX", "Coast", "10:28", "mdi:train"),
        ("sensor.bus_88", "3 min", "Bus 88", "88", "Stadium", "10:13", "mdi:bus"),
        ("sensor.tram_7", "9 min", "Tram 7", "T7", "Harbor", "10:19", "mdi:tram"),
        ("sensor.metro_b", "15 min", "Metro B", "B", "Park", "10:25", "mdi:subway"),
        ("sensor.bus_5", "1 min", "Bus 5", "5", "City Hall", "10:11", "mdi:bus"),
    ]
    for eid, state, name, route, dest, arr, icon in transit_variants:
        hass.states.set(
            eid,
            state,
            {
                "friendly_name": name,
                "route_name": route,
                "destination": dest,
                "next_arrival": arr,
                "icon": icon,
            },
        )

    # Candlestick / financial entities
    finance_variants = [
        ("sensor.btc", "116.0", "$", "Bitcoin"),
        ("sensor.eth", "3450", "$", "Ethereum"),
        ("sensor.aapl", "189.5", "$", "Apple"),
        ("sensor.tsla", "245.8", "$", "Tesla"),
        ("sensor.gold", "2310", "$", "Gold"),
        ("sensor.sp500", "5210", "$", "S&P 500"),
        ("sensor.nasdaq", "16420", "$", "Nasdaq"),
        ("sensor.eur_usd", "1.085", "$", "EUR/USD"),
        ("sensor.oil", "78.4", "$", "Oil"),
    ]
    for eid, state, unit, name in finance_variants:
        hass.states.set(eid, state, {"unit_of_measurement": unit, "friendly_name": name})

    # Create fake album art for media widget
    media_album_art = create_fake_album_art(300)

    # Variant tables — each slot picks a different entry by `slot % len`.
    gauge_variants = [
        ("sensor.cpu", "CPU", COLOR_CYAN, "chip"),
        ("sensor.memory", "RAM", COLOR_PURPLE, "memory"),
        ("sensor.disk", "Disk", COLOR_ORANGE, "harddisk"),
        ("sensor.gpu", "GPU", COLOR_LIME, "chip"),
        ("sensor.battery_phone", "Batt", COLOR_YELLOW, "battery"),
        ("sensor.network", "Net", COLOR_TEAL, "wifi"),
        ("sensor.fan", "Fan", COLOR_GRAY, "fan"),
        ("sensor.power", "Pwr", COLOR_RED, "flash"),
        ("sensor.brightness", "Brt", COLOR_GOLD, "brightness"),
    ]
    sensor_variants = [
        ("sensor.temp", "Temp", COLOR_ORANGE, "thermometer"),
        ("sensor.humidity", "Humidity", COLOR_CYAN, "water-percent"),
        ("sensor.pressure", "Pressure", COLOR_PURPLE, "gauge"),
        ("sensor.wind", "Wind", COLOR_TEAL, "weather-windy"),
        ("sensor.uv", "UV", COLOR_YELLOW, "weather-sunny"),
        ("sensor.aqi", "AQI", COLOR_LIME, "leaf"),
        ("sensor.co2", "CO2", COLOR_GRAY, "molecule-co2"),
        ("sensor.lux", "Light", COLOR_GOLD, "white-balance-sunny"),
        ("sensor.noise", "Noise", COLOR_RED, "volume-high"),
    ]
    progress_variants = [
        ("sensor.steps", "Steps", COLOR_LIME, "heart", 10000),
        ("sensor.calories", "Calories", COLOR_RED, "fire", 2400),
        ("sensor.water", "Water", COLOR_CYAN, "cup-water", 8),
        ("sensor.sleep", "Sleep", COLOR_PURPLE, "sleep", 8),
        ("sensor.distance", "Distance", COLOR_ORANGE, "run", 10),
        ("sensor.active_min", "Active", COLOR_YELLOW, "run-fast", 60),
        ("sensor.floors", "Floors", COLOR_TEAL, "stairs", 20),
        ("sensor.workouts", "Workouts", COLOR_GOLD, "dumbbell", 5),
        ("sensor.read_pages", "Reading", COLOR_GRAY, "book-open", 100),
    ]
    status_variants = [
        ("binary_sensor.door", "Door", COLOR_LIME, "lock"),
        ("binary_sensor.window", "Window", COLOR_CYAN, "window-closed"),
        ("binary_sensor.motion", "Motion", COLOR_ORANGE, "motion-sensor"),
        ("binary_sensor.lock", "Lock", COLOR_PURPLE, "lock"),
        ("binary_sensor.garage", "Garage", COLOR_YELLOW, "garage"),
        ("binary_sensor.smoke", "Smoke", COLOR_RED, "smoke-detector"),
        ("binary_sensor.leak", "Leak", COLOR_TEAL, "water"),
        ("binary_sensor.presence", "Home", COLOR_GOLD, "home"),
        ("binary_sensor.gas", "Gas", COLOR_GRAY, "fire"),
    ]
    weather_entities = [
        "weather.home",
        "weather.london",
        "weather.tokyo",
        "weather.sydney",
        "weather.nyc",
        "weather.dubai",
        "weather.berlin",
        "weather.rio",
        "weather.oslo",
    ]
    media_entities = [v[0] for v in media_variants]
    climate_entities = [v[0] for v in climate_variants]
    transit_entities = [v[0] for v in transit_variants]
    finance_entity_variants = [
        ("sensor.btc", "Bitcoin"),
        ("sensor.eth", "Ethereum"),
        ("sensor.aapl", "Apple"),
        ("sensor.tsla", "Tesla"),
        ("sensor.gold", "Gold"),
        ("sensor.sp500", "S&P 500"),
        ("sensor.nasdaq", "Nasdaq"),
        ("sensor.eur_usd", "EUR/USD"),
        ("sensor.oil", "Oil"),
    ]
    text_variants = [
        ("Hello", COLOR_CYAN),
        ("Welcome", COLOR_LIME),
        ("Online", COLOR_GOLD),
        ("Ready", COLOR_PURPLE),
        ("Active", COLOR_ORANGE),
        ("Status", COLOR_TEAL),
        ("Connected", COLOR_YELLOW),
        ("Live", COLOR_RED),
        ("Standby", COLOR_GRAY),
    ]
    clock_variants = [
        {"show_date": True, "time_format": "24h"},
        {"show_date": False, "time_format": "24h", "show_seconds": True},
        {"show_date": True, "time_format": "12h"},
        {"show_date": False, "time_format": "12h", "show_seconds": True},
        {"show_date": True, "time_format": "24h", "show_seconds": True},
        {"show_date": False, "time_format": "24h"},
        {"show_date": True, "time_format": "12h", "show_seconds": True},
        {"show_date": False, "time_format": "12h"},
        {"show_date": True, "time_format": "24h"},
    ]
    clock_colors = [
        COLOR_WHITE,
        COLOR_CYAN,
        COLOR_LIME,
        COLOR_GOLD,
        COLOR_PURPLE,
        COLOR_ORANGE,
        COLOR_TEAL,
        COLOR_YELLOW,
        COLOR_RED,
    ]
    attribute_list_options = [
        ("Bus 42", [("route_name", "Route"), ("destination", "To"), ("state", "Arrives")]),
        ("Bus 15", [("route_name", "Line"), ("destination", "Bound"), ("next_arrival", "At")]),
        ("Tram 3", [("route_name", "Line"), ("destination", "To"), ("state", "ETA")]),
        ("Metro A", [("route_name", "Line"), ("destination", "To"), ("state", "Arrives")]),
        ("Express", [("route_name", "Service"), ("destination", "To"), ("next_arrival", "Dep")]),
        ("Bus 88", [("route_name", "Route"), ("destination", "To"), ("state", "ETA")]),
        ("Tram 7", [("route_name", "Line"), ("destination", "To"), ("state", "Arrives")]),
        ("Metro B", [("route_name", "Line"), ("destination", "Stop"), ("next_arrival", "At")]),
        ("Bus 5", [("route_name", "Route"), ("destination", "To"), ("state", "ETA")]),
    ]

    def pick(seq, slot):
        return seq[slot % len(seq)]

    def make_gauge_bar(slot: int) -> GaugeWidget:
        eid, label, color, icon = pick(gauge_variants, slot)
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"style": "bar", "icon": icon},
            )
        )

    def make_gauge_ring(slot: int) -> GaugeWidget:
        eid, label, color, _icon = pick(gauge_variants, slot)
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"style": "ring"},
            )
        )

    def make_gauge_arc(slot: int) -> GaugeWidget:
        eid, label, color, _icon = pick(gauge_variants, slot)
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"style": "arc"},
            )
        )

    def make_entity_icon(slot: int) -> EntityWidget:
        eid, label, color, icon = pick(sensor_variants, slot)
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"icon": icon},
            )
        )

    def make_entity_plain(slot: int) -> EntityWidget:
        eid, label, color, _icon = pick(sensor_variants, slot)
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={},
            )
        )

    def make_clock(slot: int) -> ClockWidget:
        return ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=slot,
                color=pick(clock_colors, slot),
                options=dict(pick(clock_variants, slot)),
            )
        )

    def make_text(slot: int) -> TextWidget:
        text, color = pick(text_variants, slot)
        return TextWidget(
            WidgetConfig(
                widget_type="text",
                slot=slot,
                color=color,
                options={"text": text},
            )
        )

    def make_progress(slot: int) -> ProgressWidget:
        eid, label, color, icon, target = pick(progress_variants, slot)
        return ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"target": target, "icon": icon},
            )
        )

    def make_weather(slot: int) -> WeatherWidget:
        return WeatherWidget(
            WidgetConfig(
                widget_type="weather",
                slot=slot,
                entity_id=pick(weather_entities, slot),
                color=COLOR_YELLOW,
                options={"show_forecast": True, "forecast_days": 3},
            )
        )

    def make_status(slot: int) -> StatusWidget:
        eid, label, color, icon = pick(status_variants, slot)
        return StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={"icon": icon},
            )
        )

    def make_chart(slot: int) -> ChartWidget:
        eid, label, color, _icon = pick(sensor_variants, slot)
        return ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={},
            )
        )

    def make_chart_binary(slot: int) -> ChartWidget:
        eid, label, color, _icon = pick(status_variants, slot)
        return ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id=eid,
                label=label,
                color=color,
                options={},
            )
        )

    def make_candlestick(slot: int) -> CandlestickWidget:
        eid, label = pick(finance_entity_variants, slot)
        return CandlestickWidget(
            WidgetConfig(
                widget_type="candlestick",
                slot=slot,
                entity_id=eid,
                label=label,
                options={"candle_count": 15},
            )
        )

    def make_media(slot: int) -> MediaWidget:
        return MediaWidget(
            WidgetConfig(
                widget_type="media",
                slot=slot,
                entity_id=pick(media_entities, slot),
                color=COLOR_CYAN,
                options={"show_album_art": True, "show_artist": True, "show_progress": True},
            )
        )

    def make_climate(slot: int) -> ClimateWidget:
        return ClimateWidget(
            WidgetConfig(
                widget_type="climate",
                slot=slot,
                entity_id=pick(climate_entities, slot),
                color=COLOR_ORANGE,
                options={"show_target": True, "show_humidity": True, "show_mode": True},
            )
        )

    def make_attribute_list(slot: int) -> AttributeListWidget:
        title, attrs = pick(attribute_list_options, slot)
        return AttributeListWidget(
            WidgetConfig(
                widget_type="attribute_list",
                slot=slot,
                entity_id=pick(transit_entities, slot),
                color=COLOR_CYAN,
                options={
                    "title": title,
                    "attributes": [{"key": k, "label": lab} for k, lab in attrs],
                },
            )
        )

    # Chart history data — list of histories per widget_name; each slot picks
    # one by `slot % len(histories)` so different instances show different
    # trends.
    chart_histories: dict[str, list[list[float]]] = {
        "chart": [
            [20, 21, 22, 21, 23, 24, 23, 22, 21, 22, 23, 24],
            [42, 45, 48, 50, 49, 47, 46, 48, 51, 53, 52, 50],
            [1010, 1011, 1012, 1013, 1013, 1014, 1015, 1014, 1013, 1012, 1013, 1014],
            [5, 7, 9, 12, 14, 13, 11, 9, 8, 10, 12, 13],
            [2, 3, 4, 5, 6, 6, 7, 6, 5, 4, 3, 2],
            [38, 40, 42, 44, 46, 44, 42, 41, 43, 45, 47, 46],
            [720, 750, 770, 800, 820, 810, 790, 780, 760, 740, 730, 720],
            [320, 340, 360, 380, 360, 340, 320, 310, 300, 320, 340, 360],
            [50, 52, 55, 58, 60, 58, 55, 53, 51, 50, 52, 54],
        ],
        "chart_binary": [
            [0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0],
            [0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0],
            [1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1],
            [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            [0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
        ],
    }

    # Candlestick OHLC data — list of histories per widget_name; each slot
    # picks one so different instances show different price action.
    candlestick_histories: dict[str, list[list[tuple[float, float, float, float]]]] = {
        "candlestick": [
            [
                (100, 108, 97, 105),
                (105, 112, 103, 110),
                (110, 111, 102, 103),
                (103, 107, 100, 106),
                (106, 115, 104, 113),
                (113, 118, 110, 112),
                (112, 114, 105, 107),
                (107, 109, 98, 99),
                (99, 106, 96, 104),
                (104, 110, 103, 109),
                (109, 116, 108, 115),
                (115, 120, 112, 118),
                (118, 119, 110, 111),
                (111, 113, 107, 112),
                (112, 117, 109, 116),
            ],
            [
                (3300, 3380, 3280, 3350),
                (3350, 3420, 3340, 3400),
                (3400, 3450, 3380, 3390),
                (3390, 3410, 3320, 3330),
                (3330, 3360, 3290, 3300),
                (3300, 3360, 3290, 3350),
                (3350, 3470, 3340, 3460),
                (3460, 3510, 3440, 3500),
                (3500, 3530, 3470, 3480),
                (3480, 3500, 3420, 3430),
                (3430, 3460, 3400, 3450),
                (3450, 3490, 3440, 3470),
                (3470, 3500, 3450, 3490),
                (3490, 3520, 3460, 3470),
                (3470, 3500, 3440, 3450),
            ],
            [
                (180, 184, 178, 182),
                (182, 186, 180, 185),
                (185, 188, 183, 184),
                (184, 187, 181, 183),
                (183, 188, 182, 187),
                (187, 192, 185, 190),
                (190, 193, 188, 189),
                (189, 191, 184, 185),
                (185, 188, 183, 187),
                (187, 190, 185, 189),
                (189, 193, 188, 192),
                (192, 196, 190, 194),
                (194, 195, 188, 189),
                (189, 191, 185, 188),
                (188, 190, 184, 189),
            ],
            [
                (240, 252, 235, 248),
                (248, 256, 244, 246),
                (246, 250, 238, 240),
                (240, 244, 232, 235),
                (235, 245, 230, 244),
                (244, 258, 242, 256),
                (256, 264, 252, 254),
                (254, 256, 244, 246),
                (246, 252, 240, 250),
                (250, 260, 248, 258),
                (258, 268, 256, 266),
                (266, 270, 258, 260),
                (260, 264, 248, 250),
                (250, 256, 244, 252),
                (252, 258, 246, 245),
            ],
            [
                (2280, 2310, 2270, 2300),
                (2300, 2330, 2290, 2320),
                (2320, 2340, 2300, 2310),
                (2310, 2325, 2285, 2295),
                (2295, 2315, 2280, 2310),
                (2310, 2335, 2305, 2330),
                (2330, 2350, 2320, 2325),
                (2325, 2340, 2300, 2305),
                (2305, 2320, 2295, 2315),
                (2315, 2340, 2310, 2335),
                (2335, 2360, 2330, 2350),
                (2350, 2365, 2335, 2340),
                (2340, 2350, 2310, 2315),
                (2315, 2330, 2305, 2325),
                (2325, 2345, 2315, 2310),
            ],
            [
                (5100, 5160, 5080, 5140),
                (5140, 5200, 5130, 5180),
                (5180, 5220, 5170, 5200),
                (5200, 5230, 5180, 5190),
                (5190, 5210, 5150, 5160),
                (5160, 5200, 5150, 5195),
                (5195, 5240, 5190, 5230),
                (5230, 5260, 5220, 5250),
                (5250, 5275, 5230, 5240),
                (5240, 5260, 5210, 5220),
                (5220, 5240, 5190, 5200),
                (5200, 5230, 5195, 5225),
                (5225, 5260, 5220, 5255),
                (5255, 5280, 5245, 5270),
                (5270, 5290, 5250, 5260),
            ],
            [
                (16100, 16250, 16050, 16200),
                (16200, 16350, 16180, 16320),
                (16320, 16400, 16280, 16290),
                (16290, 16330, 16200, 16220),
                (16220, 16280, 16180, 16270),
                (16270, 16400, 16260, 16380),
                (16380, 16450, 16360, 16420),
                (16420, 16470, 16400, 16430),
                (16430, 16480, 16380, 16390),
                (16390, 16430, 16330, 16350),
                (16350, 16400, 16320, 16380),
                (16380, 16440, 16370, 16420),
                (16420, 16470, 16400, 16410),
                (16410, 16450, 16380, 16440),
                (16440, 16490, 16420, 16480),
            ],
            [
                (1.080, 1.085, 1.078, 1.083),
                (1.083, 1.088, 1.082, 1.087),
                (1.087, 1.090, 1.083, 1.084),
                (1.084, 1.086, 1.078, 1.080),
                (1.080, 1.084, 1.077, 1.083),
                (1.083, 1.089, 1.082, 1.088),
                (1.088, 1.092, 1.086, 1.087),
                (1.087, 1.089, 1.082, 1.083),
                (1.083, 1.086, 1.080, 1.085),
                (1.085, 1.089, 1.084, 1.088),
                (1.088, 1.092, 1.087, 1.090),
                (1.090, 1.094, 1.088, 1.085),
                (1.085, 1.087, 1.080, 1.082),
                (1.082, 1.085, 1.078, 1.084),
                (1.084, 1.088, 1.082, 1.085),
            ],
            [
                (75, 78, 73, 77),
                (77, 80, 76, 79),
                (79, 81, 77, 78),
                (78, 79, 74, 75),
                (75, 78, 73, 77),
                (77, 82, 76, 81),
                (81, 84, 80, 82),
                (82, 83, 78, 79),
                (79, 81, 77, 80),
                (80, 83, 79, 82),
                (82, 85, 81, 84),
                (84, 86, 82, 83),
                (83, 84, 78, 79),
                (79, 81, 76, 80),
                (80, 82, 78, 78),
            ],
        ],
    }

    # Widget configs: (name, factory)
    widget_types = [
        ("gauge_bar", make_gauge_bar),
        ("gauge_ring", make_gauge_ring),
        ("gauge_arc", make_gauge_arc),
        ("entity_icon", make_entity_icon),
        ("entity_plain", make_entity_plain),
        ("clock", make_clock),
        ("text", make_text),
        ("progress", make_progress),
        ("weather", make_weather),
        ("status", make_status),
        ("chart", make_chart),
        ("chart_binary", make_chart_binary),
        ("candlestick", make_candlestick),
        ("media", make_media),
        ("climate", make_climate),
        ("attribute_list", make_attribute_list),
    ]

    # Layout configs: (suffix, layout_class, num_slots, padding, gap)
    layouts = [
        ("1x1", None, 1, 8, 8),  # Single widget
        ("1x2", SplitHorizontal, 2, 8, 8),  # 2 side-by-side
        ("2x1", SplitVertical, 2, 8, 8),  # 2 stacked
        ("2x2", Grid2x2, 4, 8, 8),
        ("2x3", Grid2x3, 6, 8, 8),
        ("3x2", Grid3x2, 6, 8, 8),  # 3 rows, 2 columns
        ("3x3", Grid3x3, 9, 6, 6),
    ]

    for widget_name, make_widget in widget_types:
        for layout_suffix, layout_class, num_slots, padding, gap in layouts:
            img, draw = renderer.create_canvas()

            if layout_suffix == "1x1":
                # Single widget using hero layout with minimal footer
                layout = HeroLayout(footer_slots=1, hero_ratio=1.0, padding=padding, gap=gap)
                layout.set_widget(0, make_widget(0))
            elif layout_suffix == "1x2":
                layout = SplitHorizontal(ratio=0.5, padding=padding, gap=gap)
                for i in range(2):
                    layout.set_widget(i, make_widget(i))
            elif layout_suffix == "2x1":
                layout = SplitVertical(ratio=0.5, padding=padding, gap=gap)
                for i in range(2):
                    layout.set_widget(i, make_widget(i))
            else:
                assert layout_class is not None
                layout = layout_class(padding=padding, gap=gap)
                for i in range(num_slots):
                    layout.set_widget(i, make_widget(i))

            # Build chart_history for all slots if this is a chart widget
            slot_chart_history: dict[int, list[float]] = {}
            if widget_name in chart_histories:
                histories = chart_histories[widget_name]
                for i in range(num_slots):
                    slot_chart_history[i] = histories[i % len(histories)]

            # Build candlestick_data for all slots if this is a candlestick widget
            slot_candlestick: dict[int, list[tuple[float, float, float, float]]] = {}
            if widget_name in candlestick_histories:
                candle_data = candlestick_histories[widget_name]
                for i in range(num_slots):
                    slot_candlestick[i] = candle_data[i % len(candle_data)]

            # Build images dict for media widgets
            slot_images: dict[int, Image.Image] = {}
            if widget_name == "media":
                for i in range(num_slots):
                    slot_images[i] = media_album_art

            layout.render(
                renderer,
                draw,
                build_widget_states(
                    layout,
                    hass,
                    slot_chart_history,
                    images=slot_images,
                    candlestick_data=slot_candlestick,
                ),
            )
            save_image(renderer, img, f"{widget_name}_{layout_suffix}", widgets_dir)

    print(f"Generated widget size samples in {widgets_dir}")


def generate_system_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate system monitor dashboard using Grid2x2 layout with GaugeWidgets."""
    hass = MockHass()
    create_system_monitor_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # CPU gauge (slot 0 - top left)
    cpu_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.cpu_usage",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "ring", "max": 100, "icon": "chip"},
        )
    )
    layout.set_widget(0, cpu_widget)

    # Memory gauge (slot 1 - top right)
    mem_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.memory_usage",
            label="Memory",
            color=COLOR_PURPLE,
            options={"style": "ring", "max": 100, "icon": "memory"},
        )
    )
    layout.set_widget(1, mem_widget)

    # Disk gauge (slot 2 - bottom left)
    disk_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.disk_usage",
            label="Disk",
            color=COLOR_ORANGE,
            options={"style": "bar", "max": 100, "icon": "harddisk"},
        )
    )
    layout.set_widget(2, disk_widget)

    # Network gauge (slot 3 - bottom right)
    net_widget = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=3,
            entity_id="sensor.network_throughput",
            label="Network",
            color=COLOR_LIME,
            options={"style": "bar", "max": 100, "icon": "network"},
        )
    )
    layout.set_widget(3, net_widget)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "01_system_monitor", output_dir)


def generate_smart_home(renderer: Renderer, output_dir: Path) -> None:
    """Generate smart home dashboard using Grid2x3 layout."""
    hass = MockHass()
    create_smart_home_states(hass)

    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Row 1: Device status widgets
    # Living Room Light (slot 0)
    light1 = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="light.living_room",
            label="Lights",
            color=COLOR_GOLD,
            options={"show_name": True, "icon": "lightbulb", "show_panel": True},
        )
    )
    layout.set_widget(0, light1)

    # Kitchen Light (slot 1)
    light2 = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="light.kitchen",
            label="Kitchen",
            color=COLOR_GRAY,
            options={"show_name": True, "icon": "lightbulb", "show_panel": True},
        )
    )
    layout.set_widget(1, light2)

    # AC status (slot 2)
    ac = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="climate.thermostat",
            label="AC",
            color=COLOR_CYAN,
            options={"show_name": True, "show_panel": True},
        )
    )
    layout.set_widget(2, ac)

    # Row 2: Sensors
    # Temperature (slot 3)
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.temperature",
            color=COLOR_ORANGE,
            options={"show_name": True, "show_unit": True, "show_panel": True},
        )
    )
    layout.set_widget(3, temp)

    # Humidity (slot 4)
    humidity = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=4,
            entity_id="sensor.humidity",
            color=COLOR_CYAN,
            options={"show_name": True, "show_unit": True, "icon": "water", "show_panel": True},
        )
    )
    layout.set_widget(4, humidity)

    # Lock status (slot 5)
    lock = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=5,
            entity_id="lock.front_door",
            label="Door",
            color=COLOR_LIME,
            options={"show_name": True, "icon": "lock", "show_panel": True},
        )
    )
    layout.set_widget(5, lock)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "02_smart_home", output_dir)


def generate_weather(renderer: Renderer, output_dir: Path) -> None:
    """Generate weather dashboard using HeroLayout."""
    hass = MockHass()
    create_weather_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.75, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Weather widget with forecast
    weather = WeatherWidget(
        WidgetConfig(
            widget_type="weather",
            slot=0,
            entity_id="weather.home",
            options={"show_forecast": True, "forecast_days": 3, "show_humidity": True},
        )
    )
    layout.set_widget(0, weather)

    # Footer slots can show additional info if needed
    # For now, leave them empty to let the weather widget shine

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "03_weather", output_dir)


def generate_server_stats(renderer: Renderer, output_dir: Path) -> None:
    """Generate server stats dashboard using Grid2x3 layout."""
    hass = MockHass()
    create_server_stats_states(hass)

    # Use 2x3 grid for better spacing (6 widgets instead of 9)
    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Row 1: CPU, Memory, Disk
    cpu = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.server_cpu",
            label="CPU",
            color=COLOR_TEAL,
            options={"style": "bar", "icon": "chip"},
        )
    )
    layout.set_widget(0, cpu)

    mem = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.server_memory",
            label="MEM",
            color=COLOR_PURPLE,
            options={"style": "bar", "icon": "memory"},
        )
    )
    layout.set_widget(1, mem)

    disk = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.server_disk",
            label="DISK",
            color=COLOR_ORANGE,
            options={"style": "bar", "icon": "harddisk"},
        )
    )
    layout.set_widget(2, disk)

    # Row 2: Temp, Upload, Download
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.server_temp",
            label="Temp",
            color=COLOR_RED,
            options={"show_panel": True},
        )
    )
    layout.set_widget(3, temp)

    upload = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=4,
            entity_id="sensor.server_upload",
            label="Upload",
            color=COLOR_LIME,
            options={"icon": "arrow_up", "show_panel": True},
        )
    )
    layout.set_widget(4, upload)

    download = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=5,
            entity_id="sensor.server_download",
            label="Down",
            color=COLOR_RED,
            options={"icon": "arrow_down", "show_panel": True},
        )
    )
    layout.set_widget(5, download)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "04_server_stats", output_dir)


def generate_media_player(renderer: Renderer, output_dir: Path) -> None:
    """Generate media player dashboard using fullscreen layout with album art."""
    hass = MockHass()
    create_media_player_states(hass)

    layout = FullscreenLayout(padding=0)
    img, draw = renderer.create_canvas()

    # Media widget takes full screen with album art
    media = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True, "show_album_art": True},
        )
    )
    layout.set_widget(0, media)

    # Create fake album art for the sample
    album_art = create_fake_album_art(300)
    images = {0: album_art}

    layout.render(renderer, draw, build_widget_states(layout, hass, images=images))
    save_image(renderer, img, "05_media_player", output_dir)


def generate_media_player_paused(renderer: Renderer, output_dir: Path) -> None:
    """Generate paused media player dashboard showing centered pause icon."""
    hass = MockHass()
    create_media_player_paused_states(hass)

    layout = FullscreenLayout(padding=0)
    img, draw = renderer.create_canvas()

    # Media widget in paused state
    media = MediaWidget(
        WidgetConfig(
            widget_type="media",
            slot=0,
            entity_id="media_player.living_room",
            color=COLOR_CYAN,
            options={"show_artist": True, "show_progress": True, "show_album_art": True},
        )
    )
    layout.set_widget(0, media)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "05b_media_player_paused", output_dir)


def generate_energy_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate energy monitor dashboard using Grid2x2 layout."""
    hass = MockHass()
    create_energy_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Consumption (slot 0)
    consumption = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=0,
            entity_id="sensor.energy_consumption",
            label="Using",
            color=COLOR_ORANGE,
            options={"icon": "lightning-bolt", "show_panel": True},
        )
    )
    layout.set_widget(0, consumption)

    # Solar (slot 1)
    solar = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.solar_production",
            label="Solar",
            color=COLOR_GOLD,
            options={"icon": "weather-sunny", "show_panel": True},
        )
    )
    layout.set_widget(1, solar)

    # Grid export (slot 2)
    grid = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.grid_export",
            label="Export",
            color=COLOR_LIME,
            options={"icon": "power", "show_panel": True},
        )
    )
    layout.set_widget(2, grid)

    # Today total (slot 3)
    today = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.energy_today",
            label="Today",
            color=COLOR_CYAN,
            options={"icon": "lightning-bolt", "show_panel": True},
        )
    )
    layout.set_widget(3, today)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "06_energy_monitor", output_dir)


def generate_fitness(renderer: Renderer, output_dir: Path) -> None:
    """Generate fitness dashboard using HeroLayout with MultiProgressWidget."""
    hass = MockHass()
    create_fitness_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Multi-progress for activity rings replacement
    progress = MultiProgressWidget(
        WidgetConfig(
            widget_type="progress",
            slot=0,
            options={
                "title": "Activity",
                "items": [
                    {
                        "entity_id": "sensor.move_calories",
                        "label": "Move",
                        "target": 800,
                        "color": COLOR_RED,
                        "unit": "cal",
                        "icon": "fire",
                    },
                    {
                        "entity_id": "sensor.exercise_minutes",
                        "label": "Exercise",
                        "target": 40,
                        "color": COLOR_LIME,
                        "unit": "min",
                        "icon": "walk",
                    },
                    {
                        "entity_id": "sensor.stand_hours",
                        "label": "Stand",
                        "target": 12,
                        "color": COLOR_CYAN,
                        "unit": "hr",
                    },
                ],
            },
        )
    )
    layout.set_widget(0, progress)

    # Footer: Steps, Distance, Heart Rate (no units to save space)
    steps = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.steps",
            label="Steps",
            color=COLOR_WHITE,
            options={"show_name": True, "show_unit": False},
        )
    )
    layout.set_widget(1, steps)

    distance = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.distance",
            label="Dist",
            color=COLOR_WHITE,
            options={"show_name": True, "show_unit": False},
        )
    )
    layout.set_widget(2, distance)

    heart = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.heart_rate",
            label="BPM",
            color=COLOR_RED,
            options={"show_name": True, "show_unit": False, "icon": "heart"},
        )
    )
    layout.set_widget(3, heart)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "07_fitness", output_dir)


def generate_clock_dashboard(renderer: Renderer, output_dir: Path) -> None:
    """Generate clock dashboard using HeroLayout."""
    hass = MockHass()
    create_clock_states(hass)

    layout = HeroLayout(footer_slots=2, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Clock widget
    clock = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            color=COLOR_WHITE,
            options={"show_date": True, "show_seconds": False},
        )
    )
    layout.set_widget(0, clock)

    # Footer: Temperature and Calendar
    temp = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.outdoor_temp",
            label="Outside",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(1, temp)

    calendar = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="calendar.personal",
            label="Next",
            color=COLOR_GOLD,
        )
    )
    layout.set_widget(2, calendar)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "08_clock_dashboard", output_dir)


def generate_network_monitor(renderer: Renderer, output_dir: Path) -> None:
    """Generate network monitor dashboard using HeroLayout with StatusListWidget."""
    hass = MockHass()
    create_network_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Device status list
    devices = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Devices",
                "entities": [
                    ("device_tracker.phone", "Phone"),
                    ("device_tracker.laptop", "Laptop"),
                    ("device_tracker.tablet", "Tablet"),
                    ("device_tracker.tv", "Smart TV"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_GRAY,
            },
        )
    )
    layout.set_widget(0, devices)

    # Footer: Download, Upload, Total devices (no units to save space)
    download = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.router_download",
            label="Down",
            color=COLOR_LIME,
            options={"show_unit": False},
        )
    )
    layout.set_widget(1, download)

    upload = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.router_upload",
            label="Up",
            color=COLOR_ORANGE,
            options={"show_unit": False},
        )
    )
    layout.set_widget(2, upload)

    total = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.devices_online",
            label="Online",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(3, total)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "09_network_monitor", output_dir)


def generate_thermostat(renderer: Renderer, output_dir: Path) -> None:
    """Generate thermostat dashboard using HeroLayout with ClimateWidget."""
    hass = MockHass()
    create_thermostat_states(hass)

    layout = HeroLayout(footer_slots=3, hero_ratio=0.7, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Climate widget showing current temp, target, and hvac status
    thermostat = ClimateWidget(
        WidgetConfig(
            widget_type="climate",
            slot=0,
            entity_id="climate.main",
            label="Thermostat",
            color=COLOR_ORANGE,
            options={
                "show_target": True,
                "show_humidity": True,
                "show_mode": True,
            },
        )
    )
    layout.set_widget(0, thermostat)

    # Footer: Room temperatures
    living = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=1,
            entity_id="sensor.living_temp",
            label="Living",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(1, living)

    bedroom = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=2,
            entity_id="sensor.bedroom_temp",
            label="Bedroom",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(2, bedroom)

    bathroom = EntityWidget(
        WidgetConfig(
            widget_type="entity",
            slot=3,
            entity_id="sensor.bathroom_temp",
            label="Bath",
            color=COLOR_CYAN,
        )
    )
    layout.set_widget(3, bathroom)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "10_thermostat", output_dir)


def generate_batteries(renderer: Renderer, output_dir: Path) -> None:
    """Generate battery status dashboard using Grid2x2 layout."""
    hass = MockHass()
    create_battery_states(hass)

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Phone battery
    phone = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=0,
            entity_id="sensor.phone_battery",
            label="Phone",
            color=COLOR_LIME,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(0, phone)

    # Tablet battery
    tablet = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=1,
            entity_id="sensor.tablet_battery",
            label="Tablet",
            color=COLOR_GOLD,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(1, tablet)

    # Watch battery (low - red)
    watch = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=2,
            entity_id="sensor.watch_battery",
            label="Watch",
            color=COLOR_RED,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(2, watch)

    # AirPods battery
    airpods = GaugeWidget(
        WidgetConfig(
            widget_type="gauge",
            slot=3,
            entity_id="sensor.earbuds_battery",
            label="AirPods",
            color=COLOR_LIME,
            options={"style": "ring", "icon": "battery"},
        )
    )
    layout.set_widget(3, airpods)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "11_batteries", output_dir)


def generate_security(renderer: Renderer, output_dir: Path) -> None:
    """Generate security dashboard using SplitLayout."""
    hass = MockHass()
    create_security_states(hass)

    layout = SplitVertical(ratio=0.5, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Top: Door status list
    doors = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=0,
            options={
                "title": "Doors",
                "entities": [
                    ("lock.front_door", "Front Door"),
                    ("lock.back_door", "Back Door"),
                    ("lock.garage", "Garage"),
                ],
                "on_color": COLOR_LIME,
                "off_color": COLOR_RED,
                "on_text": "LOCKED",
                "off_text": "OPEN",
            },
        )
    )
    layout.set_widget(0, doors)

    # Bottom: Motion sensor status list
    motion = StatusListWidget(
        WidgetConfig(
            widget_type="status_list",
            slot=1,
            options={
                "title": "Motion",
                "entities": [
                    ("binary_sensor.living_motion", "Living Room"),
                    ("binary_sensor.kitchen_motion", "Kitchen"),
                    ("binary_sensor.backyard_motion", "Backyard"),
                ],
                "on_color": COLOR_RED,
                "off_color": COLOR_LIME,
                "on_text": "MOTION",
                "off_text": "Clear",
            },
        )
    )
    layout.set_widget(1, motion)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "12_security", output_dir)


def generate_binary_sensor_states(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample showing binary sensor device class icons and state translations.

    Shows all common device classes with their state-specific icons:
    - Icons read from HA icons.json files
    - States translated based on device_class (e.g., door on -> "Open")
    """
    hass = MockHass()

    # Create two grids side by side for more device classes
    # Left side: "On" states, Right side: Additional device classes
    # Using 2x Grid2x3 combined horizontally

    # Grid 1: Door/Window/Motion/Presence types (common home sensors)
    sensors_grid1 = [
        ("binary_sensor.door_on", "on", "Door", "door", COLOR_RED),
        ("binary_sensor.door_off", "off", "Door", "door", COLOR_LIME),
        ("binary_sensor.window_on", "on", "Window", "window", COLOR_ORANGE),
        ("binary_sensor.motion_on", "on", "Motion", "motion", COLOR_YELLOW),
        ("binary_sensor.motion_off", "off", "Motion", "motion", COLOR_CYAN),
        ("binary_sensor.presence", "on", "Home", "presence", COLOR_PURPLE),
    ]

    # Grid 2: Lock/Connectivity/Safety/Smoke
    sensors_grid2 = [
        ("binary_sensor.lock_on", "on", "Lock", "lock", COLOR_RED),
        ("binary_sensor.lock_off", "off", "Lock", "lock", COLOR_LIME),
        ("binary_sensor.wifi", "on", "WiFi", "connectivity", COLOR_CYAN),
        ("binary_sensor.smoke", "on", "Smoke", "smoke", COLOR_RED),
        ("binary_sensor.battery", "on", "Battery", "battery", COLOR_ORANGE),
        ("binary_sensor.plug", "on", "Plug", "plug", COLOR_LIME),
    ]

    # Set up all states
    for entity_id, state, name, device_class, _ in sensors_grid1 + sensors_grid2:
        hass.states.set(
            entity_id,
            state,
            {"friendly_name": name, "device_class": device_class},
        )

    # Create first grid (2x3)
    layout1 = Grid2x3(padding=8, gap=6)
    img1, draw1 = renderer.create_canvas()

    for slot, (entity_id, _, label, _, color) in enumerate(sensors_grid1):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout1.set_widget(slot, widget)

    layout1.render(renderer, draw1, build_widget_states(layout1, hass))
    save_image(renderer, img1, "16_binary_sensors", output_dir)

    # Create second grid (2x3) with additional device classes
    layout2 = Grid2x3(padding=8, gap=6)
    img2, draw2 = renderer.create_canvas()

    for slot, (entity_id, _, label, _, color) in enumerate(sensors_grid2):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout2.set_widget(slot, widget)

    layout2.render(renderer, draw2, build_widget_states(layout2, hass))
    save_image(renderer, img2, "17_binary_sensors_more", output_dir)


def generate_domain_icons(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample showing domain-specific state icons.

    Shows how different domains display icons based on state:
    - light: lightbulb on/off
    - switch: toggle on/off
    - fan: fan on/off
    - lock: lock/unlock
    """
    hass = MockHass()

    # Set up entities with various domains and states
    domain_entities = [
        # Row 1: Lights
        ("light.living_room", "on", "Light On", COLOR_GOLD),
        ("light.bedroom", "off", "Light Off", COLOR_GRAY),
        ("switch.outlet", "on", "Switch On", COLOR_LIME),
        # Row 2: Switch/Fan
        ("switch.plug", "off", "Switch Off", COLOR_GRAY),
        ("fan.ceiling", "on", "Fan On", COLOR_CYAN),
        ("fan.desk", "off", "Fan Off", COLOR_GRAY),
    ]

    for entity_id, state, name, _ in domain_entities:
        hass.states.set(
            entity_id,
            state,
            {"friendly_name": name},
        )

    layout = Grid2x3(padding=8, gap=6)
    img, draw = renderer.create_canvas()

    for slot, (entity_id, _, label, color) in enumerate(domain_entities):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id=entity_id,
                label=label,
                color=color,
                options={"show_name": True, "show_unit": False},
            )
        )
        layout.set_widget(slot, widget)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "18_domain_icons", output_dir)


def generate_welcome_screen(renderer: Renderer, output_dir: Path) -> None:
    """Generate welcome screen shown when device has no configuration.

    This mimics the dynamic welcome layout with clock, HA version, and entity count.
    """
    from custom_components.geekmagic.layouts.hero import HeroLayout
    from custom_components.geekmagic.widgets.clock import ClockWidget
    from custom_components.geekmagic.widgets.text import TextWidget

    hass = MockHass()

    layout = HeroLayout(footer_slots=3, hero_ratio=0.65, padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Hero: Clock — no explicit color → theme.text_primary at render time.
    clock = ClockWidget(
        WidgetConfig(
            widget_type="clock",
            slot=0,
            options={"show_date": True, "show_seconds": False},
        )
    )
    layout.set_widget(0, clock)

    # Footer: HA version, entity count, setup hint — uniform text_primary
    # values under text_secondary captions.
    for slot, label, text in (
        (1, "HA", "2024.12.1"),
        (2, "Entities", "247"),
        (3, "Setup", "Ready"),
    ):
        layout.set_widget(
            slot,
            TextWidget(
                WidgetConfig(
                    widget_type="text",
                    slot=slot,
                    label=label,
                    options={"text": text, "size": "small", "align": "center"},
                )
            ),
        )

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "00_welcome_screen", output_dir)


def generate_charts_dashboard(renderer: Renderer, output_dir: Path) -> None:
    """Generate charts dashboard showing numeric and binary sensor history."""
    from custom_components.geekmagic.widgets.chart import ChartWidget

    hass = MockHass()
    hass.states.set(
        "sensor.temperature", "23.5", {"unit_of_measurement": "°C", "friendly_name": "Temperature"}
    )
    hass.states.set(
        "sensor.humidity", "65", {"unit_of_measurement": "%", "friendly_name": "Humidity"}
    )
    hass.states.set(
        "binary_sensor.motion", "off", {"friendly_name": "Motion", "device_class": "motion"}
    )
    hass.states.set("binary_sensor.door", "off", {"friendly_name": "Door", "device_class": "door"})

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    # Chart history data for each slot
    chart_history: dict[int, list[float]] = {
        0: [21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 23.8, 23.5, 23.0, 22.5, 23.0, 23.5],  # temp
        1: [60, 62, 65, 68, 70, 68, 65, 63, 60, 58, 60, 65],  # humidity
        2: [0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0],  # motion (binary)
        3: [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # door (binary)
    }

    # Temperature chart (numeric)
    temp_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=0,
            entity_id="sensor.temperature",
            label="Temperature",
            color=COLOR_ORANGE,
            options={},
        )
    )
    layout.set_widget(0, temp_chart)

    # Humidity chart (numeric)
    humid_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=1,
            entity_id="sensor.humidity",
            label="Humidity",
            color=COLOR_CYAN,
            options={},
        )
    )
    layout.set_widget(1, humid_chart)

    # Motion sensor chart (binary)
    motion_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=2,
            entity_id="binary_sensor.motion",
            label="Motion",
            color=COLOR_RED,
            options={},
        )
    )
    layout.set_widget(2, motion_chart)

    # Door sensor chart (binary)
    door_chart = ChartWidget(
        WidgetConfig(
            widget_type="chart",
            slot=3,
            entity_id="binary_sensor.door",
            label="Door",
            color=COLOR_LIME,
            options={},
        )
    )
    layout.set_widget(3, door_chart)

    layout.render(renderer, draw, build_widget_states(layout, hass, chart_history))
    save_image(renderer, img, "15_charts_dashboard", output_dir)


def generate_gauge_sizes_2x2(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauges in 2x2 layout (large cells) to show responsive behavior."""
    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.mem", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "45", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set("sensor.net", "82", {"unit_of_measurement": "%", "friendly_name": "Network"})

    layout = Grid2x2(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    widgets = [
        ("sensor.cpu", "CPU", "cpu", COLOR_LIME),
        ("sensor.mem", "Memory", "memory", COLOR_PURPLE),
        ("sensor.disk", "Disk", "disk", COLOR_ORANGE),
        ("sensor.net", "Network", "network", COLOR_CYAN),
    ]

    for i, (entity, label, icon, color) in enumerate(widgets):
        gauge = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=i,
                entity_id=entity,
                label=label,
                color=color,
                options={"style": "bar", "icon": icon},
            )
        )
        layout.set_widget(i, gauge)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "13_gauges_large", output_dir)


def generate_gauge_sizes_2x3(renderer: Renderer, output_dir: Path) -> None:
    """Generate gauges in 2x3 layout (small cells) to show responsive behavior."""
    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.mem", "68", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set("sensor.disk", "45", {"unit_of_measurement": "%", "friendly_name": "Disk"})
    hass.states.set("sensor.net", "82", {"unit_of_measurement": "%", "friendly_name": "Network"})
    hass.states.set("sensor.gpu", "55", {"unit_of_measurement": "%", "friendly_name": "GPU"})
    hass.states.set("sensor.swap", "30", {"unit_of_measurement": "%", "friendly_name": "Swap"})

    layout = Grid2x3(padding=8, gap=8)
    img, draw = renderer.create_canvas()

    widgets = [
        ("sensor.cpu", "CPU", "cpu", COLOR_LIME),
        ("sensor.mem", "Memory", "memory", COLOR_PURPLE),
        ("sensor.disk", "Disk", "disk", COLOR_ORANGE),
        ("sensor.net", "Network", "network", COLOR_CYAN),
        ("sensor.gpu", "GPU", "temp", COLOR_RED),
        ("sensor.swap", "Swap", "memory", COLOR_TEAL),
    ]

    for i, (entity, label, icon, color) in enumerate(widgets):
        gauge = GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=i,
                entity_id=entity,
                label=label,
                color=color,
                options={"style": "bar", "icon": icon},
            )
        )
        layout.set_widget(i, gauge)

    layout.render(renderer, draw, build_widget_states(layout, hass))
    save_image(renderer, img, "14_gauges_small", output_dir)


def generate_layout_samples(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample images for all layouts showing their structure.

    Each layout is filled with a mix of widget types so the examples feel
    like real dashboards rather than the same widget repeated. A pool of
    varied slot recipes is rotated per layout so different layout images
    also feature different widget combinations.
    """
    from custom_components.geekmagic.widgets.clock import ClockWidget

    layouts_dir = output_dir / "layouts"
    layouts_dir.mkdir(exist_ok=True)

    hass = MockHass()
    hass.states.set("sensor.cpu", "73", {"unit_of_measurement": "%", "friendly_name": "CPU"})
    hass.states.set("sensor.memory", "62", {"unit_of_measurement": "%", "friendly_name": "Memory"})
    hass.states.set(
        "sensor.battery",
        "92",
        {"unit_of_measurement": "%", "friendly_name": "Battery", "icon": "mdi:battery"},
    )
    hass.states.set(
        "sensor.temp",
        "23.5",
        {
            "unit_of_measurement": "°C",
            "friendly_name": "Temperature",
            "icon": "mdi:thermometer",
        },
    )
    hass.states.set(
        "sensor.humidity",
        "48",
        {
            "unit_of_measurement": "%",
            "friendly_name": "Humidity",
            "icon": "mdi:water-percent",
        },
    )
    hass.states.set(
        "sensor.steps",
        "8542",
        {"unit_of_measurement": "steps", "friendly_name": "Steps"},
    )
    hass.states.set(
        "binary_sensor.door",
        "on",
        {"friendly_name": "Door", "device_class": "door"},
    )
    hass.states.set(
        "weather.home",
        "sunny",
        {
            "friendly_name": "Weather",
            "temperature": 24.3,
            "temperature_unit": "°C",
            "humidity": 45,
            "forecast": [
                {
                    "datetime": "2024-01-15",
                    "condition": "sunny",
                    "temperature": 26.0,
                    "templow": 17.0,
                },
                {
                    "datetime": "2024-01-16",
                    "condition": "cloudy",
                    "temperature": 23.7,
                    "templow": 15.0,
                },
                {
                    "datetime": "2024-01-17",
                    "condition": "rainy",
                    "temperature": 19.0,
                    "templow": 12.3,
                },
            ],
        },
    )

    chart_temp_history: list[float] = [20, 21, 22, 21, 23, 24, 23, 22, 21, 22, 23, 24]

    # Each recipe is a callable returning a widget for the given slot index,
    # paired with optional history data.
    def w_clock(slot: int):
        return ClockWidget(
            WidgetConfig(
                widget_type="clock",
                slot=slot,
                color=COLOR_WHITE,
                options={"show_date": True, "time_format": "24h"},
            )
        )

    def w_gauge_ring_cpu(slot: int):
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id="sensor.cpu",
                label="CPU",
                color=COLOR_CYAN,
                options={"style": "ring", "icon": "chip"},
            )
        )

    def w_entity_temp(slot: int):
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id="sensor.temp",
                label="Temp",
                color=COLOR_ORANGE,
                options={"icon": "thermometer"},
            )
        )

    def w_status_door(slot: int):
        return StatusWidget(
            WidgetConfig(
                widget_type="status",
                slot=slot,
                entity_id="binary_sensor.door",
                label="Door",
                color=COLOR_LIME,
                options={"icon": "door"},
            )
        )

    def w_progress_steps(slot: int):
        return ProgressWidget(
            WidgetConfig(
                widget_type="progress",
                slot=slot,
                entity_id="sensor.steps",
                label="Steps",
                color=COLOR_PURPLE,
                options={"target": 10000, "icon": "shoe-print"},
            )
        )

    def w_chart_temp(slot: int):
        return ChartWidget(
            WidgetConfig(
                widget_type="chart",
                slot=slot,
                entity_id="sensor.temp",
                label="Temp",
                color=COLOR_TEAL,
                options={},
            )
        )

    def w_weather(slot: int):
        return WeatherWidget(
            WidgetConfig(
                widget_type="weather",
                slot=slot,
                entity_id="weather.home",
                color=COLOR_YELLOW,
                options={"show_forecast": True, "forecast_days": 3},
            )
        )

    def w_gauge_bar_battery(slot: int):
        return GaugeWidget(
            WidgetConfig(
                widget_type="gauge",
                slot=slot,
                entity_id="sensor.battery",
                label="Batt",
                color=COLOR_GOLD,
                options={"style": "bar", "icon": "battery"},
            )
        )

    def w_entity_humidity(slot: int):
        return EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=slot,
                entity_id="sensor.humidity",
                label="Humid",
                color=COLOR_CYAN,
                options={"icon": "water-percent"},
            )
        )

    # (factory, needs_chart_history). 9 varied recipes — enough to fill 3x3.
    recipes = [
        (w_clock, False),
        (w_gauge_ring_cpu, False),
        (w_entity_temp, False),
        (w_status_door, False),
        (w_progress_steps, False),
        (w_chart_temp, True),
        (w_weather, False),
        (w_gauge_bar_battery, False),
        (w_entity_humidity, False),
    ]

    layouts_to_generate = [
        ("fullscreen", FullscreenLayout()),
        ("grid_2x2", Grid2x2()),
        ("grid_2x3", Grid2x3()),
        ("grid_3x2", Grid3x2()),
        ("grid_3x3", Grid3x3()),
        ("split_horizontal", SplitHorizontal()),
        ("split_vertical", SplitVertical()),
        ("split_h_1_2", SplitHorizontal1To2()),
        ("split_h_2_1", SplitHorizontal2To1()),
        ("three_column", ThreeColumnLayout()),
        ("three_row", ThreeRowLayout()),
        ("hero", HeroLayout()),
        ("hero_simple", HeroSimpleLayout()),
        ("sidebar_left", SidebarLeft()),
        ("sidebar_right", SidebarRight()),
        ("hero_corner_tl", HeroCornerTL()),
        ("hero_corner_tr", HeroCornerTR()),
        ("hero_corner_bl", HeroCornerBL()),
        ("hero_corner_br", HeroCornerBR()),
    ]

    for layout_idx, (layout_name, layout) in enumerate(layouts_to_generate):
        img, draw = renderer.create_canvas()
        slot_count = layout.get_slot_count()
        chart_history: dict[int, list[float]] = {}

        for i in range(slot_count):
            factory, needs_history = recipes[(i + layout_idx) % len(recipes)]
            widget = factory(i)
            layout.set_widget(i, widget)
            if needs_history:
                chart_history[i] = chart_temp_history

        layout.render(renderer, draw, build_widget_states(layout, hass, chart_history))
        save_image(renderer, img, f"layout_{layout_name}", layouts_dir)

    print(f"Generated layout samples in {layouts_dir}")


def generate_theme_samples(renderer: Renderer, output_dir: Path) -> None:
    """Generate sample images for each theme with varied widgets."""
    import random

    layouts_dir = output_dir / "layouts"
    layouts_dir.mkdir(exist_ok=True)

    hass = MockHass()
    hass.states.set(
        "sensor.cpu",
        "42",
        {"unit_of_measurement": "%", "friendly_name": "CPU", "icon": "mdi:cpu-64-bit"},
    )
    hass.states.set(
        "sensor.memory",
        "68",
        {"unit_of_measurement": "%", "friendly_name": "Memory", "icon": "mdi:memory"},
    )
    hass.states.set(
        "sensor.disk",
        "55",
        {"unit_of_measurement": "%", "friendly_name": "Disk", "icon": "mdi:harddisk"},
    )
    hass.states.set(
        "sensor.network",
        "85",
        {"unit_of_measurement": "Mb/s", "friendly_name": "Net", "icon": "mdi:lan"},
    )
    hass.states.set(
        "sensor.temp",
        "23",
        {"unit_of_measurement": "°C", "friendly_name": "Temp", "device_class": "temperature"},
    )
    hass.states.set(
        "sensor.humidity",
        "58",
        {"unit_of_measurement": "%", "friendly_name": "Humidity", "device_class": "humidity"},
    )
    hass.states.set(
        "sensor.battery",
        "87",
        {"unit_of_measurement": "%", "friendly_name": "Battery", "device_class": "battery"},
    )
    hass.states.set(
        "sensor.power",
        "2.4",
        {"unit_of_measurement": "kW", "friendly_name": "Power", "device_class": "power"},
    )
    hass.states.set(
        "sensor.solar",
        "3.2",
        {"unit_of_measurement": "kW", "friendly_name": "Solar", "icon": "mdi:solar-power"},
    )
    hass.states.set("device_tracker.phone", "home", {"friendly_name": "Phone"})

    # Define unique widget configurations for each theme
    theme_configs: dict[str, list] = {
        "classic": [
            ("gauge", "sensor.cpu", "CPU", {"style": "ring"}),
            ("gauge", "sensor.memory", "Memory", {"style": "ring"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("gauge", "sensor.disk", "Disk", {"style": "bar"}),
        ],
        "minimal": [
            ("entity", "sensor.temp", "Temp", {}),
            ("entity", "sensor.humidity", "Humidity", {}),
            ("status", "device_tracker.phone", "Phone", {}),
            ("entity", "sensor.power", "Power", {}),
        ],
        "neon": [
            ("gauge", "sensor.cpu", "CPU", {"style": "arc"}),
            ("gauge", "sensor.memory", "MEM", {"style": "arc"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("gauge", "sensor.battery", "BAT", {"style": "ring"}),
        ],
        "retro": [
            ("gauge", "sensor.cpu", "CPU", {"style": "bar"}),
            ("gauge", "sensor.memory", "MEM", {"style": "bar"}),
            ("gauge", "sensor.disk", "DSK", {"style": "bar"}),
            ("gauge", "sensor.network", "NET", {"style": "bar"}),
        ],
        "soft": [
            ("entity", "sensor.temp", "Inside", {}),
            ("progress", "sensor.battery", "Battery", {"target": 100}),
            ("chart", "sensor.temp", "Trend", {}),
            ("entity", "sensor.humidity", "Humidity", {}),
        ],
        "light": [
            ("gauge", "sensor.cpu", "CPU", {"style": "ring"}),
            ("gauge", "sensor.memory", "Memory", {"style": "ring"}),
            ("entity", "sensor.temp", "Temp", {}),
            ("progress", "sensor.disk", "Disk", {"target": 100}),
        ],
        "ocean": [
            ("gauge", "sensor.humidity", "Humidity", {"style": "arc"}),
            ("chart", "sensor.temp", "Temp", {}),
            ("entity", "sensor.temp", "Inside", {}),
            ("gauge", "sensor.battery", "Battery", {"style": "ring"}),
        ],
        "sunset": [
            ("gauge", "sensor.power", "Power", {"style": "arc", "max": 5}),
            ("gauge", "sensor.solar", "Solar", {"style": "arc", "max": 5}),
            ("chart", "sensor.temp", "Temp", {}),
            ("entity", "sensor.battery", "Battery", {}),
        ],
        "forest": [
            ("entity", "sensor.temp", "Outdoor", {}),
            ("gauge", "sensor.humidity", "Humidity", {"style": "bar"}),
            ("chart", "sensor.temp", "Climate", {}),
            ("progress", "sensor.solar", "Solar", {"target": 5}),
        ],
        "candy": [
            ("gauge", "sensor.battery", "Battery", {"style": "ring"}),
            ("entity", "sensor.temp", "Temp", {}),
            ("progress", "sensor.cpu", "CPU", {"target": 100}),
            ("chart", "sensor.temp", "Trend", {}),
        ],
    }

    for theme_name, theme in THEMES.items():
        layout = Grid2x2(padding=8, gap=8)
        layout.theme = theme

        accent_colors = theme.accent_colors
        configs = theme_configs.get(theme_name, theme_configs["classic"])

        chart_history: dict[int, list[float]] = {}

        for i, (widget_type, entity_id, label, options) in enumerate(configs):
            color = accent_colors[i % len(accent_colors)]
            widget: (
                ClockWidget
                | GaugeWidget
                | EntityWidget
                | ChartWidget
                | ProgressWidget
                | StatusWidget
            )

            if widget_type == "gauge":
                widget = GaugeWidget(
                    WidgetConfig(
                        widget_type="gauge",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
            elif widget_type == "entity":
                widget = EntityWidget(
                    WidgetConfig(
                        widget_type="entity",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options={"show_panel": True, **options},
                    )
                )
            elif widget_type == "chart":
                widget = ChartWidget(
                    WidgetConfig(
                        widget_type="chart",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
                rng = random.Random(42 + i)  # noqa: S311
                chart_history[i] = [20 + rng.uniform(-3, 5) for _ in range(48)]
            elif widget_type == "progress":
                widget = ProgressWidget(
                    WidgetConfig(
                        widget_type="progress",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options=options,
                    )
                )
            elif widget_type == "status":
                widget = StatusWidget(
                    WidgetConfig(
                        widget_type="status",
                        slot=i,
                        entity_id=entity_id,
                        label=label,
                        color=color,
                        options={"on_color": theme.success, "off_color": theme.error},
                    )
                )
            else:
                continue

            layout.set_widget(i, widget)

        img, draw = renderer.create_canvas(background=theme.background)
        layout.render(renderer, draw, build_widget_states(layout, hass, chart_history))
        save_image(renderer, img, f"layout_theme_{theme_name}", layouts_dir)

    print(f"Generated {len(THEMES)} theme samples in {layouts_dir}")


def main() -> None:
    """Generate all sample images."""
    output_dir = Path(__file__).parent.parent / "samples"
    output_dir.mkdir(exist_ok=True)

    renderer = Renderer()

    print("Generating sample dashboards using layout system...")
    print()

    generate_welcome_screen(renderer, output_dir)
    generate_system_monitor(renderer, output_dir)
    generate_smart_home(renderer, output_dir)
    generate_weather(renderer, output_dir)
    generate_server_stats(renderer, output_dir)
    generate_media_player(renderer, output_dir)
    generate_media_player_paused(renderer, output_dir)
    generate_energy_monitor(renderer, output_dir)
    generate_fitness(renderer, output_dir)
    generate_clock_dashboard(renderer, output_dir)
    generate_network_monitor(renderer, output_dir)
    generate_thermostat(renderer, output_dir)
    generate_batteries(renderer, output_dir)
    generate_security(renderer, output_dir)
    generate_binary_sensor_states(renderer, output_dir)
    generate_domain_icons(renderer, output_dir)
    generate_gauge_sizes_2x2(renderer, output_dir)
    generate_gauge_sizes_2x3(renderer, output_dir)
    generate_charts_dashboard(renderer, output_dir)
    generate_widget_sizes(renderer, output_dir)
    generate_layout_samples(renderer, output_dir)
    generate_theme_samples(renderer, output_dir)

    print()
    print(f"Done! Generated all samples in {output_dir}")


if __name__ == "__main__":
    main()
