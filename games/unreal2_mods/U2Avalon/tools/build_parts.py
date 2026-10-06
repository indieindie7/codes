"""The parts library: buildings assembled from parts, driven by the binder's building sheets.

    blender -b --python build_parts.py -- <out_dir> [ids=hall_a,dorm,...]

For every building sheet whose kind is one the library assembles (hall, office, dorm, house, pump, jetty,
pad) it writes <out_dir>/B_<id>.glb (metres, front = -Y, origin at the footprint's centre on the ground).
The other kinds (tank, silo, cooling, rig, mast, dock, tower) keep the scripted meshes from
U2AvalonCards/tools/build_buildings.py.

What a sheet decides (the Shenmue rule: a building is a reflection of its users and usage):
  size            footprint and height; storeys = height // 3.4 for office/dorm/house
  doors           per side: personnel (small, lit lamp over it), roller (wide, cart height), airlock (a box)
  bays            a loading platform with a canopy on that side
  roof            flat (parapet), sawtooth (lit faces if lit), pitched, none
  wear            0..1: that share of wall panels are dark holes or rust, roof panels missing, lamps dead
  lit             glow strips and lamps on; off = dark glass
  kind            office/house: pale walls, window strips, a stair if 2 storeys; dorm: window strips both
                  long sides; hall: concrete, big volume; pump: small, pipes out the sea (back) side;
                  jetty: planks on posts; pad: a slab with light posts
"""
import math, os, random, sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import binder  # noqa

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(a[0])
o = dict(x.split("=", 1) for x in a[1:])
os.makedirs(out, exist_ok=True)
ONLY = set(o["ids"].split(",")) if "ids" in o else None

MATS = {}
COLOURS = {"concrete": (0.58, 0.58, 0.56), "pale": (0.70, 0.70, 0.68), "orange": (0.85, 0.34, 0.07),
           "dark": (0.18, 0.19, 0.21), "rust": (0.42, 0.22, 0.12), "glow": (1.0, 0.45, 0.1)}
PANEL = 4.0          # wall panel width, metres
STOREY = 3.4


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = COLOURS[name] + (1,)
        bsdf.inputs["Roughness"].default_value = 0.85 if name != "glow" else 0.4
        if name == "glow":
            bsdf.inputs["Emission Color"].default_value = COLOURS[name] + (1,)
            bsdf.inputs["Emission Strength"].default_value = 4
        MATS[name] = m
    return MATS[name]


def box(x, y, z, sx, sy, sz, m="concrete", rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ob.data.materials.append(mat(m))
    return ob


def cyl(x, y, z, r, h, m="concrete", n=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h)
    ob = bpy.context.object
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ob.data.materials.append(mat(m))
    return ob


# --- side geometry: a side is (outward normal (nx, ny), the wall's centre line offset, its length) ---
def sides(W, D):
    return {"front": ((0, -1), D / 2, W), "back": ((0, 1), D / 2, W), "left": ((-1, 0), W / 2, D), "right": ((1, 0), W / 2, D)}


def along_side(side, W, D, t):
    """a point on the side's wall face, t in -1..1 along it, returns (x, y, outward normal, rotation about Z)"""
    (nx, ny), off, length = sides(W, D)[side]
    x, y = nx * off, ny * off
    if nx == 0:
        x += t * length / 2
    else:
        y += t * length / 2
    rot = math.atan2(ny, nx)
    return x, y, (nx, ny), rot


def wall_panels(side, W, D, H, wear, base_mat, rng, keep=()):
    """the side's wall as PANEL-wide panels; wear turns some into dark holes or rust; keep = t ranges
    (t0, t1) that must stay whole (where doors are)"""
    (nx, ny), off, length = sides(W, D)[side]
    n = max(1, int(round(length / PANEL)))
    pw = length / n
    for i in range(n):
        t = -1 + (i + 0.5) * 2.0 / n
        x, y, _, rot = along_side(side, W, D, t)
        m = base_mat
        r = rng.random()
        if not any(t0 <= t <= t1 for t0, t1 in keep):
            if r < wear * 0.35:
                m = "dark"             # a missing panel: the dark inside shows
            elif r < wear * 0.8:
                m = "rust"
        box(x - nx * 0.15, y - ny * 0.15, H / 2, 0.3, pw - 0.08, H, m, (0, 0, rot))


def door(side, W, D, t, typ, lit, wear):
    x, y, (nx, ny), rot = along_side(side, W, D, t)
    if typ == "roller":
        w, h = 4.0, 4.0
    elif typ == "airlock":
        w, h = 2.0, 3.0
    else:
        w, h = 1.3, 2.6
    if typ == "airlock":
        box(x + nx * 0.9, y + ny * 0.9, h / 2, 1.8, w + 0.6, h + 0.3, "dark", (0, 0, rot))
        box(x + nx * 1.85, y + ny * 1.85, h / 2 - 0.2, 0.1, w - 0.6, h - 0.8, "orange", (0, 0, rot))
    else:
        box(x + nx * 0.05, y + ny * 0.05, h / 2 + 0.1, 0.12, w + 0.4, h + 0.4, "orange", (0, 0, rot))
        box(x + nx * 0.10, y + ny * 0.10, h / 2, 0.12, w, h, "dark", (0, 0, rot))
    if lit and wear < 0.7:
        box(x + nx * 0.35, y + ny * 0.35, h + 0.7, 0.4, 0.8, 0.25, "glow", (0, 0, rot))      # the lamp over the door
    return w


def bay(side, W, D, t, lit):
    x, y, (nx, ny), rot = along_side(side, W, D, t)
    box(x + nx * 1.6, y + ny * 1.6, 0.6, 3.2, 7.0, 1.2, "concrete", (0, 0, rot))             # platform
    box(x + nx * 2.0, y + ny * 2.0, 4.6, 4.0, 7.6, 0.3, "dark", (0, 0, rot))                 # canopy
    for s in (-1, 1):
        box(x + nx * 3.7 + s * (-ny) * 3.4, y + ny * 3.7 + s * nx * 3.4, 2.3, 0.3, 0.3, 4.6, "dark", (0, 0, rot))
    if lit:
        box(x + nx * 2.0, y + ny * 2.0, 4.4, 3.0, 0.3, 0.2, "glow", (0, 0, rot))


def window_strip(side, W, D, z, lit, wear, rng):
    (nx, ny), off, length = sides(W, D)[side]
    x, y, _, rot = along_side(side, W, D, 0)
    m = "glow" if lit and rng.random() > wear else "dark"
    box(x - nx * 0.05, y - ny * 0.05, z, 0.14, length * 0.8, 0.9, m, (0, 0, rot))


def roof(kind, W, D, H, lit, wear, rng):
    if kind == "flat":
        box(0, 0, H + 0.2, W + 0.4, D + 0.4, 0.4, "pale")
        for side in ("front", "back", "left", "right"):
            x, y, (nx, ny), rot = along_side(side, W, D, 0)
            box(x + nx * 0.1, y + ny * 0.1, H + 0.7, 0.3, (W if nx == 0 else D) + 0.4, 0.7, "pale", (0, 0, rot))
        cyl(W * 0.3, D * 0.2, H + 1.2, 0.5, 1.6, "dark", 10)                                  # a vent
        box(-W * 0.3, -D * 0.2, H + 0.9, 1.6, 1.2, 1.0, "dark")                                # an AC box
    elif kind == "sawtooth":
        # the ref-sheet hall has a heavy flat slab overhanging the walls (the silhouette check missed it):
        # a 1.5 m overhang all round, the teeth sit on it
        box(0, 0, H + 0.25, W + 3.0, D + 3.0, 0.5, "concrete")
        n = max(2, int(W // 6))
        pitch = W / n
        for i in range(n):
            x = -W / 2 + (i + 0.5) * pitch
            missing = rng.random() < wear * 0.5
            if not missing:
                box(x, 0, H + 1.0, pitch * 0.97, D, 1.8, "pale", (0, math.radians(18), 0))
            box(x + pitch * 0.42, 0, H + 1.0, 0.3, D * 0.96, 2.4, "glow" if lit and not missing else "dark")
    elif kind == "pitched":
        for s in (-1, 1):
            if rng.random() < wear * 0.4:
                continue
            box(0, s * D / 4, H + 0.9, W + 0.6, D / 2 + 0.6, 0.3, "pale", (s * math.radians(-22), 0, 0))
        box(0, 0, H + 1.9, W + 0.8, 0.5, 0.4, "dark")


def stair(side, W, D, H):
    x, y, (nx, ny), rot = along_side(side, W, D, 0.6)
    box(x + nx * 1.0, y + ny * 1.0, H / 2, 1.8, 3.6, H, "dark", (0, 0, rot))


def building(b, rng):
    kind = b["kind"]
    W, D, H = b["size"]
    lit, wear = b["lit"], b["wear"]
    doors = b.get("doors", {})
    bays = b.get("bays", [])
    if kind == "jetty":
        for i in range(int(W // 2)):
            x = -W / 2 + 1 + i * 2
            if rng.random() < wear * 0.5:
                continue
            box(x, 0, H - 0.1, 1.9, D, 0.2, "rust")
            if i % 2 == 0:
                for s in (-1, 1):
                    cyl(x, s * (D / 2 - 0.4), H / 2 - 0.4, 0.2, H + 1.0, "dark", 8)
        if lit:
            box(W / 2 - 1, 0, H + 1.6, 0.3, 0.3, 0.3, "glow")
        return
    if kind == "pad":
        box(0, 0, 0.5, W, D, 1.0, "concrete")
        box(0, 0, 1.02, W * 0.72, D * 0.72, 0.06, "dark")
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (W / 2 - 1.5), sy * (D / 2 - 1.5)
                cyl(x, y, 3.5, 0.2, 5.0, "dark", 8)
                if lit:
                    box(x, y, 6.2, 0.9, 0.9, 0.4, "glow")
        for k in range(4):                                                                 # edge markings
            t = -0.6 + k * 0.4
            box(t * W / 2, -D / 2 + 1.2, 1.03, 1.2, 0.3, 0.05, "orange")
        return
    # a walled building
    base = "pale" if kind in ("office", "house") else "concrete"
    storeys = max(1, int(H // STOREY)) if kind in ("office", "dorm", "house") else 1
    keep = {s: [] for s in sides(W, D)}
    spots = {}
    for side, typ in doors.items():
        ts = {"front": 0.0, "back": 0.0, "left": -0.2, "right": 0.2}[side]
        if side in bays:
            ts = -0.45
        spots[side] = ts
        keep[side].append((ts - 0.3, ts + 0.3))
    for side in sides(W, D):
        wall_panels(side, W, D, H, wear, base, rng, keep[side])
    box(0, 0, H / 2, W - 0.5, D - 0.5, H, "dark")                                               # the inside, dark
    box(0, 0, H + 0.05, W, D, 0.1, "pale" if base == "pale" else "concrete")                    # roof slab
    for side, typ in doors.items():
        door(side, W, D, spots[side], typ, lit, wear)
    for side in bays:
        bay(side, W, D, 0.45, lit)
    if kind in ("office", "dorm", "house"):
        for k in range(storeys):
            for side in (("front", "back") if kind == "dorm" else ("front", "right", "left")):
                window_strip(side, W, D, k * STOREY + 2.2, lit, wear, rng)
        if storeys > 1:
            stair("back" if kind != "dorm" else "left", W, D, H)
    if kind == "pump":
        for i, dy in enumerate((-0.3, 0.0, 0.3)):                                              # pipes out the back
            cyl(dy * W, D / 2 + 3.0, 0.6 + 0.3 * i, 0.35, 6.0, "rust" if wear > 0.3 else "dark", 10, (math.pi / 2, 0, 0))
        cyl(W * 0.3, 0, H + 1.5, 0.6, 3.0, "dark", 10)
        cyl(-W * 0.3, 0, H + 1.2, 0.6, 2.4, "dark", 10)
    if kind == "office":
        # the company's only ornament: a dish on the roof and a flag-pole stub
        cyl(W * 0.3, -D * 0.25, H + 1.0, 0.25, 1.6, "dark", 8)
        cyl(W * 0.3, -D * 0.25, H + 2.0, 1.6, 0.25, "pale", 16, (math.radians(50), 0, 0))
        cyl(-W * 0.4, D * 0.3, H + 2.5, 0.08, 5.0, "pale", 6)
    if kind == "dorm":
        # the annex nobody planned: a stack of containers against the right end, with a ladder
        for k, (dz, dy) in enumerate(((1.3, -1.6), (1.3, 1.6), (3.9, 0.0))):
            box(W / 2 + 1.6, dy, dz, 2.6, 6.2, 2.5, "rust" if k != 1 else "dark")
        box(W / 2 + 3.0, 3.4, 2.6, 0.3, 0.6, 5.2, "dark")
    if kind == "pad" and "authority" in b["id"]:
        # the Authority's one antenna, on a guyed pole at the pad's corner
        cyl(W / 2 - 2.5, D / 2 - 2.5, 7.0, 0.15, 12.0, "pale", 8)
        box(W / 2 - 2.5, D / 2 - 2.5, 12.6, 2.4, 0.2, 0.9, "dark")
    if kind == "hall" and "generator" in b["id"]:
        cyl(W * 0.25, D * 0.1, H + 2.5, 0.7, 5.0, "dark", 12)
        cyl(-W * 0.25, D * 0.1, H + 2.5, 0.7, 5.0, "dark", 12)
    roof(b.get("roof", "flat"), W, D, H, lit, wear, rng)


ASSEMBLED = ("hall", "office", "dorm", "house", "pump", "jetty", "pad")
citizens, buildings = binder.load()
for bid, b in buildings.items():
    if b["kind"] not in ASSEMBLED or "size" not in b:
        continue
    if ONLY and bid not in ONLY:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    rng = random.Random(hash(bid) & 0xffff)
    building(b, rng)
    for ob in bpy.context.scene.objects:
        ob.select_set(ob.type == "MESH")
    path = os.path.join(out, f"B_{bid}.glb")
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLB", export_apply=True)
    print("BUILT", bid, b["kind"], b["size"], "wear", b["wear"], "->", path)
