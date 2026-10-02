"""Outfit portraits for the Options > MISC dropdown.

    py -3.13 make_portraits.py RUN_DIR

RUN_DIR is a U2Pilot run of scripts/wardrobe_photos.txt: one frame per outfit (menu
order, "wardrobe photo N" stands it in front of the camera) and a last frame of the
empty background. Each outfit is cut out by comparing with the background and put on
a see-through background (alpha); the portraits are packed into Textures/Portraits.tga
(4 x 2 cells of 240 x 400), which U2Wardrobe imports. Prints the cell rectangles for
the menu script (ssmenu_v2.py PORTRAIT_CELL must match).
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CELL_W, CELL_H, COLS = 240, 400, 4
CROP_W, CROP_H, CROP_TOP = 300, 500, 25       # in the 960x540 frames
KEEP_X = (260, 700)                            # clear of the HUD in the bottom corners
BACK = (20, 22, 26)                            # preview only

HERE = os.path.dirname(os.path.abspath(__file__))


def cutout(frame, bg):
    a = np.asarray(frame.convert("RGB")).astype(int)
    diff = np.abs(a - bg).sum(axis=2)
    m = (diff > 45).astype(np.uint8) * 255
    m[:, :KEEP_X[0]] = 0
    m[:, KEEP_X[1]:] = 0
    mi = Image.fromarray(m, "L").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    ImageDraw.floodfill(mi, (0, 0), 128)       # everything reachable from the corner is background
    mask = np.asarray(mi) != 128
    ys, xs = np.where(mask)
    cx = int(np.median(xs))                    # the bulk of the figure (stray specks pull min/max)
    alpha = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8))
    img = Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA")
    img.putalpha(alpha)
    return img, cx


def main(run_dir):
    frames = sorted(glob.glob(os.path.join(run_dir, "frames", "*.bmp")))
    bg = np.asarray(Image.open(frames[-1]).convert("RGB")).astype(int)
    outfits = frames[:-1]
    rows = (len(outfits) + COLS - 1) // COLS
    atlas = Image.new("RGBA", (1024, 1024 if rows > 1 else 512), (0, 0, 0, 0))
    for i, f in enumerate(outfits):
        img, cx = cutout(Image.open(f), bg)
        crop = img.crop((cx - CROP_W // 2, CROP_TOP, cx + CROP_W // 2, CROP_TOP + CROP_H))
        x, y = (i % COLS) * CELL_W, (i // COLS) * CELL_H
        atlas.paste(crop.resize((CELL_W, CELL_H), Image.LANCZOS), (x, y))
        print(f"WardrobePic{i},{x},{y},{CELL_W},{CELL_H}")
    out = os.path.join(HERE, "Textures", "Portraits.tga")
    atlas.save(out)
    preview = Image.new("RGBA", atlas.size, BACK + (255,))
    preview.alpha_composite(atlas)
    preview.convert("RGB").save(os.path.join(HERE, "Textures", "Portraits_preview.png"))
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
