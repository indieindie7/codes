"""Turnaround reference views of a textured model: front, 45, side, 135, back (and the other side).

Run:  blender -b --python turnaround.py -- <model.glb> <out_prefix> [angles=0,45,90,135,180,225,270,315]
      [size=1024] [lit=0]
Orthographic views with the model's own texture, unlit by default (flat colours, the way a reference
sheet is drawn), on a light grey background. Angle 0 is the front (-Y); angles go round toward the
model's left. Writes <out>_<angle>.png for each angle and <out>_sheet.png (all of them in a row).
"""
import math, os, sys
import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], os.path.splitext(os.path.abspath(a[1]))[0]
o = dict(x.split("=", 1) for x in a[2:])
ANGLES = [int(x) for x in o.get("angles", "0,45,90,135,180,225,270,315").split(",")]
SIZE, LIT = int(o.get("size", 1024)), int(o.get("lit", 0))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
P = np.concatenate([[tuple(m.matrix_world @ v.co) for v in m.data.vertices] for m in meshes])
c = (P.min(0) + P.max(0)) / 2
h = float(P[:, 2].max() - P[:, 2].min())
if not LIT:
    # unlit: every material shows its base-colour texture as emission
    for m in meshes:
        for mat in m.data.materials:
            if not mat or not mat.use_nodes:
                continue
            nt = mat.node_tree
            tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image), None)
            outn = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
            if tex and outn:
                em = nt.nodes.new("ShaderNodeEmission")
                nt.links.new(tex.outputs["Color"], em.inputs["Color"])
                nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
sc = bpy.context.scene
# Cycles on the CPU: no GPU use at all, so it can run while a game has the graphics card
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16 if LIT else 6
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 1 if LIT else 0
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.78, 0.78, 1)
sc.world = world
if LIT:
    for ang in (35, -60):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 2.5 if ang > 0 else 1.0
        sun.rotation_euler = (math.radians(55), 0, math.radians(ang))
        sc.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = h * 1.12
sc.render.resolution_x = sc.render.resolution_y = SIZE
tiles = []
for ang in ANGLES:
    r = math.radians(ang)
    cam.location = (c[0] + h * 3 * math.sin(r), c[1] - h * 3 * math.cos(r), c[2])
    cam.rotation_euler = (math.radians(90), 0, r)
    sc.render.filepath = f"{out}_{ang:03d}.png"
    bpy.ops.render.render(write_still=True)
    tiles.append(np.array(bpy.data.images.load(sc.render.filepath).pixels[:]).reshape(SIZE, SIZE, 4))
# sheet: crop each tile to the middle 62% of its width (a standing figure never needs more)
w0, w1 = int(SIZE * 0.19), int(SIZE * 0.81)
row = np.concatenate([t[:, w0:w1] for t in tiles], 1)
sheet = bpy.data.images.new("sheet", row.shape[1], SIZE)
sheet.pixels = row.ravel()
sheet.filepath_raw = out + "_sheet.png"
sheet.file_format = "PNG"
sheet.save()
print(f"TURNAROUND {out}_sheet.png: {len(ANGLES)} views {ANGLES}")
