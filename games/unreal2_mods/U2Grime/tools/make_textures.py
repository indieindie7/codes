"""Makes U2Grime's dust textures (Source/U2Grime/Textures/Dust*.tga).

The projector multiplies the floor by twice the texture (PB_Modulate), so 128 grey leaves the
floor as it is and darker greys darken it. Each texture is mid-grey at its border and darker,
in uneven clumps, toward the middle, slightly warmer than grey (dust is brownish).

Two shapes (clumpy, gritty) x three strengths (Dust<shape><level>: level 0 strongest; the
mod steps a spot to the next level as people walk over it). Run with Python 3 + numpy + Pillow:
    python make_textures.py
"""
import os
import numpy as np
from PIL import Image

SIZE = 128
STRENGTH = [0.42, 0.27, 0.14]          # how much darker the middle gets, per level
TINT = np.array([0.85, 0.95, 1.1])     # per channel: blue darkens most, so the dust reads warm
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Source', 'U2Grime', 'Textures')


def value_noise(rng, cells):
    """Smooth noise in 0..1: random values on a cells x cells grid (wrapping), bicubic-ish blend."""
    grid = rng.random((cells, cells))
    x = np.linspace(0, cells, SIZE, endpoint=False)
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    i0, i1 = i % cells, (i + 1) % cells
    a = grid[np.ix_(i0, i0)] * (1 - f)[None, :] + grid[np.ix_(i0, i1)] * f[None, :]
    b = grid[np.ix_(i1, i0)] * (1 - f)[None, :] + grid[np.ix_(i1, i1)] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def fbm(rng, octaves):
    total, weight, amp = 0, 0, 1.0
    for cells in octaves:
        total = total + value_noise(rng, cells) * amp
        weight += amp
        amp *= 0.55
    return total / weight


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mask(shape):
    rng = np.random.default_rng(7 + shape)
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    r = np.hypot(x - (SIZE - 1) / 2, y - (SIZE - 1) / 2) / (SIZE / 2)
    edge = fbm(rng, [4, 8]) - 0.5                      # wobbly outline
    fall = 1 - smoothstep(0.25, 0.92, r + edge * 0.35)
    if shape == 0:   # clumpy: soft patches
        body = smoothstep(0.30, 0.75, fbm(rng, [6, 12, 24]))
        m = fall * (0.35 + 0.65 * body)
    else:            # gritty: patches plus fine specks
        body = smoothstep(0.35, 0.8, fbm(rng, [8, 16]))
        grit = smoothstep(0.55, 0.9, fbm(rng, [32, 64]))
        m = fall * (0.25 + 0.45 * body + 0.3 * grit)
    m[r > 0.97] = 0                                    # border stays exactly neutral
    return np.clip(m, 0, 1)


def main():
    os.makedirs(OUT, exist_ok=True)
    for shape in range(2):
        m = mask(shape)
        for level, s in enumerate(STRENGTH):
            mult = 1 - s * m[..., None] * TINT[None, None, :]
            rgb = np.clip(np.round(128 * mult), 0, 255).astype(np.uint8)
            name = os.path.join(OUT, f'Dust{shape}{level}.tga')
            Image.fromarray(rgb, 'RGB').save(name)
            print(name, 'min', rgb.min(axis=(0, 1)), 'border', rgb[0, 0])


if __name__ == '__main__':
    main()
