r"""Soft puff textures for AvalonPlume (U2AvalonCards): py tools/make_puffs.py <out dir>

SteamPuff.tga: white cloud in RGB on exact black (drawn additive: the game's own smoke textures leave a
faint grey square round the shape, which piles up into visible rectangles when puffs overlap).
SmokePuff.tga: the same cloud shape in ALPHA over flat grey RGB (drawn alpha blended, tinted dark).
Both 128x128, uncompressed 32-bit, top-down rows; the border is fully empty so mips stay clean.
"""
import os, sys
import numpy as np
from PIL import Image

out = sys.argv[1] if len(sys.argv) > 1 else "."
N = 128
rng = np.random.default_rng(7)
y, x = (np.mgrid[0:N, 0:N] + 0.5) / N * 2 - 1
r = np.hypot(x, y)
noise = np.zeros((N, N))
for k, a in ((4, 0.5), (8, 0.3), (16, 0.2)):            # a few octaves of smooth value noise
    g = rng.random((k + 1, k + 1))
    noise += a * np.array(Image.fromarray((g * 255).astype("u1")).resize((N, N), Image.BICUBIC)) / 255.0
shape = np.clip(1 - r / 0.92, 0, 1) ** 1.6 * (0.55 + 0.45 * noise)
shape = np.clip(shape / shape.max(), 0, 1)
shape[r > 0.92] = 0
v = (shape * 255).astype("u1")
Image.fromarray(np.dstack([v, v, v, v]), "RGBA").save(os.path.join(out, "SteamPuff.tga"), compression=None)
grey = np.full((N, N), 90, "u1")                  # dark: exhaust, not steam
Image.fromarray(np.dstack([grey, grey, grey, v]), "RGBA").save(os.path.join(out, "SmokePuff.tga"), compression=None)
print("puffs ->", out)

# RainStreak.tga: one thin falling streak for AvalonStorm (additive: bright core on exact black), 32x128
W, H = 32, 128
yy, xx = (np.mgrid[0:H, 0:W] + 0.5)
core = np.exp(-((xx - W / 2) / 1.6) ** 2)                    # a hair-thin line across
along = np.clip(np.sin(np.pi * yy / H), 0, 1) ** 0.6           # fades at both ends
s = (np.clip(core * along, 0, 1) * 255).astype("u1")
s[:, :2] = 0; s[:, -2:] = 0; s[:2] = 0; s[-2:] = 0
Image.fromarray(np.dstack([s, s, s, s]), "RGBA").save(os.path.join(out, "RainStreak.tga"), compression=None)
