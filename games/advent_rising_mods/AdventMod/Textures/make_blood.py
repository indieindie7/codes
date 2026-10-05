"""Procedural blood decals for AdventMod (ModGore): writes 32-bit TGAs with alpha
next to this script (colour already mixed for a 2x multiply: 50% grey leaves the
surface as it is), imported into AdventMod.u by Classes/ModBloodTextures.uc.

  blood_splat0..3   impact splats: a lumpy blob, satellite droplets, streaks flying outward
  blood_spray0..1   a wall spray: the same pieces thrown one way (+X), for shots that hit
                    a wall behind the victim (the projector's roll lines it up with the shot)
  blood_pool0       a pool under a body (round, thick, a soft rim)
  blood_remains0..1 what's left on the floor when the game takes a body away (chunks, bone)
  blood_meat        the cut face of a gib part (opaque, not a decal)
  alien_*           the same in the Seekers' purple
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


# blood colours, thin and thick (RGB 0..1, before the 2x-multiply mix), matched to the game's
# own hit particles: humans 136/0/0 (fx_person_Bullet_Blood), Seekers 128/0/255 (fx_person_bulletS)
RED = ((0.62, 0.08, 0.05), (0.37, 0.05, 0.05))
PURPLE = ((0.46, 0.07, 0.82), (0.26, 0.03, 0.52))


def render(size, balls, rng, edge_noise=0.55, name="x", palette=RED):
    """balls: (x, y, r, sx, sy) in 0..1 units; sx/sy stretch a ball into a streak"""
    thin, thick_ = palette
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
            r_, g_, b_ = [t + (k - t) * thick + 0.06 * (n - 0.5) for t, k in zip(thin, thick_)]
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


def coat(rng, amount):
    """blood on a body (ModBloodCoat projects it onto a character): splats spread over the
    whole square, more and bigger with amount (0, 1, 2), with runs downward (+y)"""
    balls = []
    for _ in range((4, 9, 16)[amount]):
        cx, cy = rng.uniform(0.12, 0.88), rng.uniform(0.1, 0.85)
        r0 = rng.uniform(0.02, 0.035) * (1, 1.3, 1.7)[amount]
        for _ in range(rng.randint(2, 5)):
            balls.append((cx + rng.gauss(0, 0.03), cy + rng.gauss(0, 0.03), r0 * rng.uniform(0.6, 1.1), 1, 1))
        for _ in range(rng.randint(6, 14)):
            ang = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0.03, 0.14)
            balls.append((cx + math.cos(ang) * dist, cy + math.sin(ang) * dist, 0.004 + 0.008 * rng.random() ** 2, 1, 1))
        if rng.random() < 0.6:
            teardrop(balls, cx, cy + rng.uniform(0.05, 0.16), -math.pi / 2, r0 * 0.5, rng.uniform(0.05, 0.14))
    return balls


def dirt(name, rng, kind, size=128):
    """grime and battle damage for ModDirt's decals, mixed for the projector's 2x multiply
    (50% grey leaves the surface as it is; darker = dirt; the d3d layer's parallax rule reads
    darker as deeper, so cracks and craters sink in). kind: grime, crack, rubble, crater"""
    noise, noise2 = fbm(size, rng), fbm(size, rng)
    px = bytearray()
    lines = []
    if kind == "crack":
        for _ in range(rng.randint(3, 5)):
            x, y, ang = 0.5 + rng.gauss(0, 0.05), 0.5 + rng.gauss(0, 0.05), rng.uniform(0, 2 * math.pi)
            for _ in range(rng.randint(8, 16)):
                nx, ny = x + math.cos(ang) * 0.035, y + math.sin(ang) * 0.035
                lines.append((x, y, nx, ny, rng.uniform(0.004, 0.011)))
                x, y, ang = nx, ny, ang + rng.gauss(0, 0.45)
    stones = [(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.02, 0.06)) for _ in range(22)] if kind == "rubble" else []
    for py in range(size):
        for qx in range(size):
            u, v = qx / (size - 1), py / (size - 1)
            d = math.hypot(u - 0.5, v - 0.5)
            fade = smoothstep(0.5, 0.3, d)                     # nothing at the square's edge
            dark, tint = 0.0, (1.0, 0.96, 0.9)
            n = noise[py][qx]
            if kind == "grime":
                dark = fade * smoothstep(0.35, 0.75, n) * (0.25 + 0.3 * noise2[py][qx])
                tint = (0.92, 0.86, 0.74)
            elif kind == "crack":
                near = min([abs((y1 - y0) * u - (x1 - x0) * v + x1 * y0 - y1 * x0) / max(math.hypot(x1 - x0, y1 - y0), 1e-5) / w
                            if min(x0, x1) - w <= u <= max(x0, x1) + w and min(y0, y1) - w <= v <= max(y0, y1) + w else 9.0
                            for x0, y0, x1, y1, w in lines] or [9.0])
                dark = fade * (smoothstep(1.0, 0.25, near) * 0.85 + 0.08 * smoothstep(0.4, 0.8, n))
            elif kind == "rubble":
                k = max([smoothstep(r, r * 0.55, math.hypot(u - sx, v - sy)) for sx, sy, r in stones] or [0])
                dark = fade * (0.18 * smoothstep(0.3, 0.7, n) + 0.3 * k * (0.6 + 0.8 * noise2[py][qx]))
                tint = (0.9, 0.88, 0.84)
            else:                                              # crater: a burnt pit, a raised rim's shadow, soot
                pit = smoothstep(0.2 + 0.06 * (n - 0.5), 0.06, d)
                soot = smoothstep(0.46, 0.15, d) * (0.3 + 0.4 * n)
                dark = min(1.0, 0.8 * pit + 0.35 * soot)
                tint = (0.9, 0.86, 0.82)
            g = 0.5 * (1 - dark)
            px += bytes([int(255 * min(max(g * t, 0), 1) + 0.5) for t in (tint[2], tint[1], tint[0])] + [int(255 * dark + 0.5)])
    path = os.path.join(HERE, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


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

def remains(name, rng, palette=RED, size=128):
    """what's left where a body was taken away (the game recycles its dead): a wide smeared
    pool, flesh chunks a shade darker and glossy, pale bone shards, drag smears. Flat, so
    it costs nothing once it's down (the Project Zomboid way)"""
    thin, thick_ = palette
    noise = fbm(size, rng)
    pool_b = [(0.5 + rng.gauss(0, 0.08), 0.5 + rng.gauss(0, 0.05), rng.uniform(0.06, 0.10), rng.uniform(1.0, 1.8), 1) for _ in range(7)]
    pool_b += [(0.5 + rng.gauss(0, 0.2), 0.5 + rng.gauss(0, 0.14), rng.uniform(0.01, 0.025), 1, 1) for _ in range(14)]
    # chunks: lumpy pieces, a few big, more small
    chunks = []
    for _ in range(rng.randint(9, 14)):
        cx, cy = 0.5 + rng.gauss(0, 0.13), 0.5 + rng.gauss(0, 0.09)
        r = 0.02 + 0.04 * rng.random() ** 1.5
        for _ in range(rng.randint(2, 4)):
            chunks.append((cx + rng.gauss(0, r * 0.6), cy + rng.gauss(0, r * 0.6), r * rng.uniform(0.6, 1.0)))
    # bone shards: thin bright slivers
    shards = []
    for _ in range(rng.randint(4, 7)):
        shards.append((0.5 + rng.gauss(0, 0.12), 0.5 + rng.gauss(0, 0.08), rng.uniform(0, math.pi), rng.uniform(0.02, 0.05), rng.uniform(0.005, 0.009)))
    px = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            u, v = (x + 0.5) / size, (y + 0.5) / size
            n = noise[y][x]
            f = 0.0
            for bx, by, r, sx, sy in pool_b:
                dx, dy = (u - bx) / sx, (v - by) / sy
                f += r * r / max(dx * dx + dy * dy, 1e-6)
            a = smoothstep(0.85, 1.15, f * (1.0 + 0.6 * (n - 0.5)))
            thick = smoothstep(1.0, 4.0, f) * (0.65 + 0.7 * (n - 0.5))
            col = [t + (k - t) * thick + 0.06 * (n - 0.5) for t, k in zip(thin, thick_)]
            # flesh chunks: darker, a highlight on the upper-left of each (wet)
            ch = 0.0
            hl = 0.0
            for cx, cy, r in chunks:
                d = math.hypot(u - cx, v - cy) / r
                if d < 1.3:
                    ch = max(ch, 1 - smoothstep(0.75, 1.05, d + 0.25 * (n - 0.5)))
                    hl = max(hl, math.exp(-((u - cx + r * 0.35) ** 2 + (v - cy - r * 0.35) ** 2) / (r * 0.25) ** 2))
            if ch > 0:
                # meat: the thin colour, lighter, mottled; a dark rim where it meets the pool
                rim = ch * (1 - ch) * 4
                flesh = [min(1.0, t * 1.15 + 0.08) * (0.8 + 0.4 * n) for t in thin]
                col = [c * (1 - ch) + fl * ch for c, fl in zip(col, flesh)]
                col = [c * (1 - 0.6 * rim) + 0.3 * hl * ch for c in col]
                a = max(a, ch)
            # bone shards
            for sx_, sy_, ang, ln, wd in shards:
                du, dv = u - sx_, v - sy_
                along = du * math.cos(ang) + dv * math.sin(ang)
                across = -du * math.sin(ang) + dv * math.cos(ang)
                d = max(abs(along) / ln, abs(across) / (wd * (1 - 0.6 * abs(along) / ln)))
                if d < 1.0:
                    b = 1 - smoothstep(0.7, 1.0, d)
                    col = [c * (1 - b) + bone * b for c, bone in zip(col, (0.95, 0.9, 0.78))]
                    a = max(a, b)
            border = min(u, v, 1 - u, 1 - v)
            a *= smoothstep(0.0, 0.06, border)
            a = min(max(a, 0), 1)
            # 2x modulate, as in render(); bone may brighten the floor a little (up to 0.68)
            r_, g_, b_ = col
            px_c = []
            for c in (b_, g_, r_):
                c = min(max(c, 0), 1)
                m = 0.5 * (1 - a * (1 - c)) if c <= 0.5 else 0.5 + a * (c - 0.5) * 0.36
                px_c.append(m)
            px += bytes([int(255 * q + 0.5) for q in px_c] + [int(255 * a + 0.5)])
    path = os.path.join(HERE, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


def meat(name, rng, palette=RED, size=64):
    """the cut face of a gib part (an opaque texture, not a decal): raw tissue in the
    blood colour, mottled, paler fat and gristle streaks, dark wet spots"""
    thin, thick_ = palette
    noise = fbm(size, rng)
    streaks = fbm(size, rng)
    px = bytearray()
    for y in range(size - 1, -1, -1):
        for x in range(size):
            n, st = noise[y][x], streaks[y][x]
            base = [t * (0.75 + 0.5 * n) for t in thin]
            fat = smoothstep(0.62, 0.72, st)
            col = [c * (1 - fat) + f * fat for c, f in zip(base, (0.85, 0.72, 0.62))]
            wet = smoothstep(0.65, 0.8, n)
            col = [c * (1 - 0.5 * wet) for c in col]
            r_, g_, b_ = (min(max(c, 0), 1) for c in col)
            px += bytes([int(255 * c + 0.5) for c in (b_, g_, r_)] + [255])
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
    # the same shapes in each colour: blood_* red, alien_* purple
    for prefix, pal in (("blood", RED), ("alien", PURPLE)):
        for i in range(4):
            rng = random.Random(1000 + i)
            render(128, splat(rng), rng, edge_noise=0.8, name="%s_splat%d" % (prefix, i), palette=pal)
        for i in range(2):
            rng = random.Random(2000 + i)
            render(128, splat(rng, directional=True), rng, edge_noise=0.8, name="%s_spray%d" % (prefix, i), palette=pal)
        rng = random.Random(3000)
        render(128, pool(rng), rng, edge_noise=0.35, name="%s_pool0" % prefix, palette=pal)
        for i in range(2):
            remains("%s_remains%d" % (prefix, i), random.Random(6000 + i), palette=pal)
        meat("%s_meat" % prefix, random.Random(7000), palette=pal)
        for i in range(3):
            rng = random.Random(8000 + i)
            render(128, coat(rng, i), rng, edge_noise=0.7, name="%s_coat%d" % (prefix, i), palette=pal)
    for i, kind in enumerate(("grime", "grime", "crack", "crack", "rubble", "crater")):
        dirt("dirt_%s%d" % (kind, i % 2), random.Random(9000 + i), kind)
