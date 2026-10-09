"""Detail textures for the fork's world-space detail rule (Avalon Q81: surface=<palette hash> world_detail.hlsl <dds>).

    py tools/make_detail_dds.py <colour image> <out.dds> [size=256] [contrast=1.0] [std=40]

Takes a CC0 colour map (ambientCG etc.), makes it grey and tileable-neutral: luminance moved so the texture's
MEAN is 0.5 (the shader multiplies by detail x 2, so on average the palette colour is unchanged) and its spread
set to stdev `std`/255 (default 40) x `contrast`. Writes a 32-bit A8R8G8B8 DDS with the full mip chain (what
the fork's LoadDDS reads), into the game's System\\U2Shaders when <out.dds> is a bare name.
"""
import os, struct, sys
from PIL import Image, ImageStat

src, out = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
N, K = int(o.get("size", 256)), float(o.get("contrast", 1.0))
if os.path.dirname(out) == "":
    out = os.path.join(r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\System\U2Shaders", out)

g = Image.open(src).convert("L").resize((N, N), Image.LANCZOS)
m = ImageStat.Stat(g).mean[0]
# deviations rescaled to a fixed spread: stdev `std` (default 40/255 = +-16 %) times `contrast`, whatever the source's
# own contrast (CC0 colour maps are often nearly flat in luminance: Rust004's stdev was 5/255)
sd = max(ImageStat.Stat(g).stddev[0], 1e-3)
STD = float(o.get("std", 40)) * K
g = g.point(lambda v: max(0, min(255, int(round(128 + (v - m) * STD / sd)))))
mips, im = [], g
while True:
    mips.append(im)
    if im.size[0] == 1:
        break
    im = im.resize((max(1, im.size[0] // 2), max(1, im.size[1] // 2)), Image.BOX)

hdr = struct.pack("<4sIIIIIII44x", b"DDS ", 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | 0x20000, N, N, N * 4, 0, len(mips))
hdr += struct.pack("<IIIIIIII", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
hdr += struct.pack("<IIII4x", 0x1000 | 0x8 | 0x400000, 0, 0, 0)
with open(out, "wb") as f:
    f.write(hdr)
    for im in mips:
        L = im.tobytes()
        f.write(bytes(b for v in L for b in (v, v, v, 255)))
print("%s: %dx%d, %d mips, source mean %.0f stdev %.1f -> 128 / %.0f" % (out, N, N, len(mips), m, sd, STD))
