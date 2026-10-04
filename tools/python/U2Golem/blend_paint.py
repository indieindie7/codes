"""Mix two paints of the same low-poly (same UVs): the projection of the drawings where it can be trusted,
a generated texture (Hunyuan3D-Paint) everywhere else, with the generated one colour-matched to the drawings.

    python blend_paint.py <projection_albedo.png> <trust.png> <generated_albedo.png> <out_albedo.png> [k=12] [match=1] [mix=1]

mix=0 keeps the generated texture everywhere and only corrects its colours.
trust.png is retopo_bake.py's extra=Trust map (1 = front/back drawings saw the surface squarely).
Colour match: the generated texture's colours are clustered; for each cluster the median colour of the
projection over the same trusted texels gives an offset (pale yellow -> the sheet's orange, and so on),
applied softly to every texel, so the sides the drawings never show also take the sheet's palette.
"""
import sys
import numpy as np
from PIL import Image

a = sys.argv[1:]
o = dict(x.split("=", 1) for x in a[4:])
K, MATCH, MIX = int(o.get("k", 12)), int(o.get("match", 1)), float(o.get("mix", 1))
proj = np.asarray(Image.open(a[0]).convert("RGB"), np.float32) / 255
trust = np.asarray(Image.open(a[1]).convert("L"), np.float32) / 255
gen = np.asarray(Image.open(a[2]).convert("RGB").resize(proj.shape[1::-1], Image.LANCZOS), np.float32) / 255
if MATCH:
    m = trust > 0.7
    g, p = gen[m], proj[m]
    rng = np.random.default_rng(0)
    sub = rng.choice(len(g), min(len(g), 60000), replace=False)
    gs, ps = g[sub], p[sub]
    cent = [gs[rng.integers(len(gs))]]
    for _ in range(K - 1):                                # k-means++ on the generated colours
        d = np.min([((gs - c) ** 2).sum(1) for c in cent], 0)
        cent.append(gs[rng.choice(len(gs), p=d / d.sum())])
    cent = np.array(cent)
    for _ in range(25):
        lab = ((gs[:, None] - cent[None]) ** 2).sum(2).argmin(1)
        cent = np.array([gs[lab == k].mean(0) if (lab == k).any() else cent[k] for k in range(K)])
    off = np.zeros((K, 3), np.float32)
    for k in range(K):
        # only texel pairs that can be the same material count: the two paints never line up exactly, and a
        # gold trim line lying over green armour must not turn every trim green
        same = (lab == k) & (np.linalg.norm(ps - gs, axis=1) < 0.3)
        if same.sum() > 50:
            off[k] = np.median(ps[same], 0) - np.median(gs[same], 0)
        print(f"CLUSTER {k}: generated {np.round(cent[k], 2)} shift {np.round(off[k], 2)} ({int((lab == k).sum())} texels)")
    flat = gen.reshape(-1, 3)
    out = np.empty_like(flat)
    for i in range(0, len(flat), 400000):                 # soft assignment keeps gradients smooth
        d2 = ((flat[i:i + 400000, None] - cent[None]) ** 2).sum(2)
        w = np.exp(-d2 / (2 * 0.06 ** 2))
        w /= w.sum(1, keepdims=True) + 1e-9
        out[i:i + 400000] = flat[i:i + 400000] + w @ off
    gen = out.reshape(gen.shape).clip(0, 1)
w = np.clip((trust - 0.35) / 0.45, 0, 1)[..., None]       # full projection above 0.8 trust, none below 0.35
w = w * w * (3 - 2 * w) * MIX                           # mix=0: colour match only, no projection
res = proj * w + gen * (1 - w)
Image.fromarray((res * 255 + 0.5).astype(np.uint8)).save(a[3])
print(f"BLEND_PAINT {a[3]}: projection on {float((w > 0.5).mean()) * 100:.0f}% of the texture")
