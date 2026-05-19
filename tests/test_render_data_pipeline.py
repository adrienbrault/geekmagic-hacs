"""Tests for the render_data_pipeline module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.geekmagic.layouts.grid import Grid2x2
from custom_components.geekmagic.render_data_pipeline import RenderDataPipeline
from custom_components.geekmagic.widget_state_builder import PrefetchedData
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.chart import ChartWidget
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.media import MediaWidget


def _hass_with_states(states: dict | None = None):
    hass = MagicMock()
    resolved = states or {}
    hass.states.get = resolved.get
    hass.services.async_call = AsyncMock(return_value={})
    return hass


class TestEmptyLayout:
    @pytest.mark.asyncio
    async def test_empty_layout_does_no_fetches(self):
        pipeline = RenderDataPipeline(_hass_with_states())
        result = await pipeline.prefetch(Grid2x2())
        assert isinstance(result, PrefetchedData)
        assert result.camera_images == {}
        assert result.chart_history == {}
        assert result.weather_forecasts == {}

    @pytest.mark.asyncio
    async def test_layout_with_no_prefetchable_widgets_skips_io(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        hass = _hass_with_states()
        pipeline = RenderDataPipeline(hass)
        await pipeline.prefetch(layout)
        # No service calls — weather/recorder/camera weren't touched
        hass.services.async_call.assert_not_awaited()


class TestChartFetch:
    @pytest.mark.asyncio
    async def test_chart_widget_history_lands_in_prefetched(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        hass = _hass_with_states()
        pipeline = RenderDataPipeline(hass)

        with patch(
            "custom_components.geekmagic.render_data_pipeline.HistoryFetcher"
        ) as mock_fetcher_cls:
            instance = mock_fetcher_cls.return_value
            instance.available = True
            instance.fetch_numeric = AsyncMock(return_value=[1.0, 2.0, 3.0])
            result = await pipeline.prefetch(layout)

        assert result.chart_history["sensor.temp"] == [1.0, 2.0, 3.0]

    @pytest.mark.asyncio
    async def test_chart_skipped_when_recorder_unavailable(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            ChartWidget(WidgetConfig(widget_type="chart", slot=0, entity_id="sensor.temp")),
        )
        pipeline = RenderDataPipeline(_hass_with_states())

        with patch(
            "custom_components.geekmagic.render_data_pipeline.HistoryFetcher"
        ) as mock_fetcher_cls:
            mock_fetcher_cls.return_value.available = False
            result = await pipeline.prefetch(layout)

        assert result.chart_history == {}


class TestMediaImagesClearedWhenAttributeGone:
    @pytest.mark.asyncio
    async def test_media_image_cleared_when_entity_picture_missing(self):
        layout = Grid2x2()
        layout.set_widget(
            0,
            MediaWidget(WidgetConfig(widget_type="media", slot=0, entity_id="media_player.spk")),
        )
        # First populate the cache, then run a fetch where the state has no entity_picture
        state = MagicMock()
        state.attributes = {}  # no entity_picture
        hass = _hass_with_states({"media_player.spk": state})

        pipeline = RenderDataPipeline(hass)
        pipeline._media_images["media_player.spk"] = b"stale"

        await pipeline.prefetch(layout)
        assert "media_player.spk" not in pipeline._media_images


class TestNotificationImageSourcePassedThrough:
    @pytest.mark.asyncio
    async def test_image_source_camera_id_added_to_fetch_set(self):
        layout = Grid2x2()
        layout.set_widget(0, ClockWidget(WidgetConfig(widget_type="clock", slot=0)))
        hass = _hass_with_states()
        pipeline = RenderDataPipeline(hass)

        mock_image = MagicMock()
        mock_image.content = b"jpegbytes"
        with patch(
            "homeassistant.components.camera.async_get_image",
            new=AsyncMock(return_value=mock_image),
        ) as mock_get:
            await pipeline.prefetch(layout, image_source="camera.front_door")

        mock_get.assert_awaited_once()
        assert pipeline._camera_images["camera.front_door"] == b"jpegbytes"
