"""Flat-colour clean-up of a projected paint job, then bake it to a texture.

Run:  blender -b <painted.blend> --python flatten_bake.py -- <out_prefix> [k=6] [size=1024] [rounds=6]
      [low=<lowpoly.obj|glb>] [merge=0.08]
<painted.blend> is project_views.py output (a mesh with the "Col" vertex colour).

1. Cluster the vertex colours (k-means in sRGB) into k flat paint colours; clusters closer than
   "merge" are merged. Each vertex takes its cluster's colour.
2. Clean the labels with a neighbour majority vote ("rounds" passes). Thin features like the ink
   outlines and cel-shade streaks of the reference drawing lose the vote and disappear; real regions
   (gloves, visor, trims) are wide enough to survive.
3. Bake: without low=, the painted mesh gets Smart UVs and the flat colours are baked into
   <out>_albedo.png. With low=, the low-poly mesh gets the UVs and the colours are baked from the painted
   high-poly onto it (selected-to-active, the usual high-to-low bake), so the game mesh carries the texture.
Writes <out>.blend, <out>.glb (textured) and <out>.png (front, 3/4, side, back preview).
"""
import math, os, sys
import bpy, bmesh
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(args[0]))[0]
o = dict(a.split("=", 1) for a in args[1:])
K, SIZE, ROUNDS = int(o.get("k", 6)), int(o.get("size", 1024)), int(o.get("rounds", 6))
MERGE = float(o.get("merge", 0.08))
low_path = o.get("low")

hi = [ob for ob in bpy.context.scene.objects if ob.type == "MESH" and ob.data.color_attributes.get("Col")][0]
me = hi.data
attr = me.color_attributes["Col"]
lin = np.array([tuple(attr.data[i].color)[:3] for i in range(len(me.vertices))])
srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, 1), 1 / 2.4) - 0.055)

# ---- k-means (k-means++ init, deterministic) ----
rng = np.random.default_rng(0)
cent = [srgb[rng.integers(len(srgb))]]
for _ in range(K - 1):
    d = np.min([((srgb - c) ** 2).sum(1) for c in cent], 0)
    cent.append(srgb[rng.choice(len(srgb), p=d / d.sum())])
cent = np.array(cent)
for _ in range(30):
    lab = np.argmin(((srgb[:, None] - cent[None]) ** 2).sum(2), 1)
    cent = np.array([srgb[lab == k].mean(0) if (lab == k).any() else cent[k] for k in range(len(cent))])
# merge near-duplicate clusters, and shade variants of one paint (same hue, or both grey)
import colorsys
def same_paint(a, b):
    ha, sa, va = colorsys.rgb_to_hsv(*a.clip(0, 1))
    hb, sb, vb = colorsys.rgb_to_hsv(*b.clip(0, 1))
    if np.linalg.norm(a - b) <= MERGE:
        return True
    if min(va, vb) < 0.12:                      # near-black stays its own paint
        return False
    if sa > 0.25 and sb > 0.25:                 # chromatic: same hue family
        dh = abs(ha - hb); dh = min(dh, 1 - dh)
        return dh < float(o.get("hue", 0.07))
    return sa <= 0.25 and sb <= 0.25 and abs(va - vb) < 0.35   # greys
pop = np.bincount(lab, minlength=len(cent))
keep = []
for k in np.argsort(-pop):
    if not any(same_paint(cent[k], cent[j]) for j in keep):
        keep.append(k)
cent = cent[keep]
lab = np.argmin(((srgb[:, None] - cent[None]) ** 2).sum(2), 1)

# ---- neighbour majority vote ----
nbr = [[] for _ in me.vertices]
for e in me.edges:
    a, b = e.vertices
    nbr[a].append(b)
    nbr[b].append(a)
for r in range(ROUNDS):
    new = lab.copy()
    for i, nb in enumerate(nbr):
        if nb:
            new[i] = np.bincount(lab[nb + [i]], minlength=len(cent)).argmax()
    changed = int((new != lab).sum())
    lab = new
    if changed == 0:
        break
counts = np.bincount(lab, minlength=len(cent))
for k, c in enumerate(cent):
    print(f"PAINT {k}: #{''.join(f'{int(round(x * 255)):02x}' for x in c.clip(0, 1))} {counts[k]} vertices")

flat = me.color_attributes.new("Flat", "FLOAT_COLOR", "POINT")
flat_lin = np.where(cent <= 0.04045, cent / 12.92, ((cent + 0.055) / 1.055) ** 2.4)
for i, k in enumerate(lab):
    flat.data[i].color = (*flat_lin[k], 1.0)

# high-poly shows the flat colours as emission (what the bake reads)
mh = bpy.data.materials.new("FlatPaint")
mh.use_nodes = True
nt = mh.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
vc = nt.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Flat"
em = nt.nodes.new("ShaderNodeEmission")
mo = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(vc.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], mo.inputs["Surface"])
me.materials.clear()
me.materials.append(mh)

# ---- target mesh for the bake ----
if low_path:
    before = set(bpy.data.objects)
    if low_path.lower().endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=low_path)
    else:
        bpy.ops.import_scene.gltf(filepath=low_path)
    target = [ob for ob in bpy.data.objects if ob not in before and ob.type == "MESH"][0]
    target.data.transform(target.matrix_world)
    target.matrix_world.identity()
    target.data.materials.clear()
else:
    target = hi
bpy.ops.object.select_all(action="DESELECT")
target.select_set(True)
bpy.context.view_layer.objects.active = target
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
bpy.ops.object.mode_set(mode="OBJECT")

img = bpy.data.images.new(os.path.basename(out) + "_albedo", SIZE, SIZE)
img.filepath_raw = out + "_albedo.png"
img.file_format = "PNG"
mt = bpy.data.materials.new("Baked")
mt.use_nodes = True
tn = mt.node_tree.nodes.new("ShaderNodeTexImage")
tn.image = img
mt.node_tree.nodes.active = tn
if target is hi:
    # bake on the same mesh: keep the emission material for the bake, add the image node to it
    tn2 = nt.nodes.new("ShaderNodeTexImage")
    tn2.image = img
    nt.nodes.active = tn2
else:
    target.data.materials.append(mt)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 4
sc.render.bake.margin = 8
if target is not hi:
    hi.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    size = max(target.dimensions)
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = size * 0.02
    sc.render.bake.max_ray_distance = size * 0.05
bpy.ops.object.bake(type="EMIT")
img.save()
print("BAKED", img.filepath_raw)

# final material on the target: the baked texture as base colour
for m in list(target.data.materials):
    target.data.materials.pop()
fm = bpy.data.materials.new("Albedo")
fm.use_nodes = True
ft = fm.node_tree.nodes.new("ShaderNodeTexImage")
ft.image = img
fm.node_tree.links.new(ft.outputs["Color"], fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.45
target.data.materials.append(fm)
if target is not hi:
    hi.hide_render = True
    hi.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.object.select_all(action="DESELECT")
target.select_set(True)
bpy.ops.export_scene.gltf(filepath=out + ".glb", use_selection=True)

# preview with the texture
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.display.shading.show_cavity = True
P = np.array([tuple(v.co) for v in target.data.vertices])
lo, hi_ = P.min(0), P.max(0)
c, h = (lo + hi_) / 2, float(hi_[2] - lo[2])
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = h * 1.06
sc.render.resolution_x, sc.render.resolution_y = 480, 1000
shots = []
for ang in (0, 35, 270, 180):
    r = math.radians(ang)
    cam.location = (c[0] + h * 3 * math.sin(r), c[1] - h * 3 * math.cos(r), c[2])
    cam.rotation_euler = (math.radians(90), 0, r)
    f = out + f"_{ang}.png"
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    shots.append(f)
ims = [np.array(bpy.data.images.load(f).pixels[:]).reshape(1000, 480, 4) for f in shots]
sheet = bpy.data.images.new("sheet", 480 * len(ims), 1000)
sheet.pixels = np.concatenate(ims, 1).ravel()
sheet.filepath_raw = out + ".png"
sheet.file_format = "PNG"
sheet.save()
for f in shots:
    os.remove(f)
print("FLATTEN_BAKE", out + ".glb", len(target.data.polygons), "faces")
