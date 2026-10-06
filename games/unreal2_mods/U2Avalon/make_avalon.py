"""Avalon, remade: the Liandri plant seen from the Authority's tower, as a real map.

    python make_avalon.py           meshes (terrain tiles, sea, tower) + avalon_actors.t3d
    python build_avalon.py assets   -> StaticMeshes/AvalonSM.usx (buildings, palette, terrain, tower)
    python build_avalon.py map      -> Maps/Avalon.un2 (+ paths)

Stage 1 = the outside world, in TutA's coordinates so the U2AvalonCards layouts carry over:
  sea level Z = -4967 (TutA's sea surface), the tower at (0,0) with its command room ~9200 above the sea,
  the player on a balcony at (-250,1100) looking ~300 degrees out over the plant.
  land: a hill under the tower falling to a shore to the north-west (+X,-Y), high ground to the south-west
  (-X,-Y: the radio mast's hill) and east; sea beyond the shore line.
World is -WORLD..WORLD (the engine's limit); the dead rig moves in from 30000 to 26000.
Buildings: tools\\glb_to_ase.py's ASE meshes, scaled by DrawScale to the heights of the cube blockout
(U2AvalonCards/layout_liandri_blocks.txt). Same ASE conventions as U2Hover/make_map.py.
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
from ase import write_ase, tri_facing  # noqa

WORLD = 30720
N = 240                 # heightfield cells per side (256 units)
TILES = 8
SEA_Z = -4967.0         # world Z of the sea surface
SKY_Z = 20000           # centre of the sky room: the big room brush again, stacked above the main room (build_avalon.py)
UV_TILE = 1024.0
TOWER = (0.0, 0.0)
ROOM_Z = SEA_Z + 9200   # the command room's floor
LOOK_YAW = 300          # degrees
# the player stands at the balcony's rim on the look side (standing in the middle of a 1700-unit disc,
# the floor hides everything below 4 degrees); the real room (stage 2) puts the window at (-250,1100)
BALCONY = (1550 * math.cos(math.radians(LOOK_YAW)), 1550 * math.sin(math.radians(LOOK_YAW)))

random.seed(11)
HILLS = [(random.uniform(-WORLD, WORLD), random.uniform(-WORLD, WORLD), random.uniform(1500, 4000),
          random.uniform(300, 1200)) for _ in range(40)]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def height(x, y):
    """land height above the sea (negative = sea floor)"""
    # the base slope: from +2200 at the tower's hill down to the shore line, which runs from the
    # north (y>0, x~-6000) round to the east (x~9000, y<0); everything beyond is sea
    dx, dy = x - TOWER[0], y - TOWER[1]
    along = dx * math.cos(math.radians(LOOK_YAW)) + dy * math.sin(math.radians(LOOK_YAW))   # toward the sea
    across = -dx * math.sin(math.radians(LOOK_YAW)) + dy * math.cos(math.radians(LOOK_YAW))
    shore = 7000 + 1500 * math.sin(across / 4000.0) + 600 * math.sin(across / 1300.0 + 1)
    h = 2200 * smooth((shore - along) / 9000.0) - 20
    # the plant's shelf: flat ground at +250 where the plant stands (x 2000..7000, y -11500..-4500)
    shelf = smooth((4500 - math.hypot((x - 4500) / 1.0, (y - -8000) / 1.4)) / 1500.0)
    h = h * (1 - shelf) + shelf * 250
    # hills on the land only, the big one under the radio mast
    land = smooth((shore - along + 2000) / 3000.0)
    for cx, cy, r, amp in HILLS:
        h += amp * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r)) * land * (1 - shelf)
    h += 3200 * math.exp(-((x + 12849) ** 2 + (y + 8612) ** 2) / (5000.0 ** 2))
    h += 2600 * math.exp(-(dx * dx + dy * dy) / (2600.0 ** 2))          # the tower's own hill
    # the sea floor falls away gently
    if along > shore:
        h -= 600 * smooth((along - shore) / 6000.0)
    # the rim: land rises toward the walls on the land sides
    edge = WORLD - max(abs(x), abs(y))
    if along < shore - 3000:
        h += 3000 * smooth((5000 - edge) / 5000.0)
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


# palette swatches (tools\glb_to_ase.py's Pal.tga, 8x8 cells): the order the buildings' materials came in
def sw(i):
    return ((i % 8 + 0.5) / 8.0, (i // 8 + 0.5) / 8.0)


def tower():
    """the Authority's tower as a shell: a tapering shaft, the command-room drum near the top, a balcony
    ring at the room's floor (where the player stands for now), a cap and a mast. Heights relative to SEA_Z."""
    verts, uvs, tris = [], [], []
    ground = height(*TOWER)
    room = ROOM_Z - SEA_Z
    cylinder(verts, uvs, tris, 0, 0, ground - 400, room - 600, 1400, 900, uv=sw(0), cap=False)
    cylinder(verts, uvs, tris, 0, 0, room - 600, room - 100, 900, 1700, uv=sw(0), cap=False)
    cylinder(verts, uvs, tris, 0, 0, room - 100, room, 1700, 1700, uv=sw(1), cap=True)    # the balcony floor
    cylinder(verts, uvs, tris, 0, 0, room, room + 700, 1250, 1250, uv=sw(3), cap=False)   # the room (dark glass band)
    cylinder(verts, uvs, tris, 0, 0, room + 700, room + 1500, 1300, 500, uv=sw(0), cap=True)
    cylinder(verts, uvs, tris, 0, 0, room + 1500, room + 3200, 60, 60, n=8, uv=sw(3), cap=True)   # the mast
    return verts, uvs, tris


def cube_brush(name, z, half=256, csg="CSG_Subtract"):
    """a cube brush actor for the T3D (the sky room): built from the subtractive-brush format UnrealEd exports.
    MAP IMPORTADD takes it and MAP REBUILD carves it; this avoids BRUSH LOAD, which keeps the builder brush's
    MainScale from the last loaded file (so a 'small' sky cube came out room-sized and merged the two zones)."""
    h = half
    faces = [  # (normal, four vertices counter-clockwise seen from outside)
        ((-1, 0, 0), [(-h, -h, -h), (-h, -h, h), (-h, h, h), (-h, h, -h)]),
        ((0, 1, 0), [(-h, h, -h), (-h, h, h), (h, h, h), (h, h, -h)]),
        ((1, 0, 0), [(h, h, -h), (h, h, h), (h, -h, h), (h, -h, -h)]),
        ((0, -1, 0), [(h, -h, -h), (h, -h, h), (-h, -h, h), (-h, -h, -h)]),
        ((0, 0, 1), [(-h, h, h), (-h, -h, h), (h, -h, h), (h, h, h)]),
        ((0, 0, -1), [(-h, -h, -h), (-h, h, -h), (h, h, -h), (h, -h, -h)]),
    ]
    L = [f"Begin Actor Class=Brush Name={name}", f"    CsgOper={csg}", f"    Location=(X=0.0,Y=0.0,Z={z:.1f})",
         f"    Begin Brush Name={name}Model", "       Begin PolyList"]
    for n, vs in faces:
        u = (0, 1, 0) if n[0] else (1, 0, 0)
        v = (0, 0, -1) if n[2] == 0 else (0, 1, 0)
        L += ["          Begin Polygon",
              "             Origin   %+013.6f,%+013.6f,%+013.6f" % vs[0],
              "             Normal   %+013.6f,%+013.6f,%+013.6f" % n,
              "             TextureU %+013.6f,%+013.6f,%+013.6f" % tuple(c / 128.0 for c in u),
              "             TextureV %+013.6f,%+013.6f,%+013.6f" % tuple(c / 128.0 for c in v)]
        L += ["             Vertex   %+013.6f,%+013.6f,%+013.6f" % p for p in vs]
        L.append("          End Polygon")
    L += ["       End PolyList", "    End Brush", "End Actor"]   # no Brush= line: the importer binds the model itself
    return "\n".join(L) + "\n"


def actor(cls, name, loc, props="", rot=None):
    x, y, z = loc
    r = f"    Rotation=(Pitch={rot[0]},Yaw={rot[1]},Roll={rot[2]})\n" if rot else ""
    return (f"Begin Actor Class={cls} Name={name}\n"
            f"    Location=(X={x:.1f},Y={y:.1f},Z={z:.1f})\n{r}{props}End Actor\n")


def yaw(deg):
    return int(deg * 65536 / 360.0) & 65535


# the plant: (mesh, x, y, yaw degrees, target height in world units)  from layout_liandri_blocks.txt
PLANT = [
    ("CoolingTower", 6300, -6000, 45, 2600), ("CoolingTower", 6500, -7600, 45, 2400),
    ("ProcessingHall", 3000, -6200, 30, 900), ("ProcessingHall", 2600, -8400, 30, 1100), ("ProcessingHall", 4300, -9700, 30, 700),
    ("StorageTank", 4700, -5400, 0, 800), ("StorageTank", 5500, -5000, 0, 800), ("StorageTank", 4900, -6600, 0, 800), ("StorageTank", 5700, -6400, 0, 800),
    ("OreTank", 5000, -8000, 0, 900), ("OreTank", 5700, -8500, 0, 900), ("OreTank", 5200, -9100, 0, 900),
    ("CargoDropship", 3900, -11200, 20, 600),
    ("DockCrane", 12300, -5800, 345, 1900),
    ("DrillingRig", 17151, -16112, 0, 4000), ("DeadRig", 26000, -11000, 20, 3400),
    ("Pylon", 4200, -5000, 0, 1500), ("Pylon", 3000, -3600, 0, 1500), ("Pylon", 1800, -2200, 0, 1500),
    ("RadioMast", -12849, -8612, 0, 4200),
]
TERRAIN_TEX = "Texture'Mission_10T.Terrain.BryoTerr_U10B740_'"
SEA_SHADER = "Shader'JungleT.Water.WaterSurfaceM081'"
NO_COLLISION = "    bCollideActors=False\n    bBlockActors=False\n    bBlockPlayers=False\n"


def write_actors(path, bounds):
    # (cube_brush("SkyRoom", SKY_Z) is NOT used: an imported Brush actor is ignored by MAP REBUILD, and without
    # a Brush= line the importer crashes in PrepBrush; the sky room is carved by build_avalon.py instead)
    out = ["Begin Map\n"]
    for ti in range(TILES):
        for tj in range(TILES):
            out.append(actor("StaticMeshActor", f"Ground{ti}{tj}", (0, 0, SEA_Z),
                             f"    StaticMesh=StaticMesh'AvalonSM.Ground.Ground{ti}{tj}'\n    Skins(0)={TERRAIN_TEX}\n"))
    out.append(actor("StaticMeshActor", "Sea", (0, 0, SEA_Z),
                     f"    StaticMesh=StaticMesh'AvalonSM.Ground.Sea'\n    Skins(0)={SEA_SHADER}\n"
                     "    bBlockActors=False\n    bBlockPlayers=False\n    bBlockNonZeroExtentTraces=False\n"))
    out.append(actor("StaticMeshActor", "Tower", (0, 0, SEA_Z),
                     "    StaticMesh=StaticMesh'AvalonSM.Tower.Tower'\n    Skins(0)=Texture'AvalonSM.Pal.Pal'\n"))
    for k, (mesh, x, y, deg, h) in enumerate(PLANT):
        b = bounds[mesh]
        s = h / b["h"]
        # rigs stand on the sea (legs a little under it); everything else on the land (the ASE's origin is its bottom)
        z = SEA_Z + max(0.0, height(x, y)) if "Rig" not in mesh else SEA_Z - 0.12 * h
        out.append(actor("StaticMeshActor", f"{mesh}{k}", (x, y, z),
                         f"    StaticMesh=StaticMesh'AvalonSM.Liandri.{mesh}'\n    Skins(0)=Texture'AvalonSM.Pal.Pal'\n"
                         f"    DrawScale={s:.3f}\n", (0, yaw(deg), 0)))
    # sky, sun, ambient, start on the balcony
    out.append(actor("SkyZoneInfo", "SkyZoneInfo0", (0, 0, SKY_Z)))
    out.append(actor("StaticMeshActor", "SkyBox", (0, 0, SKY_Z),
                     "    StaticMesh=StaticMesh'HoverTestSM.SkyBox'\n    Skins(0)=Texture'HoverTestSM.SkyAtlas'\n    bUnlit=True\n" + NO_COLLISION))
    # a late-afternoon sun from the north-east, 30 degrees up: side light across the plant as seen from the
    # tower (a sun out over the sea backlights everything and the hills shade the plant)
    # the sun actor must stand in open air: actors are sunlit only if the trace toward it is clear, and
    # above the tower it was inside the tower mesh. 20000 units out, in the direction the light comes from.
    sf = math.radians(LOOK_YAW - 60 + 180)
    sun_at = (14000 * math.cos(sf) * math.cos(math.radians(30)), 14000 * math.sin(sf) * math.cos(math.radians(30)), 7000)
    out.append(actor("SunLight", "Sun0", sun_at,
                     "    LightBrightness=220.0\n    LightHue=24\n    LightSaturation=110\n", (-5461, yaw(LOOK_YAW - 60), 0)))
    out.append(actor("ZoneInfo", "ZoneInfo0", (0, 0, 0), "    AmbientBrightness=60\n    AmbientHue=160\n    AmbientSaturation=170\n"))
    bx, by = BALCONY
    out.append(actor("PlayerStart", "PlayerStart0", (bx, by, ROOM_Z + 120), "", (0, yaw(LOOK_YAW), 0)))
    out.append("End Map\n")
    open(path, "w").write("".join(out))


if __name__ == "__main__":
    ase = os.path.join(HERE, "Models", "ase")
    os.makedirs(ase, exist_ok=True)
    for ti in range(TILES):
        for tj in range(TILES):
            write_ase(os.path.join(ase, f"Ground{ti}{tj}.ase"), f"Ground{ti}{tj}", *tile(ti, tj))
    write_ase(os.path.join(ase, "Sea.ase"), "Sea", *sea())
    write_ase(os.path.join(ase, "Tower.ase"), "Tower", *tower())
    bounds = json.load(open(os.path.join(ase, "bounds.json")))
    write_actors(os.path.join(HERE, "avalon_actors.t3d"), bounds)
    print("tower hill %.0f  plant shelf %.0f  mast hill %.0f  shore(8000,-8000) %.0f  rig %.0f  balcony %.0f" % (
        height(0, 0), height(4500, -8000), height(-12849, -8612), height(8000, -8000), height(17151, -16112),
        height(*BALCONY)))
