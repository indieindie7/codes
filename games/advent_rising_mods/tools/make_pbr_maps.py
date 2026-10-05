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
    for name, test, ro, me in PRESETS[preset]:
        mask = test(v, s, r, g, b)
        rough[mask] = ro
        metal[mask] = me
        print("  %-10s %5.1f%%  roughness %.2f metal %.1f" % (name, 100 * mask.mean(), ro, me))
    rough, metal = blur(rough, 1.5), blur(metal, 1.5)
    # the painting's fine light and dark as a little extra roughness in the dark lines
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    fine = lum - blur(lum, 3)
    rough = np.clip(rough - fine * 0.6, 0.05, 1)
    # height from the same: broad shapes a little, fine lines more; wraps like the texture
    height = blur(lum, 1.0) + 0.5 * blur(lum, 4)
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    n = np.stack([-dx * bump, -dy * bump, np.full_like(dx, 1.0 / 8)], axis=2)
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
