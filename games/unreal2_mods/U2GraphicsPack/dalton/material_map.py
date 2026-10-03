"""Dalton's material map: his two 512x512 atlases with the alpha channel replaced by a material ID
the dalton_metal.hlsl shader reads (the game's own alpha is a noisy gloss mask).

  alpha 1.0   polished plate  (the gold armour plates)      -> chrome or gold, gold rims
  alpha 0.66  gunmetal        (grey metal parts)            -> darker brushed metal
  alpha 0.33  cloth           (blue suit, straps, pouches)  -> rough fabric
  alpha 0.0   skin / other    (face, eyes, teeth)           -> the game's own look

Writes PlayerTorso_Material.dds / PlayerLimbs_Material.dds (32-bit, with mips) and preview PNGs.
Run: py -3.13 material_map.py [out_dir]
"""
import os, sys, struct
import numpy as np
from PIL import Image, ImageFilter

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
SRC = os.path.join(GAME, r"Meshes\Characters\Player")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

# skin and face rectangles in the torso atlas (x0, y0, x1, y1), found by eye on the atlas
SKIN = {"PlayerTorso_Default": [(228, 330, 512, 478), (440, 476, 486, 506), (440, 205, 512, 222)]}


def islands(fg):
    """connected regions of the atlas (4-neighbour), labels 1.. ; 0 = background"""
    from collections import deque
    lab = np.zeros(fg.shape, np.int32)
    h, w = fg.shape
    n = 0
    for y0 in range(h):
        for x0 in range(w):
            if fg[y0, x0] and not lab[y0, x0]:
                n += 1
                lab[y0, x0] = n
                q = deque([(y0, x0)])
                while q:
                    y, x = q.popleft()
                    for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= yy < h and 0 <= xx < w and fg[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n
                            q.append((yy, xx))
    return lab, n


def blur_within(f, mask, radius):
    """colour blurred only with pixels of the same island (normalized convolution)"""
    m = mask.astype(np.float32)
    out = np.zeros_like(f)
    mb = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255
    for c in range(3):
        cb = np.array(Image.fromarray((f[..., c] * m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255
        out[..., c] = cb / np.maximum(mb, 1e-3)
    return out


def classify(rgb):
    f = rgb.astype(np.float32) / 255
    v = f.max(-1)
    fg = v > 0.045
    sm = blur_within(f, fg, 3.0)
    r, g, b = sm[..., 0], sm[..., 1], sm[..., 2]
    mx, mn = sm.max(-1), sm.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    warm = r - b
    mat = np.full(v.shape, 0.33)                                  # cloth by default (navy suit, straps)
    grey = (np.abs(warm) < 0.035) & (sat < 0.30) & (mx > 0.10)
    mat[grey] = 0.66                                              # neutral grey = gunmetal
    gold = (warm > 0.045) & (sat > 0.22)
    mat[gold] = 1.0
    mat[~fg] = 0.33
    # island vote: small islands take one material (their majority), so little bolts don't speckle
    lab, n = islands(fg)
    for i in range(1, n + 1):
        sel = lab == i
        cnt = sel.sum()
        if cnt < 400:
            vals, c = np.unique(mat[sel], return_counts=True)
            mat[sel] = vals[np.argmax(c)]
    return mat


def mode_filter(mat, size=5):
    # majority vote over a window, so the plates come out solid (no speckle from scratches)
    levels = [0.0, 0.33, 0.66, 1.0]
    votes = [np.array(Image.fromarray(((mat == l) * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(size // 2))) for l in levels]
    return np.array(levels)[np.argmax(np.stack(votes), axis=0)]


def save_dds(path, rgba):
    levels = []
    im = Image.fromarray(rgba, "RGBA")
    while True:
        levels.append(np.array(im))
        if im.width == 1:
            break
        im = im.resize((im.width // 2, im.height // 2), Image.BOX)
    w, h = rgba.shape[1], rgba.shape[0]
    hdr = [0] * 32
    hdr[0], hdr[1] = 0x20534444, 124
    hdr[2] = 0x1007 | 0x8 | 0x20000
    hdr[3], hdr[4], hdr[5], hdr[7] = h, w, w * 4, len(levels)
    hdr[19], hdr[20], hdr[22] = 32, 0x41, 32
    hdr[23], hdr[24], hdr[25], hdr[26] = 0xFF0000, 0xFF00, 0xFF, 0xFF000000
    hdr[27] = 0x1000 | 0x400000 | 0x8
    with open(path, "wb") as fh:
        fh.write(struct.pack("<32I", *hdr))
        for l in levels:
            fh.write(l[..., [2, 1, 0, 3]].tobytes())                 # BGRA


for name, out in [("PlayerTorso_Default", "PlayerTorso_Material"), ("PlayerLimbs_Default", "PlayerLimbs_Material")]:
    rgba = np.array(Image.open(os.path.join(SRC, name + ".dds")).convert("RGBA"))
    mat = mode_filter(classify(rgba[..., :3]), 7)
    for x0, y0, x1, y1 in SKIN.get(name, []):
        mat[y0:y1, x0:x1] = 0.0
    rgba[..., 3] = (mat * 255).round().astype(np.uint8)
    save_dds(os.path.join(OUT, out + ".dds"), rgba)
    colours = np.array([[230, 200, 170], [40, 80, 220], [150, 150, 160], [255, 200, 40]], np.uint8)
    idx = np.round(mat * 3).astype(int)
    Image.fromarray(colours[idx]).save(os.path.join(OUT, out + "_preview.png"))
    print(out, {l: int((idx == i).sum()) for i, l in enumerate(["skin", "cloth", "gunmetal", "plate"])})
