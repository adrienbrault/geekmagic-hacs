"""Keep a crashing rendering engine out of Home Assistant.

blitz-py is native code. When it crashes (issue #262: SIGILL on a
Synology VMM guest, on every boot) there is no exception to catch — the
whole Home Assistant process dies, and the Supervisor restarts it into
the same crash until the integration is deleted by hand.

So before the engine may load into Core, a throwaway child Python runs
``engine_selftest`` — the integration's real render pipeline on one
busy frame — and only its verdict opens the gate in ``engine``:

- passed: the engine loads on first use, as before. The verdict is
  cached in a ``Store`` under a key of everything it depends on, so
  later boots skip the child until one of those changes.
- crashed (killed by a signal, non-zero exit, timed out, could not
  start): the engine is never imported in this process, displays show
  the engine-unavailable screen, one error is logged with the signal
  and the child's last output, and a repair issue explains it. A
  failure is not cached — the next boot tries again, and a pass clears
  the issue.
- no engine installed (or below the floor): nothing native could
  crash; the existing install-hint screen applies.

One self-test per Home Assistant process, shared by every config entry
and the panel preview (``DATA_ENGINE_PROBE``). Every render path awaits
:func:`async_engine_ready` first; the gate itself is the backstop.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import platform
import signal
import sys
from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration
from homeassistant.util.hass_dict import HassKey

from . import engine
from .const import DOMAIN
from .engine_selftest import EXIT_NO_ENGINE, EXIT_OK

_LOGGER = logging.getLogger(__name__)

# Starting a Python, importing Pillow, the widgets and the native
# engine, registering seven fonts and rendering a supersampled 2x2 neon
# frame with glow takes 0.1-0.3 s on a desktop or in an aarch64 HA
# container. A Raspberry Pi 3 on an SD card with a cold page cache, while
# the rest of Home Assistant is booting around it, can be one to two
# orders of magnitude slower. 60 s keeps a wide margin over that and
# still bounds a hung engine; it is only paid on boots whose cache key
# changed.
PROBE_TIMEOUT = 60.0
# Enough of the child's stderr for the stage it died in and a
# faulthandler traceback.
_STDERR_TAIL_CHARS = 3000

STORAGE_KEY = f"{DOMAIN}.engine_probe"
STORAGE_VERSION = 1

ISSUE_ID = "engine_crashed"
ISSUES_URL = "https://github.com/adrienbrault/geekmagic-hacs/issues"

DATA_ENGINE_PROBE: HassKey[asyncio.Task[bool]] = HassKey(f"{DOMAIN}_engine_probe")

# Runs in the child. Imports the self-test from the package directory
# WITHOUT running the package's ``__init__`` (which pulls in Home
# Assistant): the package and its parent are stubbed as bare namespace
# modules. The parent's sys.path is reused verbatim, so the child finds
# the very blitz-py Core would import (including a ``deps`` directory
# Home Assistant may add at runtime).
_BOOTSTRAP = """\
import importlib, json, os, sys, types
args = json.loads(sys.argv[1])
sys.path[:] = args["sys_path"]
package = args["package"]
paths = {package: args["path"]}
parent = package.rpartition(".")[0]
if parent:
    paths[parent] = os.path.dirname(args["path"])
for name in sorted(paths):
    module = types.ModuleType(name)
    module.__path__ = [paths[name]]
    sys.modules[name] = module
sys.exit(importlib.import_module(package + ".engine_selftest").main())
"""


@dataclass(frozen=True)
class ProbeResult:
    """How the self-test child ended."""

    returncode: int | None
    stderr: str = ""
    timed_out: bool = False
    spawn_error: str | None = None

    @property
    def passed(self) -> bool:
        """The frame rendered."""
        return self.returncode == EXIT_OK

    @property
    def no_engine(self) -> bool:
        """blitz-py is missing or too old: nothing native ran."""
        return self.returncode == EXIT_NO_ENGINE

    def describe(self) -> str:
        """One phrase for logs and the repair issue: what went wrong."""
        if self.spawn_error is not None:
            return f"could not start: {self.spawn_error}"
        if self.timed_out:
            return f"no answer after {PROBE_TIMEOUT:.0f} s"
        code = self.returncode
        if code is not None and code < 0:
            try:
                name = signal.Signals(-code).name
            except ValueError:
                name = "an unknown signal"
            return f"killed by {name} (signal {-code})"
        return f"exited with code {code}"


async def async_run_probe() -> ProbeResult:
    """Run the self-test in a child Python; never raises (but cancellation)."""
    package_dir = Path(__file__).parent
    args = json.dumps({"package": __package__, "path": str(package_dir), "sys_path": sys.path})
    try:
        proc = await create_subprocess_exec(
            sys.executable,
            # No user site-packages and no cwd on sys.path (it comes from
            # args), but Core's environment stays: not -I, which would also
            # drop PYTHON* settings such as the PYTHONMALLOC=mimalloc
            # Home Assistant's image runs Core with
            "-s",
            "-P",
            "-X",
            "faulthandler",  # a native crash prints the Python stack
            "-c",
            _BOOTSTRAP,
            args,
            stdin=DEVNULL,
            stdout=DEVNULL,
            stderr=PIPE,
        )
    except OSError as err:
        return ProbeResult(None, spawn_error=f"{type(err).__name__}: {err}")

    communicate = asyncio.ensure_future(proc.communicate())
    try:
        done, _pending = await asyncio.wait({communicate}, timeout=PROBE_TIMEOUT)
        timed_out = not done
        if timed_out:
            with suppress(ProcessLookupError):
                proc.kill()
        # After a kill the pipe closes, so this returns what the child
        # managed to print before it hung.
        _stdout, stderr = await communicate
    except asyncio.CancelledError:
        with suppress(ProcessLookupError):
            proc.kill()
        communicate.cancel()
        raise
    tail = (stderr or b"").decode("utf-8", "replace")[-_STDERR_TAIL_CHARS:].strip()
    return ProbeResult(None if timed_out else proc.returncode, tail, timed_out=timed_out)


def _cpu_flags_hash() -> str:
    """Hash of the CPU feature line (x86 ``flags``, ARM ``Features``).

    A VM moved to a host with a different CPU model gets a new key, so
    it re-probes. Empty where /proc/cpuinfo is not readable.
    """
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in cpuinfo.splitlines():
        label = line.split(":", 1)[0].strip()
        if label in ("flags", "Features"):
            return hashlib.sha256(line.encode()).hexdigest()[:16]
    return ""


def probe_environment(integration_version: str) -> tuple[dict[str, str] | None, str]:
    """The cache key for a passed self-test, and a platform description.

    Blocking (package metadata, /proc/cpuinfo, ``platform``): run it in
    the executor. The key is None when blitz-py is not installed — there
    is nothing to probe. It holds every input the verdict depends on:
    the engine build, the interpreter, the CPU (architecture and
    feature flags), and the integration version (the self-test renders
    through the integration's own code).
    """
    description = platform.platform()
    blitz = engine.installed_version()
    if blitz is None:
        return None, description
    key = {
        "blitz_py": blitz,
        "python": platform.python_version(),
        "machine": platform.machine(),
        "cpu_flags": _cpu_flags_hash(),
        "integration": integration_version,
    }
    return key, description


@callback
def async_start_engine_probe(hass: HomeAssistant) -> asyncio.Task[bool]:
    """Start the process's one self-test (idempotent); hold the gate until it ends."""
    task = hass.data.get(DATA_ENGINE_PROBE)
    if task is None:
        engine.hold()
        task = hass.async_create_task(_async_probe_engine(hass), "geekmagic engine self-test")
        hass.data[DATA_ENGINE_PROBE] = task
    return task


async def async_engine_ready(hass: HomeAssistant) -> bool:
    """Wait for the self-test verdict; True unless the engine was blocked.

    Shielded: a cancelled caller (a closed preview, an unloading entry)
    must not cancel the self-test every other caller is waiting on.
    """
    return await asyncio.shield(async_start_engine_probe(hass))


async def _async_probe_engine(hass: HomeAssistant) -> bool:
    store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    key: dict[str, str] = {}
    description = "unknown platform"
    try:
        integration = await async_get_integration(hass, DOMAIN)
        found, description = await hass.async_add_executor_job(
            probe_environment, str(integration.version)
        )
        if found is None:
            _LOGGER.debug("blitz-py is not installed; no engine self-test to run")
            return _passed(hass)
        key = found
        if await _async_cached_key(store) == key:
            _LOGGER.debug("Engine self-test already passed for %s", key)
            return _passed(hass)
        result = await async_run_probe()
    except Exception as err:  # fail closed; _failed logs the one error
        _LOGGER.debug("The rendering engine self-test could not run", exc_info=True)
        result = ProbeResult(None, spawn_error=f"{type(err).__name__}: {err}")

    if result.passed:
        try:
            await store.async_save({"key": key})
        except Exception:  # an unsaved pass only costs a re-probe
            _LOGGER.debug("Could not cache the engine self-test verdict", exc_info=True)
        _LOGGER.debug("Engine self-test passed for %s", key)
        return _passed(hass)
    if result.no_engine:
        _LOGGER.debug("Engine self-test found no usable engine: %s", result.stderr)
        return _passed(hass)
    _failed(hass, result, key, description)
    return False


async def _async_cached_key(store: Store[dict[str, Any]]) -> Any:
    """The key of the last passed self-test; None when unreadable."""
    try:
        data = await store.async_load()
    except Exception:  # a broken cache only costs a re-probe
        _LOGGER.debug("Engine self-test cache unreadable; probing again", exc_info=True)
        return None
    return data.get("key") if isinstance(data, dict) else None


def _passed(hass: HomeAssistant) -> bool:
    engine.release()
    ir.async_delete_issue(hass, DOMAIN, ISSUE_ID)
    return True


def _failed(
    hass: HomeAssistant, result: ProbeResult, key: dict[str, str], description: str
) -> None:
    reason = result.describe()
    engine.block(reason)
    _LOGGER.error(
        "The GeekMagic rendering engine failed its self-test in a separate process: "
        "%s. It was not loaded into Home Assistant, where the same crash would have "
        "taken Home Assistant down. blitz-py %s, Python %s, %s. Displays show "
        "'Rendering engine disabled' until a self-test passes; it runs again at "
        "every restart. Please report this message at %s. Self-test output:\n%s",
        reason,
        key.get("blitz_py", "unknown"),
        key.get("python", platform.python_version()),
        description,
        ISSUES_URL,
        result.stderr or "(none)",
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_ID,
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_ID,
        translation_placeholders={
            "reason": reason,
            "blitz_version": key.get("blitz_py", "unknown"),
            "platform": description,
            "issues_url": ISSUES_URL,
        },
        learn_more_url=ISSUES_URL,
    )
