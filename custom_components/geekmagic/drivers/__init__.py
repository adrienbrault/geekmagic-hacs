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

# Detection probes use a short timeout so an absent endpoint fails fast.
_DETECT_TIMEOUT = aiohttp.ClientTimeout(total=5)

# Errors that mean the host itself is unreachable. When a probe hits one of
# these, the remaining probes would fail identically, so we stop early instead
# of burning a full timeout per probe (relevant for offline-host setup retries).
_HOST_UNREACHABLE = (
    aiohttp.ClientConnectorError,
    aiohttp.ClientConnectorDNSError,
    TimeoutError,
)


class _HostUnreachableError(Exception):
    """Raised internally to abort detection when the host is unreachable."""


async def _probe_status_json(session: aiohttp.ClientSession, url: str) -> dict | None:
    """GET ``url``; return parsed JSON on HTTP 200, else None.

    Raises :class:`_HostUnreachableError` if the host is unreachable so the
    caller can stop probing early.
    """
    try:
        async with session.get(url, timeout=_DETECT_TIMEOUT) as response:
            if response.status == 200:
                return await response.json(content_type=None)
    except _HOST_UNREACHABLE as err:
        raise _HostUnreachableError(str(err)) from err
    except (aiohttp.ClientError, ValueError) as err:
        # A missing endpoint (404) or non-JSON body is expected during probing.
        _LOGGER.debug("Probe %s failed for detection: %s", url, err)
    return None


async def _probe_exists(session: aiohttp.ClientSession, url: str) -> bool:
    """Return True if ``url`` responds with HTTP 200 (body ignored).

    Used for legacy probes that only check endpoint presence. Raises
    :class:`_HostUnreachableError` if the host is unreachable.
    """
    try:
        async with session.get(url, timeout=_DETECT_TIMEOUT) as response:
            return response.status == 200
    except _HOST_UNREACHABLE as err:
        raise _HostUnreachableError(str(err)) from err
    except aiohttp.ClientError as err:
        _LOGGER.debug("Probe %s failed for detection: %s", url, err)
    return False


async def _identify_driver(
    session: aiohttp.ClientSession,
    host: str,
    base_url: str,
    session_provider: SessionProvider,
) -> FirmwareDriver | None:
    """Run the probe sequence; return a driver if identified, else None."""
    # 1. Stock identification via /v.json.
    data = await _probe_status_json(session, f"{base_url}/v.json")
    if data is not None:
        model_str = str(data.get("m", ""))
        version = data.get("v")
        upper = model_str.upper()
        if "PRO" in upper:
            _LOGGER.info("Detected SmallTV Pro (%s) at %s", model_str, host)
            return StockDriver(PRO, host, base_url, session_provider, version)
        if "ULTRA" in upper:
            _LOGGER.info("Detected SmallTV Ultra (%s) at %s", model_str, host)
            return StockDriver(ULTRA, host, base_url, session_provider, version)

    # 2. SD_PRO community firmware via /config.
    data = await _probe_status_json(session, f"{base_url}/config")
    if isinstance(data, dict) and "theme" in data and "brightness" in data:
        _LOGGER.info("Detected SD_PRO community firmware at %s", host)
        return SdProDriver(host, base_url, session_provider)

    # 3. Legacy fallback for old stock firmware without /v.json. These are
    #    presence checks only — the body is not used.
    if await _probe_exists(session, f"{base_url}/.sys/app.json"):
        _LOGGER.info("Detected SmallTV Pro (legacy /.sys/app.json) at %s", host)
        return StockDriver(PRO, host, base_url, session_provider)
    if await _probe_exists(session, f"{base_url}/app.json"):
        _LOGGER.info("Detected SmallTV Ultra (legacy /app.json) at %s", host)
        return StockDriver(ULTRA, host, base_url, session_provider)

    return None


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

    If the host is unreachable, probing stops after the first probe and the
    default driver is returned; the subsequent ``test_connection()`` then
    reports the failure as retryable rather than every probe timing out.
    """
    session = await session_provider()

    # Detection is best-effort: it must never crash setup. The subsequent
    # test_connection() is the authority on whether the host is reachable.
    try:
        driver = await _identify_driver(session, host, base_url, session_provider)
    except _HostUnreachableError as err:
        _LOGGER.debug(
            "Host %s unreachable during detection (%s); deferring to connection test",
            host,
            err,
        )
        return StockDriver(ULTRA, host, base_url, session_provider)
    except Exception as err:
        # Detection must not break setup; default and let test_connection decide.
        _LOGGER.debug("Firmware detection error for %s (%s); defaulting", host, err)
        return StockDriver(ULTRA, host, base_url, session_provider)

    if driver is not None:
        return driver

    # Default: assume stock Ultra (matches the historic UNKNOWN->theme-3 path).
    _LOGGER.warning("Could not detect firmware for %s; defaulting to SmallTV Ultra", host)
    return StockDriver(ULTRA, host, base_url, session_provider)
