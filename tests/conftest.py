"""Test fixtures for GeekMagic integration."""

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
