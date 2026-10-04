"""Dye: repaint kitbash donor textures into one palette, so parts from different characters read
as one suit (the idea behind Destiny's shaders and UT's team colours: armour is split into
material channels, and one palette paints every piece).

Channels, from each pixel's (lightly blurred) colour:
  plate  warm, saturated (bronze, gold, brown leather, red paint)  -> palette "plate"
  metal  neutral grey/silver (bare steel, bolts, spikes)            -> palette "metal"
  cloth  cool or other saturated colours (blue suit, green cloth)   -> palette "cloth"
  dark   near black (seams, gaps, shadows)                          -> kept as is
The repaint keeps the texture's own shading: the new colour takes the palette's hue and
saturation, and the pixel's brightness relative to its channel's average brightness.

    from dye import palette_from, dye
    pal = palette_from(["PlayerTorso_Default.tga", "PlayerLimbs_Default.tga"], skip_rects=...)
    dye("NightMaleABodyA.tga", pal, "NightMaleABodyA_dyed.tga")
"""
import colorsys
import numpy as np
from PIL import Image, ImageFilter

CHANNELS = ("plate", "metal", "cloth")


def _hsv(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    mx, mn = a.max(-1), a.min(-1)
    v = mx
    s = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = np.maximum(mx - mn, 1e-4)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, s, v


def classify(im):
    """channel index per pixel: 0 plate, 1 metal, 2 cloth, -1 dark"""
    h, s, v = _hsv(im.convert("RGB").filter(ImageFilter.GaussianBlur(1.5)))
    ch = np.full(h.shape, 2, np.int8)
    warm = ((h < 60) | (h > 330)) & (s > 0.22)
    neutral = s <= 0.22
    ch[warm] = 0
    ch[neutral] = 1
    ch[v < 0.07] = -1
    return ch, h, s, v


def palette_from(paths, skip_rects=None):
    """the mean hue/saturation/brightness of each channel over a set of textures (the base
    character's look); skip_rects: {path: [(x0, y0, x1, y1) in 0..1]} to leave out (faces)"""
    acc = {c: [] for c in CHANNELS}
    for p in paths:
        im = Image.open(p)
        ch, h, s, v = classify(im)
        keep = np.ones(ch.shape, bool)
        for x0, y0, x1, y1 in (skip_rects or {}).get(p, []):
            H, W = ch.shape
            keep[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = False
        for i, c in enumerate(CHANNELS):
            m = (ch == i) & keep
            if m.sum() > 50:
                hh = np.radians(h[m])
                hue = np.degrees(np.arctan2(np.sin(hh).mean(), np.cos(hh).mean())) % 360
                acc[c].append((m.sum(), hue, s[m].mean(), v[m].mean()))
    pal = {}
    for c, rows in acc.items():
        n = sum(r[0] for r in rows)
        pal[c] = tuple(sum(r[0] * r[k] for r in rows) / n for k in (1, 2, 3)) if n else None
    return pal


def dye(src, pal, dst, strength=1.0):
    im = Image.open(src).convert("RGBA")
    rgb = im.convert("RGB")
    ch, _, _, _ = classify(rgb)
    h, s, v = _hsv(rgb)
    out = np.asarray(rgb).astype(np.float32) / 255
    for i, c in enumerate(CHANNELS):
        if pal.get(c) is None:
            continue
        m = ch == i
        if m.sum() == 0:
            continue
        ph, ps, pv = pal[c]
        nv = np.clip(v[m] / max(v[m].mean(), 1e-3) * pv, 0, 1)        # keep the shading
        if c == "metal":
            ns = np.minimum(s[m], 0.12) * 0.5 + ps * 0.5                # metal stays near grey
        else:
            ns = np.full(nv.shape, ps)
        col = np.array([colorsys.hsv_to_rgb(ph / 360, a, b) for a, b in zip(ns, nv)]) if m.sum() < 2000 else None
        if col is None:
            # vectorised hsv -> rgb
            H = np.full(nv.shape, ph / 60.0)
            C = nv * ns
            X = C * (1 - abs(H % 2 - 1))
            z = np.zeros_like(C)
            k = int(H[0]) % 6
            r, g, b = [(C, X, z), (X, C, z), (z, C, X), (z, X, C), (X, z, C), (C, z, X)][k]
            mm = nv - C
            col = np.stack([r + mm, g + mm, b + mm], -1)
        out[m] = out[m] * (1 - strength) + col * strength
    res = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")
    res.putalpha(im.getchannel("A"))
    res.save(dst)
    return dst
