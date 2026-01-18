#!/usr/bin/env python3
"""Sync icon definitions from Home Assistant core repository.

This script downloads the icons.json files from various HA components
and stores them locally. The widget code reads from these files to
display correct icons for different entity states.

Usage:
    uv run python scripts/sync_ha_icons.py

The script downloads icons for:
- binary_sensor (door, motion, lock, etc.)
- light, switch, fan, lock, cover, vacuum, media_player, climate, etc.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

# Base URL for raw GitHub content from HA core
HA_CORE_RAW_URL = (
    "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components"
)

# Components to download icons for
COMPONENTS = [
    "binary_sensor",
    "light",
    "switch",
    "fan",
    "lock",
    "cover",
    "vacuum",
    "media_player",
    "climate",
    "humidifier",
    "water_heater",
    "siren",
    "automation",
    "script",
    "input_boolean",
    "sensor",
]

# Output directory for icons
OUTPUT_DIR = Path(__file__).parent.parent / "custom_components" / "geekmagic" / "data" / "ha_icons"


def download_icons(component: str) -> dict | None:
    """Download icons.json for a component from HA core."""
    url = f"{HA_CORE_RAW_URL}/{component}/icons.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  ⚠ No icons.json found for {component}")
            return None
        raise
    except Exception as e:
        print(f"  ✗ Error downloading {component}: {e}")
        return None


def main() -> None:
    """Download and save all component icons."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Syncing Home Assistant icon definitions...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    downloaded = 0
    for component in COMPONENTS:
        print(f"Downloading {component}...")
        icons = download_icons(component)
        if icons:
            output_path = OUTPUT_DIR / f"{component}.json"
            with output_path.open("w") as f:
                json.dump(icons, f, indent=2)
            print(f"  ✓ Saved to {output_path.name}")
            downloaded += 1

    print()
    print(f"Done! Downloaded {downloaded}/{len(COMPONENTS)} icon files.")
    print()
    print("Icon files saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
