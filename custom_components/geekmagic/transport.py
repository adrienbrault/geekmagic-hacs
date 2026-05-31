"""HTTP transport helpers for GeekMagic firmware profiles."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=30)


class DeviceTransport:
    """Small HTTP transport used by firmware profile adapters."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession | None = None,
        source_address: str | None = None,
    ) -> None:
        """Initialize transport for a device host, hostname, or URL."""
        if host.startswith(("http://", "https://")):
            parsed = urlparse(host)
            self.host = parsed.netloc
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.host = host
            self.base_url = f"http://{host}"

        self._session = session
        self._owns_session = session is None
        self.source_address = source_address

    @property
    def session(self) -> aiohttp.ClientSession | None:
        """Return the current aiohttp session, if created."""
        return self._session

    @session.setter
    def session(self, value: aiohttp.ClientSession | None) -> None:
        self._session = value

    @property
    def owns_session(self) -> bool:
        """Return whether this transport owns its aiohttp session."""
        return self._owns_session

    @owns_session.setter
    def owns_session(self, value: bool) -> None:
        self._owns_session = value

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None:
            connector = (
                aiohttp.TCPConnector(local_addr=(self.source_address, 0))
                if self.source_address
                else None
            )
            self._session = aiohttp.ClientSession(timeout=TIMEOUT, connector=connector)
        return self._session

    async def close(self) -> None:
        """Close the session if this transport owns it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def check_device_response(self, response: aiohttp.ClientResponse, action: str) -> None:
        """Raise for HTTP errors and firmware-level FAIL responses."""
        response.raise_for_status()
        try:
            text = (await response.text()).strip()
        except Exception:
            return

        if text.upper() == "FAIL":
            raise RuntimeError(f"Device rejected {action}: {text}")

    async def get_json(
        self,
        path: str,
        request_timeout: aiohttp.ClientTimeout | None = None,
    ) -> dict[str, object]:
        """Fetch a JSON object from the device."""
        session = await self.get_session()
        kwargs = {"timeout": request_timeout} if request_timeout is not None else {}
        async with session.get(f"{self.base_url}{path}", **kwargs) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
            if not isinstance(data, dict):
                raise TypeError(f"Expected JSON object from {path}")
            return data

    async def get_text(self, path: str) -> str:
        """Fetch text from the device."""
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}{path}") as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as err:
            if self.is_malformed_firmware_response(err):
                return (await self.raw_http_get(path)).decode(errors="replace")
            raise

    async def get_bytes(self, path: str) -> bytes:
        """Fetch bytes from the device."""
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}{path}") as response:
                response.raise_for_status()
                return await response.read()
        except aiohttp.ClientResponseError as err:
            if self.is_malformed_firmware_response(err):
                return await self.raw_http_get(path)
            raise

    async def get_checked(self, path: str, action: str) -> None:
        """Run a GET request that must return OK rather than FAIL."""
        session = await self.get_session()
        async with session.get(f"{self.base_url}{path}") as response:
            await self.check_device_response(response, action)

    async def post_file(
        self,
        path: str,
        field_name: str,
        image_data: bytes,
        filename: str,
        content_type: str,
    ) -> None:
        """Post a multipart file upload to the device."""
        form = aiohttp.FormData()
        form.add_field(
            field_name,
            image_data,
            filename=filename,
            content_type=content_type,
        )
        session = await self.get_session()
        async with session.post(f"{self.base_url}{path}", data=form) as response:
            response.raise_for_status()

    @staticmethod
    def is_malformed_firmware_response(err: aiohttp.ClientResponseError) -> bool:
        """Return whether aiohttp rejected a known malformed device response."""
        message = str(err.message) if err.message else ""
        return err.status == 400 and (
            "Duplicate Content-Length" in message or "Data after" in message
        )

    async def raw_http_get(self, path: str) -> bytes:
        """Fallback HTTP/1.0 GET for firmware responses aiohttp refuses to parse."""
        parsed = urlparse(self.base_url)
        host = parsed.hostname or self.host
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "https":
            raise RuntimeError("Raw fallback only supports HTTP devices")

        local_addr = (self.source_address, 0) if self.source_address else None
        reader, writer = await asyncio.open_connection(host, port, local_addr=local_addr)
        try:
            request = f"GET {path} HTTP/1.0\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
            writer.write(request.encode("ascii"))
            await writer.drain()
            raw = await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()

        header, _, body = raw.partition(b"\r\n\r\n")
        status_line = header.splitlines()[0] if header else b""
        if not status_line.startswith(b"HTTP/") or b" 200 " not in status_line:
            raise RuntimeError(f"Raw HTTP GET failed for {path}: {status_line!r}")
        return body
