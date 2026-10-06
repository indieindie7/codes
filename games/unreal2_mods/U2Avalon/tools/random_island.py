r"""A random island heightmap in TutA's terrain frame (128x128 G16 BMP, same header as the exported island1.bmp):

    py tools/random_island.py <seed> <template island1.bmp> <out.bmp> [relief=3500] [radius=48]

The island is a noisy blob round a random centre that always covers the command tower (cell 92,57) and the
plant's coastal plain (cells 96..106, 33..46, kept low: the binder town stands there); the sea floor lies at
Z -5500 with the sea surface at -4967. Heights are ridged fBm (value noise, numpy only) scaled by the
distance to the shore, and the cells round the tower blend into the template's heights so the BSP tower
base is never buried or left hanging. Erosion (tools/python/terrain) and cut-and-fill run afterwards.
"""
import math, struct, sys
import numpy as np

seed = int(sys.argv[1])
src, dst = sys.argv[2], sys.argv[3]
o = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)
RELIEF = float(o.get("relief", 3500))      # Z units of the highest peak over the sea
RADIUS = float(o.get("radius", 48))        # cells
LOC_Z, SCALE_Z = -131.845703, 128.0
SEA_Z, FLOOR_Z = -4967.0, -5500.0
TOWER = (92, 57)
PLAIN = (96, 106, 33, 46)                  # i0, i1, j0, j1 of the plant's shore (keep near sea level)

rng = np.random.default_rng(seed)
N = 128
raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
rows_up = h < 0
T = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if not rows_up:
    T = T[::-1]
TZ = LOC_Z + (T - 32768) * SCALE_Z / 256


def value_noise(n, cells):
    """bilinear value noise: a cells x cells random grid upsampled to n x n"""
    g = rng.random((cells + 1, cells + 1))
    xs = np.linspace(0, cells, n, endpoint=False)
    i0 = np.floor(xs).astype(int)
    t = xs - i0
    i1 = np.minimum(i0 + 1, cells)
    a = g[np.ix_(i0, i0)] * np.outer(1 - t, 1 - t) + g[np.ix_(i0, i1)] * np.outer(1 - t, t) \
        + g[np.ix_(i1, i0)] * np.outer(t, 1 - t) + g[np.ix_(i1, i1)] * np.outer(t, t)
    return a


def fbm(n, octaves=6, base=4, gain=0.5, ridged=False):
    out = np.zeros((n, n))
    amp, total = 1.0, 0.0
    for k in range(octaves):
        v = value_noise(n, base * 2 ** k)
        if ridged:
            v = 1 - abs(v * 2 - 1)
        out += amp * v
        total += amp
        amp *= gain
    return out / total


J, I = np.mgrid[0:N, 0:N]
# the blob: centre so the tower and the plain are inside, boundary perturbed by low-frequency noise
cx = rng.uniform(58, 76)
cy = rng.uniform(52, 70)
edge = fbm(N, octaves=4, base=2)
edge = (edge - edge.mean()) / (edge.std() + 1e-9)      # unit variance, so the wobble really wobbles
rot = rng.uniform(0, math.pi)
stretch = rng.uniform(0.65, 1.0)                        # an elongated island, turned at random
u = (I - cx) * math.cos(rot) + (J - cy) * math.sin(rot)
v = (-(I - cx) * math.sin(rot) + (J - cy) * math.cos(rot)) / stretch
r = np.hypot(u, v)
rad = RADIUS * np.clip(1 + 0.45 * edge, 0.45, 1.5)     # the shore wobbles: bays and headlands
inside = np.clip((rad - r) / 6.0, 0, 1)                # 0 at sea, 1 six cells inland


def seg_dist(ax, ay, bx, by):
    """distance of every cell to the segment a-b"""
    vx, vy = bx - ax, by - ay
    t = np.clip(((I - ax) * vx + (J - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
    return np.hypot(I - (ax + t * vx), J - (ay + t * vy))


# a land corridor from the island's centre over the tower to the plant, so the town never sits on an islet
px, py = (PLAIN[0] + PLAIN[1]) / 2, (PLAIN[2] + PLAIN[3]) / 2
corridor = np.minimum(seg_dist(cx, cy, TOWER[0], TOWER[1]), seg_dist(TOWER[0], TOWER[1], px, py))
inside = np.maximum(inside, np.clip((9 - corridor) / 5.0, 0, 1))
inside = inside * inside * (3 - 2 * inside)
# relief: ridged fBm, rising inland; the plain stays low
relief = fbm(N, octaves=6, base=3, ridged=True)
relief = (relief - relief.min()) / (relief.max() - relief.min() + 1e-9)
inland = np.clip((rad - r) / (RADIUS * 0.9), 0, 1)
hills = relief ** 1.6 * inland ** 0.8
hills = hills / (hills.max() + 1e-9)                   # the highest peak reaches RELIEF
i0, i1, j0, j1 = PLAIN
plain = np.exp(-(((I - (i0 + i1) / 2) / 9.0) ** 2 + ((J - (j0 + j1) / 2) / 9.0) ** 2))
hills = hills * (1 - 0.9 * plain)
Z = FLOOR_Z + 40 * (fbm(N, octaves=3, base=8) - 0.5)                                  # sea floor
land_z = SEA_Z + 120 + hills * RELIEF                                                 # beach at +120
Z = Z * (1 - inside) + land_z * inside
Z = np.where(inside > 0.5, Z, np.minimum(Z, SEA_Z - 60))                               # no half-drowned plateaus
# the plain: land at a gentle height, never below the beach
plain_z = SEA_Z + 180 + 260 * plain
Z = np.where(plain > 0.35, np.maximum(Z, plain_z * plain + Z * (1 - plain)), Z)
# the tower blends into the template heights (radius 9 cells) so the BSP base fits
dt = np.hypot(I - TOWER[0], J - TOWER[1])
wt = np.clip((9 - dt) / 5.0, 0, 1)
Z = Z * (1 - wt) + TZ * wt
# the original's map edge (water) is kept so nothing pokes out of TutA's sea room
E = np.clip((np.minimum.reduce([I, J, N - 1 - I, N - 1 - J]) - 3) / 6.0, 0, 1)
Z = Z * E + TZ * (1 - E)
Hn = np.clip(np.round(32768 + (Z - LOC_Z) * 256 / SCALE_Z), 0, 65535).astype("<u2")
pix = (Hn if rows_up else Hn[::-1]).tobytes()
open(dst, "wb").write(raw[:off] + pix + raw[off + len(pix):])
land = (Z > SEA_Z).mean()
print(f"seed {seed}: centre ({cx:.0f},{cy:.0f}) land {land:.0%} peak Z {Z.max():.0f} tower Z {Z[TOWER[1], TOWER[0]]:.0f} "
      f"plain Z {Z[(j0 + j1) // 2, (i0 + i1) // 2]:.0f} -> {dst}")
