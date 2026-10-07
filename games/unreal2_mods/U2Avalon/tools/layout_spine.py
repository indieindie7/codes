r"""Spine-based town layout: the street first, then plots along it, then the buildings in the plots.

    py tools/layout_spine.py <heightmap.bmp> <out.json> [seed=1] [png=out.png]

How a one-reason settlement is actually built (see games/reports/How others build towns.md): one road
from the external connection (the dock) past the works to the tower and on to the mine; frontage plots
along both sides; every building faces its plot's road; neighbours at known distances; fences close the
gaps; the ore line is the one dominant structure. The binder still says what exists and when (layers),
systems.py still says what each building needs and the reach of each resource; this file only changes
WHERE: a building can only stand in a plot.

Output: the same JSON as layout.py (buildings {x, y, yaw, z, cells}, roads, connections added later by
systems.py) plus "spine", "plots" and "fences" for the clutter pass. Heightmap frame = TutA (see
terrain_cutfill.py); a cell is 512 units = 10.24 m.
"""
import heapq, json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa
import systems  # noqa

src, dst = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
SEED = int(o.get("seed", 1))
PNG = o.get("png")
CAMERA_K = float(o.get("camera", 2.0))     # how strongly the camera term counts against systems/ring pulls
VIS = None                            # vis=<viewshed npz>: how much the player sees each cell (viewshed.py)
if o.get("vis"):
    _v = np.load(o["vis"])["score"]
    VIS = np.clip(_v / max(1e-6, np.percentile(_v[_v > 0], 95)), 0, 1) if (_v > 0).any() else None


def camera_weight(bid, b):
    """how much a building wants to be in the player's view: the story's places most, plumbing least
    (film-set rule: dress what the camera sees)"""
    if b.get("function") in ("social", "clinic", "store") or b.get("kind") in ("hall", "office", "dorm", "cooling", "silo", "mast"):
        return 1.8
    if b.get("kind") in ("pump", "wellhead") or bid.startswith(("shed", "pump", "water_tanks", "intake")):
        return 0.4
    return 1.0
rng = np.random.default_rng(SEED)

LOOK, M = 300.0, 50.0
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, N = 512.0, 128
CELL_M = CELL / M
SEA_Z = -4967.0
TOWER_WORLD = (-349.0, 1388.0)
ANCHORS = {"tower", "authority_pad"}
WINDOW = (LOOK, 34.0)                 # the command room looks along yaw 300 +- 34: the works stand there
GAP_M = 10.0                          # metres of yard between neighbouring plots (a fence or a gate)
SETBACK_M = 4.0                       # from the road edge to the plot front
ROAD_HALF_M = 4.0

# --- terrain -------------------------------------------------------------------------------------------
raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * 0.5
Zm = Z / M
gy, gx = np.gradient(Zm, CELL_M)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
WATER = Z <= SEA_Z
DEPTH = np.clip((SEA_Z - Z) / M, 0, None)
J, I = np.mgrid[0:N, 0:N]
WX = LOC[0] + (I - N / 2) * CELL
WY = LOC[1] + (J - N / 2) * CELL


def chamfer(mask):
    big = 1e9
    D = np.where(mask, 0.0, big)
    for j in range(N):
        for i in range(N):
            if D[j, i] == 0:
                continue
            b = D[j, i]
            if i > 0: b = min(b, D[j, i - 1] + 1)
            if j > 0:
                b = min(b, D[j - 1, i] + 1)
                if i > 0: b = min(b, D[j - 1, i - 1] + 1.414)
                if i < N - 1: b = min(b, D[j - 1, i + 1] + 1.414)
            D[j, i] = b
    for j in range(N - 1, -1, -1):
        for i in range(N - 1, -1, -1):
            b = D[j, i]
            if i < N - 1: b = min(b, D[j, i + 1] + 1)
            if j < N - 1:
                b = min(b, D[j + 1, i] + 1)
                if i < N - 1: b = min(b, D[j + 1, i + 1] + 1.414)
                if i > 0: b = min(b, D[j + 1, i - 1] + 1.414)
            D[j, i] = b
    return D


D_WATER = chamfer(WATER) * CELL_M
D_LAND = chamfer(~WATER) * CELL_M
DEEP = chamfer(DEPTH > 2.0) * CELL_M


def world_to_cell(x, y):
    return (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2


def cell_to_world(fi, fj):
    return LOC[0] + (fi - N / 2) * CELL, LOC[1] + (fj - N / 2) * CELL


def at(F, x, y, default=0.0):
    fi, fj = world_to_cell(x, y)
    i, j = int(round(fi)), int(round(fj))
    if 0 <= i < N and 0 <= j < N:
        return float(F[j, i])
    return default


def zb(x, y):
    fi, fj = world_to_cell(x, y)
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return SEA_Z
    ti, tj = fi - i0, fj - j0
    return float(Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)


def main_mass():
    ti, tj = world_to_cell(*TOWER_WORLD)
    land = ~WATER
    seen = np.zeros((N, N), bool)
    stack = [(int(ti), int(tj))]
    while stack:
        i, j = stack.pop()
        if not (0 <= i < N and 0 <= j < N) or seen[j, i] or not land[j, i]:
            continue
        seen[j, i] = True
        stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    return seen


MAIN = main_mass()
ROOM = None


def room_map(radius_m=80.0, max_slope=14.0):
    ok = MAIN & (SLOPE <= max_slope)
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
citizens, buildings = binder.load()
SPEC = {i: systems.spec_of(i, buildings[i]) for i in buildings}

# --- 1. the key sites: dock (external connection), the works stretch, the mine ------------------------------
tx, ty = TOWER_WORLD
ang_t = np.degrees(np.arctan2(WY - ty, WX - tx))
dang = np.abs((ang_t - WINDOW[0] + 180) % 360 - 180)
dist_t = np.hypot(WX - tx, WY - ty) / M
shore = MAIN & (D_WATER <= 1.2 * CELL_M) & (~WATER)
# the dock as NEAR as the shore allows (200-550 m): the works between it and the tower then sit close and big in
# the command room's window (the user's first play: at 300-700 m the town read as specks and nobody saw roads)
dock_score = np.where(shore & (dang < WINDOW[1]) & (dist_t > 200) & (dist_t < 550) & (DEEP < 60),
                      1.5 * ROOM + 0.6 * (1 - dang / WINDOW[1]) + 1.0 * np.clip((550 - dist_t) / 350, 0, 1), -1)
if dock_score.max() <= 0:
    dock_score = np.where(shore & (dist_t < 900), ROOM, -1)
j, i = np.unravel_index(int(dock_score.argmax()), dock_score.shape)
DOCK = cell_to_world(i + 0.5, j + 0.5)
# the mine: inland, high, out of the window sector or far behind the works, 250-800 m from the tower
inland = MAIN & (D_WATER > 120) & (dist_t > 250) & (dist_t < 800) & (SLOPE < 22)
height_t = np.clip((Z - SEA_Z) / 4000.0, 0, 1)
mine_score = np.where(inland, height_t + 0.3 * (1 - np.clip(np.hypot(WX - DOCK[0], WY - DOCK[1]) / M / 800, 0, 1)) * 0 + 0.2 * (dang > WINDOW[1]), -1)
j, i = np.unravel_index(int(mine_score.argmax()), mine_score.shape)
MINE = cell_to_world(i + 0.5, j + 0.5)


# --- 2. the spine: least-cost road dock -> tower -> mine, smoothed --------------------------------------------
def path(a, b):
    ai, aj = (int(v) for v in world_to_cell(*a))
    bi, bj = (int(v) for v in world_to_cell(*b))
    dist = {(ai, aj): 0.0}
    prev = {}
    pq = [(0.0, ai, aj)]
    while pq:
        d, i, j = heapq.heappop(pq)
        if (i, j) == (bi, bj):
            out = [(i, j)]
            while (i, j) in prev:
                i, j = prev[(i, j)]
                out.append((i, j))
            return out[::-1]
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
                c = step * (1 + 30 * dz * dz)
                if WATER[nj, ni]:
                    c += 400.0
                if not MAIN[nj, ni]:
                    c += 50.0
                nd = d + c
                if nd < dist.get((ni, nj), np.inf):
                    dist[(ni, nj)] = nd
                    prev[(ni, nj)] = (i, j)
                    heapq.heappush(pq, (nd, ni, nj))
    return []


def chaikin(pts, n=2):
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        out.append(pts[-1])
        pts = out
    return pts


cells = path(DOCK, TOWER_WORLD)
cells2 = path(TOWER_WORLD, MINE)
spine_cells = cells + cells2[1:]
spine = chaikin([cell_to_world(i + 0.5, j + 0.5) for i, j in spine_cells], 2)
# the tower stands beside the road, not on it: nudge the spine around the tower's pad (radius 700 units)
spine = [(x, y) if math.hypot(x - tx, y - ty) > 700 else
         (tx + (x - tx) / max(1e-6, math.hypot(x - tx, y - ty)) * 700, ty + (y - ty) / max(1e-6, math.hypot(x - tx, y - ty)) * 700)
         for x, y in spine]


class Road:
    """a polyline with arclength; plots hang off it"""
    def __init__(self, pts, name):
        self.pts = pts
        self.name = name
        self.s = [0.0]
        for a, b in zip(pts[:-1], pts[1:]):
            self.s.append(self.s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.s[-1]
        self.taken = {+1: [], -1: []}          # (s0, s1) intervals per side

    def point(self, s):
        s = min(max(s, 0), self.length)
        k = max(0, min(len(self.s) - 2, int(np.searchsorted(self.s, s) - 1)))
        t = (s - self.s[k]) / max(1e-6, self.s[k + 1] - self.s[k])
        a, b = self.pts[k], self.pts[k + 1]
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = max(1e-6, math.hypot(dx, dy))
        return x, y, dx / L, dy / L

    def free(self, side, s0, s1):
        return all(s1 <= a or s0 >= b for a, b in self.taken[side])


SPINE = Road(spine, "spine")
ROADS = [SPINE]


def branches_to_room(max_branches=2):
    """side roads from the spine toward the roomiest flats within 320 m of it (the works get room), least-cost"""
    sp = np.array(SPINE.pts)
    dsp = np.full((N, N), np.inf)
    for x, y in sp[::3]:
        dsp = np.minimum(dsp, np.hypot(WX - x, WY - y) / M)
    cand = np.where(MAIN & (dsp > 70) & (dsp < 320) & (D_WATER > 30), ROOM, -1)
    made = 0
    for _ in range(max_branches):
        j, i = np.unravel_index(int(cand.argmax()), cand.shape)
        if cand[j, i] < 0.45:
            break
        target = cell_to_world(i + 0.5, j + 0.5)
        k = int(np.argmin([math.hypot(x - target[0], y - target[1]) for x, y in SPINE.pts]))
        start = SPINE.pts[k]
        cells_b = path(start, target)
        if len(cells_b) > 3:
            pts = chaikin([cell_to_world(ci + 0.5, cj + 0.5) for ci, cj in cells_b], 1)
            pts[0] = start
            ROADS.append(Road(pts, "branch%d" % len(ROADS)))
            s_k = SPINE.s[k]
            for side in (+1, -1):
                SPINE.taken[side].append((s_k - 14 * M, s_k + 14 * M))     # the junction stays open
            made += 1
        cand = np.where(np.hypot(WX - target[0], WY - target[1]) / M < 220, -1, cand)
    return made


N_BRANCH = branches_to_room()
S_DOCK = 0.0
S_TOWER = SPINE.s[int(np.argmin([math.hypot(x - tx, y - ty) for x, y in SPINE.pts]))]     # where the road passes the tower
S_MINE = SPINE.length
# where along the spine is the works stretch: the flattest, roomiest 40 % between dock and tower
placed = {}
PLOTS = []
FENCES = []


def place(bid, x, y, yaw, plot=None):
    b = buildings[bid]
    r = max(b["size"][0], b["size"][1]) * M * 0.6
    fi, fj = world_to_cell(x, y)
    rc = r / CELL
    cells_ = [(i, j) for j in range(max(0, int(fj - rc)), min(N, int(fj + rc) + 2))
              for i in range(max(0, int(fi - rc)), min(N, int(fi + rc) + 2))
              if (i + 0.5 - fi) ** 2 + (j + 0.5 - fj) ** 2 <= (rc + 0.5) ** 2]
    placed[bid] = dict(x=float(x), y=float(y), yaw=float(yaw), r=float(r), kind=b["kind"], cells=cells_, z=zb(x, y), plot=plot)


def footprint_m(b):
    wdt, dpt = b["size"][0], b["size"][1]
    spec = b.get("count", "1").split()
    gap = max(wdt, dpt) * 1.5
    if spec[0].lower() == "2x2":
        return wdt + gap, dpt + gap
    if len(spec) == 2:
        n = int(spec[0])
        return (wdt + (n - 1) * gap, dpt) if spec[1] == "along" else (wdt, dpt + (n - 1) * gap)
    return wdt, dpt


# --- 3. anchors and the water things -----------------------------------------------------------------------------
for bid, b in buildings.items():
    if "at" in b and (bid in ANCHORS or b.get("anchor", "no").lower() == "yes"):
        along, across, deg = b["at"]
        a = math.radians(LOOK)
        ox, oy = ((along - buildings["tower"]["at"][0]) * math.cos(a) - (across - buildings["tower"]["at"][1]) * math.sin(a),
                  (along - buildings["tower"]["at"][0]) * math.sin(a) + (across - buildings["tower"]["at"][1]) * math.cos(a))
        place(bid, tx + ox, ty + oy, deg)

# the dock: at the dock site, reaching into the sea (yaw = toward the water)
gyw, gxw = np.gradient(D_WATER)
dock_yaw = math.degrees(math.atan2(-at(gyw, *DOCK), -at(gxw, *DOCK)))
if "dock" in buildings:
    L_dock = buildings["dock"]["size"][0] * M
    dx, dy = math.cos(math.radians(dock_yaw)), math.sin(math.radians(dock_yaw))
    place("dock", DOCK[0] + dx * L_dock * 0.35, DOCK[1] + dy * L_dock * 0.35, dock_yaw)


def water_site(bid, dmin, dmax, near=None, near_max=None, in_window=False):
    cand = np.nonzero(WATER & (DEPTH > 2.5) & (D_LAND > dmin) & (D_LAND < dmax))
    pts = list(zip(cand[1], cand[0]))
    if near is not None:
        pts = [(i, j) for i, j in pts if math.hypot(WX[j, i] - near[0], WY[j, i] - near[1]) / M < near_max] or pts
    if not pts:
        return None
    # never in the window's way (the tower looks at the works, the rig stands off to a side)
    def off_window(p):
        return abs(((math.degrees(math.atan2(WY[p[1], p[0]] - ty, WX[p[1], p[0]] - tx)) - LOOK + 180) % 360) - 180)
    # rigs stay out of the window's way; far scenery stands IN it (the horizon the command room looks at)
    pts.sort(key=lambda p: (off_window(p) if in_window else -off_window(p)) * rng.uniform(0.5, 1.0))
    i, j = pts[0] if rng.random() < 0.7 else pts[int(rng.integers(min(len(pts), 6)))]
    return cell_to_world(i + rng.uniform(0.2, 0.8), j + rng.uniform(0.2, 0.8))


for bid, b in buildings.items():
    if bid in placed or "at" not in b:
        continue
    if b["kind"] == "rig" and not bid.startswith("wellhead"):
        p = water_site(bid, 150, 700, DOCK, 1500)
        if p: place(bid, p[0], p[1], rng.uniform(0, 360))
    elif b["kind"] == "barge":
        p = water_site(bid, 15, 120, DOCK, 400)
        if p: place(bid, p[0], p[1], dock_yaw + rng.uniform(-30, 30))
    elif b["kind"] == "wreck":
        p = water_site(bid, 30, 250)
        if p: place(bid, p[0], p[1], rng.uniform(0, 360))
    elif b["kind"] == "islet":                                      # far scenery: out at sea, deep, far from land
        p = water_site(bid, 450, 2000, in_window=True)
        if p: place(bid, p[0], p[1], rng.uniform(0, 360))

# --- 4. plots along the roads, in binder layer order, providers before consumers --------------------------------
LAYERS = {"core": 0, "boom": 1, "decline": 2}
PRIORITY = ["plant_office", "hall_a", "hall_b", "hall_c", "silos", "generator_house", "tank_farm", "dorm", "cooling_towers"]
order = [bid for bid in buildings if "at" in buildings[bid] and bid not in placed]
order.sort(key=lambda i: (LAYERS.get(buildings[i].get("layer", "boom"), 1), PRIORITY.index(i) if i in PRIORITY else 99, i))
ordered, pending = [], list(order)
while pending:
    prog = False
    for i in list(pending):
        need = SPEC[i][1]
        prov = [j for j in pending if j != i and any(r in SPEC[j][0] for r in need)
                and LAYERS.get(buildings[j].get("layer", "boom"), 1) <= LAYERS.get(buildings[i].get("layer", "boom"), 1)
                and not any(r in SPEC[i][0] for r in SPEC[j][1])]
        if not prov:
            ordered.append(i); pending.remove(i); prog = True
    if not prog:
        ordered.append(pending.pop(0))

# stretch preferences along the spine (fractions of S_TOWER = the dock->tower leg; > 1 = beyond the tower)
STRETCH = {
    "office": (0.05, 0.5), "pad": (0.1, 0.8), "hall": (0.15, 1.3), "silo": (0.1, 1.2), "tank": (0.2, 1.3),
    "cooling": (0.2, 1.3), "pump": (0.0, 1.4), "dorm": (0.45, 1.5), "house": (0.5, 1.9), "mast": (0.3, 1.9),
    "jetty": (0.0, 0.3),
}
SIDE = {"hall": -1, "tank": -1, "silo": -1, "cooling": -1, "pump": -1, "pad": -1,       # sea side: the works
        "dorm": +1, "house": +1, "office": +1, "mast": +1}                                 # hill side: people


def sea_side(road, s):
    x, y, ux, uy = road.point(s)
    left = (x - uy * 400, y + ux * 400)
    right = (x + uy * 400, y - ux * 400)
    return +1 if at(D_WATER, *left) < at(D_WATER, *right) else -1      # +1 = left is the sea side


def plot_ok(road, s0, s1, side, depth_u, max_slope=20.0):
    """every corner and the centre on the main landmass, dry, and not too steep"""
    for s in np.linspace(s0, s1, 4):
        x, y, ux, uy = road.point(s)
        nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
        for d in (ROAD_HALF_M * M + SETBACK_M * M, ROAD_HALF_M * M + SETBACK_M * M + depth_u):
            px, py = x + nx * d, y + ny * d
            if at(WATER, px, py, 1) or not at(MAIN, px, py, 0) or at(SLOPE, px, py, 90) > max_slope:
                return False
    return True


def try_place(bid, b):
    wdt_m, dpt_m = footprint_m(b)
    front = wdt_m + GAP_M
    kind = b["kind"]
    lo, hi = STRETCH.get(kind, (0.0, 1.4))
    if bid.startswith("wellhead"):                                   # the mine end of the road
        lo, hi = (S_MINE - 260 * M) / max(1.0, S_TOWER), S_MINE / max(1.0, S_TOWER)
    want_side = SIDE.get(kind, 0)
    max_slope = 32.0 if (bid.startswith("wellhead") or kind in ("mast",)) else 20.0
    best = None
    for road in ROADS:
        smax = road.length
        for s0 in np.arange(0, smax - front * M, 5 * M):
            s1 = s0 + front * M
            frac = s0 / max(1.0, S_TOWER) if road is SPINE else 0.5
            if road is SPINE and not (lo <= frac <= hi):
                continue
            for side in (+1, -1):
                if not road.free(side, s0, s1) or not plot_ok(road, s0, s1, side, dpt_m * M, max_slope):
                    continue
                x, y, ux, uy = road.point((s0 + s1) / 2)
                nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
                d = ROAD_HALF_M * M + SETBACK_M * M + dpt_m * M / 2
                cx, cy = x + nx * d, y + ny * d
                score = 1.0
                # the sea side for the works, the hill side for people
                ss = sea_side(road, (s0 + s1) / 2)
                if want_side:
                    score += 0.8 if (side == ss) == (want_side < 0) else -0.3
                # systems: every need pulls toward a placed provider within reach
                for res in sorted(SPEC[bid][1]):
                    reach = systems.RES[res][1]
                    pts = [(p["x"], p["y"]) for pid, p in placed.items() if res in SPEC[pid][0]]
                    if pts:
                        dm = min(math.hypot(px - cx, py - cy) for px, py in pts) / M
                        score += (1.0 if res in systems.CORE else 0.5) * (1.2 - min(dm / reach, 1.5))
                # avoid: dorms and houses away from cooling/tanks; everything away from the dock's own stretch
                if kind in ("dorm", "house"):
                    for pid in ("cooling_towers", "tank_farm", "fuel_depot"):
                        if pid in placed:
                            dm = math.hypot(placed[pid]["x"] - cx, placed[pid]["y"] - cy) / M
                            score -= max(0, 1 - dm / 150)
                if kind == "house" and bid == "directors_house":
                    score += 1.5 * (zb(cx, cy) - SEA_Z) / 4000.0            # the view
                if VIS is not None:                                          # the camera: seen ground is worth more
                    score += CAMERA_K * camera_weight(bid, buildings[bid]) * at(VIS, cx, cy)
                score += rng.uniform(0, 0.15)
                if best is None or score > best[0]:
                    best = (score, road, s0, s1, side, cx, cy, ux, uy, nx, ny)
    if best is None:
        return False
    score, road, s0, s1, side, cx, cy, ux, uy, nx, ny = best
    road.taken[side].append((s0, s1))
    yaw = math.degrees(math.atan2(-ny, -nx))                                   # the front faces the road
    place(bid, cx, cy, yaw, plot=dict(road=road.name, s0=s0, s1=s1, side=side))
    PLOTS.append(dict(id=bid, road=road.name, s0=round(s0), s1=round(s1), side=side,
                      corners=[[round(v) for v in (road.point(s0)[0] + nx * (ROAD_HALF_M + SETBACK_M) * M, road.point(s0)[1] + ny * (ROAD_HALF_M + SETBACK_M) * M)],
                               [round(v) for v in (road.point(s1)[0] + nx * (ROAD_HALF_M + SETBACK_M) * M, road.point(s1)[1] + ny * (ROAD_HALF_M + SETBACK_M) * M)]]))
    return True


def add_branch(bid):
    """no plot left on the spine: a side road from the roomiest free spine point on the works stretch"""
    best = None
    for s in np.arange(0.1 * S_TOWER, 0.9 * S_TOWER, 5 * M):
        x, y, ux, uy = SPINE.point(s)
        for side in (+1, -1):
            nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
            end = (x + nx * 140 * M, y + ny * 140 * M)
            if at(WATER, *end, 1) or not at(MAIN, *end, 0):
                continue
            r = at(ROOM, end[0] - nx * 70 * M, end[1] - ny * 70 * M)
            if best is None or r > best[0]:
                best = (r, s, side, x, y, nx, ny)
    if best is None:
        return False
    r, s, side, x, y, nx, ny = best
    pts = [(x + nx * (ROAD_HALF_M * M + d), y + ny * (ROAD_HALF_M * M + d)) for d in np.linspace(0, 140 * M, 6)]
    br = Road(pts, "branch%d" % len(ROADS))
    SPINE.taken[side].append((s - 12 * M, s + 12 * M))
    ROADS.append(br)
    return True


for bid in ordered:
    b = buildings[bid]
    if b["kind"] in ("dock",) or bid in placed:
        continue
    ok = try_place(bid, b)
    if not ok and add_branch(bid):
        ok = try_place(bid, b)
    if not ok:
        print("  no plot for", bid, file=sys.stderr)

# --- 5. fences in the gaps between neighbouring plots on the same side of a road ---------------------------------
for road in ROADS:
    for side in (+1, -1):
        iv = sorted(road.taken[side])
        for (a0, a1), (b0, b1) in zip(iv[:-1], iv[1:]):
            if 0 < b0 - a1 < 60 * M:
                for s in (a1, b0):
                    x, y, ux, uy = road.point(s)
                    nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
                    d0, d1 = (ROAD_HALF_M + SETBACK_M) * M, (ROAD_HALF_M + SETBACK_M + 22) * M
                    FENCES.append([[round(x + nx * d0), round(y + ny * d0)], [round(x + nx * d1), round(y + ny * d1)]])
                # and the front line between the two plots
                xa, ya, _, _ = road.point(a1)
                xb, yb, ux, uy = road.point(b0)
                nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
                d0 = (ROAD_HALF_M + SETBACK_M) * M
                FENCES.append([[round(xa + nx * d0), round(ya + ny * d0)], [round(xb + nx * d0), round(yb + ny * d0)]])

# --- output ------------------------------------------------------------------------------------------------------
roads_out = [[[round(x, 1), round(y, 1)] for x, y in r.pts] for r in ROADS]
out = {"seed": SEED, "shift": -5300, "heightmap": os.path.abspath(src), "method": "spine",
       "buildings": {bid: {"x": round(p["x"], 1), "y": round(p["y"], 1), "yaw": round(p["yaw"], 1), "z": round(p["z"], 1),
                           "interest": 1.0, "cells": [list(c) for c in p["cells"]]} for bid, p in placed.items()},
       "roads": roads_out, "spine": roads_out[0], "plots": PLOTS, "fences": FENCES,
       "sites": {"dock": [round(v) for v in DOCK], "mine": [round(v) for v in MINE], "tower": list(TOWER_WORLD)}}
json.dump(out, open(dst, "w"), indent=0)
print(f"spine {SPINE.length / M:.0f} m, {len(ROADS) - 1} branches, {len(PLOTS)} plots, {len(placed)} buildings placed, {len(FENCES)} fence runs -> {dst}")

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
    for r in ROADS:
        dr.line([P(x, y) for x, y in r.pts], fill=(90, 70, 50), width=4)
    for f in FENCES:
        dr.line([P(*f[0]), P(*f[1])], fill=(230, 230, 230), width=1)
    for bid, p in placed.items():
        cx, cy = P(p["x"], p["y"])
        rr = max(3, p["r"] / CELL * S)
        col = (230, 60, 60) if bid in ANCHORS else ((80, 200, 255) if p["kind"] in ("rig", "barge", "wreck", "dock", "jetty") and not bid.startswith("wellhead") else (240, 220, 80))
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=2)
        a = math.radians(p["yaw"])
        dr.line([(cx, cy), (cx + rr * 1.6 * math.cos(a), cy - rr * 1.6 * math.sin(a))], fill=col, width=2)
        dr.text((cx + rr + 2, cy - 6), bid, fill=(255, 255, 255))
    for nm, pt in (("DOCK", DOCK), ("MINE", MINE)):
        dr.text(P(*pt), nm, fill=(255, 128, 255))
    img.save(PNG)
