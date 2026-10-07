r"""Desire lines: the citizens' routines walked over the island, so the ground shows where people go.

    py tools/walks.py <heightmap.bmp> <layout.json> [png=walks.png] [passes=3]

Every routine step (place -> next place, wrapping to the next morning) is one trip, weighted by the
citizen's `headcount:` (default 1). Trips are routed on a half-cell grid (5.12 m) by Dijkstra:
  * cost = metres x slope term (1 + (deg/10)^2, cliffs over 35 deg nearly closed) x 0.6 on a road
    x a wear discount: the active-walker model (Helbing 1997) - each pass makes walked ground cheaper,
    so the next pass's trips fall into the same tracks and merge into a few worn trunks;
  * walled buildings block; pads, quays and jetties do not;
  * a trip leaves and arrives through the building's doors (binder `doors:`); a wall side may be used
    at a penalty of DOOR_PENALTY metres, and when it is, the building "wants a door" there - the
    neighbour rule for build_parts (a door toward the arriving path);
  * a place on the water (rigs, the barge, islets) is reached from the nearest dock or boat landing,
    the last leg by boat.
Writes into the layout JSON: "walks" (each trip: who, from, to, weight, path, metres, minutes, exits,
boat) and "door_wants"; prints the greybox checks: a trip longer than the time the routine leaves for it,
a commute over 15 minutes, a place nobody can reach on foot.
"""
import json, math, os, struct, sys

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

src, layout_path = sys.argv[1:3]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
PASSES = int(o.get("passes", 3))
PNG = o.get("png")
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, M, N = 512.0, 50.0, 128
F = 2                                   # fine cells per terrain cell
NF = N * F
FC = CELL / F                           # 256 u = 5.12 m
SEA_Z = -4967.0
WALK = 1.3                              # m/s, a worker on rough ground
DOOR_PENALTY = 40.0                     # metres: a wall side is used only when the door detour costs more
WEAR_T = 24.0                           # trip weight at which ground is fully worn (half price)
NOT_WALLED = ("pad", "dock", "jetty", "wellhead", "rig", "islet", "barge", "wreck", "memorial", "mast")
SHORE = ("dock", "boat_landing", "jetty")

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
Hm = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    Hm = Hm[::-1]
Zc = LOC[2] + (Hm - 32768) * 0.5
JJ, II = np.mgrid[0:NF, 0:NF]
Z = map_coordinates(Zc, [JJ / F, II / F], order=1, mode="nearest")     # fine cell k <-> coarse coordinate k/F
WATER = Z <= SEA_Z + 30


def to_fine(x, y):
    return (x - LOC[0]) / FC + NF / 2, (y - LOC[1]) / FC + NF / 2


def to_world(i, j):
    return LOC[0] + (i - NF / 2) * FC, LOC[1] + (j - NF / 2) * FC


L = json.load(open(layout_path))
B = L["buildings"]
citizens, sheets = binder.load()

# ---- footprints and exits -------------------------------------------------------------------------
BLOCK = np.zeros((NF, NF), bool)
EXITS = {}          # bid -> [(side, fine index, door type or None)]
SIDE_N = {"front": (1, 0), "back": (-1, 0), "left": (0, -1), "right": (0, 1)}   # mesh sides in Unreal local axes


def instances(bid):
    b, P = sheets[bid], B[bid]
    W, D = b["size"][0] * M, b["size"][1] * M
    gap = max(W, D) * 1.5
    spec = b.get("count", "1").split()
    pts = [(0, 0)]
    if spec[0].lower() == "2x2":
        pts = [(-gap / 2, -gap / 2), (gap / 2, -gap / 2), (-gap / 2, gap / 2), (gap / 2, gap / 2)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    a = math.radians(P["yaw"])
    return [(P["x"] + da * math.cos(a) - dc * math.sin(a), P["y"] + da * math.sin(a) + dc * math.cos(a)) for da, dc in pts]


for bid, P in B.items():
    b = sheets.get(bid)
    if b is None or "size" not in b:
        continue
    W, D = b["size"][0] * M, b["size"][1] * M        # local X (front axis) spans D, local Y spans W
    a = math.radians(P["yaw"])
    ca, sa = math.cos(a), math.sin(a)
    walled = b["kind"] not in NOT_WALLED
    for cx, cy in instances(bid):
        if walled:
            r = math.hypot(W, D) / 2 / FC + 1
            fi, fj = to_fine(cx, cy)
            i0, i1 = max(0, int(fi - r)), min(NF, int(fi + r) + 2)
            j0, j1 = max(0, int(fj - r)), min(NF, int(fj + r) + 2)
            for j in range(j0, j1):
                for i in range(i0, i1):
                    wx, wy = to_world(i, j)
                    lx, ly = (wx - cx) * ca + (wy - cy) * sa, -(wx - cx) * sa + (wy - cy) * ca
                    if abs(lx) <= D / 2 and abs(ly) <= W / 2:
                        BLOCK[j, i] = True
    # exits on the main instance: each side's middle, 5 m out (doors from the sheet; no doors = every side open)
    doors = b.get("doors") or {}
    ex = []
    for side, (nx, ny) in SIDE_N.items():
        half = D / 2 if nx else W / 2
        lx, ly = nx * (half + 250), ny * (half + 250)
        wx, wy = P["x"] + lx * ca - ly * sa, P["y"] + lx * sa + ly * ca
        fi, fj = to_fine(wx, wy)
        i, j = int(round(fi)), int(round(fj))
        if 0 <= i < NF and 0 <= j < NF:
            ex.append((side, j * NF + i, doors.get(side) if doors else "open"))
    EXITS[bid] = ex

FREE = ~BLOCK & ~WATER

# roads (from the layout) at fine resolution
ROAD = np.zeros((NF, NF), bool)
for r in L.get("roads", []):
    for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
        n = int(math.hypot(bx - ax, by - ay) / (FC / 2)) + 1
        for t in np.linspace(0, 1, n):
            fi, fj = to_fine(ax + (bx - ax) * t, ay + (by - ay) * t)
            i, j = int(round(fi)), int(round(fj))
            if 0 <= i < NF and 0 <= j < NF:
                ROAD[j, i] = True

# ---- the grid graph --------------------------------------------------------------------------------
NB = [(1, 0), (0, 1), (1, 1), (1, -1)]          # (di, dj); the reverse edges are added too
idx = np.arange(NF * NF).reshape(NF, NF)
S = NF * NF                                      # the super-source node


def sl(d):
    """slices (from, to) along one axis for a shift d"""
    return (slice(0, NF - d), slice(d, NF)) if d >= 0 else (slice(-d, NF), slice(0, NF + d))


def graph(wear, extra=()):
    """8-connected grid as CSR (both directions); extra = (u, v, w) one-way edges"""
    rows, cols, vals = [], [], []
    base = np.where(ROAD, 0.6, 1.0) * (1 - 0.5 * np.clip(wear / WEAR_T, 0, 1))
    for di, dj in NB:
        (ja, jb), (ia, ib) = sl(dj), sl(di)
        a, b = (ja, ia), (jb, ib)
        ok = FREE[a] & FREE[b]
        d = FC / M * math.hypot(di, dj)
        dz = np.abs(Z[a] - Z[b]) / M
        deg = np.degrees(np.arctan(dz / d))
        c = d * (1 + (deg / 10.0) ** 2) * np.where(deg > 35, 50, 1) * (base[a] + base[b]) / 2
        u, v = idx[a][ok], idx[b][ok]
        rows += [u, v]
        cols += [v, u]
        vals += [c[ok], c[ok]]
    for u, v, wgt in extra:
        rows.append(np.array([u]))
        cols.append(np.array([v]))
        vals.append(np.array([max(wgt, 1e-3)]))
    return csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(S + 1, S + 1))


def nearest_free(k):
    j, i = divmod(k, NF)
    if FREE[j, i]:
        return k
    for r in range(1, 8):
        j0, i0 = max(0, j - r), max(0, i - r)
        js, is_ = np.nonzero(FREE[j0:j + r + 1, i0:i + r + 1])
        if len(js):
            q = np.argmin((js + j0 - j) ** 2 + (is_ + i0 - i) ** 2)
            return int((js[q] + j0) * NF + is_[q] + i0)
    return None


def exits(bid):
    out = []
    for side, k, door in EXITS.get(bid, []):
        k2 = nearest_free(k)
        if k2 is not None:
            out.append((side, k2, 0.0 if door else DOOR_PENALTY))
    return out


# ---- trips -----------------------------------------------------------------------------------------
trips = []
for cid, c in citizens.items():
    r = c.get("routine") or []
    n = float(c.get("headcount", 1) or 1)
    for k in range(len(r)):
        t0, a = r[k]
        t1, b = r[(k + 1) % len(r)]
        if a == b or a not in B or b not in B:
            continue
        gap = (t1 - t0) % 1440 or 1440
        trips.append(dict(who=cid, frm=a, to=b, n=n, gap=gap))


def on_water(bid):
    return bid in sheets and (sheets[bid]["kind"] in ("rig", "islet", "barge", "wreck") or not exits(bid))


def landing_for(bid):
    """the shore place a boat leaves from for a place on the water"""
    P = B[bid]
    best = None
    for s in B:
        if s in sheets and (sheets[s]["kind"] in SHORE or s in SHORE) and not on_water(s):
            d = math.hypot(B[s]["x"] - P["x"], B[s]["y"] - P["y"])
            if best is None or d < best[0]:
                best = (d, s)
    return best[1] if best else None


wear = np.zeros((NF, NF))
results = []
for p in range(PASSES):
    new = np.zeros((NF, NF))
    results = []
    for t in trips:
        a, b, boat = t["frm"], t["to"], None
        def is_shore(x):
            return x in sheets and (sheets[x]["kind"] in SHORE or x in SHORE)
        if on_water(a):                     # the boat leaves from the other end if that is a quay already
            boat, a = a, (b if is_shore(b) else landing_for(a))
        if on_water(b):
            boat, b = b, (a if is_shore(a) else landing_for(b))
        res = dict(who=t["who"], frm=t["frm"], to=t["to"], n=t["n"], gap=t["gap"], boat=boat, path=[], m=0.0, min=0.0, exits=None)
        if a is None or b is None or a == b:
            results.append(res)
            continue
        ea, eb = exits(a), exits(b)
        G = graph(wear, [(S, k, pen) for _, k, pen in ea])
        dist, pred = dijkstra(G, directed=True, indices=S, return_predecessors=True)
        best = min(((dist[k] + pen, side, k) for side, k, pen in eb), default=None)
        if best is None or not np.isfinite(best[0]):
            res.update(m=float("inf"), min=float("inf"))
            results.append(res)
            continue
        path, k = [], best[2]
        while k != S and k >= 0:
            path.append(k)
            k = pred[k]
        path.reverse()
        side_a = next((side for side, kk, _ in ea if kk == path[0]), "?")
        js, is_ = np.divmod(np.array(path), NF)
        np.add.at(new, (js, is_), t["n"])
        metres = float(np.sum(np.hypot(np.diff(is_), np.diff(js))) * FC / M) if len(path) > 1 else 0.0
        pts = [to_world(i, j) for j, i in zip(js[::3], is_[::3])] + [to_world(is_[-1], js[-1])]
        res.update(path=[[round(x, 1), round(y, 1)] for x, y in pts], m=round(metres, 1),
                   min=round(metres / WALK / 60, 1), exits=[side_a, best[1]], frm_at=a, to_at=b)
        results.append(res)
    wear = new
    print("pass %d: %d trips, worn cells %d" % (p + 1, len(results), int((wear > 0).sum())), flush=True)

# ---- door wants, checks ----------------------------------------------------------------------------
wants = {}
for r in results:
    if not r.get("exits"):
        continue
    for bid, side in ((r["frm_at"], r["exits"][0]), (r["to_at"], r["exits"][1])):
        doors = sheets.get(bid, {}).get("doors") or {}
        if doors and side not in doors:
            wants.setdefault(bid, {}).setdefault(side, 0)
            wants[bid][side] += r["n"]
checks = []
for r in results:
    if not np.isfinite(r["m"]):
        checks.append("%s: %s -> %s cannot be walked" % (r["who"], r["frm"], r["to"]))
    elif r["min"] > r["gap"]:
        checks.append("%s: %s -> %s is %.0f min on foot, the routine leaves %d" % (r["who"], r["frm"], r["to"], r["min"], r["gap"]))
    elif r["min"] > 15:
        checks.append("%s: %s -> %s is a %.0f min walk (over 15 for a daily trip)" % (r["who"], r["frm"], r["to"], r["min"]))
for bid, sides in sorted(wants.items()):
    for side, n in sorted(sides.items(), key=lambda kv: -kv[1]):
        checks.append("%s wants a door on its %s side (%g trips a day walk round to the doors)" % (bid, side, n))


def clean(v):
    return None if isinstance(v, float) and not np.isfinite(v) else v


L["walks"] = [{k: clean(v) for k, v in r.items() if k != "gap"} for r in results]
L["door_wants"] = wants
L["walk_checks"] = checks
json.dump(L, open(layout_path, "w"), indent=1)
walked = [r for r in results if r["path"]]
tot = sum(r["m"] * r["n"] for r in walked)
longest = max(walked, key=lambda r: r["m"], default=None)
print("walks: %d trips, %.1f km walked a day, longest %s; %d checks" % (
    len(walked), tot / 1000, "%s %s->%s %.0f m" % (longest["who"], longest["frm"], longest["to"], longest["m"]) if longest else "-", len(checks)))
for c in checks:
    print("  " + c)

if PNG:
    from PIL import Image
    gy, gx = np.gradient(Z, FC)
    lit = np.clip(0.6 + 1.5 * (-gx - gy), 0.2, 1.0)
    rgb = np.zeros((NF, NF, 3))
    for ch, (lo, hi, sea) in enumerate(((60, 170, 30), (70, 165, 60), (50, 120, 120))):
        rgb[..., ch] = np.where(WATER, sea, lo + (hi - lo) * lit)
    rgb[ROAD] = (150, 140, 125)
    rgb[BLOCK] = (35, 35, 40)
    wv = np.clip(wear / WEAR_T, 0, 1)
    m = wear > 0
    rgb[m] = np.stack([np.full(m.sum(), 240.0), 210 - 170 * wv[m], 70 - 60 * wv[m]], -1)
    Image.fromarray(rgb[::-1].astype("u1")).resize((768, 768), Image.NEAREST).save(PNG)
    print("->", PNG)
