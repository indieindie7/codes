"""The colour pattern of the Hunyuan paint models, measured: pulls the texture out of each *_paint.glb and
quantises it, so the scripted/parts builders can use the same colours.

    py tools/hunyuan_palette.py <dir with *_paint.glb> [out.json]

Prints, per model, its 6 dominant colours (sRGB 0-255, with their share of the texture), and a merged
palette over all models (share-weighted k-means) as JSON.
"""
import glob, json, os, struct, sys
from io import BytesIO
from PIL import Image

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, "hunyuan_palette.json")


def glb_images(path):
    data = open(path, "rb").read()
    magic, ver, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF"
    off = 12
    js, bins = None, None
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bins = chunk
        off += 8 + clen
    imgs = []
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        b = bins[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]]
        imgs.append(Image.open(BytesIO(b)).convert("RGB"))
    return imgs


def dominant(im, n=6):
    small = im.resize((256, 256))
    q = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:n * 3]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]), round(c / total, 3)) for c, i in counts]


allpix = []
report = {}
for f in sorted(glob.glob(os.path.join(src, "*_paint.glb"))):
    name = os.path.basename(f)[:-10]
    imgs = glb_images(f)
    if not imgs:
        continue
    cols = dominant(imgs[0])
    report[name] = [{"rgb": c, "share": s} for c, s in cols]
    print(name, " ".join("#%02x%02x%02x %.0f%%" % (c + (s * 100,)) for c, s in cols))
    allpix.append(imgs[0].resize((128, 128)))
# the merged palette: quantise a strip of every model's texture together
strip = Image.new("RGB", (128 * len(allpix), 128))
for k, im in enumerate(allpix):
    strip.paste(im, (128 * k, 0))
merged = dominant(strip, 7)
report["_merged"] = [{"rgb": c, "share": s} for c, s in merged]
print("MERGED", " ".join("#%02x%02x%02x %.0f%%" % (c + (s * 100,)) for c, s in merged))
json.dump(report, open(out, "w"), indent=1)
print("->", out)
