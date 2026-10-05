"""Contact sheets from a CardGallery pilot run: one sheet per package (several pages if large), each tile
labelled with its number, the mesh name and its real size in Unreal units.

    python gallery_sheets.py <run dir> <out dir> [cols=6] [rows=6]

The run's Unreal2.log has a "Gallery: shot <n> <Package.Group.Name> <WxDxH>" line per picture, in the
order of frames/f*.bmp. Also writes index.txt (number, mesh, size) to look pieces up by their number.
"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont

run, out = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:])
COLS, ROWS = int(o.get("cols", 6)), int(o.get("rows", 6))
TW, TH = 400, 225
os.makedirs(out, exist_ok=True)
shots = re.findall(r"Gallery: shot (\d+) (\S+) (\S+)", open(os.path.join(run, "Unreal2.log"), encoding="latin1").read())
frames = sorted(f for f in os.listdir(os.path.join(run, "frames")) if f.endswith(".bmp"))
if len(frames) != len(shots):
    print("warning: %d frames, %d gallery shots" % (len(frames), len(shots)))
try:
    font = ImageFont.truetype("arial.ttf", 13)
except OSError:
    font = ImageFont.load_default()
by_pkg = {}
with open(os.path.join(out, "index.txt"), "w") as idx:
    for (n, mesh, size), f in zip(shots, frames):
        by_pkg.setdefault(mesh.split(".")[0], []).append((int(n), mesh, size, f))
        idx.write("%s %s %s\n" % (n, mesh, size))
for pkg, items in by_pkg.items():
    per = COLS * ROWS
    for page in range(0, len(items), per):
        part = items[page:page + per]
        rows = (len(part) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * TW, rows * TH), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, (n, mesh, size, f) in enumerate(part):
            im = Image.open(os.path.join(run, "frames", f)).convert("RGB")
            w, h = im.size
            im = im.crop((int(w * 0.18), int(h * 0.08), int(w * 0.82), int(h * 0.92))).resize((TW, TH))
            x, y = (i % COLS) * TW, (i // COLS) * TH
            sheet.paste(im, (x, y))
            label = "%d  %s  %s" % (n, ".".join(mesh.split(".")[1:]), size)
            d.rectangle((x, y + TH - 20, x + TW, y + TH), fill=(0, 0, 0))
            d.text((x + 4, y + TH - 18), label, fill=(255, 255, 255), font=font)
        name = "%s_%d.jpg" % (pkg, page // per + 1)
        sheet.save(os.path.join(out, name), quality=88)
        print(name, len(part))
