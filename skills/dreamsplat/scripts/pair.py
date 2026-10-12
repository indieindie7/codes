"""10-12 side painting helper for Kontext: put a painted front and an unpainted side next to each other,
or cut the painted result back apart.
py -3.13 sdf/pair.py join <front.png> <side.png> <out.png>     (each fitted into a 512x1024 cell, white bg)
py -3.13 sdf/pair.py split <pair.png> <front_out.png> <side_out.png>"""
import sys
from PIL import Image

def cell(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    im = bg.convert("RGB"); im.thumbnail((480, 980))
    c = Image.new("RGB", (512, 1024), "white"); c.paste(im, ((512 - im.width) // 2, (1024 - im.height) // 2))
    return c

if sys.argv[1] == "join":
    a, b, out = sys.argv[2:5]
    pair = Image.new("RGB", (1024, 1024), "white"); pair.paste(cell(a), (0, 0)); pair.paste(cell(b), (512, 0))
    pair.save(out)
else:
    p, fo, so = sys.argv[2:5]
    im = Image.open(p).convert("RGB").resize((1024, 1024))
    im.crop((0, 0, 512, 1024)).save(fo); im.crop((512, 0, 1024, 1024)).save(so)
print("PAIR", sys.argv[1])
