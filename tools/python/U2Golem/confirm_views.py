"""Confirm a multi-view 3D result against the views it was made from.

Run:  blender -b --python confirm_views.py -- <mesh.glb|obj> <out.png> front=<img> [side=<img>] [back=<img>]
The input images should be cut-outs with alpha (img2shape_mv.py saves them as *_input_<view>.png).

Renders the mesh's silhouette from the front (-Y), back (+Y) and both sides (+X, -X), compares each
with the matching input silhouette (both cropped to their bounding box and resampled to 128x256),
and prints intersection-over-union per view:
    CONFIRM front 0.91 OK
    CONFIRM side 0.88 OK (matches camera +X)
    CONFIRM back 0.90 OK
A view below 0.75 is flagged CHECK. For the side view, both side cameras are scored, so a mirrored side
input shows up as a better score on the opposite camera. out.png is a sheet: top row inputs, middle row
renders, bottom row overlap (white = both, red = only input, cyan = only render).
"""
import math, os, sys
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
mesh_path, out = args[0], args[1]
views = dict(a.split("=", 1) for a in args[2:])
W, H = 128, 256

bpy.ops.wm.read_factory_settings(use_empty=True)
if mesh_path.lower().endswith(".obj"):
    bpy.ops.wm.obj_import(filepath=mesh_path)
else:
    bpy.ops.import_scene.gltf(filepath=mesh_path)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
P = np.array([tuple(o.matrix_world @ v.co) for o in objs for v in o.data.vertices])
lo, hi = P.min(0), P.max(0)
c = (lo + hi) / 2
size = float((hi - lo).max())

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (1, 1, 1)
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 512
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = size * 1.1
cam.data.clip_end = size * 20
tmp = os.path.splitext(out)[0] + "_tmp.png"


def render_from(direction):
    d = Vector(direction).normalized()
    cam.location = Vector(c) + d * size * 5
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp, check_existing=False)
    a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[::-1]
    bpy.data.images.remove(img)
    return a[..., 3] > 0.5


def load_mask(path):
    img = bpy.data.images.load(os.path.abspath(path), check_existing=False)
    a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[::-1]
    bpy.data.images.remove(img)
    if a[..., 3].min() < 0.99:
        return a[..., 3] > 0.5
    rgb = a[..., :3]
    bg = np.median(np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]), 0)
    return np.abs(rgb - bg).max(2) > 0.12


def norm(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return np.zeros((H, W), bool)
    m = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # fit into W x H keeping aspect, centred
    s = min(W / m.shape[1], H / m.shape[0])
    w, h = max(int(m.shape[1] * s), 1), max(int(m.shape[0] * s), 1)
    yi = (np.arange(h) / s).astype(int).clip(0, m.shape[0] - 1)
    xi = (np.arange(w) / s).astype(int).clip(0, m.shape[1] - 1)
    small = m[yi][:, xi]
    canvas = np.zeros((H, W), bool)
    y0, x0 = (H - h) // 2, (W - w) // 2
    canvas[y0:y0 + h, x0:x0 + w] = small
    return canvas


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


cams = {"front": (0, -1, 0), "back": (0, 1, 0), "+X": (1, 0, 0), "-X": (-1, 0, 0)}
renders = {k: norm(render_from(v)) for k, v in cams.items()}
cols = []
for view in ("front", "side", "back"):
    if view not in views:
        continue
    inp = norm(load_mask(views[view]))
    if view == "side":
        scores = {k: iou(inp, renders[k]) for k in ("+X", "-X")}
        best = max(scores, key=scores.get)
        score, ren = scores[best], renders[best]
        note = f"(matches camera {best}; other side {scores['-X' if best == '+X' else '+X']:.2f})"
    else:
        ren = renders[view]
        score = iou(inp, ren)
        note = ""
    print(f"CONFIRM {view} {score:.2f} {'OK' if score >= 0.75 else 'CHECK'} {note}".rstrip())
    overlap = np.zeros((H, W, 3))
    overlap[inp & ren] = 1
    overlap[inp & ~ren] = (1, 0.2, 0.2)
    overlap[~inp & ren] = (0.2, 1, 1)
    cols.append(np.concatenate([np.repeat(inp[..., None], 3, 2) * 1.0, np.repeat(ren[..., None], 3, 2) * 0.8, overlap], 0))
os.remove(tmp)
sheet = np.concatenate([np.pad(cl, ((4, 4), (4, 4), (0, 0)), constant_values=0.15) for cl in cols], 1)
img = bpy.data.images.new("confirm", sheet.shape[1], sheet.shape[0])
img.pixels = np.concatenate([sheet[::-1], np.ones(sheet.shape[:2] + (1,))[::-1]], 2).ravel()
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("CONFIRM_SHEET", out)
