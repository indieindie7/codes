"""Single-picture cards (trees): a cut-out picture (transparent background) -> a square 32-bit TGA, the
object centred, its lowest pixel 6% above the bottom (CardSprite stands it on the ground that way).

    <python with Pillow> prep_cards.py <out_dir> Name0=<cut.png> [Name1=<cut.png> ...] [size=256]
"""
import os, sys
from PIL import Image

out = sys.argv[1]
args = dict(a.split("=", 1) for a in sys.argv[2:])
size = int(args.pop("size", 256))
os.makedirs(out, exist_ok=True)
for name, path in args.items():
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    im = im.crop(a.getbbox())
    s = 0.92 * size / max(im.size)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    card.paste(im, ((size - im.width) // 2, size - int(0.06 * size) - im.height), im)
    card.save(os.path.join(out, name + ".tga"))
    print("card", name, im.size)
