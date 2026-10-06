"""Makes the material map char_pbr.hlsl wants (the d3d8 layer's pbr=HASH map.dds rule) from
a character's own texture: r, g = normal x, y; b = roughness; a = metalness.

    <python with numpy and Pillow> tools/make_pbr_maps.py <texture.dds|png> <out.dds> [preset]

The game has only the painted colour texture, so the rest is guessed from it:
  - the normal map from the painting's light and dark (dark lines are grooves, seams, folds);
  - roughness and metalness by what the colour says the material is (PRESETS: skin, pale
    cloth, dark cloth or leather, grey gear as worn metal).
A first pass for testing the look; the maps of a character that matters can be repainted
by hand afterwards (the output is a plain 32-bit DDS).
"""
import struct
import sys

import numpy as np
from PIL import Image, ImageFilter

# (name, test on (value, saturation, r, g, b) arrays) -> roughness, metalness; later rows win
PRESETS = {
    "uniform": [
        ("base",       lambda v, s, r, g, b: v >= 0,                              0.70, 0.0),
        ("pale cloth", lambda v, s, r, g, b: (v > 0.6) & (s < 0.25),              0.85, 0.0),
        ("dark cloth", lambda v, s, r, g, b: v < 0.22,                            0.50, 0.0),
        ("gear",       lambda v, s, r, g, b: (v > 0.22) & (v < 0.6) & (s < 0.22), 0.38, 0.7),
        ("skin",       lambda v, s, r, g, b: (r > g * 1.12) & (g > b * 1.05) & (v > 0.35) & (s > 0.25), 0.55, 0.0),
        ("lights",     lambda v, s, r, g, b: (s > 0.6) & (v > 0.6) & (b > r),     0.25, 0.0),
    ],
}


# Hand corrections per texture: (x0, y0, x1, y1 in the texture's pixels at 512 wide, test,
# roughness, metalness), applied in order after the colour rules. Read off the texture with a
# grid over it (the atlas's parts: jacket, gear, vest, skin, gloves and boots, trousers).
ANY = lambda v, s, r, g, b: v >= 0
REGIONS = {
    "gideon_uniform": [
        ((0, 0, 212, 262),     ANY,                                         0.90, 0.0),   # the white jacket: matt cloth
        ((0, 0, 212, 262),     lambda v, s, r, g, b: v < 0.35,              0.50, 0.0),   # its loops and trim
        ((158, 4, 192, 46),    lambda v, s, r, g, b: v < 0.78,              0.28, 1.0),   # rank bars: metal
        ((150, 160, 190, 262), lambda v, s, r, g, b: v < 0.4,               0.60, 0.0),   # quilted band
        ((212, 0, 392, 130),   lambda v, s, r, g, b: v <= 0.3,              0.45, 0.0),   # gear: dark plastic
        ((212, 0, 392, 130),   lambda v, s, r, g, b: (v > 0.3) & (s < 0.3), 0.30, 0.9),   # gear: its metal
        ((392, 0, 512, 130),   ANY,                                         0.72, 0.0),   # dark cloth
        ((424, 40, 466, 80),   lambda v, s, r, g, b: (r > g * 1.15) & (v > 0.5), 0.22, 1.0),   # the gold emblem
        ((212, 130, 512, 262), ANY,                                         0.72, 0.0),   # the vest
        ((0, 262, 112, 512),   ANY,                                         0.50, 0.0),   # skin
        ((0, 262, 112, 316),   lambda v, s, r, g, b: v < 0.7,               0.65, 0.0),   # hair
        ((112, 262, 215, 512), ANY,                                         0.33, 0.0),   # gloves and boots: polished leather
        ((215, 262, 512, 512), ANY,                                         0.80, 0.0),   # trousers
        ((215, 262, 512, 512), lambda v, s, r, g, b: (v > 0.42) & (s < 0.25), 0.28, 1.0), # their buckle, studs, zip pull
        ((250, 266, 282, 326), lambda v, s, r, g, b: v > 0.22,              0.35, 0.9),   # the zip
    ],
}


# how strong the generated normal map is per region (a factor on the preset's bump; later
# rows win): the painted shading of pale, smooth cloth reads as noise when bumped, dark cloth
# and leather take it well (the user, 2026-10-05: white jacket weird, dark clothes good)
BUMP_REGIONS = {
    "gideon_uniform": [
        ((0, 0, 212, 262), 0.25),      # the white jacket
        ((212, 130, 512, 262), 0.6),   # the vest
        ((0, 262, 112, 512), 0.4),     # skin and hair
    ],
}


def blur(a, radius):
    im = Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255


def make(texture, preset="uniform", bump=2.5):
    rgb = np.asarray(Image.open(texture).convert("RGB"), dtype=np.float32) / 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    v = rgb.max(axis=2)
    s = (v - rgb.min(axis=2)) / np.maximum(v, 1e-4)
    rough = np.zeros_like(v)
    metal = np.zeros_like(v)
    for name, test, ro, me in PRESETS.get(preset, PRESETS["uniform"]):
        mask = test(v, s, r, g, b)
        rough[mask] = ro
        metal[mask] = me
        print("  %-10s %5.1f%%  roughness %.2f metal %.1f" % (name, 100 * mask.mean(), ro, me))
    k = rgb.shape[1] / 512.0
    for (x0, y0, x1, y1), test, ro, me in REGIONS.get(preset, []):
        mask = np.zeros(v.shape, dtype=bool)
        mask[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)] = True
        mask &= test(v, s, r, g, b)
        rough[mask] = ro
        metal[mask] = me
    rough, metal = blur(rough, 1.0), blur(metal, 0.8)
    # the painting's fine light and dark as a little extra roughness in the dark lines
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fine = lum - blur(lum, 3)
    rough = np.clip(rough - fine * 0.6, 0.05, 1)
    # height from the same: broad shapes a little, fine lines more; wraps like the texture
    height = blur(lum, 1.0) + 0.5 * blur(lum, 4)
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    bumpmap = np.full_like(dx, bump)
    for (x0, y0, x1, y1), factor in BUMP_REGIONS.get(preset, []):
        bumpmap[int(y0 * k):int(y1 * k), int(x0 * k):int(x1 * k)] = bump * factor
    bumpmap = blur(bumpmap / max(bump, 1e-6), 2.0) * bump
    n = np.stack([-dx * bumpmap, -dy * bumpmap, np.full_like(dx, 1.0 / 8)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    out = np.stack([rough, n[..., 1] * 0.5 + 0.5, n[..., 0] * 0.5 + 0.5, metal], axis=2)   # B, G, R, A
    return np.uint8(np.clip(out, 0, 1) * 255 + 0.5)


def write_dds(path, bgra):
    levels = [bgra]
    while levels[-1].shape[0] > 1 or levels[-1].shape[1] > 1:
        a = levels[-1].astype(np.float32)
        h, w = max(1, a.shape[0] // 2), max(1, a.shape[1] // 2)
        a = a[:h * 2 or 1, :w * 2 or 1]
        if a.shape[0] >= 2 and a.shape[1] >= 2:
            a = (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4
        levels.append(np.uint8(a[:h, :w] + 0.5))
    h, w = bgra.shape[:2]
    head = struct.pack("<4s7I44x", b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x8, h, w, w * 4, 0, len(levels))
    head += struct.pack("<2I4s5I", 32, 0x41, b"\0\0\0\0", 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    head += struct.pack("<5I", 0x1000 | 0x400000 | 0x8, 0, 0, 0, 0)
    assert len(head) == 128, len(head)
    with open(path, "wb") as fh:
        fh.write(head)
        for a in levels:
            fh.write(a.tobytes())
    print(path, "%dx%d, %d levels" % (w, h, len(levels)))


if __name__ == "__main__":
    write_dds(sys.argv[2], make(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else "uniform"))
