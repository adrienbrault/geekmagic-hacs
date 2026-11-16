"""The one door to the blitz-py rendering engine.

Nothing in the integration imports ``blitz_py`` at module level: the
engine is native code, and a native crash on import (or on the first
render) does not raise — it kills the whole Home Assistant process
(issue #262: SIGILL on every boot, Core crash-looping until the
integration folder was deleted). Every engine call goes through
:func:`get_engine`, which imports on first use.

Home Assistant runs a throwaway self-test (``engine_probe``) before the
engine may load into Core. While it runs the gate is *held* and
:func:`get_engine` answers None; a failed self-test *blocks* it for the
rest of the process, so displays get the engine-unavailable screen
instead of taking Core down. Scripts and tests never touch the gate:
it starts open, and first use just imports.

HA-free on purpose: the self-test subprocess imports this module
without Home Assistant.
"""

from __future__ import annotations

import threading
from enum import Enum
from importlib import import_module
from typing import Any

# The pipeline requires blitz-py >= 0.4.2 (layered compositing,
# process-wide font registration that survives font-less systems,
# per-layer animation clocks). An older engine on disk gets the
# install-hint screen instead of a half-working fallback pipeline: the
# legacy per-document + Pillow compositing paths were removed once
# 0.4.2 became the floor. manifest.json pins a newer release — the
# functional floor stays 0.4.2 so a working older install is not turned
# into an error screen.
ENGINE_FLOOR = (0, 4, 2)

ENGINE_DISTRIBUTION = "blitz-py"
ENGINE_MODULE = "blitz_py"


class _Gate(Enum):
    OPEN = "open"  # first use imports (scripts, tests, a passed self-test)
    HELD = "held"  # self-test running: nothing may load the engine yet
    BLOCKED = "blocked"  # self-test failed: never load it in this process


_lock = threading.Lock()
_gate = _Gate.OPEN
_blocked_reason: str | None = None
_loaded = False
_module: Any = None
_meets_floor = False


def engine_version() -> tuple[int, ...] | None:
    """The installed blitz-py version, read from package metadata.

    Never imports the engine. None when the distribution is not
    installed (or carries no parseable version). Blocking file I/O:
    call it from an executor in Home Assistant.
    """
    from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415

    try:
        raw = version(ENGINE_DISTRIBUTION)
    except PackageNotFoundError:
        return None
    parts: list[int] = []
    for piece in raw.split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or None


def _load() -> None:
    """Import the engine once (caller holds ``_lock``)."""
    global _loaded, _module, _meets_floor  # noqa: PLW0603
    try:
        module: Any = import_module(ENGINE_MODULE)
    except ImportError:
        module = None
    meets_floor = False
    if module is not None and hasattr(module, "render_layers"):
        try:
            installed = engine_version()
        except Exception:  # pragma: no cover - broken metadata
            installed = None
        # A source install without metadata: the API surface is there,
        # trust it.
        meets_floor = installed is None or installed >= ENGINE_FLOOR
    _module = module
    _meets_floor = meets_floor
    _loaded = True


def get_engine() -> Any:
    """The ``blitz_py`` module, imported on first use.

    None when it is not installed, or while the gate is held or blocked
    (the self-test has not cleared it for this process). Any engine call
    in the integration goes through here — never ``import blitz_py``.
    """
    if _gate is not _Gate.OPEN:
        return None
    if not _loaded:
        with _lock:
            if not _loaded:
                _load()
    return _module


def engine_available() -> bool:
    """True when the engine may be used and meets the pipeline's floor."""
    return get_engine() is not None and _meets_floor


def hold() -> None:
    """Keep the engine out of the process until :func:`release`/:func:`block`."""
    global _gate  # noqa: PLW0603
    with _lock:
        if _gate is _Gate.OPEN:
            _gate = _Gate.HELD


def release() -> None:
    """Let the engine load on first use (the self-test passed)."""
    global _gate, _blocked_reason  # noqa: PLW0603
    with _lock:
        _gate = _Gate.OPEN
        _blocked_reason = None


def block(reason: str) -> None:
    """Never load the engine in this process; displays explain why."""
    global _gate, _blocked_reason  # noqa: PLW0603
    with _lock:
        _gate = _Gate.BLOCKED
        _blocked_reason = reason


def blocked_reason() -> str | None:
    """Why the engine was blocked, or None when it was not."""
    return _blocked_reason if _gate is _Gate.BLOCKED else None
