"""Liandri buildings as SCRIPTED geometry: primitives and flat materials, built in Blender from the ref
sheets' descriptions (the img2threejs / blender-kiln idea: reconstruction by code, not a generated blob).

    blender -b --python build_buildings.py -- <out_dir> [names=cooling_tower,storage_tank,...]

Writes <out_dir>/<name>_script.glb per building (metres; the layout scales them anyway). Materials:
concrete grey, orange panels, dark steel, rust, orange glow. Each builder is a few primitives; edit the
numbers to match the sheet, score with fidelity.py, repeat.
"""
import math, os, sys
import bpy

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(a[0])
o = dict(x.split("=", 1) for x in a[1:])
os.makedirs(out, exist_ok=True)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "U2Avalon", "tools"))
import palette  # noqa  (the Liandri palette measured from the Hunyuan models; old names are aliased)

MATS = {}
COLOURS = palette.COLOURS


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = palette.colour(name) + (1,)
        bsdf.inputs["Roughness"].default_value = 0.85 if name != "glow" else 0.4
        if name == "glow":
            bsdf.inputs["Emission Color"].default_value = COLOURS[name] + (1,)
            bsdf.inputs["Emission Strength"].default_value = 4
        MATS[name] = m
    return MATS[name]


def place(ob, x, y, z, m, rot=(0, 0, 0)):
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ob.data.materials.append(mat(m))
    return ob


def box(x, y, z, sx, sy, sz, m="concrete", rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    return place(ob, x, y, z, m, rot)


def cyl(x, y, z, r, h, m="concrete", n=24, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r, radius2=r2, depth=h)
    return place(bpy.context.object, x, y, z, m, rot)


def sphere(x, y, z, r, m="concrete"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=24, ring_count=12)
    return place(bpy.context.object, x, y, z, m)


def ring_of(n, r, fn):
    for i in range(n):
        t = 2 * math.pi * i / n
        fn(r * math.cos(t), r * math.sin(t), t)


def doors(x, y, z, w, h, facing_y=True):
    """a dark doorway with an orange frame on a wall facing -Y (or -X)"""
    if facing_y:
        box(x, y - 0.02, z + h / 2, w + 0.3, 0.1, h + 0.3, "orange")
        box(x, y - 0.06, z + h / 2, w, 0.1, h, "dark")
    else:
        box(x - 0.02, y, z + h / 2, 0.1, w + 0.3, h + 0.3, "orange")
        box(x - 0.06, y, z + h / 2, 0.1, w, h, "dark")


def cooling_tower():
    cyl(0, 0, 2, 7, 4, "concrete", 32, 5.4)                    # flared base
    cyl(0, 0, 18, 5.2, 28, "concrete", 32)                     # shaft
    cyl(0, 0, 32.6, 5.6, 1.2, "pale", 32)                      # top rim
    cyl(0, 0, 33.4, 4.6, 0.6, "dark", 32)                      # vent mouth
    for sgn in (-1, 1):
        box(sgn * 3.6, -4.9, 16, 1.8, 0.4, 9, "orange")        # tall panels
        box(sgn * 3.6, -4.9, 26, 1.8, 0.4, 3, "orange")
    doors(0, -5.4, 0.2, 1.6, 2.6)
    ring_of(6, 5.4, lambda x, y, t: box(x, y, 2.2, 1.0, 1.0, 4.4, "pale", (0, 0, t)))   # base buttresses


def processing_hall():
    box(0, 0, 4, 30, 14, 8, "concrete")                        # hall
    for i in range(5):                                          # sawtooth roof
        x = -12 + i * 6
        box(x, 0, 9.0, 5.8, 14, 2, "pale", (0, math.radians(18), 0))
        box(x + 2.6, 0, 9.0, 0.3, 14, 2.6, "glow")             # the lit face of each tooth
    for i in range(4):
        doors(-10 + i * 6.5, -7, 0, 3, 4)
    box(-16, 0, 1.5, 4, 8, 3, "concrete")                      # loading bay
    box(16, 0, 1.5, 4, 8, 3, "concrete")
    ring_of(4, 0, lambda x, y, t: None)


def storage_tank():
    cyl(0, 0, 0.6, 6.5, 1.2, "dark", 32)                       # base ring
    cyl(0, 0, 5.5, 6, 8.6, "concrete", 32)                     # shell
    sphere(0, 0, 9.8, 6, "concrete")                           # dome (lower half inside the shell)
    for i in range(8):                                          # ribs
        t = 2 * math.pi * i / 8
        box(5.9 * math.cos(t), 5.9 * math.sin(t), 5.5, 0.5, 0.9, 8.6, "pale", (0, 0, t))
    box(0, -6.1, 5.5, 3.4, 0.3, 4, "orange")                    # panel
    cyl(0, 0, 13.2, 0.6, 1.6, "dark", 12)                      # valve stack
    box(2.2, -5.9, 2.5, 0.4, 0.5, 5, "dark")                    # ladder


def ore_tank():
    for i in range(4):                                          # legs
        t = math.pi / 4 + 2 * math.pi * i / 4
        box(3.2 * math.cos(t), 3.2 * math.sin(t), 2.5, 0.8, 0.8, 5, "dark", (0, 0, t))
    cyl(0, 0, 6.0, 4.4, 3.0, "dark", 8, 1.2)                   # hopper (cone)
    cyl(0, 0, 13.5, 4.6, 12, "rust", 8)                        # octagonal silo
    cyl(0, 0, 20.6, 4.8, 2.2, "rust", 8, 0.8)                  # roof cone
    cyl(0, 0, 22.0, 0.5, 1.2, "dark", 8)
    box(0, -4.7, 13.5, 1.6, 0.3, 1.6, "glow")                   # lit hatch
    box(0, -4.6, 9.0, 1.2, 0.3, 5, "dark")                      # ladder


def dock_crane():
    box(0, 0, 0.3, 24, 8, 0.6, "concrete")                      # dock slab
    for sgn in (-1, 1):
        box(sgn * 8.5, 0, 6.5, 5.5, 4.5, 13, "concrete")        # wall-like legs
        box(sgn * 8.5, -2.3, 6.5, 3.5, 0.2, 9, "orange")
    box(0, 0, 15.0, 23, 4.5, 4.0, "concrete")                   # thick beam
    box(0, -2.3, 15.0, 21, 0.2, 2.6, "orange")
    box(2, 0, 12.8, 3, 3, 1.6, "dark")                          # trolley
    cyl(2, 0, 7.5, 0.08, 9, "dark", 8)                          # cable
    box(2, 0, 2.6, 1.6, 1.4, 1.2, "dark")                       # hook block
    box(-6, 3, 2.0, 4, 2.4, 2.4, "rust")                        # containers
    box(-1, -3, 2.0, 4, 2.4, 2.4, "dark")


def rig(dead=False):
    body, trim = ("rust", "dark") if dead else ("concrete", "orange")
    for i in range(4):
        t = math.pi / 4 + 2 * math.pi * i / 4
        x, y = 9 * math.cos(t), 9 * math.sin(t)
        box(x, y, 9, 4.2, 4.2, 18, body, (0, 0, t))             # thick legs
        box(x, y, 0.8, 6, 6, 1.6, body)                         # feet
    box(0, 0, 21, 28, 26, 8, body)                              # deck (tall)
    box(0, 0, 25.3, 26, 24, 0.6, trim)
    box(-4, -3, 29.5, 16, 12, 8, body)                          # quarters block
    box(-4, -9.1, 29.5, 14, 0.2, 2.4, "glow" if not dead else "dark")
    box(8, 6, 30, 5, 5, 9, body)                                 # derrick block
    cyl(8, 6, 36.5, 0.7, 4, "dark", 8)
    box(13, -8, 27, 10, 1, 1, "dark", (0, math.radians(-25), 0))   # flare boom
    if not dead:
        sphere(17.5, -8, 29.2, 1.2, "glow")                     # the flare
    cyl(-10, 9, 25.6, 3.5, 0.5, trim, 12)                       # helipad


def drilling_rig(): rig(False)
def dead_rig(): rig(True)


def cargo_dropship():
    box(0, 0, 0.3, 18, 18, 0.6, "concrete")                     # pad
    box(0, 0, 0.7, 14, 14, 0.3, "dark")
    box(0, 0, 6, 16, 9, 9, "concrete")                          # hull (tall box)
    box(0, 0, 10.9, 12, 7, 1.6, "dark")                         # spine
    box(-8.1, 0, 5.5, 0.4, 7, 6, "orange")                      # open rear ramp face
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(sx * 5, sy * 6.0, 5.5, 1.5, 4.4, "dark", 16, rot=(0, math.radians(90), 0))   # engine pods
            cyl(sx * 7.3, sy * 6.0, 5.5, 1.1, 0.3, "glow", 16, rot=(0, math.radians(90), 0))
        box(0, sx * 5.4, 6.0, 8, 2.4, 0.8, "pale")              # stub wings
    box(6.5, 0, 8.0, 3, 5, 3.0, "dark")                         # cockpit


def pylon():
    box(0, 0, 10, 4.4, 2.6, 20, "concrete")                      # slab post
    box(0, -1.35, 12, 3.2, 0.2, 14, "dark")                      # recessed channel
    box(0, 0, 21.2, 5.2, 3.2, 2.4, "pale")                       # head
    for sgn in (-1, 1):
        box(sgn * 2.9, 0, 18.5, 1.4, 1.0, 1.4, "concrete")       # short arms
        cyl(sgn * 2.9, 0, 17.3, 0.25, 1.4, "dark", 8)            # insulators
    box(0, -1.4, 18.6, 2.4, 0.1, 1.2, "glow")                    # orange light
    box(0, 0, 0.5, 6, 4, 1, "concrete")                          # footing


def radio_mast():
    box(0, 0, 1.5, 6, 5, 3, "concrete")                          # hut
    doors(0, -2.5, 0, 1.4, 2.4)
    box(0, 0, 14, 4.2, 3.4, 22, "concrete")                      # blocky housing
    box(0, 0, 27, 5.5, 4.5, 4, "pale")                           # head box
    box(3.0, 0, 25, 1.2, 3.0, 2.0, "dark")                       # side pod
    cyl(0, -2.4, 26.5, 1.9, 0.6, "dark", 20, rot=(math.radians(90), 0, 0))   # dish
    sphere(0, -2.5, 26.5, 0.5, "glow")                           # dish eye
    sphere(0, 0, 29.6, 0.5, "glow")                              # beacon
    box(0, -1.75, 14, 1.0, 0.1, 10, "orange")


BUILDERS = {"cooling_tower": cooling_tower, "processing_hall": processing_hall, "storage_tank": storage_tank,
            "ore_tank": ore_tank, "dock_crane": dock_crane, "drilling_rig": drilling_rig, "dead_rig": dead_rig,
            "cargo_dropship": cargo_dropship, "pylon": pylon, "radio_mast": radio_mast}
names = o.get("names", ",".join(BUILDERS)).split(",")
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    BUILDERS[name]()
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
    path = os.path.join(out, name + "_script.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True)
    print("BUILT", name, len(bpy.context.scene.objects), "parts ->", path)
