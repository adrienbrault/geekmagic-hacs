"""Regression tests for profile request handling (Pro upload errors)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.geekmagic.models import DeviceFile
from custom_components.geekmagic.profiles import StockProProfile


def _pro_profile(upload_error: Exception) -> tuple[StockProProfile, AsyncMock]:
    transport = MagicMock()
    transport.post_file = AsyncMock(side_effect=upload_error)
    profile = StockProProfile(transport)
    # The album already holds dashboard.jpg from the previous refresh.
    listing = AsyncMock(return_value=[DeviceFile("dashboard.jpg", "/image/dashboard.jpg", 12)])
    return profile, listing


@pytest.mark.parametrize(
    "error",
    [
        aiohttp.ServerDisconnectedError(),
        aiohttp.ClientOSError(104, "Connection reset by peer"),
        aiohttp.ClientPayloadError("truncated"),
    ],
    ids=["disconnected", "reset", "payload"],
)
async def test_pro_upload_tolerates_disconnect_after_write(error: Exception) -> None:
    """A dropped connection after the write counts when the file is listed."""
    profile, listing = _pro_profile(error)

    with patch.object(profile, "get_image_files", listing):
        await profile.upload(b"jpeg", "dashboard.jpg")

    listing.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [
        aiohttp.ClientResponseError(MagicMock(), (), status=500, message="Server Error"),
        aiohttp.ClientResponseError(MagicMock(), (), status=413, message="Too Large"),
        aiohttp.ClientConnectorError(MagicMock(), OSError(111, "Connection refused")),
    ],
    ids=["http-500", "http-413", "connect-refused"],
)
async def test_pro_upload_failures_are_not_masked_by_old_file(error: Exception) -> None:
    """An HTTP error or a failed connect is a failure even though dashboard.jpg exists."""
    profile, listing = _pro_profile(error)

    with patch.object(profile, "get_image_files", listing), pytest.raises(type(error)):
        await profile.upload(b"jpeg", "dashboard.jpg")

    listing.assert_not_awaited()
