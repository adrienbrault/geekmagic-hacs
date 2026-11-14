"""Make the dev Home Assistant ready to test, with zero clicks.

Idempotent; scripts/dev-ha runs it after every `up`:

1. Onboarding through HA's own onboarding API (user dev/dev), so the
   browser never sees the wizard (trusted_networks then auto-logs in).
2. A long-lived token in dev/.state/token, for scripts and agents.
3. A GeekMagic entry for the fake device (and for GEEKMAGIC_HOST, a real
   device, when set) through the integration's real config flow.
4. Demo views through the integration's websocket API, assigned to every
   device that has none yet.

Talks only to the public HTTP/websocket APIs, never to .storage files, so it
keeps working across HA releases and integration storage changes.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp

HA_URL = os.environ.get("HA_URL", "http://homeassistant:8123")
CLIENT_ID = f"{HA_URL}/"
USERNAME = "dev"
PASSWORD = "dev"  # noqa: S105 - throwaway local dev instance
TOKEN_FILE = Path("/state/token")
FAKE_DEVICE_HOST = os.environ.get("FAKE_DEVICE_HOST", "fake-device")
REAL_DEVICE_HOST = os.environ.get("GEEKMAGIC_HOST", "").strip()

Json = dict[str, Any]


def log(message: str) -> None:
    """Print a bootstrap progress line."""
    print(f"[bootstrap] {message}", flush=True)


# ---------------------------------------------------------------- views ---

W = Json


def w(widget_type: str, slot: int, entity_id: str | None = None, **options: Any) -> W:
    """Build one widget config entry; `label` is lifted out of the options."""
    widget: W = {"type": widget_type, "slot": slot}
    if entity_id:
        widget["entity_id"] = entity_id
    if "label" in options:
        widget["label"] = options.pop("label")
    if options:
        widget["options"] = options
    return widget


def overview(theme: str, name: str) -> Json:
    """The same 2x2 board, used to compare themes side by side."""
    return {
        "name": name,
        "layout": "grid_2x2",
        "theme": theme,
        "widgets": [
            w("clock", 0, show_date=True),
            w("entity", 1, "sensor.dev_room_temperature", label="Room"),
            w("gauge", 2, "sensor.dev_cpu_load", style="ring", label="CPU"),
            w("status", 3, "input_boolean.dev_switch", label="Lamp"),
        ],
    }


VIEWS: list[Json] = [
    overview("watchos", "01 Overview (watchOS)"),
    {
        "name": "02 Weather",
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [w("weather", 0, "weather.demo_weather_south", forecast_days=3)],
    },
    {
        "name": "03 Media",
        "layout": "fullscreen",
        "theme": "watchos",
        "widgets": [w("media", 0, "media_player.living_room", show_album=True)],
    },
    {
        "name": "04 Charts",
        "layout": "grid_2x2",
        "theme": "watchos",
        "widgets": [
            w("chart", 0, "sensor.dev_cpu_load", period="1 hour", label="CPU"),
            w("chart", 1, "sensor.dev_room_temperature", period="1 hour", label="Temp"),
            w("candlestick", 2, "sensor.dev_cpu_load", candle_interval="5 minutes"),
            w("gauge", 3, "sensor.dev_room_temperature", style="arc", min=10, max=30),
        ],
    },
    {
        "name": "05 Home status",
        "layout": "grid_2x3",
        "theme": "watchos",
        "widgets": [
            w("climate", 0, "climate.hvac"),
            w("climate", 1, "climate.ecobee"),
            w(
                "status_list",
                2,
                title="Lights",
                entities=["light.bed_light", "light.ceiling_lights", "light.kitchen_lights"],
            ),
            w("status", 3, "binary_sensor.movement_backyard"),
            w("progress", 4, "sensor.dev_cpu_load", target=100, label="CPU"),
            w(
                "multi_progress",
                5,
                title="Load",
                items=[
                    {"entity_id": "sensor.dev_cpu_load", "label": "CPU", "target": 100},
                    {"entity_id": "sensor.outside_humidity", "label": "Hum", "target": 100},
                ],
            ),
        ],
    },
    {
        "name": "06 Hero",
        "layout": "hero",
        "theme": "watchos",
        "widgets": [
            w("clock", 0, show_date=True),
            w("entity", 1, "sensor.outside_temperature", label="Out"),
            w("entity", 2, "sensor.outside_humidity", label="Hum"),
            w("entity", 3, "sensor.dev_cpu_load", label="CPU"),
        ],
    },
    overview("standby", "07 Overview (StandBy)"),
    overview("night", "08 Overview (Night)"),
    overview("neon", "09 Overview (Neon)"),
    overview("retro", "10 Overview (Retro)"),
]


# --------------------------------------------------------------- client ---


class HA:
    """Minimal REST + websocket client authenticated as the dev user."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self.session = session
        self.token = token
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self._msg_id = 0

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def rest(self, method: str, path: str, payload: Json | None = None) -> Any:
        async with self.session.request(
            method, f"{HA_URL}{path}", json=payload, headers=self.headers
        ) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"{method} {path} -> {resp.status}: {await resp.text()}")
            return await resp.json()

    async def ws_call(self, msg_type: str, **payload: Any) -> Any:
        if self.ws is None:
            self.ws = await self.session.ws_connect(f"{HA_URL}/api/websocket")
            await self.ws.receive_json()  # auth_required
            await self.ws.send_json({"type": "auth", "access_token": self.token})
            reply = await self.ws.receive_json()
            if reply.get("type") != "auth_ok":
                raise RuntimeError(f"websocket auth failed: {reply}")
        self._msg_id += 1
        await self.ws.send_json({"id": self._msg_id, "type": msg_type, **payload})
        while True:
            reply = await self.ws.receive_json()
            if reply.get("id") == self._msg_id and reply.get("type") == "result":
                break
        if not reply.get("success"):
            raise RuntimeError(f"{msg_type} failed: {reply.get('error')}")
        return reply.get("result")

    async def close(self) -> None:
        if self.ws is not None:
            await self.ws.close()


# ----------------------------------------------------------- onboarding ---


async def exchange_code(session: aiohttp.ClientSession, code: str) -> str:
    """Trade an auth code for an access token."""
    async with session.post(
        f"{HA_URL}/auth/token",
        data={"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
    ) as resp:
        resp.raise_for_status()
        return (await resp.json())["access_token"]


async def login(session: aiohttp.ClientSession) -> str:
    """Password login for an already-onboarded instance."""
    async with session.post(
        f"{HA_URL}/auth/login_flow",
        json={
            "client_id": CLIENT_ID,
            "handler": ["homeassistant", None],
            "redirect_uri": f"{CLIENT_ID}?auth_callback=1",
        },
    ) as resp:
        resp.raise_for_status()
        flow_id = (await resp.json())["flow_id"]
    async with session.post(
        f"{HA_URL}/auth/login_flow/{flow_id}",
        json={"client_id": CLIENT_ID, "username": USERNAME, "password": PASSWORD},
    ) as resp:
        resp.raise_for_status()
        result = await resp.json()
    if result.get("type") != "create_entry":
        raise RuntimeError(f"login failed (did the dev user change?): {result}")
    return await exchange_code(session, result["result"])


async def onboard(session: aiohttp.ClientSession) -> str:
    """Finish any pending onboarding step; return an access token."""
    async with session.get(f"{HA_URL}/api/onboarding") as resp:
        steps = {s["step"]: s["done"] for s in await resp.json()} if resp.status == 200 else {}

    if steps and not steps.get("user", True):
        log("onboarding: creating user dev/dev")
        async with session.post(
            f"{HA_URL}/api/onboarding/users",
            json={
                "client_id": CLIENT_ID,
                "name": "Dev",
                "username": USERNAME,
                "password": PASSWORD,
                "language": "en",
            },
        ) as resp:
            resp.raise_for_status()
            token = await exchange_code(session, (await resp.json())["auth_code"])
    else:
        token = await login(session)

    headers = {"Authorization": f"Bearer {token}"}
    for step, path, payload in (
        ("core_config", "core_config", {}),
        ("analytics", "analytics", {}),
        (
            "integration",
            "integration",
            {"client_id": CLIENT_ID, "redirect_uri": f"{CLIENT_ID}?auth_callback=1"},
        ),
    ):
        if steps and not steps.get(step, True):
            log(f"onboarding: {step}")
            async with session.post(
                f"{HA_URL}/api/onboarding/{path}", json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
    return token


# ---------------------------------------------------------------- setup ---


def _token_saved() -> bool:
    return TOKEN_FILE.exists() and bool(TOKEN_FILE.read_text().strip())


async def ensure_long_lived_token(ha: HA) -> None:
    """Write a long-lived token for scripts/agents, once."""
    if await asyncio.to_thread(_token_saved):
        return
    token = await ha.ws_call(
        "auth/long_lived_access_token", client_name="dev-ha scripts", lifespan=3650
    )
    await asyncio.to_thread(TOKEN_FILE.write_text, token + "\n")
    log(f"long-lived token written to dev/.state/{TOKEN_FILE.name}")


async def ensure_device(ha: HA, host: str, name: str) -> None:
    """Add a GeekMagic entry for host through the real config flow.

    The flow's own unique-id check makes this idempotent: an existing entry
    for host aborts with "already_configured".
    """
    flow = await ha.rest("POST", "/api/config/config_entries/flow", {"handler": "geekmagic"})
    result = await ha.rest(
        "POST",
        f"/api/config/config_entries/flow/{flow['flow_id']}",
        {"host": host, "name": name},
    )
    if result.get("type") == "abort" and result.get("reason") == "already_configured":
        return
    if result.get("type") == "form" and result.get("step_id") == "pro_managed_album":
        # A real Pro asks whether we may manage its album; dev answers no.
        result = await ha.rest(
            "POST",
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            {"manage_pro_album": False},
        )
    if result.get("type") != "create_entry":
        raise RuntimeError(f"config flow for {host} did not finish: {result}")
    log(f"added GeekMagic device {name} at {host}")


async def ensure_views(ha: HA) -> None:
    """Seed the demo views (only into an empty store) and assign them."""
    existing = (await ha.ws_call("geekmagic/views/list"))["views"]
    if existing:
        view_ids = [v["id"] for v in existing]
    else:
        log(f"seeding {len(VIEWS)} views")
        view_ids = [
            (await ha.ws_call("geekmagic/views/create", **view))["view_id"] for view in VIEWS
        ]

    devices = (await ha.ws_call("geekmagic/devices/list"))["devices"]
    for device in devices:
        if not device.get("assigned_views"):
            log(f"assigning views to {device.get('name', device['entry_id'])}")
            await ha.ws_call(
                "geekmagic/devices/assign_views", entry_id=device["entry_id"], view_ids=view_ids
            )


async def wait_for_geekmagic(ha: HA) -> None:
    """Wait until the websocket API exists and every entry has a coordinator."""
    for _ in range(60):
        entries = await ha.rest("GET", "/api/config/config_entries/entry?domain=geekmagic")
        try:
            devices = (await ha.ws_call("geekmagic/devices/list"))["devices"]
        except RuntimeError:
            devices = []
        if devices and len(devices) >= len(entries):
            return
        await asyncio.sleep(1)
    raise RuntimeError("GeekMagic entries never finished setting up; see `scripts/dev-ha logs`")


async def main() -> int:
    """Bootstrap everything."""
    async with aiohttp.ClientSession() as session:
        token = await onboard(session)
        ha = HA(session, token)
        try:
            await ensure_long_lived_token(ha)
            await ensure_device(ha, FAKE_DEVICE_HOST, "Fake Display")
            if REAL_DEVICE_HOST:
                await ensure_device(ha, REAL_DEVICE_HOST, "GeekMagic Display")
            await wait_for_geekmagic(ha)
            await ensure_views(ha)
        finally:
            await ha.close()
    log("ready")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
