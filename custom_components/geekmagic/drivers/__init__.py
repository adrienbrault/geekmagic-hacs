"""Firmware drivers for GeekMagic displays.

``detect_driver`` fingerprints a device and returns the matching
:class:`FirmwareDriver`. ``GeekMagicDevice`` delegates to it.
"""

from __future__ import annotations

import logging

import aiohttp

from .base import (
    ConnectionResult,
    DeviceState,
    DriverCapabilities,
    FirmwareDriver,
    SessionProvider,
    SpaceInfo,
)
from .sdpro import SdProDriver
from .stock import PRO, ULTRA, StockDriver

_LOGGER = logging.getLogger(__name__)

# Detection probes use a short timeout so an absent endpoint fails fast.
_DETECT_TIMEOUT = aiohttp.ClientTimeout(total=5)

__all__ = [
    "ConnectionResult",
    "DeviceState",
    "DriverCapabilities",
    "FirmwareDriver",
    "SdProDriver",
    "SpaceInfo",
    "StockDriver",
    "detect_driver",
]


async def detect_driver(
    host: str, base_url: str, session_provider: SessionProvider
) -> FirmwareDriver:
    """Detect the firmware at ``base_url`` and return its driver.

    Detection order matters:
      1. ``/v.json`` — stock firmware identification (distinguishes Pro/Ultra).
      2. ``/config`` — SD_PRO community firmware (has no ``/v.json``).
      3. Legacy probe of ``/.sys/app.json`` / ``/app.json`` for old stock
         firmware that predates ``/v.json``.
      4. Default to the Ultra stock driver with a warning.
    """
    session = await session_provider()

    # 1. Stock identification via /v.json.
    try:
        async with session.get(f"{base_url}/v.json", timeout=_DETECT_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json(content_type=None)
                model_str = str(data.get("m", ""))
                version = data.get("v")
                upper = model_str.upper()
                if "PRO" in upper:
                    _LOGGER.info("Detected SmallTV Pro (%s) at %s", model_str, host)
                    return StockDriver(PRO, host, base_url, session_provider, version)
                if "ULTRA" in upper:
                    _LOGGER.info("Detected SmallTV Ultra (%s) at %s", model_str, host)
                    return StockDriver(ULTRA, host, base_url, session_provider, version)
    except Exception as err:
        _LOGGER.debug("/v.json detection failed for %s: %s", host, err)

    # 2. SD_PRO community firmware via /config.
    try:
        async with session.get(f"{base_url}/config", timeout=_DETECT_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json(content_type=None)
                if isinstance(data, dict) and "theme" in data and "brightness" in data:
                    _LOGGER.info("Detected SD_PRO community firmware at %s", host)
                    return SdProDriver(host, base_url, session_provider)
    except Exception as err:
        _LOGGER.debug("/config detection failed for %s: %s", host, err)

    # 3. Legacy fallback for old stock firmware without /v.json.
    try:
        async with session.get(f"{base_url}/.sys/app.json", timeout=_DETECT_TIMEOUT) as response:
            if response.status == 200:
                _LOGGER.info("Detected SmallTV Pro (legacy /.sys/app.json) at %s", host)
                return StockDriver(PRO, host, base_url, session_provider)
    except Exception as err:
        _LOGGER.debug("Legacy Pro probe failed for %s: %s", host, err)

    try:
        async with session.get(f"{base_url}/app.json", timeout=_DETECT_TIMEOUT) as response:
            if response.status == 200:
                _LOGGER.info("Detected SmallTV Ultra (legacy /app.json) at %s", host)
                return StockDriver(ULTRA, host, base_url, session_provider)
    except Exception as err:
        _LOGGER.debug("Legacy Ultra probe failed for %s: %s", host, err)

    # 4. Default: assume stock Ultra (matches the historic UNKNOWN->theme-3 path).
    _LOGGER.warning("Could not detect firmware for %s; defaulting to SmallTV Ultra", host)
    return StockDriver(ULTRA, host, base_url, session_provider)
