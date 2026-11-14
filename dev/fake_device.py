"""Fake GeekMagic display for the local dev Home Assistant.

Emulates the stock SmallTV Ultra HTTP API closely enough for the integration
to detect it, upload frames and drive it (identity, state, brightness,
album, file list, upload, delete). Responses mirror the captures in
docs/devices/old-ultra/report.md.

Open http://localhost:<port>/ to watch the screen: the page polls the
current frame and shows the last requests, including every path the fake
does NOT implement (served as 404 and flagged), so an integration change
that starts calling a new endpoint is visible immediately.

Runs inside the Home Assistant image (which ships aiohttp); no extra deps.
"""

from __future__ import annotations

import collections
import json
import os
import time
from dataclasses import dataclass, field

from aiohttp import BodyPartReader, web
from aiohttp.typedefs import Handler

TOTAL_SPACE = 3_121_152
CUSTOM_IMAGE_THEME = 3
MODEL = os.environ.get("FAKE_MODEL_NAME", "SmallTV-Ultra")
FIRMWARE = os.environ.get("FAKE_FIRMWARE", "Ultra-V9.0.40-fake")


@dataclass
class DeviceState:
    """Mutable device state, kept in memory (a restart is a factory reset)."""

    theme: int = 1
    brightness: int = 71
    image: str | None = None
    autoplay: int = 0
    interval: int = 5
    files: dict[str, bytes] = field(default_factory=dict)
    frame_version: int = 0
    log: collections.deque[dict[str, object]] = field(
        default_factory=lambda: collections.deque(maxlen=40)
    )


STATE_KEY = web.AppKey("state", DeviceState)


def _state(request: web.Request) -> DeviceState:
    return request.app[STATE_KEY]


def _ok() -> web.Response:
    return web.Response(text="OK")


@web.middleware
async def log_requests(
    request: web.Request,
    handler: Handler,
) -> web.StreamResponse:
    """Record device API calls (not the viewer's own polling)."""
    status = 500
    try:
        response = await handler(request)
        status = response.status
    except web.HTTPException as err:
        status = err.status
        raise
    finally:
        if not request.path.startswith("/_fake/") and request.path != "/":
            _state(request).log.appendleft(
                {
                    "t": time.strftime("%H:%M:%S"),
                    "method": request.method,
                    "path": request.path_qs,
                    "status": status,
                }
            )
    return response


async def identity(_request: web.Request) -> web.Response:
    """GET /v.json - model and firmware."""
    return web.json_response({"m": MODEL, "v": FIRMWARE})


async def app_json(request: web.Request) -> web.Response:
    """GET /app.json - Ultra returns only the theme."""
    return web.json_response({"theme": _state(request).theme})


async def brightness(request: web.Request) -> web.Response:
    """GET /brt.json - brightness as a string, like the firmware."""
    return web.json_response({"brt": str(_state(request).brightness)})


async def space(request: web.Request) -> web.Response:
    """GET /space.json - flash usage in bytes."""
    used = sum(len(data) for data in _state(request).files.values())
    return web.json_response({"total": TOTAL_SPACE, "free": max(0, TOTAL_SPACE - used)})


async def album(request: web.Request) -> web.Response:
    """GET /album.json - album autoplay settings."""
    state = _state(request)
    return web.json_response({"autoplay": state.autoplay, "i_i": state.interval})


async def set_(request: web.Request) -> web.Response:
    """GET /set?... - every state-changing knob the integration uses."""
    state = _state(request)
    query = request.query
    if "brt" in query:
        state.brightness = int(query["brt"])
    if "theme" in query:
        state.theme = int(query["theme"])
        state.frame_version += 1
    if "img" in query:
        name = query["img"].rsplit("/", 1)[-1]
        if name not in state.files:
            return web.Response(text="FAIL")
        state.image = name
        state.frame_version += 1
    if "i_i" in query:
        state.interval = int(query["i_i"])
    if "autoplay" in query:
        state.autoplay = int(query["autoplay"])
    if query.get("clear") == "image":
        state.files.clear()
        state.image = None
        state.frame_version += 1
    return _ok()


async def upload(request: web.Request) -> web.Response:
    """POST /doUpload?dir=/image/ - multipart field "file"."""
    state = _state(request)
    reader = await request.multipart()
    async for part in reader:
        if isinstance(part, BodyPartReader) and part.filename:
            state.files[part.filename] = bytes(await part.read())
            # Re-uploading the displayed file refreshes the screen on the
            # real firmware without a /set?img= call.
            if part.filename == state.image:
                state.frame_version += 1
    return _ok()


async def filelist(request: web.Request) -> web.Response:
    """GET /filelist?dir=/image/ - HTML table rows, sizes in KB."""
    rows = "".join(
        f"<tr><td><a href='/image/{name}'>{name}</a></td><td>{max(1, len(data) // 1024)}</td></tr>"
        for name, data in _state(request).files.items()
    )
    return web.Response(text=f"<table>{rows}</table>", content_type="text/html")


async def image(request: web.Request) -> web.Response:
    """GET /image/<name> - raw uploaded bytes."""
    data = _state(request).files.get(request.match_info["name"])
    if data is None:
        raise web.HTTPNotFound
    return web.Response(body=data, content_type=_content_type(request.match_info["name"]))


async def delete(request: web.Request) -> web.Response:
    """GET /delete?file=/image/<name>."""
    state = _state(request)
    name = request.query.get("file", "").rsplit("/", 1)[-1]
    state.files.pop(name, None)
    if state.image == name:
        state.image = None
        state.frame_version += 1
    return _ok()


async def fake_state(request: web.Request) -> web.Response:
    """GET /_fake/state - what the viewer page polls."""
    state = _state(request)
    showing = state.image if state.theme == CUSTOM_IMAGE_THEME else None
    return web.json_response(
        {
            "model": MODEL,
            "theme": state.theme,
            "brightness": state.brightness,
            "image": showing,
            "frame_version": state.frame_version,
            "files": {name: len(data) for name, data in state.files.items()},
            "log": list(state.log),
        }
    )


async def not_found(request: web.Request) -> web.Response:
    """Anything else: 404, like a firmware without that endpoint."""
    return web.Response(status=404, text=f"Not found: {request.path}")


def _content_type(name: str) -> str:
    if name.endswith(".gif"):
        return "image/gif"
    if name.endswith(".png"):
        return "image/png"
    return "image/jpeg"


VIEWER = """<!doctype html>
<html><head><meta charset="utf-8"><title>Fake GeekMagic</title>
<style>
  body { background:#111; color:#ddd; font:13px ui-monospace,monospace; margin:24px;
         display:flex; gap:32px; flex-wrap:wrap; }
  .bezel { background:#000; padding:18px; border-radius:14px; box-shadow:0 0 0 2px #333; }
  #screen { width:480px; height:480px; image-rendering:pixelated; display:block;
            background:#000; }
  .placeholder { width:480px; height:480px; display:flex; align-items:center;
                 justify-content:center; color:#666; text-align:center; }
  table { border-collapse:collapse; } td { padding:1px 8px 1px 0; white-space:nowrap; }
  .s404 { color:#ff6b6b; font-weight:bold; } h3 { margin:16px 0 6px; color:#999; }
</style></head><body>
<div><div class="bezel"><img id="screen" alt="">
  <div id="ph" class="placeholder"></div></div>
  <p id="meta"></p></div>
<div><h3>Requests (newest first; red = error / not implemented by the fake)</h3>
<table id="log"></table><h3>Files</h3><div id="files"></div></div>
<script>
let shown = null;
async function tick() {
  try {
    const s = await (await fetch('/_fake/state')).json();
    const img = document.getElementById('screen'), ph = document.getElementById('ph');
    const key = s.image ? s.image + '#' + s.frame_version : null;
    if (key !== shown) {
      shown = key;
      if (s.image) {
        img.src = '/image/' + encodeURIComponent(s.image) + '?v=' + s.frame_version;
        img.style.display = 'block'; ph.style.display = 'none';
      } else {
        img.style.display = 'none'; ph.style.display = 'flex';
        ph.textContent = 'Built-in theme ' + s.theme + ' (no custom image showing)';
      }
    }
    img.style.filter = 'brightness(' + Math.max(0.15, s.brightness / 100) + ')';
    document.getElementById('meta').textContent =
      s.model + ' · theme ' + s.theme + ' · brightness ' + s.brightness;
    document.getElementById('log').innerHTML = s.log.map(r =>
      `<tr class="${r.status >= 400 ? 's404' : ''}"><td>${r.t}</td><td>${r.method}</td>` +
      `<td>${r.status}</td><td>${r.path.replace(/</g, '&lt;')}</td></tr>`).join('');
    document.getElementById('files').textContent =
      Object.entries(s.files).map(([n, b]) => n + ' (' + b + ' B)').join(', ') || '(none)';
  } catch (e) { /* device restarting */ }
}
setInterval(tick, 500); tick();
</script></body></html>"""


async def viewer(_request: web.Request) -> web.Response:
    """GET / - the live screen viewer."""
    return web.Response(text=VIEWER, content_type="text/html")


def build_app() -> web.Application:
    """Assemble the fake device app."""
    app = web.Application(middlewares=[log_requests], client_max_size=8 * 1024 * 1024)
    app[STATE_KEY] = DeviceState()
    app.router.add_get("/", viewer)
    app.router.add_get("/_fake/state", fake_state)
    app.router.add_get("/v.json", identity)
    app.router.add_get("/app.json", app_json)
    app.router.add_get("/brt.json", brightness)
    app.router.add_get("/space.json", space)
    app.router.add_get("/album.json", album)
    app.router.add_get("/set", set_)
    app.router.add_post("/doUpload", upload)
    app.router.add_get("/filelist", filelist)
    app.router.add_get("/image/{name}", image)
    app.router.add_get("/delete", delete)
    app.router.add_route("*", "/{tail:.*}", not_found)
    return app


if __name__ == "__main__":
    print(json.dumps({"fake_device": MODEL, "firmware": FIRMWARE}), flush=True)
    web.run_app(build_app(), port=int(os.environ.get("PORT", "80")), print=None)
