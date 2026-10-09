r"""Rain textures for AvalonStorm (Q34, 2026-10-08, from games/research_notes/Realistic clouds and rain):
py tools/make_rain.py <out dir>

All drawn additive (light on exact black), dim and blue-grey rather than bold white dashes - a real streak is a
faint refraction of the sky, seen mostly against dark ground. Sprites can't rotate, so the wind's slant is baked:
each texture comes in three slants (L = leaning left on screen, C = straight, R = leaning right) and the storm
picks one each tick from the wind across the view.

RainDropL/C/R.tga  32x128: one thin tapered streak with a soft tail (the near drops)
RainSheetL/C/R.tga 256x256: a few dozen faint streaks of mixed length at random (the mid and far rain layers:
                   one sprite = a patch of rain falling a few metres to tens of metres away)
"""
import os, sys
import numpy as np
from PIL import Image

out = sys.argv[1] if len(sys.argv) > 1 else "."
rng = np.random.default_rng(11)
TINT = np.array([0.80, 0.88, 1.0])             # blue-grey: the dusk sky through water
SLANT = {"L": -0.32, "C": 0.0, "R": 0.32}       # screen dx per dy (about 18 degrees)


def save(name, v):
    v = np.clip(v, 0, 1)
    v[:2] = 0; v[-2:] = 0; v[:, :2] = 0; v[:, -2:] = 0     # empty borders: clean mips, no square
    rgb = (v[..., None] * TINT * 255).astype("u1")
    a = (v * 255).astype("u1")
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(os.path.join(out, name + ".tga"), compression=None)


def streak(img, x0, y0, length, width, peak, slant):
    """a tapered streak from (x0, y0) downward: a bright leading head, a fading tail"""
    H, W = img.shape
    ys = np.arange(max(0, int(y0)), min(H, int(y0 + length)))
    for y in ys:
        t = min(max((y - y0) / length, 0.0), 1.0)              # 0 = top (tail) .. 1 = bottom (head)
        a = peak * (t ** 1.5) * np.clip((1 - t) * 6, 0, 1)      # tail fades in, head ends soft
        cx = x0 + slant * (y - y0)
        xs = np.arange(max(0, int(cx - 4)), min(W, int(cx + 5)))
        img[y, xs] += a * np.exp(-((xs - cx) / width) ** 2)


for k, s in SLANT.items():
    # one drop: centred so the slant stays inside the 32 px width
    W, H = 32, 128
    d = np.zeros((H, W))
    streak(d, W / 2 - s * 0.45 * H, 6, H - 12, 0.9, 0.55, s)
    save("RainDrop" + k, d)
    # a sheet of rain: many faint streaks, mixed lengths and strengths
    N = 256
    sh = np.zeros((N, N))
    for _ in range(46):
        L = rng.uniform(30, 110)
        y0 = rng.uniform(4, N - L - 4)
        x0 = rng.uniform(12, N - 12) - s * L / 2
        streak(sh, x0, y0, L, rng.uniform(0.6, 1.1), rng.uniform(0.12, 0.42), s)
    yy, xx = (np.mgrid[0:N, 0:N] + 0.5) / N * 2 - 1
    sh *= np.clip(1 - np.maximum(np.abs(xx), np.abs(yy)) ** 6, 0, 1)   # fade the edges: sheets overlap unseen
    save("RainSheet" + k, sh)
# a splash (Q34 next step, 2026-10-08): the crown a drop throws up where it lands, seen side-on (sprites face the
# camera); the bottom half of the sprite is empty so the sprite's centre sits on the ground
N = 64
sp = np.zeros((N, N))
yy, xx = np.mgrid[0:N, 0:N] + 0.5
cx, cy = N / 2, N / 2
sp += 0.5 * np.exp(-(((xx - cx) / 13) ** 2 + ((yy - cy) / 1.6) ** 2))     # the flat ring on the ground
for i in range(9):                                                         # the crown's droplets, fanned upward
    ang = np.radians(-70 + 140 * i / 8 + rng.uniform(-6, 6))
    L = rng.uniform(9, 17)
    for t in np.linspace(0.15, 1.0, 24):
        x = cx + np.sin(ang) * L * t * 1.2
        y = cy - np.cos(ang) * L * t * (1.15 - 0.35 * t)
        sp += 0.16 * (1 - t * 0.6) * np.exp(-(((xx - x) / 1.1) ** 2 + ((yy - y) / 1.1) ** 2))
sp[int(cy) + 3:] = 0
save("RainSplash", sp)
print("rain ->", out)
