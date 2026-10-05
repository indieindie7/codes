"""Make the PBR map of a character for the d3d8to9 fork's `pbr=` rule (Unreal II, U2Shaders.ini).

Run (Pillow + numpy: use Tools\\Hunyuan3D-2\\venv\\Scripts\\python):
    make_pbr_map.py <normal.png> <albedo.png> <out.dds> [size=1024] [flip_green=1] [preview=<png>]
        [cloth=0.85] [skin=0.6] [white=0.38] [gold=0.28] [white_metal=0.15]

normal / albedo are retopo_bake.py's `_normal.png` and `_albedo.png` (the unshaded colour, not `_diffuse`).
The map's layout is what shaders\\char_pbr.hlsl reads: r,g = tangent normal x,y (v*0.5+0.5), b = roughness,
a = metalness; uncompressed BGRA DDS with mip levels, top row first like the skin texture.

- Blender bakes the normal with green up; the game wants it down. flip_green=1 (the default) inverts it.
  Checked in game on Dalton PK: without the flip the quilting reads as dents.
- Roughness and metal are GUESSED from the albedo's colours, per pixel: saturated bright yellow = gold
  (smooth, metal), bright unsaturated = white plates (smooth, slightly metallic), dark orange-red = skin,
  everything else = cloth (rough). The numbers are the roughness of each class; tune them per character
  and look at preview= (red = roughness, green = metal) to see what each pixel was taken for.

Install: copy the .dds into <game>\\System\\U2Shaders\\ and add under [U2Shaders] in U2Shaders.ini
    pbr=<HASH> <name>.dds <highlight strength> <normal strength>          (Dalton PK: 1.6 1.5)
HASH is the fork's hash of the skin texture: run once with log=2 and find the skin in U2Shaders\\dump.
It changes whenever the skin texture changes.
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageFilter

a = sys.argv[1:]
if len(a) < 3:
    raise SystemExit(__doc__)
nrm_path, alb_path, out = a[:3]
o = dict(x.split("=", 1) for x in a[3:])
N = int(o.get("size", 1024))
R = {k: float(o.get(k, d)) for k, d in (("cloth", 0.85), ("skin", 0.6), ("white", 0.38), ("gold", 0.28))}
WHITE_METAL = float(o.get("white_metal", 0.15))


def write_dds(path, bgra):                  # same writer as advent_rising_mods/tools/make_pbr_maps.py
    levels = [bgra]
    while levels[-1].shape[0] > 1 or levels[-1].shape[1] > 1:
        m = levels[-1].astype(np.float32)
        h, w = max(1, m.shape[0] // 2), max(1, m.shape[1] // 2)
        m = m[:h * 2 or 1, :w * 2 or 1]
        if m.shape[0] >= 2 and m.shape[1] >= 2:
            m = (m[0::2, 0::2] + m[1::2, 0::2] + m[0::2, 1::2] + m[1::2, 1::2]) / 4
        levels.append(np.uint8(m[:h, :w] + 0.5))
    h, w = bgra.shape[:2]
    head = struct.pack("<4s7I44x", b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x8, h, w, w * 4, 0, len(levels))
    head += struct.pack("<2I4s5I", 32, 0x41, b"\0\0\0\0", 32, 0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    head += struct.pack("<5I", 0x1000 | 0x400000 | 0x8, 0, 0, 0, 0)
    assert len(head) == 128, len(head)
    with open(path, "wb") as fh:
        fh.write(head)
        for m in levels:
            fh.write(m.tobytes())
    print("PBRMAP", path, "%dx%d, %d levels" % (w, h, len(levels)))


load = lambda p: np.asarray(Image.open(p).convert("RGB").resize((N, N), Image.LANCZOS), np.float32) / 255
nrm, alb = load(nrm_path), load(alb_path)
r, g, b = alb[..., 0], alb[..., 1], alb[..., 2]
mx, mn = alb.max(2), alb.min(2)
sat, val, d = (mx - mn) / np.maximum(mx, 1e-4), mx, np.maximum(mx - mn, 1e-5)
hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
gold = (hue > 0.09) & (hue < 0.17) & (sat > 0.55) & (val > 0.45)      # bright saturated yellow: trim, knee cap
white = (sat < 0.22) & (val > 0.62)                                   # plates, boots
skin = (hue < 0.08) & (sat > 0.3) & (val > 0.12) & (val < 0.6)
rough = np.full((N, N), R["cloth"], np.float32)
rough[white], rough[skin], rough[gold] = R["white"], R["skin"], R["gold"]
metal = np.zeros((N, N), np.float32)
metal[gold], metal[white] = 1.0, WHITE_METAL
soft = lambda m: np.asarray(Image.fromarray(np.uint8(m * 255)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
rough, metal = soft(rough), soft(metal)
print("PBRMAP coverage: gold %.1f%%, white %.1f%%, skin %.1f%%" % (gold.mean() * 100, white.mean() * 100, skin.mean() * 100))

bgra = np.uint8(np.dstack([rough, nrm[..., 1], nrm[..., 0], metal]) * 255 + 0.5)
if int(o.get("flip_green", 1)):
    bgra[..., 1] = 255 - bgra[..., 1]
write_dds(out, bgra)
if "preview" in o:
    Image.fromarray(np.uint8(np.dstack([rough, metal, np.zeros_like(rough)]) * 255)).save(o["preview"])
