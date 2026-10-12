# Cut dreamsplat sheet cells into transparent imposter frames: art/imposter/<name>_NN.png (NN 00 = first angle).
# One crop box per object (union over its angles) so frames don't jump in size between angles.
import json, sys, numpy as np
from PIL import Image
from scipy import ndimage
lay = json.load(open(sys.argv[1])); out = sys.argv[2]
im = np.asarray(Image.open(lay["sheet"]).convert("RGB")).astype(np.float32)
S, LAB, HEAD = lay["size"], lay["lab"], lay["head"]
def cut(cell):
    bg = np.median(np.concatenate([cell[0], cell[-1], cell[:, 0], cell[:, -1]]), axis=0)
    fg = np.abs(cell - bg).max(axis=2) > 18
    lab, _ = ndimage.label(~fg)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    a = ~np.isin(lab, list(border))
    a = ndimage.binary_opening(a, iterations=1)
    l2, n = ndimage.label(a)
    if n > 1:
        a = l2 == (np.argmax(ndimage.sum(a, l2, range(1, n + 1))) + 1)
    return ndimage.gaussian_filter(a.astype(np.float32), 0.7)
for r, name in enumerate(lay["rows"]):
    cells = [im[HEAD + r * S: HEAD + (r + 1) * S, LAB + j * S: LAB + (j + 1) * S] for j in range(len(lay["angles"]))]
    alphas = [cut(c) for c in cells]
    m = np.max(alphas, axis=0) > 0.05
    ys, xs = np.nonzero(m)
    y1 = ys.max() + 1; y0 = ys.min(); x0, x1 = xs.min(), xs.max() + 1
    for j, (c, a) in enumerate(zip(cells, alphas)):
        rgba = np.dstack([c, a * 255])[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(f"{out}/{name}_{j:02d}.png")
    print(name, x1 - x0, y1 - y0)
