"""Avalon, remade: the Liandri plant seen from the Authority's tower, as a real map, laid out from the binder.

    python make_avalon.py           meshes (terrain tiles, sea, tower, room, quay, pipeline) + avalon_actors.t3d
    python build_avalon.py assets   -> StaticMeshes/AvalonSM.usx (everything in Models/ase/manifest.txt)
    python build_avalon.py map      -> Maps/Avalon.un2 (+ paths)

Coordinates: the tower at (0,0); the LOOK is 300 degrees (the window's direction); the binder's building
sheets give positions as (along, across) in that frame, in world units, plus the yaw their front faces.
Scale: 1 m = 50 units (the parts and the scripted buildings are modelled in metres and placed with
DrawScale 50). Sea level Z = -4967 (TutA's); the command room's floor is 5200 above it, ~2400 above the
tower's hill, so the plant (along 12000..17500) sits ~19 degrees below the window's horizon.
Terrain tiles are split in three materials by slope and height (grass / rock / shore sand).
Buildings come from the binder (binder/buildings/*.md): kinds hall/office/dorm/house/pump/jetty/pad are
assembled from parts (tools/build_parts.py -> B_<id>); tank/silo/cooling/rig/mast/dock keep the scripted
meshes (U2AvalonCards/tools/build_buildings.py). Same ASE conventions as U2Hover/make_map.py.
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
from ase import write_ase, tri_facing  # noqa
import binder  # noqa

WORLD = 30720
N = 240                 # heightfield cells per side (256 units)
TILES = 8
SEA_Z = -4967.0         # world Z of the sea surface
SKY_Z = 20000           # centre of the sky room: the big room brush again, stacked above the main room (build_avalon.py)
UV_TILE = 1024.0
TOWER = (0.0, 0.0)
LOOK_YAW = 300          # degrees, the window's direction
ROOM_Z = SEA_Z + 5200   # the command room's floor
M = 50.0                # units per metre
SHORE = 17500.0         # where the land meets the sea along the look (the binder's shore buildings sit at ~17000)
PLANT_AT = (14500.0, 0.0)   # the plant's shelf (along, across)
# the command room: a box on top of the tower, its window wall facing LOOK_YAW; the player stands inside it
ROOM_LEN, ROOM_WID, ROOM_HI = 2400.0, 2000.0, 520.0
DUSK = "dusk" in sys.argv[1:]    # the brief's one frame: low sun out over the sea, the plant lit, the tower dark
PLAYER_FROM_GLASS = 200.0

random.seed(11)
HILLS = [(random.uniform(-WORLD, WORLD), random.uniform(-WORLD, WORLD), random.uniform(1500, 4000),
          random.uniform(300, 1200)) for _ in range(40)]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def look_frame(x, y):
    """(along the look direction, across it) of a world point, from the tower"""
    dx, dy = x - TOWER[0], y - TOWER[1]
    a = math.radians(LOOK_YAW)
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def from_frame(along, across):
    a = math.radians(LOOK_YAW)
    return (TOWER[0] + along * math.cos(a) - across * math.sin(a), TOWER[1] + along * math.sin(a) + across * math.cos(a))


def shore_at(across):
    return SHORE + 1500 * math.sin(across / 4000.0) + 600 * math.sin(across / 1300.0 + 1)


def height(x, y):
    """land height above the sea (negative = sea floor)"""
    dx, dy = x - TOWER[0], y - TOWER[1]
    along, across = look_frame(x, y)
    shore = shore_at(across)
    # the base slope: from +2200 at the tower's hill down to the shore line; everything beyond is sea
    h = 2200 * smooth((shore - along) / (SHORE - 1500.0)) - 20
    # the plant's shelf: flat ground at +400
    # (an ellipse in the look frame: along 11500..17500, across +-5100, so it stops at the shore)
    shelf = smooth((3000 - math.hypot(along - PLANT_AT[0], (across - PLANT_AT[1]) / 1.7)) / 1200.0)
    h = h * (1 - shelf) + shelf * 400
    # hills on the land only, the big one under the company mast
    land = smooth((shore - along + 2000) / 3000.0)
    for cx, cy, r, amp in HILLS:
        h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r)) * land * (1 - shelf)
    mx, my = from_frame(1000, -15400)
    h += 3200 * math.exp(-((x - mx) ** 2 + (y - my) ** 2) / (5000.0 ** 2))
    h += 600 * math.exp(-(dx * dx + dy * dy) / (2600.0 ** 2))           # the tower's own hill
    # the director's green hill
    gx, gy = from_frame(10600, -4200)
    h += 500 * math.exp(-((x - gx) ** 2 + (y - gy) ** 2) / (1800.0 ** 2)) * (1 - shelf)
    # the sea floor falls away gently
    if along > shore:
        h -= 600 * smooth((along - shore) / 6000.0)
    # the rim: land rises toward the walls on the land sides
    edge = WORLD - max(abs(x), abs(y))
    if along < shore - 3000:
        h += 3000 * smooth((5000 - edge) / 5000.0)
    return h


def slope(x, y, d=64.0):
    hx = (height(x + d, y) - height(x - d, y)) / (2 * d)
    hy = (height(x, y + d) - height(x, y - d)) / (2 * d)
    return math.hypot(hx, hy)


ROADS = []            # world segments ((x0,y0),(x1,y1)) where people walk between buildings (from the routines)


def roads_from(citizens, buildings):
    """every consecutive pair of places in a routine becomes a worn track between the two buildings; the
    more people walk it, the wider (the width is used by material_at)"""
    counts = {}
    for c in citizens.values():
        r = c.get("routine", [])
        for k in range(1, len(r)):
            a, b = r[k - 1][1], r[k][1]
            if a != b and a in buildings and b in buildings and "at" in buildings[a] and "at" in buildings[b]:
                if buildings[a]["kind"] == "rig" or buildings[b]["kind"] == "rig":
                    continue                                   # the rig shuttle is a boat, not a path
                key = tuple(sorted((a, b)))
                counts[key] = counts.get(key, 0) + 1
    segs = []
    for (a, b), n in counts.items():
        pa = from_frame(*buildings[a]["at"][:2])
        pb = from_frame(*buildings[b]["at"][:2])
        segs.append((pa, pb, 120 + 60 * min(n, 4)))
    return segs


def material_at(x, y):
    """0 grass, 1 rock (steep), 2 sand (the shore band, and the worn tracks between buildings)"""
    h = height(x, y)
    if -300 < h < 160:
        return 2
    for (x0, y0), (x1, y1), w in ROADS:
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        if math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) < w:
            return 2
    if slope(x, y) > 1.1 or h > 4200:
        return 1
    return 0


MAT_NAMES = ("Grass", "Rock", "Sand")
MAT_TEX = ("Texture'Mission_10T.Terrain.BryoTerr_U10B740_'", "Texture'Mission_10T.Terrain.rockterr_u10a741_'",
           "Texture'ScottT.Generic.SandFlor_U06S667'")


def tile(ti, tj):
    """three (verts, uvs, tris) sets, one per material (empty ones are skipped by the caller)"""
    T = N // TILES
    step = 2 * WORLD / N
    verts, uvs = [], []
    for j in range(tj * T, tj * T + T + 1):
        for i in range(ti * T, ti * T + T + 1):
            x, y = -WORLD + i * step, -WORLD + j * step
            verts.append((x, y, height(x, y)))
            uvs.append((x / UV_TILE, -y / UV_TILE))
    sets = [[], [], []]
    for j in range(T):
        for i in range(T):
            a = j * (T + 1) + i; b = a + 1; c = a + T + 1; d = c + 1
            cx, cy = -WORLD + (ti * T + i + 0.5) * step, -WORLD + (tj * T + j + 0.5) * step
            m = material_at(cx, cy)
            sets[m] += [tri_facing(verts, (a, b, d), (0, 0, 1)), tri_facing(verts, (a, d, c), (0, 0, 1))]
    outs = []
    for tris in sets:
        if not tris:
            outs.append(None)
            continue
        used = sorted({k for t in tris for k in t})
        idx = {k: n for n, k in enumerate(used)}
        outs.append(([verts[k] for k in used], [uvs[k] for k in used], [tuple(idx[k] for k in t) for t in tris]))
    return outs


def sea():
    """one quad over the whole world at Z 0 (placed at SEA_Z); the land pokes through it"""
    s = WORLD * 1.02
    verts = [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)]
    uvs = [(0, 0), (s / 512.0, 0), (s / 512.0, s / 512.0), (0, s / 512.0)]
    tris = [tri_facing(verts, (0, 1, 2), (0, 0, 1)), tri_facing(verts, (0, 2, 3), (0, 0, 1))]
    return verts, uvs, tris


def cylinder(verts, uvs, tris, cx, cy, z0, z1, r0, r1, n=24, uv=(0.5, 0.5), cap=True):
    base = len(verts)
    for k in range(n):
        a = 2 * math.pi * k / n
        verts.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0)); uvs.append(uv)
        verts.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1)); uvs.append(uv)
    for k in range(n):
        a, b = base + 2 * k, base + 2 * ((k + 1) % n)
        ang = 2 * math.pi * (k + 0.5) / n
        out = (math.cos(ang), math.sin(ang), 0)
        tris += [tri_facing(verts, (a, b, b + 1), out), tri_facing(verts, (a, b + 1, a + 1), out)]
    if cap:
        c = len(verts); verts.append((cx, cy, z1)); uvs.append(uv)
        for k in range(n):
            a, b = base + 2 * k + 1, base + 2 * ((k + 1) % n) + 1
            tris.append(tri_facing(verts, (a, b, c), (0, 0, 1)))


def rot_z(p, deg):
    a = math.radians(deg)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2])


def box(verts, uvs, tris, cx, cy, cz, sx, sy, sz, yaw=0.0, uv=(0.5, 0.5), skip=()):
    """an axis box of full sizes sx sy sz centred at (cx,cy,cz), turned by yaw"""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    faces = {"-x": ((-1, 0, 0), [(-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz)]),
             "+y": ((0, 1, 0), [(-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz)]),
             "+x": ((1, 0, 0), [(hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz), (hx, -hy, -hz)]),
             "-y": ((0, -1, 0), [(hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz), (-hx, -hy, -hz)]),
             "+z": ((0, 0, 1), [(-hx, hy, hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz)]),
             "-z": ((0, 0, -1), [(-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz)])}
    for key, (n, vs) in faces.items():
        if key in skip:
            continue
        base = len(verts)
        for v in vs:
            r = rot_z(v, yaw)
            verts.append((cx + r[0], cy + r[1], cz + r[2])); uvs.append(uv)
        nw = rot_z(n, yaw)
        tris.append(tri_facing(verts, (base, base + 1, base + 2), nw))
        tris.append(tri_facing(verts, (base, base + 2, base + 3), nw))


# palette swatches: tools\glb_to_ase.py's Pal.tga is 8 column stripes, palette.json lists their colours in order;
# look a stripe up by the colour name the buildings use (build_parts.py's COLOURS)
import palette  # noqa
SW_COLOURS = palette.COLOURS
_PAL = None


def sw(name):
    global _PAL
    if _PAL is None:
        _PAL = json.load(open(os.path.join(HERE, "Models", "ase", "palette.json")))
    want = palette.colour(name)
    best = min(range(len(_PAL)), key=lambda i: sum((a - b) ** 2 for a, b in zip(_PAL[i], want)))
    return ((best + 0.5) / 8.0, 0.5)


def tower():
    """the Authority's tower as a shell: a tapering shaft, a flared head carrying the command room's deck, a
    cap and a mast. Heights relative to SEA_Z (the actor stands at SEA_Z)."""
    verts, uvs, tris = [], [], []
    ground = height(*TOWER)
    room = ROOM_Z - SEA_Z
    cylinder(verts, uvs, tris, 0, 0, ground - 400, room - 700, 1400, 900, uv=sw("concrete"), cap=False)
    # the head ends at the room's glass (half-length 1200): a deck in front of the glass hid the whole view down
    cylinder(verts, uvs, tris, 0, 0, room - 700, room - 60, 900, 1250, uv=sw("concrete"), cap=False)      # the flared head
    cylinder(verts, uvs, tris, 0, 0, room - 60, room, 1250, 1250, uv=sw("dark"), cap=True)            # the deck
    cylinder(verts, uvs, tris, 0, 0, room + ROOM_HI, room + ROOM_HI + 500, 1500, 500, uv=sw("concrete"), cap=True)   # the cap
    cylinder(verts, uvs, tris, 0, 0, room + ROOM_HI + 500, room + ROOM_HI + 2400, 60, 60, n=8, uv=sw("dark"), cap=True)
    return verts, uvs, tris


def room():
    """the command room on the deck: floor, ceiling, three walls, and the window wall as a frame (a low sill, a
    lintel and mullions) so the glass side is open to the view. Built along +X then turned to LOOK_YAW; Z 0 =
    the room's floor (actor at ROOM_Z)."""
    verts, uvs, tris = [], [], []
    L, W, H = ROOM_LEN, ROOM_WID, ROOM_HI
    t = 40.0
    box(verts, uvs, tris, 0, 0, -t / 2, L + 2 * t, W + 2 * t, t, LOOK_YAW, uv=sw("dark"))                     # floor slab
    box(verts, uvs, tris, 0, 0, H + t / 2, L + 2 * t, W + 2 * t, t, LOOK_YAW, uv=sw("dark"))                  # ceiling
    box(verts, uvs, tris, -L / 2 - t / 2, 0, H / 2, t, W + 2 * t, H, LOOK_YAW, uv=sw("concrete"))                  # back wall
    box(verts, uvs, tris, 0, W / 2 + t / 2, H / 2, L, t, H, LOOK_YAW, uv=sw("concrete"))                           # side walls
    box(verts, uvs, tris, 0, -W / 2 - t / 2, H / 2, L, t, H, LOOK_YAW, uv=sw("concrete"))
    gx = L / 2 + t / 2
    box(verts, uvs, tris, gx, 0, 15, t, W + 2 * t, 30, LOOK_YAW, uv=sw("dark"))                                # sill
    box(verts, uvs, tris, gx, 0, H - 35, t, W + 2 * t, 70, LOOK_YAW, uv=sw("dark"))                            # lintel
    k = -W / 2
    while k <= W / 2 + 1:
        box(verts, uvs, tris, gx, k, H / 2, t, 24, H, LOOK_YAW, uv=sw("dark"))                                 # mullions
        k += 1000
    box(verts, uvs, tris, L / 2 - 420, 0, 40, 200, W * 0.7, 80, LOOK_YAW, uv=sw("dark"))                        # the console
    box(verts, uvs, tris, L / 2 - 420, 0, 84, 180, W * 0.68, 8, LOOK_YAW, uv=sw("glow"))
    for k in (-600, -200, 200, 600):                                                                     # cabinets
        box(verts, uvs, tris, -L / 2 + 120, k, 140, 240, 300, 280, LOOK_YAW, uv=sw("dark"))
    return verts, uvs, tris


def quay(b):
    """the dock: a long concrete slab into the sea with bollards (Z 0 = its bottom; the actor stands at SEA_Z - 80)"""
    verts, uvs, tris = [], [], []
    Lq, Wq = b["size"][0] * M, b["size"][1] * M
    box(verts, uvs, tris, 0, 0, 150, Lq, Wq, 300, 0, uv=sw("concrete"))
    k = -Lq / 2 + 400
    while k < Lq / 2 - 300:
        box(verts, uvs, tris, k, Wq / 2 - 70, 360, 80, 80, 120, 0, uv=sw("dark"))
        k += 750
    return verts, uvs, tris


def pipeline(pts, z_of):
    """a rust pipe on posts through the given world points; z_of(x, y) = the pipe's height above SEA_Z"""
    verts, uvs, tris = [], [], []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        z0, z1 = z_of(x0, y0), z_of(x1, y1)
        n = 10
        base = len(verts)
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        px, py = -dy / ln, dx / ln
        for k in range(n):
            a = 2 * math.pi * k / n
            ox, oy, oz = px * 60 * math.cos(a), py * 60 * math.cos(a), 60 * math.sin(a)
            verts.append((x0 + ox, y0 + oy, z0 + oz)); uvs.append(sw("rust"))
            verts.append((x1 + ox, y1 + oy, z1 + oz)); uvs.append(sw("rust"))
        for k in range(n):
            a, b = base + 2 * k, base + 2 * ((k + 1) % n)
            ang = 2 * math.pi * (k + 0.5) / n
            out = (px * math.cos(ang), py * math.cos(ang), math.sin(ang))
            tris += [tri_facing(verts, (a, b, b + 1), out), tri_facing(verts, (a, b + 1, a + 1), out)]
        for s in (0.25, 0.5, 0.75):
            x, y = x0 + dx * s, y0 + dy * s
            g = max(height(x, y), -600)
            top = z0 + (z1 - z0) * s - 50
            box(verts, uvs, tris, x, y, (g + top) / 2, 50, 50, max(10, top - g), 0, uv=sw("dark"))
    return verts, uvs, tris


def fence(buildings):
    """the company fence round the plant's shelf: posts every 8 m with two rails, on the shelf ellipse (along
    11500..17500, across +-5100) but only on the land side, with gaps where the tracks cross it. Z 0 = SEA_Z."""
    verts, uvs, tris = [], [], []
    ra, rc = 3000.0 - 300, 5100.0 - 500
    n = 160
    pts = []
    for k in range(n + 1):
        t = -math.pi / 2 + math.pi * k / n              # the land half of the ellipse (toward the tower)
        along = PLANT_AT[0] - ra * math.cos(t)
        across = PLANT_AT[1] + rc * math.sin(t)
        pts.append(from_frame(along, across))
    def near_track(x, y):
        for (x0, y0), (x1, y1), w in ROADS:
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            tt = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
            if math.hypot(x - (x0 + tt * dx), y - (y0 + tt * dy)) < w + 150:
                return True
        return False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        if near_track(xm, ym) or height(xm, ym) < 0:
            continue
        g0, g1 = height(x0, y0), height(x1, y1)
        box(verts, uvs, tris, x0, y0, g0 + 60, 14, 14, 130, 0, uv=sw("dark"))
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        for z in (45, 105):
            box(verts, uvs, tris, xm, ym, (g0 + g1) / 2 + z, L, 5, 5, ang, uv=sw("dark"))
    return verts, uvs, tris


def floodmast(verts, uvs, tris, x, y, g, lit=True):
    """a floodlight mast: a 14 m pole with a cross-arm and two lamp heads"""
    box(verts, uvs, tris, x, y, g + 350, 22, 22, 700, 0, uv=sw("dark"))
    box(verts, uvs, tris, x, y, g + 690, 160, 14, 14, 0, uv=sw("dark"))
    for dx in (-70, 70):
        box(verts, uvs, tris, x + dx, y, g + 670, 36, 30, 30, 0, uv=sw("glow" if lit else "dark"))


def actor(cls, name, loc, props="", rot=None):
    x, y, z = loc
    r = f"    Rotation=(Pitch={rot[0]},Yaw={rot[1]},Roll={rot[2]})\n" if rot else ""
    return (f"Begin Actor Class={cls} Name={name}\n"
            f"    Location=(X={x:.1f},Y={y:.1f},Z={z:.1f})\n{r}{props}End Actor\n")


def yaw(deg):
    return int(deg * 65536 / 360.0) & 65535


SEA_SHADER = "Shader'JungleT.Water.WaterSurfaceM081'"
NO_COLLISION = "    bCollideActors=False\n    bBlockActors=False\n    bBlockPlayers=False\n"
PAL = "    Skins(0)=Texture'AvalonSM.Pal.Pal'\n"
BOUNDS = {}      # mesh name -> bounds + the texture it uses (glb_to_ase.py's bounds.json)


def skin(mesh):
    tex = BOUNDS.get(mesh, {}).get("texture", "Pal")
    return PAL if tex == "Pal" else f"    Skins(0)=Texture'AvalonSM.Bake.{tex}'\n"
TREES = ["Flora_M.Tree.Tree3", "Flora_M.Tree.Tree1_clump1"]
CRATES = ["Terran_DecoM.Crates.Crate1Low", "Terran_DecoM.Crates.Crate1Medium", "Terran_DecoM.Crates.crate_pallet_01"]
BARRELS = ["Terran_DecoM.Barrels.Metal_Barrel_01", "Terran_DecoM.Barrels.Metal_Barrel_Broken_01"]
# the binder's kinds that keep a scripted mesh (metres, DrawScale M), by kind or by id
SCRIPTED = {"tank": "StorageTank", "silo": "OreTank", "cooling": "CoolingTower", "mast": "RadioMast",
            "new_rig": "DrillingRig", "dead_rig": "DeadRig"}
ASSEMBLED = ("hall", "office", "dorm", "house", "pump", "jetty", "pad")


def land_z(x, y):
    return SEA_Z + height(x, y)


CARD_PX = 256          # the cards' size (tools/bake_cards.py size=256); the building fills 92%, base line 6% up


def card_actor(name, k, base, x, y, z_ground, deg, size_units):
    """an 8-view imposter of a Hunyuan model: U2AvalonCards.CardSprite with the frames AvalonSM.Cards.<base>0..7.
    Frame k faces k*45 degrees clockwise from the card's yaw; the sprite's centre sits 0.44*size above the base line."""
    frames = "".join(f"    Frames({i})=Texture'AvalonSM.Cards.{base}{i}'\n" for i in range(8))
    return actor("U2AvalonCards.CardSprite", f"C{k}_{base}", (x, y, z_ground + 0.44 * size_units),
                 frames + f"    Texture=Texture'AvalonSM.Cards.{base}0'\n    NumFrames=8\n    Style=STY_Masked\n"
                 f"    DrawScale={size_units / CARD_PX:.3f}\n    bUnlit=False\n", (0, yaw(deg), 0))


def instances(b):
    """the (x, y, yaw) of each copy of a building: 'count: 3 across' / '2 along' / '2x2' in the look frame"""
    along, across, deg = b["at"]
    w, d = b["size"][0] * M, b["size"][1] * M
    gap = max(w, d) * 1.5
    spec = b.get("count", "1").split()
    pts = [(0, 0)]
    if spec[0].lower() == "2x2":
        pts = [(-gap / 2, -gap / 2), (gap / 2, -gap / 2), (-gap / 2, gap / 2), (gap / 2, gap / 2)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    out = []
    for da, dc in pts:
        x, y = from_frame(along + da, across + dc)
        out.append((x, y, deg))
    return out


def write_actors(path, bounds, manifest, buildings):
    out = ["Begin Map\n"]
    k = 0
    for name, group, tex in manifest:
        if group != "Ground":
            continue
        out.append(actor("StaticMeshActor", name, (0, 0, SEA_Z),
                         f"    StaticMesh=StaticMesh'AvalonSM.Ground.{name}'\n    Skins(0)={tex}\n"))
    out.append(actor("StaticMeshActor", "Sea", (0, 0, SEA_Z),
                     f"    StaticMesh=StaticMesh'AvalonSM.Ground.Sea'\n    Skins(0)={SEA_SHADER}\n"
                     "    bBlockActors=False\n    bBlockPlayers=False\n    bBlockNonZeroExtentTraces=False\n"))
    out.append(actor("StaticMeshActor", "Tower", (0, 0, SEA_Z), "    StaticMesh=StaticMesh'AvalonSM.Tower.Tower'\n" + PAL))
    out.append(actor("StaticMeshActor", "Room", (0, 0, ROOM_Z), "    StaticMesh=StaticMesh'AvalonSM.Tower.Room'\n" + PAL))

    def mesh_actor(mesh, x, y, z, deg, scale=1.0, extra=""):
        nonlocal k
        out.append(actor("StaticMeshActor", f"A{k}_{mesh}", (x, y, z),
                         f"    StaticMesh=StaticMesh'AvalonSM.Liandri.{mesh}'\n" + skin(mesh) + f"    DrawScale={scale:.3f}\n" + extra,
                         (0, yaw(deg), 0)))
        k += 1

    def prop(mesh, x, y, s=1.0, bottom=0.0, yaw_deg=None, sink=0.0, collide=True, z=None):
        nonlocal k
        yd = random.uniform(0, 360) if yaw_deg is None else yaw_deg
        zz = land_z(x, y) if z is None else z
        out.append(actor("StaticMeshActor", f"P{k}", (x, y, zz - bottom * s - sink),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n" + ("" if collide else NO_COLLISION),
                         (0, yaw(yd), 0)))
        k += 1

    # --- the binder's buildings ---
    placed = {}            # id -> [(x, y)] for props, pylons, pipeline
    for bid, b in buildings.items():
        if "at" not in b:
            continue
        pts = instances(b)
        placed[bid] = [(x, y) for x, y, _ in pts]
        kind = b["kind"]
        if bid == "tower":
            continue                                    # tower() above
        if kind == "dock":
            x, y, deg = pts[0]
            out.append(actor("StaticMeshActor", "Quay", (x, y, SEA_Z - 80), "    StaticMesh=StaticMesh'AvalonSM.Liandri.Quay'\n" + PAL, (0, yaw(deg), 0)))
            # the crane near the sea end, containers along the quay
            a = math.radians(deg)
            Lq = b["size"][0] * M
            if not b.get("card"):
                mesh_actor("DockCrane", x + math.cos(a) * Lq * 0.3, y + math.sin(a) * Lq * 0.3, SEA_Z - 80 + 300, deg + 90)
            else:
                cw = b["card"].split()
                out.append(card_actor(cw[0], k, cw[0], x + math.cos(a) * Lq * 0.3, y + math.sin(a) * Lq * 0.3, SEA_Z - 80 + 300, deg + 90, float(cw[1])))
                k += 1
            for kx in range(int(-Lq / 2 + 500), int(Lq / 2 - 1500), 650):
                if random.random() < 0.7:
                    prop(random.choice(CRATES), x + kx * math.cos(a) - 250 * math.sin(a), y + kx * math.sin(a) + 250 * math.cos(a),
                         1.0, bottom=-130, yaw_deg=deg + random.choice((0, 90)), z=SEA_Z - 80 + 300)
            continue
        if b.get("card"):
            # a Hunyuan imposter instead of (or on top of) the mesh: "card: DrillingRigHY 4000"
            cw = b["card"].split()
            cname, csize = cw[0], float(cw[1]) if len(cw) > 1 else b["size"][2] * M / 0.92
            for x, y, deg in pts:
                if kind == "rig":
                    zg = SEA_Z - 0.06 * csize
                elif kind in ("dock", "pad"):
                    zg = (SEA_Z - 80 + 300) if kind == "dock" else SEA_Z + max(0.0, height(x, y)) + 1.0 * M
                    a2 = math.radians(deg)
                    if kind == "dock":
                        x, y = x + math.cos(a2) * b["size"][0] * M * 0.3, y + math.sin(a2) * b["size"][0] * M * 0.3
                else:
                    zg = SEA_Z + max(0.0, height(x, y))
                out.append(card_actor(cname, k, cname, x, y, zg, deg, csize))
                k += 1
            if kind in ("rig", "cooling"):
                continue                      # the card replaces the mesh for these
        mesh = b.get("mesh") or (f"B_{bid}" if kind in ASSEMBLED else SCRIPTED.get(bid, SCRIPTED.get(kind)))
        if mesh is None:
            print("no mesh for", bid, kind)
            continue
        for x, y, deg in pts:
            if kind == "rig":
                z = SEA_Z - 0.12 * b["size"][2] * M          # legs a little under the sea
            elif kind == "jetty":
                z = SEA_Z - 60
            else:
                z = SEA_Z + max(0.0, height(x, y))
            mesh_actor(mesh, x, y, z, deg)
        # usage dressing
        if kind == "pad" and bid == "cargo_pad" and not b.get("card"):
            x, y, deg = pts[0]
            mesh_actor("CargoDropship", x, y, SEA_Z + max(0.0, height(x, y)) + 1.0 * M, deg + 20, 0.5)
        if kind == "pad" and bid == "authority_pad":
            x, y, deg = pts[0]
            prop("Terran_DecoM.Vehicles.Terran_Dropship_01", x, y, 1.6, bottom=-74, yaw_deg=deg + 160, z=land_z(x, y) + 1.0 * M)
        if kind in ("hall", "dorm") and not b["abandoned"]:
            for x, y, deg in pts:
                for _ in range(5):
                    a2, d2 = random.uniform(0, 2 * math.pi), random.uniform(max(b["size"][:2]) * M * 0.7, max(b["size"][:2]) * M * 1.1)
                    px_, py_ = x + d2 * math.cos(a2), y + d2 * math.sin(a2)
                    if height(px_, py_) > 0:
                        prop(random.choice(CRATES if random.random() < 0.6 else BARRELS), px_, py_, random.uniform(0.8, 1.2), bottom=-130)
        if b["abandoned"] and kind == "hall":
            for x, y, deg in pts:
                for _ in range(6):
                    a2, d2 = random.uniform(0, 2 * math.pi), random.uniform(600, 1200)
                    prop(random.choice(BARRELS), x + d2 * math.cos(a2), y + d2 * math.sin(a2), 1.0, bottom=-30)

    # the pipeline: tank farm -> generator house side -> shore -> the new rig; the pylon line: generator house -> tower
    def along_pts(ids, extra=()):
        pts = [placed[i][0] for i in ids if i in placed] + list(extra)
        return pts
    pipe_pts = along_pts(["tank_farm", "hall_b", "generator_house"]) + [from_frame(SHORE + 300, 3800)]
    if "new_rig" in placed:
        rx, ry = placed["new_rig"][0]
        lx, ly = pipe_pts[-1]
        pipe_pts += [(lx + (rx - lx) * 0.5, ly + (ry - ly) * 0.5), (lx + (rx - lx) * 0.94, ly + (ry - ly) * 0.94)]
    pipe = pipeline(pipe_pts, lambda x, y: max(height(x, y), 0) + 180)
    write_ase(os.path.join(HERE, "Models", "ase", "Pipeline.ase"), "Pipeline", *pipe)
    out.append(actor("StaticMeshActor", "Pipeline", (0, 0, SEA_Z), "    StaticMesh=StaticMesh'AvalonSM.Liandri.Pipeline'\n" + PAL))
    fv = fence(buildings)
    write_ase(os.path.join(HERE, "Models", "ase", "Fence.ase"), "Fence", *fv)
    out.append(actor("StaticMeshActor", "Fence", (0, 0, SEA_Z), "    StaticMesh=StaticMesh'AvalonSM.Liandri.Fence'\n" + PAL + NO_COLLISION))
    mv = ([], [], [])
    for bid in ("cargo_pad", "dock"):
        if bid in placed:
            x, y = placed[bid][0]
            b = buildings[bid]
            a2 = math.radians(b["at"][2])
            W2, D2 = b["size"][0] * M / 2, b["size"][1] * M / 2
            for sx, sy in ((-1, -1), (1, 1)) if bid == "cargo_pad" else ((-0.9, 1.2),):
                px_, py_ = x + sx * W2 * math.cos(a2) - sy * D2 * math.sin(a2), y + sx * W2 * math.sin(a2) + sy * D2 * math.cos(a2)
                g = max(height(px_, py_), 0) if bid == "cargo_pad" else 220
                floodmast(*mv, px_, py_, g, b["lit"])
    write_ase(os.path.join(HERE, "Models", "ase", "Floodmasts.ase"), "Floodmasts", *mv)
    out.append(actor("StaticMeshActor", "Floodmasts", (0, 0, SEA_Z), "    StaticMesh=StaticMesh'AvalonSM.Liandri.Floodmasts'\n" + PAL))
    if "generator_house" in placed:
        gx, gy = placed["generator_house"][0]
        for f in (0.85, 0.65, 0.45, 0.25):
            x, y = gx * f, gy * f
            mesh_actor("pylon_1_kiln" if "pylon_1_kiln" in bounds else "Pylon", x, y, SEA_Z + max(0.0, height(x, y)), LOOK_YAW + 90)

    # trees on the land, away from the buildings, the tower and the sea
    random.seed(21)
    n = 0
    spots = [p for pts in placed.values() for p in pts]
    while n < 170:
        x, y = random.uniform(-WORLD + 3000, WORLD - 3000), random.uniform(-WORLD + 3000, WORLD - 3000)
        h = height(x, y)
        along, across = look_frame(x, y)
        if h < 250 or along > shore_at(across) - 1200 or math.hypot(x, y) < 2300:
            continue
        if any(math.hypot(x - sx, y - sy) < 1500 for sx, sy in spots):
            continue
        prop(random.choice(TREES), x, y, random.uniform(0.9, 1.5), sink=20)
        n += 1

    # sky, sun, ambient
    out.append(actor("SkyZoneInfo", "SkyZoneInfo0", (0, 0, SKY_Z)))
    out.append(actor("StaticMeshActor", "SkyBox", (0, 0, SKY_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.SkyBox'\n    Skins(0)=Texture'HoverTestSM.SkyAtlas'\n    bUnlit=True\n" + NO_COLLISION))
    if not DUSK:
        # a late-afternoon sun from the north-east, 45 degrees up: side light across the plant as seen from the
        # tower. The sun actor must stand in open air (actors are sunlit only if the trace toward it is clear).
        sf = math.radians(LOOK_YAW - 60 + 180)
        sun_at = (14000 * math.cos(sf) * math.cos(math.radians(45)), 14000 * math.sin(sf) * math.cos(math.radians(45)), 7500)
        out.append(actor("SunLight", "Sun0", sun_at,
                         "    LightBrightness=240.0\n    LightHue=24\n    LightSaturation=100\n", (-8192, yaw(LOOK_YAW - 60), 0)))
        out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=130\n    AmbientHue=28\n    AmbientSaturation=120\n"))
        a = math.radians(LOOK_YAW)
        for dd in (-600, 300):
            lx, ly = dd * math.cos(a), dd * math.sin(a)
            out.append(actor("Light", f"RoomLight{dd}", (lx, ly, ROOM_Z + ROOM_HI - 60),
                             "    LightBrightness=150.0\n    LightHue=28\n    LightSaturation=120\n    LightRadius=100\n"))
    else:
        # the one frame: the sun setting out over the sea in the look direction (it travels toward the tower),
        # a cold blue ambient, every lit building with its own warm lamp, the tower's room dark, and one light
        # on the dead rig where there should be none
        sf = math.radians(LOOK_YAW)
        sun_at = (22000 * math.cos(sf) * math.cos(math.radians(8)), 22000 * math.sin(sf) * math.cos(math.radians(8)), 3200)
        out.append(actor("SunLight", "Sun0", sun_at,
                         "    LightBrightness=170.0\n    LightHue=18\n    LightSaturation=60\n", (-1400, yaw(LOOK_YAW + 180), 0)))
        out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=55\n    AmbientHue=150\n    AmbientSaturation=110\n"))
        n = 0
        for bid, b in buildings.items():
            if "at" not in b or bid == "tower":
                continue
            lamps = []
            if bid in ("cargo_pad", "dock") and b["lit"]:
                x, y, _ = instances(b)[0]
                lamps.append((x, y, 13.0 * M))
            if b["lit"]:
                lamps = [(x, y, 7.0 * M) for x, y, _ in instances(b)]
            elif bid == "dead_rig":
                x, y, _ = instances(b)[0]
                lamps = [(x, y, 30.0 * M)]
            for x, y, dz in lamps:
                z = (SEA_Z + max(0.0, height(x, y)) if b["kind"] not in ("rig", "dock", "jetty") else SEA_Z + 200) + dz
                radius = 90 if b["kind"] in ("pad", "dock", "hall") else 60
                out.append(actor("Light", f"Lamp{n}", (x, y, z),
                                 f"    LightBrightness=200.0\n    LightHue=22\n    LightSaturation=90\n    LightRadius={radius}\n"))
                n += 1
    d = ROOM_LEN / 2 - PLAYER_FROM_GLASS
    out.append(actor("PlayerStart", "PlayerStart0", (d * math.cos(a), d * math.sin(a), ROOM_Z + 100), "", (0, yaw(LOOK_YAW), 0)))
    out.append("End Map\n")
    open(path, "w").write("".join(out))


if __name__ == "__main__":
    citizens, buildings = binder.load()
    problems, _ = binder.check(citizens, buildings, verbose=False)
    if problems:
        print("the binder has problems (python tools/binder.py); building anyway:")
        for p in problems:
            print("  ", p)
    ROADS[:] = roads_from(citizens, buildings)
    print(len(ROADS), "tracks from the routines")
    ase = os.path.join(HERE, "Models", "ase")
    os.makedirs(ase, exist_ok=True)
    manifest = []           # (mesh name, group, texture for the actor or "")
    for ti in range(TILES):
        for tj in range(TILES):
            for m, part in enumerate(tile(ti, tj)):
                if part is None:
                    continue
                name = f"Ground{ti}{tj}{MAT_NAMES[m]}"
                write_ase(os.path.join(ase, name + ".ase"), name, *part)
                manifest.append((name, "Ground", MAT_TEX[m]))
    write_ase(os.path.join(ase, "Sea.ase"), "Sea", *sea()); manifest.append(("Sea", "Ground", SEA_SHADER))
    write_ase(os.path.join(ase, "Tower.ase"), "Tower", *tower()); manifest.append(("Tower", "Tower", ""))
    write_ase(os.path.join(ase, "Room.ase"), "Room", *room()); manifest.append(("Room", "Tower", ""))
    write_ase(os.path.join(ase, "Quay.ase"), "Quay", *quay(buildings["dock"])); manifest.append(("Quay", "Liandri", ""))
    manifest.append(("Pipeline", "Liandri", ""))
    manifest.append(("Fence", "Liandri", ""))
    manifest.append(("Floodmasts", "Liandri", ""))
    bounds = json.load(open(os.path.join(ase, "bounds.json")))
    BOUNDS.update(bounds)
    for b in sorted(bounds):
        manifest.append((b, "Liandri", ""))
    cards_dir = os.path.join(HERE, "Models", "cards")
    for b in buildings.values():
        if b.get("card"):
            base = b["card"].split()[0]
            for i in range(8):
                if os.path.exists(os.path.join(cards_dir, f"{base}{i}.tga")):
                    manifest.append((f"{base}{i}", "Cards", os.path.join("Models", "cards", f"{base}{i}.tga")))
    # the baked textures (one per mesh) for build_avalon's TEXTURE IMPORT: "name Bake <tga path>"
    for b in sorted(bounds):
        tex = bounds[b].get("texture", "Pal")
        if tex != "Pal":
            manifest.append((tex, "Bake", os.path.join("Models", "bake", tex + ".tga")))
    with open(os.path.join(ase, "manifest.txt"), "w") as f:
        for name, group, tex in manifest:
            f.write(f"{name} {group} {tex}\n")
    write_actors(os.path.join(HERE, "avalon_actors_dusk.t3d" if DUSK else "avalon_actors.t3d"), bounds,
                 [m for m in manifest if m[0] != "Sea"], buildings)
    counts = {g: sum(1 for m in manifest if m[1] == g) for g in ("Ground", "Tower", "Liandri")}
    px, py = from_frame(*PLANT_AT)
    print("meshes", counts, " tower hill %.0f  plant shelf %.0f  shore(%.0f) at %.0f  rig %.0f" % (
        height(0, 0), height(px, py), SHORE, height(*from_frame(SHORE, 0)), height(*from_frame(22500, 6800))))
