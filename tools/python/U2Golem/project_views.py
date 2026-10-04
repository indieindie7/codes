"""Paint a mesh from the reference views it was made from (multi-view projection into vertex colours).

Run:  blender -b --python project_views.py -- <mesh.glb|obj> <out.blend> front=<img> [side=<img>] [back=<img>]
      [subdiv=1] [sidecam=-X]
Images are cut-outs with alpha (img2shape_mv.py saves *_input_<view>.png); "side" is the view seen from
camera sidecam (-X for Hunyuan 2mv's "left" input, as confirm_views.py reports).

Each view is an orthographic camera (front -Y, back +Y, side +-X). A view's silhouette bounding box is
matched to the mesh's projected bounding box, the same normalisation confirm_views.py scores with.
A vertex takes a weighted mix of the views that see it: weight = max(0, normal . to_camera)^2, zero
if a ray toward that camera hits the mesh first (occluded). Vertices no view sees take the average
of their coloured neighbours (flood fill). Writes <out>.blend, <out>.glb and <out>.png (front, 3/4, side, back).
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
mesh_path, out = args[0], os.path.splitext(os.path.abspath(args[1]))[0]
opts = dict(a.split("=", 1) for a in args[2:])
subdiv = int(opts.pop("subdiv", "1"))
sidecam = opts.pop("sidecam", "-X")

bpy.ops.wm.read_factory_settings(use_empty=True)
if mesh_path.lower().endswith(".obj"):
    bpy.ops.wm.obj_import(filepath=mesh_path)
else:
    bpy.ops.import_scene.gltf(filepath=mesh_path)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
ob.data.transform(ob.matrix_world)
ob.matrix_world.identity()
ob.data.materials.clear()
if subdiv:
    m = ob.modifiers.new("sub", "SUBSURF")
    m.subdivision_type = "SIMPLE"
    m.levels = m.render_levels = subdiv
    bpy.ops.object.modifier_apply(modifier=m.name)
me = ob.data
me.calc_normals_split() if hasattr(me, "calc_normals_split") else None
P = np.array([tuple(v.co) for v in me.vertices])
N = np.array([tuple(v.normal) for v in me.vertices])
bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())

# camera direction (from object toward camera) and the image's horizontal axis for each view
side_dir = (-1, 0, 0) if sidecam == "-X" else (1, 0, 0)
CAMS = {
    "front": (np.array((0, -1, 0)), np.array((1, 0, 0))),
    "back": (np.array((0, 1, 0)), np.array((-1, 0, 0))),
    "side": (np.array(side_dir), np.cross(-np.array(side_dir), (0, 0, 1))),
}


def load(path):
    img = bpy.data.images.load(os.path.abspath(path), check_existing=False)
    a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[::-1]   # row 0 = top
    bpy.data.images.remove(img)
    rgb, alpha = a[..., :3], a[..., 3]
    if alpha.min() > 0.99:     # no alpha: key out the border colour
        bg = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), 0)
        alpha = (np.abs(rgb - bg).max(2) > 0.12).astype(float)
    return rgb, alpha > 0.5


acc = np.zeros((len(P), 3))
wsum = np.zeros(len(P))
for view, path in opts.items():
    if view not in CAMS:
        continue
    d, right = CAMS[view]
    rgb, mask = load(path)
    ys, xs = np.where(mask)
    ix0, ix1, iy0, iy1 = xs.min(), xs.max(), ys.min(), ys.max()
    u = P @ right
    w = P[:, 2]
    u0, u1, w0, w1 = u.min(), u.max(), w.min(), w.max()
    px = (ix0 + (u - u0) / (u1 - u0) * (ix1 - ix0)).round().astype(int).clip(0, rgb.shape[1] - 1)
    py = (iy0 + (w1 - w) / (w1 - w0) * (iy1 - iy0)).round().astype(int).clip(0, rgb.shape[0] - 1)
    facing = (N @ d).clip(0, 1) ** 2
    seen = np.zeros(len(P), bool)
    dv = Vector(tuple(float(x) for x in d))
    span = float((P.max(0) - P.min(0)).max()) * 3
    for i in np.where(facing > 0.02)[0]:
        hit = bvh.ray_cast(Vector(P[i]) + dv * 1e-3 * span + Vector(N[i]) * 1e-4 * span, dv, span)
        seen[i] = hit[0] is None
    # only sample inside the reference silhouette (edge pixels of the cut-out are unreliable)
    inside = mask[py, px]
    wgt = facing * seen * inside
    acc += rgb[py, px] * wgt[:, None]
    wsum += wgt
    print(f"VIEW {view}: {int((wgt > 0).sum())} of {len(P)} vertices painted")

col = np.where(wsum[:, None] > 1e-6, acc / np.maximum(wsum, 1e-6)[:, None], np.nan)
# flood-fill vertices no view saw from their painted neighbours
nbr = [[] for _ in P]
for e in me.edges:
    a, b = e.vertices
    nbr[a].append(b)
    nbr[b].append(a)
todo = np.where(np.isnan(col[:, 0]))[0]
print("UNSEEN", len(todo))
for _ in range(200):
    if not len(todo):
        break
    new = col.copy()
    for i in todo:
        cs = [col[j] for j in nbr[i] if not np.isnan(col[j, 0])]
        if cs:
            new[i] = np.mean(cs, 0)
    col = new
    todo = np.where(np.isnan(col[:, 0]))[0]
col = np.nan_to_num(col, nan=0.5)

attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
lin = np.where(col <= 0.04045, col / 12.92, ((col + 0.055) / 1.055) ** 2.4)   # sRGB -> linear
for i, c in enumerate(lin):
    attr.data[i].color = (*c, 1.0)
mat = bpy.data.materials.new("Projected")
mat.use_nodes = True
nt = mat.node_tree
vc = nt.nodes.new("ShaderNodeVertexColor")
vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
me.materials.append(mat)
for f in me.polygons:
    f.use_smooth = True
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb")

# preview: front, 3/4, side, back
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "VERTEX"
sc.display.shading.show_cavity = True
lo, hi = P.min(0), P.max(0)
c, h = (lo + hi) / 2, float(hi[2] - lo[2])
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
print("PROJECTED", out + ".glb")
