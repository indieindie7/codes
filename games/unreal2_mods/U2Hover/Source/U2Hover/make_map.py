"""Generate the HoverTest map's pieces (the map itself is assembled in UnrealEd
by build_editor.py):

  Models/ase/Hills??.ase  heightfield tiles: rolling hills, a raised rim at the
                          walls, a river channel winding across the map
  Models/ase/River.ase    water surface strip following the river
  Models/ase/SkyBox.ase   inward-facing cube for the sky zone (atlas UVs)
  Textures/HillGrass.tga  tiling ground texture
  Textures/SkyAtlas.tga   Sanctuary's six sky faces (sky/*.png) in a 3x2 atlas
  hills_actors.t3d        everything placed in the level: ground tiles, water,
                          rocks, plants, sky zone, sun, zone, player start

Scenery is Unreal II's own (Mission_05M rocks and swamp plants), referenced,
not copied.

Unreal II's ASE importer mirrors X. Vertices are written with X negated, and a
triangle faces the way OPPOSITE to (v1-v0) x (v2-v0) of its real coordinates
(found in game with the hills).
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = 10240           # main room is -ROOM..ROOM in X and Y, -3072..3072 in Z
N = 80                 # heightfield cells per side (256 units)
TILES = 5              # TILES x TILES meshes (one huge mesh gets no collision)
FLOOR_Z = -2750        # world Z of height 0 (room floor is at -3072)
WATER = -120           # water surface, relative to FLOOR_Z
SKY_Z = 10000          # centre of the sky room (outside the main room)
UV_TILE = 1024.0

random.seed(7)
HILLS = [(random.uniform(-8000, 8000), random.uniform(-8000, 8000),
          random.uniform(500, 1300), random.uniform(250, 900)) for _ in range(26)]
HILLS.append((4200, -1200, 900, 700))          # a long rise ahead of the start


def river_y(x):
    return 3200 + 1500 * math.sin(x / 2600.0) + 500 * math.sin(x / 900.0 + 1.3)


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def height(x, y):
    h = 0.0
    for cx, cy, r, amp in HILLS:
        h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))
    h *= smooth((math.hypot(x, y) - 900) / 1200)          # flat start area
    # rim: the land rises to hide the walls
    edge = ROOM - max(abs(x), abs(y))
    wobble = 700 * math.sin(x / 1300.0 + 0.7) * math.sin(y / 1700.0 + 2.1) + 400 * math.sin((x + y) / 800.0)
    h += (1500 + wobble) * smooth((3400 + 0.6 * wobble - edge) / 3400)
    # river channel
    d = abs(y - river_y(x))
    bank = smooth((d - 380) / 520)                         # 0 in the channel, 1 on land
    return h * bank + (1 - bank) * -260


# --- ASE -------------------------------------------------------------------

def tri_facing(v, tri, want):
    """Order tri so that it faces WANT after import (see module docstring)."""
    a, b, c = (v[i] for i in tri)
    u = [b[k] - a[k] for k in range(3)]
    w = [c[k] - a[k] for k in range(3)]
    n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
    if sum(n[k] * want[k] for k in range(3)) > 0:
        return (tri[0], tri[2], tri[1])
    return tri


def write_ase(path, name, verts, uvs, tris):
    L = ["*3DSMAX_ASCIIEXPORT 200", "*GEOMOBJECT {", f'\t*NODE_NAME "{name}"', "\t*MESH {",
         f"\t\t*MESH_NUMVERTEX {len(verts)}", f"\t\t*MESH_NUMFACES {len(tris)}", "\t\t*MESH_VERTEX_LIST {"]
    L += [f"\t\t\t*MESH_VERTEX {k} {-v[0]:.3f} {v[1]:.3f} {v[2]:.3f}" for k, v in enumerate(verts)]
    L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
    L += [f"\t\t\t*MESH_FACE {k}: A: {t[0]} B: {t[1]} C: {t[2]} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0"
          for k, t in enumerate(tris)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(uvs)}", "\t\t*MESH_TVERTLIST {"]
    L += [f"\t\t\t*MESH_TVERT {k} {t[0]:.5f} {t[1]:.5f} 0.0000" for k, t in enumerate(uvs)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(tris)}", "\t\t*MESH_TFACELIST {"]
    L += [f"\t\t\t*MESH_TFACE {k} {t[0]} {t[1]} {t[2]}" for k, t in enumerate(tris)]
    L += ["\t\t}", "\t}", "}"]
    open(path, "w").write("\n".join(L) + "\n")


def hills_tile(ti, tj):
    T = N // TILES
    step = 2 * ROOM / N
    verts, uvs, tris = [], [], []
    for j in range(tj * T, tj * T + T + 1):
        for i in range(ti * T, ti * T + T + 1):
            x, y = -ROOM + i * step, -ROOM + j * step
            verts.append((x, y, height(x, y)))
            uvs.append((x / UV_TILE, -y / UV_TILE))
    for j in range(T):
        for i in range(T):
            a = j * (T + 1) + i; b = a + 1; c = a + T + 1; d = c + 1
            tris += [tri_facing(verts, (a, b, d), (0, 0, 1)), tri_facing(verts, (a, d, c), (0, 0, 1))]
    return verts, uvs, tris


def river_strip():
    verts, uvs, tris = [], [], []
    xs = [-ROOM + k * 256 for k in range(int(2 * ROOM / 256) + 1)]
    for k, x in enumerate(xs):
        yc = river_y(x)
        for s in (-1, 1):
            verts.append((x, yc + s * 760, WATER))
            uvs.append((x / 512.0, s * 760 / 512.0))
        if k:
            a, b, c, d = 2 * k - 2, 2 * k - 1, 2 * k, 2 * k + 1
            tris += [tri_facing(verts, (a, c, d), (0, 0, 1)), tri_facing(verts, (a, d, b), (0, 0, 1))]
    return verts, uvs, tris


# sky atlas cells (col, row) in a 4x2 grid of 512 squares (2048x1024: the
# importer wants power-of-two sizes; two cells stay empty)
SKY_CELLS = {"UP": (0, 0), "DN": (1, 0), "LF": (2, 0), "RT": (0, 1), "FR": (1, 1), "BK": (2, 1)}


def skybox(s=400.0):
    """Inward-facing cube. Looking along +X you see FR, turning right (+Y) RT,
    then BK (-X) and LF (-Y); UP/DN have +X at their top edge."""
    faces = [  # name, 4 corners in order: top-left, top-right, bottom-right, bottom-left (seen from inside)
        ("FR", [(s, -s, s), (s, s, s), (s, s, -s), (s, -s, -s)]),
        ("RT", [(s, s, s), (-s, s, s), (-s, s, -s), (s, s, -s)]),
        ("BK", [(-s, s, s), (-s, -s, s), (-s, -s, -s), (-s, s, -s)]),
        ("LF", [(-s, -s, s), (s, -s, s), (s, -s, -s), (-s, -s, -s)]),
        ("UP", [(s, -s, s), (s, s, s), (-s, s, s), (-s, -s, s)]),
        ("DN", [(-s, -s, -s), (-s, s, -s), (s, s, -s), (s, -s, -s)]),
    ]
    verts, uvs, tris = [], [], []
    e = 1.5 / 512                                # stay off the cell edges
    for name, quad in faces:
        col, row = SKY_CELLS[name]
        u0, v0 = col / 4.0 + e, row / 2.0 + e
        u1, v1 = (col + 1) / 4.0 - e, (row + 1) / 2.0 - e
        base = len(verts)
        verts += quad
        uvs += [(u0, 1 - v0), (u1, 1 - v0), (u1, 1 - v1), (u0, 1 - v1)]
        centre = [sum(p[k] for p in quad) / 4 for k in range(3)]
        inward = [-c for c in centre]
        tris += [tri_facing(verts, (base, base + 1, base + 2), inward),
                 tri_facing(verts, (base, base + 2, base + 3), inward)]
    return verts, uvs, tris


# --- textures ----------------------------------------------------------------

def write_grass(path):
    im = Image.new("RGB", (256, 256))
    px = im.load()
    for y in range(256):
        for x in range(256):
            n = random.randint(-18, 18)
            px[x, y] = (70 + n, 115 + n, 45 + n // 2)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    ImageDraw.Draw(im).rectangle([0, 0, 255, 255], outline=(60, 98, 40), width=1)
    im.save(path)


def _edges(im):
    """Mean colour along each edge, 64 samples: top/bottom left->right, left/right top->bottom."""
    a = im.resize((64, 64)).load()
    top = [a[i, 0] for i in range(64)]; bottom = [a[i, 63] for i in range(64)]
    left = [a[0, i] for i in range(64)]; right = [a[63, i] for i in range(64)]
    return top, bottom, left, right


def _diff(p, q):
    return sum(abs(x[c] - y[c]) for x, y in zip(p, q) for c in range(3))


def _variants(im):
    """The 8 rotations/mirrors of an image, with a label."""
    out = []
    for m in (False, True):
        b = im.transpose(Image.FLIP_LEFT_RIGHT) if m else im
        for r in (0, 90, 180, 270):
            out.append((("m" if m else "") + str(r), b.rotate(r, expand=True)))
    return out


def arrange_sky():
    """Which stock face goes on which side of the skybox, and how it must be
    turned, found by matching the edges where faces meet. Side slots in
    turn-right order: +X, +Y, -X, -Y (see skybox())."""
    from itertools import permutations
    img = {n: Image.open(os.path.join(HERE, "sky", f"m08_7_{n}.png")).convert("RGB") for n in SKY_CELLS}
    sides = ["FR", "RT", "BK", "LF"]
    best = None
    for order in permutations(sides):
        for mask in range(16):
            ims = [img[n].transpose(Image.FLIP_LEFT_RIGHT) if mask >> k & 1 else img[n] for k, n in enumerate(order)]
            e = [_edges(i) for i in ims]
            cost = sum(_diff(e[k][3], e[(k + 1) % 4][2]) for k in range(4))   # right edge meets next's left
            if best is None or cost < best[0]:
                best = (cost, order, ims)
    _, order, sides_im = best
    top_rows = [_edges(i)[0] for i in sides_im]
    bottom_rows = [_edges(i)[1] for i in sides_im]

    def cap(name, rows, is_up):
        bestc = None
        for label, v in _variants(img[name]):
            t, b, l, r = _edges(v)
            if is_up:   # top<->+X, right(top->bottom)<->+Y, bottom(reversed)<->-X, left(reversed)<->-Y
                cost = _diff(t, rows[0]) + _diff(r, rows[1]) + _diff(b[::-1], rows[2]) + _diff(l[::-1], rows[3])
            else:       # bottom<->+X, right(reversed)<->+Y, top(reversed)<->-X, left<->-Y
                cost = _diff(b, rows[0]) + _diff(r[::-1], rows[1]) + _diff(t[::-1], rows[2]) + _diff(l, rows[3])
            if bestc is None or cost < bestc[0]:
                bestc = (cost, v, label)
        return bestc

    up = cap("UP", top_rows, True)
    dn = cap("DN", bottom_rows, False)
    slots = {"+X": sides_im[0], "+Y": sides_im[1], "-X": sides_im[2], "-Y": sides_im[3], "UP": up[1], "DN": dn[1]}
    print("sky: +X %s, +Y %s, -X %s, -Y %s; UP %s, DN %s (edge cost %d)"
          % (order[0], order[1], order[2], order[3], up[2], dn[2], best[0]))
    return slots, order


# skybox() cell per slot: FR cell = +X, RT = +Y, BK = -X, LF = -Y
SLOT_CELL = {"+X": "FR", "+Y": "RT", "-X": "BK", "-Y": "LF", "UP": "UP", "DN": "DN"}


def write_sky_atlas(path):
    slots, order = arrange_sky()
    atlas = Image.new("RGB", (2048, 1024))
    for slot, im in slots.items():
        col, row = SKY_CELLS[SLOT_CELL[slot]]
        atlas.paste(im.resize((512, 512)), (col * 512, row * 512))
    atlas.save(path)
    # the sun is in the stock FR face: light travels away from its side
    return {"+X": 32768, "+Y": 49152, "-X": 0, "-Y": 16384}[["+X", "+Y", "-X", "-Y"][order.index("FR")]]


# --- level actors -------------------------------------------------------------

def actor(cls, name, loc, props="", rot=None):
    x, y, z = loc
    r = f"    Rotation=(Pitch={rot[0]},Yaw={rot[1]},Roll={rot[2]})\n" if rot else ""
    return (f"Begin Actor Class={cls} Name={name}\n"
            f"    Location=(X={x:.1f},Y={y:.1f},Z={z:.1f})\n{r}{props}End Actor\n")


ROCKS = ["Mission_05M.Misc.generic_rock_01", "Mission_05M.Misc.kai_stone_01",
         "Mission_05M.Misc.kai_stone_02", "Mission_05M.Misc.kai_stone_03"]
PLANTS = ["Mission_05M.Vegetation.swamp_underbrush_001", "Mission_05M.Vegetation.swamp_underbrush_003",
          "Mission_05M.Vegetation.highpoly_fern_02", "Mission_05M.Vegetation.highpoly_fern_03c",
          "Mission_05M.Vegetation.SwampPlantA02", "Mission_05M.Vegetation.SwampPlantA03",
          "Mission_05M.Vegetation.swamp_smallplant_002", "Mission_05M.Vegetation.swamp_smallplant_004",
          "Mission_05M.Vegetation.Swamp_GrassGroup_005"]
FLOWERS = ["Mission_05M.Vegetation.marsh_flowers_001"]     # tall stalks: only a few
TREES = ["Mission_05M.Vegetation.swamp_smalltree_deco"]
NO_COLLISION = "    bCollideActors=False\n    bBlockActors=False\n    bBlockPlayers=False\n"


def scatter(count, pick, near_river=False):
    out = []
    while len(out) < count:
        x, y = random.uniform(-ROOM + 900, ROOM - 900), random.uniform(-ROOM + 900, ROOM - 900)
        d = abs(y - river_y(x))
        if math.hypot(x, y) < 1400:                # keep the start clear
            continue
        if near_river and not (700 < d < 1500):
            continue
        if not near_river and d < 900:
            continue
        out.append((pick(), x, y))
    return out


def write_actors(path, sun_yaw=32768):
    out = ["Begin Map\n"]
    for ti in range(TILES):
        for tj in range(TILES):
            out.append(actor("StaticMeshActor", f"Hills{ti}{tj}", (0, 0, FLOOR_Z),
                             f"    StaticMesh=StaticMesh'HoverTestSM.Hills{ti}{tj}'\n"
                             "    Skins(0)=Texture'Mission_10T.Terrain.BryoTerr_U10B740_'\n"))
    # water: traces (the bike's repulsors, shots) hit it, walkers and the bike's body pass
    out.append(actor("StaticMeshActor", "RiverSurface", (0, 0, FLOOR_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.River'\n"
                     "    Skins(0)=Shader'JungleT.Water.WaterSurfaceM081'\n"
                     "    bBlockActors=False\n    bBlockPlayers=False\n    bBlockNonZeroExtentTraces=False\n"))
    k = 0
    def rock(x, y, s):
        return actor("StaticMeshActor", f"Rock{k}", (x, y, FLOOR_Z + height(x, y) - 8 * s),
                     f"    StaticMesh=StaticMesh'{random.choice(ROCKS)}'\n    DrawScale={s:.2f}\n",
                     (random.randint(-2500, 2500), random.randint(0, 65535), random.randint(-2500, 2500)))
    # loose rocks on the hills, bigger than before so they read from the bike
    for mesh, x, y in scatter(40, lambda: None):
        out.append(rock(x, y, random.uniform(1.5, 3.5)))
        k += 1
    # clusters along the river banks: a big boulder with smaller ones around it
    for c in range(16):
        x = -ROOM + 1500 + c * (2 * ROOM - 3000) / 15 + random.uniform(-400, 400)
        side = random.choice((-1, 1))
        cy = river_y(x) + side * random.uniform(620, 900)
        if math.hypot(x, cy) < 1400:
            continue
        out.append(rock(x, cy, random.uniform(3.0, 5.0)))
        k += 1
        for _ in range(random.randint(3, 6)):
            a = random.uniform(0, 2 * math.pi); r = random.uniform(180, 520)
            out.append(rock(x + r * math.cos(a), cy + r * math.sin(a), random.uniform(1.0, 2.5)))
            k += 1
    for mesh, x, y in scatter(160, lambda: random.choice(PLANTS)) + scatter(90, lambda: random.choice(PLANTS), True):
        s = random.uniform(0.8, 1.6)
        out.append(actor("StaticMeshActor", f"Plant{k}", (x, y, FLOOR_Z + height(x, y) - 4),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n" + NO_COLLISION,
                         (0, random.randint(0, 65535), 0)))
        k += 1
    for mesh, x, y in scatter(18, lambda: random.choice(FLOWERS)):
        s = random.uniform(0.7, 1.1)
        out.append(actor("StaticMeshActor", f"Flower{k}", (x, y, FLOOR_Z + height(x, y) - 4),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n" + NO_COLLISION,
                         (0, random.randint(0, 65535), 0)))
        k += 1
    for mesh, x, y in scatter(30, lambda: random.choice(TREES), True):
        s = random.uniform(0.9, 1.5)
        out.append(actor("StaticMeshActor", f"Tree{k}", (x, y, FLOOR_Z + height(x, y) - 10),
                         f"    StaticMesh=StaticMesh'{mesh}'\n    DrawScale={s:.2f}\n",
                         (0, random.randint(0, 65535), 0)))
        k += 1
    # sky zone: its own sealed room far above, holding the skybox cube
    out.append(actor("SkyZoneInfo", "SkyZoneInfo0", (0, 0, SKY_Z)))
    out.append(actor("StaticMeshActor", "SkyBox", (0, 0, SKY_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.SkyBox'\n"
                     "    Skins(0)=Texture'HoverTestSM.SkyAtlas'\n    bUnlit=True\n" + NO_COLLISION))
    # light: low sun from the sunny side (FR = +X), plus ambient
    out.append(actor("SunLight", "Sun0", (0, 0, 2500),
                     "    LightBrightness=110.0\n    LightHue=20\n    LightSaturation=210\n", (-6000, sun_yaw, 0)))
    out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=14\n"))
    out.append(actor("PlayerStart", "PlayerStart0", (0, 0, FLOOR_Z + 150)))
    # a few Skaarj out on the hills, facing the start (Marsh places them the same way)
    for n, (cls, x, y) in enumerate([("U2SkaarjLight", 5200, -2600), ("U2SkaarjLight", -4800, -4200),
                                     ("U2SkaarjMedium", 3000, 6800), ("U2SkaarjMedium", -6200, 1800)]):
        yaw = int(math.atan2(-y, -x) * 32768 / math.pi) & 65535
        out.append(actor("U2Pawns." + cls, f"Skaarj{n}", (x, y, FLOOR_Z + height(x, y) + 110), "", (0, yaw, 0)))
    out.append("End Map\n")
    open(path, "w").write("".join(out))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "Models", "ase"), exist_ok=True)
    for ti in range(TILES):
        for tj in range(TILES):
            write_ase(os.path.join(HERE, "Models", "ase", f"Hills{ti}{tj}.ase"), f"Hills{ti}{tj}", *hills_tile(ti, tj))
    write_ase(os.path.join(HERE, "Models", "ase", "River.ase"), "River", *river_strip())
    write_ase(os.path.join(HERE, "Models", "ase", "SkyBox.ase"), "SkyBox", *skybox())
    write_grass(os.path.join(HERE, "Textures", "HillGrass.tga"))
    sun_yaw = write_sky_atlas(os.path.join(HERE, "Textures", "SkyAtlas.tga"))
    write_actors(os.path.join(HERE, "hills_actors.t3d"), sun_yaw)
    print("heights %.0f..%.0f" % (min(height(-ROOM + i * 256, -ROOM + j * 256) for i in range(N + 1) for j in range(N + 1)),
                                  max(height(-ROOM + i * 256, -ROOM + j * 256) for i in range(N + 1) for j in range(N + 1))))
