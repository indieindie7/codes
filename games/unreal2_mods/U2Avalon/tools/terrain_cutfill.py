"""Cut-and-fill TutA's terrain heightmap under the binder's buildings (the real-world way to build on a
slope: a level plinth cut into the bank, the spoil filling the low side, a benched blend back to the hill).

    py tools/terrain_cutfill.py <island1.bmp exported by UnrealEd> <out.bmp> [shift=-5300] [margin=250] [blend=700]

The BMP is the 16-bit (G16) heightmap UnrealEd exports with OBJ EXPORT TYPE=Texture; the same bytes go
back with TEXTURE IMPORT. TutA's TerrainInfo0 (read in game with 'hub list TerrainInfo'):
    location (-14487.5, 4835.8, -131.8), scale (512, 512, 128), heightmap 128x128
UE2 maps pixel (i, j) -> world (Location.X + (i - 64) * 512, Location.Y + (j - 64) * 512) and a height
value h -> Z = Location.Z + (h - 32768) * ScaleZ / 256. Each land building gets a flat pad of its footprint
plus `margin`, at the terrain height sampled at its centre, blended back over `blend` units; roads get
nothing (they are painted, not cut).
"""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

src, dst = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)   # shift= margin= blend= max_terrace= layout=
SHIFT = float(o.get("shift", -5300))
MARGIN = float(o.get("margin", 600))      # a heightmap cell is 512 units: the pad must reach past the next cell centre
BLEND = float(o.get("blend", 400))        # shorter blend = real terraces (walls at the rims); 700 made soft mounds
MAX_TERRACE = float(o.get("max_terrace", 3200))   # merged terraces never grow past this radius
LOOK, M = 300.0, 50.0
LOC = (-14487.546875, 4835.837891, -131.845703)
SCALE = (512.0, 512.0, 128.0)
SEA_H = 32768 + (-4967 - LOC[2]) * 256 / SCALE[2]      # the sea surface as a height value


def from_frame(along, across):
    a = math.radians(LOOK)
    return (along * math.cos(a) - across * math.sin(a), along * math.sin(a) + across * math.cos(a))


LAYOUT = None
if o.get("layout"):
    import json as _json
    LAYOUT = _json.load(open(o["layout"]))["buildings"]


def instances(b):
    along, across, deg = b["at"]
    if LAYOUT and b["id"] in LAYOUT:
        # layout.py placed it: world position + yaw, instance offsets turned with the yaw
        L = LAYOUT[b["id"]]
        along, across, deg = None, None, L["yaw"]
    w, d = b["size"][0] * M, b["size"][1] * M
    gap = max(w, d) * 1.5
    spec = b.get("count", "1").split()
    pts = [(0, 0)]
    if "x" in spec[0].lower():                  # "3x4": a block (2x2 as before)
        na_, nc_ = (int(v) for v in spec[0].lower().split("x"))
        pts = [((ka_ - (na_ - 1) / 2) * gap, (kc_ - (nc_ - 1) / 2) * gap) for kc_ in range(nc_) for ka_ in range(na_)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    if along is None:
        a = math.radians(deg)
        return [(L["x"] + da * math.cos(a) - dc * math.sin(a), L["y"] + da * math.sin(a) + dc * math.cos(a)) for da, dc in pts]
    return [from_frame(along + SHIFT + da, across + dc) for da, dc in pts]


raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
bpp = struct.unpack_from("<H", raw, 28)[0]
assert bpp == 16 and w == 128, (bpp, w, h)
rows_up = h < 0            # positive height = bottom-up rows in the file
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if not rows_up:
    H = H[::-1]
ORIG = H.copy()

ix = (np.arange(w) - w / 2) * SCALE[0] + LOC[0]      # world X of each column
jy = (np.arange(abs(h)) - abs(h) / 2) * SCALE[1] + LOC[1]
X, Y = np.meshgrid(ix, jy)


def sample(x, y):
    """bilinear height at a world point"""
    fi = (x - LOC[0]) / SCALE[0] + w / 2
    fj = (y - LOC[1]) / SCALE[1] + abs(h) / 2
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < w - 1 and 0 <= j0 < abs(h) - 1):
        return None
    ti, tj = fi - i0, fj - j0
    return (ORIG[j0, i0] * (1 - ti) * (1 - tj) + ORIG[j0, i0 + 1] * ti * (1 - tj)
            + ORIG[j0 + 1, i0] * (1 - ti) * tj + ORIG[j0 + 1, i0 + 1] * ti * tj)


citizens, buildings = binder.load()
pads = []
FOOT = {}      # pad id -> the footprint discs (x, y, r) of its buildings
for bid, b in buildings.items():
    if "at" not in b or b["kind"] in ("rig", "barge", "wreck", "jetty") or bid == "tower":
        continue
    r = max(b["size"][0], b["size"][1]) * M * 0.6 + MARGIN
    pts = instances(b)
    hs = [sample(x, y) for x, y in pts]
    hs = [v for v in hs if v is not None]
    if not hs:
        continue
    # one level per building, not per instance: a row of silos stands on one terrace
    hc = max(sum(hs) / len(hs), SEA_H + 50 * 256 / SCALE[2])     # never below 50 units over the sea
    FOOT[bid] = [(x, y, r) for x, y in pts]
    if len(pts) > 1:
        # the group's pad: a disc round the group's centre big enough for the row
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        rg = max(math.hypot(x - cx, y - cy) for x, y in pts) + r
        pads.append((bid, cx, cy, rg, hc))
    else:
        pads.append((bid, pts[0][0], pts[0][1], r, hc))
# overlapping pads become ONE terrace (otherwise the later pad cuts into the earlier one and a silo row
# ends up on three levels): merge discs that overlap into a disc covering both, at the area-weighted height
merged = True
while merged:
    merged = False
    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            bi, xi, yi, ri, hi = pads[i]
            bj, xj, yj, rj, hj = pads[j]
            if math.hypot(xi - xj, yi - yj) < ri + rj - 200:
                wi, wj = ri * ri, rj * rj
                cx, cy = (xi * wi + xj * wj) / (wi + wj), (yi * wi + yj * wj) / (wi + wj)
                rr = max(math.hypot(xi - cx, yi - cy) + ri, math.hypot(xj - cx, yj - cy) + rj)
                if rr > MAX_TERRACE:
                    continue                      # too big a terrace: leave them separate (nearest pad wins per cell)
                pads[i] = (bi + "+" + bj, cx, cy, rr, (hi * wi + hj * wj) / (wi + wj))
                FOOT[bi + "+" + bj] = FOOT.pop(bi, []) + FOOT.pop(bj, [])
                del pads[j]
                merged = True
                break
        if merged:
            break
# apply: every cell belongs to its NEAREST pad (distance over the pad's radius), flat inside it, blended
# (smoothstep) over BLEND outside it; neighbouring terraces then meet at a seam instead of cutting each other
cut = fill = 0.0
if pads:
    S = np.full(H.shape, np.inf)
    T = np.zeros(H.shape)
    for bid, x, y, r, hc in pads:
        s = np.hypot(X - x, Y - y) - r            # distance outside the pad's edge (negative inside)
        better = s < S
        S[better] = s[better]
        T[better] = hc
    # every building's own footprint is forced onto its terrace, whatever neighbour terrace is nearer
    for bid, x, y, r, hc in pads:
        for fx, fy, fr in FOOT.get(bid, []):
            inside = np.hypot(X - fx, Y - fy) <= fr
            S[inside] = -1e9
            T[inside] = hc
    t = np.clip(S / BLEND, 0, 1)
    wgt = 1 - (t * t * (3 - 2 * t))               # 1 inside the pad, 0 beyond the blend
    new = H * (1 - wgt) + T * wgt
    dz = (new - H) * SCALE[2] / 256
    cut = float(-dz[dz < 0].sum()) * SCALE[0] * SCALE[1]
    fill = float(dz[dz > 0].sum()) * SCALE[0] * SCALE[1]
    H = new
# roads: graded into the ground. Each road polyline is sampled every half cell; the ground along it is
# replaced by a smoothed profile (moving average over ~7 samples, grade capped at MAX_GRADE) and the cells
# within ROAD_W/2 of the line take that height, blended over one cell beyond, so a road reads as a cut
# bench on a slope and a causeway over a dip instead of a line painted on bumps.
ROAD_W = float(o.get("road_w", 1.3))        # cells
MAX_GRADE = float(o.get("max_grade", 0.12))  # rise/run
if LAYOUT:
    import json as _j
    _L = _j.load(open(o["layout"]))
    road_cut = 0.0
    for r in _L.get("roads", []):
        pts = []
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) / (SCALE[0] * 0.5)))
            for k in range(n):
                t = k / n
                pts.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        pts.append(tuple(r[-1]))
        if len(pts) < 3:
            continue
        hs = []
        for x, y in pts:
            fi, fj = (x - LOC[0]) / SCALE[0] + w / 2, (y - LOC[1]) / SCALE[1] + abs(h) / 2
            i0, j0 = min(w - 2, max(0, int(fi))), min(abs(h) - 2, max(0, int(fj)))
            hs.append(H[j0, i0])
        hs = np.array(hs, float)
        k = 7
        sm = np.convolve(np.pad(hs, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        step_max = MAX_GRADE * SCALE[0] * 0.5 * 256 / SCALE[2]
        for a in range(1, len(sm)):
            sm[a] = min(max(sm[a], sm[a - 1] - step_max), sm[a - 1] + step_max)
        for a in range(len(sm) - 2, -1, -1):
            sm[a] = min(max(sm[a], sm[a + 1] - step_max), sm[a + 1] + step_max)
        D = np.full(H.shape, np.inf)
        T = np.zeros(H.shape)
        for (x, y), hv in zip(pts, sm):
            d = np.hypot(X - x, Y - y) / SCALE[0]
            better = d < D
            D[better] = d[better]
            T[better] = hv
        wgt = np.clip(1 - (D - ROAD_W / 2) / 1.0, 0, 1)
        wgt = wgt * wgt * (3 - 2 * wgt)
        newH = H * (1 - wgt) + T * wgt
        road_cut += float(np.abs(newH - H).sum()) * SCALE[2] / 256 * SCALE[0] * SCALE[1]
        H = newH
    print(f"roads graded: {len(_L.get('roads', []))} legs, earth moved {road_cut / 1e9:.2f} (1e9 units^3)")
H = np.clip(np.round(H), 0, 65535).astype("<u2")
pix = (H if rows_up else H[::-1]).tobytes()
open(dst, "wb").write(raw[:off] + pix + raw[off + len(pix):])
changed = int((H.astype(float) != ORIG).sum())
print(f"{len(pads)} pads, {changed} of {w * abs(h)} heightmap cells changed, cut {cut / 1e9:.2f} fill {fill / 1e9:.2f} (1e9 units^3) -> {dst}")
for bid, x, y, r, hc in pads[:40]:
    print(f"  {bid:16s} at ({x:7.0f},{y:7.0f}) r {r:5.0f} pad Z {LOC[2] + (hc - 32768) * SCALE[2] / 256:7.0f}")
