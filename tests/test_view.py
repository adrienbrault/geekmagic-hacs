"""``view.py``: a view built, assembled and painted without Home Assistant."""

from __future__ import annotations

import base64
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from custom_components.geekmagic.const import LAYOUT_SLOT_COUNTS, SUPERSAMPLE_SCALE
from custom_components.geekmagic.view import (
    LAYOUT_CLASSES,
    assemble_widget_states,
    build_layout,
)
from custom_components.geekmagic.widgets.state import EntityState

REPO_ROOT = Path(__file__).parent.parent
NOW = datetime(2026, 11, 16, 8, 30, tzinfo=UTC)


@dataclass
class _Data:
    """A ``FrameData`` from plain dicts, recording the pictures asked for."""

    chart_history: dict[tuple[str, float], list[float]] = field(default_factory=dict)
    candlestick_data: dict[tuple[str, int, int], list[tuple[float, float, float, float]]] = field(
        default_factory=dict
    )
    weather_forecasts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    source_images: dict[str, Image.Image] = field(default_factory=dict)
    templates: dict[Any, dict[str, str]] = field(default_factory=dict)
    radar: dict[Any, Any] = field(default_factory=dict)
    pictures: dict[str, Image.Image] = field(default_factory=dict)
    asked: list[tuple[str, str]] = field(default_factory=list)

    def picture(self, entity_id: str, kind: str) -> Image.Image | None:
        self.asked.append((entity_id, kind))
        return self.pictures.get(entity_id)


def _states(entities: dict[str, str]):
    def get(entity_id: str) -> EntityState | None:
        if entity_id not in entities:
            return None
        return EntityState(entity_id=entity_id, state=entities[entity_id], attributes={})

    return get


def test_every_layout_has_a_class():
    assert set(LAYOUT_CLASSES) == set(LAYOUT_SLOT_COUNTS)


def test_states_come_from_the_frame_data():
    layout = build_layout(
        {
            "layout": "grid_2x3",
            "widgets": [
                {"type": "chart", "slot": 0, "entity_id": "sensor.power", "options": {"hours": 6}},
                {"type": "camera", "slot": 1, "entity_id": "camera.door"},
                {"type": "media", "slot": 2, "entity_id": "media_player.den"},
                {"type": "weather", "slot": 3, "entity_id": "weather.home"},
                {"type": "image", "slot": 4, "options": {"source": "/local/a.png"}},
                {
                    "type": "html",
                    "slot": 5,
                    "options": {
                        "html": "{{ picture('media_player.den') }}{{ picture('image.snap') }}"
                        "{{ history('sensor.power', 6) }}{{ forecast('weather.home') }}"
                    },
                },
            ],
        }
    )
    big = Image.new("RGB", (2000, 2000), (200, 30, 30))
    source = Image.new("RGB", (10, 10))
    forecast = [{"datetime": "2026-11-17T12:00:00+00:00", "condition": "sunny"}]
    data = _Data(
        chart_history={("sensor.power", 6.0): [1.0, 2.0]},
        weather_forecasts={"weather.home": forecast},
        source_images={"/local/a.png": source},
        pictures={"camera.door": big, "media_player.den": big, "image.snap": big},
    )

    states = assemble_widget_states(layout, _states({"sensor.power": "3"}), data, NOW)

    assert states[0].history == [1.0, 2.0]
    assert states[0].entity is not None and states[0].entity.state == "3"
    assert states[1].image is big
    assert states[2].image is big
    assert states[3].forecast == forecast
    assert states[4].image is source
    assert set(states[5].pictures) == {"media_player.den", "image.snap"}
    assert states[5].histories == {("sensor.power", 6.0): [1.0, 2.0]}
    assert states[5].forecasts == {"weather.home": forecast}
    assert all(state.now == NOW for state in states.values())
    # Album art is asked for as media, everything else as camera
    assert sorted(set(data.asked)) == [
        ("camera.door", "camera"),
        ("image.snap", "camera"),
        ("media_player.den", "media"),
    ]


def test_html_pictures_are_fitted_to_the_cell():
    layout = build_layout(
        {
            "layout": "fullscreen",
            "widgets": [{"type": "html", "options": {"html": "{{ picture('camera.x') }}"}}],
        }
    )
    data = _Data(pictures={"camera.x": Image.new("RGB", (4000, 4000))})

    uri = assemble_widget_states(layout, _states({}), data, NOW)[0].pictures["camera.x"]

    x1, y1, x2, y2 = layout.slots[0].rect
    fitted = Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    assert fitted.size == ((x2 - x1) * SUPERSAMPLE_SCALE, (y2 - y1) * SUPERSAMPLE_SCALE)


def test_view_imports_without_home_assistant_or_the_engine():
    """In a fresh interpreter, the package's ``__init__`` skipped as tools do.

    ``homeassistant`` can't be imported at all there, and importing the
    module must not load ``blitz_py`` (the engine loads on first use only).
    """
    code = (
        "import importlib.abc, sys, types\n"
        "class NoHA(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] == 'homeassistant':\n"
        "            raise ImportError('no Home Assistant here')\n"
        "sys.meta_path.insert(0, NoHA())\n"
        "for name, path in (('custom_components', 'custom_components'),\n"
        "                   ('custom_components.geekmagic', 'custom_components/geekmagic')):\n"
        "    module = types.ModuleType(name)\n"
        "    module.__path__ = [path]\n"
        "    sys.modules[name] = module\n"
        "import custom_components.geekmagic.image_decode, custom_components.geekmagic.view\n"
        "assert 'blitz_py' not in sys.modules, 'blitz_py imported at module import'\n"
        "assert not [m for m in sys.modules if m.startswith('homeassistant')]\n"
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
