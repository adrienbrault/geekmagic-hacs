"""The offline view renderer: its bootstrap, its command line, and parity.

``skills/geekmagic-views/scripts/render_view.py`` renders views with the
integration's own code, without Home Assistant. The parity test is the
point: the same view and data, loaded into Home Assistant and rendered by
the panel preview, give the same PNG, byte for byte.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import websocket_api
from homeassistant.components.camera import Image as CameraImage
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.util import dt as dt_util
from PIL import Image

from custom_components.geekmagic.frame import FrameInputs
from custom_components.geekmagic.view import build_layout
from custom_components.geekmagic.view_io import (
    States,
    StatesFrameData,
    load_states,
    render_view,
    resolve_forecast,
)
from custom_components.geekmagic.websocket import ws_preview_render
from scripts import make_demo_home

REPO_ROOT = Path(__file__).parent.parent
SKILL = REPO_ROOT / "skills" / "geekmagic-views"
SCRIPT = SKILL / "scripts" / "render_view.py"
DEMO = SKILL / "demo"
EXAMPLES = sorted((SKILL / "examples").glob("*.json"))
MANIFEST = json.loads((REPO_ROOT / "custom_components" / "geekmagic" / "manifest.json").read_text())


def _load_script() -> Any:
    """The script as a module (it does nothing at import)."""
    spec = importlib.util.spec_from_file_location("render_view", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_view_cli = _load_script()


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - our own interpreter and script
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


# =============================================================================
# Versions
# =============================================================================


def test_versions_match_the_manifest():
    """The release the script downloads, and the engine it installs, are the manifest's."""
    assert MANIFEST["version"] == render_view_cli.INTEGRATION_VERSION
    assert f"blitz-py=={render_view_cli.BLITZ_VERSION}" in MANIFEST["requirements"]
    pep723 = re.search(r"^# /// script\n(.*?)^# ///$", SCRIPT.read_text(), re.MULTILINE | re.DOTALL)
    assert pep723 is not None
    assert f'"blitz-py=={render_view_cli.BLITZ_VERSION}"' in pep723[1]


# =============================================================================
# Finding the integration
# =============================================================================


def test_finds_the_checkout_it_runs_from():
    assert render_view_cli.find_checkout(SCRIPT.parent) == REPO_ROOT


def test_no_checkout_outside_the_repository(tmp_path):
    assert render_view_cli.find_checkout(tmp_path) is None


def _tarball(version: str, *, extra: dict[str, bytes] | None = None, link: str | None = None):
    """A GitHub-style source tarball holding a minimal integration."""
    files = {
        "custom_components/geekmagic/manifest.json": json.dumps({"version": version}).encode(),
        "custom_components/geekmagic/view_io.py": b"# view_io\n",
        "README.md": b"readme\n",
        **(extra or {}),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"geekmagic-hacs-{version}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if link is not None:
            info = tarfile.TarInfo(f"geekmagic-hacs-{version}/custom_components/geekmagic/evil")
            info.type = tarfile.SYMTYPE
            info.linkname = link
            tar.addfile(info)
    return buf.getvalue()


class _Opener:
    """A stand-in for ``urllib.request.urlopen``: no network in tests."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float) -> Any:
        self.urls.append(url)
        return io.BytesIO(self.data)


def test_downloads_the_release_once(tmp_path):
    opener = _Opener(_tarball("9.9.9"))

    root = render_view_cli.fetch_integration("9.9.9", tmp_path, urlopen=opener)

    assert opener.urls == [
        "https://codeload.github.com/adrienbrault/geekmagic-hacs/tar.gz/refs/tags/9.9.9"
    ]
    assert (root / "custom_components" / "geekmagic" / "view_io.py").is_file()
    assert not (root / "README.md").exists(), "only the integration is extracted"
    assert [p.name for p in tmp_path.iterdir()] == ["integration-9.9.9"]
    # Cached: no second download
    assert render_view_cli.fetch_integration("9.9.9", tmp_path, urlopen=opener) == root
    assert len(opener.urls) == 1


def test_refuses_a_tarball_of_another_version(tmp_path):
    with pytest.raises(render_view_cli.UnavailableError, match=r"expected '9\.9\.9'"):
        render_view_cli.fetch_integration("9.9.9", tmp_path, urlopen=_Opener(_tarball("1.0.0")))
    assert list(tmp_path.iterdir()) == []


def test_a_release_without_the_renderer_says_so(tmp_path):
    data = _tarball("1.0.0")
    buf = io.BytesIO()
    with (
        tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as src,
        tarfile.open(fileobj=buf, mode="w:gz") as dst,
    ):
        for member in src.getmembers():
            if not member.name.endswith("view_io.py"):
                dst.addfile(member, src.extractfile(member))
    with pytest.raises(render_view_cli.UnavailableError, match="predates the offline renderer"):
        render_view_cli.fetch_integration("1.0.0", tmp_path, urlopen=_Opener(buf.getvalue()))


def test_refuses_links_out_of_the_cache(tmp_path):
    opener = _Opener(_tarball("9.9.9", link="/etc/passwd"))
    with pytest.raises(tarfile.TarError):
        render_view_cli.fetch_integration("9.9.9", tmp_path, urlopen=opener)
    assert list(tmp_path.iterdir()) == []


def test_a_failed_download_is_unavailable(tmp_path):
    def offline(url: str, timeout: float) -> Any:
        raise OSError("network is unreachable")

    with pytest.raises(render_view_cli.UnavailableError, match="could not download"):
        render_view_cli.fetch_integration("9.9.9", tmp_path, urlopen=offline)


def test_requirements_are_satisfied_here():
    """The test environment has the exact engine pin: no private virtualenv."""
    assert render_view_cli.missing_requirements() == []


# =============================================================================
# The command line (a real process, like an AI runs it)
# =============================================================================


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_renders_every_example(example, tmp_path):
    result = _run(str(example), "-o", "out.png", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    image = Image.open(tmp_path / "out.png")
    assert image.size == (240, 240)


def test_contact_sheet_and_zoom(tmp_path):
    (tmp_path / "unlocked.json").write_text(
        json.dumps({"entities": {"lock.front_door": {"state": "unlocked"}}})
    )
    result = _run(
        str(SKILL / "examples" / "html-bedside.json"),
        "--scenario",
        "unlocked.json",
        "--theme",
        "watchos",
        "--theme",
        "night",
        "--zoom",
        "2",
        "-o",
        "sheet.png",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    sheet = Image.open(tmp_path / "sheet.png")
    assert sheet.width > 2 * 480 and sheet.height > 2 * 480


def test_invalid_view_exits_1(tmp_path):
    (tmp_path / "v.json").write_text(json.dumps({"layout": "grid_9x9", "widgets": []}))
    result = _run("v.json", "--check", cwd=tmp_path)
    assert result.returncode == 1
    assert "unknown layout 'grid_9x9'" in result.stderr


def test_template_error_exits_1(tmp_path):
    view = {
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [{"type": "html", "slot": 0, "options": {"html": "{{ nope( }}"}}],
    }
    (tmp_path / "v.json").write_text(json.dumps(view))
    result = _run("v.json", cwd=tmp_path)
    assert result.returncode == 1
    assert "error:" in result.stderr
    assert (tmp_path / "view.png").is_file(), "the PNG is written anyway, to look at"


def test_missing_data_warns_without_failing_the_render(tmp_path):
    """A chart with no history for its window renders "No data", and says why."""
    view = {
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [{"type": "chart", "slot": 0, "entity_id": "sensor.energy_today"}],
    }
    (tmp_path / "v.json").write_text(json.dumps(view))
    result = _run("v.json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "warning: slot 0: no history for sensor.energy_today over 24h" in result.stderr
    assert (tmp_path / "view.png").is_file()


def test_a_panel_export_is_a_view_and_its_data(tmp_path):
    """The panel's "Copy for AI" renders as is: its view, its entities over the demo."""
    view = json.loads((SKILL / "examples" / "front-door.json").read_text())
    data = {
        "version": 1,
        "timezone": "Europe/Paris",
        "entities": {"lock.front_door": {"state": "unlocked"}},
    }
    (tmp_path / "export.json").write_text(json.dumps({**data, "view": view}))
    (tmp_path / "view.json").write_text(json.dumps(view))
    (tmp_path / "states.json").write_text(json.dumps(data))

    exported = _run("export.json", "-o", "a.png", cwd=tmp_path)
    split = _run("view.json", "--states", "states.json", "-o", "b.png", cwd=tmp_path)
    demo = _run("view.json", "-o", "c.png", cwd=tmp_path)

    assert exported.returncode == 0, exported.stderr
    assert split.returncode == 0, split.stderr
    assert demo.returncode == 0, demo.stderr
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "c.png").read_bytes()


def test_states_files_go_over_a_panel_export(tmp_path):
    """--states overrides an export's entities, as it does with the view and export split.

    The order is demo home, then the export, then each --states file:
    exports carry no pictures, and a --states file is how one is added.
    """
    view = json.loads((SKILL / "examples" / "front-door.json").read_text())
    export = {"version": 1, "entities": {"lock.front_door": {"state": "unlocked"}}}
    override = {"version": 1, "entities": {"lock.front_door": {"state": "locked"}}}
    (tmp_path / "export.json").write_text(json.dumps({**export, "view": view}))
    (tmp_path / "view.json").write_text(json.dumps(view))
    (tmp_path / "data.json").write_text(json.dumps(export))
    (tmp_path / "override.json").write_text(json.dumps(override))

    exported = _run("export.json", "--states", "override.json", "-o", "a.png", cwd=tmp_path)
    layered = ("--states", "data.json", "--states", "override.json")
    split = _run("view.json", *layered, "-o", "b.png", cwd=tmp_path)
    unlocked = _run("export.json", "-o", "c.png", cwd=tmp_path)

    assert exported.returncode == 0, exported.stderr
    assert split.returncode == 0, split.stderr
    assert unlocked.returncode == 0, unlocked.stderr
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "c.png").read_bytes()


def test_schema_demo_and_remap(tmp_path):
    schema = json.loads(_run("--schema", cwd=tmp_path).stdout)
    assert {"layouts", "themes", "widgets"} <= set(schema)

    demo = _run("--demo", cwd=tmp_path).stdout
    assert "camera.front_door  idle" in demo

    result = _run(
        str(SKILL / "examples" / "front-door.json"),
        "--map",
        "lock.front_door=lock.porch",
        "--save-view",
        "mine.json",
        "--check",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "no state for lock.porch" in result.stderr
    saved = json.loads((tmp_path / "mine.json").read_text())
    assert saved["widgets"][1]["entity_id"] == "lock.porch"


# =============================================================================
# The demo home
# =============================================================================


def test_demo_home_is_generated():
    """``home.json`` is what ``scripts/make_demo_home.py`` writes, pictures included."""
    assert (DEMO / "home.json").read_text(encoding="utf-8") == make_demo_home.home_json()
    states = load_states(DEMO / "home.json")
    pictures = [data["picture"] for data in states.entities.values() if "picture" in data]
    assert pictures
    for path in pictures:
        assert Image.open(path).size >= (240, 240)


# =============================================================================
# Parity: the CLI's PNG is the panel preview's
# =============================================================================

ART_URL = "https://art.example.com/album.jpg"
TEMPLATE_VIEW: dict[str, Any] = {
    "layout": "grid_2x2",
    "theme": "standby",
    "widgets": [
        {
            "type": "entity",
            "slot": 0,
            "entity_id": "sensor.outdoor_temperature",
            "label": "{{ name }} {{ states('sensor.co2') }}",
        },
        {
            "type": "chart",
            "slot": 1,
            "entity_id": "sensor.power_consumption",
            "options": {"hours": 24},
        },
        # Flags off: neither side draws the art / forecast it has
        {
            "type": "media",
            "slot": 2,
            "entity_id": "media_player.living_room",
            "options": {"show_album_art": False},
        },
        {
            "type": "weather",
            "slot": 3,
            "entity_id": "weather.home",
            "options": {"show_forecast": False},
        },
    ],
}
PARITY_CASES = {
    **{path.stem: json.loads(path.read_text()) for path in EXAMPLES},
    "templates_and_flags": TEMPLATE_VIEW,
}


@pytest.fixture
def demo_hass(hass, aioclient_mock):
    """The demo home loaded into Home Assistant, with its pictures and forecast."""
    states = load_states(DEMO / "home.json")
    for entity_id, data in states.entities.items():
        attributes = dict(data.get("attributes") or {})
        if entity_id.startswith("media_player.") and "picture" in data:
            attributes["entity_picture"] = ART_URL
        hass.states.async_set(entity_id, data["state"], attributes)
    aioclient_mock.get(ART_URL, content=(DEMO / "album.jpg").read_bytes())

    forecast_calls: list[ServiceCall] = []

    async def get_forecasts(call: ServiceCall):
        forecast_calls.append(call)
        forecast = states.entities["weather.home"]["forecast"]
        return {"weather.home": {"forecast": resolve_forecast(forecast, dt_util.now())}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    camera = AsyncMock(
        return_value=CameraImage("image/jpeg", (DEMO / "front_door.jpg").read_bytes())
    )
    with patch("homeassistant.components.camera.async_get_image", camera):
        yield {
            "states": states,
            "camera": camera,
            "forecasts": forecast_calls,
            "art": lambda: sum(str(call[1]) == ART_URL for call in aioclient_mock.mock_calls),
        }


def _with_recorded_series(states: States, view: dict[str, Any]):
    """Serve the demo's history and candles as FrameInputs' recorder fetch.

    A recorder can't hand back an exact pre-resampled series, so the two
    fetchers are replaced by what the states file says (``StatesFrameData``):
    everything downstream of the fetch is the real pipeline on both sides.
    """
    served: list[int] = []

    async def chart_history(self: FrameInputs, widgets: Any) -> None:
        data = StatesFrameData(states, build_layout(view), dt_util.now())
        self.chart_history.update(data.chart_history)
        served.append(len(data.chart_history))

    async def candlesticks(self: FrameInputs, widgets: Any) -> None:
        data = StatesFrameData(states, build_layout(view), dt_util.now())
        self.candlestick_data.update(data.candlestick_data)
        served.append(len(data.candlestick_data))

    return served, (
        patch.object(FrameInputs, "async_fetch_chart_history", chart_history),
        patch.object(FrameInputs, "async_fetch_candlestick_history", candlesticks),
    )


@pytest.mark.parametrize("case", list(PARITY_CASES))
async def test_cli_render_matches_the_preview(hass, hass_ws_client, freezer, demo_hass, case):
    """Demo data in Home Assistant, through the panel preview == the CLI's PNG."""
    websocket_api.async_register_command(hass, ws_preview_render)
    client = await hass_ws_client(hass)
    view = PARITY_CASES[case]
    states: States = demo_hass["states"]
    served, patches = _with_recorded_series(states, view)

    with patches[0], patches[1]:
        await client.send_json({"id": 1, "type": "geekmagic/preview/render", "view_config": view})
        msg = await client.receive_json()
    assert msg["success"], msg
    preview_png = base64.b64decode(msg["result"]["image"])

    # What Home Assistant rendered for the label template, as an export carries it
    templates: dict[int, dict[str, str]] = {}
    if case == "templates_and_flags":
        templates = {0: {TEMPLATE_VIEW["widgets"][0]["label"]: "Outdoor 612"}}
    cli_states = States(entities=states.entities, templates=templates)
    cli_png = await hass.async_add_executor_job(
        lambda: render_view(view, cli_states, now=dt_util.now())
    )

    assert cli_png == preview_png, "the CLI differs from the panel preview"
    # Both sides really drew the inputs this view reads
    dumped = json.dumps(view)
    if "camera.front_door" in dumped:
        assert demo_hass["camera"].await_count >= 1
    if "media_player.living_room" in dumped and case != "templates_and_flags":
        assert demo_hass["art"]() >= 1
    else:
        assert demo_hass["art"]() == 0
    if "weather.home" in dumped and case != "templates_and_flags":
        assert demo_hass["forecasts"]
    if "history(" in dumped or '"chart"' in dumped or '"candlestick"' in dumped:
        assert any(served)
    assert Image.open(BytesIO(cli_png)).size == (240, 240)
