"""The engine self-test keeps a crashing blitz-py out of Home Assistant (#262).

A native crash in the rendering engine cannot be caught: it kills Core.
So the engine only loads into Home Assistant after a throwaway child
process has rendered a frame with it. These tests drive that gate
through the real integration setup, with the child mocked at
``create_subprocess_exec`` — except one, which runs the real child.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component
from PIL import Image

from custom_components.geekmagic import engine, engine_probe
from custom_components.geekmagic.const import DOMAIN, LAYOUT_GRID_2X2, THEME_WATCHOS
from custom_components.geekmagic.engine_probe import (
    ISSUE_ID,
    STORAGE_KEY,
    ProbeResult,
    async_run_probe,
    probe_environment,
)
from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.view import render_still

from .conftest import FakeProbeProcess
from .test_ha_integration import setup_integration

REPO_ROOT = Path(__file__).parent.parent

SIGILL_STDERR = (
    b"geekmagic engine self-test: loading blitz_py\n"
    b"Fatal Python error: Illegal instruction\n\n"
    b'  File "<frozen importlib._bootstrap>", line 488 in _call_with_frames_removed\n'
)


@pytest.fixture
def engine_import():
    """Unload the engine and record every attempt to import it in Core.

    The suite itself has ``blitz_py`` in ``sys.modules`` already, so "was
    it imported" is asked of the accessor's only import seam instead.
    """
    calls: list[str] = []
    real_import = engine.import_module

    def _import(name: str):
        calls.append(name)
        return real_import(name)

    engine._loaded = False
    engine._module = None
    with patch.object(engine, "import_module", _import):
        yield calls


async def _current_key(hass: HomeAssistant) -> dict[str, str]:
    integration = await async_get_integration(hass, DOMAIN)
    key, _description = await hass.async_add_executor_job(
        probe_environment, str(integration.version)
    )
    assert key is not None
    return key


def _cache(hass_storage, key: dict[str, str]) -> None:
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {"key": key},
    }


def _issue(hass: HomeAssistant) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID)


def _disabled_screen_png() -> bytes:
    """The frame a display gets while the engine is blocked."""
    renderer = Renderer()
    with (
        patch.object(engine, "_gate", engine._Gate.BLOCKED),
        patch.object(engine, "_blocked_reason", "test"),
    ):
        return renderer.to_png(render_still(renderer, Grid2x2(), {}))


def _pixels(png: bytes) -> bytes:
    return Image.open(BytesIO(png)).convert("RGB").tobytes()


def _coordinator(hass: HomeAssistant, entry):
    return hass.data[DOMAIN][entry.entry_id]


class TestSelfTestPasses:
    async def test_engine_loads_and_the_pass_is_cached(
        self, hass, aioclient_mock, hass_storage, probe_spawns, engine_import
    ):
        probe_spawns.process = FakeProbeProcess(delay=0.05)
        entry = await setup_integration(hass, aioclient_mock, theme=3)

        assert entry.state is ConfigEntryState.LOADED
        assert len(probe_spawns.calls) == 1
        assert engine_import == ["blitz_py"]
        assert engine.engine_available()
        assert hass_storage[STORAGE_KEY]["data"]["key"] == await _current_key(hass)
        frame = _coordinator(hass, entry).last_image
        assert frame is not None
        # A real frame, not a one-colour error screen.
        assert Image.open(BytesIO(frame)).convert("RGB").getcolors(maxcolors=64) is None
        assert _issue(hass) is None

    async def test_child_is_the_package_selftest_without_its_init(self, hass, probe_spawns):
        await engine_probe.async_engine_ready(hass)

        (argv,) = probe_spawns.calls
        assert argv[0] == sys.executable
        args = json.loads(argv[-1])
        assert args["package"] == "custom_components.geekmagic"
        assert Path(args["path"]) == Path(engine_probe.__file__).parent
        assert args["sys_path"] == sys.path
        assert "faulthandler" in argv

    async def test_child_keeps_cores_python_environment(self, hass, probe_spawns):
        """Not -I/-E: they drop PYTHON* settings (HA's image sets PYTHONMALLOC)."""
        await engine_probe.async_engine_ready(hass)

        (argv,) = probe_spawns.calls
        options = argv[1 : argv.index("-c")]
        assert "-s" in options
        assert "-P" in options
        assert not {"-I", "-E"} & set(options)

    async def test_cached_pass_skips_the_child(
        self, hass, aioclient_mock, hass_storage, probe_spawns
    ):
        _cache(hass_storage, await _current_key(hass))

        entry = await setup_integration(hass, aioclient_mock, theme=3)

        assert entry.state is ConfigEntryState.LOADED
        assert probe_spawns.calls == []
        assert engine.engine_available()

    async def test_new_engine_version_probes_again(
        self, hass, aioclient_mock, hass_storage, probe_spawns
    ):
        key = await _current_key(hass)
        _cache(hass_storage, {**key, "blitz_py": "0.5.0"})

        await setup_integration(hass, aioclient_mock, theme=3)

        assert len(probe_spawns.calls) == 1
        assert hass_storage[STORAGE_KEY]["data"]["key"] == key

    async def test_moved_to_another_cpu_probes_again(
        self, hass, aioclient_mock, hass_storage, probe_spawns
    ):
        key = await _current_key(hass)
        _cache(hass_storage, {**key, "cpu_flags": "0123456789abcdef"})

        await setup_integration(hass, aioclient_mock, theme=3)

        assert len(probe_spawns.calls) == 1

    async def test_one_selftest_for_every_entry_and_the_preview(self, hass, probe_spawns):
        first = engine_probe.async_start_engine_probe(hass)
        assert engine_probe.async_start_engine_probe(hass) is first
        await asyncio.gather(
            engine_probe.async_engine_ready(hass), engine_probe.async_engine_ready(hass)
        )
        assert len(probe_spawns.calls) == 1

    async def test_cancelled_waiter_does_not_cancel_the_selftest(self, hass, probe_spawns):
        probe_spawns.process = FakeProbeProcess(hang=True)
        waiter = hass.async_create_task(engine_probe.async_engine_ready(hass))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        task = engine_probe.async_start_engine_probe(hass)
        assert not task.done()
        probe_spawns.process.kill()
        await task


class TestSelfTestCrashes:
    async def test_sigill_keeps_the_engine_out_of_core(
        self, hass, aioclient_mock, probe_spawns, engine_import, caplog
    ):
        probe_spawns.process = FakeProbeProcess(-4, SIGILL_STDERR, delay=0.05)
        caplog.set_level(logging.ERROR, logger=engine_probe.__name__)

        entry = await setup_integration(hass, aioclient_mock, theme=3)

        # The display still sets up: entities exist and it is sent the
        # engine-disabled screen.
        assert entry.state is ConfigEntryState.LOADED
        assert hass.states.async_entity_ids("image")
        assert _pixels(_coordinator(hass, entry).last_image) == _pixels(_disabled_screen_png())
        assert any("doUpload" in str(url) for _m, url, *_ in aioclient_mock.mock_calls)
        # ...and the engine never came near Core.
        assert engine_import == []
        assert engine.get_engine() is None

        errors = [r for r in caplog.records if r.name == engine_probe.__name__]
        assert len(errors) == 1
        message = errors[0].getMessage()
        assert "SIGILL" in message
        assert "Illegal instruction" in message
        assert engine.installed_version() in message

        issue = _issue(hass)
        assert issue is not None
        assert issue.severity is ir.IssueSeverity.ERROR
        assert issue.translation_placeholders is not None
        assert issue.translation_placeholders["reason"] == "killed by SIGILL (signal 4)"
        assert issue.learn_more_url == engine_probe.ISSUES_URL

    async def test_failure_is_not_cached(self, hass, aioclient_mock, hass_storage, probe_spawns):
        probe_spawns.process = FakeProbeProcess(-4, SIGILL_STDERR)

        await setup_integration(hass, aioclient_mock, theme=3)

        assert STORAGE_KEY not in hass_storage

    async def test_timeout_kills_the_child_and_blocks(
        self, hass, aioclient_mock, probe_spawns, engine_import, caplog
    ):
        probe_spawns.process = FakeProbeProcess(hang=True)
        caplog.set_level(logging.ERROR, logger=engine_probe.__name__)

        with patch.object(engine_probe, "PROBE_TIMEOUT", 0.01):
            entry = await setup_integration(hass, aioclient_mock, theme=3)

        assert probe_spawns.process.killed
        assert entry.state is ConfigEntryState.LOADED
        assert _pixels(_coordinator(hass, entry).last_image) == _pixels(_disabled_screen_png())
        assert engine_import == []
        assert "no answer after" in caplog.text
        assert _issue(hass) is not None

    async def test_child_that_cannot_start_blocks(self, hass, probe_spawns, engine_import):
        async def _spawn_fails(*_args, **_kwargs):
            raise PermissionError("python3 is not executable")

        with patch.object(engine_probe, "create_subprocess_exec", _spawn_fails):
            assert await engine_probe.async_engine_ready(hass) is False

        assert engine.blocked_reason() == (
            "could not start: PermissionError: python3 is not executable"
        )
        assert engine_import == []
        assert _issue(hass) is not None

    async def test_preview_waits_for_the_verdict(
        self, hass, hass_ws_client, probe_spawns, engine_import
    ):
        """The panel preview renders even with no display set up."""
        probe_spawns.process = FakeProbeProcess(-4, SIGILL_STDERR, delay=0.05)
        assert await async_setup_component(hass, DOMAIN, {})
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "geekmagic/preview/render",
                "view_config": {
                    "layout": LAYOUT_GRID_2X2,
                    "theme": THEME_WATCHOS,
                    "widgets": [{"type": "clock", "slot": 0}],
                },
            }
        )
        response = await client.receive_json()

        assert response["success"], response
        png = base64.b64decode(response["result"]["image"])
        assert _pixels(png) == _pixels(_disabled_screen_png())
        assert engine_import == []

    async def test_missing_engine_is_not_a_crash(self, hass, probe_spawns):
        probe_spawns.process = FakeProbeProcess(3, b"no usable engine")

        assert await engine_probe.async_engine_ready(hass) is True
        assert engine.blocked_reason() is None
        assert _issue(hass) is None


class TestLaterPass:
    async def test_pass_clears_the_repair_issue(self, hass, aioclient_mock, probe_spawns):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ID,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ID,
        )

        await setup_integration(hass, aioclient_mock, theme=3)

        assert _issue(hass) is None
        assert engine.engine_available()

    async def test_cached_pass_clears_the_repair_issue(
        self, hass, aioclient_mock, hass_storage, probe_spawns
    ):
        _cache(hass_storage, await _current_key(hass))
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ID,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ID,
        )

        await setup_integration(hass, aioclient_mock, theme=3)

        assert probe_spawns.calls == []
        assert _issue(hass) is None


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (ProbeResult(-4), "killed by SIGILL (signal 4)"),
        (ProbeResult(-11), "killed by SIGSEGV (signal 11)"),
        (ProbeResult(1), "exited with code 1"),
        (ProbeResult(None, timed_out=True), "no answer after 60 s"),
    ],
)
def test_describe(result, expected):
    assert result.describe() == expected


def test_importing_the_integration_does_not_load_the_engine():
    """Every module of the package, in a fresh interpreter.

    The suite's own imports would mask it here.
    """
    code = (
        "import importlib, pkgutil, sys\n"
        "import custom_components.geekmagic as package\n"
        "for module in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):\n"
        "    importlib.import_module(module.name)\n"
        "assert 'blitz_py' not in sys.modules, 'blitz_py imported at module import'\n"
    )
    result = subprocess.run(  # noqa: S603 - our own interpreter and code
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def test_real_selftest_renders_with_the_installed_engine(probe_spawns):
    """The real child, real engine: the snippet works against what is installed."""
    with patch.object(engine_probe, "create_subprocess_exec", asyncio.create_subprocess_exec):
        result = await async_run_probe()

    assert result.passed, result.stderr
    assert "rendering a frame" in result.stderr
    assert "ok (" in result.stderr
