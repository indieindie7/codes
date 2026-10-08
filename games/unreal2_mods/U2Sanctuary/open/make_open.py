r"""Sanctuary Open, phase 1: the drivable blockout of the whole of Sanctuary in one map (site.py is the plan).

    py make_open.py            -> <game>\U2SanctuaryOpen\Models\ase\Ground*.ase, Basin.ase, open_actors.t3d
    py build_open.py assets    -> StaticMeshes\SanctuaryOpenSM.usx (+ the big room brush)
    py build_open.py map       -> Maps\PrairieSanctuary.un2 ("Prairie*": U2Hover's mutator gives the Manta)

THE LAND IS REAL: Serra dos Carajas (the N4 mine, Amazon), Copernicus GLO-30 (fetch_dem.py; credit "Copernicus
DEM GLO-30, (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by
the European Union and ESA"), 6.6 km onto the map, heights at VSCALE UU per metre.

Forked from U2Prairie/make_prairie.py (static-mesh terrain tiles in a -30720..30720 room, the Sanctuary skybox),
with the land shaped by the site plan instead of one trail:
  - gentle swells and jungle hills; the rim rises toward the walls to hide them
  - every place flattened to its pad (the plant and the power plant a little raised, the shaft head too)
  - the mine pit: a terraced bowl 1800 deep, benches every 300
  - the runoff basin: a sunken pool by the plant, with a water surface
  - the roads: a bed eased to a smoothed, grade-capped profile (the Manta climbs 25 % comfortably), then the
    terrain blended to it over a shoulder
  - the jungle: Sanctuary's own JungleM trees and plants (the shipped maps' kit) dense off the roads and away from
    the places, thinning to stumps on the cleared field, none in the pit
  - landmarks from the Mission_08M / Terran kits: the plant's comm tower (the weenie seen from the LZ), its tanks
    and superstructure, the power plant's stacks, pad lights; scales are first guesses for the review pass
"""
import json, math, os, random, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(GAME, "U2SanctuaryOpen")
sys.path.insert(0, os.path.join(GAME, "U2Hover"))
sys.path.insert(0, HERE)
from make_map import write_ase, tri_facing, actor, NO_COLLISION, ROCKS  # noqa
import plan as S  # noqa
import playable  # noqa

WORLD = S.WORLD
N = 240
TILES = 8
STEP = 2 * WORLD / N
FLOOR_Z = -3900
SKY_Z = 12000
UV_TILE = 1024.0
GRADE = 0.25
random.seed(8)

xs = np.linspace(-WORLD, WORLD, N + 1)
X, Y = np.meshgrid(xs, xs)          # H[j, i] at (xs[i], xs[j])


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


DEM = r"C:\Users\john\Documents\U2_research\sanctuary\dem\carajas_n4.npy"     # fetch_dem.py -6.00 -6.14 -50.24 -50.10
DEM_BOX = (-6.00, -6.14, -50.24, -50.10)            # what the .npy covers (lat N, lat S, lon W, lon E)
WINDOW = (-6.025, -6.095, -50.225, -50.155)         # the 6.6 km of Carajas on the map (plan.py)
VSCALE = 6.0                                        # UU per real metre of height (horizontal is ~9.3: relief a bit flattened)


def base():
    """the real land: Carajas N4 (Copernicus GLO-30), resampled to the grid, plus a little high-frequency swell"""
    Z = np.load(DEM)
    H0, W0 = Z.shape
    n, s_, w, e = DEM_BOX
    wn, ws, ww, we = WINDOW
    # grid x (east) -> lon, grid y (south, plan's +y) -> lat
    lon = ww + (X + WORLD) / (2 * WORLD) * (we - ww)
    lat = wn + (Y + WORLD) / (2 * WORLD) * (ws - wn)
    fi = (lon - w) / (e - w) * (W0 - 1)
    fj = (n - lat) / (n - s_) * (H0 - 1)
    i0, j0 = np.clip(np.floor(fi).astype(int), 0, W0 - 2), np.clip(np.floor(fj).astype(int), 0, H0 - 2)
    tx, ty = fi - i0, fj - j0
    z = (Z[j0, i0] * (1 - tx) * (1 - ty) + Z[j0, i0 + 1] * tx * (1 - ty) + Z[j0 + 1, i0] * (1 - tx) * ty + Z[j0 + 1, i0 + 1] * tx * ty)
    # the DSM carries the forest canopy: a light blur takes its texture off
    k = np.ones(5) / 5
    z = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 2, mode="edge"), k, mode="valid"), 1, z)
    z = np.apply_along_axis(lambda c: np.convolve(np.pad(c, 2, mode="edge"), k, mode="valid"), 0, z)
    h = (z - z.min()) * VSCALE
    rng = np.random.default_rng(8)
    for _ in range(60):
        cx, cy = rng.uniform(-WORLD, WORLD, 2)
        r, a = rng.uniform(900, 2400), rng.uniform(20, 90)
        h += a * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (r * r))
    return h


def shape(h):
    for q in S.PLACES:
        if not q["r"] or q["id"] in ("pit", "basin", "shaft"):          # (the shaft is inside the generator building)
            continue
        d = np.hypot(X - q["x"], Y - q["y"])
        f = 1 - smooth((d - q["r"] * 0.7) / (q["r"] * 0.6))
        pad = float(np.median(h[d < q["r"] * 0.7])) + q["z"]          # the real ground's middle height there
        h = h * (1 - f) + f * pad
    # the pit: a terraced bowl
    p = next(q for q in S.PLACES if q["id"] == "pit")
    d = np.hypot(X - p["x"], Y - p["y"])
    t = 1 - smooth(d / p["r"])
    depth = 1800 * t
    bench = np.floor(depth / 300) * 300 + 300 * smooth((depth % 300 - 220) / 80)
    rimz = float(h[np.unravel_index(np.argmin(np.abs(d - p["r"])), d.shape)])
    inside = d < p["r"]
    h = np.where(inside, np.minimum(h, rimz) - bench, h)
    # the runoff basin: a settling pond goes where the water goes - the lowest valley head 3-8 km... (3000-8000 UU)
    # from the plant; the plan's spot is only the first guess
    b = next(q for q in S.PLACES if q["id"] == "basin")
    pl = next(q for q in S.PLACES if q["id"] == "plant")
    dp = np.hypot(X - pl["x"], Y - pl["y"])
    ring = (dp > 3000) & (dp < 8000)
    jj, ii = np.unravel_index(np.argmin(np.where(ring, h, 1e9)), h.shape)
    b["x"], b["y"] = float(xs[ii]), float(xs[jj])
    d = np.hypot(X - b["x"], Y - b["y"])
    f = 1 - smooth((d - b["r"] * 0.8) / (b["r"] * 0.35))
    h = h * (1 - f) + f * (h - 420)
    return h


def road_lines():
    out = []
    for r in S.ROADS:
        pts = [S.where(p) for p in r["pts"]]
        # Catmull-Rom through the points, every ~200 UU
        P = []
        for i in range(len(pts) - 1):
            p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
            n = max(2, int(math.dist(p1, p2) / 200))
            for k in range(n):
                u = k / n
                P.append(tuple(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
                               for a, b, c, d in zip(p0, p1, p2, p3)))
        P.append(pts[-1])
        out.append((r, np.array(P)))
    return out


def sample(h, x, y):
    fi, fj = (x + WORLD) / STEP, (y + WORLD) / STEP
    i0, j0 = int(np.clip(np.floor(fi), 0, N - 1)), int(np.clip(np.floor(fj), 0, N - 1))
    tx, ty = fi - i0, fj - j0
    return (h[j0, i0] * (1 - tx) * (1 - ty) + h[j0, i0 + 1] * tx * (1 - ty) + h[j0 + 1, i0] * (1 - tx) * ty + h[j0 + 1, i0 + 1] * tx * ty)


def roads(h):
    lines = road_lines()
    best = np.full(X.shape, 1e9)
    target = np.zeros_like(X)
    width = np.zeros_like(X)
    for r, P in lines:
        z = np.array([sample(h, x, y) for x, y in P])
        k = max(1, int(2400 / 200))
        z = np.convolve(np.pad(z, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
        for it in range(3):                                   # cap the grade both ways
            for i in range(1, len(z)):
                z[i] = np.clip(z[i], z[i - 1] - GRADE * 200, z[i - 1] + GRADE * 200)
            for i in range(len(z) - 2, -1, -1):
                z[i] = np.clip(z[i], z[i + 1] - GRADE * 200, z[i + 1] + GRADE * 200)
        for (x, y), zz in zip(P, z):
            m = (np.abs(X - x) < 3000) & (np.abs(Y - y) < 3000)
            d = np.hypot(X[m] - x, Y[m] - y)
            upd = d < best[m]
            bm = best[m]; tm = target[m]; wm = width[m]
            bm[upd] = d[upd]; tm[upd] = zz; wm[upd] = r["w"]
            best[m] = bm; target[m] = tm; width[m] = wm
    f = 1 - smooth((best - width / 2) / 900)
    return h * (1 - f) + f * target, best, lines


def rim(h):
    edge = WORLD - np.maximum(np.abs(X), np.abs(Y))
    wob = 900 * np.sin(X / 2300 + 0.7) * np.sin(Y / 2900 + 2.1) + 500 * np.sin((X + Y) / 1400)
    # toward the walls the land rises to just over the highest ground (the room's ceiling is 4096 + FLOOR_Z)
    top = float(np.percentile(h, 97)) + 700
    f = smooth((6000 + 0.6 * wob - edge) / 6000)
    return np.maximum(h, h * (1 - f) + f * (top + 0.3 * wob))


def tile(H, ti, tj):
    T = N // TILES
    verts, uvs, tris = [], [], []
    for j in range(tj * T, tj * T + T + 1):
        for i in range(ti * T, ti * T + T + 1):
            x, y = xs[i], xs[j]
            verts.append((x, y, float(H[j, i])))
            uvs.append((x / UV_TILE, -y / UV_TILE))
    for j in range(T):
        for i in range(T):
            a = j * (T + 1) + i; b = a + 1; c = a + T + 1; d = c + 1
            tris += [tri_facing(verts, (a, b, d), (0, 0, 1)), tri_facing(verts, (a, d, c), (0, 0, 1))]
    return verts, uvs, tris


def basin_water(H):
    b = next(q for q in S.PLACES if q["id"] == "basin")
    z = sample(H, b["x"], b["y"]) + 260
    r = b["r"] * 0.95
    verts = [(b["x"] - r, b["y"] - r, z), (b["x"] + r, b["y"] - r, z), (b["x"] - r, b["y"] + r, z), (b["x"] + r, b["y"] + r, z)]
    uvs = [(0, 0), (r / 256, 0), (0, r / 256), (r / 256, r / 256)]
    tris = [tri_facing(verts, (0, 1, 3), (0, 0, 1)), tri_facing(verts, (0, 3, 2), (0, 0, 1))]
    return (verts, uvs, tris), z


CANOPY = ["Flora_M.Tree.Tree1_clump1", "Flora_M.Tree.Tree1_clump1", "Mission_05M.Vegetation.Swamp_tree_new_001"]
MID = ["JungleM.Tree.Bumbershoot_stack1", "Mission_05M.Vegetation.highpoly_fern_02", "Mission_05M.Vegetation.highpoly_fern_03c"]
UNDER = ["JungleM.Plant.Plant_2_Elephantine", "JungleM.Plant.Plant_1", "Mission_08M.M08B_Outside.TestFern1",
         "Mission_05M.Vegetation.m08_grass_001", "Mission_05M.Vegetation.SwampPlantA01"]
JTREES = ["JungleM.Tree.Bumbershoot_stack1"]
JPLANTS = ["JungleM.Plant.Plant_2_Elephantine", "JungleM.Plant.Plant_1", "Mission_08M.M08B_Outside.TestFern1",
           "Mission_05M.Vegetation.SwampPlantA01"]
JGRASS = ["Mission_05M.Vegetation.m08_grass_001", "Mission_05M.Vegetation.Swamp_GrassGroup_005",
          "Mission_05M.Vegetation.swamp_smallplant_002"]
VINES = ["JungleM.Tree.SmallVineCollection_1", "JungleM.Vine.JungleRootVine1"]
STUMPS = ["Mission_05M.Vegetation.swamp_stump_002", "Mission_05M.Vegetation.swamp_tree_stump_001"]
DEADTREES = ["Mission_05M.Vegetation.swamp_tree_001", "Mission_05M.Vegetation.Swamp_tree_new_002"]
LANDMARK = {
    "plant": [("Terran_DecoM.Towers.CommTower_Entire", (1200, -900), 1.0), ("Mission_08M.M08B_Outside.M08B_SuperStructure1", (-800, 600), 1.0),
              ("Terran_DecoM.Misc.gas_tank", (1800, 1400), 1.6), ("Terran_DecoM.Misc.gas_tank", (2300, 900), 1.6),
              ("MM_WaterfrontM.Interior.tank_001", (-1900, -1500), 1.0), ("Mission_08M.M08B_Outside.M08B_IndustrialPondPipe1", (-600, -2600), 1.0)],
    "power": [("Mission_08M.bunker5.firebreather1", (900, 900), 1.0), ("Mission_08M.bunker5.firebreather1", (1700, -300), 1.0),
              ("Mission_08M.M08_B.Lofttower1", (-1200, 400), 0.8), ("Mission_08M.M08B_Outside.M08B_SuperStructure1", (-300, -1500), 1.0)],
    "pit": [("Mission_08M.M08_B.Lofttower1", (0, 0), 0.6)],
    "lz": [("Mission_08M.Bunker.M08A_padLights1", (d * math.cos(a), d * math.sin(a)), 1.0) for d in (1400,) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)],
    "pad": [("Mission_SulferonM.Base.LandingPadLight1", (d * math.cos(a), d * math.sin(a)), 1.0) for d in (1300,) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)],
}


def write_actors(H, dist_road, water_z, path):
    out = ["Begin Map\n"]
    k = [0]
    for ti in range(TILES):
        for tj in range(TILES):
            out.append(actor("StaticMeshActor", f"Ground{ti}{tj}", (0, 0, FLOOR_Z),
                             f"    StaticMesh=StaticMesh'SanctuaryOpenSM.Ground{ti}{tj}'\n"
                             "    Skins(0)=Texture'Mission_10T.Terrain.BryoTerr_U10B740_'\n"))
    out.append(actor("StaticMeshActor", "BasinWater", (0, 0, FLOOR_Z),
                     "    StaticMesh=StaticMesh'SanctuaryOpenSM.Basin'\n    Skins(0)=Shader'JungleT.Water.WaterSurfaceM081'\n"
                     "    bBlockActors=False\n    bBlockPlayers=False\n    bBlockNonZeroExtentTraces=False\n"))

    def prop(mesh, x, y, s, sink=6, collide=True, rot=None):
        out.append(actor("StaticMeshActor", f"P{k[0]}", (x, y, FLOOR_Z + sample(H, x, y) - sink),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n" + ("" if collide else NO_COLLISION),
                         rot if rot else (0, random.randint(0, 65535), 0)))
        k[0] += 1

    def droad(x, y):
        fi, fj = int(round((x + WORLD) / STEP)), int(round((y + WORLD) / STEP))
        return dist_road[min(max(fj, 0), N), min(max(fi, 0), N)]

    def place_at(x, y, pad=1.0):
        for q in S.PLACES:
            if q["r"] and math.hypot(x - q["x"], y - q["y"]) < q["r"] * pad:
                return q["id"]
        return None
    lim = WORLD - 2500
    counts = {"canopy": 0, "mid": 0, "under": 0}
    CAP = {"canopy": 1500, "mid": 1300, "under": 2800}
    # the jungle in three layers (the canopy survey, 2026-10-08: Flora_M's Tree1_clump1 and Mission_05M's big swamp
    # tree read as rainforest; JungleM's umbrella plants and the high-poly fern are the middle; the Sanctuary maps'
    # own big-leaf plants the floor). Densest in the band the player sees from the roads and places (0.9-3.5 km of
    # UU from them), thin deep inside where nobody looks: the frame rate goes to what is seen.
    for _ in range(60000):
        x, y = random.uniform(-lim, lim), random.uniform(-lim, lim)
        dr, pl = droad(x, y), place_at(x, y, 1.1)
        if pl in ("pit", "basin", "plant", "power", "pad", "lz", "shaft"):
            continue
        if pl == "field":
            if random.random() < 0.01:
                prop(random.choice(STUMPS + DEADTREES), x, y, random.uniform(0.4, 0.7), sink=12)
            continue
        if dr < 750:
            continue
        near = 1.0 if dr < 3500 else 0.35
        r = random.random()
        if dr > 1300 and counts["canopy"] < CAP["canopy"] and r < 0.05 * near:
            prop(random.choice(CANOPY), x, y, random.uniform(0.9, 1.5), sink=30)
            counts["canopy"] += 1
        elif counts["mid"] < CAP["mid"] and r < 0.09 * near:
            mesh = random.choice(MID)
            prop(mesh, x, y, random.uniform(1.0, 1.8), sink=10, collide=mesh.startswith("JungleM.Tree"))
            counts["mid"] += 1
        elif counts["under"] < CAP["under"] and r < 0.2 * near:
            prop(random.choice(UNDER), x, y, random.uniform(1.0, 2.2), sink=6, collide=False)
            counts["under"] += 1
    n_tree, n_plant = counts["canopy"] + counts["mid"], counts["under"]
    # the cleared field: haul debris and pipe racks as cover (stand-ins)
    f = next(q for q in S.PLACES if q["id"] == "field")
    for _ in range(26):
        a, d = random.uniform(0, 2 * math.pi), random.uniform(600, f["r"] * 0.85)
        x, y = f["x"] + d * math.cos(a), f["y"] + d * math.sin(a)
        if droad(x, y) > 700:
            prop(random.choice(["Terran_DecoM.Crates.crate2_highfull", "Terran_DecoM.Barrels.Metal_Barrel_01",
                                "Mission_08M.Crates.Boxnum2", "MM_WaterfrontM.Pipes.pipes01"]), x, y, random.uniform(0.9, 1.3), sink=4)
    # rocks on the pit benches
    p = next(q for q in S.PLACES if q["id"] == "pit")
    for _ in range(40):
        a, d = random.uniform(0, 2 * math.pi), random.uniform(1000, p["r"] * 0.95)
        x, y = p["x"] + d * math.cos(a), p["y"] + d * math.sin(a)
        if droad(x, y) > 600:
            s = random.uniform(1.5, 3.5)
            prop(random.choice(ROCKS), x, y, s, sink=8 * s, rot=(random.randint(-2500, 2500), random.randint(0, 65535), random.randint(-2500, 2500)))
    # the places, laid out by playable.py (the town generator's fork for combat arenas): buildings, gates, enemy
    # spawn sheds, cover clusters and the high spot, the Manta's lanes kept clear
    PL = playable.layout_all()
    json.dump(PL, open(os.path.join(OUT, "playable.json"), "w"), indent=1)
    for pid, area in PL.items():
        for o in area["props"]:
            yaw = int(o["yaw"] * 65536 / 360) & 65535
            prop(o["mesh"], o["x"], o["y"], o.get("scale", 1.0), sink=8, rot=(0, yaw, 0))
    # sky, sun (low, behind the plant from the LZ: dusk, the key art's light), start at the LZ facing the plant
    out.append(actor("SkyZoneInfo", "SkyZoneInfo0", (0, 0, SKY_Z)))
    out.append(actor("StaticMeshActor", "SkyBox", (0, 0, SKY_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.SkyBox'\n    Skins(0)=Texture'HoverTestSM.SkyAtlas'\n    bUnlit=True\n" + NO_COLLISION))
    lz = next(q for q in S.PLACES if q["id"] == "lz")
    plant = next(q for q in S.PLACES if q["id"] == "plant")
    yaw = int(math.atan2(plant["y"] - lz["y"], plant["x"] - lz["x"]) * 32768 / math.pi) & 65535
    out.append(actor("SunLight", "Sun0", (0, 0, 2500), "    LightBrightness=190.0\n    LightHue=20\n    LightSaturation=150\n", (-5200, (yaw + 32768) & 65535, 0)))
    out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=34\n    AmbientHue=140\n    AmbientSaturation=200\n"
                     "    bDistanceFog=True\n    DistanceFogColor=(R=46,G=52,B=44)\n    DistanceFogStart=3500\n    DistanceFogEnd=20000\n"))
    # the start: off the dropship's ramp, 1600 up the haul road, facing the plant
    a = yaw * math.pi / 32768
    sx, sy = lz["x"] + 1600 * math.cos(a), lz["y"] + 1600 * math.sin(a)
    out.append(actor("PlayerStart", "PlayerStart0", (sx, sy, FLOOR_Z + sample(H, sx, sy) + 150), "", (0, yaw, 0)))
    out.append("End Map\n")
    open(path, "w").write("".join(out))
    return n_tree, n_plant, k[0]


if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "Models", "ase"), exist_ok=True)
    H = shape(base())
    H, dist_road, lines = roads(H)
    H = rim(H)
    for ti in range(TILES):
        for tj in range(TILES):
            write_ase(os.path.join(OUT, "Models", "ase", f"Ground{ti}{tj}.ase"), f"Ground{ti}{tj}", *tile(H, ti, tj))
    (wv, wu, wt), wz = basin_water(H)
    write_ase(os.path.join(OUT, "Models", "ase", "Basin.ase"), "Basin", wv, wu, wt)
    nt, npl, nprops = write_actors(H, dist_road, wz, os.path.join(OUT, "open_actors.t3d"))
    np.save(os.path.join(OUT, "heights.npy"), H)
    print("heights %.0f..%.0f; %d trees, %d plants, %d props" % (H.min(), H.max(), nt, npl, nprops))
    for q in S.PLACES:
        print("  %-8s z %.0f" % (q["id"], sample(H, q["x"], q["y"])))
