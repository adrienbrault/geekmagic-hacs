#!/usr/bin/env python3
# ruff: noqa: S311, DTZ005
"""Debug script to render dashboards and upload to a GeekMagic device.

This simulates Home Assistant coordinator updates without needing HA installed.

Usage:
    uv run python scripts/debug_render.py <device_ip> [--cycle] [--interval 5]

Examples:
    # Render once and upload
    uv run python scripts/debug_render.py 192.168.1.100

    # Cycle through all dashboards every 5 seconds
    uv run python scripts/debug_render.py 192.168.1.100 --cycle --interval 5

    # Upload a specific dashboard
    uv run python scripts/debug_render.py 192.168.1.100 --dashboard system_monitor
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime
from pathlib import Path

# Add the custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.geekmagic.const import (
    COLOR_BLUE,
    COLOR_DARK_GRAY,
    COLOR_GRAY,
    COLOR_LIME,
    COLOR_ORANGE,
    COLOR_PANEL,
    COLOR_PINK,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
    COLOR_YELLOW,
    MODEL_PRO,
)
from custom_components.geekmagic.device import GeekMagicDevice
from custom_components.geekmagic.renderer import Renderer


def _print_pro_picture_note(device: GeekMagicDevice) -> None:
    """Tell Pro users how to make the uploaded image visible."""
    if device.model == MODEL_PRO:
        print("For Pro devices, manually select the Picture app if the image is not visible.")


def render_system_monitor(renderer: Renderer) -> bytes:
    """Render a system monitor dashboard with live-ish data."""
    img, draw = renderer.create_canvas()

    # Simulated live data
    cpu = random.randint(15, 85)
    mem = random.randint(40, 90)
    disk = random.randint(30, 70)
    net_data = [random.randint(20, 100) for _ in range(25)]

    # Title
    renderer.draw_text(
        draw, "SYSTEM", (120, 12), font=renderer.font_small, color=COLOR_GRAY, anchor="mm"
    )

    # CPU Ring
    renderer.draw_ring_gauge(draw, (60, 70), 35, cpu, COLOR_TEAL, COLOR_DARK_GRAY, width=5)
    renderer.draw_text(
        draw, f"{cpu}%", (60, 70), font=renderer.font_large, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "CPU", (60, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Memory Ring
    renderer.draw_ring_gauge(draw, (180, 70), 35, mem, COLOR_PURPLE, COLOR_DARK_GRAY, width=5)
    renderer.draw_text(
        draw, f"{mem}%", (180, 70), font=renderer.font_large, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "MEM", (180, 115), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Disk bar
    renderer.draw_icon(draw, "harddisk", (12, 135), size=14, color=COLOR_ORANGE)
    renderer.draw_text(
        draw, "DISK", (32, 142), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_bar(draw, (75, 137, 190, 147), disk, COLOR_ORANGE, COLOR_DARK_GRAY)
    renderer.draw_text(
        draw, f"{disk}%", (200, 142), font=renderer.font_tiny, color=COLOR_WHITE, anchor="lm"
    )

    # Network sparkline
    renderer.draw_panel(draw, (8, 160, 232, 205), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw, "NETWORK", (16, 168), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_sparkline(draw, (16, 175, 224, 198), net_data, COLOR_LIME, fill=True)

    # Timestamp
    now = datetime.now().strftime("%H:%M:%S")
    renderer.draw_text(
        draw, now, (120, 220), font=renderer.font_small, color=COLOR_GRAY, anchor="mm"
    )

    return renderer.to_jpeg(img)


def render_clock(renderer: Renderer) -> bytes:
    """Render a clock dashboard."""
    img, draw = renderer.create_canvas()

    now = datetime.now()

    # Large time
    renderer.draw_text(
        draw,
        now.strftime("%H:%M"),
        (120, 70),
        font=renderer.font_huge,
        color=COLOR_WHITE,
        anchor="mm",
    )
    renderer.draw_text(
        draw,
        f":{now.strftime('%S')}",
        (185, 65),
        font=renderer.font_medium,
        color=COLOR_GRAY,
        anchor="lm",
    )

    # Date
    renderer.draw_text(
        draw,
        now.strftime("%A, %B %d"),
        (120, 110),
        font=renderer.font_small,
        color=COLOR_GRAY,
        anchor="mm",
    )

    # Weather placeholder
    renderer.draw_panel(draw, (8, 135, 232, 195), COLOR_PANEL, radius=4)
    renderer.draw_icon(draw, "weather-sunny", (20, 150), size=24, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "21°C", (55, 155), font=renderer.font_large, color=COLOR_WHITE, anchor="lm"
    )
    renderer.draw_text(
        draw, "Sunny", (55, 175), font=renderer.font_small, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw, "H: 24° L: 16°", (160, 165), font=renderer.font_small, color=COLOR_GRAY, anchor="lm"
    )

    # Upcoming
    renderer.draw_text(
        draw,
        "Next: Meeting in 2h",
        (120, 215),
        font=renderer.font_small,
        color=COLOR_TEAL,
        anchor="mm",
    )

    return renderer.to_jpeg(img)


def render_fitness(renderer: Renderer) -> bytes:
    """Render a fitness dashboard."""
    img, draw = renderer.create_canvas()

    # Simulated data
    move = random.randint(60, 95)
    exercise = random.randint(40, 80)
    stand = random.randint(70, 100)
    steps = random.randint(5000, 12000)
    hr = random.randint(60, 90)

    center = (70, 80)

    # Activity rings
    renderer.draw_ring_gauge(
        draw, center, 50, move, COLOR_PINK, renderer.dim_color(COLOR_PINK), width=8
    )
    renderer.draw_ring_gauge(
        draw, center, 38, exercise, COLOR_LIME, renderer.dim_color(COLOR_LIME), width=8
    )
    renderer.draw_ring_gauge(
        draw, center, 26, stand, COLOR_TEAL, renderer.dim_color(COLOR_TEAL), width=8
    )

    # Center icon
    renderer.draw_text(
        draw, "\u2665", center, font=renderer.font_large, color=COLOR_PINK, anchor="mm"
    )

    # Ring labels
    labels = [
        ("MOVE", f"{move}%", COLOR_PINK),
        ("EXERCISE", f"{exercise}%", COLOR_LIME),
        ("STAND", f"{stand}%", COLOR_TEAL),
    ]
    for i, (label, value, color) in enumerate(labels):
        y = 30 + i * 36
        renderer.draw_text(draw, label, (140, y), font=renderer.font_tiny, color=color, anchor="lm")
        renderer.draw_text(
            draw, value, (140, y + 12), font=renderer.font_medium, color=COLOR_WHITE, anchor="lm"
        )

    # Stats
    renderer.draw_panel(draw, (8, 145, 232, 232), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw,
        f"STEPS: {steps:,}",
        (16, 165),
        font=renderer.font_small,
        color=COLOR_WHITE,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"HR: {hr} bpm",
        (16, 185),
        font=renderer.font_small,
        color=COLOR_PINK,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"CAL: {int(steps * 0.04)}",
        (130, 165),
        font=renderer.font_small,
        color=COLOR_ORANGE,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"DIST: {steps * 0.0007:.1f} km",
        (130, 185),
        font=renderer.font_small,
        color=COLOR_TEAL,
        anchor="lm",
    )

    # Timestamp
    now = datetime.now().strftime("%H:%M")
    renderer.draw_text(
        draw, now, (120, 218), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    return renderer.to_jpeg(img)


def render_server_stats(renderer: Renderer) -> bytes:
    """Render a server stats dashboard."""
    img, draw = renderer.create_canvas()

    # Simulated data
    cpu = random.randint(20, 90)
    mem = random.randint(40, 85)
    disk = random.randint(30, 60)
    swap = random.randint(5, 25)
    load = random.uniform(0.5, 4.0)
    temp = random.randint(45, 75)
    cpu_history = [random.randint(20, 90) for _ in range(25)]

    # Header
    renderer.draw_text(
        draw, "SERVER", (120, 12), font=renderer.font_small, color=COLOR_TEAL, anchor="mm"
    )

    # CPU ring
    renderer.draw_ring_gauge(draw, (60, 65), 32, cpu, COLOR_TEAL, COLOR_DARK_GRAY, width=6)
    renderer.draw_text(
        draw, f"{cpu}", (60, 65), font=renderer.font_large, color=COLOR_WHITE, anchor="mm"
    )
    renderer.draw_text(
        draw, "CPU %", (60, 105), font=renderer.font_tiny, color=COLOR_GRAY, anchor="mm"
    )

    # Side metrics
    metrics = [
        ("LOAD", f"{load:.1f}", COLOR_LIME),
        ("TEMP", f"{temp}°C", COLOR_ORANGE),
    ]
    for i, (label, value, color) in enumerate(metrics):
        y = 40 + i * 35
        renderer.draw_text(
            draw, label, (130, y), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_text(
            draw, value, (130, y + 12), font=renderer.font_medium, color=color, anchor="lm"
        )

    # CPU history sparkline
    renderer.draw_panel(draw, (125, 95, 230, 115), COLOR_PANEL, radius=2)
    renderer.draw_sparkline(draw, (128, 98, 227, 112), cpu_history, COLOR_TEAL, fill=True)

    # Resource bars
    y_section = 125
    renderer.draw_text(
        draw, "RESOURCES", (16, y_section), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )

    resources = [
        ("MEM", mem, COLOR_PURPLE),
        ("DISK", disk, COLOR_ORANGE),
        ("SWAP", swap, COLOR_BLUE),
    ]

    for i, (name, percent, color) in enumerate(resources):
        y = y_section + 18 + i * 24
        renderer.draw_text(
            draw, name, (16, y + 5), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
        )
        renderer.draw_bar(draw, (50, y, 180, y + 10), percent, color, COLOR_DARK_GRAY)
        renderer.draw_text(
            draw, f"{percent}%", (188, y + 5), font=renderer.font_tiny, color=color, anchor="lm"
        )

    # Network
    up = random.randint(10, 200)
    down = random.randint(50, 500)
    renderer.draw_text(
        draw,
        f"\u25b2 {up} MB/s",
        (16, 210),
        font=renderer.font_tiny,
        color=COLOR_LIME,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"\u25bc {down} MB/s",
        (100, 210),
        font=renderer.font_tiny,
        color=COLOR_RED,
        anchor="lm",
    )

    return renderer.to_jpeg(img)


def render_energy(renderer: Renderer) -> bytes:
    """Render an energy monitor dashboard."""
    img, draw = renderer.create_canvas()

    # Simulated data
    current_power = random.uniform(0.5, 4.0)
    solar = random.uniform(2.0, 5.0)
    grid = current_power - solar
    usage_data = [random.uniform(0.5, 4.0) for _ in range(30)]

    # Header
    renderer.draw_icon(draw, "lightning-bolt", (10, 8), size=16, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "ENERGY", (32, 16), font=renderer.font_small, color=COLOR_WHITE, anchor="lm"
    )

    # Main power panel
    renderer.draw_panel(draw, (8, 32, 232, 95), COLOR_PANEL, radius=4)

    # Current power
    renderer.draw_text(
        draw,
        f"{current_power:.1f}",
        (60, 55),
        font=renderer.font_huge,
        color=COLOR_LIME if grid < 0 else COLOR_ORANGE,
        anchor="mm",
    )
    renderer.draw_text(
        draw, "kW", (60, 82), font=renderer.font_small, color=COLOR_GRAY, anchor="mm"
    )

    # Solar
    renderer.draw_icon(draw, "weather-sunny", (130, 40), size=14, color=COLOR_YELLOW)
    renderer.draw_text(
        draw, "SOLAR", (150, 47), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_text(
        draw,
        f"{solar:.1f} kW",
        (150, 62),
        font=renderer.font_medium,
        color=COLOR_YELLOW,
        anchor="lm",
    )

    # Grid
    grid_color = COLOR_LIME if grid < 0 else COLOR_RED
    grid_label = "EXPORT" if grid < 0 else "IMPORT"
    renderer.draw_text(
        draw,
        grid_label,
        (150, 78),
        font=renderer.font_tiny,
        color=COLOR_GRAY,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"{abs(grid):.1f} kW",
        (150, 88),
        font=renderer.font_small,
        color=grid_color,
        anchor="lm",
    )

    # Usage graph
    renderer.draw_text(
        draw, "TODAY", (16, 108), font=renderer.font_tiny, color=COLOR_GRAY, anchor="lm"
    )
    renderer.draw_panel(draw, (8, 118, 232, 165), COLOR_PANEL, radius=4)
    renderer.draw_sparkline(draw, (16, 125, 224, 158), usage_data, COLOR_TEAL, fill=True)

    # Stats
    used = sum(usage_data) / len(usage_data) * 24
    solar_today = solar * 8
    renderer.draw_text(
        draw,
        f"USED: {used:.1f} kWh",
        (16, 180),
        font=renderer.font_small,
        color=COLOR_ORANGE,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"SOLAR: {solar_today:.1f} kWh",
        (120, 180),
        font=renderer.font_small,
        color=COLOR_YELLOW,
        anchor="lm",
    )

    # Cost
    cost = used * 0.15
    saved = solar_today * 0.20
    renderer.draw_panel(draw, (8, 200, 232, 232), COLOR_PANEL, radius=4)
    renderer.draw_text(
        draw,
        f"COST: ${cost:.2f}",
        (16, 216),
        font=renderer.font_small,
        color=COLOR_WHITE,
        anchor="lm",
    )
    renderer.draw_text(
        draw,
        f"SAVED: ${saved:.2f}",
        (130, 216),
        font=renderer.font_small,
        color=COLOR_LIME,
        anchor="lm",
    )

    return renderer.to_jpeg(img)


DASHBOARDS = {
    "system_monitor": ("System Monitor", render_system_monitor),
    "clock": ("Clock", render_clock),
    "fitness": ("Fitness", render_fitness),
    "server_stats": ("Server Stats", render_server_stats),
    "energy": ("Energy", render_energy),
}


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug render to GeekMagic device")
    parser.add_argument("device_ip", help="IP address of the GeekMagic device")
    parser.add_argument("--cycle", action="store_true", help="Cycle through all dashboards")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between updates")
    parser.add_argument(
        "--dashboard", choices=list(DASHBOARDS.keys()), help="Render a specific dashboard"
    )
    parser.add_argument("--list", action="store_true", help="List available dashboards")

    args = parser.parse_args()

    if args.list:
        print("Available dashboards:")
        for key, (name, _) in DASHBOARDS.items():
            print(f"  {key}: {name}")
        return

    renderer = Renderer()
    device = GeekMagicDevice(args.device_ip)

    print(f"Connecting to device at {args.device_ip}...")

    try:
        # Test connection
        if not await device.test_connection():
            print(f"Error: Could not connect to device at {args.device_ip}")
            return

        await device.detect_model()
        identity = device.model_name or device.model
        if device.firmware_version:
            identity = f"{identity} ({device.firmware_version})"
        print(f"Connected! Detected: {identity}")

        try:
            brightness = await device.get_brightness()
            print(f"Current brightness: {brightness}")
        except Exception as err:
            print(f"Brightness unavailable: {err}")

        try:
            state = await device.get_state()
            print(f"Current theme: {state.theme}, current image: {state.current_image}")
        except Exception as err:
            print(f"State unavailable: {err}")

        if args.dashboard:
            # Single dashboard
            name, render_func = DASHBOARDS[args.dashboard]
            print(f"Rendering {name}...")
            jpeg_data = render_func(renderer)
            print(f"Uploading ({len(jpeg_data)} bytes)...")
            await device.upload_and_display(jpeg_data, "debug.jpg")
            _print_pro_picture_note(device)
            print("Done!")

        elif args.cycle:
            # Cycle through all dashboards
            print(f"Cycling through dashboards every {args.interval}s (Ctrl+C to stop)")
            dashboard_keys = list(DASHBOARDS.keys())
            idx = 0

            while True:
                key = dashboard_keys[idx % len(dashboard_keys)]
                name, render_func = DASHBOARDS[key]

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Rendering {name}...")
                jpeg_data = render_func(renderer)
                await device.upload_and_display(jpeg_data, "debug.jpg")
                print(f"  Uploaded {len(jpeg_data)} bytes")
                _print_pro_picture_note(device)

                idx += 1
                await asyncio.sleep(args.interval)

        else:
            # Default: render system monitor once
            print("Rendering System Monitor...")
            jpeg_data = render_system_monitor(renderer)
            print(f"Uploading ({len(jpeg_data)} bytes)...")
            await device.upload_and_display(jpeg_data, "debug.jpg")
            _print_pro_picture_note(device)
            print("Done!")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        await device.close()


if __name__ == "__main__":
    asyncio.run(main())
