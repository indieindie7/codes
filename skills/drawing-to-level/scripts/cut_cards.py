"""Cut tree / round-building / mansion cards from the page-3 scans (mask = dilated dark ink, holes filled; inside pixels untouched)."""
import json, numpy as np, cv2
from PIL import Image
L = json.load(open('layout.json'))
up = np.array(Image.open('map_up.png').convert('RGB'))
k = up.shape[1] / 1400
def card(rgb, name, thr=110, grow=9):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ink = (g < thr).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((grow, grow), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink)
    keep = np.zeros_like(ink)
    for i in range(1, n):                       # drop specks and long ruled-line bits
        if st[i, 4] > 0.002 * ink.size: keep[lab == i] = 1
    h, w = keep.shape
    ff = np.pad(keep, 1) * 255; m = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(ff, m, (0, 0), 128)
    mask = (ff[1:-1, 1:-1] != 128).astype(np.uint8) * 255
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    ys, xs = np.nonzero(mask > 0); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    Image.fromarray(np.dstack([rgb, mask])[y0:y1, x0:x1]).save(f'card_{name}.png'); print(name, x1 - x0, y1 - y0)
for name, (a, b, c, d) in L['cuts_preview_px'].items():
    card(up[int(b * k):int(d * k), int(a * k):int(c * k)], name)
A = np.array(Image.open('IMG_20261012_0002.jpg').convert('RGB'))
h, w = A.shape[:2]
card(A[int(0.0 * h):int(0.80 * h), int(0.04 * w):int(0.90 * w)], 'mansion', thr=120, grow=15)
