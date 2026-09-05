# -*- coding: utf-8 -*-
"""Генерирует многоразмерный icon.ico (пиксельный сундук Minecraft-стиля) через Pillow.

ВАЖНО: Pillow корректно пишет многоразмерный .ico, если сохранять САМОЕ БОЛЬШОЕ
изображение с параметром sizes=[...] — тогда каждый размер записывается как
отдельный кадр (16/24/32/48/64/128/256). append_images для ICO ненадёжен.

Запуск: python tools/make_icon.py  →  icon.ico в корне проекта.
"""
import os
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(BASE), "icon.ico")

PAL = {
    "wh": "#caa06a", "w": "#9b7140", "wm": "#7a5a30", "wl": "#4e3a1f",
    "ih": "#aab1b6", "i": "#7c8489", "il": "#3f4549",
    "lh": "#ffd45a", "lnw": "#c89a18", "ll": "#7a5d09",
    "sh": "#1a1a1f",
}


def chest(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    lid_h = s // 2
    body_top = lid_h
    body_h = s - lid_h - max(2, s // 16)
    for y in range(0, lid_h, 2):
        d.rectangle([2, y, s - 2, y + 2], fill=PAL["wh"] if (y // 2) % 2 == 0 else PAL["w"])
    d.rectangle([2, lid_h - 4, s - 2, lid_h - 1], fill=PAL["wl"])
    for px in (s // 4, s // 2, 3 * s // 4):
        d.rectangle([px, 0, px + max(1, s // 32), lid_h], fill=PAL["wm"])
    iron_t = max(1, s // 16)
    d.rectangle([1, 0, s - 2, iron_t], fill=PAL["i"])
    d.rectangle([1, 0, s - 2, 1], fill=PAL["ih"])
    d.rectangle([1, iron_t - 1, s - 2, iron_t], fill=PAL["il"])
    bx0, by0, bx1, by1 = 1, body_top, s - 2, body_top + body_h
    for y in range(by0, by1, 2):
        d.rectangle([bx0, y, bx1, y + 2], fill=PAL["w"] if ((y - by0) // 2) % 2 == 0 else PAL["wm"])
    d.rectangle([bx0, by0, bx1, by0 + iron_t], fill=PAL["i"])
    d.rectangle([bx0, by1 - iron_t, bx1, by1], fill=PAL["i"])
    d.rectangle([bx0, by0, bx0 + 1, by1], fill=PAL["i"])
    d.rectangle([bx1 - 1, by0, bx1, by1], fill=PAL["i"])
    d.rectangle([bx0, by0, bx0 + 3, by0 + 1], fill=PAL["ih"])
    d.rectangle([bx1 - 3, by0, bx1, by0 + 1], fill=PAL["ih"])
    L_w, L_h = s // 3, s // 5
    L_x, L_y = (s - L_w) // 2, by0 + body_h // 2 - L_h // 2
    d.rectangle([L_x, L_y, L_x + L_w, L_y + L_h], fill=PAL["i"])
    d.rectangle([L_x, L_y, L_x + L_w, L_y + 2], fill=PAL["ih"])
    d.rectangle([L_x, L_y + L_h - 2, L_x + L_w, L_y + L_h], fill=PAL["il"])
    bow_t = max(1, s // 24)
    d.rectangle([L_x + L_w // 4, L_y - bow_t * 2, L_x + 3 * (L_w // 4), L_y - bow_t], fill=PAL["i"])
    sla_w, sla_h = L_w // 2, L_h // 2
    sla_x, sla_y = L_x + (L_w - sla_w) // 2, L_y + (L_h - sla_h) // 2 - 2
    d.rectangle([sla_x, sla_y, sla_x + sla_w, sla_y + sla_h], fill=PAL["lnw"])
    d.rectangle([sla_x, sla_y, sla_x + sla_w, sla_y + 1], fill=PAL["lh"])
    d.rectangle([sla_x, sla_y + sla_h - 1, sla_x + sla_w, sla_y + sla_h], fill=PAL["ll"])
    sx, sy = sla_x + sla_w // 2 - 1, sla_y + sla_h // 2
    d.rectangle([sx, sy, sx + 2, sy + 4], fill=PAL["sh"])
    riv = max(1, s // 24)
    pad = max(2, s // 24) + 1
    for (cx, cy) in [(bx0 + pad, by0 + body_h // 2), (bx1 - pad - riv, by0 + body_h // 2),
                     (bx0 + pad, by0 + pad), (bx1 - pad - riv, by0 + pad),
                     (bx0 + pad, by1 - pad - riv), (bx1 - pad - riv, by1 - pad - riv)]:
        d.rectangle([cx, cy, cx + riv, cy + riv], fill=PAL["il"])
        d.rectangle([cx, cy, cx + riv - 1, cy + riv - 1], fill=PAL["ih"])
    shadow_y = by1 + 1
    if shadow_y < s:
        d.rectangle([bx0 + 2, shadow_y, bx1 - 2, shadow_y + 1], fill=PAL["sh"])
    return img


def main():
    base = chest(256)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(OUT, format="ICO", sizes=sizes)
    import struct
    with open(OUT, "rb") as f:
        head = f.read(6)
    count = struct.unpack("<H", head[4:6])[0]
    print("Wrote %s (%d bytes), ICO frames: %d" % (OUT, os.path.getsize(OUT), count))
    assert count == len(sizes), "ICO должен содержать %d кадров, а записалось %d" % (len(sizes), count)


if __name__ == "__main__":
    main()
