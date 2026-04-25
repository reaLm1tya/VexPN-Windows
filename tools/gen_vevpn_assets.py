# -*- coding: utf-8 -*-
"""Генерирует vexpn/assets/ (как iOS: GIF, PNG connect) — запуск: python tools/gen_vevpn_assets.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# pc/tools -> parent pc
PC_ROOT = Path(__file__).resolve().parent.parent
ASSETS = PC_ROOT / "vexpn" / "assets"

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Install Pillow: pip install pillow", file=sys.stderr)
    raise


def _ensure_dir() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)


def _lerp(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2, strict=True))


def _radial_wash(size: int, c_center: tuple, c_edge: tuple) -> Image.Image:
    w, h = size, size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = max(w, h) / 2.0
    for y in range(h):
        for x in range(w):
            t = min(1.0, ((x - w / 2) ** 2 + (y - h / 2) ** 2) ** 0.5 / d * 0.9)
            col = _lerp(c_center, c_edge, t)
            img.putpixel((x, y), col + (255,))
    return img


def _add_round_rect_alpha(img: Image.Image, r: int = 32) -> Image.Image:
    m = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(m)
    draw.rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1), r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), m)
    return out


def _draw_connection_png(path: Path, playing: bool) -> None:
    s = 420
    if playing:
        c1, c2 = (243, 238, 255), (200, 185, 255)
    else:
        c1, c2 = (248, 245, 255), (230, 225, 255)
    img = _radial_wash(s, c1, c2)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy, rr = s // 2, s // 2, 150
    for i, alpha in ((0, 32), (1, 16)):
        draw.ellipse(
            (cx - rr - i * 3, cy - rr - i * 3, cx + rr + i * 3, cy + rr + i * 3),
            fill=(255, 255, 255, alpha),
        )
    purple = (0x73, 0x26, 0xF2, 255)
    if not playing:
        w, h_ = 68, 120
        draw.polygon(
            (cx - w // 2, cy - h_ // 2, cx - w // 2, cy + h_ // 2, cx + 52, cy),
            fill=purple,
        )
    else:
        wbar, hbar, gap = 32, 120, 20
        x0 = cx - wbar - gap // 2
        x1 = cx + gap // 2
        rrect = 14
        draw.rounded_rectangle(
            (x0, cy - hbar // 2, x0 + wbar, cy + hbar // 2), rrect, fill=purple
        )
        draw.rounded_rectangle(
            (x1, cy - hbar // 2, x1 + wbar, cy + hbar // 2), rrect, fill=purple
        )
    out = _add_round_rect_alpha(img, 64).resize((210, 210), Image.Resampling.LANCZOS)
    out.save(path, "PNG", optimize=True)


def _append_gif_frames(path: Path, frames: list[Image.Image], duration_ms: int) -> None:
    if not frames:
        return
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )


def _thunder_gif() -> list[Image.Image]:
    w, h = 32, 32
    import math

    out: list[Image.Image] = []
    for f in range(4):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        a = 0.5 * (1.0 + math.sin(f * 1.4))
        c = (255, int(200 - 50 * a), 40, 255)
        ox = f % 2
        d.line((14 + ox, 4, 8, 16), fill=c, width=3)
        d.line((8, 16, 22, 16), fill=c, width=3)
        d.line((22, 16, 10, 30), fill=c, width=3)
        out.append(img)
    return out


def _folder_crawl_gif() -> list[Image.Image]:
    w, h = 40, 40
    frames: list[Image.Image] = []
    acc = (0x45, 0, 0xE5)
    for f in (0, 1, 2, 1):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((4, 10, 32, 30), 4, fill=(*acc, 200))
        d.polygon((4, 10, 8, 6, 20, 6, 20, 10), fill=(*_lerp(acc, (200, 180, 255), 0.2), 220))
        ox = f * 2
        d.ellipse((18 + ox, 22, 24 + ox, 28), fill=(255, 200, 80, 255))
        frames.append(img)
    return frames


def _hourglass_gif() -> list[Image.Image]:
    w, h = 24, 24
    frames: list[Image.Image] = []
    for f in (0, 1):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        top = 6 if f == 0 else 8
        col = (140, 140, 150, 255)
        d.polygon([(4, 4), (20, 4), (12, 12)], outline=col, width=1)
        d.polygon([(4, 20), (20, 20), (12, 12)], outline=col, width=1)
        fill_h = 8 - f * 2
        d.rectangle((11, top, 13, top + fill_h), fill=(0x8E, 0x8E, 0x93, 200))
        frames.append(img)
    return frames


def main() -> None:
    _ensure_dir()
    _draw_connection_png(ASSETS / "connection_disconnected.png", False)
    _draw_connection_png(ASSETS / "connection_connected.png", True)
    _append_gif_frames(ASSETS / "thunder.gif", _thunder_gif(), 50)
    _append_gif_frames(ASSETS / "spider-crawl-folder.gif", _folder_crawl_gif(), 90)
    _append_gif_frames(ASSETS / "hour-glass.gif", _hourglass_gif(), 200)
    print("OK:", ASSETS)


if __name__ == "__main__":
    main()
