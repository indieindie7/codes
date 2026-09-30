"""Sanctuary Prairie: a generated open map for The Seven's chapter 1.

    python make_prairie.py          meshes + prairie_actors.t3d
    python build_prairie.py assets  -> StaticMeshes/PrairieSM.usx, brushes/bigroom.u3d
    python build_prairie.py map     -> Maps/Prairie.un2 (+ paths)

Layout (world is -WORLD..WORLD, the engine's limit):
  west  (-25000, 0)      the crash: a scar in the grass, the Atlantis in pieces, Aida's console, the Manta
  creek  x ~ -9000       winding water, low banks: the bike crosses it
  ridge  x ~ +7000       a long rise across the route; the station is seen from its top
  east  (+23000, +5000)  a flat pad for the station compound (built by the director/brushes later)
  tunnel (+27000, +8500) a notch in the eastern hills (the ruins' entrance, later)

Same conventions as U2Hover/make_map.py (ASE mirror, tri facing, sky atlas).
"""
import math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOVER = os.path.join(os.path.dirname(HERE), "U2Hover")
sys.path.insert(0, HOVER)
from make_map import write_ase, tri_facing, skybox, actor, NO_COLLISION, PLANTS, ROCKS, FLOWERS, TREES  # noqa

WORLD = 30720          # half-size; the room is -WORLD..WORLD in X and Y
N = 240                # heightfield cells per side (256 units)
TILES = 8              # 8x8 meshes of 30x30 cells (a huge mesh gets no collision)
FLOOR_Z = -2750
WATER = -140
SKY_Z = 12000
UV_TILE = 1024.0

CRASH = (-25000.0, 0.0)
STATION = (23000.0, 5000.0)
TUNNEL = (27000.0, 8500.0)

# the trail: crash -> creek ford -> north round the big hill -> the ridge saddle -> down to the station
ROUTE = [(-24000, 800), (-19000, 3500), (-13500, 8500), (-8500, 11000), (-2500, 10500),
         (2500, 7500), (7200, 3200), (11500, 1200), (16500, 2400), (21000, 4500), (23000, 5000)]
BIGHILL = (-6000, 3500, 5200, 1500)      # the hill the trail swings around (cx, cy, r, amp)


def route_point(t):
    """position along the trail, t in 0..1, Catmull-Rom through ROUTE"""
    n = len(ROUTE) - 1
    f = min(max(t, 0.0), 0.999999) * n
    i = int(f); u = f - i
    p0 = ROUTE[max(i - 1, 0)]; p1 = ROUTE[i]; p2 = ROUTE[min(i + 1, n)]; p3 = ROUTE[min(i + 2, n)]
    def cr(a, b, c, d):
        return 0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u)
    return (cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1]))


ROUTE_PTS = None
def route_dist(x, y):
    """distance from (x, y) to the trail, and the trail's t there"""
    global ROUTE_PTS
    if ROUTE_PTS is None:
        ROUTE_PTS = [(route_point(k / 400.0), k / 400.0) for k in range(401)]
    best = 1e9; bt = 0
    for (px, py), t in ROUTE_PTS:
        d = (px - x) ** 2 + (py - y) ** 2
        if d < best:
            best = d; bt = t
    return math.sqrt(best), bt

random.seed(11)
# gentle swells everywhere, a few real hills, and the ridge
SWELLS = [(random.uniform(-WORLD, WORLD), random.uniform(-WORLD, WORLD),
           random.uniform(1800, 4200), random.uniform(60, 220)) for _ in range(90)]
HILLS = [(random.uniform(-WORLD, WORLD), random.uniform(-WORLD, WORLD),
          random.uniform(900, 2200), random.uniform(300, 900)) for _ in range(22)]


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def creek_y(x):
    return 1200 * math.sin(x / 5200.0) + 700 * math.sin(x / 1700.0 + 0.8)


def creek_x(y):
    # the creek runs north-south near x=-9000, wandering with y
    return -9000 + 1400 * math.sin(y / 6000.0) + 500 * math.sin(y / 1900.0 + 2.0)


def ridge(x, y):
    # a long rise across the route at x ~ 7000, broken by a saddle near the route
    d = x - (7000 + 900 * math.sin(y / 7000.0))
    r = 1100 * math.exp(-(d * d) / (2600.0 * 2600.0))
    saddle = 1 - 0.55 * math.exp(-((y - 2500) ** 2) / (2200.0 * 2200.0))
    return r * saddle


def flat_at(x, y, cx, cy, r, inner=0.6):
    return 1 - smooth((math.hypot(x - cx, y - cy) - r * inner) / (r * (1 - inner)))


def height(x, y):
    h = 0.0
    for cx, cy, r, amp in SWELLS:
        h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))
    for cx, cy, r, amp in HILLS:
        h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))
    h += ridge(x, y)
    cx, cy, r, amp = BIGHILL
    h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))
    # the rim: land rises toward the walls to hide them
    edge = WORLD - max(abs(x), abs(y))
    wobble = 900 * math.sin(x / 2300.0 + 0.7) * math.sin(y / 2900.0 + 2.1) + 500 * math.sin((x + y) / 1400.0)
    h += (3400 + wobble) * smooth((6000 + 0.6 * wobble - edge) / 6000)
    # the trail bed: eased toward a smooth line so the ride reads as a track
    d, t = route_dist(x, y)
    bed = smooth((d - 500) / 700)                          # 0 on the trail, 1 off it
    h = h * (bed + (1 - bed) * 0.94) - (1 - bed) * 12
    # flats: the crash scar, the station pad
    for (cx, cy), r in ((CRASH, 2600), (STATION, 3000)):
        f = flat_at(x, y, cx, cy, r)
        h = h * (1 - f) + f * (h * 0.15)
    # the crash scar itself: a shallow furrow running east from the wreck
    sx, sy = x - CRASH[0], y - CRASH[1]
    if -600 < sx < 2200:
        h -= 90 * math.exp(-(sy * sy) / (260.0 * 260.0)) * smooth((2200 - sx) / 800) * smooth((sx + 600) / 600)
    # the creek channel
    d = abs(x - creek_x(y))
    bank = smooth((d - 420) / 620)
    h = h * bank + (1 - bank) * -300
    return h


def tile(ti, tj):
    T = N // TILES
    step = 2 * WORLD / N
    verts, uvs, tris = [], [], []
    for j in range(tj * T, tj * T + T + 1):
        for i in range(ti * T, ti * T + T + 1):
            x, y = -WORLD + i * step, -WORLD + j * step
            verts.append((x, y, height(x, y)))
            uvs.append((x / UV_TILE, -y / UV_TILE))
    for j in range(T):
        for i in range(T):
            a = j * (T + 1) + i; b = a + 1; c = a + T + 1; d = c + 1
            tris += [tri_facing(verts, (a, b, d), (0, 0, 1)), tri_facing(verts, (a, d, c), (0, 0, 1))]
    return verts, uvs, tris


def creek_strip():
    verts, uvs, tris = [], [], []
    ys = [-WORLD + k * 256 for k in range(int(2 * WORLD / 256) + 1)]
    for k, y in enumerate(ys):
        xc = creek_x(y)
        for s in (-1, 1):
            verts.append((xc + s * 900, y, WATER))
            uvs.append((s * 900 / 512.0, y / 512.0))
        if k:
            a, b, c, d = 2 * k - 2, 2 * k - 1, 2 * k, 2 * k + 1
            tris += [tri_facing(verts, (a, c, d), (0, 0, 1)), tri_facing(verts, (a, d, b), (0, 0, 1))]
    return verts, uvs, tris


POLES = ["Mission_08M.M08_B_Inside2.CenterPole1"]
CABLESUP = ["Mission_08M.Structures_Inside.M08A_cablesupport1"]
DEADTREES = ["Mission_05M.Vegetation.swamp_tree_001", "Mission_05M.Vegetation.swamp_tree_002",
             "Mission_05M.Vegetation.swamp_tree_003", "Mission_05M.Vegetation.Swamp_tree_new_002"]
STUMPS = ["Mission_05M.Vegetation.swamp_stump_002", "Mission_05M.Vegetation.swamp_tree_stump_001"]
BIGTREES = ["Flora_M.Tree.Tree3", "Flora_M.Tree.Tree1_clump1"]
DEBRIS = ["Mission_05M.Misc.debris_misc_01", "Mission_05M.Misc.debris_misc_02",
          "Mission_05M.Misc.debris_sheet_001", "Mission_05M.Misc.debris_sheet_002"]
CRATES = ["Terran_DecoM.Crates.Crate1Low", "Terran_DecoM.Crates.Crate1Medium", "Terran_DecoM.Crates.crate2_highfull",
          "Terran_DecoM.Crates.crate_pallet_01"]
BARRELS = ["Terran_DecoM.Barrels.Metal_Barrel_01", "Terran_DecoM.Barrels.Metal_Barrel_Broken_01"]
TANKS = ["Terran_DecoM.Misc.gas_tank", "MM_WaterfrontM.Interior.tank_001", "MM_WaterfrontM.Interior.tank_002"]
PIPES = ["MM_WaterfrontM.Pipes.pipes01", "MM_WaterfrontM.Pipes.pipes02", "Mission_SulferonM.Base.PipeSet1"]
TOWERS = ["Terran_DecoM.Towers.CommTower_Entire", "Mission_SulferonM.Base.Tower1a", "Mission_08M.M08_B.Lofttower1"]
ANTENNA = ["Mission_08M.electronics.M08A_small_antenna1", "Mission_10M.wires.antennainwires1"]
PADLIGHT = ["Mission_08M.Bunker.M08A_padLights1", "Mission_SulferonM.Base.LandingPadLight1"]
GRASS = ["Mission_05M.Vegetation.Swamp_GrassGroup_005", "Mission_05M.Vegetation.swamp_smallplant_002",
         "Mission_05M.Vegetation.swamp_smallplant_004", "Mission_05M.Vegetation.swamp_underbrush_001"]
WRECK = [  # import-path test: the dropship as a plain prop, no rotation, on the ground
    ("Terran_DecoM.Crates.Terran_Dropship_01", (0, 0), 0.3, None),
    ("Mission_05M.debris_sheet_003.Crashed_Transport", (1500, -500), 1.0, None),
]


def scatter(count, keep):
    out = []
    while len(out) < count:
        x, y = random.uniform(-WORLD + 3000, WORLD - 3000), random.uniform(-WORLD + 3000, WORLD - 3000)
        if keep(x, y):
            out.append((x, y))
    return out


def far_from(x, y, pts, r):
    return all(math.hypot(x - px, y - py) > r for px, py in pts)


def write_actors(path, sun_yaw=32768):
    out = ["Begin Map\n"]
    for ti in range(TILES):
        for tj in range(TILES):
            out.append(actor("StaticMeshActor", f"Ground{ti}{tj}", (0, 0, FLOOR_Z),
                             f"    StaticMesh=StaticMesh'PrairieSM.Ground{ti}{tj}'\n"
                             "    Skins(0)=Texture'Mission_10T.Terrain.BryoTerr_U10B740_'\n"))
    out.append(actor("StaticMeshActor", "CreekSurface", (0, 0, FLOOR_Z),
                     "    StaticMesh=StaticMesh'PrairieSM.Creek'\n"
                     "    Skins(0)=Shader'JungleT.Water.WaterSurfaceM081'\n"
                     "    bBlockActors=False\n    bBlockPlayers=False\n    bBlockNonZeroExtentTraces=False\n"))
    k = 0
    cx, cy = CRASH
    # the wreck
    for mesh, (dx, dy), s, rot in WRECK:
        x, y = cx + dx, cy + dy
        out.append(actor("StaticMeshActor", f"Wreck{k}", (x, y, FLOOR_Z + height(x, y) - 10),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n", rot))
        k += 1
    def yaw_along(t):
        ax, ay = route_point(max(t - 0.005, 0)); bx, by = route_point(min(t + 0.005, 1))
        return int(math.atan2(by - ay, bx - ax) * 32768 / math.pi) & 65535

    def prop(mesh, x, y, s, rot=None, sink=6, collide=True):
        nonlocal k
        out.append(actor("StaticMeshActor", f"P{k}", (x, y, FLOOR_Z + height(x, y) - sink),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n" + ("" if collide else NO_COLLISION),
                         rot if rot else (0, random.randint(0, 65535), 0)))
        k += 1

    on_water = lambda x, y: abs(x - creek_x(y)) < 1100
    in_scar = lambda x, y: -400 < x - cx < 2400 and abs(y - cy) < 500

    # --- the trail's lining: markers along both sides, thinning where the land opens
    L = 640
    for m in range(L):
        t = m / (L - 1.0)
        x, y = route_point(t); yaw = yaw_along(t)
        nx, ny = -math.sin(yaw * math.pi / 32768), math.cos(yaw * math.pi / 32768)   # left normal
        side = 1 if m % 2 == 0 else -1
        d = random.uniform(650, 900)
        px, py = x + nx * d * side, y + ny * d * side
        if on_water(px, py) or math.hypot(px - STATION[0], py - STATION[1]) < 3200:
            continue
        r = random.random()
        if t < 0.18:          # leaving the crash: colony fence poles with cable supports, some debris
            if r < 0.55: prop(random.choice(POLES), px, py, random.uniform(0.25, 0.35), sink=20)
            elif r < 0.8: prop(random.choice(CABLESUP), px, py, 1.0, sink=10)
            elif r < 0.9: prop(random.choice(DEBRIS), px, py, random.uniform(1.0, 1.6))
        elif t < 0.45:        # the creek and the hill: dead trees and stumps, rocks
            if r < 0.45: prop(random.choice(DEADTREES), px, py, random.uniform(0.35, 0.55), sink=14)
            elif r < 0.65: prop(random.choice(STUMPS), px, py, random.uniform(0.5, 0.8), sink=10)
            elif r < 0.75: prop(random.choice(ROCKS), px, py, random.uniform(1.5, 3.0), sink=10,
                                rot=(random.randint(-1500, 1500), random.randint(0, 65535), random.randint(-1500, 1500)))
        elif t < 0.75:        # over the ridge: the colony's pipeline runs beside the trail, with barrels
            if r < 0.45: prop(random.choice(PIPES), px, py, random.uniform(0.3, 0.4), sink=12, rot=(0, yaw, 0))
            elif r < 0.75: prop(random.choice(BARRELS), px, py, 1.0, sink=4)
            elif r < 0.9: prop(random.choice(ANTENNA), px, py, 0.7, sink=8)
            else: prop(random.choice(POLES), px, py, 0.3, sink=20)
        else:                 # the approach: crates, tanks, pad lights, towers
            if r < 0.4: prop(random.choice(CRATES), px, py, random.uniform(0.9, 1.3), sink=4)
            elif r < 0.65: prop(random.choice(TANKS), px, py, random.uniform(0.8, 1.2), sink=8)
            elif r < 0.85: prop(random.choice(PADLIGHT), px, py, 1.0, sink=4)
            elif r < 0.95: prop(random.choice(BARRELS), px, py, 1.0, sink=4)
            else: prop(random.choice(TOWERS), px, py, random.uniform(0.5, 0.7), sink=20)

    # --- big trees: a few clumps, never on the trail
    for x, y in scatter(28, lambda x, y: not on_water(x, y) and route_dist(x, y)[0] > 1800
                        and far_from(x, y, [CRASH, STATION], 4500)):
        prop(random.choice(BIGTREES), x, y, random.uniform(0.8, 1.3), sink=20)
    # dead trees along the creek banks
    for x, y in scatter(70, lambda x, y: 1000 < abs(x - creek_x(y)) < 2000):
        prop(random.choice(DEADTREES + STUMPS), x, y, random.uniform(0.35, 0.6), sink=14)

    # --- grass: dense everywhere but the scar, the water and the trail bed itself
    keep = lambda x, y: not on_water(x, y) and not in_scar(x, y) and route_dist(x, y)[0] > 350
    for x, y in scatter(2600, keep):
        prop(random.choice(GRASS), x, y, random.uniform(0.9, 1.7), collide=False)
    for x, y in scatter(60, keep):
        prop(random.choice(FLOWERS), x, y, random.uniform(0.8, 1.2), sink=4, collide=False)
    # rocks on the ridge and the rim
    for x, y in scatter(70, lambda x, y: keep(x, y) and (ridge(x, y) > 300 or WORLD - max(abs(x), abs(y)) < 7000)):
        s = random.uniform(1.5, 4.0)
        prop(random.choice(ROCKS), x, y, s, sink=8 * s,
             rot=(random.randint(-2500, 2500), random.randint(0, 65535), random.randint(-2500, 2500)))

    # sky, sun, ambient, start (next to the wreck, facing east along the scar)
    out.append(actor("SkyZoneInfo", "SkyZoneInfo0", (0, 0, SKY_Z)))
    out.append(actor("StaticMeshActor", "SkyBox", (0, 0, SKY_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.SkyBox'\n"
                     "    Skins(0)=Texture'HoverTestSM.SkyAtlas'\n    bUnlit=True\n" + NO_COLLISION))
    out.append(actor("SunLight", "Sun0", (0, 0, 2500),
                     "    LightBrightness=210.0\n    LightHue=24\n    LightSaturation=170\n", (-7500, sun_yaw, 0)))
    out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=36\n    AmbientHue=150\n    AmbientSaturation=200\n"))
    out.append(actor("PlayerStart", "PlayerStart0", (cx + 400, cy + 1500, FLOOR_Z + height(cx + 400, cy + 1500) + 150), "", (0, -16384, 0)))
    out.append("End Map\n")
    open(path, "w").write("".join(out))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "Models", "ase"), exist_ok=True)
    for ti in range(TILES):
        for tj in range(TILES):
            write_ase(os.path.join(HERE, "Models", "ase", f"Ground{ti}{tj}.ase"), f"Ground{ti}{tj}", *tile(ti, tj))
    write_ase(os.path.join(HERE, "Models", "ase", "Creek.ase"), "Creek", *creek_strip())
    from make_map import write_sky_atlas
    sun_yaw = 32768
    write_actors(os.path.join(HERE, "prairie_actors.t3d"), sun_yaw)
    hs = [height(-WORLD + i * 1024, -WORLD + j * 1024) for i in range(61) for j in range(61)]
    print("heights %.0f..%.0f  crash %.0f  station %.0f  ridge top ~%.0f" % (
        min(hs), max(hs), height(*CRASH), height(*STATION), height(7000, -3000)))
