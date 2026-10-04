"""Drop-in replacement for Hunyuan3D-2's compiled `custom_rasterizer_kernel` (which needs nvcc + MSVC).

Only rasterize_image() is provided: that is all hy3dgen.texgen uses. Same contract as the C++/CUDA kernel:
V (N,4) clip-space vertices, F (M,3) faces -> findices (H,W) int32 with 0 = empty and face index + 1
otherwise, and barycentric (H,W,3), perspective-correct. Nearest depth wins. It runs on the CPU with numpy,
one bounding box per triangle, so it is slower than the kernel (seconds per call at 40k faces) but needs
no compiler. Put this folder and hy3dgen/texgen/custom_rasterizer on sys.path before importing hy3dgen.texgen.
"""
import numpy as np
import torch


def rasterize_image(V, F, D, width, height, occlusion_truncation, use_depth_prior):
    dev = V.device
    v = V.detach().cpu().numpy().astype(np.float64)
    f = F.detach().cpu().numpy().astype(np.int64)
    w = v[:, 3]
    sx = (v[:, 0] / w * 0.5 + 0.5) * (width - 1) + 0.5
    sy = (0.5 + 0.5 * v[:, 1] / w) * (height - 1) + 0.5
    sz = v[:, 2] / w * 0.49999 + 0.5
    prior = None
    if use_depth_prior and D is not None and D.numel():
        prior = D.detach().cpu().numpy().reshape(height, width) * 0.49999 + 0.5 + occlusion_truncation
    zbuf = np.full((height, width), np.inf)
    fidx = np.zeros((height, width), np.int32)
    bary = np.zeros((height, width, 3), np.float32)
    X0, Y0, Z0 = sx[f[:, 0]], sy[f[:, 0]], sz[f[:, 0]]
    X1, Y1, Z1 = sx[f[:, 1]], sy[f[:, 1]], sz[f[:, 1]]
    X2, Y2, Z2 = sx[f[:, 2]], sy[f[:, 2]], sz[f[:, 2]]
    xmin = np.clip(np.floor(np.minimum(X0, np.minimum(X1, X2))).astype(np.int64), 0, width - 1)
    xmax = np.clip(np.floor(np.maximum(X0, np.maximum(X1, X2))).astype(np.int64) + 1, 0, width - 1)
    ymin = np.clip(np.floor(np.minimum(Y0, np.minimum(Y1, Y2))).astype(np.int64), 0, height - 1)
    ymax = np.clip(np.floor(np.maximum(Y0, np.maximum(Y1, Y2))).astype(np.int64) + 1, 0, height - 1)
    den = (Y1 - Y2) * (X0 - X2) + (X2 - X1) * (Y0 - Y2)
    W0, W1, W2 = w[f[:, 0]], w[f[:, 1]], w[f[:, 2]]
    for i in np.where(np.abs(den) > 1e-12)[0]:
        xs = np.arange(xmin[i], xmax[i] + 1)
        ys = np.arange(ymin[i], ymax[i] + 1)
        px, py = xs[None, :] + 0.5, ys[:, None] + 0.5
        b0 = ((Y1[i] - Y2[i]) * (px - X2[i]) + (X2[i] - X1[i]) * (py - Y2[i])) / den[i]
        b1 = ((Y2[i] - Y0[i]) * (px - X2[i]) + (X0[i] - X2[i]) * (py - Y2[i])) / den[i]
        b2 = 1.0 - b0 - b1
        depth = b0 * Z0[i] + b1 * Z1[i] + b2 * Z2[i]
        sl = (slice(ymin[i], ymax[i] + 1), slice(xmin[i], xmax[i] + 1))
        ok = (b0 >= 0) & (b1 >= 0) & (b2 >= 0) & (depth >= (prior[sl] if prior is not None else 0.0)) & (depth < zbuf[sl])
        if not ok.any():
            continue
        zbuf[sl][ok] = depth[ok]
        fidx[sl][ok] = i + 1
        p0, p1, p2 = b0 / W0[i], b1 / W1[i], b2 / W2[i]
        s = p0 + p1 + p2
        bb = bary[sl]
        bb[ok, 0], bb[ok, 1], bb[ok, 2] = (p0 / s)[ok], (p1 / s)[ok], (p2 / s)[ok]
    return torch.from_numpy(fidx).to(dev), torch.from_numpy(bary).to(dev)
