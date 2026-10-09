r"""Placement rules for the binder's story buildings (binder 1940260), instead of their placeholder `at:` values.

    py tools/anchors.py <run folder> [heightmap=isl_e.bmp] [layout=isl_layout.json] [out=<run>\anchors.json]
                        [png=<run>\isl_anchors.png] [write=0]

The rules (redesign/2026-10-09: writer s. 1 + 3.10, engineer E14', level designer I3, artist s. 3.1):
  * liandri_tower (the parti's hero): the SUMMIT - the highest buildable ground inside the town's land (main island,
    within TOWN_M of the spine, off the shore), where "buildable" = its footprint's ground spans no more than the 30 m
    battered plinth can take up; with a truck road (grade-capped, MAX_GRADE) down to the spine. Front faces the road.
  * guest_house: beside directors_house (same yaw, one side or the other, on the flatter free side).
  * water_tower: E14' - the service reservoir on the LOWEST ground within the pipe's reach (300 m) of the water
    consumers (the hero included) whose tank still stands >= 28 m over the highest floor it serves (target 28-50 m);
    the pump house should sit below it.
  * drain: an UNDERGROUND culvert from the dorm square, under the spine, to a sea outfall (by the pump house, >= 150 m
    from the intake, E24). Section 384 x 320 UU with a dry ledge, the junction room 768 x 768 and the sluice gallery
    1536 x 768 x 448 UU (level designer I3); the invert falls >= 0.5 % to the sea. It counts as a walkable path for
    walks.py (walk_edges()).

As a library (the pipeline hooks, tools/HOOKS.md):
  * summit(Z, spine, sheet, main=None, avoid=()) -> site dict with the truck road; layout_spine calls it after its
    branches (before plots), places the hero there and adds the road;
  * beside(B, sheets, host, guest, Z) / water_tower_site(Z, B, sheets) / drain(Z, L, sheets) work on a placed layout;
  * apply(L, Z, sheets) does all four on a layout dict (the standalone path, or town.py after layout_spine).
Heightmap frame = TutA (as layout_spine.py): a cell is 512 UU = 10.24 m, 1 m = 50 UU.
"""
import heapq, json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, N, M = 512.0, 128, 50.0
CELL_M = CELL / M
SEA_Z = -4967.0
TOWER_WORLD = (-349.0, 1388.0)
LOOK, HALF_W = 300.0, 34.0              # the command room's window (compose.py)

PLINTH_M = 30.0                          # the hero's battered plinth (artist s. 3.1): the ground range it can take up
TOWN_M = 300.0                           # the town's land: main island within this of the town's spine stretch
TOWN_PAST_M = 0.0                        # the town's spine stretch: dock -> tower, and this far on toward the mine
FUEL_CLEAR_M = 100.0                     # E16: a dwelling stands >= 100 m from a fuel store
BESIDE_MAX_M = 60.0                      # how much further than "next door" the guest house may move to clear E16
WINDOW_BONUS = 1000.0                   # metres of "height": any summit in the window frame beats any outside it
WINDOW_THIRDS_M = 25.0                   # inside the frame, a vertical third is worth this many metres of height
EDGE_U = 0.1                             # a hero this close to the frame's side edge counts as OUTSIDE it (round 3; compose.EDGE_U)
WIDE_M = 600.0                           # the frame search widens to this far from the town's spine before falling back
BEHIND_DEG = 100.0                       # the town's land: within this of the window bearing (yaw 300) from the tower
SHORE_M = 40.0                           # ... and this far off the sea
HERO_SLOPE = 24.0                        # mean slope under the footprint, degrees
MAX_GRADE = 0.12                         # truck roads (terrain_cutfill's MAX_GRADE; engineer E1)
AVOID = {"tower": 150.0, "authority_pad": 120.0, "dock": 100.0}   # metres kept clear round these (security; the quay's yard: 100 m, so a Cine8-like dock in the window still leaves the frame its hero)

try:                                     # the parti's hero (liandri_tower since binder 1940260), "tower" as the fallback
    PARTI_HERO = json.load(open(os.path.join(HERE, "binder", "parti.json"))).get("hero", "tower")
except (OSError, ValueError):
    PARTI_HERO = "tower"

UU_CULVERT = (384, 320)                 # w, h (level designer I3); dry ledge 128
UU_LEDGE = 128
UU_JUNCTION = (768, 768, 448)
UU_GALLERY = (1536, 768, 448)            # l, w, h: the sluice gallery, the reveal
UU_QUIET = 3600                          # the LD7 quiet stretch before the gallery
COVER_M = 1.0                            # earth over the culvert's roof
MIN_FALL = 0.005                         # invert grade toward the outfall
OUTFALL_M = 0.5                          # the outfall invert over the sea (a free outfall: +0.5..2 m)
MAX_COVER_M = 12.0                       # buildable: no more earth than this over the culvert's roof
DROP_M = 2.0                             # a step down steeper than the fall by this much is a drop shaft
HEADWALL_M = 15.0                        # the last metres to the outfall may run at grade (the headwall)
WATER_REACH_M = 300.0                    # systems.RES water
HEAD_M = 28.0                            # E14': tank base >= highest served floor + 28 m (round 3; the engineer's E14)
HEAD_MAX_M = 50.0                        # ... and no more than this (the target 28-50 m: more bursts the pipes)
NO_FLOORS = ("cooling", "tank", "silo", "mast", "pump", "wellhead", "rig", "pad", "dock", "jetty")


# --- terrain ---------------------------------------------------------------------------------------------------
def load_heights(bmp):
    """the 16-bit heightmap -> Z[j, i] in world units (as layout_spine.py)"""
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
    if h > 0:
        H = H[::-1]
    return LOC[2] + (H - 32768) * 0.5


def w2c(x, y):
    return (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2


def c2w(i, j):
    return LOC[0] + (i - N / 2) * CELL, LOC[1] + (j - N / 2) * CELL


def zat(Z, x, y):
    """bilinear ground height (world units)"""
    fi, fj = w2c(x, y)
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return SEA_Z
    ti, tj = fi - i0, fj - j0
    return float(Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)


def main_land(Z, seed=TOWER_WORLD):
    """the land mass the Authority tower stands on (layout_spine.main_mass)"""
    from scipy.ndimage import label
    lab, _ = label(Z > SEA_Z)
    i, j = (int(v) for v in w2c(*seed))
    k = lab[j, i]
    return lab == k if k else (Z > SEA_Z)


def slope_deg(Z):
    gy, gx = np.gradient(Z / M, CELL_M)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def raster(lines, every=CELL / 3):
    """cells under polylines (world units)"""
    m = np.zeros((N, N), bool)
    for r in lines:
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            n = int(math.hypot(bx - ax, by - ay) / every) + 1
            for t in np.linspace(0, 1, n + 1):
                fi, fj = w2c(ax + (bx - ax) * t, ay + (by - ay) * t)
                i, j = int(round(fi)), int(round(fj))
                if 0 <= i < N and 0 <= j < N:
                    m[j, i] = True
    return m


def dist_m(mask):
    from scipy.ndimage import distance_transform_edt
    if not mask.any():
        return np.full((N, N), 1e9)
    return distance_transform_edt(~mask) * CELL_M


def disc(r_cells):
    r = int(math.ceil(r_cells))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r_cells * r_cells + 0.5


def cells_of(x, y, size):
    """the cells a building covers (layout_spine.place: radius 0.6 x its longest side)"""
    r = max(size[0], size[1]) * M * 0.6
    fi, fj = w2c(x, y)
    rc = r / CELL
    return [[i, j] for j in range(max(0, int(fj - rc)), min(N, int(fj + rc) + 2))
            for i in range(max(0, int(fi - rc)), min(N, int(fi + rc) + 2))
            if (i + 0.5 - fi) ** 2 + (j + 0.5 - fj) ** 2 <= (rc + 0.5) ** 2]


def chaikin(pts, n=2):
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts[:-1], pts[1:]))


MOVES8 = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]
MOVES16 = MOVES8 + [(a * s, b * t) for a, b in ((1, 2), (2, 1)) for s in (-1, 1) for t in (-1, 1)]   # + knight moves


def grid_path(cost_fn, start, goals, allowed, moves=MOVES8):
    """Dijkstra on cells (8-connected, or 16 with knight moves for finer headings) from start (i, j) to the cheapest of
    goals (set of (i, j)); cost_fn(i, j, ni, nj) -> step cost (inf = closed). Returns the cell list start..goal, or []"""
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    while pq:
        d, (i, j) = heapq.heappop(pq)
        if (i, j) in goals:
            out = [(i, j)]
            while (i, j) in prev:
                i, j = prev[(i, j)]
                out.append((i, j))
            return out[::-1]
        if d > dist.get((i, j), np.inf):
            continue
        for di, dj in moves:
            ni, nj = i + di, j + dj
            if not (0 <= ni < N and 0 <= nj < N) or not allowed[nj, ni]:
                continue
            c = cost_fn(i, j, ni, nj)
            if not np.isfinite(c):
                continue
            nd = d + c
            if nd < dist.get((ni, nj), np.inf):
                dist[(ni, nj)] = nd
                prev[(ni, nj)] = (i, j)
                heapq.heappush(pq, (nd, (ni, nj)))
    return []


# --- 1. the summit: liandri_tower ------------------------------------------------------------------------------
def town_spine(spine, past_m=TOWN_PAST_M):
    """the town's stretch of the spine: dock -> the Authority tower, plus past_m beyond it (the rest climbs to the
    mine, which is not the town)"""
    if len(spine) < 2:
        return spine
    k = min(range(len(spine)), key=lambda q: math.hypot(spine[q][0] - TOWER_WORLD[0], spine[q][1] - TOWER_WORLD[1]))
    s = 0.0
    out = list(spine[:k + 1])
    for a, b in zip(spine[k:-1], spine[k + 1:]):
        s += math.hypot(b[0] - a[0], b[1] - a[1])
        if s > past_m * M:
            break
        out.append(b)
    return out

def truck_road(Z, a, spine, main, max_grade=MAX_GRADE, start_r_m=0.0):
    """least-cost road from a (world) down to the nearest spine cell, GRADE-CAPPED: a step steeper than the cap is
    closed, so the road switchbacks across the contours (16 headings: knight moves give the gentle diagonals). The cap
    is the branch class limit (MAX_GRADE); only when no capped road exists is it relaxed (x1.25, x1.5, x2, then soft),
    and the result says so. Inside the plinth (start_r_m) the ground is built, so it is free of the cap.
    Returns (points, metres, steepest grade on the natural ground, the cap used)"""
    goals = {(int(round(w2c(x, y)[0])), int(round(w2c(x, y)[1]))) for x, y in spine}
    goals = {g for g in goals if 0 <= g[0] < N and 0 <= g[1] < N}
    Zm = Z / M
    fi, fj = w2c(*a)
    s0 = (int(round(fi)), int(round(fj)))
    plinth_c = start_r_m / CELL_M

    def make_cost(cap, soft=False):
        def cost(i, j, ni, nj):
            d = math.hypot(ni - i, nj - j) * CELL_M
            if math.hypot(ni - s0[0], nj - s0[1]) <= plinth_c:
                return d
            g = abs(Zm[nj, ni] - Zm[j, i]) / d
            if g > cap:
                return d * 25.0 * (1 + 20 * g * g) if soft else np.inf
            return d * (1 + 20 * g * g)
        return cost
    cells, cap_used = [], max_grade
    for k, f in enumerate((1.0, 1.25, 1.5, 2.0, None)):
        cap_used = max_grade * (f or 2.0)
        cells = grid_path(make_cost(cap_used, soft=f is None), s0, goals, main, MOVES16)
        if cells:
            break
    if not cells:
        return [], 0.0, 0.0, cap_used
    # knight moves jump a cell: fill in the cell between so the road has no gaps
    full = [cells[0]]
    for (i, j), (ni, nj) in zip(cells[:-1], cells[1:]):
        if max(abs(ni - i), abs(nj - j)) == 2:
            full.append(((i + ni) / 2.0, (j + nj) / 2.0))
        full.append((ni, nj))
    pts = chaikin([c2w(i, j) for i, j in full], 1)
    pts[0] = tuple(a)
    if start_r_m > 0:                     # the road starts at the plinth's foot, not under the tower
        keep = [p for p in pts if math.hypot(p[0] - a[0], p[1] - a[1]) >= start_r_m * M]
        if keep:
            k0 = pts.index(keep[0])
            ux, uy = keep[0][0] - a[0], keep[0][1] - a[1]
            r = math.hypot(ux, uy)
            pts = [(a[0] + ux / r * start_r_m * M, a[1] + uy / r * start_r_m * M)] + pts[k0:]
    # the steepest natural grade along the routed cells, outside the plinth (terrain_cutfill grades the rest to MAX_GRADE)
    grade = 0.0
    for (i, j), (ni, nj) in zip(cells[:-1], cells[1:]):
        if math.hypot(*(np.subtract(c2w(i, j), a))) < start_r_m * M:
            continue
        grade = max(grade, abs(Zm[nj, ni] - Zm[j, i]) / (math.hypot(ni - i, nj - j) * CELL_M))
    return [[round(x, 1), round(y, 1)] for x, y in pts], plen(pts) / M, grade, cap_used


def summit(Z, spine, sheet, main=None, avoid=(), occupied=None, town_m=TOWN_M, plinth_m=PLINTH_M, works_z=None):
    """the hero on the highest buildable ground inside the town's land.
    spine: [(x, y)] world; sheet: the binder sheet (size); avoid: [(x, y, metres)]; occupied: bool[N, N] cells already
    built on. Returns {x, y, z, yaw, ground_lo/hi/mean (m), plinth_used_m, road, road_m, road_grade, in_window, ...}"""
    from scipy.ndimage import maximum_filter, minimum_filter, uniform_filter
    main = main_land(Z) if main is None else main
    Zm = Z / M
    land = main & (Z > SEA_Z)
    spine = town_spine(spine)
    d_spine = dist_m(raster([spine]))
    d_sea = dist_m(~land)
    town = land & (d_spine <= town_m) & (d_sea >= SHORE_M)
    # the town lies in front of the Authority tower (its window side); the mountain behind it is not the town's land
    Jg, Ig = np.mgrid[0:N, 0:N]
    Xg, Yg = c2w(Ig, Jg)
    bearing = np.degrees(np.arctan2(Yg - TOWER_WORLD[1], Xg - TOWER_WORLD[0]))
    town &= np.abs((bearing - LOOK + 180) % 360 - 180) <= BEHIND_DEG
    r = max(sheet["size"][0], sheet["size"][1]) / 2.0 / CELL_M        # the footprint's half diagonal-ish, in cells
    fp = disc(max(1.0, r))
    hi = maximum_filter(Zm, footprint=fp, mode="nearest")
    lo = minimum_filter(Zm, footprint=fp, mode="nearest")
    k = fp.shape[0]
    mean = uniform_filter(Zm, size=k, mode="nearest")
    slope = uniform_filter(slope_deg(Z), size=k, mode="nearest")
    J, I = np.mgrid[0:N, 0:N]
    WX, WY = c2w(I, J)
    site_ok = (hi - lo <= plinth_m) & (slope <= HERO_SLOPE)
    for (ax, ay, am) in avoid:
        site_ok &= np.hypot(WX - ax, WY - ay) / M >= am + r * CELL_M
    if occupied is not None:
        site_ok &= ~maximum_filter(occupied.astype(np.uint8), footprint=disc(r + 1), mode="constant").astype(bool)

    def within(mask):
        return minimum_filter(mask.astype(np.uint8), footprint=fp, mode="constant", cval=0).astype(bool) & site_ok
    ok = within(town)
    # the window: the parti wants the temple as the command room's hero. A candidate whose top is in compose's frame
    # (yaw 300 +- HALF_W, pitch -15 +- HALF_H) and not hidden by the terrain beats any candidate outside it; inside,
    # height wins, with a pull to a vertical third (WINDOW_THIRDS_M metres of height per unit of thirds score). When
    # the town's strip has no such spot, the frame is searched on wider land (WIDE_M from the town's spine) before
    # falling back.
    top_m = sheet["size"][2] if len(sheet["size"]) > 2 else 60.0

    # round 3: an EDGE-ONLY spot (u < EDGE_U or > 1 - EDGE_U) counts as OUTSIDE the frame - no bonus at all (it was
    # half); the cooling towers then stay the window's hero (compose.py, plan D1 fallback c). Among the inner spots the
    # tiebreak is the height over the works (works_z: the works' mean ground, world units; a constant shift, so the
    # order is the height order - it is reported as over_works_m).
    works_m = (works_z / M) if works_z is not None else None

    def frame_scores(cand):
        sc = np.where(cand, mean, -1e9)
        fr, edge = {}, {}
        for j_, i_ in zip(*np.nonzero(cand)):
            x_, y_ = c2w(i_, j_)
            u = in_frame(Z, x_, y_, hi[j_, i_] * M + top_m * M)
            if u is None:
                continue
            if u < EDGE_U or u > 1 - EDGE_U:
                edge[(j_, i_)] = u            # on the frame's side edge: outside, for the choice
                continue
            fr[(j_, i_)] = u
            thirds = max(0.0, 1 - min(abs(u - 1 / 3), abs(u - 2 / 3)) / 0.17)
            sc[j_, i_] = WINDOW_BONUS + (mean[j_, i_] - (works_m or 0.0)) + WINDOW_THIRDS_M * thirds
        return sc, fr, edge
    # tiers: the town's strip with a spot inside the frame; wider land with one; else the fallback (the highest in the
    # strip, outside the frame - edge-only spots included)
    score, frame, edge_spots = frame_scores(ok)
    widened = False
    if not frame:
        wide = within(land & (d_spine <= WIDE_M) & (d_sea >= SHORE_M))
        sc2, fr2, ed2 = frame_scores(wide)
        if fr2:
            score, frame, edge_spots, ok, widened = sc2, fr2, ed2, wide, True
    if not ok.any():
        return None
    j, i = np.unravel_index(int(score.argmax()), score.shape)
    x, y = c2w(i, j)
    fallback = (j, i) not in frame
    if fallback:
        print("  summit: no buildable spot inside the window frame (%d edge-only); the highest outside it (%d candidates)" % (
            len(edge_spots), int(ok.sum())), file=sys.stderr)
    road, road_m, grade, cap = truck_road(Z, (x, y), spine, main, start_r_m=r * CELL_M + 5)
    gate = road[0] if road else min(spine, key=lambda p: math.hypot(p[0] - x, p[1] - y))
    yaw = math.degrees(math.atan2(gate[1] - y, gate[0] - x))              # the front (the ceremonial stair) to the road
    ang = math.degrees(math.atan2(y - TOWER_WORLD[1], x - TOWER_WORLD[0]))
    dw = abs((ang - LOOK + 180) % 360 - 180)
    return {"x": round(x, 1), "y": round(y, 1), "z": round(float(Z[j, i]), 1), "yaw": round(yaw, 1),
            "ground_mean_m": round(float(mean[j, i] - SEA_Z / M), 1), "ground_lo_m": round(float(lo[j, i] - SEA_Z / M), 1),
            "ground_hi_m": round(float(hi[j, i] - SEA_Z / M), 1), "plinth_used_m": round(float(hi[j, i] - lo[j, i]), 1),
            "town_top_m": round(float(Zm[town].max() - SEA_Z / M), 1) if town.any() else None,
            "road": road, "road_m": round(road_m), "road_grade": round(grade, 3), "road_cap": round(cap, 3),
            "dist_tower_m": round(math.hypot(x - TOWER_WORLD[0], y - TOWER_WORLD[1]) / M),
            "window_deg_off": round(dw, 1), "in_window": not fallback, "frame_u": round(frame[(j, i)], 2) if not fallback else None,
            "edge_u": round(edge_spots[(j, i)], 2) if (j, i) in edge_spots else None,
            "over_works_m": round(float(mean[j, i] - works_m), 1) if works_m is not None else None,
            "window_candidates": len(frame), "edge_only_candidates": len(edge_spots), "fallback": fallback, "widened": widened}


def in_frame(Z, x, y, top_z):
    """compose's window frame: u (0..1) of the point (x, y, top_z) when it is in the frame and the terrain does not
    hide it from the command room's eye, else None"""
    import compose
    p = compose.project(x, y, top_z)
    if p is None:
        return None
    ex, ey, ez = compose.EYE
    for t in np.linspace(0.02, 0.95, 60):
        if zat(Z, ex + (x - ex) * t, ey + (y - ey) * t) > ez + (top_z - ez) * t + 1.0:
            return None
    return p[0]


# --- 2. beside: guest_house next to directors_house -------------------------------------------------------------
def fuel_stores(B, sheets):
    """the buildings that store fuel (E16's fire set-back sources): providers of fuel by systems.spec_of"""
    import systems
    return [bid for bid in B if bid in sheets and not B[bid].get("abandoned") and "fuel" in systems.spec_of(bid, sheets[bid])[0]]


def fuel_clear_m(B, sheets, x, y):
    fs = fuel_stores(B, sheets)
    return min((math.hypot(B[f]["x"] - x, B[f]["y"] - y) / M for f in fs), default=1e9)


def beside(B, sheets, host, guest, Z, gap_m=6.0, fuel_m=FUEL_CLEAR_M):
    """the guest beside the host: same yaw, on a side of the host's frontage (local Y) or behind it, the flatter free
    spot, nearest the host - but never within fuel_m of a fuel store (E16, a dwelling). When every spot near the host
    breaks E16 it walks further out (up to BESIDE_MAX_M); if still none, the spot farthest from the fuel, flagged"""
    if host not in B or guest not in sheets:
        return None
    h = B[host]
    wh, wg = sheets[host]["size"][0], sheets[guest]["size"][0]
    dh, dg = sheets[host]["size"][1], max(sheets[guest]["size"][0], sheets[guest]["size"][1])
    a = math.radians(h["yaw"])
    lx, ly = -math.sin(a), math.cos(a)                                  # the host's local Y (its width)
    fx, fy = math.cos(a), math.sin(a)                                   # its front
    zh = zat(Z, h["x"], h["y"])
    best = None
    for extra in np.arange(0.0, BESIDE_MAX_M + 1, 6.0):
        for side, back in ((+1, 0.0), (-1, 0.0), (+1, -0.5), (-1, -0.5), (+1, 0.5), (-1, 0.5), (0, -1.0)):
            if side:
                off_l, off_f = side * (wh / 2 + gap_m + wg / 2 + extra), back * dg
            else:                                                   # behind the host
                off_l, off_f = 0.0, -(dh / 2 + gap_m + dg / 2 + extra)
            x = h["x"] + (lx * off_l + fx * off_f) * M
            y = h["y"] + (ly * off_l + fy * off_f) * M
            z = zat(Z, x, y)
            if z <= SEA_Z + 20:
                continue
            clash = 0
            for bid, p in B.items():
                if bid in (host, guest) or bid not in sheets or "size" not in sheets[bid]:
                    continue
                rr = (max(sheets[bid]["size"][0], sheets[bid]["size"][1]) / 2 + dg / 2) * M
                if math.hypot(p["x"] - x, p["y"] - y) < rr:
                    clash += 1
            fuel = fuel_clear_m(B, sheets, x, y)
            e16 = fuel >= fuel_m
            cost = (0 if e16 else 1000 + (fuel_m - fuel) * 10) + clash * 100 + abs(z - zh) / M + abs(back) * 3 + extra * 0.5 + (4 if not side else 0)
            if best is None or cost < best[0]:
                best = (cost, x, y, z, side, back, clash, fuel, e16, extra)
    if best is None:
        return None
    _, x, y, z, side, back, clash, fuel, e16, extra = best
    if not e16:
        print("  %s: no spot near %s is %d m from the fuel (best %.0f m)" % (guest, host, fuel_m, fuel), file=sys.stderr)
    return {"x": round(x, 1), "y": round(y, 1), "z": round(z, 1), "yaw": round(h["yaw"], 1), "host": host,
            "side": {1: "left", -1: "right", 0: "behind"}[side], "extra_m": float(extra), "step_m": round(abs(z - zh) / M, 1),
            "clashes": clash, "fuel_m": round(fuel), "e16_ok": e16}


# --- 3. the water tower on the high point (E14') ----------------------------------------------------------------
def water_consumers(B, sheets, exclude=("water_tower",)):
    import systems
    out = []
    for bid, p in B.items():
        if bid in exclude or bid not in sheets or sheets[bid].get("abandoned") or p.get("abandoned"):
            continue
        if "water" in systems.spec_of(bid, sheets[bid])[1]:
            out.append(bid)
    return out


def water_tower_site(Z, B, sheets, wid="water_tower", main=None, reach_m=WATER_REACH_M, head_m=HEAD_M, must=(PARTI_HERO,)):
    """E14': the reservoir on the lowest buildable ground that still reaches (most of) the water consumers with
    head_m of head over the highest floor it serves. Candidates must reach >= 75 % of the best coverage (and the hero,
    `must`, when any can); of those, the lowest with enough head wins (round 3; it was the highest ground)."""
    if wid not in sheets:
        return None
    main = main_land(Z) if main is None else main
    cons = water_consumers(B, sheets, exclude=(wid,))
    if not cons:
        return None
    S = slope_deg(Z)
    occ = np.zeros((N, N), bool)
    for bid, p in B.items():
        if bid != wid and bid in sheets and "size" in sheets[bid] and sheets[bid].get("kind") not in ("rig", "islet", "barge", "wreck"):
            for i, j in cells_of(p["x"], p["y"], sheets[bid]["size"]):
                occ[j, i] = True
    J, I = np.mgrid[0:N, 0:N]
    WX, WY = c2w(I, J)
    ok = main & (Z > SEA_Z + 100) & (S <= 20) & ~occ
    cover = np.zeros((N, N))
    for bid in cons:
        cover += (np.hypot(WX - B[bid]["x"], WY - B[bid]["y"]) / M <= reach_m)
    cover = np.where(ok, cover, -1)
    if cover.max() <= 0:
        return None
    cand = cover >= 0.75 * cover.max()
    # the rule-placed company buildings (the hero on its summit) have no plot pull toward a provider: the tower must
    # reach them (with a margin), when any candidate can
    for bid in must:
        if bid in cons:
            near = (np.hypot(WX - B[bid]["x"], WY - B[bid]["y"]) / M <= 0.9 * reach_m) & ok
            if (cand & near).any():
                cand &= near
            elif near.any():
                cand = near
    mast = sheets[wid]["size"][2] if len(sheets[wid]["size"]) > 2 else 22.0

    def floor_m(b):                    # the highest floor people use: storeys of 3.4 m (process plant has no floors)
        h = sheets[b]["size"][2] if len(sheets[b]["size"]) > 2 else 3.4
        storeys = 1 if sheets[b].get("kind") in NO_FLOORS else max(1, min(4, int(h // 3.4)))
        return zat(Z, B[b]["x"], B[b]["y"]) / M + (storeys - 1) * 3.4
    # round 3 (E14'): the head is computed PER CANDIDATE - the tank base (the top fifth of the mast) over the highest
    # floor of everything within reach of that spot - and the LOWEST candidate with head >= head_m wins (target
    # head_m..HEAD_MAX_M: a tower on the peak gave Cine8 89 m, which bursts the pipes). If no candidate reaches
    # head_m, the one with the most head is taken.
    top_floor_map = np.full((N, N), -1e9)
    for bid in cons:
        near_b = np.hypot(WX - B[bid]["x"], WY - B[bid]["y"]) / M <= reach_m
        top_floor_map = np.where(near_b, np.maximum(top_floor_map, floor_m(bid)), top_floor_map)
    head_map = Z / M + 0.8 * mast - top_floor_map
    enough = cand & (head_map >= head_m)
    if enough.any():
        score = np.where(enough, -Z, -1e12)          # the lowest ground that still gives the head
        chosen = "lowest with >= %g m head" % head_m
    else:
        score = np.where(cand, head_map, -1e12)      # none reaches it: the most head
        chosen = "most head (none reaches %g m)" % head_m
    j, i = np.unravel_index(int(score.argmax()), score.shape)
    x, y = c2w(i, j)
    zg = float(Z[j, i])
    served = [bid for bid in cons if math.hypot(B[bid]["x"] - x, B[bid]["y"] - y) / M <= reach_m]
    tank_base = zg / M + 0.8 * mast                                     # the tank sits on the top fifth of the mast
    top_floor = max(floor_m(b) for b in served)
    head = tank_base - top_floor
    ph = B.get("pump_house")
    return {"x": round(x, 1), "y": round(y, 1), "z": round(zg, 1), "yaw": 0.0, "ground_m": round(zg / M - SEA_Z / M, 1),
            "served": served, "consumers": len(cons), "head_m": round(head, 1), "e14_ok": head >= head_m,
            "head_in_target": head_m <= head <= HEAD_MAX_M, "pick": chosen, "candidates_with_head": int(enough.sum()),
            "pump_house_below": (zat(Z, ph["x"], ph["y"]) < zg) if ph else None}


# --- 4. the drain: the outfall culvert under the spine ----------------------------------------------------------
def drain(Z, L, sheets, main=None, start=None):
    """the culvert from the dorm square under the spine to a sea outfall; the invert falls to the sea.
    Returns {path: [[x, y, z_ground, z_invert]], length_m/_uu, grate, outfall, segments, max_depth_m, ...}"""
    B = L["buildings"]
    main = main_land(Z) if main is None else main
    roads = L.get("roads", [])
    cls = L.get("road_class") or (["spine"] + ["branch"] * (len(roads) - 1))
    spine = L.get("spine") or (roads[0] if roads else [])
    on_spine = raster([spine])
    on_road = raster([r for r, c in zip(roads, cls) if c != "path"])
    under = np.zeros((N, N), bool)
    for bid, p in B.items():
        if bid in sheets and "size" in sheets[bid] and sheets[bid].get("kind") not in ("pad", "dock", "jetty", "culvert"):
            for i, j in cells_of(p["x"], p["y"], sheets[bid]["size"]):
                under[j, i] = True
    # the grate: the dorm square = the road point nearest the dorms' centre (the 'dorm' building first)
    dorms = [b for b in ("dorm", "dorm_b", "dorm_c") if b in B and not B[b].get("abandoned")]
    if start is None:
        if not dorms:
            return None
        cx = B[dorms[0]]["x"]
        cy = B[dorms[0]]["y"]
        pts = [p for r in roads for p in r]
        start = min(pts, key=lambda p: math.hypot(p[0] - cx, p[1] - cy)) if pts else (cx, cy)
    Zm = Z / M
    land = main & (Z > SEA_Z)
    J, I = np.mgrid[0:N, 0:N]
    WX, WY = c2w(I, J)
    # the outfall: a shore cell; below the pump house if there is one, >= 150 m from the intake (E24)
    from scipy.ndimage import binary_dilation
    shore = land & binary_dilation(~land)
    if "intake" in B:
        shore &= np.hypot(WX - B["intake"]["x"], WY - B["intake"]["y"]) / M >= 150
    if not shore.any():
        return None
    pull = np.zeros((N, N))
    if "pump_house" in B:
        pull = np.hypot(WX - B["pump_house"]["x"], WY - B["pump_house"]["y"]) / M

    def cost(i, j, ni, nj):
        d = math.hypot(ni - i, nj - j) * CELL_M
        k = 0.3 if on_spine[nj, ni] else (0.6 if on_road[nj, ni] else 1.0)
        if under[nj, ni]:
            k += 0.8                                          # under a foundation: avoid
        rise = max(0.0, Zm[nj, ni] - Zm[j, i]) / d            # against the fall: dig deeper
        over = max(0.0, Zm[nj, ni] - z_grate - MAX_COVER_M)   # ground the culvert can't reach under at MAX_COVER_M: go round
        return d * k * (1 + 4 * rise) + d * 2.0 * over
    fi, fj = w2c(*start)
    z_grate = zat(Z, *start) / M
    s0 = (int(round(fi)), int(round(fj)))
    # Dijkstra to every shore cell, then the outfall = least (path cost + 0.5 x metres from the pump house)
    dist = {s0: 0.0}
    prev = {}
    pq = [(0.0, s0)]
    while pq:
        d, (i, j) = heapq.heappop(pq)
        if d > dist.get((i, j), np.inf):
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if not (0 <= ni < N and 0 <= nj < N) or not land[nj, ni]:
                    continue
                nd = d + cost(i, j, ni, nj)
                if nd < dist.get((ni, nj), np.inf):
                    dist[(ni, nj)] = nd
                    prev[(ni, nj)] = (i, j)
                    heapq.heappush(pq, (nd, (ni, nj)))
    # a free outfall needs the culvert's height + cover over the sea at the shore: prefer a bank high enough
    need = (UU_CULVERT[1] / M + COVER_M + OUTFALL_M)
    ends = [(dist[(i, j)] + 0.5 * pull[j, i] + 8.0 * max(0.0, need - (Zm[j, i] - SEA_Z / M)), (i, j)) for (i, j) in dist if shore[j, i]]
    if not ends:
        return None
    _, (i, j) = min(ends)
    cells = [(i, j)]
    while (i, j) in prev:
        i, j = prev[(i, j)]
        cells.append((i, j))
    cells.reverse()
    pts = chaikin([tuple(start)] + [c2w(i, j) for i, j in cells[1:]], 2)
    # one point every ~half cell, the ground under it, and the invert: falling >= MIN_FALL toward the outfall
    dense = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (CELL / 2)))
        dense += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(1, n + 1)]
    s = [0.0]
    for a, b in zip(dense[:-1], dense[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = s[-1]
    q_end = min(UU_QUIET, max(0.0, total - UU_GALLERY[0] - 400))      # the quiet stretch, then the gallery
    g0, g1 = q_end, min(total, q_end + UU_GALLERY[0])
    jn = 0.5 * q_end                                                    # the junction room halfway along the quiet stretch

    def height_at(sv):
        return UU_GALLERY[2] if g0 <= sv <= g1 else (UU_JUNCTION[2] if abs(sv - jn) <= UU_JUNCTION[0] / 2 else UU_CULVERT[1])
    ground = [zat(Z, x, y) for x, y in dense]
    # the invert, laid from the OUTFALL upstream: at the sea it sits OUTFALL_M over the water (a free outfall, never
    # drowned); going upstream it rises by the minimum fall, and never lies deeper than MAX_COVER_M of cover - where the
    # ground climbs, the invert climbs with it (gravity still holds: it only ever falls toward the sea). Where it then
    # drops faster than the fall going downstream, that step is a DROP SHAFT; where the cover would be < COVER_M the
    # culvert is shallow (cut-and-cover, or the headwall at the outfall).
    n = len(dense)
    inv = [0.0] * n
    inv[-1] = SEA_Z + OUTFALL_M * M
    for k in range(n - 2, -1, -1):
        lo = ground[k] - height_at(s[k]) - MAX_COVER_M * M
        inv[k] = max(inv[k + 1] + MIN_FALL * (s[k + 1] - s[k]), lo)
    drops, shallow = [], 0
    for k in range(n - 1):
        dz = inv[k] - inv[k + 1] - MIN_FALL * (s[k + 1] - s[k])
        if dz > DROP_M * M:
            drops.append({"s_uu": round(s[k]), "x": round(dense[k][0], 1), "y": round(dense[k][1], 1), "drop_m": round(dz / M, 1)})
    for k in range(n):
        if ground[k] - inv[k] - height_at(s[k]) < COVER_M * M and s[k] < total - HEADWALL_M * M:
            shallow += s[k + 1] - s[k] if k + 1 < n else 0.0
    # merge drops within 20 m into one shaft
    shafts = []
    for d_ in drops:
        if shafts and d_["s_uu"] - shafts[-1]["s_uu"] < 20 * M:
            shafts[-1]["drop_m"] = round(shafts[-1]["drop_m"] + d_["drop_m"], 1)
        else:
            shafts.append(d_)
    path = [[round(x, 1), round(y, 1), round(gz, 1), round(iv, 1)] for (x, y), gz, iv in zip(dense, ground, inv)]
    depth = [(gz - iv) / M for gz, iv in zip(ground, inv)]
    cover = [(gz - iv - height_at(sv)) / M for gz, iv, sv in zip(ground, inv, s)]
    under_spine = sum(1 for x, y in dense if on_spine[int(round(w2c(x, y)[1])) % N, int(round(w2c(x, y)[0])) % N]) / len(dense)
    segs = [{"kind": "grate", "s_uu": 0, "w": UU_CULVERT[0], "h": UU_CULVERT[1]},
            {"kind": "culvert", "s0_uu": 0, "s1_uu": round(g0), "w": UU_CULVERT[0], "h": UU_CULVERT[1], "ledge": UU_LEDGE},
            {"kind": "junction_room", "s_uu": round(jn), "w": UU_JUNCTION[0], "l": UU_JUNCTION[1], "h": UU_JUNCTION[2], "light": "shaft from a street grate"},
            {"kind": "sluice_gallery", "s0_uu": round(g0), "s1_uu": round(g1), "w": UU_GALLERY[1], "h": UU_GALLERY[2],
             "note": "the reveal: lamps 1..6 on the right wall, the far sluice gate with the red beacon"},
            {"kind": "culvert", "s0_uu": round(g1), "s1_uu": round(total), "w": UU_CULVERT[0], "h": UU_CULVERT[1], "ledge": UU_LEDGE},
            {"kind": "outfall", "s_uu": round(total), "w": UU_CULVERT[0], "h": UU_CULVERT[1]}]
    if g1 - g0 < UU_GALLERY[0] - 1:
        segs[3]["short"] = True
    return {"path": path, "length_m": round(total / M, 1), "length_uu": round(total), "walk_s": round(total / 263.0, 1),
            "grate": path[0][:2], "outfall": path[-1][:2], "segments": segs,
            "section_uu": {"culvert": list(UU_CULVERT), "ledge": UU_LEDGE, "junction": list(UU_JUNCTION), "gallery": list(UU_GALLERY)},
            "max_depth_m": round(max(depth), 1), "min_depth_m": round(min(depth), 1),
            "max_cover_m": round(max(cover), 1), "drop_shafts": shafts, "shallow_m": round(shallow / M),
            "outfall_invert_vs_sea_m": round((inv[-1] - SEA_Z) / M, 1), "under_spine": round(under_spine, 2),
            "dorm_square": dorms[0] if dorms else None}


def walk_edges(dr, to_fine, nearest_free, NF, cost_k=1.0):
    """walks.py: the drain as a walkable path - one tunnel edge each way between its two mouths (the grate and the
    outfall), weighted by its length (metres x cost_k). Returns [(u, v, w)] for walks.graph(extra=...)"""
    if not dr:
        return []
    ends = []
    for x, y in (dr["grate"], dr["outfall"]):
        fi, fj = to_fine(x, y)
        i, j = int(round(fi)), int(round(fj))
        if not (0 <= i < NF and 0 <= j < NF):
            return []
        k = nearest_free(j * NF + i)
        if k is None:
            return []
        ends.append(k)
    w = dr["length_m"] * cost_k
    return [(ends[0], ends[1], w), (ends[1], ends[0], w)]


# --- all four on a layout ---------------------------------------------------------------------------------------
def place_entry(B, bid, site, sheet, layer=None):
    B[bid] = dict(B.get(bid, {}), x=site["x"], y=site["y"], yaw=site["yaw"], z=site["z"],
                  cells=cells_of(site["x"], site["y"], sheet["size"]) if "size" in sheet else [],
                  layer=layer or sheet.get("layer", "boom"))
    B[bid].setdefault("interest", 1.0)
    return B[bid]


def apply(L, Z, sheets=None, hero=None):
    """the four rules on a placed layout dict (in place). The hero goes on the summit (moving it if it was placed),
    its truck road joins L['roads'] as a branch; guest_house beside directors_house; water_tower by E14'; the drain
    into L['drain'] (and B['drain'] at its grate). Returns the report dict (also L['anchors'])"""
    if sheets is None:
        import binder
        _, sheets = binder.load()
    if hero is None:
        try:
            hero = json.load(open(os.path.join(HERE, "binder", "parti.json"))).get("hero", "tower")
        except (OSError, ValueError):
            hero = "tower"
    B = L["buildings"]
    main = main_land(Z)
    rep = {}
    if hero in sheets and hero != "tower":
        occ = np.zeros((N, N), bool)
        for bid, p in B.items():
            if bid != hero:
                for i, j in (p.get("cells") or []):
                    occ[j, i] = True
        avoid = [(B[k]["x"], B[k]["y"], m) for k, m in AVOID.items() if k in B]
        if "sites" in L and "mine" in L["sites"]:
            avoid.append((L["sites"]["mine"][0], L["sites"]["mine"][1], 150.0))
        works = [zat(Z, p["x"], p["y"]) for bid, p in B.items() if sheets.get(bid, {}).get("kind") in ("hall", "tank", "silo", "cooling")]
        wz = float(np.mean(works)) if works else None
        site = summit(Z, L.get("spine") or L["roads"][0], sheets[hero], main, avoid, occupied=occ, works_z=wz)
        if site is None:                                             # nothing free: relax the occupancy
            site = summit(Z, L.get("spine") or L["roads"][0], sheets[hero], main, avoid, works_z=wz)
            if site:
                site["note"] = "every free summit site taken; placed over other buildings"
        if site:
            place_entry(B, hero, site, sheets[hero])
            if site["road"]:
                L["roads"].append(site["road"])
                if "road_class" in L:
                    L["road_class"].append("branch")
                if "road_w" in L:
                    L["road_w"].append(1.1)
            rep[hero] = {k: v for k, v in site.items() if k != "road"}
            rep["summit"] = rep[hero]
    if "guest_house" in sheets and "directors_house" in B:
        g = beside(B, sheets, "directors_house", "guest_house", Z)
        if g:
            place_entry(B, "guest_house", g, sheets["guest_house"])
            rep["guest_house"] = g
    if "water_tower" in sheets:
        wt = water_tower_site(Z, B, sheets, main=main)
        if wt:
            place_entry(B, "water_tower", wt, sheets["water_tower"])
            rep["water_tower"] = {k: v for k, v in wt.items() if k != "served"} | {"served_n": len(wt["served"])}
    if "drain" in sheets:
        dr = drain(Z, L, sheets, main)
        if dr:
            L["drain"] = dr
            gx, gy = dr["grate"]
            B["drain"] = dict(B.get("drain", {}), x=gx, y=gy, yaw=0.0, z=round(zat(Z, gx, gy), 1), cells=[],
                              layer=sheets["drain"].get("layer", "core"), interest=1.0, underground=True)
            rep["drain"] = {k: v for k, v in dr.items() if k not in ("path", "segments")}
    L["anchors"] = rep
    return rep


def overlay(Z, L, png, rep=None, S=6):
    from PIL import Image, ImageDraw
    t = np.clip((Z - SEA_Z) / 3500, 0, 1)
    rgb = np.zeros((N, N, 3), np.uint8)
    land = Z > SEA_Z
    rgb[..., 0] = np.where(land, 80 + 150 * t, 30)
    rgb[..., 1] = np.where(land, 120 + 100 * t, 60)
    rgb[..., 2] = np.where(land, 60 + 150 * t, 140)
    img = Image.fromarray(rgb[::-1]).resize((N * S, N * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)

    def P(x, y):
        fi, fj = w2c(x, y)
        return (fi * S, (N - fj) * S)
    for r, c in zip(L.get("roads", []), L.get("road_class") or ["branch"] * len(L.get("roads", []))):
        if len(r) > 1:
            dr.line([P(*p[:2]) for p in r], fill=(90, 70, 50) if c != "path" else (150, 120, 90), width=4 if c == "spine" else 2)
    for bid, p in L["buildings"].items():
        cx, cy = P(p["x"], p["y"])
        dr.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(240, 220, 80))
    d = L.get("drain")
    if d:
        dr.line([P(*p[:2]) for p in d["path"]], fill=(0, 220, 255), width=3)
        for sg in d["segments"]:
            if sg["kind"] == "sluice_gallery":
                s_pts = [p for p, sv in zip(d["path"], _arclen(d["path"])) if sg["s0_uu"] <= sv <= sg["s1_uu"]]
                if len(s_pts) > 1:
                    dr.line([P(*p[:2]) for p in s_pts], fill=(255, 40, 40), width=6)
        dr.text(P(*d["outfall"]), "outfall", fill=(255, 255, 255))
        dr.text(P(*d["grate"]), "grate", fill=(255, 255, 255))
    for bid, col in (("liandri_tower", (255, 60, 200)), ("guest_house", (255, 160, 0)), ("water_tower", (60, 160, 255)),
                     ("directors_house", (255, 255, 255))):
        if bid in L["buildings"]:
            cx, cy = P(L["buildings"][bid]["x"], L["buildings"][bid]["y"])
            dr.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=col, width=3)
            dr.text((cx + 10, cy - 6), bid, fill=col)
    if "tower" in L["buildings"]:
        tx, ty = P(TOWER_WORLD[0], TOWER_WORLD[1])
        for a in (LOOK - HALF_W, LOOK + HALF_W):
            dr.line([(tx, ty), (tx + 400 * math.cos(math.radians(a)), ty - 400 * math.sin(math.radians(a)))], fill=(255, 255, 255), width=1)
    if rep:
        y0 = 4
        for k, v in rep.items():
            line = "%s: %s" % (k, ", ".join("%s=%s" % (kk, vv) for kk, vv in v.items() if not isinstance(vv, (list, dict)))[:150])
            dr.text((4, y0), line, fill=(255, 255, 255))
            y0 += 12
    img.save(png)


def _arclen(path):
    s = [0.0]
    for a, b in zip(path[:-1], path[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return s


if __name__ == "__main__":
    run = sys.argv[1]
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    hm = os.path.join(run, o.get("heightmap", "isl_e.bmp"))
    lp = os.path.join(run, o.get("layout", "isl_layout.json"))
    Z = load_heights(hm)
    L = json.load(open(lp))
    rep = apply(L, Z)
    out = o.get("out", os.path.join(run, "anchors.json"))
    json.dump({"heightmap": hm, "layout": lp, "report": rep, "drain": L.get("drain"),
               "placed": {k: L["buildings"][k] for k in ("liandri_tower", "guest_house", "water_tower", "drain") if k in L["buildings"]},
               "roads_added": L["roads"][-1:] if "liandri_tower" in rep else []},
              open(out, "w"), indent=1)
    overlay(Z, L, o.get("png", os.path.join(run, "isl_anchors.png")), rep)
    if o.get("write") == "1":                     # write=1: the layout itself gets the placements (a re-run of systems etc. follows)
        json.dump(L, open(lp, "w"), indent=0)
    for k, v in rep.items():
        print("%-14s %s" % (k, ", ".join("%s %s" % (kk, vv) for kk, vv in v.items() if not isinstance(vv, (list, dict)))))
    print("->", out)
