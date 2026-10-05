"""Bake an imposter card set from a model: N views round it, transparent background, as 32-bit TGAs.

    blender -b --python bake_cards.py -- <model.glb> <out_dir> <Name> [frames=8] [size=256] [elev=12]
        [sun=135] [sunelev=35] [ambient=0.45] [water=0]

water=0.15 cuts off the lowest 15% of the model (an oil rig's feet under the sea).

Writes <out_dir>/<Name>0.tga .. <Name>{frames-1}.tga and <Name>_sheet.png. Frame k has the camera at
k*360/frames degrees round the model, CLOCKWISE seen from above, starting in front of the model (-Y in
Blender, the glTF front), at elev degrees above the horizon (the tower looks down on the sea).
That is the order CardSprite (U2AvalonCards) picks frames in: Unreal's yaw turns clockwise too.
The sun is fixed to the model (sun = its azimuth in the same clockwise degrees, sunelev its height), so
the light stays put in the world as the views change. Orthographic, each frame framed on the model's
whole bounding sphere, so the object keeps its size from frame to frame and sits on the same base line
(the model's lowest point at 6% of the height from the bottom).
"""
import math, os, sys
import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
src, out, name = a[0], os.path.abspath(a[1]), a[2]
o = dict(x.split("=", 1) for x in a[3:])
N, SIZE = int(o.get("frames", 8)), int(o.get("size", 256))
ELEV, SUN, SUNELEV, AMB = (float(o.get(k, d)) for k, d in (("elev", 12), ("sun", 135), ("sunelev", 35), ("ambient", 0.45)))
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
P = np.concatenate([[tuple(m.matrix_world @ v.co) for v in m.data.vertices] for m in meshes])
lo, hi = P.min(0), P.max(0)
WATER = float(o.get("water", 0))
if WATER > 0:
    # cut away what is under the sea (the lowest WATER of the model's height), so the card's base line
    # is the waterline
    import bmesh
    zcut = lo[2] + WATER * (hi[2] - lo[2])
    for m in meshes:
        bm = bmesh.new()
        bm.from_mesh(m.data)
        inv = m.matrix_world.inverted()
        co = inv @ Vector((0, 0, zcut))
        no = (inv.to_3x3().transposed().inverted() @ Vector((0, 0, 1))).normalized()
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                               clear_inner=True)
        bm.to_mesh(m.data)
        bm.free()
    P = np.concatenate([[tuple(m.matrix_world @ v.co) for v in m.data.vertices] for m in meshes])
    lo, hi = P.min(0), P.max(0)
c = (lo + hi) / 2
R = float(np.linalg.norm(hi - lo)) / 2

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 48
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 0.86, 0.72, 1)   # warm evening sky
world.node_tree.nodes["Background"].inputs[1].default_value = AMB
sc.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.data.color = (1.0, 0.82, 0.6)
sc.collection.objects.link(sun)
az = math.radians(-SUN) - math.pi / 2          # clockwise degrees from the front (-Y)
sd = Vector((math.cos(math.radians(SUNELEV)) * math.cos(az), math.cos(math.radians(SUNELEV)) * math.sin(az),
             math.sin(math.radians(SUNELEV))))
sun.rotation_euler = (-sd).to_track_quat("-Z", "Y").to_euler()

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2 * R * 1.02
tiles = []
for k in range(N):
    az = math.radians(-k * 360.0 / N) - math.pi / 2
    d = Vector((math.cos(math.radians(ELEV)) * math.cos(az), math.cos(math.radians(ELEV)) * math.sin(az),
                math.sin(math.radians(ELEV))))
    # aim so the model's lowest point lands 6% above the bottom edge
    target = Vector(c) + Vector((0, 0, (R * 1.02 - 0.06 * 2 * R * 1.02) - (c[2] - lo[2])))
    cam.location = target + d * (4 * R)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.image_settings.file_format = "TARGA_RAW"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = os.path.join(out, "%s%d.tga" % (name, k))
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(sc.render.filepath)
    tiles.append(np.array(img.pixels[:]).reshape(SIZE, SIZE, 4))
    print("CARD", sc.render.filepath)
sheet = bpy.data.images.new("sheet", SIZE * N, SIZE, alpha=True)
sheet.pixels = np.concatenate(tiles, 1).ravel()
sheet.filepath_raw = os.path.join(out, name + "_sheet.png")
sheet.file_format = "PNG"
sheet.save()
print("CARDS", N, "frames ->", out)
