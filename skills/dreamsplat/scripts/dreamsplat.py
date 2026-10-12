"""10-12 Dreamsplat reference sheet + polish loop (CPU). Same strokes as splat.py (tight row), laid out as a grid:
one ROW per object, one COLUMN per view angle. The user paints over the sheet, then polish takes the colours back.
<hunyuan venv python> sdf/dreamsplat.py sheet  <objects.json> <out_prefix> [size=360] [angles=0,45,...,315]
<hunyuan venv python> sdf/dreamsplat.py polish <objects.json> <painted_sheet.png> <layout.json> <out_prefix>
objects.json: [{"name": "kA", "mesh": "sdf/A_t040.glb", "front": "sdf/paint/kA_front.png", "right": "...", "colors": optional .npy}]
sheet  -> <out_prefix>_sheet.png + <out_prefix>_layout.json (cell size, angles, row order: polish needs it)
polish -> per stroke, the column that faces it best and sees it (depth test) gives its colour, shading divided out;
          only pixels that differ from the sheet as sent count (untouched views never override); strokes nobody sees keep their old colour.
          Writes <out_prefix>_<name>.npy colours + a new sheet, so the loop can go round again (put the .npy in "colors")."""
import sys, json, os
import numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont

BG = (245, 242, 235); LAB = 140; HEAD = 40                           # label column width, header row height
L = np.array([-0.5, 0.7, 0.6]); L /= np.linalg.norm(L)
K = np.linspace(0, 2 * np.pi, 10, endpoint=False)
N_STROKES, R, JIT = 45000, 0.012, 0.25

def tex(p):
    im = Image.open(p).convert("RGBA"); a = np.asarray(im).astype(np.float32) / 255
    solid = a[..., 3] > 0.5
    if solid.all(): solid = a[..., :3].min(axis=2) < 0.93
    ys, xs = np.nonzero(solid)
    return a[..., :3], (xs.min(), ys.min(), xs.max(), ys.max())

def look(img, u, v):
    rgb, (x0, y0, x1, y1) = img
    x = np.clip(np.round(x0 + u * (x1 - x0)).astype(int), 0, rgb.shape[1] - 1)
    y = np.clip(np.round(y0 + v * (y1 - y0)).astype(int), 0, rgb.shape[0] - 1)
    return rgb[y, x]

def strokes(o):
    """identical to splat.py's tight row (same seeds), so sheets and polish passes line up stroke for stroke"""
    rng = np.random.default_rng(7)
    m = trimesh.load(o["mesh"], force="mesh"); lo, hi = m.bounds
    pts, fi = trimesh.sample.sample_surface_even(m, N_STROKES, seed=3)
    nr = m.face_normals[fi]
    FR, RT = tex(o["front"]), tex(o["right"])
    u_x = (pts[:, 0] - lo[0]) / (hi[0] - lo[0]); u_z = (pts[:, 2] - lo[2]) / (hi[2] - lo[2])
    v = (hi[1] - pts[:, 1]) / (hi[1] - lo[1])
    side = np.abs(nr[:, 0]) > np.abs(nr[:, 2])
    cs = look(RT, np.where(nr[:, 0] > 0, 1 - u_z, u_z), v); cf = look(FR, np.where(nr[:, 2] > 0, u_x, 1 - u_x), v)
    paper = lambda c: c.min(axis=1) > 0.86
    side = np.where(paper(cs) & ~paper(cf), False, np.where(paper(cf) & ~paper(cs), True, side))
    col = np.where(side[:, None], cs, cf)
    col = col * (1 + rng.normal(0, JIT * 0.25, (len(col), 1)))
    up = np.where(np.abs(nr[:, 1:2]) > 0.9, [[1, 0, 0]], [[0, 1, 0]])
    t1 = np.cross(nr, up); t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    ang = rng.normal(0, JIT, len(t1)); t2 = np.cross(nr, t1)
    t1, t2 = t1 * np.cos(ang)[:, None] + t2 * np.sin(ang)[:, None], -t1 * np.sin(ang)[:, None] + t2 * np.cos(ang)[:, None]
    rad = R * (1 + rng.uniform(-JIT, JIT, len(t1)))
    if o.get("colors") and os.path.exists(o["colors"]): col = np.load(o["colors"])
    return dict(pts=pts + nr * R * 0.3, nr=nr, col=np.clip(col, 0, 1), a1=t1 * (rad * 1.8)[:, None], a2=t2 * (rad * 0.7)[:, None], lo=lo, hi=hi)

def view(st, yaw, S):
    """camera maths shared by render and polish: screen xy, depth, view normal, lambert shade"""
    c, s = np.cos(yaw), np.sin(yaw)
    Rm = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    P, N = st["pts"] @ Rm.T, st["nr"] @ Rm.T
    sc = S / (max(st["hi"] - st["lo"]) * 1.15); mid = (st["lo"] + st["hi"]) / 2 @ Rm.T
    xy = (P[:, :2] - mid[:2]) * [sc, -sc] + [S / 2, S / 2]
    return Rm, P, N, xy, sc, mid, 0.35 + 0.65 * np.clip(N @ L, 0, 1)

def render(st, yaw, S):
    Rm, P, N, xy, sc, mid, shade = view(st, yaw, S)
    rgb = np.clip(st["col"] * shade[:, None], 0, 1)
    keep = N[:, 2] > -0.25
    idx = np.nonzero(keep)[0][np.argsort(P[keep, 2])]
    A1, A2 = st["a1"] @ Rm.T, st["a2"] @ Rm.T
    ring = P[idx, None, :2] + np.cos(K)[None, :, None] * A1[idx, None, :2] + np.sin(K)[None, :, None] * A2[idx, None, :2]
    ring = (ring - mid[:2]) * [sc, -sc] + [S / 2, S / 2]
    im = Image.new("RGB", (S, S), BG); d = ImageDraw.Draw(im, "RGBA")
    for poly, cc in zip(ring, rgb[idx]):
        d.polygon([tuple(q) for q in poly], fill=tuple(int(x * 255) for x in cc) + (215,))
    return im

def sheet(objs, sts, angles, S, pre):
    try: font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    except OSError: font = ImageFont.load_default()
    W, H = LAB + S * len(angles), HEAD + S * len(objs)
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    for j, a in enumerate(angles):
        d.text((LAB + j * S + S // 2 - 20, 8), f"{a}\u00b0", fill="black", font=font)
        d.line([(LAB + j * S, 0), (LAB + j * S, H)], fill=(200, 200, 200))
    for i, (o, st) in enumerate(zip(objs, sts)):
        d.text((10, HEAD + i * S + S // 2 - 11), o["name"], fill="black", font=font)
        d.line([(0, HEAD + i * S), (W, HEAD + i * S)], fill=(200, 200, 200))
        for j, a in enumerate(angles):
            im.paste(render(st, np.radians(a), S), (LAB + j * S, HEAD + i * S))
        print(o["name"], "row done", flush=True)
    im.save(pre + "_sheet.png")
    json.dump(dict(sheet=os.path.abspath(pre + "_sheet.png"), size=S, lab=LAB, head=HEAD, angles=angles, rows=[o["name"] for o in objs], W=W, H=H),
              open(pre + "_layout.json", "w"), indent=1)
    print("SHEETDONE", pre + "_sheet.png", flush=True)

def polish(objs, sts, painted, lay, pre):
    S, angles = lay["size"], lay["angles"]
    img = Image.open(painted).convert("RGB")
    if img.size != (lay["W"], lay["H"]): img = img.resize((lay["W"], lay["H"]))   # painted at another resolution
    A = np.asarray(img).astype(np.float32) / 255
    O = np.asarray(Image.open(lay["sheet"]).convert("RGB")).astype(np.float32) / 255   # the sheet as sent: only repainted pixels count
    for i, (o, st) in enumerate(zip(objs, sts)):
        if o["name"] not in lay["rows"]: continue
        r = lay["rows"].index(o["name"]); n = len(st["pts"])
        best = np.full(n, -1.0); new = st["col"].copy()
        for j, a in enumerate(angles):
            Rm, P, N, xy, sc, mid, shade = view(st, np.radians(a), S)
            g = 4                                                         # depth test on a 4 px grid
            gx = np.clip((xy[:, 0] / g).astype(int), 0, S // g - 1); gy = np.clip((xy[:, 1] / g).astype(int), 0, S // g - 1)
            zmax = np.full((S // g, S // g), -np.inf); np.maximum.at(zmax, (gy, gx), np.where(N[:, 2] > 0, P[:, 2], -np.inf))
            vis = (N[:, 2] > 0.2) & (P[:, 2] >= zmax[gy, gx] - 0.03 * max(st["hi"] - st["lo"]))
            px = np.clip(np.round(xy[:, 0]).astype(int), 0, S - 1) + lay["lab"] + j * S
            py = np.clip(np.round(xy[:, 1]).astype(int), 0, S - 1) + lay["head"] + r * S
            c = A[py, px]
            changed = np.abs(c - O[py, px]).max(axis=1) > 0.08
            ok = vis & changed & (N[:, 2] > best)
            u = c[ok] / shade[ok, None]; new[ok] = u / np.maximum(1, u.max(axis=1, keepdims=True))   # unshade, keep hue (no per-channel clip); best[ok] = N[ok, 2]
        st["col"] = new
        np.save(f"{pre}_{o['name']}.npy", new)
        print(o["name"], "recoloured %d of %d strokes" % ((best > 0).sum(), n), flush=True)

if __name__ == "__main__":
    mode, objs = sys.argv[1], json.load(open(sys.argv[2]))
    if mode == "sheet":
        pre = sys.argv[3]; S = int(sys.argv[4]) if len(sys.argv) > 4 else 360
        angles = [int(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else list(range(0, 360, 45))
        sheet(objs, [strokes(o) for o in objs], angles, S, pre)
    else:
        painted, lay, pre = sys.argv[3], json.load(open(sys.argv[4])), sys.argv[5]
        sts = [strokes(o) for o in objs]
        polish(objs, sts, painted, lay, pre)
        sheet(objs, sts, lay["angles"], lay["size"], pre)
