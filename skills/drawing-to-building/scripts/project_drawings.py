"""Blender (headless): paint a building/object from the user's drawings by projecting each view onto it, baked to a texture.
blender -b --factory-startup -P project_drawings.py -- <in.glb> <out.glb> <views.json> [res=1024] [ink=140] [minface=0.2]
views.json: [{"img": path, "objects": ["upper_B", ...] or "all", "yaw": deg, "pitch": deg, "weight": 1, "mirror": 0,
              "use": "paint" | "plan"}, ...]
  yaw/pitch say where the viewer stands: yaw 0 = in front (-Y), 90 = right (+X), 180 = back, 270 = left; pitch 90 = top.
  An angled/perspective sketch is a view too (yaw 41, pitch 10 for housePlan1), read as orthographic.
  use "plan": a top view that is only a wall plan / layout (not what the roof looks like) -> never painted.
  mirror 1: also paint the opposite face with the flipped drawing (gable ends, symmetric sides).
How: texel positions and normals are baked (Cycles EMIT, UVs from Smart UV Project); then numpy, per view: the listed
objects' projected bbox is stretched onto the drawing's ink bbox, a z-buffer keeps hidden texels unpainted, weight =
weight * (normal . view)^2 (>= minface); the best view per texel wins. Dark pixels (< ink) are kept as ink; the rest is paper, so ruled lines and
paper grain drop out. Texels no view sees stay paper. Written 2026-10-11 for housePlan1 (scenefit house\tex)."""
import sys, os, json, math
import bpy, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
src, out, vj = a[:3]
kv = dict(x.split("=", 1) for x in a[3:] if "=" in x)
RES, INK, MINF = int(kv.get("res", 1024)), int(kv.get("ink", 140)), float(kv.get("minface", 0.2))
KEEP = float(kv.get("keep", 0))   # >0: keep the UVs + painted texture already on the mesh, at this weight (new views win above it)
PAPER = np.array([0.93, 0.91, 0.86], np.float32)
views = json.load(open(vj))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.data.objects if o.type == "MESH"]
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 1
sc.render.bake.margin = 4

def bake(o, which):
    """Emit world position or normal into a float image over the object's UVs."""
    m = bpy.data.materials.new(f"bake_{which}"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    g, em, oo = nt.nodes.new("ShaderNodeNewGeometry"), nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(g.outputs["Position" if which == "pos" else "Normal"], em.inputs["Color"]); nt.links.new(em.outputs[0], oo.inputs[0])
    img = bpy.data.images.new(f"{o.name}_{which}", RES, RES, float_buffer=True, alpha=True)
    img.generated_color = (0, 0, 0, 0)
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; nt.nodes.active = t
    o.data.materials.clear(); o.data.materials.append(m)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type="EMIT", margin=4)
    return np.array(img.pixels[:], np.float32).reshape(RES, RES, 4)

data = {}
for o in objs:
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    old = None
    if KEEP:
        ims = [nd.image for m in o.data.materials if m and m.use_nodes for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image]
        if ims:
            old = ims[0]
            if tuple(old.size) != (RES, RES): old.scale(RES, RES)
            old = np.array(old.pixels[:], np.float32).reshape(RES, RES, 4)[..., :3]
    if old is None:
        while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0005); bpy.ops.object.mode_set(mode="OBJECT")
    p, n = bake(o, "pos"), bake(o, "nrm")
    data[o.name] = {"pos": p[..., :3], "nrm": n[..., :3], "ok": np.abs(n[..., :3]).sum(2) > 0.5,
                    "col": np.tile(PAPER, (RES, RES, 1)), "w": np.zeros((RES, RES), np.float32)}
    if old is not None:
        painted = np.abs(old - PAPER).sum(2) > 0.02
        data[o.name]["col"][:] = old; data[o.name]["w"][painted] = KEEP
    q = p[..., 3] > 0.5; print("baked", o.name, "alpha>0.5", int(q.sum()), "pos min", p[..., :3].min((0, 1)), "max", p[..., :3].max((0, 1)), "nonzero", int((np.abs(p[..., :3]).sum(2) > 1e-6).sum()))

def load_ink(path):
    import bpy as _b
    im = _b.data.images.load(os.path.abspath(path)); w, h = im.size
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]      # row 0 = top
    g = px.mean(2) * 255; ink = g < INK
    ys, xs = np.nonzero(ink)
    box = (np.percentile(xs, 0.5), np.percentile(xs, 99.5), np.percentile(ys, 0.5), np.percentile(ys, 99.5))
    col = np.where(ink[..., None], px, PAPER)
    return col, box

for v in views:
    if v.get("use", "paint") != "paint": print("skip (plan)", v["img"]); continue
    col, (x0, x1, y0, y1) = load_ink(v["img"]); H, W = col.shape[:2]
    names = [o.name for o in objs] if v.get("objects", "all") == "all" else v["objects"]
    for flip in ([0, 1] if v.get("mirror") else [0]):
        yaw, pit = math.radians(v.get("yaw", 0) + 180 * flip), math.radians(v.get("pitch", 0))
        c = np.array([math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), math.sin(pit)], np.float32)
        right = np.array([math.cos(yaw), math.sin(yaw), 0], np.float32); up = np.cross(right, -c)
        if flip: col_v = col[:, ::-1]                                          # seen from behind: mirror the drawing
        else: col_v = col
        allp = np.concatenate([data[k]["pos"][data[k]["ok"]] for k in names])
        u_all, w_all = allp @ right, allp @ up
        umin, umax, wmin, wmax = u_all.min(), u_all.max(), w_all.min(), w_all.max()
        bx0, bx1 = ((W - x1, W - x0) if flip else (x0, x1))
        def to_img(P):
            return (bx0 + (P @ right - umin) / (umax - umin) * (bx1 - bx0),
                    y1 - (P @ up - wmin) / (wmax - wmin) * (y1 - y0), P @ c)
        # z-buffer over every object (anything can hide anything), at drawing resolution
        zb = np.full((H, W), -1e9, np.float32)
        for k, d in data.items():
            px, py, z = to_img(d["pos"][d["ok"]]); ix, iy = np.clip(px.astype(int), 0, W - 1), np.clip(py.astype(int), 0, H - 1)
            np.maximum.at(zb, (iy, ix), z)
        span = float(np.ptp(allp @ c)) + 1e-6
        for k in names:
            d = data[k]; ok = d["ok"]; P, N = d["pos"][ok], d["nrm"][ok]
            px, py, z = to_img(P); ix, iy = np.clip(px.astype(int), 0, W - 1), np.clip(py.astype(int), 0, H - 1)
            vis = z >= zb[iy, ix] - 0.02 * span
            cos = N @ c; w = np.where((cos >= MINF) & vis, cos ** 2, 0) * v.get("weight", 1.0)
            cc, ww = d["col"][ok], d["w"][ok]
            best = w > ww                                                   # the view that sees it most squarely wins (no doubled lines)
            cc[best] = col_v[iy, ix][best]; ww[best] = w[best]
            d["col"][ok], d["w"][ok] = cc, ww
    print("painted", v["img"], "yaw", v.get("yaw", 0), "on", names)

os.makedirs(os.path.splitext(out)[0] + "_tex", exist_ok=True)
for o in objs:
    d = data[o.name]; w = d["w"][..., None]
    rgb = d["col"]
    img = bpy.data.images.new(o.name + "_paint", RES, RES)
    img.pixels[:] = np.concatenate([rgb, np.ones((RES, RES, 1), np.float32)], 2).ravel()
    img.filepath_raw = os.path.join(os.path.splitext(out)[0] + "_tex", o.name + ".png"); img.file_format = "PNG"; img.save()
    m = bpy.data.materials.new(o.name + "_drawn"); m.use_nodes = True; nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]; t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = 0.9
    o.data.materials.clear(); o.data.materials.append(m)
    print(o.name, "painted texels", int((d["w"] > 1e-4).sum()), "of", int(d["ok"].sum()))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out), export_format="GLB", use_selection=True)
print("PROJECTED", out)
