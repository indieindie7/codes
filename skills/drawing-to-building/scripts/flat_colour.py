"""Repaint a pen sketch as flat, shaded colour shapes so Hunyuan builds solids instead of wire lines.
Usage: venv/Scripts/python flat_colour.py <shapes.json> <outdir> [size=512]
shapes.json: {"view_name": [[kind, [[x,y],...]], ...], ...}  coords are 0-1 of the view square, drawn in order.
kind: wall | wall2 (side in shadow) | roof | chimney | post | dark.
Why (2026-10-11): pen outlines came out as sticks and filled cut-outs as flat slabs; flat-coloured,
side-lit elevations built solid houses. Each face gets a flat tone, a soft top-light gradient and a thin dark edge."""
import sys, json, os, cv2, numpy as np

COL = {"wall": (205, 225, 235), "wall2": (150, 170, 182), "roof": (80, 110, 90), "chimney": (60, 75, 150),
       "post": (235, 240, 240), "dark": (60, 50, 45)}   # BGR
shapes, outdir = json.load(open(sys.argv[1])), sys.argv[2]
size = int(dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a).get("size", 512))
os.makedirs(outdir, exist_ok=True)
yy = np.linspace(1.08, 0.88, size)[:, None, None]          # a bit lighter at the top, darker at the base
for view, parts in shapes.items():
    img = np.full((size, size, 3), 255, np.uint8)
    for kind, pts in parts:
        p = (np.array(pts) * size).astype(np.int32)
        m = np.zeros((size, size), np.uint8); cv2.fillPoly(m, [p], 255)
        face = np.clip(np.array(COL[kind], np.float32)[None, None] * yy, 0, 255).astype(np.uint8)
        img[m > 0] = face.repeat(size, 1)[m > 0]
        cv2.polylines(img, [p], True, (40, 40, 40), max(2, size // 200), cv2.LINE_AA)
    cv2.imwrite(os.path.join(outdir, view + ".png"), img)
    print("flat_colour", view)
