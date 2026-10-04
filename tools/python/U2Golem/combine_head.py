"""Put a separately generated head (e.g. a Hunyuan head + beret bust) on a layered StdGEN character.

Run:  blender -b --python combine_head.py -- <out_prefix> clothes=<glb> body=<glb> head=<glb>
      [faces=150000] [head_eye_z=0.19] [head_cut_z=-0.75] [neck_z=auto] [head_scale=1.05]

- clothes/body: StdGEN refined layers (vertex colour "Color"), decimated to `faces` each.
- head: a bust normalised to +-1 (Hunyuan output), painted (project_views.py, colour "Col").
  It is scaled so its width at eye level matches the body's head width at eye level, moved so the
  eye heights and the head centres line up, and cut below head_cut_z (keeps the collar/hood, drops the
  shoulders). head_eye_z is the bust's eye height in its own units (from the reference crop).
- the body's own head (StdGEN's mannequin head) is deleted above the neck so it can't poke through.
Writes <out>.blend, <out>.glb and <out>.png (front, 3/4, side, back), vertex colours.
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(a[0]))[0]
o = dict(x.split("=", 1) for x in a[1:])
FACES = int(o.get("faces", 150000))
EYE_H = float(o.get("head_eye_z", 0.19))
CUT_H = float(o.get("head_cut_z", -0.75))
HEAD_SCALE = float(o.get("head_scale", 1.05))   # >1: the bust's skin sits outside the mannequin; heroic heads go bigger

bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    ms = [x for x in bpy.data.objects if x not in before and x.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for m in ms:
        m.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.data.transform(ob.matrix_world)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    for x in [x for x in bpy.data.objects if x not in before and x != ob]:
        bpy.data.objects.remove(x, do_unlink=True)
    ob.name = name
    return ob


def decimate(ob, faces):
    if len(ob.data.polygons) > faces:
        m = ob.modifiers.new("dec", "DECIMATE")
        m.ratio = faces / len(ob.data.polygons)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=m.name)


def verts(ob):
    return np.array([tuple(v.co) for v in ob.data.vertices])


clothes = load(o["clothes"], "Clothes")
body = load(o["body"], "Body")
head = load(o["head"], "Head")
decimate(clothes, FACES)
decimate(body, FACES)

# body head: top, and width at eye level
B = verts(body)
top = B[:, 2].max()
neck_z = float(o["neck_z"]) if "neck_z" in o else None
# head region: points above the narrowest slice between the shoulders and the top
zs = np.linspace(top - 0.35 * (top - B[:, 2].min()), top - 0.02, 60)
widths = []
for z in zs:
    band = B[np.abs(B[:, 2] - z) < 0.006]
    band = band[np.abs(band[:, 0]) < 0.25]
    widths.append(band[:, 0].max() - band[:, 0].min() if len(band) > 10 else 9)
if neck_z is None:
    lower = [i for i, z in enumerate(zs) if z < top - 0.12 * (top - B[:, 2].min()) * 0.9]
    neck_z = zs[min(lower, key=lambda i: widths[i])] if lower else top - 0.25
head_h = top - neck_z
eye_z = neck_z + 0.55 * head_h
band = B[(np.abs(B[:, 2] - eye_z) < 0.008) & (np.abs(B[:, 0]) < 0.25)]
body_w = band[:, 0].max() - band[:, 0].min()
body_c = (band.min(0) + band.max(0)) / 2

H = verts(head)
hband = H[np.abs(H[:, 2] - EYE_H) < 0.04]
head_w = hband[:, 0].max() - hband[:, 0].min()
head_c = (hband.min(0) + hband.max(0)) / 2
s = body_w / head_w * HEAD_SCALE
print(f"HEAD body top {top:.3f} neck {neck_z:.3f} eye {eye_z:.3f} width {body_w:.3f}; bust width {head_w:.3f} -> scale {s:.4f}")

# cut the bust below the collar, then scale and place it
bm = bmesh.new()
bm.from_mesh(head.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < CUT_H], context="VERTS")
bm.to_mesh(head.data)
bm.free()
off = Vector((body_c[0], body_c[1], eye_z)) - Vector((head_c[0], head_c[1], EYE_H)) * s
head.data.transform(Matrix.Translation(off) @ Matrix.Scale(s, 4))

# remove the body's mannequin head above the neck (the new head replaces it)
bm = bmesh.new()
bm.from_mesh(body.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > neck_z + 0.01], context="VERTS")
bm.to_mesh(body.data)
bm.free()

# one colour attribute name for all parts, one material that shows it
ca = head.data.color_attributes.get("Col")
if ca:
    ca.name = "Color"
mat = bpy.data.materials.new("VertexColour")
mat.use_nodes = True
vc = mat.node_tree.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Color"
mat.node_tree.links.new(vc.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
for ob in (clothes, body, head):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for f in ob.data.polygons:
        f.use_smooth = True
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb")

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "VERTEX"
sc.display.shading.show_cavity = True
P = np.concatenate([verts(x) for x in (clothes, body, head)])
lo, hi = P.min(0), P.max(0)
c, h = (lo + hi) / 2, float(hi[2] - lo[2])
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = h * 1.05
sc.render.resolution_x, sc.render.resolution_y = 560, 1000
shots = []
for ang in (0, 35, 270, 180):
    r = math.radians(ang)
    cam.location = (c[0] + h * 3 * math.sin(r), c[1] - h * 3 * math.cos(r), c[2])
    cam.rotation_euler = (math.radians(90), 0, r)
    f = out + f"_{ang}.png"
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    shots.append(f)
ims = [np.array(bpy.data.images.load(f).pixels[:]).reshape(1000, 560, 4) for f in shots]
sheet = bpy.data.images.new("sheet", 560 * len(ims), 1000)
sheet.pixels = np.concatenate(ims, 1).ravel()
sheet.filepath_raw = out + ".png"
sheet.file_format = "PNG"
sheet.save()
for f in shots:
    os.remove(f)
print("COMBINED", out + ".glb", sum(len(x.data.polygons) for x in (clothes, body, head)), "faces")
