"""Test fixtures for GeekMagic integration."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from homeassistant.core import State
from PIL import Image


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return


def _init_pycares_thread():
    """Pre-initialize pycares daemon thread before any tests run.

    The pycares library (used by aiodns for DNS resolution) creates a daemon thread
    named '_run_safe_shutdown_loop' that persists for the process lifetime. HA's test
    harness asserts no new threads are left after a test. Pre-initializing ensures
    the thread exists in the 'before' snapshot.
    """
    try:
        import pycares

        # Create a channel to trigger thread creation
        pycares.Channel()
    except ImportError:
        pass


_init_pycares_thread()


class FakeProbeProcess:
    """What ``asyncio.create_subprocess_exec`` returns, for the engine self-test.

    ``returncode`` is the child's verdict (negative: killed by that
    signal); ``hang`` never finishes until killed; ``delay`` is how long
    the child takes (a real one takes about a second).
    """

    def __init__(
        self, returncode: int = 0, stderr: bytes = b"", *, hang: bool = False, delay: float = 0
    ) -> None:
        self._delay = delay
        self._final = returncode
        self._stderr = stderr
        self._hang = hang
        self._killed = asyncio.Event()
        self.returncode: int | None = None
        self.killed = False

    async def communicate(self):
        await asyncio.sleep(self._delay)
        if self._hang:
            await self._killed.wait()
            self.returncode = -9
        else:
            self.returncode = self._final
        return None, self._stderr

    def kill(self) -> None:
        self.killed = True
        self._killed.set()


@pytest.fixture
def probe_spawns():
    """Replace the self-test child; set ``.process`` to choose its fate.

    Records each spawn's argv in ``.calls``.
    """

    class _Spawner:
        def __init__(self) -> None:
            self.process = FakeProbeProcess()
            self.calls: list[tuple] = []

        async def __call__(self, *args, **kwargs):
            self.calls.append(args)
            return self.process

    spawner = _Spawner()
    with patch("custom_components.geekmagic.engine_probe.create_subprocess_exec", spawner):
        yield spawner


@pytest.fixture(autouse=True)
def _engine_selftest_passes(probe_spawns):
    """Every test's Home Assistant gets a passing engine self-test.

    The real child would cost a Python start per test. The engine gate
    is process-global, so it is restored after each test.
    """
    from custom_components.geekmagic import engine

    saved = {
        name: getattr(engine, name)
        for name in ("_gate", "_blocked_reason", "_loaded", "_module", "_meets_floor")
    }
    yield
    for name, value in saved.items():
        setattr(engine, name, value)


@pytest.fixture
def renderer():
    """Create a Renderer instance."""
    from custom_components.geekmagic.renderer import Renderer

    return Renderer()


@pytest.fixture
def sample_image():
    """Create a sample 240x240 test image."""
    return Image.new("RGB", (240, 240), (0, 0, 0))


@pytest.fixture
def recorder_history(hass):
    """A recorder whose history is whatever the test puts in the returned dict.

    Patched at Home Assistant's recorder API, below anything the integration
    owns: ``{entity_id: [(state, last_changed), ...]}``. Each query is
    listed under ``"calls"`` as ``(entity_id, start, end)``.
    """
    series: dict = {"calls": []}

    def state_changes_during_period(_hass, start, end, entity_id, **_kwargs):
        series["calls"].append((entity_id, start, end))
        return {
            entity_id: [
                State(entity_id, value, last_changed=changed, last_updated=changed)
                for value, changed in series.get(entity_id, [])
            ]
        }

    recorder = SimpleNamespace(async_add_executor_job=hass.async_add_executor_job)
    with (
        patch("homeassistant.components.recorder.get_instance", return_value=recorder),
        patch(
            "homeassistant.components.recorder.history.state_changes_during_period",
            state_changes_during_period,
        ),
    ):
        yield series
