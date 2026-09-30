"""Tests for the device HTTP transport (timeouts)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.geekmagic.device import GeekMagicDevice
from custom_components.geekmagic.transport import (
    REQUEST_TIMEOUT,
    TRANSFER_TIMEOUT,
    DeviceTransport,
)


def _response(*, json=None, text: str = "OK", body: bytes = b"") -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=json if json is not None else {})
    response.text = AsyncMock(return_value=text)
    response.read = AsyncMock(return_value=body)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


@pytest.fixture
def shared_session() -> MagicMock:
    """A caller-owned session, like Home Assistant's shared one (no own timeout)."""
    session = MagicMock()
    session.get = MagicMock(return_value=_response())
    session.post = MagicMock(return_value=_response())
    return session


async def test_requests_on_shared_session_carry_explicit_timeouts(shared_session) -> None:
    """Every request bounds itself instead of inheriting the session's default."""
    transport = DeviceTransport("192.168.1.100", session=shared_session)

    await transport.get_json("/app.json")
    await transport.get_text("/")
    await transport.get_checked("/set?brt=5", "brightness")
    await transport.get_bytes("/image/a.jpg")
    await transport.post_file("/doUpload?dir=/image/", "file", b"x", "a.jpg", "image/jpeg")

    get_timeouts = [c.kwargs["timeout"] for c in shared_session.get.call_args_list]
    assert get_timeouts == [REQUEST_TIMEOUT, REQUEST_TIMEOUT, REQUEST_TIMEOUT, TRANSFER_TIMEOUT]
    assert shared_session.post.call_args.kwargs["timeout"] == TRANSFER_TIMEOUT


async def test_per_call_timeout_override_is_kept(shared_session) -> None:
    """Detection's short probes keep their own timeout."""
    transport = DeviceTransport("192.168.1.100", session=shared_session)
    probe = aiohttp.ClientTimeout(total=5)

    await transport.get_json("/v.json", request_timeout=probe)

    assert shared_session.get.call_args.kwargs["timeout"] is probe


async def test_raw_http_get_is_bounded() -> None:
    """The raw fallback reads until EOF; a device that never closes must time out."""
    transport = DeviceTransport("192.168.1.100")

    async def never_eof(*_args: object) -> bytes:
        await asyncio.Event().wait()
        return b""

    reader = MagicMock()
    reader.read = never_eof
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()

    with (
        patch(
            "custom_components.geekmagic.transport.asyncio.open_connection",
            AsyncMock(return_value=(reader, writer)),
        ),
        pytest.raises(TimeoutError),
    ):
        await asyncio.wait_for(transport.raw_http_get("/", timeout_s=0.05), 2)

    writer.close.assert_called_once()


async def test_connection_timeout_message_matches_request_timeout(shared_session) -> None:
    """The reported timeout is the one actually applied."""
    shared_session.get.side_effect = TimeoutError()
    device = GeekMagicDevice("192.168.1.100", session=shared_session)

    result = await device.test_connection()

    assert result.error == "timeout"
    assert result.message == "Connection timed out after 10 seconds"
