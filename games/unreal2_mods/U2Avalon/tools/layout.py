r"""Place the binder's town on a terrain: anchors stay where their sheet says, everything else is seeded by
interest maps (Emilien & Galin 2012, "Procedural Generation of Villages on Arbitrary Terrains"), roads
grow as buildings arrive, then the floating buildings drift toward their Voronoi centroids.

    py tools/layout.py <heightmap.bmp> <out.json> [seed=1] [shift=-5300] [png=out.png] [relax=3]

Output JSON: {"buildings": {id: {"x", "y", "yaw", "cells": [[x, y], ...]}}, "roads": [[[x, y], ...]]} in
TutA world units (yaw in degrees, world). terrain_cutfill.py and export_mutator.py take layout=<json>
and use these positions instead of the sheets' `at:`. The heightmap is TutA's 128x128 G16 frame
(see terrain_cutfill.py for the mapping); a cell is 512 units = 10.24 m.

Interest I = max(0, sum w_i f_i) with f_i in [-1, 1]; any f_i = -1 forbids the spot. Functions: slope
bell, water distance (close / far / in-water), sociability (attraction-repulsion to named neighbours),
accessibility (distance to the growing road network), domination (height over the surroundings),
avoidance (minimum distance to named buildings). Weights live in KIND below, per sheet kind with id
overrides; the sheets' own `site:` line can override the kind defaults later.
"""
import heapq, json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa
import systems  # noqa   (provides/needs: the systemic relations that drive placement)

src, dst = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
SEED = int(o.get("seed", 1))
SHIFT = float(o.get("shift", -5300))
PNG = o.get("png")
RELAX = int(o.get("relax", 3))
rng = np.random.default_rng(SEED)

LOOK, M = 300.0, 50.0
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL = 512.0
SEA_Z = -4967.0
N = 128
CELL_M = CELL / M                      # 10.24 m per cell
ANCHORS = {"tower", "authority_pad"}
TOWER_WORLD = (-349.0, 1388.0)      # where TutA's command tower really stands (the sheet's 0 0 is the generated map's origin)


def from_frame(along, across):
    a = math.radians(LOOK)
    return (along * math.cos(a) - across * math.sin(a), along * math.sin(a) + across * math.cos(a))


# --- terrain ---------------------------------------------------------------------------------------------
raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * 0.5
Zm = Z / M                                                     # metres
gy, gx = np.gradient(Zm, CELL_M)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
WATER = Z <= SEA_Z
DEPTH = np.clip((SEA_Z - Z) / M, 0, None)                      # metres of water
J, I = np.mgrid[0:N, 0:N]
WX = LOC[0] + (I - N / 2) * CELL
WY = LOC[1] + (J - N / 2) * CELL


def chamfer(mask):
    """distance (cells) from every cell to the nearest True cell; two-pass 3-4 chamfer"""
    big = 1e9
    D = np.where(mask, 0.0, big)
    for j in range(N):
        for i in range(N):
            if D[j, i] == 0:
                continue
            best = D[j, i]
            if i > 0:
                best = min(best, D[j, i - 1] + 1)
            if j > 0:
                best = min(best, D[j - 1, i] + 1)
                if i > 0:
                    best = min(best, D[j - 1, i - 1] + 1.414)
                if i < N - 1:
                    best = min(best, D[j - 1, i + 1] + 1.414)
            D[j, i] = best
    for j in range(N - 1, -1, -1):
        for i in range(N - 1, -1, -1):
            best = D[j, i]
            if i < N - 1:
                best = min(best, D[j, i + 1] + 1)
            if j < N - 1:
                best = min(best, D[j + 1, i] + 1)
                if i < N - 1:
                    best = min(best, D[j + 1, i + 1] + 1.414)
                if i > 0:
                    best = min(best, D[j + 1, i - 1] + 1.414)
            D[j, i] = best
    return D


D_WATER = chamfer(WATER) * CELL_M                              # metres to the sea
D_LAND = chamfer(~WATER) * CELL_M                              # metres to land (for things at sea)
DEEP = chamfer(DEPTH > 2.0) * CELL_M                           # metres to water at least 2 m deep


def domination(radius_cells=6):
    """Emilien's geographical domination: sum (h(x)-h(p)) / (1+|x-p|^2) over the neighbourhood, normalised"""
    out = np.zeros_like(Zm)
    for dj in range(-radius_cells, radius_cells + 1):
        for di in range(-radius_cells, radius_cells + 1):
            if di == 0 and dj == 0:
                continue
            d2 = (di * di + dj * dj) * CELL_M * CELL_M / 100.0
            sh = np.roll(np.roll(Zm, dj, 0), di, 1)
            out += (Zm - sh) / (1 + d2)
    s = out[~WATER]
    return np.clip(out / (np.percentile(np.abs(s), 95) + 1e-9), -1, 1)


DOM = domination()


def room_map(radius_m=100.0, max_slope=12.0):
    """GDMC-style buildable-area map: the share of cells within radius that are land, on the main mass and
    gentle; the plant needs room round its office, not a single flat cell on a cliff ledge"""
    ok = (~WATER) & (SLOPE <= max_slope)
    r = int(radius_m / CELL_M)
    acc = np.zeros_like(Zm)
    cnt = 0
    for dj in range(-r, r + 1):
        for di in range(-r, r + 1):
            if di * di + dj * dj <= r * r:
                acc += np.roll(np.roll(ok, dj, 0), di, 1)
                cnt += 1
    return acc / cnt


ROOM = room_map()


def main_landmass():
    """flood fill of land from the tower's cell: islets and sandbars are not buildable"""
    ti, tj = int((TOWER_WORLD[0] - LOC[0]) / CELL + N / 2), int((TOWER_WORLD[1] - LOC[1]) / CELL + N / 2)
    land = ~WATER
    seen = np.zeros((N, N), bool)
    stack = [(ti, tj)]
    while stack:
        i, j = stack.pop()
        if not (0 <= i < N and 0 <= j < N) or seen[j, i] or not land[j, i]:
            continue
        seen[j, i] = True
        stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    return seen

# --- the building encyclopedia -----------------------------------------------------------------------------
# f values: bell(x, lo, best, hi) = 1 at best, 0 at lo/hi, -1 beyond; close(d, best, maxd); far(d, mind)
def bell(x, lo, best, hi):
    x = np.asarray(x, float)
    up = np.where(x <= best, 1 - ((best - x) / max(best - lo, 1e-6)) ** 2, 1 - ((x - best) / max(hi - best, 1e-6)) ** 2)
    return np.where((x < lo) | (x > hi), -1.0, np.clip(up, 0, 1))


def close(d, best, maxd):
    d = np.asarray(d, float)
    return np.where(d > maxd, -1.0, np.where(d <= best, 1.0, 1 - (d - best) / max(maxd - best, 1e-6)))


def far(d, mind, best):
    d = np.asarray(d, float)
    return np.where(d < mind, -1.0, np.clip((d - mind) / max(best - mind, 1e-6), 0, 1))


HARD_NEAR = True        # beyond 1.5 lmax a "near" relation forbids the spot (keeps the plant a plant, not a scatter)


def attract(d, lmin, l0, lmax):
    """attraction-repulsion: -1 inside lmin, 1 at l0, 0 at lmax, forbidden beyond 1.5 lmax when HARD_NEAR"""
    d = np.asarray(d, float)
    v = np.where(d < lmin, -1.0, np.where(d <= l0, (d - lmin) / max(l0 - lmin, 1e-6),
                                           np.clip(1 - (d - l0) / max(lmax - l0, 1e-6), 0, 1)))
    if HARD_NEAR:
        v = np.where(d > 1.5 * lmax, -1.0, v)
    return v


# per kind: slope (lo, best, hi) deg; water: ("close", best, max) | ("far", min, best) | ("in", min_depth,
# dist_to_land_min, dist_to_land_max); near: [(id_or_kind, lmin, l0, lmax, w)]; avoid: [(id_or_kind, mind, best, w)];
# road: (best, max, w); dom: w (domination weight, may be negative); w_slope, w_water
KIND = {
    "office": dict(slope=(0, 2, 8), water=("close", 80, 350), near=[("tower", 180, 350, 700, 2.0)], road=(10, 200, 1.0), dom=0.5),
    "hall":   dict(slope=(0, 2, 7), water=("close", 60, 500), near=[("plant_office", 40, 110, 320, 2.5), ("hall", 25, 60, 220, 1.0)],
                   road=(10, 160, 1.0)),
    "tank":   dict(slope=(0, 1.5, 6), water=("close", 100, 600), near=[("hall", 40, 90, 260, 2.0)], road=(15, 200, 0.8)),
    "silo":   dict(slope=(0, 1.5, 6), water=("close", 60, 500), near=[("hall", 35, 80, 240, 2.0), ("dock", 60, 160, 500, 1.0)], road=(15, 200, 0.8)),
    "cooling": dict(slope=(0, 2, 7), water=("close", 60, 450), near=[("hall", 40, 100, 300, 2.0)], road=(20, 250, 0.5),
                    avoid=[("dorm", 120, 300, 1.5)]),
    "pump":   dict(slope=(0, 3, 12), water=("close", 0, 60), near=[("hall", 40, 150, 500, 1.0)], road=(10, 250, 0.6)),
    "dorm":   dict(slope=(0, 2, 8), water=("close", 100, 600), near=[("hall", 90, 180, 400, 2.0)], road=(10, 150, 1.2),
                   avoid=[("cooling", 150, 350, 1.5), ("tank", 100, 250, 1.0)]),
    "house":  dict(slope=(0, 4, 14), water=("close", 50, 500), near=[("hall", 150, 300, 700, 1.0)], road=(15, 220, 0.8), dom=1.5,
                   avoid=[("hall", 150, 300, 1.0)]),
    "pad":    dict(slope=(0, 1, 4), water=("close", 80, 700), near=[("plant_office", 80, 200, 500, 1.5)], road=(10, 200, 1.0)),
    "dock":   dict(slope=(0, 4, 20), water=("close", 0, 25), near=[("plant_office", 100, 250, 700, 1.5)], road=(0, 300, 0.6), deep=(0, 60, 2.0)),
    "jetty":  dict(slope=(0, 4, 20), water=("close", 0, 25), near=[("dock", 150, 350, 900, 1.0)], road=(0, 400, 0.4), deep=(0, 80, 1.5)),
    "mast":   dict(slope=(0, 6, 25), water=("close", 0, 900), near=[], road=(20, 500, 0.3), dom=3.0),
    "rig":    dict(water=("in", 3, 150, 700), near=[("dock", 200, 500, 1500, 1.0)]),
    "barge":  dict(water=("in", 1.5, 20, 150), near=[("dock", 40, 90, 300, 2.0)]),
    "wreck":  dict(water=("in", 1, 40, 250), near=[], avoid=[("dock", 200, 500, 1.0)]),
}
OVERRIDE = {
    "wellhead_a": dict(slope=(0, 4, 16), water=("far", 150, 500), near=[("wellhead", 150, 300, 800, 1.0)], road=(20, 500, 0.5), avoid=[("dorm", 150, 400, 1.0)]),
    "beacon": dict(slope=(0, 8, 30), water=("close", 0, 80), near=[], road=(0, 2000, 0.0), dom=3.0, avoid=[("hall", 300, 800, 1.0)]),
    "company_mast": dict(slope=(0, 6, 25), water=("close", 0, 900), near=[("plant_office", 100, 250, 800, 1.0)], road=(20, 400, 0.4), dom=2.5),
    "directors_house": dict(slope=(0, 4, 14), water=("close", 40, 300), near=[("tower", 250, 500, 1200, 0.8)], road=(15, 200, 0.8), dom=2.5,
                            avoid=[("hall", 200, 450, 1.5), ("dorm", 150, 400, 1.0)]),
    "old_camp": dict(slope=(0, 3, 10), water=("close", 60, 400), near=[("wellhead", 60, 150, 500, 1.5)], road=(10, 250, 0.6),
                     avoid=[("hall", 200, 500, 1.0)]),
    "checkpoint": "road:0.45",          # placed on the trunk road tower -> plant office
    "fuel_depot": dict(slope=(0, 1.5, 6), water=("close", 60, 400), near=[("dock", 60, 140, 400, 2.0)], road=(10, 200, 0.8)),
    "cargo_pad": dict(slope=(0, 1, 4), water=("close", 80, 700), near=[("plant_office", 120, 260, 600, 1.5), ("dock", 150, 350, 900, 0.8)], road=(10, 200, 1.0)),
    "intake": dict(slope=(0, 4, 15), water=("close", 0, 40), near=[("cooling", 60, 150, 500, 1.5)], road=(10, 300, 0.4)),
    "dead_rig": dict(water=("in", 3, 250, 900), near=[], avoid=[("new_rig", 300, 700, 1.5)]),
}
OVERRIDE["wellhead_b"] = OVERRIDE["wellhead_old"] = OVERRIDE["wellhead_a"]
# the island is only ~1.3 km across and the binder town ~120 x 200 m: the distances above were written at
# village scale, so they are shrunk here (slopes untouched)
DIST_SCALE = float(o.get("dist_scale", 0.35))


def _scale(spec):
    if not isinstance(spec, dict):
        return spec
    out = dict(spec)
    if "water" in out:
        wk = out["water"]
        out["water"] = (wk[0],) + tuple(v * DIST_SCALE if k > 0 and not (wk[0] == "in" and k == 1) else v for k, v in enumerate(wk[1:], 1))
        if wk[0] == "close":
            out["water"] = ("close", out["water"][1], max(out["water"][2], 1.3 * CELL_M))   # a shore cell is 10 m from water
    out["near"] = [(n, a * DIST_SCALE, b * DIST_SCALE, c * DIST_SCALE, wgt) for n, a, b, c, wgt in out.get("near", [])]
    out["avoid"] = [(n, a * DIST_SCALE, b * DIST_SCALE, wgt) for n, a, b, wgt in out.get("avoid", [])]
    if "road" in out:
        out["road"] = (out["road"][0] * DIST_SCALE, out["road"][1] * DIST_SCALE, out["road"][2])
    if "deep" in out:
        out["deep"] = (out["deep"][0] * DIST_SCALE, out["deep"][1] * DIST_SCALE, out["deep"][2])
    return out


KIND = {k: _scale(v) for k, v in KIND.items()}
OVERRIDE = {k: _scale(v) for k, v in OVERRIDE.items()}
PRIORITY = ["plant_office", "dock", "hall_a", "hall_b", "hall_c", "dorm", "tank_farm", "silos", "cooling_towers"]
LAYERS = {"core": 0, "boom": 1, "decline": 2}

# --- state ------------------------------------------------------------------------------------------------
citizens, buildings = binder.load()
buildings_at_tower = buildings["tower"]["at"]
MAIN = main_landmass()
placed = {}            # id -> dict(x, y, yaw, r, kind, cells)
ROAD = np.zeros((N, N), bool)
OCC = np.zeros((N, N), bool)


def world_to_cell(x, y):
    return (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2


def cell_to_world(fi, fj):
    return LOC[0] + (fi - N / 2) * CELL, LOC[1] + (fj - N / 2) * CELL


def footprint_cells(x, y, r_units):
    fi, fj = world_to_cell(x, y)
    rc = r_units / CELL
    cells = []
    for j in range(max(0, int(fj - rc)), min(N, int(fj + rc) + 2)):
        for i in range(max(0, int(fi - rc)), min(N, int(fi + rc) + 2)):
            if (i + 0.5 - fi) ** 2 + (j + 0.5 - fj) ** 2 <= (rc + 0.5) ** 2:
                cells.append((i, j))
    return cells


def group_offsets(b):
    """instance offsets (units) in the building's own frame, as make_avalon/export_mutator do"""
    wdt, dpt = b["size"][0] * M, b["size"][1] * M
    gap = max(wdt, dpt) * 1.5
    spec = b.get("count", "1").split()
    if spec[0].lower() == "2x2":
        return [(-gap / 2, -gap / 2), (gap / 2, -gap / 2), (-gap / 2, gap / 2), (gap / 2, gap / 2)], gap
    if len(spec) == 2:
        n = int(spec[0])
        return [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)], gap
    return [(0, 0)], 0


def radius_of(b):
    offs, gap = group_offsets(b)
    r = max(b["size"][0], b["size"][1]) * M * 0.6
    return r + max(math.hypot(a, c) for a, c in offs)


def dist_to(ids_or_kind):
    """distance map (metres) to the nearest placed building named or of that kind; None if none placed"""
    pts = [(p["x"], p["y"]) for pid, p in placed.items() if pid == ids_or_kind or p["kind"] == ids_or_kind
           or (ids_or_kind == "wellhead" and pid.startswith("wellhead"))]
    if not pts:
        return None
    d = np.full((N, N), np.inf)
    for x, y in pts:
        d = np.minimum(d, np.hypot(WX - x, WY - y) / M)
    return d


def interest_map(bid, b):
    spec = OVERRIDE.get(bid, KIND.get(b["kind"], KIND["hall"]))
    if isinstance(spec, str):
        return None, spec
    terms = []
    r_m = radius_of(b) / M
    if "slope" in spec:
        lo, best, hi = spec["slope"]
        terms.append((1.5, bell(SLOPE, lo - 1, best, hi * 2)))          # the pads terrace the ground: slope is a preference
    wkind = spec["water"]
    if wkind[0] == "close":
        terms.append((1.0, close(D_WATER, wkind[1], wkind[2])))
        margin = 0 if b["kind"] in ("dock", "jetty", "pump") else max(r_m * 0.5, 8)          # quays reach into the water
        terms.append((3.0, np.where(WATER | (D_WATER < margin), -1.0, 1.0)))                     # the footprint stays dry
    elif wkind[0] == "far":
        terms.append((1.0, far(D_WATER, wkind[1], wkind[2])))
        terms.append((3.0, np.where(WATER, -1.0, 1.0)))
    else:                                                                                      # at sea
        _, mind, dmin, dmax = wkind
        terms.append((2.0, np.where((~WATER) | (DEPTH < mind), -1.0, 1.0)))
        terms.append((1.0, bell(D_LAND, dmin * 0.5, (dmin + dmax) / 2, dmax)))
    if "deep" in spec:
        best, maxd, wgt = spec["deep"]
        terms.append((wgt, close(DEEP, best, maxd)))
    for name, lmin, l0, lmax, wgt in spec.get("near", []):
        d = dist_to(name)
        if d is not None:
            terms.append((wgt, attract(d, lmin, l0, lmax)))
    # systemic relations: every need pulls the building toward a placed provider, and forbids beyond reach
    prov, need = systems.spec_of(bid, b)
    for res in sorted(need):
        carrier, reach = systems.RES[res]
        pts = [(p["x"], p["y"]) for pid, p in placed.items() if res in systems.spec_of(pid, buildings[pid])[0]]
        if not pts:
            continue
        d = np.full((N, N), np.inf)
        for x, y in pts:
            d = np.minimum(d, np.hypot(WX - x, WY - y) / M)
        lmin = r_m + 12
        v = np.where(d < lmin, -1.0, np.where(d <= reach * 0.45, 1.0, np.clip(1 - (d - reach * 0.45) / (reach * 0.55), 0, 1)))
        if HARD_NEAR:
            v = np.where(d > reach, -1.0, v)
        terms.append((2.0 if res in systems.CORE else 1.0, v))
    for name, mind, best, wgt in spec.get("avoid", []):
        d = dist_to(name)
        if d is not None:
            terms.append((wgt, far(d, mind, best)))
    if "road" in spec and ROAD.any() and spec["road"][2] > 0:
        best, maxd, wgt = spec["road"]
        droad = chamfer(ROAD) * CELL_M
        terms.append((wgt, np.where(droad > maxd, 0.0, np.where(droad <= best, 1.0, 1 - (droad - best) / max(maxd - best, 1e-6)))))
    if spec.get("room"):
        need, wgt = spec["room"]
        terms.append((wgt, np.where(ROOM < need, -1.0, np.clip((ROOM - need) / (1 - need), 0, 1))))
    if "sector" in spec:
        cx0, cy0, yaw0, half = spec["sector"]
        ang = np.degrees(np.arctan2(WY - cy0, WX - cx0))
        dang = np.abs((ang - yaw0 + 180) % 360 - 180)
        terms.append((2.0, np.where(dang > half, -1.0, 1 - dang / half)))
    if spec.get("dom"):
        terms.append((spec["dom"], DOM if not wkind[0] == "in" else np.zeros_like(DOM)))
    if wkind[0] != "in":
        terms.append((3.0, np.where(MAIN, 1.0, -1.0)))
    # no overlap with what stands already
    dall = dist_to(None)
    occ_d = chamfer(OCC) * CELL_M if OCC.any() else np.full((N, N), 1e9)
    terms.append((3.0, np.where(occ_d < r_m + 6, -1.0, 1.0)))
    forbidden = np.zeros((N, N), bool)
    total = np.zeros((N, N))
    wsum = 0.0
    for wgt, f in terms:
        forbidden |= f <= -1.0
        total += wgt * f
        wsum += wgt
    Imap = np.where(forbidden, 0.0, np.clip(total / wsum, 0, 1))
    Imap[:2, :] = Imap[-2:, :] = Imap[:, :2] = Imap[:, -2:] = 0
    return Imap, spec


def sample(Imap, tries=60):
    """Emilien's seeding: random positions, keep with probability I; fall back to the best of the tries"""
    flat = Imap.ravel()
    cand = np.flatnonzero(flat > 0)
    if len(cand) == 0:
        return None
    best, bestI = None, -1
    for _ in range(tries):
        k = cand[rng.integers(len(cand))]
        Ik = flat[k]
        if rng.random() < Ik ** 4:                       # steep: only good spots get taken early
            return k
        if Ik > bestI:
            best, bestI = k, Ik
    return best


def least_cost_path(start, goals):
    """Dijkstra on the grid from start cell to any goal cell: slope^2, water and footprints cost, roads cheap"""
    if not goals.any():
        return []
    si, sj = start
    dist = {(si, sj): 0.0}
    prev = {}
    pq = [(0.0, si, sj)]
    gi = set(zip(*np.nonzero(goals.T)))
    while pq:
        d, i, j = heapq.heappop(pq)
        if (i, j) in gi:
            path = [(i, j)]
            while (i, j) in prev:
                i, j = prev[(i, j)]
                path.append((i, j))
            return path[::-1]
        if d > dist.get((i, j), np.inf):
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if not (0 <= ni < N and 0 <= nj < N):
                    continue
                step = math.hypot(di, dj)
                dz = abs(Zm[nj, ni] - Zm[j, i]) / (step * CELL_M)
                c = step * (1 + 25 * dz * dz)
                if WATER[nj, ni]:
                    c += 400.0
                if OCC[nj, ni] and not goals[nj, ni]:
                    c += 40.0
                if ROAD[nj, ni]:
                    c *= 0.2
                nd = d + c
                if nd < dist.get((ni, nj), np.inf):
                    dist[(ni, nj)] = nd
                    prev[(ni, nj)] = (i, j)
                    heapq.heappush(pq, (nd, ni, nj))
    return []


def place(bid, b, x, y, yaw):
    r = radius_of(b)
    cells = footprint_cells(x, y, r)
    for i, j in cells:
        OCC[j, i] = True
    placed[bid] = dict(x=float(x), y=float(y), yaw=float(yaw), r=float(r), kind=b["kind"], cells=cells)


roads = []


def connect(bid):
    p = placed[bid]
    if p["kind"] in ("rig", "barge", "wreck"):
        return
    fi, fj = world_to_cell(p["x"], p["y"])
    start = (int(fi), int(fj))
    goals = ROAD.copy()
    if not goals.any():
        ti, tj = world_to_cell(placed["tower"]["x"], placed["tower"]["y"]) if "tower" in placed else (fi, fj)
        goals[int(tj), int(ti)] = True
    path = least_cost_path(start, goals)
    if len(path) > 1:
        for i, j in path:
            ROAD[j, i] = True
        roads.append([cell_to_world(i + 0.5, j + 0.5) for i, j in path])


# the window: the plant office (and so the plant) stands where the command room can see it
OVERRIDE["plant_office"] = dict(KIND["office"], sector=(TOWER_WORLD[0], TOWER_WORLD[1], LOOK, 32.0), room=(0.45, 3.0))
for _k in ("hall", "tank", "silo", "cooling", "pad", "dorm"):
    KIND[_k]["room"] = (0.3, 1.5)

TOWER_WORLD = (-349.0, 1388.0)      # where TutA's command tower really stands (the sheet's 0 0 is the generated map's origin)

# --- 1. anchors ---------------------------------------------------------------------------------------------
for bid, b in buildings.items():
    if "at" not in b:
        continue
    if bid in ANCHORS or b.get("anchor", "no").lower() == "yes":
        along, across, deg = b["at"]
        # anchors ride with the real tower: their sheet offset from the tower, no shift
        ox, oy = from_frame(along - buildings_at_tower[0], across - buildings_at_tower[1])
        place(bid, b, TOWER_WORLD[0] + ox, TOWER_WORLD[1] + oy, deg)

# --- 2. seeding in layer order, roads as we go ----------------------------------------------------------------
order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed]
order.sort(key=lambda i: (LAYERS.get(buildings[i].get("layer", "boom"), 1),
                          PRIORITY.index(i) if i in PRIORITY else 99, i))
# providers before consumers within the same layer (the generator house before the halls it powers)
SPEC = {i: systems.spec_of(i, buildings[i]) for i in buildings}
ordered, pending = [], list(order)
while pending:
    progressed = False
    for i in list(pending):
        _, need = SPEC[i]
        providers = [j for j in pending if j != i and any(r in SPEC[j][0] for r in need) and
                     LAYERS.get(buildings[j].get("layer", "boom"), 1) <= LAYERS.get(buildings[i].get("layer", "boom"), 1)]
        # a provider that itself needs something from i (generator <-> fuel depot) does not block
        providers = [j for j in providers if not any(r in SPEC[i][0] for r in SPEC[j][1])]
        if not providers:
            ordered.append(i)
            pending.remove(i)
            progressed = True
    if not progressed:
        ordered.append(pending.pop(0))
order = ordered
deferred = []
for bid in order:
    b = buildings[bid]
    Imap, spec = interest_map(bid, b)
    if Imap is None:
        deferred.append((bid, spec))
        continue
    if Imap.max() <= 0:                                   # the relations cannot all hold: relax them
        HARD_NEAR = False
        Imap, spec = interest_map(bid, b)
        HARD_NEAR = True
    k = sample(Imap)
    if k is None:
        print("  no site for", bid, "(interest everywhere 0): keeping its sheet position", file=sys.stderr)
        along, across, deg = b["at"]
        x, y = from_frame(along + SHIFT, across)
        place(bid, b, x, y, deg)
        continue
    j, i = divmod(int(k), N)
    x, y = cell_to_world(i + rng.uniform(0.2, 0.8), j + rng.uniform(0.2, 0.8))
    place(bid, b, x, y, 0.0)
    placed[bid]["I"] = float(Imap.ravel()[k])
    connect(bid)

# --- 3. Voronoi fluctuation: drift toward the cell centroid while the interest holds ----------------------------
ids = [i for i in placed if i not in ANCHORS and placed[i]["kind"] not in ("rig", "barge", "wreck")]
for it in range(RELAX):
    pts = np.array([[placed[i]["x"], placed[i]["y"]] for i in placed])
    names = list(placed)
    d = np.stack([np.hypot(WX - px, WY - py) for px, py in pts])
    owner = d.argmin(0)
    near = d.min(0) < 150 * M                                        # a cell belongs to a town building within 150 m
    for bid in ids:
        k = names.index(bid)
        mask = (owner == k) & near & ~WATER
        if mask.sum() < 2:
            continue
        cx, cy = WX[mask].mean(), WY[mask].mean()
        p = placed[bid]
        nx, ny = p["x"] + 0.35 * (cx - p["x"]), p["y"] + 0.35 * (cy - p["y"])
        # recompute this building's interest without itself in the maps
        saved = placed.pop(bid)
        for i, j in saved["cells"]:
            OCC[j, i] = False
        Imap, _ = interest_map(bid, buildings[bid])
        fi, fj = world_to_cell(nx, ny)
        fi0, fj0 = world_to_cell(saved["x"], saved["y"])
        ok = 0 <= int(fi) < N and 0 <= int(fj) < N and Imap[int(fj), int(fi)] >= 0.8 * Imap[int(fj0), int(fi0)] - 1e-6 \
            and Imap[int(fj), int(fi)] > 0
        if ok:
            place(bid, buildings[bid], nx, ny, saved["yaw"])
            placed[bid]["I"] = float(Imap[int(fj), int(fi)])
        else:
            placed[bid] = saved
            for i, j in saved["cells"]:
                OCC[j, i] = True
# roads are rebuilt from scratch on the final positions (the drift moved their ends)
ROAD[:] = False
roads = []
for bid in order:
    if bid in placed:
        connect(bid)

# --- 4. deferred: the checkpoint on the trunk road -----------------------------------------------------------------
for bid, spec in deferred:
    frac = float(spec.split(":")[1])
    if roads and "plant_office" in placed:
        ti, tj = world_to_cell(placed["tower"]["x"], placed["tower"]["y"])
        goals = np.zeros((N, N), bool)
        pi, pj = world_to_cell(placed["plant_office"]["x"], placed["plant_office"]["y"])
        goals[int(pj), int(pi)] = True
        path = least_cost_path((int(ti), int(tj)), goals)
        if len(path) > 2:
            i, j = path[int(frac * (len(path) - 1))]
            a, c = path[max(0, int(frac * (len(path) - 1)) - 1)], path[min(len(path) - 1, int(frac * (len(path) - 1)) + 1)]
            yaw = math.degrees(math.atan2(c[1] - a[1], c[0] - a[0]))
            place(bid, buildings[bid], *cell_to_world(i + 0.5, j + 0.5), yaw)
            continue
    along, across, deg = buildings[bid]["at"]
    place(bid, buildings[bid], *from_frame(along + SHIFT, across), deg)

# --- 5. yaw: the front faces the nearest road; docks and jetties face the sea --------------------------------------
droad = chamfer(ROAD) if ROAD.any() else None
gwy, gwx = np.gradient(D_WATER)
for bid, p in placed.items():
    if bid in ANCHORS:
        continue
    fi, fj = world_to_cell(p["x"], p["y"])
    i, j = min(N - 1, max(0, int(fi))), min(N - 1, max(0, int(fj)))
    if p["kind"] in ("dock", "jetty", "pump") or bid == "intake":
        p["yaw"] = math.degrees(math.atan2(-gwy[j, i], -gwx[j, i]))              # downhill of the water distance = toward the sea
    elif p["kind"] in ("rig", "barge", "wreck"):
        p["yaw"] = float(rng.uniform(0, 360))
    elif droad is not None and bid not in [d[0] for d in deferred]:
        best, bd = None, 1e9
        for dj in range(-6, 7):
            for di in range(-6, 7):
                ni, nj = i + di, j + dj
                if 0 <= ni < N and 0 <= nj < N and ROAD[nj, ni] and 0 < di * di + dj * dj < bd:
                    best, bd = (ni, nj), di * di + dj * dj
        if best:
            p["yaw"] = math.degrees(math.atan2(best[1] - j, best[0] - i))

# --- output -----------------------------------------------------------------------------------------------------
out = {"seed": SEED, "shift": SHIFT, "heightmap": os.path.abspath(src),
       "buildings": {bid: {"x": round(p["x"], 1), "y": round(p["y"], 1), "yaw": round(p["yaw"], 1),
                           "z": round(float(Z[min(N - 1, max(0, int(world_to_cell(p["x"], p["y"])[1]))),
                                              min(N - 1, max(0, int(world_to_cell(p["x"], p["y"])[0])))]), 1),
                           "interest": round(p.get("I", 1.0), 3), "cells": [list(c) for c in p["cells"]]} for bid, p in placed.items()},
       "roads": [[[round(x, 1), round(y, 1)] for x, y in r] for r in roads]}
json.dump(out, open(dst, "w"), indent=0)
low = [bid for bid, p in placed.items() if p.get("I", 1) < 0.3]
print(f"seed {SEED}: {len(placed)} buildings placed, {len(roads)} road legs, {int(ROAD.sum())} road cells -> {dst}"
      + (f"  (low interest: {', '.join(low)})" if low else ""))

if PNG:
    from PIL import Image, ImageDraw
    S = 6
    img = Image.new("RGB", (N * S, N * S), (30, 60, 140))
    px = img.load()
    t = np.clip((Z - SEA_Z) / 3500, 0, 1)
    for j in range(N):
        for i in range(N):
            if not WATER[j, i]:
                c = (int(80 + 150 * t[j, i]), int(120 + 100 * t[j, i]), int(60 + 150 * t[j, i]))
                for a in range(S):
                    for bb in range(S):
                        px[i * S + a, (N - 1 - j) * S + bb] = c
    dr = ImageDraw.Draw(img)

    def P(x, y):
        fi, fj = world_to_cell(x, y)
        return (fi * S, (N - fj) * S)
    for r in roads:
        dr.line([P(x, y) for x, y in r], fill=(90, 70, 50), width=3)
    for bid, p in placed.items():
        cx, cy = P(p["x"], p["y"])
        rr = max(3, p["r"] / CELL * S)
        col = (230, 60, 60) if bid in ANCHORS else ((80, 200, 255) if p["kind"] in ("rig", "barge", "wreck", "dock", "jetty") else (240, 220, 80))
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=2)
        a = math.radians(p["yaw"])
        dr.line([(cx, cy), (cx + rr * 1.6 * math.cos(a), cy - rr * 1.6 * math.sin(a))], fill=col, width=2)
        dr.text((cx + rr + 2, cy - 6), bid, fill=(255, 255, 255))
    img.save(PNG)
