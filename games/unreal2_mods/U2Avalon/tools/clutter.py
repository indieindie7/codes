r"""Clutter and vegetation: the glue between the buildings. Reads the final heightmap and the layout (roads,
connections, footprints) and writes StaticMeshActors (T3D) from the game's own packages:

    py tools/clutter.py <final heightmap.bmp> <layout.json> <out.t3d> [seed=1] [trees=1.0] [rocks=1.0]

  * lamp posts along the trunk roads every ~60 m on the verge (Mission_03M.RecievingPad.LampPost01)
  * crates and pallets within the yards, on the bay side of halls and at the dock; barrels at the fuel depot,
    the tank farm and the generator house (Terran_DecoM)
  * fence runs along the yard edge of the core plant, facing the road (Mission_03M.Izanagi fence segments)
  * rocks on steep ground and ridges (Mission_03M.M03A1.Rock*), bigger ones higher up
  * trees on gentle grassy ground away from the town, in clumps (Flora_M.Tree.*), none on sand or rock
Everything stands on the ground (bilinear height) with a random yaw; density scales with trees= / rocks=.
"""
import json, math, os, struct, sys

import numpy as np

src, layout, out = sys.argv[1:4]
o = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)
BEFORE = o.get("before")           # the heightmap before the pads were cut: terrace rims get retaining walls
SEED = int(o.get("seed", 1))
TREES, ROCKS = float(o.get("trees", 1.0)), float(o.get("rocks", 1.0))
rng = np.random.default_rng(SEED)
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, M, N = 512.0, 50.0, 128
SEA_Z = -4967.0

LAMP = "Mission_03M.RecievingPad.LampPost01"
CRATES = ["Terran_DecoM.Crates.Crate1Low", "Terran_DecoM.Crates.Crate1Medium", "Terran_DecoM.Crates.crate_pallet_01"]
BARRELS = ["Terran_DecoM.Barrels.Metal_Barrel_01", "Terran_DecoM.Barrels.Metal_Barrel_Broken_01"]
FENCE_LONG, FENCE_LEN = "Mission_03M.Izanagi.Izanagi_Fence_long", 422.0
ROCKS_SMALL = ["Mission_03M.M03A1.Rock04", "Mission_03M.M03A1.Rock05", "Mission_03M.M03A1.Rock12"]
ROCKS_BIG = ["Mission_03M.M03A1.Rock01", "Mission_03M.M03A1.Rock02", "Mission_03M.M03A1.Rock03"]
TREES_M = ["Flora_M.Tree.Tree3", "Flora_M.Tree.Tree1_clump1"]

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * 0.5
gy, gx = np.gradient(Z / M, CELL / M)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
WATER = Z <= SEA_Z
J, I = np.mgrid[0:N, 0:N]
WX = LOC[0] + (I - N / 2) * CELL
WY = LOC[1] + (J - N / 2) * CELL


def ground(x, y):
    fi, fj = (x - LOC[0]) / CELL + N / 2, (y - LOC[1]) / CELL + N / 2
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return None
    ti, tj = fi - i0, fj - j0
    return (Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)


L = json.load(open(layout))
B = L["buildings"]
actors = []


# draw distances (Actor.CullDistance, units): small props vanish first, trees and terrace walls stay longest.
# Without them every crate, rock and tree on the island was drawn every frame and the game crawled.
CULL = (("Tree", 14000), ("B_wall", 14000), ("LampPost", 9000), ("Fence", 8000), ("Rock", 8000),
        ("Crate", 5000), ("crate", 5000), ("Barrel", 4500))


def cull_of(mesh):
    return next((d for k, d in CULL if k in mesh), 8000)


def actor(mesh, x, y, yaw_deg, scale=1.0, lift=0.0):
    z = ground(x, y)
    if z is None or z <= SEA_Z + 20:
        return
    actors.append("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n"
                  "    Rotation=(Yaw=%d)\n    DrawScale=%.3f\n    CullDistance=%d\n    bStatic=True\nEnd Actor"
                  % (mesh, x, y, z + lift, int(yaw_deg * 65536 / 360) % 65536, scale, cull_of(mesh)))


def near_building(x, y, r_units):
    return any(math.hypot(b["x"] - x, b["y"] - y) < r_units for b in B.values())


# distance fields (cells) to roads and footprints, for the vegetation masks
def seg_dist(ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = np.clip(((WX - ax) * vx + (WY - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
    return np.hypot(WX - (ax + t * vx), WY - (ay + t * vy)) / CELL


droad = np.full((N, N), np.inf)
roads = L.get("roads", [])
for r in roads:
    for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
        droad = np.minimum(droad, seg_dist(ax, ay, bx, by))
for wk in L.get("walks", []):                    # the worn foot paths (walks.py) stay clear like roads
    p = wk.get("path") or []
    for (ax, ay), (bx, by) in zip(p[:-1], p[1:]):
        droad = np.minimum(droad, seg_dist(ax, ay, bx, by) + 0.4)
dbld = np.full((N, N), np.inf)
for bid, b in B.items():
    dbld = np.minimum(dbld, np.hypot(WX - b["x"], WY - b["y"]) / CELL)

# 0. the road surface: B_road slabs (10 m, pivot at the bottom of the gravel shoulders, 0.43 m to the asphalt
#    top) every ~8 m along every road, aimed along it and pitched to the graded ground, stretched to the spacing
ROAD = o.get("road", "AvalonSM.Liandri.B_road")
n_road = 0
if ROAD:
    seen = set()
    for r in roads:
        pts = []
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            seg = math.hypot(bx - ax, by - ay)
            n = max(1, int(seg // 400))
            pts += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
        pts.append(tuple(r[-1]))
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            key = (round((x0 + x1) / 300), round((y0 + y1) / 300))
            if key in seen:                              # shared stretches (branch junctions) once
                continue
            seen.add(key)
            g0, g1 = ground(x0, y0), ground(x1, y1)
            seg = math.hypot(x1 - x0, y1 - y0)
            if g0 is None or g1 is None or seg < 50 or min(g0, g1) <= SEA_Z + 30:
                continue
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            yaw = math.degrees(math.atan2(y1 - y0, x1 - x0))
            pitch = math.degrees(math.atan2(g1 - g0, seg))
            actors.append("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n"
                          "    Rotation=(Pitch=%d,Yaw=%d)\n    DrawScale3D=(X=%.3f,Y=1,Z=1)\n    CullDistance=20000\n    bStatic=True\nEnd Actor"
                          % (ROAD, mx, my, (g0 + g1) / 2 - 15, int(pitch * 65536 / 360) % 65536, int(yaw * 65536 / 360) % 65536, seg / 500 * 1.04))
            n_road += 1

# 1. lamps along the longest roads (the trunk), every ~60 m, on the right-hand verge
roads_sorted = sorted(roads, key=lambda r: -sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(r[:-1], r[1:])))
n_lamps = 0
for r in roads_sorted[:4]:
    acc = 0.0
    for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
        seg = math.hypot(bx - ax, by - ay)
        if seg < 1:
            continue
        ux, uy = (bx - ax) / seg, (by - ay) / seg
        while acc < seg:
            x, y = ax + ux * acc, ay + uy * acc
            actor(LAMP, x + uy * 230, y - ux * 230, math.degrees(math.atan2(uy, ux)) + 90, 1.0)
            n_lamps += 1
            acc += 60 * M
        acc -= seg

# 2. crates, pallets, barrels in the yards
n_crates = 0
for bid, b in B.items():
    kind = b.get("kind", "")
    yaw = math.radians(b["yaw"])
    fx, fy = math.cos(yaw), math.sin(yaw)              # the front: toward the road
    if bid.startswith("hall") or kind in ("dock", "pad") or bid in ("shed_a", "shed_b", "cargo_pad", "plant_office"):
        for k in range(int(rng.integers(3, 7))):
            d = rng.uniform(160, 420)
            side = rng.uniform(-1, 1) * 420
            x, y = b["x"] + fx * d - fy * side, b["y"] + fy * d + fx * side
            actor(CRATES[int(rng.integers(len(CRATES)))], x, y, b["yaw"] + rng.uniform(-20, 20), rng.uniform(0.9, 1.3))
            n_crates += 1
    if bid in ("fuel_depot", "tank_farm", "generator_house", "pump_house"):
        for k in range(int(rng.integers(4, 9))):
            ang = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(220, 480)
            actor(BARRELS[int(rng.integers(len(BARRELS)))], b["x"] + d * math.cos(ang), b["y"] + d * math.sin(ang), rng.uniform(0, 360), 1.0)
            n_crates += 1

# 3. fence runs: the spine layout gives the gaps between plots; otherwise along each core building's front
n_fence = 0
for f in L.get("fences", []):
    (x0, y0), (x1, y1) = f
    Lf = math.hypot(x1 - x0, y1 - y0)
    n = int(Lf // FENCE_LEN)
    for k in range(n):
        t = (k + 0.5) / n
        actor(FENCE_LONG, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, math.degrees(math.atan2(y1 - y0, x1 - x0)), 1.0)
        n_fence += 1
for bid, b in ([] if L.get("fences") else B.items()):
    if bid.startswith("hall") or bid in ("tank_farm", "fuel_depot", "silos"):
        yaw = math.radians(b["yaw"])
        fx, fy = math.cos(yaw), math.sin(yaw)
        d = 560                                          # just outside the yard, parallel to the front
        n = int(rng.integers(2, 5))
        start = -n / 2 * FENCE_LEN
        for k in range(n):
            s = start + (k + 0.5) * FENCE_LEN
            x, y = b["x"] + fx * d - fy * s, b["y"] + fy * d + fx * s
            if rng.random() < 0.85:                      # a missing segment now and then: a gate or a gap
                actor(FENCE_LONG, x, y, b["yaw"] + 90, 1.0)
                n_fence += 1

# 4. rocks on steep ground, 5. trees on gentle green ground away from the town
land = (~WATER) & (dbld > 2.0) & (droad > 1.2)
steep = land & (SLOPE > 18)
gentle = land & (SLOPE < 14) & (dbld > 3.0)
height_t = np.clip((Z - SEA_Z) / 4500.0, 0, 1)
n_rocks = n_trees = 0
for j, i in zip(*np.nonzero(steep)):
    if rng.random() < 0.10 * ROCKS:
        big = rng.random() < 0.35 + 0.4 * height_t[j, i]
        mesh = (ROCKS_BIG if big else ROCKS_SMALL)[int(rng.integers(3))]
        actor(mesh, WX[j, i] + rng.uniform(-200, 200), WY[j, i] + rng.uniform(-200, 200), rng.uniform(0, 360),
              rng.uniform(0.6, 1.1) if big else rng.uniform(0.8, 1.6), lift=-30)
        n_rocks += 1
# trees: clump centres on gentle ground, 2-5 trees each (fewer than the first pass: frame rate)
cand = list(zip(*np.nonzero(gentle)))
rng.shuffle(cand)
for j, i in cand[:min(60, int(len(cand) * 0.03 * TREES))]:
    cx, cy = WX[j, i], WY[j, i]
    for k in range(int(rng.integers(2, 6))):
        ang, d = rng.uniform(0, 2 * math.pi), rng.uniform(0, 420)
        x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
        if near_building(x, y, 900):
            continue
        actor(TREES_M[int(rng.integers(len(TREES_M)))], x, y, rng.uniform(0, 360), rng.uniform(0.8, 1.35), lift=-10)
        n_trees += 1

# 6. retaining walls: where the pads changed the ground by more than 1.5 m, a wall band along the rim on the
#    cut/fill side (the plinth or terrace wall every slope-site strategy draws as a visible band)
n_walls = 0
WALL = o.get("wall", "AvalonSM.Liandri.B_wall")   # our own part: 512 u long (one cell), 2.2 m high, origin bottom centre, long axis = Y at yaw 0
if WALL and BEFORE and os.path.exists(BEFORE):
    rawb = open(BEFORE, "rb").read()
    offb = struct.unpack_from("<I", rawb, 10)[0]
    wb, hb = struct.unpack_from("<ii", rawb, 18)
    Hb = np.frombuffer(rawb[offb:offb + wb * abs(hb) * 2], dtype="<u2").reshape(abs(hb), wb).astype(float)
    if hb > 0:
        Hb = Hb[::-1]
    Zb = LOC[2] + (Hb - 32768) * 0.5
    dZ = Z - Zb                                        # + = fill, - = cut
    changed = np.abs(dZ) > 130                        # rims of 2.6 m and more get a wall; smaller steps stay earth
    # the wall stands where the FLAT pad meets the drop: a flat cell (slope < 6 deg) whose 4-neighbour is steep
    # (slope > 16 deg); it faces the neighbour, its foot on the lower of the two, its height the step
    flat = (SLOPE < 9.0) & changed
    for j in range(1, N - 1):
        for i in range(1, N - 1):
            if not flat[j, i] or WATER[j, i]:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nj, ni = j + dj, i + di
                # the neighbour is the drop when the ground steps more than 2 m across the one cell edge and that
                # neighbour is not part of the same flat pad (the gradient-based slope is too smooth at 10 m cells)
                step = abs(Z[j, i] - Z[nj, ni])
                if step >= 100 and not WATER[nj, ni] and not (changed[nj, ni] and abs(Z[nj, ni] - Z[j, i]) < 40):
                    x = WX[j, i] + di * CELL * 0.5
                    y = WY[j, i] + dj * CELL * 0.5
                    yawd = 0 if di else 90
                    hgt = min(step, 400)
                    actors.append("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n"
                                  "    Rotation=(Yaw=%d)\n    DrawScale3D=(X=1,Y=1,Z=%.3f)\n    CullDistance=%d\n    bStatic=True\nEnd Actor"
                                  % (WALL, x, y, min(Z[j, i], Z[nj, ni]) - 10, int(yawd * 65536 / 360), max(0.6, hgt / 110.0), cull_of(WALL)))
                    n_walls += 1
open(out, "w").write("Begin Map\n" + "\n".join(actors) + "\nEnd Map\n")
print(f"clutter: {n_road} road slabs, {n_lamps} lamps, {n_crates} crates/barrels, {n_fence} fence runs, {n_rocks} rocks, {n_trees} trees, {n_walls} wall pieces -> {out}")
