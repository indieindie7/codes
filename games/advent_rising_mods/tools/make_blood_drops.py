"""Falling blood drops (ModBloodDrop, ModGore's drips): small sprites, our own art. Writes, bottom-up
like all our TGAs (the game's importer ignores the orientation flag):

  Textures/blood_drop0.tga, alien_drop0.tga   32x64, a drop: round below, a short tail above
  Textures/blood_drop1.tga, alien_drop1.tga   32x64, the same drop falling fast: a thin streak

Unlike the decals these are sprites drawn STY_Alpha: the colour is the blood's own, alpha is the
shape (0 outside), with a small wet highlight. Sprites keep the texture's aspect, so the 1:2
texture is what makes the drop look stretched.

    python tools/make_blood_drops.py
"""
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "AdventMod", "Textures")
HUMAN = (112, 8, 6)       # a little brighter than the decals' colour: a sprite is lit, not multiplied
ALIEN = (92, 22, 150)
W, H = 32, 64


def write_tga(path, w, h, px):
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for r, g, b, a in px[y * w:(y + 1) * w]:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + body)


def smooth(e):
    """coverage from a signed distance (negative inside), one pixel of antialiasing"""
    return max(0.0, min(1.0, 0.5 - e))


def drop_dist(x, y, fast):
    """signed distance (pixels, roughly) to the drop's outline; y grows downward"""
    cx = W / 2 - 0.5
    if fast:
        # a streak: a thin capsule thickening toward the bottom
        top, bot = 4.0, 58.0
        if y < top:
            return math.hypot(x - cx, y - top) - 1.2        # the rounded tip
        t = min(1.0, (y - top) / (bot - top))
        r = 1.2 + 3.3 * t ** 2
        if y > bot - 4:
            return math.hypot(x - cx, (y - (bot - 4)) * 1.2) - r   # the rounded bottom
        return abs(x - cx) - r
    # a drop: a disc (radius 9 at y 44) with a tail narrowing up to y 14
    cy, r = 44.0, 9.0
    d = math.hypot(x - cx, y - cy) - r
    if y < cy:
        t = (cy - y) / (cy - 14.0)          # 0 at the disc's middle, 1 at the tail's tip
        if t <= 1:
            half = r * (1 - t) ** 1.6
            d = min(d, abs(x - cx) - half)
    return d


def sprite(colour, fast):
    px = []
    cx = W / 2 - 0.5
    for y in range(H):
        for x in range(W):
            cov = smooth(drop_dist(x, y, fast))
            if cov <= 0:
                px.append((0, 0, 0, 0))
                continue
            # the wet highlight: up and to the left on the round part
            hx, hy = (cx - 3, 40) if not fast else (cx - 1, 50)
            hl = max(0.0, 1 - math.hypot(x - hx, y - hy) / (3.5 if not fast else 2.0)) ** 2
            # darker toward the rim
            rim = 0.75 + 0.25 * cov
            r = min(255, int(colour[0] * rim + 150 * hl))
            g = min(255, int(colour[1] * rim + 110 * hl))
            b = min(255, int(colour[2] * rim + 110 * hl))
            px.append((r, g, b, int(round(235 * cov))))
    return px


def main():
    for tag, colour in (("blood", HUMAN), ("alien", ALIEN)):
        for k, fast in ((0, False), (1, True)):
            write_tga(os.path.join(OUT, "%s_drop%d.tga" % (tag, k)), W, H, sprite(colour, fast))
    print("drops written to", OUT)


if __name__ == "__main__":
    main()
