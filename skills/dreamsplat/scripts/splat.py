"""10-12 Dreams-style splat render (CPU): cover a mesh with oriented brush-stroke splats coloured from the
painted front/side images, one fixed light, painter's algorithm. No meshing of the look, just strokes.
<hunyuan venv python> sdf/splat.py <mesh.glb> <front.png> <right.png> <out.png> [views=8] [size=360]
Rows: tight (many small strokes) and loose (fewer, bigger, jittered strokes)."""
import sys
import numpy as np, trimesh
from PIL import Image, ImageDraw

mesh_p, front_p, right_p, out = sys.argv[1:5]
NV = int(sys.argv[5]) if len(sys.argv) > 5 else 8
S = int(sys.argv[6]) if len(sys.argv) > 6 else 360
rng = np.random.default_rng(7)
m = trimesh.load(mesh_p, force="mesh")
lo, hi = m.bounds

def tex(p):
    """image as float RGB + the box of its opaque pixels (the object's extent in that view)"""
    im = Image.open(p).convert("RGBA"); a = np.asarray(im).astype(np.float32) / 255
    solid = a[..., 3] > 0.5
    if solid.all(): solid = a[..., :3].min(axis=2) < 0.93           # opaque image: object = not white paper
    ys, xs = np.nonzero(solid)
    return a[..., :3], (xs.min(), ys.min(), xs.max(), ys.max())
FR, RT = tex(front_p), tex(right_p)

def look(img, u, v):
    """u,v in 0..1 across the object's box (v=0 top) -> colour"""
    rgb, (x0, y0, x1, y1) = img
    x = np.clip(np.round(x0 + u * (x1 - x0)).astype(int), 0, rgb.shape[1] - 1)
    y = np.clip(np.round(y0 + v * (y1 - y0)).astype(int), 0, rgb.shape[0] - 1)
    return rgb[y, x]

def strokes(n, r, jit):
    pts, fi = trimesh.sample.sample_surface_even(m, n, seed=3)
    nr = m.face_normals[fi]
    u_x = (pts[:, 0] - lo[0]) / (hi[0] - lo[0]); u_z = (pts[:, 2] - lo[2]) / (hi[2] - lo[2])
    v = (hi[1] - pts[:, 1]) / (hi[1] - lo[1])
    side = np.abs(nr[:, 0]) > np.abs(nr[:, 2])                      # facing +-X -> side image, else front image
    cs = look(RT, np.where(nr[:, 0] > 0, 1 - u_z, u_z), v); cf = look(FR, np.where(nr[:, 2] > 0, u_x, 1 - u_x), v)
    paper = lambda c: c.min(axis=1) > 0.86                          # a view's outline missed the mesh here: unpainted paper
    side = np.where(paper(cs) & ~paper(cf), False, np.where(paper(cf) & ~paper(cs), True, side))
    col = np.where(side[:, None], cs, cf)
    col = col * (1 + rng.normal(0, jit * 0.25, (len(col), 1)))      # hand-mixed paint: small value wobble per stroke
    up = np.where(np.abs(nr[:, 1:2]) > 0.9, [[1, 0, 0]], [[0, 1, 0]])
    t1 = np.cross(nr, up); t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    ang = rng.normal(0, jit, len(t1))                               # stroke direction wanders a bit
    t2 = np.cross(nr, t1)
    t1, t2 = t1 * np.cos(ang)[:, None] + t2 * np.sin(ang)[:, None], -t1 * np.sin(ang)[:, None] + t2 * np.cos(ang)[:, None]
    rad = r * (1 + rng.uniform(-jit, jit, len(t1)))
    return pts + nr * r * 0.3, nr, col, t1 * (rad * 1.8)[:, None], t2 * (rad * 0.7)[:, None]

L = np.array([-0.5, 0.7, 0.6]); L /= np.linalg.norm(L)                # one light, upper left front
K = np.linspace(0, 2 * np.pi, 10, endpoint=False)
def render(st, yaw):
    pts, nr, col, a1, a2 = st
    c, s = np.cos(yaw), np.sin(yaw)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])                 # turn the object, camera stays at +Z
    P, N, A1, A2 = pts @ R.T, nr @ R.T, a1 @ R.T, a2 @ R.T
    Lr = L                                                           # light fixed to the camera rig
    shade = 0.35 + 0.65 * np.clip(N @ Lr, 0, 1)
    rgb = np.clip(col * shade[:, None], 0, 1)
    keep = N[:, 2] > -0.25                                           # back-facing strokes are hidden anyway
    order = np.argsort(P[keep, 2])                                   # far to near
    sc = S / (max(hi - lo) * 1.15); cx = cy = S / 2
    mid = (lo + hi) / 2 @ R.T
    im = Image.new("RGB", (S, S), (245, 242, 235)); d = ImageDraw.Draw(im, "RGBA")
    idx = np.nonzero(keep)[0][order]
    ring = P[idx, None, :2] + np.cos(K)[None, :, None] * A1[idx, None, :2] + np.sin(K)[None, :, None] * A2[idx, None, :2]
    ring = (ring - mid[:2]) * [sc, -sc] + [cx, cy]
    for poly, cc in zip(ring, rgb[idx]):
        d.polygon([tuple(q) for q in poly], fill=tuple(int(x * 255) for x in cc) + (215,))
    return im

rows = []
for name, n, r, jit in [("tight", 45000, 0.012, 0.25), ("loose", 9000, 0.032, 0.6)]:
    st = strokes(n, r, jit)
    rows.append(np.concatenate([np.asarray(render(st, 2 * np.pi * k / NV)) for k in range(NV)], 1))
    print(name, "done")
Image.fromarray(np.concatenate(rows, 0)).save(out)
print("SPLATDONE", out)
