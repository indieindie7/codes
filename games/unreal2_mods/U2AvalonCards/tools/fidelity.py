"""Fidelity score: how well a model matches its reference picture, as numbers (after blender-kiln's idea).

    blender -b --python fidelity.py -- <model.glb> <reference.png> <out_dir> [azimuths=0,45,90,135,180,225,270,315]
        [elevations=0,10,20] [size=512]

The reference is one view of the object on a plain background (our ref-sheet cuts). The model is
rendered as a flat silhouette, orthographic, from every listed camera direction, scaled to the
reference's silhouette height and centred on it; the best direction is kept. Reported:
  iou        silhouette overlap, 0..1 (1 = identical outline)
  width_err  mean |model width - reference width| per height band, as a fraction of the height (5 bands)
  colour     mean colour of the reference's pixels vs the model's (Workbench render, flat light), per band
Writes overlay.png (red = reference only, cyan = model only, white = both) and a side-by-side, and
prints one line "FIDELITY {json}".
"""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
model, ref, out = a[0], a[1], os.path.abspath(a[2])
o = dict(x.split("=", 1) for x in a[3:])
AZ = [float(v) for v in o.get("azimuths", "0,45,90,135,180,225,270,315").split(",")]
EL = [float(v) for v in o.get("elevations", "0,10,20").split(",")]
SIZE = int(o.get("size", 512))
os.makedirs(out, exist_ok=True)


def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def ref_mask(px):
    """object = pixels that differ from the background colour (median of the border)"""
    border = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    bg = np.median(border[:, :3], 0)
    d = np.abs(px[..., :3] - bg).sum(2)
    m = d > 0.16
    if px.shape[2] == 4:
        m &= px[..., 3] > 0.5
    return m


def crop_fit(mask, rgb, H):
    """crop to the mask's box and scale so the box is H high; returns (mask, rgb) with width kept"""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return np.zeros((H, 1), bool), np.zeros((H, 1, 3), np.float32)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    m, c = mask[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
    s = H / m.shape[0]
    W = max(1, int(round(m.shape[1] * s)))
    yy = (np.arange(H) / s).astype(int).clip(0, m.shape[0] - 1)
    xx = (np.arange(W) / s).astype(int).clip(0, m.shape[1] - 1)
    return m[yy][:, xx], c[yy][:, xx]


def pad_to(m, W, fill=0):
    if m.shape[1] >= W:
        d = (m.shape[1] - W) // 2
        return m[:, d:d + W]
    l = (W - m.shape[1]) // 2
    shape = (m.shape[0], W) + m.shape[2:]
    outm = np.full(shape, fill, m.dtype)
    outm[:, l:l + m.shape[1]] = m
    return outm


def band_widths(m, bands=5):
    H = m.shape[0]
    return [float(m[i * H // bands:(i + 1) * H // bands].any(0).sum()) / H for i in range(bands)]


def band_colour(rgb, m, bands=5):
    H = m.shape[0]
    outc = []
    for i in range(bands):
        sl = slice(i * H // bands, (i + 1) * H // bands)
        sel = rgb[sl][m[sl]]
        outc.append([round(float(v), 3) for v in sel.mean(0)] if len(sel) else [0, 0, 0])
    return outc


# --- the model, rendered as silhouette + flat colour from each direction ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=model)
meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
P = np.concatenate([[tuple(mm.matrix_world @ v.co) for v in mm.data.vertices] for mm in meshes])
lo, hi = P.min(0), P.max(0)
c = Vector((lo + hi) / 2)
R = float(np.linalg.norm(hi - lo)) / 2
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "TEXTURE"
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2 * R * 1.02

rpx = load_rgba(ref)
rmask = ref_mask(rpx)
H = SIZE
rm, rc = crop_fit(rmask, rpx[..., :3], H)
best = None
for el in EL:
    for az in AZ:
        d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(-az) - math.pi / 2),
                    math.cos(math.radians(el)) * math.sin(math.radians(-az) - math.pi / 2), math.sin(math.radians(el))))
        cam.location = c + d * (4 * R)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out, "_view.png")
        bpy.ops.render.render(write_still=True)
        mpx = load_rgba(sc.render.filepath)
        mmask = mpx[..., 3] > 0.5
        mm, mc = crop_fit(mmask, mpx[..., :3], H)
        W = max(rm.shape[1], mm.shape[1])
        A, B = pad_to(rm, W), pad_to(mm, W)
        iou = float((A & B).sum()) / max(1, float((A | B).sum()))
        if best is None or iou > best["iou"]:
            best = {"iou": round(iou, 3), "azimuth": az, "elevation": el, "A": A, "B": B,
                    "rc": pad_to(rc, W), "mc": pad_to(mc, W), "rm": pad_to(rm, W), "mm": pad_to(mm, W)}
A, B = best["A"], best["B"]
wr, wm = band_widths(best["rm"]), band_widths(best["mm"])
width_err = round(float(np.mean(np.abs(np.array(wr) - np.array(wm)))), 3)
result = {"model": os.path.basename(model), "reference": os.path.basename(ref), "iou": best["iou"],
          "best_azimuth": best["azimuth"], "best_elevation": best["elevation"], "width_err": width_err,
          "ref_widths": [round(v, 3) for v in wr], "model_widths": [round(v, 3) for v in wm],
          "ref_colour_bands": band_colour(best["rc"], best["rm"]), "model_colour_bands": band_colour(best["mc"], best["mm"])}
# overlay: red = reference only, cyan = model only, white = both
ov = np.zeros(A.shape + (4,), np.float32)
ov[..., 3] = 1
ov[A & ~B] = (1, 0.15, 0.15, 1)
ov[B & ~A] = (0.15, 0.9, 1, 1)
ov[A & B] = (1, 1, 1, 1)
side = np.concatenate([np.dstack([best["rc"], np.ones(A.shape)]), np.dstack([best["mc"], np.ones(A.shape)]), ov], 1)
for name, arr in (("overlay.png", ov), ("side_by_side.png", side)):
    img = bpy.data.images.new(name, arr.shape[1], arr.shape[0], alpha=True)
    img.pixels = arr[::-1].ravel()
    img.filepath_raw = os.path.join(out, name)
    img.file_format = "PNG"
    img.save()
json.dump(result, open(os.path.join(out, "fidelity.json"), "w"), indent=1)
print("FIDELITY " + json.dumps(result))
