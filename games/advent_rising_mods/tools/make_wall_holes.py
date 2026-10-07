"""Bullet holes for walls (wall destruction, step 1): six 128x128 decal textures, our own
drawing, that the d3d8 layer draws through its parallax rule (decal=HASH decal_parallax.hlsl
in U2Shaders.ini: darker than mid-grey reads as deeper, up to 3 world units), so the hole
looks dug into the wall when seen at an angle, as PS2 Black's and F.E.A.R.'s impact marks.

Decal-style: 50 % grey = no change (the projector multiplies the wall x2). A hole is a dark,
ragged cavity with rubble speckle (the depth), a lighter ring of broken plaster around it
(brighter than neutral: the paint knocked off), a few short cracks, and flakes further out.

    python tools/make_wall_holes.py     writes Textures/wall_hole0..5.tga and the ini rules
"""
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tex_hash import tga_hash   # noqa: E402

TEX = os.path.join(HERE, "..", "AdventMod", "Textures")
INIS = [os.path.join(HERE, "..", "AdventMod", "System", "U2Shaders.ini"),
        r"H:\SteamLibrary\steamapps\common\Advent Rising\System\U2Shaders.ini"]
N = 128
COUNT = 6
MARK = "# wall bullet holes (tools/make_wall_holes.py): parallax, darker = deeper"


def write_tga(path, px):
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, N, N, 32, 0x08)
    body = bytearray()
    for y in range(N - 1, -1, -1):
        for r, g, b, a in px[y * N:(y + 1) * N]:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + body)


def hole(seed):
    random.seed(seed)
    rc = random.uniform(0.17, 0.24)                      # the cavity's radius (texture units)
    harm = [(k, random.uniform(0, 6.3), random.uniform(0.02, 0.06)) for k in (2, 3, 5, 7, 11, 17)]
    cracks = [(random.uniform(0, 6.3), random.uniform(1.4, 2.3), random.uniform(0.8, 1.5)) for _ in range(random.randint(2, 4))]
    flakes = [(random.uniform(0, 6.3), random.uniform(1.6, 2.4) * rc, random.uniform(0.04, 0.09)) for _ in range(random.randint(3, 6))]
    px = []
    for y in range(N):
        for x in range(N):
            u = (x + 0.5) / N - 0.5
            v = (y + 0.5) / N - 0.5
            r = math.hypot(u, v)
            a = math.atan2(v, u)
            wob = 1 + sum(amp * math.sin(a * k + ph) for k, ph, amp in harm)
            rim = rc * wob                                  # the cavity's ragged edge
            lum = 128.0
            alpha = 0.0
            if r < rim:
                # the cavity: deepest a little off centre, rubble speckle on the floor, the
                # walls of the hole steep (the parallax shader follows the darkness as depth)
                t = r / rim
                depth = 1 - t ** 3                           # a steep-walled cavity, a flat dark floor
                depth = 0.45 + 0.55 * depth
                depth *= 0.9 + 0.1 * math.sin(a * 3 + seed)
                depth *= random.uniform(0.84, 1.0)          # rubble
                lum = 128 * (1 - 0.9 * depth)
                alpha = 1.0
            else:
                # the broken plaster ring: lighter, fading out raggedly
                ring = max(0.0, 1 - (r - rim) / (rim * 0.55 * wob))
                ring = ring * ring * random.uniform(0.6, 1.0)
                lum = 128 + 45 * ring
                alpha = ring
                # cracks: thin dark lines running out from the cavity
                for ca, clen, cw in cracks:
                    da = (a - ca + math.pi) % (2 * math.pi) - math.pi
                    da += 0.25 * math.sin(r * 40 + ca)       # not quite straight
                    along = r / (rim * clen)
                    if 0 < along < 1 and abs(da) * r * N < cw * 0.9:
                        c = (1 - along) * 0.6
                        lum = min(lum, 128 * (1 - c))
                        alpha = max(alpha, c + 0.2)
                # flakes: small patches of knocked-off paint further out
                for fa, fr, fs in flakes:
                    fx, fy = fr * math.cos(fa), fr * math.sin(fa)
                    d = math.hypot(u - fx, v - fy)
                    if d < fs:
                        f = (1 - d / fs) * random.uniform(0.7, 1.0)
                        lum = max(lum, 128 + 35 * f)
                        alpha = max(alpha, f)
            lum = max(0, min(255, int(round(lum))))
            # a little warmth in the cavity (bare wall under the paint)
            rr = min(255, lum + (6 if r < rim else 0))
            bb = max(0, lum - (6 if r < rim else 0))
            px.append((rr, lum, bb, int(round(250 * min(1.0, alpha)))))
    return px


def main():
    rules = []
    for k in range(COUNT):
        path = os.path.join(TEX, "wall_hole%d.tga" % k)
        write_tga(path, hole(31 + k))
        rules.append("decal=%08x decal_parallax.hlsl" % tga_hash(path))
    for ini in INIS:
        if not os.path.exists(ini):
            continue
        s = open(ini, encoding="ascii", errors="replace").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        lines = s.splitlines()
        if MARK in lines:
            i = lines.index(MARK)
            del lines[i:i + 1 + COUNT]
        # before the live-pool block, with the other decal rules
        at = next((i for i, l in enumerate(lines) if l.startswith("# live blood pools")), len(lines))
        lines[at:at] = [MARK] + rules
        open(ini, "w", encoding="ascii", newline=nl).write("\n".join(lines) + "\n")
        print(ini, "updated")
    print("\n".join(rules))


if __name__ == "__main__":
    main()
