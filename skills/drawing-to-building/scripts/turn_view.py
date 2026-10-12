"""Blender (headless) turntable: one row of N views around each glb, white clay, for comparing shapes.
blender -b --factory-startup -P turn_view.py -- <out.png> <a.glb> [b.glb ...] [n=4] [size=256] [color=texture]"""
import math, os, sys
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
kv = dict(x.split("=", 1) for x in a if "=" in x)
out, glbs = a[0], [x for x in a[1:] if "=" not in x]
n, size = int(kv.get("n", 4)), int(kv.get("size", 256))
tiles = []
for gi, glb in enumerate(glbs):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = kv.get("color", "SINGLE").upper()   # color=texture shows painted maps
    sc.display.shading.single_color = (0.85, 0.85, 0.85)
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.25, 0.25, 0.28)
    sc.render.resolution_x = sc.render.resolution_y = size
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    c, r = (lo + hi) / 2, (hi - lo).length * 1.25
    aim = bpy.data.objects.new("aim", None)
    sc.collection.objects.link(aim)
    aim.location = c
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.angle = math.radians(40)
    t = cam.constraints.new("TRACK_TO")
    t.target, t.track_axis, t.up_axis = aim, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.camera = cam
    for k in range(n):
        ang = math.radians(-90 + 360 * k / n)              # k=0: the glTF front (+Z -> Blender -Y)
        cam.location = c + Vector((r * math.cos(ang), r * math.sin(ang), r * 0.25))
        p = os.path.join(os.path.dirname(out), f"_t{gi}_{k}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append(p)
# stitch: one row per glb
img0 = bpy.data.images.load(tiles[0])
W, H = img0.size
big = bpy.data.images.new("sheet", W * n, H * len(glbs))
px = [0.0] * (W * n * H * len(glbs) * 4)
for i, p in enumerate(tiles):
    im = bpy.data.images.load(p)
    src = list(im.pixels)
    gi, k = divmod(i, n)
    row0 = (len(glbs) - 1 - gi) * H                        # Blender images start bottom-left
    for y in range(H):
        d = ((row0 + y) * W * n + k * W) * 4
        px[d:d + W * 4] = src[y * W * 4:(y + 1) * W * 4]
    os.remove(p)
big.pixels = px
big.filepath_raw, big.file_format = out, "PNG"
big.save()
