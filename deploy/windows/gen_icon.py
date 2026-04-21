"""Generate a multi-resolution placeholder icon for BinhAnHMI.

Produces BinhAnHMI.ico with a blue background and gold gear motif at
16x16, 32x32, 48x48, and 256x256 pixels.

Run from any directory — output is always placed alongside this script.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw


def _draw_gear(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    """Draw a simple gear outline centred at (cx, cy) on *draw*."""
    gold = (255, 215, 0, 255)
    teeth = 8
    r_outer = size * 13 // 32   # tip of teeth
    r_inner = size * 9 // 32    # root of teeth / gear body
    r_hub = size * 4 // 32      # centre hub radius
    line_w = max(1, size // 22)
    tooth_half = size // 24     # half-width of each tooth

    for i in range(teeth):
        angle = 2 * math.pi * i / teeth
        # Root point on outer rim
        mx = cx + r_outer * math.cos(angle)
        my = cy + r_outer * math.sin(angle)
        # Perpendicular offset for tooth width
        px = -math.sin(angle) * tooth_half
        py = math.cos(angle) * tooth_half
        # Tooth tip
        tip_r = r_outer + size // 20
        tx = cx + tip_r * math.cos(angle)
        ty = cy + tip_r * math.sin(angle)
        corners = [
            (tx + px, ty + py),
            (tx - px, ty - py),
            (mx - px, my - py),
            (mx + px, my + py),
        ]
        draw.polygon(corners, fill=gold)

    # Gear body circle (inner rim)
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        outline=gold,
        width=line_w,
    )

    # Centre hub
    draw.ellipse(
        [cx - r_hub, cy - r_hub, cx + r_hub, cy + r_hub],
        fill=gold,
    )


def make_icon(path: str) -> None:
    """Create a multi-resolution .ico at *path*.

    Draws the master image at 256x256 then uses Pillow's ICO plugin
    to produce all four standard sizes from it.
    """
    master_size = 256
    bg_color = (30, 80, 150, 255)   # #1E5096 — Binh An blue

    img = Image.new("RGBA", (master_size, master_size), bg_color)
    draw = ImageDraw.Draw(img)
    _draw_gear(draw, master_size // 2, master_size // 2, master_size)

    # Pillow ICO plugin: sizes= kwarg resamples and packs all resolutions
    img.save(
        path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    )
    print(f"BinhAnHMI.ico written to: {path}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    make_icon(os.path.join(script_dir, "BinhAnHMI.ico"))
