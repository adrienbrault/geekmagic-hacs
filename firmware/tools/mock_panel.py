#!/usr/bin/env python3
"""A gm_panel stand-in: speaks the device protocol and keeps a framebuffer.

    mock_panel.py [--port 8811] [--out frame.png]

Every rect is drawn into a 240x240 framebuffer, saved to --out after each
rect, so the integration side can be developed and tested with no device.
"""

from __future__ import annotations

import argparse
import socket
import struct
import time

from PIL import Image

W = H = 240


def recv_exact(conn: socket.socket, n: int) -> bytes | None:
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def from_rgb565(data: bytes, w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = []
    for i in range(0, len(data), 2):
        v = (data[i] << 8) | data[i + 1]
        r, g, b = (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F
        px.append((r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2))
    img.putdata(px)
    return img


def serve(port: int, out: str) -> None:
    fb = Image.new("RGB", (W, H))
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    print(f"mock gm_panel on 127.0.0.1:{port}, framebuffer -> {out}")
    while True:
        conn, peer = srv.accept()
        print("client", peer)
        conn.sendall(struct.pack("<4sHHII", b"GMH1", W, H, 40000, 30000))
        while True:
            head = recv_exact(conn, 16)
            if head is None:
                break
            magic, x, y, w, h, length = struct.unpack("<4sHHHHI", head)
            if magic != b"GMR1" or not w or not h or x + w > W or y + h > H or length != w * h * 2:
                print("bad header, closing")
                break
            t0 = time.perf_counter()
            data = recv_exact(conn, length)
            if data is None:
                break
            fb.paste(from_rgb565(data, w, h), (x, y))
            fb.save(out)
            conn.sendall(struct.pack("<4sII", b"GMA1", int((time.perf_counter() - t0) * 1e6), 40000))
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8811)
    ap.add_argument("--out", default="frame.png")
    a = ap.parse_args()
    serve(a.port, a.out)
