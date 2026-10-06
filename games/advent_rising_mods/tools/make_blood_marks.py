"""Bloody footprints and drip streaks (blood-fluid plan: footprints out of a pool, drips on a
hit body). Writes, bottom-up like all our TGAs (the game's importer ignores the orientation
flag):

  Textures/footprint_h0..2.tga, footprint_a0..2.tga   64x64, a boot sole, three strengths
                                                       (0 = fresh and dark, 2 = nearly worn off)
  Textures/drips_h.tga, drips_a.tga                    128x128, vertical streaks that tile
                                                       vertically; a TexMatrix pans them down

All are decal-style: 50% grey = no change (the decal/combiner multiplies x2).

    python tools/make_blood_marks.py
"""
import math
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "AdventMod", "Textures")
HUMAN = (76, 16, 13)
ALIEN = (70, 24, 108)


def write_tga(path, w, h, px):
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for r, g, b, a in px[y * w:(y + 1) * w]:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + body)


def mix(colour, cov):
    r = int(round(128 * (1 - cov) + colour[0] * cov))
    g = int(round(128 * (1 - cov) + colour[1] * cov))
    b = int(round(128 * (1 - cov) + colour[2] * cov))
    return (r, g, b, int(round(250 * cov)))


def footprint(colour, strength, seed):
    """a boot sole pointing +Y (the decal's +X axis is turned to the walker's direction by
    ModBloodDecal.Place, which maps the texture's X; so the sole points along texture +X)"""
    random.seed(seed)
    N = 64
    px = []
    for y in range(N):
        for x in range(N):
            # the sole along X: heel at x ~ 14, toe at x ~ 50; narrow in the middle
            u = (x - 32) / 32.0
            v = (y - 32) / 32.0
            # width profile along the sole: heel 0.42, waist 0.3, ball 0.5, toe tapering
            t = (u + 0.6) / 1.2      # 0 at heel .. 1 at toe
            if t < 0 or t > 1:
                inside = 0.0
            else:
                width = 0.42 * (1 - t) ** 0.5 if t < 0.35 else (0.3 + 0.2 * math.sin((t - 0.35) / 0.65 * math.pi))
                if t > 0.85:
                    width *= (1 - t) / 0.15 + 0.2
                edge = width - abs(v)
                inside = max(0.0, min(1.0, edge / 0.08))
            # tread: stripes across the sole, and a bare arch
            tread = 0.75 + 0.25 * (1 if int((t * 14) % 2) == 0 else -0.3)
            if 0.38 < t < 0.5:
                tread *= 0.35
            cov = inside * tread * strength * random.uniform(0.85, 1.0)
            px.append(mix(colour, max(0.0, min(1.0, cov))))
    return px


def drips(colour, seed):
    random.seed(seed)
    N = 128
    cov = [[0.0] * N for _ in range(N)]
    for _ in range(26):
        x0 = random.randint(0, N - 1)
        y0 = random.randint(0, N - 1)
        length = random.randint(20, 90)
        w = random.uniform(1.2, 3.0)
        for k in range(length):
            y = (y0 + k) % N                        # tiles vertically
            x = x0 + 0.6 * math.sin(k * 0.17 + x0)
            head = 1.0 if k > length - 8 else 0.7   # a fatter drop at the bottom
            ww = w * (1.3 if k > length - 8 else 1.0)
            for dx in range(-4, 5):
                xx = int(round(x + dx)) % N
                d = abs(xx - x)
                cov[y][xx] = max(cov[y][xx], head * max(0.0, 1 - (d / ww) ** 2))
    px = [mix(colour, min(1.0, cov[y][x] * 0.9)) for y in range(N) for x in range(N)]
    return px


def main():
    for tag, colour in (("h", HUMAN), ("a", ALIEN)):
        for k, strength in enumerate((1.0, 0.6, 0.3)):
            write_tga(os.path.join(OUT, "footprint_%s%d.tga" % (tag, k)), 64, 64, footprint(colour, strength, 11 + k))
        write_tga(os.path.join(OUT, "drips_%s.tga" % tag), 128, 128, drips(colour, 5))
    print("footprints and drips written to", OUT)


if __name__ == "__main__":
    main()
