"""multiview: several photos of one statue -> one coloured 3D triangle mesh + free-camera HTML viewer.
Geometry = NLF SMPL body of the FIRST view, triangulated with smpl_mesh.npz (ball-pivoted SMPL template, watertight,
NLF ships no faces), loop-subdivided twice. Colours live on vertices; the GPU lerps them across each triangle
(a*A + b*B + c*C, barycentric). Every view gets its own NLF fit; its 6890 verts are
aligned to the first (Umeyama similarity) -> per-view affine camera. Colour per point = visibility (z-buffer) x
facing weight blend over views, each view's colours normalised to the first view's mean (b&w photos get tinted).
Unseen vertices (back) take the mean of their coloured neighbours, shaded.
Usage: py -3.13 multiview.py <out_dir> <img1> <img1_drawcheck_ref.npz> [<img2> <npz2> ...]
Env: NLF_MODEL (torchscript path)."""
import sys, os, json, base64, numpy as np, torch, torchvision, trimesh
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
NLF = os.environ.get('NLF_MODEL', r'C:\Users\john\Documents\DeadOrAlive\saturn\sonar_intro\models_pose3d\nlf_l_multi_0.3.2.torchscript')
HERE = os.path.dirname(os.path.abspath(__file__))
od = sys.argv[1]; pairs = list(zip(sys.argv[2::2], sys.argv[3::2])); os.makedirs(od, exist_ok=True)
m = torch.jit.load(NLF).cuda().eval()

def nlf(im, UP=2):
    H, W = im.shape[:2]
    x = torch.from_numpy(np.array(Image.fromarray(im).resize((W * UP, H * UP), Image.LANCZOS))).permute(2, 0, 1)[None].cuda()
    b = torch.tensor([[W * .02 * UP, H * .01 * UP, W * .96 * UP, H * .98 * UP, 1.]], device='cuda')
    with torch.inference_mode(): d = m.estimate_smpl_batched(x, [b])
    return d['vertices3d'][0][0].float().cpu().numpy(), d['vertices2d'][0][0].float().cpu().numpy() / UP

def umeyama(A, B):  # s,R,t with B ~ s R A + t
    ma, mb = A.mean(0), B.mean(0); a, b = A - ma, B - mb
    U, S, Vt = np.linalg.svd(b.T @ a / len(A)); D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt; s = (S * np.diag(D)).sum() / (a ** 2).sum(1).mean(); return s, R, mb - s * R @ ma

views = []
for img, npz in pairs:
    im = np.array(Image.open(img).convert('RGB')); mask = np.load(npz)['mask'].astype(bool)
    v3, v2 = nlf(im); views.append(dict(name=os.path.basename(img), im=im, mask=mask, v3=v3, v2=v2))
    print(views[-1]['name'], 'nlf ok')
del m; torch.cuda.empty_cache()

C = views[0]['v3']                                   # canonical = first view's camera frame (mm, y down, z away)
sm = np.load(os.path.join(HERE, 'smpl_mesh.npz'))    # faces over 7155 verts = SMPL verts vmap (a few split for manifoldness)
P, F = trimesh.remesh.subdivide_loop(C[sm['vmap']].astype(np.float64), sm['faces'], iterations=2)
tm = trimesh.Trimesh(P, F, process=False)
if tm.volume < 0: F = F[:, ::-1].copy(); tm = trimesh.Trimesh(P, F, process=False)
N = tm.vertex_normals                                # outward normals (signed)
used = np.zeros(len(P), bool); used[F.ravel()] = True
ref_mean = None; acc = np.zeros((len(P), 3)); wsum = np.zeros(len(P)); src = np.zeros((len(P), len(views)))
for k, v in enumerate(views):
    s, R, t = umeyama(C, v['v3'])                    # canonical -> this view's camera frame
    pc = (s * (R @ P.T)).T + t; vc = (s * (R @ C.T)).T + t
    A, *_ = np.linalg.lstsq(np.c_[vc, np.ones(len(vc))], v['v2'], rcond=None)   # affine camera 4x2
    uv = np.c_[pc, np.ones(len(pc))] @ A; z = pc[:, 2]
    H, W = v['mask'].shape; u = uv[:, 0].round().astype(int); w_ = uv[:, 1].round().astype(int)
    ok = (u >= 0) & (u < W) & (w_ >= 0) & (w_ < H)
    zb = np.full((H, W), np.inf); r = 2
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            uu, vv = np.clip(u + dx, 0, W - 1), np.clip(w_ + dy, 0, H - 1); np.minimum.at(zb, (vv[ok], uu[ok]), z[ok])
    tol = 0.03 * (np.ptp(vc[:, 1]) / 1.7)            # ~3 cm at body scale
    vis = ok & (z <= zb[np.clip(w_, 0, H - 1), np.clip(u, 0, W - 1)] + tol)
    _, (iy, ix) = distance_transform_edt(~v['mask'], return_indices=True)
    uc, vcl = np.clip(u, 0, W - 1), np.clip(w_, 0, H - 1)
    col = v['im'][iy[vcl, uc], ix[vcl, uc]].astype(np.float64)
    inm = v['mask'][vcl, uc]
    mean = v['im'][v['mask']].reshape(-1, 3).mean(0)
    if ref_mean is None: ref_mean = mean
    col = np.clip(col * (ref_mean / np.maximum(mean, 1)), 0, 255)
    if v['im'].std(2).mean() < 3:                     # b&w photo: luminance x reference tint
        col = col.mean(1, keepdims=True) * (ref_mean / ref_mean.mean())
    dview = np.linalg.inv(s * R) @ np.array([0, 0, 1.0]); dview /= np.linalg.norm(dview)
    face = np.clip(-(N @ dview), 0, 1)               # >0 only when the surface faces this camera
    wt = vis * (face > 0.05) * (0.15 + face ** 2) * np.where(inm, 1, 0.3) * (2.0 if k == 0 else 1.0)
    acc += col * wt[:, None]; wsum += wt; src[:, k] = wt
    print(v['name'], 'visible pts', int(vis.sum()), 'of', len(P))
seen = (wsum > 1e-6) & used
col = np.zeros((len(P), 3)); col[seen] = acc[seen] / wsum[seen, None]
# unseen (no photo saw it): diffuse colours over the mesh edges from the seen border (smooth, no kNN streaks), darker
import scipy.sparse as sp
E = np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]
Adj = sp.coo_matrix((np.ones(len(E) * 2), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(len(P),) * 2).tocsr()
Adj = sp.diags(1 / np.maximum(Adj.sum(1).A1, 1)) @ Adj
_, nb = cKDTree(P[seen]).query(P[~seen], k=8); col[~seen] = col[seen][nb].mean(1)
for _ in range(300): c2 = Adj @ col; col[~seen] = c2[~seen]
col[~seen] *= 0.85
col = np.clip(col, 0, 255)                          # b&w tint can push red past 255 (uint8 wrap = cyan specks)
print('coloured', int(seen.sum()), 'filled', int((~seen).sum()))

# viewer data: centre, y up, metres
X = P - P.mean(0); X[:, 1] *= -1; X[:, 2] *= -1; X *= 1.7 / np.ptp(X[:, 1])   # NLF is in mm -> 1.7 units tall
np.savez(os.path.join(od, 'mesh.npz'), pts=X, faces=F, col=col, src=src, seen=seen)
trimesh.Trimesh(X, F, vertex_colors=np.c_[col.round(), np.full(len(X), 255)].astype(np.uint8), process=False).export(os.path.join(od, 'mesh.ply'))
data = dict(n=len(X), nf=len(F), idx=base64.b64encode(F.astype(np.uint32).tobytes()).decode(), pos=base64.b64encode(X.astype(np.float32).tobytes()).decode(),
            col=base64.b64encode(col.round().astype(np.uint8).tobytes()).decode(),
            src=base64.b64encode((src.argmax(1) * seen + (~seen) * 255).astype(np.uint8).tobytes()).decode(),
            views=[v['name'] for v in views])
html = open(os.path.join(HERE, 'viewer_template.html'), encoding='utf-8').read().replace('/*DATA*/null', json.dumps(data))
open(os.path.join(od, 'viewer.html'), 'w', encoding='utf-8').write(html)
print('wrote', os.path.join(od, 'viewer.html'))
