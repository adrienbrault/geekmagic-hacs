"""What ``FrameInputs`` fetches for a frame, and what each widget gets of it."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.util import dt as dt_util

from custom_components.geekmagic.frame import FrameInputs, build_layout, layout_widgets

POWER = "sensor.power"


def _ramp(hours: int) -> list[tuple[str, object]]:
    """One state change per hour over the last ``hours`` hours, rising from 0."""
    start = dt_util.utcnow() - timedelta(hours=hours)
    return [(str(i), start + timedelta(hours=i)) for i in range(hours)]


async def _states(hass, view: dict) -> dict:
    layout = build_layout(view)
    inputs = FrameInputs(hass)
    await inputs.async_gather(layout_widgets(layout))
    return await hass.async_add_executor_job(inputs.widget_states, layout)


async def test_charts_of_one_entity_keep_their_own_period(hass, recorder_history):
    """A 1 hour and a 24 hour chart of one sensor are two different series."""
    recorder_history[POWER] = _ramp(24)
    states = await _states(
        hass,
        {
            "layout": "split_horizontal",
            "widgets": [
                {"type": "chart", "slot": 0, "entity_id": POWER, "options": {"period": "1 hour"}},
                {"type": "chart", "slot": 1, "entity_id": POWER, "options": {"period": "24 hours"}},
            ],
        },
    )

    hour, day = states[0].history, states[1].history
    assert hour
    assert day
    # The last hour sits at the newest value; the day climbs through all of them
    assert min(hour) > min(day)
    assert len(recorder_history["calls"]) == 2
