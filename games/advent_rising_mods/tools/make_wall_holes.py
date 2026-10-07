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


def write_tga(path, px, n=None):
    n = n or N
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, n, n, 32, 0x08)
    body = bytearray()
    for y in range(n - 1, -1, -1):
        for r, g, b, a in px[y * n:(y + 1) * n]:
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


BREACHES = 3
BMARK = "# wall breaches (tools/make_wall_holes.py): clustered hits and blasts, parallax"


def breach(seed):
    """a wall breach, 256 px: the plaster knocked away in a big ragged patch (a lighter broken
    rim), the block or concrete under it (mid depth, coarse), the deepest core dark with two
    or three bent rebar lines crossing it, chips scattered round the rim"""
    rng = random.Random(seed)
    n = 256
    rp = rng.uniform(0.36, 0.42)                         # the plaster's broken edge
    rc = rp * rng.uniform(0.55, 0.65)                    # the core
    harm = [(k, rng.uniform(0, 6.3), rng.uniform(0.03, 0.08)) for k in (2, 3, 4, 6, 9, 13, 19)]
    harm2 = [(k, rng.uniform(0, 6.3), rng.uniform(0.05, 0.12)) for k in (2, 3, 5, 8)]
    bars = [(rng.uniform(-0.12, 0.12), rng.uniform(-0.4, 0.4), rng.uniform(0.6, 1.2)) for _ in range(rng.randint(2, 3))]
    flakes = [(rng.uniform(0, 6.3), rng.uniform(1.05, 1.35) * rp, rng.uniform(0.02, 0.05)) for _ in range(rng.randint(6, 11))]
    px = []
    for y in range(n):
        for x in range(n):
            u = (x + 0.5) / n - 0.5
            v = (y + 0.5) / n - 0.5
            r = math.hypot(u, v)
            a = math.atan2(v, u)
            edge = rp * (1 + sum(amp * math.sin(a * k + ph) for k, ph, amp in harm))
            core = rc * (1 + sum(amp * math.sin(a * k + ph) for k, ph, amp in harm2))
            lum, alpha = 128.0, 0.0
            if r < core:
                d = 0.75 + 0.25 * (1 - (r / core) ** 2)
                lum = 128 * (1 - 0.92 * d) * rng.uniform(0.8, 1.1)
                alpha = 1.0
                for off, tilt, bend in bars:                  # rebar: bent dark-rusty lines across
                    yy = v - off - tilt * u - 0.15 * bend * u * u
                    if abs(yy) < 0.006:
                        lum = 128 * 0.62                      # rebar sits shallower than the core
            elif r < edge:
                t = (r - core) / max(edge - core, 1e-3)       # 0 at the core .. 1 at the plaster edge
                blocky = 0.85 + 0.15 * math.sin(u * 60) * math.sin(v * 60 + 1.3)
                d = 0.62 * (1 - t) ** 0.8 * blocky
                lum = 128 * (1 - d) * rng.uniform(0.85, 1.05)
                alpha = 1.0
            else:
                ring = max(0.0, 1 - (r - edge) / (0.07 + 0.04 * math.sin(a * 5)))
                lum = 128 + 42 * ring * rng.uniform(0.7, 1.0)  # broken plaster: lighter
                alpha = ring * ring
                for fa, fr, fs in flakes:
                    d = math.hypot(u - fr * math.cos(fa), v - fr * math.sin(fa))
                    if d < fs:
                        f = 1 - d / fs
                        lum = 128 * (1 - 0.5 * f)
                        alpha = max(alpha, f)
            lum = max(0, min(255, int(lum)))
            warm = 5 if alpha > 0.5 and r < edge else 0
            px.append((min(255, lum + warm), lum, max(0, lum - warm), int(250 * min(1.0, alpha))))
    return px


def main():
    rules = []
    for k in range(COUNT):
        path = os.path.join(TEX, "wall_hole%d.tga" % k)
        write_tga(path, hole(31 + k))
        rules.append("decal=%08x decal_parallax.hlsl" % tga_hash(path))
    brules = []
    for k in range(BREACHES):
        path = os.path.join(TEX, "wall_breach%d.tga" % k)
        write_tga(path, breach(71 + k), 256)
        brules.append("decal=%08x decal_parallax.hlsl" % tga_hash(path))
    for ini in INIS:
        if not os.path.exists(ini):
            continue
        s = open(ini, encoding="ascii", errors="replace").read()
        nl = "\r\n" if "\r\n" in s else "\n"
        lines = s.splitlines()
        if MARK in lines:
            i = lines.index(MARK)
            del lines[i:i + 1 + COUNT]
        if BMARK in lines:
            i = lines.index(BMARK)
            del lines[i:i + 1 + BREACHES]
        # before the live-pool block, with the other decal rules
        at = next((i for i, l in enumerate(lines) if l.startswith("# live blood pools")), len(lines))
        lines[at:at] = [MARK] + rules + [BMARK] + brules
        open(ini, "w", encoding="ascii", newline=nl).write("\n".join(lines) + "\n")
        print(ini, "updated")
    print("\n".join(rules))


if __name__ == "__main__":
    main()
