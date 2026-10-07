r"""Give a generated island the stock island's relief: the land heights are remapped (monotone, so every
shape, ridge order and flat stays) onto the height distribution of TutA's own island, with the tower's
cell pinned to the stock height so the tower's BSP foot meets the ground.

    py tools/relief_match.py <island.bmp> <stock island1.bmp> [out.bmp]   (default: overwrite)

Why: island_form sets the sea for ~40 % land and caps the plateau a few metres over the sea, so its land
sat at a median ~14 m against the stock island's ~65 m (90th percentile 39 m against 120 m); in game
the island read as squashed flat. The tower cell already sits at the stock height; it stays pinned.
How: split both land distributions at the tower height; our cells below it are quantile-matched to the
stock cells below the stock tower height, those above to the stock cells above. Sea cells are untouched.
"""
import struct, sys

import numpy as np


def read_bmp(bmp):
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    return raw, off, h < 0, (H if h < 0 else H[::-1])

src, stock = sys.argv[1:3]
out = sys.argv[3] if len(sys.argv) > 3 else src
SEA_H = 32768 + (-4967 + 131.85) * 2          # the sea surface as a heightmap value
TI, TJ = 92, 57                               # the real tower's cell (column, row)

raw, off, up, A = read_bmp(src)
_, _, _, S = read_bmp(stock)
land, sland = A > SEA_H, S > SEA_H
ht, st = A[TJ, TI], S[TJ, TI]
B = A.copy()


def match(mask, ref):
    """quantile-match A[mask] onto the values ref (both sorted by rank)"""
    v = A[mask]
    if v.size == 0 or ref.size == 0:
        return
    ranks = np.argsort(np.argsort(v)) / max(1, v.size - 1)
    B[mask] = np.quantile(ref, ranks)


lo, hi = land & (A <= ht), land & (A > ht)
match(lo, S[sland & (S <= st)])
match(hi, S[sland & (S > st)])
B[TJ, TI] = st
# ease in with distance from the tower: the town ground (within ~400 m) gets 65 % of the remap, the stock
# relief is full beyond ~850 m. Without this the plain stayed at tower level while everything a little higher
# jumped to stock hill heights, and the town stood in a canyon of cut walls (first rebuild, 2026-10-07).
JJ, II = np.mgrid[0:A.shape[0], 0:A.shape[1]]
dist_m = np.hypot(II - TI, JJ - TJ) * 10.24
t = np.clip((dist_m - 400) / 450, 0, 1)
w = 0.65 + 0.35 * t * t * (3 - 2 * t)                    # 65 % of the stock relief at the town, 100 % far out
B = A + w * (B - A)
B = np.where(land, np.maximum(B, SEA_H + 4), A)          # land stays land
Hn = np.clip(np.round(B), 0, 65535).astype("<u2")
pix = (Hn if up else Hn[::-1]).tobytes()
open(out, "wb").write(raw[:off] + pix + raw[off + len(pix):])


def metres(v):
    return (v - SEA_H) * 0.5 / 50


pct = lambda X, m: [round(metres(np.percentile(X[m], q)), 1) for q in (10, 50, 90, 100)]
print("relief: land %d cells; before p10/50/90/max %s m, after %s m, stock %s m; tower %.1f -> %.1f m" % (
    land.sum(), pct(A, land), pct(B, land), pct(S, sland), metres(ht), metres(st)))
