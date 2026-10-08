r"""Lightning-lit versions of the storm sky (Q34 research action 4, 2026-10-08): the deck lit from inside, the way
ToyShop swapped a pre-baked lightning lighting for the flash frames. From Models/StormSky.png: a cool white glow
centred on a bearing, strongest where the deck is (the cloud texture's own detail modulates it, so the billows
light up rather than a flat disc), fading toward the zenith and the edges.

    py tools/make_sky_flash.py        -> Source/U2AvalonCards/Textures/StormSkyFlash0.tga, StormSkyFlash1.tga
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
base = np.asarray(Image.open(os.path.join(HERE, "..", "Models", "StormSky.png")).convert("RGB")).astype(float) / 255
H, W, _ = base.shape
u = (np.arange(W) + 0.5) / W
v = (np.arange(H) + 0.5) / H
U, V = np.meshgrid(u, v)
lum = base.mean(-1)
detail = np.clip((lum - lum.mean()) * 3 + 0.6, 0.2, 1.4)       # the billows' own light and dark
for k, (c, el) in enumerate(((0.62, 0.55), (0.18, 0.4))):        # bearing (u) and height (v: 0 zenith, 1 horizon)
    du = np.minimum(np.abs(U - c), 1 - np.abs(U - c))
    glow = np.exp(-(du / 0.09) ** 2 - ((V - el) / 0.28) ** 2)
    wide = np.exp(-(du / 0.30) ** 2) * 0.35                     # the whole deck brightens a little
    f = (glow * 0.85 + wide * 0.7) * detail
    out = base + f[..., None] * np.array([0.78, 0.84, 1.0])
    out = out / (1 + 0.35 * out)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype("u1")).save(
        os.path.join(HERE, "..", "Source", "U2AvalonCards", "Textures", "StormSkyFlash%d.tga" % k), compression=None)
print("flash skies written")
