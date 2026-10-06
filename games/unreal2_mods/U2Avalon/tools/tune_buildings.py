"""Reconstruct a ref sheet by code (the blender-kiln / img2threejs idea, without an LLM in the loop): a
parametrised builder per building type, and a silhouette search over its parameters against the sheet's
cut-out view, scored like U2AvalonCards/tools/fidelity.py (IoU of the silhouettes, best azimuth).

    blender -b --python tune_buildings.py -- <out_dir> <cuts_dir> [sheets=storage_tank_1,pylon_2,...]
        [iters=3] [size=256]

For each sheet <type>_<n>_view.png it writes <out_dir>/<type>_<n>_kiln.glb (metres, front -Y, like
build_buildings.py), <type>_<n>_kiln.json (the parameters and the score) and <type>_<n>_overlay.png
(red = sheet only, cyan = model only, white = both). iters = rounds of coordinate descent (each round tries
every parameter up and down with a shrinking step).
"""
import glob, json, math, os, random, sys
import bpy
import numpy as np
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
out, cuts = os.path.abspath(a[0]), os.path.abspath(a[1])
o = dict(x.split("=", 1) for x in a[2:])
ITERS, SIZE = int(o.get("iters", 3)), int(o.get("size", 256))
ONLY = set(o["sheets"].split(",")) if "sheets" in o else None
os.makedirs(out, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palette  # noqa

MATS = {}
COLOURS = palette.COLOURS


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = palette.colour(name) + (1,)
        bsdf.inputs["Roughness"].default_value = 0.85 if name != "glow" else 0.4
        if name == "glow":
            bsdf.inputs["Emission Color"].default_value = COLOURS[name] + (1,)
            bsdf.inputs["Emission Strength"].default_value = 4
        MATS[name] = m
    return MATS[name]


def place(ob, x, y, z, m, rot=(0, 0, 0)):
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ob.data.materials.append(mat(m))
    return ob


def box(x, y, z, sx, sy, sz, m="concrete", rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    return place(ob, x, y, z, m, rot)


def cyl(x, y, z, r, h, m="concrete", n=24, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r, radius2=r2, depth=h)
    return place(bpy.context.object, x, y, z, m, rot)


def sphere(x, y, z, r, m="concrete"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=24, ring_count=12)
    return place(bpy.context.object, x, y, z, m)


# --- parametrised builders: name -> (defaults with (value, lo, hi), build(p)) ---------------------------
def P(**kw):
    return {k: list(v) for k, v in kw.items()}


def b_storage_tank(p):
    r, h = p["r"], p["h"]
    cyl(0, 0, p["base"] / 2, r + 0.5, p["base"], "dark", 32)
    cyl(0, 0, p["base"] + h / 2, r, h, "steel", 32)
    cyl(0, 0, p["base"] + 0.6, r + 0.05, 1.2, "brown", 32)
    if p["dome"] > 0.05:
        sphere(0, 0, p["base"] + h, r, "concrete")
        bpy.context.object.scale = (1, 1, p["dome"])
    for i in range(int(p["ribs"])):
        t = 2 * math.pi * i / max(1, int(p["ribs"]))
        box((r - 0.1) * math.cos(t), (r - 0.1) * math.sin(t), p["base"] + h / 2, 0.5, 0.9, h, "pale", (0, 0, t))
    box(0, -r - 0.1, p["base"] + h * 0.6, r * 0.55, 0.3, h * 0.45, "rustred")
    cyl(0, 0, p["base"] + h + r * p["dome"] + p["stack"] / 2, 0.6, max(0.1, p["stack"]), "dark", 12)
    box(r * 0.35, -r + 0.2, p["base"] + h * 0.3, 0.4, 0.5, h * 0.6, "dark")


def b_ore_tank(p):
    legs, r, h = p["legs"], p["r"], p["h"]
    for i in range(4):
        t = math.pi / 4 + 2 * math.pi * i / 4
        box(0.7 * r * math.cos(t), 0.7 * r * math.sin(t), legs / 2, 0.8, 0.8, legs, "dark", (0, 0, t))
    cyl(0, 0, legs + p["cone"] / 2, r, p["cone"], "dark", 8, 1.0)
    cyl(0, 0, legs + p["cone"] + h / 2, r, h, "rustred", 8)
    cyl(0, 0, legs + p["cone"] + h + p["roof"] / 2, r + 0.2, p["roof"], "rust", 8, 0.8)
    cyl(0, 0, legs + p["cone"] + h + p["roof"] + 0.6, 0.5, 1.2, "dark", 8)
    box(0, -r - 0.1, legs + p["cone"] + h * 0.5, 1.6, 0.3, 1.6, "glow")
    box(0, -r, legs + p["cone"] + h * 0.3, 1.2, 0.3, h * 0.5, "dark")


def b_processing_hall(p):
    W, D, H = p["W"], p["D"], p["H"]
    box(0, 0, H / 2, W, D, H, "charcoal")
    box(0, 0, 0.6, W + 0.1, D + 0.1, 1.2, "brown")
    box(-W * 0.3, -D / 2 - 0.05, H * 0.55, W * 0.25, 0.1, H * 0.7, "rustred")
    ov = p["overhang"]
    box(0, 0, H + 0.25, W + 2 * ov, D + 2 * ov, 0.5, "grey")
    n = max(1, int(p["teeth"]))
    pitch = W / n
    for i in range(n):
        x = -W / 2 + (i + 0.5) * pitch
        box(x, 0, H + 0.5 + p["tooth"] / 2, pitch * 0.97, D, p["tooth"], "pale", (0, math.radians(18), 0))
        box(x + pitch * 0.42, 0, H + 0.5 + p["tooth"] / 2, 0.3, D * 0.96, p["tooth"] * 1.3, "glow")
    for i in range(max(1, int(p["doors"]))):
        x = -W / 2 + (i + 0.5) * W / max(1, int(p["doors"]))
        box(x, -D / 2 - 0.02, 2.0, 3.3, 0.1, 4.3, "orange")
        box(x, -D / 2 - 0.06, 2.0, 3.0, 0.1, 4.0, "dark")
    if p["bay"] > 0.5:
        box(-W / 2 - 2, 0, 1.5, 4, D * 0.6, 3, "concrete")
        box(W / 2 + 2, 0, 1.5, 4, D * 0.6, 3, "concrete")
    if p["stack"] > 0.3:
        cyl(W * 0.3, D * 0.2, H + 0.5 + p["stack"] / 2, 0.8, p["stack"], "dark", 12)


def b_pylon(p):
    H, bw, tw = p["H"], p["base"], p["top"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            # four legs leaning in: a thin box from (sx*bw, sy*bw, 0) toward (sx*tw, sy*tw, H)
            x0, y0, x1, y1 = sx * bw / 2, sy * bw / 2, sx * tw / 2, sy * tw / 2
            L = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + H * H)
            ob = box((x0 + x1) / 2, (y0 + y1) / 2, H / 2, 0.35, 0.35, L, "dark")
            d = Vector((x1 - x0, y1 - y0, H)).normalized()
            ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for k in range(max(1, int(p["arms"]))):
        z = H * (0.55 + 0.4 * k / max(1, int(p["arms"])))
        w = p["arm"] * (1 - 0.15 * k)
        box(0, 0, z, w, 0.4, 0.4, "dark")
        for s in (-1, 1):
            box(s * w / 2, 0, z - 0.9, 0.25, 0.25, 1.8, "pale")
    for k in range(int(H // 3)):
        z = 1.5 + k * 3
        f = 1 - z / H
        w = tw + (bw - tw) * f
        box(0, 0, z, w, 0.2, 0.2, "dark")
        box(0, 0, z, 0.2, w, 0.2, "dark")
    box(0, 0, H / 2 + 0.2, 0.5, 0.5, H * 0.9, "orange")


def b_radio_mast(p):
    H, bw, tw = p["H"], p["base"], p["top"]
    cyl(0, 0, H / 2, bw / 2, H, "pale", 8, tw / 2)
    cyl(0, 0, 0.4, bw * 0.9, 0.8, "concrete", 16)
    for k in range(int(p["platforms"])):
        z = H * (0.3 + 0.6 * k / max(1, int(p["platforms"])))
        f = 1 - z / H
        w = tw + (bw - tw) * f
        box(0, 0, z, w + 1.6, w + 1.6, 0.25, "dark")
        box(0, 0, z + 0.5, w + 1.6, 0.08, 1.0, "dark")
    if p["dish"] > 0.5:
        cyl(bw * 0.8, 0, H * 0.75, 1.6, 0.25, "pale", 16, rot=(0, math.radians(60), 0))
    for k in range(int(p["antennas"])):
        box(0, 0, H + 0.6 + k * 1.2, 0.12, 2.4 - 0.6 * k, 0.12, "pale")
    box(0, -bw / 2 - 0.1, H * 0.2, 0.6, 0.2, H * 0.3, "orange")
    for k in range(int(H // 2.5)):
        z = 1.2 + k * 2.5
        f = 1 - z / H
        w = tw + (bw - tw) * f
        box(0, 0, z, w + 0.4, 0.12, 0.12, "dark")
        box(0, 0, z, 0.12, w + 0.4, 0.12, "dark")


BUILDERS = {
    "storage_tank": (P(r=(6, 3.5, 9), h=(8.6, 4, 14), base=(1.2, 0.3, 2.5), dome=(0.5, 0, 1), ribs=(8, 0, 12), stack=(1.6, 0, 4)), b_storage_tank),
    "ore_tank": (P(r=(4.6, 2.5, 7), h=(12, 6, 18), legs=(5, 2, 8), cone=(3, 1, 5), roof=(2.2, 0.5, 4)), b_ore_tank),
    "processing_hall": (P(W=(30, 16, 44), D=(14, 8, 20), H=(8, 5, 14), teeth=(5, 2, 8), tooth=(2, 0.5, 4), overhang=(1.5, 0, 3.5),
                          doors=(4, 1, 6), bay=(1, 0, 1), stack=(0, 0, 10)), b_processing_hall),
    "pylon": (P(H=(22, 12, 34), base=(5, 2, 9), top=(1.2, 0.3, 3), arm=(7, 3, 12), arms=(2, 1, 3)), b_pylon),
    "radio_mast": (P(H=(30, 16, 44), base=(5, 2, 9), top=(0.8, 0.2, 2), platforms=(2, 0, 4), dish=(1, 0, 1), antennas=(2, 0, 4)), b_radio_mast),
}
INT_PARAMS = {"ribs", "teeth", "doors", "arms", "platforms", "antennas"}


# --- silhouette scoring (fidelity.py's method, in-process) -----------------------------------------------
def load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def ref_mask(px):
    border = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    bg = np.median(border[:, :3], 0)
    m = np.abs(px[..., :3] - bg).sum(2) > 0.16
    if px.shape[2] == 4:
        m &= px[..., 3] > 0.5
    return m


def crop_fit(mask, H):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return np.zeros((H, 1), bool)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    m = mask[y0:y1, x0:x1]
    s = H / m.shape[0]
    W = max(1, int(round(m.shape[1] * s)))
    yy = (np.arange(H) / s).astype(int).clip(0, m.shape[0] - 1)
    xx = (np.arange(W) / s).astype(int).clip(0, m.shape[1] - 1)
    return m[yy][:, xx]


def pad_to(m, W):
    if m.shape[1] >= W:
        d = (m.shape[1] - W) // 2
        return m[:, d:d + W]
    l = (W - m.shape[1]) // 2
    outm = np.zeros((m.shape[0], W), bool)
    outm[:, l:l + m.shape[1]] = m
    return outm


def iou(A, B):
    W = max(A.shape[1], B.shape[1])
    A, B = pad_to(A, W), pad_to(B, W)
    return float((A & B).sum()) / max(1, float((A | B).sum())), A, B


def scene_reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
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
    return cam


def render_masks(cam, azimuths=(0, 45, 90), el=10.0):
    meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    P_ = np.concatenate([[tuple(mm.matrix_world @ v.co) for v in mm.data.vertices] for mm in meshes])
    lo, hi = P_.min(0), P_.max(0)
    c = Vector((lo + hi) / 2)
    R = float(np.linalg.norm(hi - lo)) / 2
    cam.data.ortho_scale = 2 * R * 1.02
    sc = bpy.context.scene
    masks = []
    for az in azimuths:
        d = Vector((math.cos(math.radians(el)) * math.cos(math.radians(-az) - math.pi / 2),
                    math.cos(math.radians(el)) * math.sin(math.radians(-az) - math.pi / 2), math.sin(math.radians(el))))
        cam.location = c + d * (4 * R)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out, "_tune_view.png")
        bpy.ops.render.render(write_still=True)
        mpx = load_rgba(sc.render.filepath)
        masks.append(crop_fit(mpx[..., 3] > 0.5, SIZE))
    return masks


def score(build, p, rm):
    cam = scene_reset()
    build(p)
    best = (0.0, None, None)
    for m in render_masks(cam):
        v, A, B = iou(rm, m)
        if v > best[0]:
            best = (v, A, B)
    return best


def tune(name, build, spec, rm):
    p = {k: v[0] for k, v in spec.items()}
    cur, A, B = score(build, p, rm)
    print(f"  start {cur:.3f}")
    for rnd in range(ITERS):
        step = 0.5 / (rnd + 1)         # as a fraction of each parameter's range
        improved = False
        for k, (v0, lo, hi) in spec.items():
            for sgn in (-1, 1):
                q = dict(p)
                d = sgn * step * (hi - lo)
                q[k] = min(hi, max(lo, p[k] + d))
                if k in INT_PARAMS:
                    q[k] = round(q[k])
                if q[k] == p[k]:
                    continue
                v, A2, B2 = score(build, q, rm)
                if v > cur + 1e-4:
                    cur, p, A, B = v, q, A2, B2
                    improved = True
                    print(f"  round {rnd} {k}={q[k]:.2f} -> {cur:.3f}")
        if not improved and rnd >= 1:
            break
    return p, cur, A, B


for path in sorted(glob.glob(os.path.join(cuts, "*_view.png"))):
    sheet = os.path.basename(path)[:-9]                    # storage_tank_1
    typ = sheet.rsplit("_", 1)[0]
    if typ not in BUILDERS or (ONLY and sheet not in ONLY):
        continue
    spec, build = BUILDERS[typ]
    rm = crop_fit(ref_mask(load_rgba(path)), SIZE)
    print("TUNE", sheet)
    p, best, A, B = tune(sheet, build, spec, rm)
    # the final model, exported
    scene_reset()
    build(p)
    for ob in bpy.context.scene.objects:
        ob.select_set(ob.type == "MESH")
    glb = os.path.join(out, sheet + "_kiln.glb")
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format="GLB", export_apply=True)
    json.dump({"sheet": sheet, "type": typ, "iou": round(best, 3), "params": p}, open(os.path.join(out, sheet + "_kiln.json"), "w"), indent=1)
    ov = np.zeros(A.shape + (4,), np.float32)
    ov[..., 3] = 1
    ov[A & ~B] = (1, 0.15, 0.15, 1)
    ov[B & ~A] = (0.15, 0.9, 1, 1)
    ov[A & B] = (1, 1, 1, 1)
    img = bpy.data.images.new("ov", ov.shape[1], ov.shape[0], alpha=True)
    img.pixels = ov[::-1].ravel()
    img.filepath_raw = os.path.join(out, sheet + "_overlay.png")
    img.file_format = "PNG"
    img.save()
    print(f"KILN {sheet} iou {best:.3f} params {json.dumps(p)}")
