"""Armour plates for ModArmor's plate actors (the armour rebuild, ARMOUR.md): our own meshes and
textures, attached to the Seekers' bones and thrown off when they break.

    python tools/make_plates.py

Writes AdventMod/Meshes/plate_chest.ase, plate_helmet.ase, plate_shoulder.ase, plate_thigh.ase
and AdventMod/Textures/plate_metal.tga, plate_dented.tga.

Plate space (what ModArmor lines up with the body): +X out of the body (the plate's face),
+Y across, +Z up; the origin is where the plate meets the body, sizes about unit (ModArmor
scales by the character). Every triangle has both windings, so the shells show from either
side whichever way the importer mirrors (as make_rubble.py).
"""
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_rubble  # noqa: E402  (write_ase)

TEX = os.path.join(HERE, "..", "AdventMod", "Textures")


def grid(nu, nv, point):
    """a (nu+1) x (nv+1) sheet; point(u, v) -> (x, y, z) or None (a hole); uv = (u, v)"""
    verts, uvs, index = [], [], {}
    for j in range(nv + 1):
        for i in range(nu + 1):
            p = point(i / nu, j / nv)
            if p is None:
                continue
            index[(i, j)] = len(verts)
            verts.append(p)
            uvs.append((i / nu, j / nv))
    faces = []
    for j in range(nv):
        for i in range(nu):
            q = [index.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if None in q:
                continue
            faces += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
    faces += [(a, c, b) for a, b, c in faces]
    return verts, uvs, faces


def chest(u, v):
    # a breastplate: wrapped round the chest (a cylinder about Z), narrower at the waist,
    # a ridge down the middle, the top edge cut lower at the sides (arm holes)
    a = (u - 0.5) * 2.1                          # angle across, radians
    y = (v - 0.5)                                 # -0.5 bottom .. 0.5 top
    w = 0.52 - 0.1 * max(0.0, -y) * 2             # narrower toward the waist
    r = 0.55
    if abs(a) > 1.05 * (1.0 - 0.35 * max(0.0, y - 0.15) / 0.35):
        return None
    ridge = 0.05 * max(0.0, 1 - abs(a) / 0.18)
    x = r * math.cos(a) - r * 0.82 + ridge
    return (x, w * math.sin(a) / 0.87 * 1.0, y * 1.25)


def helmet(u, v):
    # a dome over the head: upper part of a sphere, a visor opening at the front
    th = u * 2 * math.pi                          # around Z, 0 = forward (+X)
    ph = v * 0.62 * math.pi                       # from the top down
    x, y, z = math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)
    front = math.cos(th)
    if front > 0.55 and 0.2 < z < 0.62:
        return None                               # the visor slot
    return (x * 0.56, y * 0.52, z * 0.6)


def shoulder(u, v):
    # a pauldron: a cap of a sphere facing out (+X), longer downward
    th = (u - 0.5) * 2.2
    ph = (v - 0.62) * 2.0
    if th * th / 1.1 + ph * ph / 1.25 > 1.0:
        return None
    x = math.cos(th) * math.cos(ph)
    return (x * 0.5 - 0.32, math.sin(th) * math.cos(ph) * 0.5, math.sin(ph) * 0.55)


def thigh(u, v):
    # a tasset / thigh guard: a curved strip, wider at the top
    a = (u - 0.5) * (1.7 - 0.5 * (1 - v))
    r = 0.42
    return (r * math.cos(a) - r * 0.7, r * math.sin(a), (v - 0.55) * 1.0)


def write_tga(path, w, h, px):
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for r, g, b, a in px[y * w:(y + 1) * w]:
            body += bytes((b, g, r, a))
    open(path, "wb").write(hdr + body)


def metal(seed, damage):
    """dark gunmetal with a lighter rim, panel lines, rivets and scratches; damage adds dents,
    scorch and bright gouges"""
    rng = random.Random(seed)
    N = 128
    base = (128, 132, 140)                       # light steel: reads against the Seekers' dark hide
    px = []
    scratches = [(rng.uniform(0, N), rng.uniform(0, N), rng.uniform(0, math.pi), rng.uniform(6, 30)) for _ in range(14 + 30 * damage)]
    dents = [(rng.uniform(10, N - 10), rng.uniform(10, N - 10), rng.uniform(4, 11)) for _ in range(int(6 * damage))]
    for y in range(N):
        for x in range(N):
            n = rng.uniform(-6, 6)
            c = [base[0] + n, base[1] + n, base[2] + n * 1.1]
            # brushed grain
            c = [k + 4 * math.sin((y + 0.3 * x) * 0.9 + seed) for k in c]
            # the rim of the plate (texture edge = plate edge): a lighter bevel
            e = min(x, y, N - 1 - x, N - 1 - y)
            if e < 4:
                c = [k + 26 - e * 5 for k in c]
            # two panel lines
            if abs(x - N * 0.5) < 1 or abs(y - N * 0.35) < 1:
                c = [k - 22 for k in c]
            # rivets along the rim
            for cx, cy in ((10, 10), (N - 10, 10), (10, N - 10), (N - 10, N - 10), (N // 2, 10), (N // 2, N - 10)):
                d = math.hypot(x - cx, y - cy)
                if d < 2.6:
                    c = [k + 40 * (1 - d / 2.6) for k in c]
            for sx, sy, a, ln in scratches:
                dx, dy = x - sx, y - sy
                along = dx * math.cos(a) + dy * math.sin(a)
                across = -dx * math.sin(a) + dy * math.cos(a)
                if 0 < along < ln and abs(across) < 0.6:
                    c = [k + (50 if damage else 24) for k in c]
            for dx, dy, r in dents:
                d = math.hypot(x - dx, y - dy)
                if d < r:
                    t = d / r
                    c = [k * (0.45 + 0.55 * t) for k in c]          # dark crater
                    if 0.75 < t < 1:
                        c = [k + 40 for k in c]                     # its bright lip
            if damage:
                s = max(0.0, 1 - math.hypot(x - N * 0.6, y - N * 0.55) / (N * 0.45))
                c = [c[0] * (1 - 0.5 * s) + 18 * s, c[1] * (1 - 0.55 * s) + 8 * s, c[2] * (1 - 0.6 * s)]   # scorch
            px.append(tuple(max(0, min(255, int(k))) for k in c) + (255,))
    return px


def main():
    for name, fn, nu, nv in (("plate_chest", chest, 16, 12), ("plate_helmet", helmet, 18, 9),
                             ("plate_shoulder", shoulder, 12, 12), ("plate_thigh", thigh, 10, 10)):
        v, uv, f = grid(nu, nv, fn)
        make_rubble.write_ase(name, v, uv, f)
        print(name, len(v), "verts", len(f) // 2, "faces")
    write_tga(os.path.join(TEX, "plate_metal.tga"), 128, 128, metal(5, 0))
    write_tga(os.path.join(TEX, "plate_dented.tga"), 128, 128, metal(5, 1))
    print("textures written")


if __name__ == "__main__":
    main()
