"""Put a separately generated head (a bust: head + hat + collar) on a generated body. Both from Hunyuan.

Run:  blender -b --python attach_head.py -- <out_prefix> body=<body.glb> head=<bust.glb>
      [body_high=<glb> head_high=<glb>] [high_faces=250000] [scale=1.0] [collar=0.78 depth=1.5]
body / head are the textured meshes (paint_mesh.py). With body_high / head_high the same fit is applied
to the untextured high-polys too, so the low-poly and its normal/AO bake can come from full detail.

How the fit is found (no hand-placed landmarks): each mesh is scanned from the top down, measuring its
width slice by slice. The widest slice near the top is the hat; under it the width narrows to the jaw
and widens again at the collar. The bust is scaled so its hat is as wide as the body's hat (and its
"top of hat to jaw" height agrees, when that could be measured), and moved so hat tops and centres coincide.
Then the body loses its own head (everything in the head's column above the jaw, and everything above
the hat brim), and the bust loses its collar and shoulders (below the jaw only a neck stub is kept, which
sinks into the body's collar). With collar=<radius in hat widths> the bust keeps its own collar or scarf
down to depth=<hat widths below the hat top> instead, which covers the body's collar and hides the join
(use scale=1.05 so it sits just outside).
Writes <out>_paint.glb (textured, two materials), <out>_high.glb (if the highs were given) and <out>.png.
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Matrix

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(a[0]))[0]
o = dict(x.split("=", 1) for x in a[1:])
HIGH_FACES = int(o.get("high_faces", 250000))
USER_SCALE = float(o.get("scale", 1.0))

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
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    for x in [x for x in bpy.data.objects if x not in before and x != ob]:
        bpy.data.objects.remove(x, do_unlink=True)
    ob.name = name
    return ob


def verts(ob):
    return np.array([tuple(v.co) for v in ob.data.vertices])


def landmarks(P, scan_frac):
    """hat top, hat (widest) slice, jaw (narrowest slice under the hat), measured from the top down"""
    top, H = P[:, 2].max(), P[:, 2].max() - P[:, 2].min()
    cx = float(np.median(P[P[:, 2] > top - 0.05 * H, 0]))
    n = 120
    zs = top - (np.arange(n) + 0.5) / n * scan_frac * H
    half = scan_frac * H / n * 0.75
    w, cxs, cys = np.zeros(n), np.zeros(n), np.zeros(n)
    for i, z in enumerate(zs):
        s = P[(np.abs(P[:, 2] - z) < half) & (np.abs(P[:, 0] - cx) < 0.25 * H)]
        if len(s) > 8:
            w[i] = s[:, 0].max() - s[:, 0].min()
            cxs[i], cys[i] = (s[:, 0].max() + s[:, 0].min()) / 2, (s[:, 1].max() + s[:, 1].min()) / 2
    for _ in range(2):
        w[1:-1] = (w[:-2] + w[1:-1] + w[2:]) / 3
    ih = int(np.argmax(w[: int(n * 0.45)]))                       # the hat
    stop = next((i for i in range(ih + 3, n) if w[i] > w[ih] * 1.03), n - 1)    # collar / shoulders wider than the hat
    ij = ih + int(np.argmin(w[ih:stop + 1]))                      # the jaw
    return dict(top=top, hat_z=zs[ih], hat_w=w[ih], jaw_z=zs[ij], jaw_w=w[ij], cx=cxs[ih], cy=cys[ih],
                head_h=top - zs[ij])


def cut(ob, keep):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    P = np.array([tuple(v.co) for v in bm.verts])
    k = keep(P)
    bmesh.ops.delete(bm, geom=[v for v, kk in zip(bm.verts, k) if not kk], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()


body, head = load(o["body"], "Body"), load(o["head"], "Head")
B, Hd = landmarks(verts(body), 0.22), landmarks(verts(head), 1.0)
s_h, s_w = B["head_h"] / Hd["head_h"], B["hat_w"] / Hd["hat_w"]
# the hat is the reliable measure: on a bust the collar often hides the jaw, so "top to jaw" can come out
# as the whole bust. The height ratio is only used when it agrees with the hat's.
s = ((s_h + s_w) / 2 if 0.8 < s_h / s_w < 1.25 else s_w) * USER_SCALE
print(f"ATTACH body: hat width {B['hat_w']:.3f}, head height {B['head_h']:.3f}; bust: {Hd['hat_w']:.3f}, {Hd['head_h']:.3f}; "
      f"scale by height {s_h:.3f}, by hat width {s_w:.3f} -> {s:.3f}")
T = Matrix.Translation((B["cx"], B["cy"], B["top"])) @ Matrix.Scale(s, 4) @ Matrix.Translation(
    (-Hd["cx"], -Hd["cy"], -Hd["top"]))
jaw_b, hh = B["jaw_z"], B["head_h"]
col = max(B["jaw_w"], Hd["jaw_w"] * s) * 0.62                     # radius of the head's column at the jaw


COLLAR = float(o.get("collar", 0))          # keep the bust's own collar/scarf: its radius, in hat widths (0 = off)
DEPTH = float(o.get("depth", 1.5))          # ... and how far below the hat top it reaches, in hat widths


def keep_body(P):
    r = np.hypot(P[:, 0] - B["cx"], P[:, 1] - B["cy"])
    # with the bust's collar kept, the body's whole head-and-neck column goes (the new collar covers the hole)
    in_col = (P[:, 2] > jaw_b - (0.35 if COLLAR else 0.05) * hh) & (r < (0.6 * B["hat_w"] if COLLAR else col))
    above_brim = (P[:, 2] > jaw_b + 0.42 * hh) & (r < B["hat_w"])
    return ~(in_col | above_brim)




def keep_head(P):                                               # P already in body space
    r = np.hypot(P[:, 0] - B["cx"], P[:, 1] - B["cy"])
    if COLLAR:
        # the bust keeps its collar (it drapes over the body's chest and hides the join); only its shoulders go
        return (P[:, 2] > jaw_b - 0.02 * hh) | ((P[:, 2] > B["top"] - DEPTH * B["hat_w"]) & (r < COLLAR * B["hat_w"]))
    return (P[:, 2] > jaw_b - 0.02 * hh) | ((P[:, 2] > jaw_b - 0.30 * hh) & (r < col * 0.8))


def fit(bo, ho):
    ho.data.transform(T)
    cut(bo, keep_body)
    cut(ho, keep_head)


fit(body, head)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
head.select_set(True)
bpy.ops.export_scene.gltf(filepath=out + "_paint.glb", use_selection=True)

if "body_high" in o and "head_high" in o:
    bh, hh_ = load(o["body_high"], "BodyHigh"), load(o["head_high"], "HeadHigh")
    for ob in (bh, hh_):
        if len(ob.data.polygons) > HIGH_FACES:
            m = ob.modifiers.new("dec", "DECIMATE")
            m.ratio = HIGH_FACES / len(ob.data.polygons)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=m.name)
    fit(bh, hh_)
    bpy.ops.object.select_all(action="DESELECT")
    bh.select_set(True)
    hh_.select_set(True)
    bpy.context.view_layer.objects.active = bh
    bpy.ops.object.join()
    bh.data.materials.clear()
    bpy.ops.object.select_all(action="DESELECT")
    bh.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out + "_high.glb", use_selection=True)
    bh.hide_render = True
    print(f"ATTACH high: {len(bh.data.polygons)} faces")

# preview: head close-ups, unlit, CPU
for ob in (body, head):
    for mat in ob.data.materials:
        if mat and mat.use_nodes:
            nt = mat.node_tree
            tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image), None)
            on = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
            if tex and on:
                em = nt.nodes.new("ShaderNodeEmission")
                nt.links.new(tex.outputs["Color"], em.inputs["Color"])
                nt.links.new(em.outputs["Emission"], on.inputs["Surface"])
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 6
sc.cycles.max_bounces = 0
sc.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.78, 0.78, 1)
sc.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = B["hat_w"] * 3.4
sc.render.resolution_x = sc.render.resolution_y = 640
cz = B["top"] - 0.8 * B["hat_w"]
tiles = []
for ang in (0, 45, 90, 180):
    r = math.radians(ang)
    cam.location = (B["cx"] + 6 * math.sin(r), B["cy"] - 6 * math.cos(r), cz)
    cam.rotation_euler = (math.radians(90), 0, r)
    sc.render.filepath = f"{out}_{ang}.png"
    bpy.ops.render.render(write_still=True)
    tiles.append(np.array(bpy.data.images.load(sc.render.filepath).pixels[:]).reshape(640, 640, 4))
    os.remove(sc.render.filepath)
sheet = bpy.data.images.new("sheet", 640 * len(tiles), 640)
sheet.pixels = np.concatenate(tiles, 1).ravel()
sheet.filepath_raw = out + ".png"
sheet.file_format = "PNG"
sheet.save()
print("ATTACHED", out + "_paint.glb")
