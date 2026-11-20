#!/usr/bin/env python3
"""Push pixels to a gm_panel device and measure how fast they land.

    push.py HOST info
    push.py HOST image picture.png [--x 0 --y 0]
    push.py HOST fill 255 0 0
    push.py HOST bench [--rounds 10]

Protocol (little-endian), see components/gm_panel/gm_panel.h:
    hello  "GMH1" u16 w u16 h u32 free_heap u32 max_block    (device -> us, on connect)
    rect   "GMR1" u16 x u16 y u16 w u16 h u32 len + RGB565 BE (us -> device)
    ack    "GMA1" u32 elapsed_us u32 free_heap                (device -> us, per rect)
"""

from __future__ import annotations

import argparse
import socket
import struct
import time

from PIL import Image

PORT = 8811


def rgb565(img: Image.Image) -> bytes:
    """RGB565 in the panel's byte order (big-endian)."""
    out = bytearray()
    for r, g, b in img.convert("RGB").getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out += v.to_bytes(2, "big")
    return bytes(out)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("device closed the connection")
        data += chunk
    return data


class Panel:
    def __init__(self, host: str, port: int = PORT) -> None:
        t0 = time.perf_counter()
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        magic, self.width, self.height, self.free_heap, self.max_block = struct.unpack(
            "<4sHHII", recv_exact(self.sock, 16)
        )
        if magic != b"GMH1":
            raise ConnectionError(f"not a gm_panel device (hello {magic!r})")
        self.connect_ms = (time.perf_counter() - t0) * 1000

    def rect(self, x: int, y: int, w: int, h: int, pixels: bytes) -> tuple[float, float, int]:
        """Send one rect; return (wall ms, device ms, free heap after)."""
        if len(pixels) != w * h * 2:
            raise ValueError("pixel data must be w*h*2 bytes")
        t0 = time.perf_counter()
        self.sock.sendall(struct.pack("<4sHHHHI", b"GMR1", x, y, w, h, len(pixels)) + pixels)
        magic, elapsed_us, heap = struct.unpack("<4sII", recv_exact(self.sock, 12))
        if magic != b"GMA1":
            raise ConnectionError(f"bad ack {magic!r}")
        return (time.perf_counter() - t0) * 1000, elapsed_us / 1000, heap


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info")
    p_img = sub.add_parser("image")
    p_img.add_argument("path")
    p_img.add_argument("--x", type=int, default=0)
    p_img.add_argument("--y", type=int, default=0)
    p_fill = sub.add_parser("fill")
    p_fill.add_argument("rgb", type=int, nargs=3)
    p_bench = sub.add_parser("bench")
    p_bench.add_argument("--rounds", type=int, default=10)
    args = ap.parse_args()

    panel = Panel(args.host)
    print(f"{panel.width}x{panel.height}, free heap {panel.free_heap} B, "
          f"largest block {panel.max_block} B, connect {panel.connect_ms:.0f} ms")
    if args.cmd == "info":
        return
    if args.cmd == "fill":
        img = Image.new("RGB", (panel.width, panel.height), tuple(args.rgb))
        print("fill: wall %.0f ms, device %.0f ms, heap %d" % panel.rect(0, 0, *img.size, rgb565(img)))
    elif args.cmd == "image":
        img = Image.open(args.path).convert("RGB")
        img = img.crop((0, 0, min(img.width, panel.width - args.x), min(img.height, panel.height - args.y)))
        print("image: wall %.0f ms, device %.0f ms, heap %d" % panel.rect(args.x, args.y, *img.size, rgb565(img)))
    elif args.cmd == "bench":
        cases = [("full 240x240", 0, 0, 240, 240), ("cell 120x120", 0, 0, 120, 120),
                 ("strip 120x60", 0, 0, 120, 60), ("digits 80x40", 80, 100, 80, 40)]
        for name, x, y, w, h in cases:
            walls, devs = [], []
            for i in range(args.rounds):
                shade = (i * 40) % 256
                pixels = rgb565(Image.new("RGB", (w, h), (shade, 255 - shade, 128)))
                wall, dev, heap = panel.rect(x, y, w, h, pixels)
                walls.append(wall)
                devs.append(dev)
            walls.sort()
            kb = w * h * 2 / 1024
            med = walls[len(walls) // 2]
            print(f"{name:14s} {kb:6.1f} KB  wall median {med:6.0f} ms (min {walls[0]:.0f}, max {walls[-1]:.0f})"
                  f"  device median {sorted(devs)[len(devs) // 2]:6.0f} ms  ->  {1000 / med:5.1f} rect/s,"
                  f" {kb * 8 / med:5.2f} Mbit/s, heap {heap}")


if __name__ == "__main__":
    main()
