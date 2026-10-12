"""10-12 SDF shell blend (CPU): keep the base's shape, take the detail mesh's surface only within +-t of it.
<hunyuan venv python> sdf/shell.py <base.glb> <detail.glb> <out_prefix> [t1,t2,...] [pitch]
  d = clip(d_detail, d_base - t, d_base + t)  -> marching cubes -> <out_prefix>_t<t*1000>.glb
SDF: magnitude from a KD-tree over dense surface samples, sign from a filled voxelisation (no rtree/embree needed)."""
import sys, time
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

base_p, det_p, pre = sys.argv[1:4]
ts = [float(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "0.02,0.04,0.08").split(",")]
P = float(sys.argv[5]) if len(sys.argv) > 5 else 0.008
t0 = time.time()
base, det = (trimesh.load(p, force="mesh") for p in (base_p, det_p))
lo = np.minimum(base.bounds[0], det.bounds[0]) - 0.1
hi = np.maximum(base.bounds[1], det.bounds[1]) + 0.1
axes = [np.arange(lo[i], hi[i], P) for i in range(3)]
G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
shape = tuple(len(a) for a in axes)
print("grid", shape, len(G))

def sdf(m):
    pts, _ = trimesh.sample.sample_surface_even(m, 600000)
    dist, _ = cKDTree(pts).query(G, workers=-1)
    vg = m.voxelized(P * 0.75).fill()
    inside = vg.is_filled(G)
    return np.where(inside, -dist, dist).reshape(shape).astype(np.float32)

dB, dD = sdf(base), sdf(det)
print("sdf done %.0fs" % (time.time() - t0))

def save(d, name):
    d = gaussian_filter(d, 0.6)                       # soften the KD-sample ripple
    v, f, n, _ = marching_cubes(d, 0.0, spacing=(P, P, P))
    m = trimesh.Trimesh(v + lo, f[:, ::-1], process=True)
    m.export(f"{pre}_{name}.glb")
    print(name, len(m.faces), "faces", "watertight" if m.is_watertight else "open")

save(dB, "base")
save(dD, "detail")
for t in ts:
    save(np.clip(dD, dB - t, dB + t), "t%03d" % round(t * 1000))
print("SHELLDONE %.0fs" % (time.time() - t0))
