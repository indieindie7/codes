"""Procedural blood decals for AdventMod (ModGore): writes 32-bit TGAs with alpha
next to this script (colour already mixed for a 2x multiply: 50% grey leaves the
surface as it is), imported into AdventMod.u by Classes/ModBloodTextures.uc.

  blood_splat0..3   impact splats: a lumpy blob, satellite droplets, streaks flying outward
  blood_spray0..1   a wall spray: the same pieces thrown one way (+X), for shots that hit
                    a wall behind the victim (the projector's roll lines it up with the shot)
  blood_pool0       a pool under a body (round, thick, a soft rim)
  scorch0..2        where an energy bolt hit a wall: a burnt pit and soot rays
  casing0           a spent shell lying on the floor, from above (ModCasing's flattened self)

Blood is a metaball field: discs of different size summed as r^2/d^2, thresholded
with value noise on the edge so the outline is ragged, darker where the field is
thick. Plain Python (no numpy), seeded, so every build makes the same pictures.
"""
import math, os, random, struct

HERE = os.path.dirname(os.path.abspath(__file__))


def value_noise(size, cells, rng):
    """smooth 2D noise in 0..1 on a size x size grid, from a random lattice of cells x cells"""
    lat = [[rng.random() for _ in range(cells + 1)] for _ in range(cells + 1)]
    out = [[0.0] * size for _ in range(size)]
    for y in range(size):
        fy = y / size * cells
        y0 = int(fy); ty = fy - y0; ty = ty * ty * (3 - 2 * ty)
        for x in range(size):
            fx = x / size * cells
            x0 = int(fx); tx = fx - x0; tx = tx * tx * (3 - 2 * tx)
            a = lat[y0][x0] + (lat[y0][x0 + 1] - lat[y0][x0]) * tx
            b = lat[y0 + 1][x0] + (lat[y0 + 1][x0 + 1] - lat[y0 + 1][x0]) * tx
            out[y][x] = a + (b - a) * ty
    return out


def fbm(size, rng):
    layers = [(6, 0.45), (16, 0.35), (32, 0.2)]
    maps = [value_noise(size, c, rng) for c, _ in layers]
    return [[sum(m[y][x] * w for m, (_, w) in zip(maps, layers)) for x in range(size)] for y in range(size)]


def smoothstep(a, b, v):
    t = min(max((v - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def render(size, balls, rng, edge_noise=0.55, name="x"):
    """balls: (x, y, r, sx, sy) in 0..1 units; sx/sy stretch a ball into a streak"""
    noise = fbm(size, rng)
    px = bytearray()
    for y in range(size - 1, -1, -1):          # TGA rows bottom-up
        for x in range(size):
            u, v = (x + 0.5) / size, (y + 0.5) / size
            f = 0.0
            for bx, by, r, sx, sy in balls:
                dx, dy = (u - bx) / sx, (v - by) / sy
                d2 = dx * dx + dy * dy
                f += r * r / max(d2, 1e-6)
            n = noise[y][x]
            # ragged outline: the threshold wanders with the noise
            g = f * (1.0 + edge_noise * (n - 0.5))
            a = smoothstep(0.85, 1.15, g)
            # keep everything inside the square (no clipped edges on the projection)
            border = min(u, v, 1 - u, 1 - v)
            a *= smoothstep(0.0, 0.06, border)
            # thicker towards the middle of a body of blood, with a mottled sheen
            thick = smoothstep(1.0, 4.0, f) * (0.65 + 0.7 * (n - 0.5))
            r_ = 0.62 - 0.25 * thick + 0.06 * (n - 0.5)
            g_ = 0.05 + 0.03 * (1 - thick)
            b_ = 0.05
            a = min(max(a * (0.88 + 0.12 * thick), 0), 1)
            # drawn with the projector's modulate, which is a 2x multiply (UE2's alpha-blend
            # projector path falls through into it): 50% grey leaves the surface as it is,
            # half the blood's tint where there is blood
            col = [0.5 * (1 - a * (1 - min(max(c, 0), 1))) for c in (b_, g_, r_)]
            px += bytes([int(255 * c + 0.5) for c in col] + [int(255 * a + 0.5)])
    path = os.path.join(HERE, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path, len(balls), "pieces")


def teardrop(balls, x, y, ang, r, length):
    """a drop that hit at speed: a head and a tail of shrinking beads pointing back at the source"""
    n = max(2, int(length / max(r, 0.002) / 1.6))
    for k in range(n):
        t = k / (n - 1)
        balls.append((x - math.cos(ang) * length * t, y - math.sin(ang) * length * t, r * (1 - 0.75 * t), 1, 1))


def splat(rng, directional=False):
    balls = []
    # the main blob: overlapping discs near the centre (smaller for a spray)
    cx, cy = (0.30, 0.5) if directional else (0.5, 0.5)
    k = 0.7 if directional else 1.0
    for _ in range(rng.randint(5, 9)):
        balls.append((cx + rng.gauss(0, 0.045), cy + rng.gauss(0, 0.045), k * rng.uniform(0.028, 0.05), 1, 1))
    # droplets thrown out: many, mostly tiny (sizes fall off like a power law)
    for _ in range(rng.randint(45, 80) if not directional else rng.randint(60, 95)):
        ang = rng.gauss(0, 0.35) if directional else rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(0.08, 0.40) if not directional else rng.uniform(0.06, 0.62)
        x, y = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
        r = 0.0035 + 0.014 * rng.random() ** 3 * (1.15 - dist)
        if rng.random() < (0.35 if not directional else 0.55):
            teardrop(balls, x, y, ang, r * 1.3, rng.uniform(0.02, 0.07) * (0.6 + dist))
        else:
            balls.append((x, y, r, 1, 1))
    return balls


def pool(rng):
    balls = [(0.5 + rng.gauss(0, 0.06), 0.5 + rng.gauss(0, 0.06), rng.uniform(0.07, 0.11), 1, 1) for _ in range(6)]
    balls += [(0.5 + rng.gauss(0, 0.16), 0.5 + rng.gauss(0, 0.16), rng.uniform(0.015, 0.03), 1, 1) for _ in range(8)]
    return balls


def scorch(name, rng, size=64):
    """an energy bolt's mark: a burnt pit, soot thrown out in rays, a thin dark ring"""
    noise = fbm(size, rng)
    rays = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.0)) for _ in range(rng.randint(7, 12))]
    px = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            u, v = (x + 0.5) / size - 0.5, (y + 0.5) / size - 0.5
            d = math.hypot(u, v) * 2            # 0 centre .. 1 edge
            ang = math.atan2(v, u)
            ray = 0.0
            for a0, s in rays:
                da = math.atan2(math.sin(ang - a0), math.cos(ang - a0))
                ray = max(ray, s * math.exp(-(da * 7) ** 2))
            n = noise[y][x]
            pit = 1 - smoothstep(0.08, 0.22 + 0.06 * n, d)
            soot = (1 - smoothstep(0.15, 0.55 + 0.35 * ray, d)) * (0.55 + 0.45 * n)
            dark = min(1.0, max(pit * 0.95, soot * 0.75))
            dark *= smoothstep(0.0, 0.08, 0.5 - max(abs(u), abs(v)))
            # 2x modulate: 0.5 = untouched; soot goes toward black, a hint of brown
            c = [0.5 * (1 - dark * k) for k in (0.97, 0.95, 0.92)]   # b, g, r
            px += bytes([int(255 * q + 0.5) for q in c] + [int(255 * dark + 0.5)])
    path = os.path.join(HERE, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


def casing(name, rng, size=32):
    """a spent cartridge seen from above, lying along X: brass body, darker mouth,
    a rim at the base, a highlight along its length. 2x modulate, so 0.5 = untouched
    and brass is the floor brightened toward yellow (it can only tint what's there)"""
    px = bytearray()
    L, Wd = 0.62, 0.17                       # length and width, in texture units
    for y in range(size - 1, -1, -1):
        for x in range(size):
            u, v = (x + 0.5) / size - 0.5, (y + 0.5) / size - 0.5
            # a capsule along X
            du = max(abs(u) - (L / 2 - Wd / 2), 0)
            d = math.hypot(du, v) / (Wd / 2)
            a = 1 - smoothstep(0.85, 1.05, d)
            along = (u + L / 2) / L               # 0 base .. 1 mouth
            shade = 1.0 - 0.45 * smoothstep(0.82, 1.0, along) - 0.25 * (1 - smoothstep(0.0, 0.08, along))
            hi = math.exp(-((v + Wd * 0.18) / (Wd * 0.18)) ** 2) * 0.35
            brass = [0.30 * shade + hi * 0.5, 0.62 * shade + hi * 0.5, 0.85 * shade + hi * 0.4]   # b, g, r (relative, x2)
            c = [0.5 * (1 - a) + a * min(k, 1.0) * 0.62 for k in brass]
            # a soft contact shadow around it
            sh = (1 - smoothstep(0.9, 1.6, d)) * (1 - a) * 0.35
            c = [q * (1 - sh) for q in c]
            px += bytes([int(255 * min(max(q, 0), 1) + 0.5) for q in c] + [int(255 * max(a, sh) + 0.5)])
    path = os.path.join(HERE, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


if __name__ == "__main__":
    casing("casing0", random.Random(5000))
    for i in range(3):
        rng = random.Random(4000 + i)
        scorch("scorch%d" % i, rng)
    for i in range(4):
        rng = random.Random(1000 + i)
        render(128, splat(rng), rng, edge_noise=0.8, name="blood_splat%d" % i)
    for i in range(2):
        rng = random.Random(2000 + i)
        render(128, splat(rng, directional=True), rng, edge_noise=0.8, name="blood_spray%d" % i)
    rng = random.Random(3000)
    render(128, pool(rng), rng, edge_noise=0.35, name="blood_pool0")
