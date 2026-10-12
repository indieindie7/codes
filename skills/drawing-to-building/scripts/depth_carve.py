"""Shape from the user's drawings without a Hunyuan base: carve a voxel block with every view's silhouette, then carve
the free space each view's Depth Anything map says lies in front of the surface. CPU only.
venv/Scripts/python depth_carve.py part  <out.glb> <views.json> [n=96] [tol=0.06] [name=part] [size=x,y,z]
venv/Scripts/python depth_carve.py scene <in.glb> <out.glb> <views.json> [n=160] [tol=0.06]
views.json: [{"img": drawing, "mask": optional filled-colour image for the silhouette (white = outside),
  "yaw": 0, "pitch": 0, "sil": 1, "depth": 1, "mirror": 0}]  - yaw/pitch as project_drawings (yaw 0 = from -Y, 90 = from +X,
  pitch 90 = from above), orthographic, the shape's projected bbox stretched onto the mask's bbox.
part:  unit block, each axis stretched to its views (assemble_measured sets the real sizes).
scene: voxelizes every mesh of an assembled GLB, carves them together (one z-buffer), writes them back as separate meshes.
Depth: relative DA V2 Small (near = large); fitted per view to the carved shape's own front depth (z = a*d + b over the
silhouette), voxels nearer than the fitted surface by > tol*span are removed. Written 2026-10-11 (housePlan1)."""
import sys, json, math, numpy as np, cv2, trimesh
from PIL import Image
from skimage import measure
from scipy.ndimage import gaussian_filter

a = sys.argv[1:]; mode = a[0]
kv = dict(x.split("=", 1) for x in a if "=" in x); pos = [x for x in a[1:] if "=" not in x]
TOL = float(kv.get("tol", 0.06))
_da = None

def depth_map(im):
    global _da
    if _da is None:
        from transformers import pipeline
        _da = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device="cpu")
    d = _da(im)["predicted_depth"].squeeze().numpy().astype(np.float32)
    return cv2.resize(d, im.size)

def silhouette(v):
    if v.get("mask"):
        m = np.asarray(Image.open(v["mask"]).convert("RGB")).min(2) < 235
    else:                                       # ink outline -> row span AND column span (open outlines still fill)
        g = np.asarray(Image.open(v["img"]).convert("L")) < 140
        g = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8)) > 0
        r = np.zeros_like(g); c = np.zeros_like(g)
        for y in np.nonzero(g.any(1))[0]:
            xs = np.nonzero(g[y])[0]; r[y, xs[0]:xs[-1] + 1] = 1
        for x in np.nonzero(g.any(0))[0]:
            ys = np.nonzero(g[:, x])[0]; c[ys[0]:ys[-1] + 1, x] = 1
        m = r & c
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.nonzero(m)
    return m, (xs.min(), xs.max(), ys.min(), ys.max())

def axes(yaw, pit):
    yaw, pit = math.radians(yaw), math.radians(pit)
    c = np.array([math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), math.sin(pit)])
    right = np.array([math.cos(yaw), math.sin(yaw), 0.0]); up = np.cross(right, -c)
    return c, right, up

def carve(occ, P, views, log):
    """occ: list of bool arrays (one per mesh) over grid points P (N,3). Changes occ in place."""
    for v in views:
        m, (x0, x1, y0, y1) = silhouette(v)
        H, W = m.shape
        dmap = depth_map(Image.open(v.get("mask") or v["img"]).convert("RGB")) if v.get("depth", 1) else None
        if dmap is not None and v.get("blur", 0):                # pen lines read as grooves: smooth them out
            dmap = cv2.GaussianBlur(dmap, (0, 0), float(v["blur"]))
        tol = float(v.get("tol", TOL)); minblob = int(v.get("minblob", 0))
        for flip in ([0, 1] if v.get("mirror") else [0]):
            c, right, up = axes(v.get("yaw", 0) + 180 * flip, v.get("pitch", 0))
            mm = m[:, ::-1] if flip else m
            dd = (dmap[:, ::-1] if flip else dmap) if dmap is not None else None
            bx0, bx1 = (W - 1 - x1, W - 1 - x0) if flip else (x0, x1)
            on = np.any(occ, 0)
            u, w, z = P @ right, P @ up, P @ c
            umin, umax, wmin, wmax = u[on].min(), u[on].max(), w[on].min(), w[on].max()
            px = np.clip((bx0 + (u - umin) / (umax - umin) * (bx1 - bx0)).round().astype(int), 0, W - 1)
            py = np.clip((y1 - (w - wmin) / (wmax - wmin) * (y1 - y0)).round().astype(int), 0, H - 1)
            inside = (u >= umin) & (u <= umax) & (w >= wmin) & (w <= wmax)
            before = [o.sum() for o in occ]
            if v.get("sil", 1):
                keep = inside & mm[py, px]
                for o in occ: o &= keep
            if dd is not None:
                on = np.any(occ, 0)
                zb = np.full((H, W), -np.inf); np.maximum.at(zb, (py[on], px[on]), z[on])   # carved shape's front depth
                yy, xx = np.nonzero(np.isfinite(zb) & mm)
                if len(yy) > 50:
                    A = np.stack([dd[yy, xx], np.ones(len(yy))], 1)
                    (k, b), *_ = np.linalg.lstsq(A, zb[yy, xx], rcond=None)
                    span = float(np.ptp(z[on]))
                    if k > 0:
                        surf = k * dd[py, px] + b
                        cut = mm[py, px] & (z > surf + tol * span)
                        if minblob:                              # only big, consistent cut regions in image space
                            img = np.zeros((H, W), np.uint8); img[py[cut], px[cut]] = 1
                            img = cv2.morphologyEx(img, cv2.MORPH_OPEN, np.ones((minblob, minblob), np.uint8))
                            cut &= img[py, px] > 0
                        for o in occ: o &= ~cut
                    log.append(f"  depth fit k={k:.4g} b={b:.3f} span={span:.3f}")
            log.append(f"{v['img'].split('/')[-1]} yaw {v.get('yaw',0)+180*flip} pitch {v.get('pitch',0)}: "
                       + ", ".join(f"{b0}->{o.sum()}" for b0, o in zip(before, occ)))

def mesh_of(o, shape, lo, step):
    g = o.reshape(shape).astype(np.float32)
    g = np.pad(g, 1)
    g = gaussian_filter(g, 0.8)
    vs, fs, _, _ = measure.marching_cubes(g, 0.5)
    vs = (vs - 1) * step + lo
    t = trimesh.Trimesh(vs[:, [0, 2, 1]] * [1, 1, -1], fs)
    if t.volume < 0: t.invert()
    return t   # Z-up -> glTF Y-up (x, z, -y)

def grid(lo, hi, n):
    step = float((hi - lo).max()) / n
    ax = [np.arange(lo[i] + step / 2, hi[i], step) for i in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing="ij")
    return np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1), X.shape, lo + step / 2, step

log = []
if mode == "part":
    out, vj = pos[0], pos[1]; views = json.load(open(vj)); n = int(kv.get("n", 96))
    P, shape, lo, step = grid(np.array([-1.0, -1, -1]), np.array([1.0, 1, 1]), n)
    occ = [np.ones(len(P), bool)]
    carve(occ, P, views, log)
    m = mesh_of(occ[0], shape, lo, step)
    if "size" in kv:                                   # size=x,y,z (Z up): final bbox, e.g. from the drawings' ink sizes
        sx, sy, sz = map(float, kv["size"].split(","))
        m.apply_scale([sx / 2, sz / 2, sy / 2])        # unit block is 2 wide; glTF axes (x, z, -y)
    sc = trimesh.Scene(); sc.add_geometry(m, node_name=kv.get("name", "part"))
    sc.export(out)
else:
    pin, out, vj = pos[0], pos[1], pos[2]; views = json.load(open(vj)); n = int(kv.get("n", 160))
    sc = trimesh.load(pin, force="scene")
    meshes = {}
    for nm in sc.graph.nodes_geometry:
        T, gname = sc.graph[nm]
        meshes[nm] = sc.geometry[gname].copy().apply_transform(T)
    # glTF Y-up -> our Z-up (x, -z, y)
    zup = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    for g in meshes.values(): g.apply_transform(zup)
    allv = np.concatenate([g.vertices for g in meshes.values()])
    pad = np.ptp(allv, 0).max() * 0.02
    P, shape, lo, step = grid(allv.min(0) - pad, allv.max(0) + pad, n)
    occ = []
    for name, g in meshes.items():
        vox = g.voxelized(step).fill()
        o = np.zeros(shape, bool)
        idx = np.round((vox.points - lo) / step).astype(int)
        ok = np.all((idx >= 0) & (idx < shape), 1); o[tuple(idx[ok].T)] = True
        occ.append(o.ravel()); log.append(f"{name}: {o.sum()} voxels")
    carve(occ, P, views, log)
    o2 = trimesh.Scene()
    for (name, _), o in zip(meshes.items(), occ):
        if o.any(): o2.add_geometry(mesh_of(o, shape, lo, step), node_name=name, geom_name=name)
    o2.export(out)
print("\n".join(log)); print("WROTE", out)
