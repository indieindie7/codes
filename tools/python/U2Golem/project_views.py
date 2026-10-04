"""Paint a mesh from the reference views it was made from (multi-view projection into vertex colours).

Run:  blender -b --python project_views.py -- <mesh.glb|obj> <out.blend> front=<img> [side=<img>] [back=<img>]
      [subdiv=1] [sidecam=-X] [mirror=1] [edge=0.006] [minface=0.3] [register=0]
Images are cut-outs with alpha (img2shape_mv.py saves *_input_<view>.png); "side" is the view seen from
camera sidecam (-X for Hunyuan 2mv's "left" input, as confirm_views.py reports).

Each view is an orthographic camera (front -Y, back +Y, side +-X). A view's silhouette bounding box is
matched to the mesh's projected bounding box, the same normalisation confirm_views.py scores with.
mirror=1 (default) also uses the side drawing, flipped, for the opposite side (characters are symmetric).
register=1 (off by default: it can leave thin horizontal streaks): the mesh never matches the drawing exactly (a hand hangs a little further out, a thigh is a
little thinner), so each pixel row is registered on its own: the mesh's silhouette runs in that row
(arm, body, arm) are mapped onto the drawing's runs when both have the same number of them.
Outline ink is kept off the surface: dark pixels within `edge` (fraction of the figure's height) of the
silhouette are not sampled unless they belong to a dark area thicker than a line (a glove), and a view
only paints surfaces that face it by at least `minface` (cosine). The side views only assist where
front or back already painted.
A vertex takes a weighted mix of the views that see it: weight = max(0, normal . to_camera)^2, zero
if a ray toward that camera hits the mesh first (occluded). Vertices no view sees take the nearest
painted vertices' colour, with height counted 4x (they stay on the same band of the limb). Writes <out>.blend, <out>.glb and <out>.png (front, 3/4, side, back).
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
MIRROR = int(opts.pop("mirror", "1"))
EDGE = float(opts.pop("edge", "0.006"))
MINFACE = float(opts.pop("minface", "0.3"))
REGISTER = int(opts.pop("register", "0"))

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


def erode(mask, n):
    m = mask.copy()
    for _ in range(n):
        k = m.copy()
        k[1:] &= m[:-1]
        k[:-1] &= m[1:]
        k[:, 1:] &= m[:, :-1]
        k[:, :-1] &= m[:, 1:]
        m = k
    return m


def row_runs(row):
    d_ = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
    st, en = np.where(d_ == 1)[0], np.where(d_ == -1)[0] - 1
    res = []
    for a_, b_ in zip(st, en):
        if res and a_ - res[-1][1] <= 3:
            res[-1][1] = b_
        else:
            res.append([a_, b_])
    return [r for r in res if r[1] - r[0] >= 2]


def register_rows(px, py, mask):
    """per pixel row: map the mesh's silhouette runs onto the drawing's runs (same count only)"""
    h, w = mask.shape
    g = np.zeros((h, w), bool)
    g[py, px] = True
    g = ~erode(~g, 2)                    # close the gaps between vertices
    out = px.astype(float)
    order = np.argsort(py, kind="stable")
    bounds = np.searchsorted(py[order], np.arange(h + 1))
    matched = 0
    for y in range(h):
        idx = order[bounds[y]:bounds[y + 1]]
        if not len(idx):
            continue
        rg, rd = row_runs(g[y]), row_runs(mask[y])
        if not rg or len(rg) != len(rd):
            continue
        matched += 1
        x = px[idx]
        for (ga, gb), (da, db) in zip(rg, rd):
            m = (x >= ga - 2) & (x <= gb + 2)
            out[idx[m]] = da + (x[m] - ga) / max(1, gb - ga) * (db - da)
    return out.round().astype(int).clip(0, w - 1), matched


jobs = sorted(((v, pth, False) for v, pth in opts.items() if v in CAMS), key=lambda j: j[0] == "side")
if MIRROR and "side" in opts:
    sd = np.array(side_dir)
    CAMS["side_mirrored"] = (-sd, np.cross(sd, (0, 0, 1)))
    jobs.append(("side_mirrored", opts["side"], True))
acc = np.zeros((len(P), 3))
wsum = np.zeros(len(P))
spread_done = False
for view, path, flipped in jobs:
    if view.startswith("side") and not spread_done:
        # before the side views: front/back colours creep a short way (2% of the height) round each part,
        # along the surface. Thin parts (hands, antennae) are then fully painted by their own colours and the
        # side drawing, where they overlap the body, does not repaint them (see the thickness test below).
        spread_done = True
        nb = [[] for _ in P]
        elen = []
        for e_ in me.edges:
            a_, b_ = e_.vertices
            nb[a_].append(b_)
            nb[b_].append(a_)
        ev = np.array([tuple(e_.vertices) for e_ in me.edges])
        steps = int(np.ceil(0.02 * (P[:, 2].max() - P[:, 2].min()) / np.linalg.norm(P[ev[:, 0]] - P[ev[:, 1]], axis=1).mean()))
        have = wsum > 1e-6
        cur = np.where(have[:, None], acc / np.maximum(wsum, 1e-6)[:, None], 0.0)
        for _ in range(min(steps, 40)):
            front = [i for i in np.where(~have)[0] if any(have[j] for j in nb[i])]
            if not front:
                break
            vals = [np.mean([cur[j] for j in nb[i] if have[j]], 0) for i in front]
            for i, v_ in zip(front, vals):
                cur[i], have[i] = v_, True
        grown = have & (wsum <= 1e-6)
        acc[grown], wsum[grown] = cur[grown] * 0.05, 0.05      # weak: a side view that may paint here wins
        print(f"SPREAD {int(grown.sum())} vertices in {steps} steps")
    d, right = CAMS[view]
    rgb, mask = load(path)
    if flipped:
        rgb, mask = rgb[:, ::-1], mask[:, ::-1]
    ys, xs = np.where(mask)
    ix0, ix1, iy0, iy1 = xs.min(), xs.max(), ys.min(), ys.max()
    u = P @ right
    w = P[:, 2]
    u0, u1, w0, w1 = u.min(), u.max(), w.min(), w.max()
    px = (ix0 + (u - u0) / (u1 - u0) * (ix1 - ix0)).round().astype(int).clip(0, rgb.shape[1] - 1)
    py = (iy0 + (w1 - w) / (w1 - w0) * (iy1 - iy0)).round().astype(int).clip(0, rgb.shape[0] - 1)
    if REGISTER and not view.startswith("side"):
        px, nreg = register_rows(px, py, mask)
        print(f"REGISTER {view}: {nreg} rows matched run for run")
    cosv = (N @ d).clip(0, 1)
    facing = np.where(cosv >= MINFACE, cosv ** 2, 0.0)
    seen = np.zeros(len(P), bool)
    dv = Vector(tuple(float(x) for x in d))
    span = float((P.max(0) - P.min(0)).max()) * 3
    for i in np.where(facing > 0.02)[0]:
        hit = bvh.ray_cast(Vector(P[i]) + dv * 1e-3 * span + Vector(N[i]) * 1e-4 * span, dv, span)
        seen[i] = hit[0] is None
    # only sample inside the reference silhouette (edge pixels of the cut-out are unreliable)
    e = max(1, int(round(EDGE * (iy1 - iy0))))
    band = mask & ~erode(mask, e)
    dark = mask & (rgb.max(2) < 0.3)
    # a dark area thicker than an ink line is a dark part (a glove, a visor), not outline
    thick = ~erode(~erode(dark, e // 2 + 1), e // 2 + 2)
    inside = (mask & ~(band & dark & ~thick))[py, px]
    wgt = facing * seen * inside
    if view.startswith("side"):
        # In the side drawing a hand overlaps the thigh and never sits exactly where the mesh's hand is, so
        # thin parts would be painted with whatever is behind them. The side views only paint parts that
        # are thick along the view axis (legs, torso, head, arms); thin ones keep the front/back spread.
        thick_ok = np.zeros(len(P), bool)
        for i in np.where(wgt > 0)[0]:
            hit = bvh.ray_cast(Vector(P[i]) - dv * 2e-3 * span, -dv, span)
            thick_ok[i] = hit[0] is None or hit[3] > 0.035 * (w1 - w0)
        wgt = wgt * thick_ok
        # the side drawing registers worst (limbs overlap in it): where front or back already painted, it only assists
        wgt = np.where(wsum > 0.15, wgt * 0.2, wgt)
    acc += rgb[py, px] * wgt[:, None]
    wsum += wgt
    print(f"VIEW {view}: {int((wgt > 0).sum())} of {len(P)} vertices painted")

col = np.where(wsum[:, None] > 1e-6, acc / np.maximum(wsum, 1e-6)[:, None], np.nan)
# vertices no view painted: the nearest painted ones, with height counted 4x (stay on the same band of the limb)
from mathutils.kdtree import KDTree
todo = np.where(np.isnan(col[:, 0]))[0]
done = np.where(~np.isnan(col[:, 0]))[0]
print("UNSEEN", len(todo))
if len(todo) and len(done):
    kd = KDTree(len(done))
    for j, i in enumerate(done):
        kd.insert((P[i, 0], P[i, 1], P[i, 2] * 4), j)
    kd.balance()
    src = col.copy()
    for i in todo:
        near = kd.find_n((P[i, 0], P[i, 1], P[i, 2] * 4), 8)
        wts = np.array([1 / (dist + 1e-6) for _, _, dist in near])
        col[i] = (np.array([src[done[j]] for _, j, _ in near]) * wts[:, None]).sum(0) / wts.sum()
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
