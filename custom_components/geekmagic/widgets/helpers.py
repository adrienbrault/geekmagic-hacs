"""Shared utilities for widgets."""

from __future__ import annotations

import contextlib
import json
import logging
from functools import lru_cache
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

# Path to HA icon JSON files
_HA_ICONS_DIR = Path(__file__).parent.parent / "data" / "ha_icons"

# States considered "on" for binary sensors and similar entities
# Includes common affirmative states across different entity types
ON_STATES = frozenset({"on", "true", "home", "locked", "open", "unlocked", "1"})

# Binary sensor device class state translations
# Maps device_class to (on_state, off_state) display strings
# Aligned with Home Assistant core: homeassistant/components/binary_sensor/strings.json
BINARY_SENSOR_TRANSLATIONS: dict[str, tuple[str, str]] = {
    # Door/window/opening sensors
    "door": ("Open", "Closed"),
    "garage_door": ("Open", "Closed"),
    "window": ("Open", "Closed"),
    "opening": ("Open", "Closed"),
    # Motion/presence sensors
    "motion": ("Detected", "Clear"),
    "presence": ("Home", "Not home"),
    "occupancy": ("Detected", "Clear"),
    # Connectivity
    "connectivity": ("Connected", "Disconnected"),
    # Power/plug
    "plug": ("Plugged in", "Unplugged"),
    "power": ("On", "Off"),
    # Lock (inverted - on = unlocked = bad for security)
    "lock": ("Unlocked", "Locked"),
    # Safety/problem
    "safety": ("Unsafe", "Safe"),
    "problem": ("Problem", "OK"),
    "tamper": ("Tampering detected", "Clear"),
    # Battery
    "battery": ("Low", "Normal"),
    "battery_charging": ("Charging", "Not charging"),
    # Environmental detection
    "carbon_monoxide": ("Detected", "Clear"),
    "smoke": ("Detected", "Clear"),
    "gas": ("Detected", "Clear"),
    "moisture": ("Wet", "Dry"),
    "cold": ("Cold", "Normal"),
    "heat": ("Hot", "Normal"),
    "light": ("Detected", "Clear"),
    # Activity detection
    "running": ("Running", "Not running"),
    "moving": ("Moving", "Not moving"),
    "vibration": ("Detected", "Clear"),
    "sound": ("Detected", "Clear"),
    # Updates
    "update": ("Update available", "Up-to-date"),
}


@lru_cache(maxsize=32)
def _load_ha_icons(component: str) -> dict | None:
    """Load icon definitions from HA JSON file.

    Uses LRU cache to avoid repeated disk reads.

    Args:
        component: Component name (e.g., "binary_sensor", "light")

    Returns:
        Parsed JSON dict or None if file doesn't exist
    """
    icon_file = _HA_ICONS_DIR / f"{component}.json"
    if not icon_file.exists():
        return None
    try:
        with icon_file.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _LOGGER.warning("Failed to load icons for %s: %s", component, e)
        return None


def _get_binary_sensor_icon_from_json(
    state: str,
    device_class: str,
) -> str | None:
    """Get binary sensor icon from HA JSON data.

    Args:
        state: Entity state ("on" or "off")
        device_class: Binary sensor device class

    Returns:
        MDI icon string or None
    """
    icons_data = _load_ha_icons("binary_sensor")
    if not icons_data:
        return None

    entity_component = icons_data.get("entity_component", {})
    device_class_data = entity_component.get(device_class)
    if not device_class_data:
        return None

    # For binary sensors: default = off, state.on = on
    if state.lower() == "on":
        return device_class_data.get("state", {}).get("on")
    return device_class_data.get("default")


def _get_domain_icon_from_json(
    domain: str,
    state: str,
    device_class: str | None = None,
) -> str | None:
    """Get domain-specific icon from HA JSON data.

    Supports state-specific icons for domains like light, switch, fan, lock.

    Args:
        domain: Entity domain (e.g., "light", "switch")
        state: Entity state
        device_class: Optional device class for device_class-specific icons

    Returns:
        MDI icon string or None
    """
    icons_data = _load_ha_icons(domain)
    if not icons_data:
        return None

    entity_component = icons_data.get("entity_component", {})

    # Check device_class specific icons first (for domains like switch with outlet class)
    if device_class:
        dc_data = entity_component.get(device_class)
        if dc_data:
            # Check for state-specific icon
            state_icon = dc_data.get("state", {}).get(state.lower())
            if state_icon:
                return state_icon
            # Fall back to default for this device class
            return dc_data.get("default")

    # Check default entity component ("_")
    default_data = entity_component.get("_")
    if not default_data:
        return None

    # Check for state-specific icon (e.g., "off" -> "mdi:lightbulb-off")
    state_icon = default_data.get("state", {}).get(state.lower())
    if state_icon:
        return state_icon

    # Return default icon (typically the "on" state icon)
    return default_data.get("default")


def _get_sensor_device_class_icon(device_class: str) -> str | None:
    """Get sensor device class icon from HA JSON data.

    Args:
        device_class: Sensor device class (e.g., "temperature", "humidity")

    Returns:
        MDI icon string or None
    """
    icons_data = _load_ha_icons("sensor")
    if not icons_data:
        return None

    entity_component = icons_data.get("entity_component", {})
    dc_data = entity_component.get(device_class)
    if dc_data:
        return dc_data.get("default")
    return None


def get_domain_state_icon(
    domain: str,
    state: str,
    device_class: str | None = None,
) -> str | None:
    """Get the appropriate icon for a domain-based entity based on its state.

    Reads from HA icon JSON files for accurate, up-to-date icons.

    Args:
        domain: Entity domain (light, switch, etc.)
        state: Entity state ("on", "off", etc.)
        device_class: Optional device class for device_class-specific icons

    Returns:
        MDI icon string, or None if no specific icon defined
    """
    return _get_domain_icon_from_json(domain, state, device_class)


def get_binary_sensor_icon(
    state: str,
    device_class: str | None,
) -> str | None:
    """Get the appropriate icon for a binary sensor based on its state.

    Reads from HA icon JSON files for accurate, up-to-date icons.

    Args:
        state: Raw entity state ("on", "off", etc.)
        device_class: Binary sensor device class (door, motion, etc.)

    Returns:
        MDI icon string, or None if no specific icon defined
    """
    if device_class is None:
        return None

    return _get_binary_sensor_icon_from_json(state, device_class)


def translate_binary_state(
    state: str,
    device_class: str | None,
) -> str:
    """Translate binary sensor state based on device class.

    For binary sensors, converts generic "on"/"off" states to
    human-readable values based on the device_class attribute.

    Examples:
        - door + "on" -> "Open"
        - door + "off" -> "Closed"
        - motion + "on" -> "Detected"
        - motion + "off" -> "Clear"

    Args:
        state: Raw entity state ("on", "off", etc.)
        device_class: Binary sensor device class (door, motion, etc.)

    Returns:
        Translated state string, or original state if no translation available
    """
    if device_class is None:
        return state

    translations = BINARY_SENSOR_TRANSLATIONS.get(device_class)
    if translations is None:
        return state

    on_state, off_state = translations
    state_lower = state.lower()

    if state_lower == "on":
        return on_state
    if state_lower == "off":
        return off_state

    return state


def truncate_text(
    text: str,
    max_chars: int,
    style: str = "end",
    ellipsis: str = "…",
) -> str:
    """Truncate text if it exceeds max_chars.

    Args:
        text: Text to truncate
        max_chars: Maximum number of characters
        style: Truncation style:
            - "end": "very long text" -> "very lon…"
            - "middle": "very long text" -> "very…ext"
            - "start": "very long text" -> "…ng text"
        ellipsis: String to use for truncation (default: "…")

    Returns:
        Original text if short enough, otherwise truncated
    """
    if len(text) <= max_chars:
        return text

    available = max_chars - len(ellipsis)
    if available <= 0:
        return ellipsis[:max_chars]

    if style == "middle":
        # Show beginning and end: "very..ext"
        start_len = (available + 1) // 2  # Slightly favor start
        end_len = available - start_len
        if end_len > 0:
            return text[:start_len] + ellipsis + text[-end_len:]
        return text[:start_len] + ellipsis
    if style == "start":
        # Show end: "..ng text"
        return ellipsis + text[-available:]
    # Default: show start: "very lo.."
    return text[:available] + ellipsis


def format_number(
    value: float | str,
    precision: int = 1,
    threshold: float = 1000,
) -> str:
    """Format large numbers with K/M/B suffixes.

    Examples:
        - 500 -> "500"
        - 1000 -> "1k"
        - 1500 -> "1.5k"
        - 12000 -> "12k"
        - 1000000 -> "1M"
        - 1500000 -> "1.5M"
        - 1000000000 -> "1B"

    Args:
        value: Number to format (can be float, int, or string)
        precision: Decimal places for formatted numbers (default: 1)
        threshold: Minimum value to start abbreviating (default: 1000)

    Returns:
        Formatted string
    """
    # Convert to float if string
    if isinstance(value, str):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return str(value)  # Return original string if not a number

    # Handle negative numbers
    if value < 0:
        return "-" + format_number(-value, precision, threshold)

    # Don't abbreviate small numbers
    if abs(value) < threshold:
        # Return integer if whole number, otherwise with decimals
        if value == int(value):
            return str(int(value))
        return f"{value:.{precision}f}".rstrip("0").rstrip(".")

    # Define suffixes and their magnitudes
    suffixes = [
        (1_000_000_000_000, "T"),  # Trillion
        (1_000_000_000, "B"),  # Billion
        (1_000_000, "M"),  # Million
        (1_000, "k"),  # Thousand
    ]

    for magnitude, suffix in suffixes:
        if abs(value) >= magnitude:
            formatted = value / magnitude
            # Remove trailing zeros
            result = f"{formatted:.{precision}f}".rstrip("0").rstrip(".")
            return f"{result}{suffix}"

    # Shouldn't reach here, but just in case
    return str(value)


def calculate_percent(
    value: float,
    min_val: float,
    max_val: float,
) -> float:
    """Calculate percentage in range [0, 100].

    Args:
        value: Current value
        min_val: Minimum value (0%)
        max_val: Maximum value (100%)

    Returns:
        Percentage clamped to [0, 100]
    """
    value_range = max_val - min_val
    if value_range <= 0:
        return 0.0
    return max(0.0, min(100.0, ((value - min_val) / value_range) * 100))


def _get_device_class_icon(domain: str | None, device_class: str) -> str | None:
    """Get icon for a device class from HA JSON data.

    Looks up sensor device class icons from the downloaded HA icons.json files.
    Falls back to binary_sensor icons if domain is binary_sensor.

    Args:
        domain: Entity domain (e.g., "sensor", "binary_sensor")
        device_class: Device class name

    Returns:
        MDI icon string or None
    """
    # For sensors, get icon from sensor.json
    if domain == "sensor":
        return _get_sensor_device_class_icon(device_class)

    # For binary sensors, get the default (off) icon
    if domain == "binary_sensor":
        return _get_binary_sensor_icon_from_json("off", device_class)

    # Try to get from the domain's JSON
    if domain:
        icons_data = _load_ha_icons(domain)
        if icons_data:
            entity_component = icons_data.get("entity_component", {})
            dc_data = entity_component.get(device_class)
            if dc_data:
                return dc_data.get("default")

    return None


def _get_domain_icon(domain: str) -> str | None:
    """Get default icon for a domain.

    First tries to load from HA JSON file, then falls back to hardcoded defaults
    for domains that don't have icons.json files.

    Args:
        domain: Entity domain

    Returns:
        MDI icon string or None
    """
    # Try to get from JSON first
    icons_data = _load_ha_icons(domain)
    if icons_data:
        entity_component = icons_data.get("entity_component", {})
        default_data = entity_component.get("_")
        if default_data and "default" in default_data:
            return default_data["default"]

    # Fallback for domains without icons.json or without entity_component._
    fallback_icons = {
        "sensor": "mdi:eye",
        "binary_sensor": "mdi:checkbox-blank-circle",
        "climate": "mdi:thermostat",
        "camera": "mdi:camera",
        "weather": "mdi:weather-partly-cloudy",
        "person": "mdi:account",
        "device_tracker": "mdi:crosshairs-gps",
        "scene": "mdi:palette",
        "input_number": "mdi:ray-vertex",
        "input_select": "mdi:format-list-bulleted",
        "input_text": "mdi:form-textbox",
        "input_datetime": "mdi:calendar-clock",
        "input_button": "mdi:gesture-tap-button",
        "counter": "mdi:counter",
        "timer": "mdi:timer",
        "calendar": "mdi:calendar",
        "alarm_control_panel": "mdi:shield-home",
        "number": "mdi:ray-vertex",
        "select": "mdi:format-list-bulleted",
        "button": "mdi:gesture-tap-button",
        "text": "mdi:form-textbox",
        "update": "mdi:package-up",
        "remote": "mdi:remote",
        "lawn_mower": "mdi:robot-mower",
        "valve": "mdi:valve",
    }
    return fallback_icons.get(domain)


def parse_color(
    value: object,
    default: tuple[int, int, int],
) -> tuple[int, int, int]:
    """Parse color value from config, converting lists to tuples.

    Handles colors from JSON (which come as lists) and ensures they are
    valid RGB tuples that PIL can use.

    Args:
        value: Color value (tuple, list, or None). Can be any type -
               invalid types will return the default.
        default: Default color to use if value is invalid

    Returns:
        Valid RGB color tuple
    """
    if value is None:
        return default
    if isinstance(value, tuple) and len(value) == 3:
        return value  # type: ignore[return-value]
    if isinstance(value, list) and len(value) == 3:
        try:
            # Type checker doesn't know list contains int-convertible values
            return (int(value[0]), int(value[1]), int(value[2]))  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return default
    return default


def estimate_max_chars(
    available_width: int,
    char_width: int = 8,
    padding: int = 10,
) -> int:
    """Estimate maximum characters that fit in available width.

    Args:
        available_width: Available width in pixels
        char_width: Estimated average character width
        padding: Horizontal padding to account for

    Returns:
        Maximum number of characters
    """
    usable_width = available_width - 2 * padding
    return max(1, usable_width // char_width)


def format_value_with_unit(
    value: str | float,
    unit: str,
    separator: str = "",
    abbreviate: bool = False,
    threshold: float = 1000,
) -> str:
    """Format value with optional unit.

    Args:
        value: Value string or number
        unit: Unit string (can be empty)
        separator: Separator between value and unit
        abbreviate: Whether to abbreviate large numbers (1k, 1M, etc.)
        threshold: Minimum value to start abbreviating (default: 1000)

    Returns:
        Formatted string like "23.5°C" or "1.5k views"
    """
    # Abbreviate if requested
    if abbreviate and isinstance(value, (int, float)):
        value = format_number(value, threshold=threshold)
    elif abbreviate and isinstance(value, str):
        with contextlib.suppress(ValueError, TypeError):
            value = format_number(float(value), threshold=threshold)

    if unit:
        return f"{value}{separator}{unit}"
    return str(value)
