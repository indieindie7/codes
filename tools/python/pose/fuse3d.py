"""fuse3d: NLF body (SMPL 6890 verts) + 3DDFA_V2 face (dense BFM) + SAM2 mask (drawcheck ref npz)
-> one coloured point cloud in image-px units -> splat-rendered turntable ("false render": back side reuses front colours).
Usage: py -3.13 fuse3d.py <img> <drawcheck_ref.npz> <face_box x0,y0,x1,y1> <out_dir>"""
import sys, os, numpy as np, torch, torchvision, cv2, yaml
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
NLF = os.environ.get('NLF_MODEL', 'models/nlf_l_multi_0.3.2.torchscript')  # https://github.com/isarandi/nlf
DDFA = os.path.abspath(os.environ.get('DDFA_DIR', '3ddfa'))  # clone of https://github.com/cleardusk/3DDFA_V2
src, refnpz, fbox, od = sys.argv[1], sys.argv[2], [float(v) for v in sys.argv[3].split(',')], sys.argv[4]
os.makedirs(od, exist_ok=True)
im = np.array(Image.open(src).convert('RGB')); Hh, Ww = im.shape[:2]
mask = np.load(refnpz)['mask'].astype(bool)

# --- body: NLF SMPL vertices (3x upscale in, px out) ---
UP = 3
m = torch.jit.load(NLF).cuda().eval()
x = torch.from_numpy(np.array(Image.fromarray(im).resize((Ww * UP, Hh * UP), Image.LANCZOS))).permute(2, 0, 1)[None].cuda()
b = torch.tensor([[Ww * .02 * UP, Hh * .01 * UP, Ww * .96 * UP, Hh * .98 * UP, 1.]], device='cuda')
with torch.inference_mode(): d = m.estimate_smpl_batched(x, [b])
v3 = d['vertices3d'][0][0].float().cpu().numpy(); v2 = d['vertices2d'][0][0].float().cpu().numpy() / UP
del m; torch.cuda.empty_cache()
A = np.c_[v3[:, :2], np.ones(len(v3))]                       # px = s*xy + t  (weak perspective fit)
sol, *_ = np.linalg.lstsq(np.r_[np.c_[v3[:, 0], np.ones(len(v3)), np.zeros(len(v3))], np.c_[v3[:, 1], np.zeros(len(v3)), np.ones(len(v3))]],
                          np.r_[v2[:, 0], v2[:, 1]], rcond=None)
s = sol[0]
body = np.c_[v2, v3[:, 2] * s]                                 # x px, y px, depth px (bigger = farther)
# densify: midpoints to 8 nearest neighbours (no SMPL faces in the torchscript)
_, nn = cKDTree(v3).query(v3, k=9)
mid = (body[:, None, :] + body[nn[:, 1:]]) / 2
body = np.unique(np.r_[body, mid.reshape(-1, 3)].round(2), axis=0)

# --- face: 3DDFA_V2 dense mesh, depth matched to the SMPL head front ---
cwd = os.getcwd(); sys.path.insert(0, DDFA); os.chdir(DDFA)
from TDDFA import TDDFA
FU = max(1, int(round(400 / (fbox[2] - fbox[0]))))
img_bgr = cv2.resize(cv2.cvtColor(im, cv2.COLOR_RGB2BGR), None, fx=FU, fy=FU, interpolation=cv2.INTER_LANCZOS4)
t = TDDFA(gpu_mode=True, **yaml.safe_load(open('configs/mb1_120x120.yml')))
param, roi = t(img_bgr, [[v * FU for v in fbox] + [1.0]])
fv = t.recon_vers(param, roi, dense_flag=True)[0].T / FU; os.chdir(cwd)
face = np.c_[fv[:, 0], fv[:, 1], -fv[:, 2]]                     # 3DDFA z grows toward camera -> flip
x0, y0, x1, y1 = fv[:, 0].min(), fv[:, 1].min(), fv[:, 0].max(), fv[:, 1].max()
inbox = (body[:, 0] > x0) & (body[:, 0] < x1) & (body[:, 1] > y0) & (body[:, 1] < y1)
head_front = np.percentile(body[inbox, 2], 15)
face[:, 2] += head_front - np.percentile(face[:, 2], 15)
# drop the SMPL face skin the BFM face replaces (front half of the head inside the face box)
body = body[~(inbox & (body[:, 2] < np.median(body[inbox, 2])))]
pts = np.r_[body, face[::2]]
part = np.r_[np.zeros(len(body)), np.ones(len(face[::2]))]

# --- colours: sample the image; outside the SAM mask take the nearest in-mask pixel (Sonar mask keeps background out) ---
_, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
px = np.clip(pts[:, 0].round().astype(int), 0, Ww - 1); py = np.clip(pts[:, 1].round().astype(int), 0, Hh - 1)
col = im[iy[py, px], ix[py, px]].astype(np.float32)

# --- splat renderer: orthographic, z-buffer by painter order, turntable about the vertical body axis ---
def render(ang, S=3, r=3, size=(None, None)):
    c = pts.mean(0); p = pts - c; a = np.radians(ang)
    xr = p[:, 0] * np.cos(a) + p[:, 2] * np.sin(a); zr = -p[:, 0] * np.sin(a) + p[:, 2] * np.cos(a)
    W, H = Ww * S, Hh * S
    u = (xr * S + W / 2).astype(int); v = ((p[:, 1] + c[1]) * S).astype(int)
    o = np.argsort(-zr)                                          # far first, near overwrites
    out = np.full((H, W, 3), 24, np.uint8)
    shade = 1.0
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            uu, vv = u[o] + dx, v[o] + dy; ok = (uu >= 0) & (uu < W) & (vv >= 0) & (vv < H)
            out[vv[ok], uu[ok]] = (col[o][ok] * shade).astype(np.uint8)
    # hole fill: gaps inside the silhouette (closing of coverage) take the nearest splatted pixel
    from scipy.ndimage import binary_closing
    cov = np.zeros((H, W), bool)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            uu, vv = u + dx, v + dy; ok = (uu >= 0) & (uu < W) & (vv >= 0) & (vv < H); cov[vv[ok], uu[ok]] = True
    sil = binary_closing(cov, np.ones((4 * r + 1, 4 * r + 1), bool))
    _, (fy, fx) = distance_transform_edt(~cov, return_indices=True)
    hole = sil & ~cov; out[hole] = out[fy[hole], fx[hole]]
    return out
frames = [render(a) for a in range(0, 360, 10)]
for a in (0, 45, 90, 180): Image.fromarray(render(a)).save(os.path.join(od, f'view_{a:03d}.png'))
sheet = np.concatenate([render(a) for a in (0, 45, 90, 180)], axis=1)
Image.fromarray(sheet).save(os.path.join(od, 'sheet.png'))
fr = [Image.fromarray(f).resize((f.shape[1] // 2, f.shape[0] // 2)) for f in frames]
fr[0].save(os.path.join(od, 'turntable.gif'), save_all=True, append_images=fr[1:], duration=80, loop=0)
np.savez(os.path.join(od, 'cloud.npz'), pts=pts, col=col, part=part)
print('points body', int((part == 0).sum()), 'face', int((part == 1).sum()), 'px_per_unit', round(s, 3))
