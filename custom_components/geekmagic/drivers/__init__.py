"""Driver factory + detection for GeekMagic firmwares."""

from __future__ import annotations

import logging

import aiohttp

from .base import (
    DETECT_TIMEOUT,
    ConnectionResult,
    DeviceDriver,
    DeviceState,
    SpaceInfo,
)
from .sdpro import SDProDriver
from .stock import STOCK_PRO_PROFILE, STOCK_ULTRA_PROFILE, StockDriver

__all__ = [
    "ConnectionResult",
    "DeviceDriver",
    "DeviceState",
    "SDProDriver",
    "SpaceInfo",
    "StockDriver",
    "detect_driver",
]

_LOGGER = logging.getLogger(__name__)


async def detect_driver(base_url: str, session: aiohttp.ClientSession) -> DeviceDriver | None:
    """Probe the device and return the right driver, or `None` if unreachable.

    Probe order, picked so the cheapest most-specific signal wins:

      1. `GET /v.json` — stock firmwares (Pro and recent Ultra) identify
         themselves with `{"m": "<model>", "v": "<version>"}`.
      2. `GET /config` — SD_PRO community firmware exposes all settings
         here; presence of `brightness` + `freespace` is the fingerprint.
      3. `GET /app.json` — legacy stock Ultra firmwares pre-`/v.json`.
    """
    # 1. /v.json — stock firmwares
    try:
        async with session.get(f"{base_url}/v.json", timeout=DETECT_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json(content_type=None)
                model_str = str(data.get("m", ""))
                version = data.get("v")
                if "PRO" in model_str.upper():
                    _LOGGER.info("Detected stock SmallTV Pro firmware (%s)", version)
                    return StockDriver(base_url, session, STOCK_PRO_PROFILE, sw_version=version)
                if "ULTRA" in model_str.upper():
                    _LOGGER.info("Detected stock SmallTV Ultra firmware (%s)", version)
                    return StockDriver(base_url, session, STOCK_ULTRA_PROFILE, sw_version=version)
                _LOGGER.warning(
                    "Unknown /v.json model %r; defaulting to Ultra driver",
                    model_str,
                )
                return StockDriver(base_url, session, STOCK_ULTRA_PROFILE, sw_version=version)
    except Exception as err:
        _LOGGER.debug("/v.json probe failed: %s", err)

    # 2. /config — SD_PRO community firmware
    try:
        async with session.get(f"{base_url}/config", timeout=DETECT_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json(content_type=None)
                if "brightness" in data and "freespace" in data:
                    _LOGGER.info("Detected SD_PRO community firmware")
                    return SDProDriver(base_url, session)
    except Exception as err:
        _LOGGER.debug("/config probe failed: %s", err)

    # 3. /app.json — legacy stock Ultra
    try:
        async with session.get(f"{base_url}/app.json", timeout=DETECT_TIMEOUT) as response:
            if response.status == 200:
                _LOGGER.info("Detected legacy stock SmallTV Ultra firmware via /app.json")
                return StockDriver(base_url, session, STOCK_ULTRA_PROFILE, sw_version=None)
    except Exception as err:
        _LOGGER.debug("/app.json probe failed: %s", err)

    _LOGGER.warning("Could not detect firmware at %s", base_url)
    return None
