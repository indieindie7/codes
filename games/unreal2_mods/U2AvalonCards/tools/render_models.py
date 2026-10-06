"""Render each painted model (.glb) to a picture and tile them into a contact sheet, on the CPU.

    blender -b --python render_models.py -- <dir with *_paint.glb> <out_dir> [size=512] [views=2]

views=1: a three-quarter view; views=2: three-quarter + the other side, side by side per model.
Workbench renderer with the model's own texture, flat studio light, grey background: a quick look, not art.
Writes <out_dir>/<name>.png per model and <out_dir>/models_sheet.jpg.
"""
import glob, math, os, sys
import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], os.path.abspath(a[1])
o = dict(x.split("=", 1) for x in a[2:])
SIZE, VIEWS = int(o.get("size", 512)), int(o.get("views", 2))
os.makedirs(out, exist_ok=True)
files = sorted(glob.glob(os.path.join(src, o.get("pattern", "*_paint.glb"))))
tiles = []
for f in files:
    name = os.path.basename(f).replace("_paint.glb", "").replace("_script.glb", "")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    P = np.concatenate([[tuple(m.matrix_world @ v.co) for v in m.data.vertices] for m in meshes])
    lo, hi = P.min(0), P.max(0)
    c = Vector((lo + hi) / 2)
    R = float(np.linalg.norm(hi - lo)) / 2
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.color = (0.35, 0.37, 0.40)
    sc.world = world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2 * R * 1.05
    row = []
    for k in range(VIEWS):
        az = math.radians(-35 - 180 * k)
        d = Vector((math.cos(math.radians(20)) * math.cos(az), math.cos(math.radians(20)) * math.sin(az), math.sin(math.radians(20))))
        cam.location = c + d * (4 * R)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out, "%s_%d.png" % (name, k))
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(sc.render.filepath)
        row.append(np.array(img.pixels[:]).reshape(SIZE, SIZE, 4))
    tiles.append((name, np.concatenate(row, 1)))
    print("RENDERED", name, len(P), "verts")
cols = 2 if VIEWS == 2 else 4
rows = (len(tiles) + cols - 1) // cols
W = SIZE * VIEWS
sheet = np.zeros((rows * SIZE, cols * W, 4), np.float32)
sheet[..., 3] = 1
for i, (name, t) in enumerate(tiles):
    r, cI = i // cols, i % cols
    sheet[(rows - 1 - r) * SIZE:(rows - r) * SIZE, cI * W:(cI + 1) * W] = t
img = bpy.data.images.new("sheet", cols * W, rows * SIZE)
img.pixels = sheet.ravel()
img.filepath_raw = os.path.join(out, "models_sheet.png")
img.file_format = "PNG"
img.save()
with open(os.path.join(out, "order.txt"), "w") as fo:
    for i, (name, _) in enumerate(tiles):
        fo.write("%d %s\n" % (i, name))
print("SHEET", len(tiles), "models ->", out)
