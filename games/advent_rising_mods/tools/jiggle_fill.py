"""Fill the plate islands of the Seeker skin from the flesh around them, no AI (JIGGLE.md, phase B,
route 1). CPU only, numpy/PIL/scipy.

    py -I tools/jiggle_fill.py <jiggle dir> [<mesh.psk> <mesh.amesh>]   (reads tex/seeker_infantry.png, plate_mask.png,
                                              tex/seekerinfantry_opacity*.png; writes tex/*_filled.png
                                              and skin_fill_sheet.png; nothing of it goes to git)

Method: exemplar synthesis in blocks. The source is the skin the plates sit in ON THE MESH, not in
the atlas: the plate islands are packed among other plate islands and padding, so their atlas
ring is metal; instead the flesh triangles of the arm bones (the amesh's non-armour faces whose
dominant bone is a shoulder/arm/forearm/hand) are rasterised in UV space and a few hundred 12x12
windows of that skin are the candidates (the ring is used only when a mesh isn't given).
The islands are filled from the edge inward (blocks of 8 px with 2 px of context, in order of
their distance from the edge): each block takes the candidate whose context agrees best with
what is already known around it (the stock outside, the filled blocks inside), chosen at random
among the best few so the grain doesn't repeat, and is pasted with a soft window. A 2-3 px
feather at the island's edge blends it to the stock. The same pass fills the opacity/spec channel
files, so the chrome mask of the material no longer marks those texels as metal.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

RING = 14          # px of flesh around an island that serves as the source
P = 12             # candidate window
B = 8              # block step
NC = 500           # candidates
TOP = 4            # pick at random among the best few
FEATHER = 2.5


def fill(img, mask, rng, source=None):
    """img float (H,W,C), mask bool: the masked texels replaced from the source (the ring when
    none); the context matched is only what the fill itself has laid down, since the atlas
    around an island is no guide; feathered at the edge"""
    H, W, C = img.shape
    out = img.copy()
    known = np.zeros_like(mask)
    ring = source if source is not None else (ndimage.binary_dilation(mask, iterations=RING) & ~mask)
    # candidate windows: centred on ring pixels, fully outside the mask
    ys, xs = np.nonzero(ring)
    cands = []
    tries = 0
    while len(cands) < NC and tries < 20000:
        tries += 1
        k = rng.integers(len(ys))
        y, x = ys[k] - P // 2, xs[k] - P // 2
        if y < 0 or x < 0 or y + P > H or x + P > W:
            continue
        if mask[y:y + P, x:x + P].any() or not ring[y:y + P, x:x + P].all():
            continue
        cands.append(img[y:y + P, x:x + P])
    cands = np.array(cands)                       # (N,P,P,C)
    # blocks to fill, edge first
    dist = ndimage.distance_transform_edt(mask)
    blocks = []
    for y in range(0, H - P + 1, B):
        for x in range(0, W - P + 1, B):
            m = mask[y + 2:y + 2 + B, x + 2:x + 2 + B]
            if m.any():
                blocks.append((dist[y + 2:y + 2 + B, x + 2:x + 2 + B][m].min(), y, x))
    blocks.sort()
    filled = known.copy()
    wy = np.minimum(np.arange(P), P - 1 - np.arange(P)).astype(np.float32) + 1
    soft = np.outer(wy, wy)
    soft /= soft.max()
    for _, y, x in blocks:
        kw = filled[y:y + P, x:x + P].astype(np.float32)
        if kw.sum() < 4:
            kw[:] = 0
        tgt = out[y:y + P, x:x + P]
        cost = (((cands - tgt) ** 2).sum(axis=3) * kw).sum(axis=(1, 2)) / (kw.sum() + 1e-3)
        best = np.argsort(cost)[:TOP]
        pick = cands[best[rng.integers(len(best))]]
        need = mask[y:y + P, x:x + P] & ~filled[y:y + P, x:x + P]
        # soft paste: a new texel takes the patch; an already filled one blends by the window
        w = np.where(need, 1.0, np.where(mask[y:y + P, x:x + P], soft * 0.5, 0.0))[..., None]
        out[y:y + P, x:x + P] = tgt * (1 - w) + pick * w
        filled[y:y + P, x:x + P] |= need
    # feather the island edges into the stock
    inner = ndimage.gaussian_filter(mask.astype(np.float32), FEATHER)
    inner = np.clip((inner - 0.5) * 2 + 0.5, 0, 1) * mask
    edge = ndimage.binary_dilation(mask, iterations=1) & ~mask
    blend = np.where(mask, np.maximum(inner, 0.6), 0.0)
    return img * (1 - blend[..., None]) + out * blend[..., None], len(cands), len(blocks)


ARM_BONES = {"leftshoulder", "leftarm", "leftforearm", "lefthand", "rightshoulder", "rightarm", "rightforearm", "righthand"}


def skin_source(psk, amesh, W, H, img=None):
    """UV rasterisation of the flesh triangles, kept to the blue skin texels (the arms' own flesh
    faces are the dark leather sleeves, so a bone set gives leather and the black between islands:
    the skin is told by colour, light and blue-dominant)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from jiggle_rig import read_psk, read_amesh_flags, influences
    m = read_psk(psk)
    flags = read_amesh_flags(amesh, len(m["faces"]))
    infl = influences(m["weights"], len(m["points"]))
    names = [b["name"].lower() for b in m["bones"]]
    dom = [names[max(l, key=lambda bw: bw[1])[0]] for l in infl]
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    n = 0
    for f, fl in zip(m["faces"], flags):
        if fl:
            continue
        dr.polygon([((m["wedges"][w][2] % 1.0) * W, (m["wedges"][w][3] % 1.0) * H) for w in f[:3]], fill=255)
        n += 1
    src = np.array(im) > 127
    if img is not None:
        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        skin = (b > r + 15) & (b > g + 5) & (b > 90) & (b < 245)
        src &= ndimage.binary_opening(skin, iterations=2)
    src = ndimage.binary_erosion(src, iterations=1)
    return src, n


def main():
    j = sys.argv[1]
    tex = os.path.join(j, "tex")
    stock = np.array(Image.open(os.path.join(tex, "seeker_infantry.png")).convert("RGB")).astype(np.float32)
    H, W = stock.shape[:2]
    mask = np.array(Image.open(os.path.join(j, "plate_mask.png")).convert("L").resize((W, H))) > 127
    rng = np.random.default_rng(3)
    source = None
    if len(sys.argv) > 3:
        source, nf = skin_source(sys.argv[2], sys.argv[3], W, H, stock)
        Image.fromarray(source.astype(np.uint8) * 255).save(os.path.join(tex, "skin_source.png"))
        print("source: %d arm flesh faces, %d texels" % (nf, int(source.sum())))
    filled, nc, nb = fill(stock, mask, rng, source)
    Image.fromarray(filled.clip(0, 255).astype(np.uint8)).save(os.path.join(tex, "seeker_infantry_filled.png"))
    print("skin: %d candidates, %d blocks, %d texels filled" % (nc, nb, int(mask.sum())))
    # the channel files
    for fn in sorted(os.listdir(tex)):
        if fn.startswith("seekerinfantry_opacity") and fn.endswith(".png") and "filled" not in fn:
            im = Image.open(os.path.join(tex, fn))
            mode = im.mode
            arr = np.array(im.convert("RGB")).astype(np.float32)
            if arr.shape[:2] != (H, W):
                m2 = np.array(Image.fromarray(mask.astype(np.uint8) * 255).resize((arr.shape[1], arr.shape[0]))) > 127
            else:
                m2 = mask
            src2 = source if (source is not None and arr.shape[:2] == (H, W)) else None
            f, _, _ = fill(arr, m2, np.random.default_rng(5), src2)
            o = Image.fromarray(f.clip(0, 255).astype(np.uint8))
            if mode == "L":
                o = o.convert("L")
            o.save(os.path.join(tex, fn[:-4] + "_filled.png"))
            print("channel %s (%s): filled" % (fn, mode))
    # the sheet: stock | filled | zooms on the two largest islands (the guards)
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:2]
    zooms = []
    for k in order:
        ys, xs = np.nonzero(lab == k + 1)
        y0, y1, x0, x1 = max(ys.min() - 12, 0), min(ys.max() + 12, H), max(xs.min() - 12, 0), min(xs.max() + 12, W)
        s = 2 if max(y1 - y0, x1 - x0) > 128 else 3
        a = Image.fromarray(stock[y0:y1, x0:x1].astype(np.uint8)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST)
        b = Image.fromarray(filled[y0:y1, x0:x1].clip(0, 255).astype(np.uint8)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST)
        zooms.append((a, b, (y0, x0, y1, x1)))
    zw = max(a.width + b.width + 10 for a, b, _ in zooms)
    zh = sum(max(a.height, b.height) + 24 for a, b, _ in zooms)
    sheet = Image.new("RGB", (W * 2 + 30 + zw, max(H + 30, zh + 30)), (20, 20, 20))
    sheet.paste(Image.fromarray(stock.astype(np.uint8)), (0, 30))
    sheet.paste(Image.fromarray(filled.clip(0, 255).astype(np.uint8)), (W + 10, 30))
    dr = ImageDraw.Draw(sheet)
    dr.text((4, 8), "stock skin", fill=(230, 230, 230))
    dr.text((W + 14, 8), "plates filled from the flesh ring (no AI)", fill=(230, 230, 230))
    yy = 30
    for a, b, box in zooms:
        sheet.paste(a, (W * 2 + 20, yy))
        sheet.paste(b, (W * 2 + 30 + a.width, yy))
        dr.text((W * 2 + 20, yy - 14), "island rows %d-%d cols %d-%d: stock | filled" % box, fill=(230, 230, 230))
        yy += max(a.height, b.height) + 24
    sheet.save(os.path.join(j, "skin_fill_sheet.png"))
    print("wrote", os.path.join(j, "skin_fill_sheet.png"))


if __name__ == "__main__":
    main()
