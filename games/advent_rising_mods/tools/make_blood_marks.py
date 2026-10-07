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


def sole_width(t):
    """half-width of a boot outsole at 0 (heel) .. 1 (toe), in units of the sole's length;
    a rounded heel, a waist, a wide ball and a rounded toe"""
    if t < 0 or t > 1:
        return -1.0
    if t < 0.1:
        return 0.13 * math.sqrt(max(0.0, 1 - ((0.1 - t) / 0.1) ** 2))     # the heel, rounded
    if t < 0.3:
        return 0.13
    if t < 0.5:
        return 0.13 - 0.035 * math.sin((t - 0.3) / 0.2 * math.pi)        # the waist
    if t < 0.8:
        return 0.13 + 0.04 * math.sin((t - 0.5) / 0.3 * math.pi)         # the ball, the widest
    return 0.155 * math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2))       # the toe, rounded


def footprint(colour, strength, seed, left=False):
    """a boot sole pointing along texture +X (ModBloodDecal.Place turns the texture's X to
    the walker's direction): an outsole outline, a bare arch, rows of tread lugs on the
    ball and heel, a toe cap, and the inner edge straighter than the outer one; the left
    print is the mirror image. Our own drawing, no photo."""
    random.seed(seed)
    N = 128
    L = 0.82                       # the sole's length as a fraction of the texture
    px = []
    for y in range(N):
        for x in range(N):
            u = (x + 0.5) / N - 0.5
            v = (y + 0.5) / N - 0.5
            if left:
                v = -v
            t = (u + L / 2) / L       # 0 heel .. 1 toe
            w = sole_width(t)
            if w < 0:
                px.append(mix(colour, 0.0))
                continue
            # asymmetric: the inner edge (v < 0) is straighter, the outer edge bulges
            if v < 0:
                w *= 0.9 if 0.5 < t < 0.8 else 1.0
            else:
                w *= 1.1 if 0.5 < t < 0.8 else 1.0
            edge = w - abs(v)
            if edge < 0:
                px.append(mix(colour, 0.0))
                continue
            rim = max(0.0, min(1.0, edge / 0.01))             # anti-aliased outline
            # the outsole: a solid band along the edge, lugs inside
            cov = 1.0 if edge < 0.018 else 0.0
            if edge >= 0.018:
                if t < 0.3:                                       # heel block: three bars across
                    row = (t - 0.03) / 0.27 * 3
                    cov = 0.95 if (row % 1.0) > 0.3 else 0.1
                elif t < 0.5:                                     # the arch: bare
                    cov = 0.08
                elif t < 0.8:                                     # the ball: chevron lugs
                    ph = (t - 0.5) / 0.3 * 5 + abs(v) * 9
                    cov = 0.95 if (ph % 1.0) > 0.4 else 0.12
                else:                                             # the toe cap: solid
                    cov = 0.9
            # a worn, uneven print: a little noise and a lighter outer third (the foot rolls)
            cov *= random.uniform(0.8, 1.0)
            if v > w * 0.45:
                cov *= 0.75
            cov = max(0.0, min(1.0, cov * rim * strength))
            px.append(mix(colour, cov))
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


def burn(frame, seed):
    """a plasma burn on a wall, 64x64, four frames from fresh to cold: a white-hot core
    with an orange ember ring over a dark scorch (frame 0), the glow shrinking and
    reddening (1, 2), and the cold scorch alone (3). Decal-style: over 50 % grey brightens
    the wall (the ember glow), under it darkens (the soot)."""
    random.seed(seed)
    N = 64
    heat = (1.0, 0.55, 0.25, 0.0)[frame]
    # a ragged rim: several harmonics with random phases, the same for every frame
    harm = [(k, random.uniform(0, 6.3), random.uniform(0.03, 0.09)) for k in (3, 4, 6, 9, 13)]
    px = []
    for y in range(N):
        for x in range(N):
            u = (x + 0.5) / N - 0.5
            v = (y + 0.5) / N - 0.5
            r = math.hypot(u, v) * 2            # 0 centre .. 1 edge
            a = math.atan2(v, u)
            wob = 1 + sum(amp * math.sin(a * k + ph) for k, ph, amp in harm)
            # soot: dense at the centre, thinning out to a soft, broken edge
            soot = max(0.0, 1 - (r / (0.8 * wob)) ** 1.6) * random.uniform(0.75, 1.0)
            soot = min(1.0, soot * 1.25)
            # the ember: a core that shrinks as it cools, a ring around it
            core = 0.26 * heat
            glow = max(0.0, 1 - (r / max(core, 1e-3)) ** 2) * heat
            ring = max(0.0, 1 - ((r - core * 1.2) / (0.16 * heat + 1e-3)) ** 2) * 0.7 * heat if heat > 0 else 0.0
            # colour: soot darkens (toward 20), the ember brightens toward white-yellow,
            # the ring toward orange-red
            base = 128 * (1 - soot) + 22 * soot
            rr, gg, bb = base, base, base
            rr = rr * (1 - ring) + 215 * ring
            gg = gg * (1 - ring) + 95 * ring
            bb = bb * (1 - ring) + 40 * ring
            rr = rr * (1 - glow) + 255 * glow
            gg = gg * (1 - glow) + 236 * glow
            bb = bb * (1 - glow) + 170 * glow
            alpha = max(soot, glow, ring)
            px.append((int(rr), int(gg), int(bb), int(250 * min(1.0, alpha))))
    return px


def main():
    for tag, colour in (("h", HUMAN), ("a", ALIEN)):
        for k, strength in enumerate((1.0, 0.6, 0.3)):
            write_tga(os.path.join(OUT, "footprint_%s%d.tga" % (tag, k)), 128, 128, footprint(colour, strength, 11 + k))
            write_tga(os.path.join(OUT, "footprint_%sl%d.tga" % (tag, k)), 128, 128, footprint(colour, strength, 11 + k, left=True))
        write_tga(os.path.join(OUT, "drips_%s.tga" % tag), 128, 128, drips(colour, 5))
    for k in range(4):
        write_tga(os.path.join(OUT, "burn%d.tga" % k), 64, 64, burn(k, 3))
    print("footprints, drips and burns written to", OUT)


if __name__ == "__main__":
    main()
