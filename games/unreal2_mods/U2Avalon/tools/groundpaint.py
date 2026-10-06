r"""Paint the ground: TutA's three terrain layers (rock base, sand/beach, plant life) as alpha maps that follow
the island and the town instead of the stock island's painting.

    py tools/groundpaint.py <final heightmap.bmp> <layout.json> <template_dir> <out_dir> [road_w=1.2] [yard=1.0]

template_dir holds the editor's exports Layer1.bmp, Layer2_Beach.bmp, PlantLife1.bmp (24-bit grey BMPs,
128x128, the same bytes go back with TEXTURE IMPORT under their names in MyLevel.IslandTerrainLayers);
out_dir gets the repainted three. Rules (cells are 10.24 m):
  * sand (Layer2_Beach): roads (width road_w cells, soft edge), building footprints and the yard round them
    (`yard` cells: worn ground, the first "glue" between buildings), the beach within 1.5 cells of the sea,
    the connection corridors (pipes/conveyors) faintly;
  * plant life (PlantLife1): gentle slopes away from the sand, thinner with height and on steep ground,
    none inside the town's yards;
  * rock (Layer1, the base layer): always full under everything (it shows where the others are thin), so
    steep slopes and ridges read as rock automatically.
Also writes <out_dir>/paint_preview.png.
"""
import json, math, os, struct, sys

import numpy as np

src, layout, tdir, odir = sys.argv[1:5]
o = dict(a.split("=", 1) for a in sys.argv[5:] if "=" in a)
ROAD_W = float(o.get("road_w", 1.2))
YARD = float(o.get("yard", 1.0))
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, M, N = 512.0, 50.0, 128
SEA_Z = -4967.0
os.makedirs(odir, exist_ok=True)

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * 0.5
gy, gx = np.gradient(Z / M, CELL / M)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
WATER = Z <= SEA_Z
J, I = np.mgrid[0:N, 0:N]
WX = LOC[0] + (I - N / 2) * CELL
WY = LOC[1] + (J - N / 2) * CELL


def seg_dist(ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = np.clip(((WX - ax) * vx + (WY - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
    return np.hypot(WX - (ax + t * vx), WY - (ay + t * vy)) / CELL      # in cells


L = json.load(open(layout))
# roads
droad = np.full((N, N), np.inf)
for r in L.get("roads", []):
    for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
        droad = np.minimum(droad, seg_dist(ax, ay, bx, by))
road = np.clip(1 - (droad - ROAD_W / 2) / 0.8, 0, 1)
# pipes / conveyors: a faint worn strip
dline = np.full((N, N), np.inf)
for c in L.get("connections", []):
    if c["carrier"] in ("pipe", "conveyor"):
        p = c["path"]
        for (ax, ay), (bx, by) in zip(p[:-1], p[1:]):
            dline = np.minimum(dline, seg_dist(ax, ay, bx, by))
lines = 0.45 * np.clip(1 - (dline - 0.4) / 0.6, 0, 1)
# footprints and yards
yard = np.zeros((N, N))
for bid, b in L["buildings"].items():
    if bid == "tower":
        continue
    cells = b.get("cells", [])
    if not cells:
        continue
    cs = np.array(cells)
    d = np.full((N, N), np.inf)
    for ci, cj in cs:
        d = np.minimum(d, np.hypot(I - ci, J - cj))
    yard = np.maximum(yard, np.clip(1 - (d - 0.5) / (YARD + 0.5), 0, 1))
# beach
dwater = np.full((N, N), np.inf)
wj, wi = np.nonzero(WATER)
if len(wi):
    # chamfer-ish: distance to the nearest water cell (coarse but fine at 128)
    for dj in range(-3, 4):
        for di in range(-3, 4):
            sh = np.roll(np.roll(WATER, dj, 0), di, 1)
            dwater = np.where(sh, np.minimum(dwater, math.hypot(di, dj)), dwater)
beach = np.clip(1 - (dwater - 0.5) / 1.5, 0, 1)
sand = np.clip(np.maximum.reduce([road, yard, beach, lines]), 0, 1)
# plant life: gentle ground, not on sand, thinner high up and on steep slopes
height_t = np.clip((Z - SEA_Z) / 4500.0, 0, 1)
plant = np.clip(1 - SLOPE / 28.0, 0, 1) * (1 - 0.7 * height_t) * (1 - sand)
rng = np.random.default_rng(int(L.get("seed", 1)))
plant *= np.clip(0.75 + 0.5 * rng.random((N, N)), 0, 1.2)
plant = np.where(WATER, 0, np.clip(plant, 0, 1))
sand = np.where(WATER, 0, sand)


def write_alpha(name, A):
    """UE2 terrain layers blend by the texture's ALPHA channel (the editor paints into RGBA8 alpha), so the
    map goes out as an uncompressed 32-bit TGA: grey in RGB, the mask in A; TEXTURE IMPORT ... ALPHA=1"""
    v = np.clip(np.round(A * 255), 0, 255).astype("u1")
    # the heightmap BMP export is bottom-up and we flip it so array row 0 is the image TOP; a bottom-up TGA
    # lists the bottom row first, so write the array reversed to land on the same orientation
    rows = v[::-1]
    px = np.zeros((N, N, 4), "u1")
    px[..., 0] = px[..., 1] = px[..., 2] = rows
    px[..., 3] = rows
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, N, N, 32, 8)   # type 2 raw truecolour, 8 alpha bits, bottom-up
    open(os.path.join(odir, name + ".tga"), "wb").write(hdr + px.tobytes())


write_alpha("Layer1", np.ones((N, N)))
write_alpha("Layer2_Beach", sand)
write_alpha("PlantLife1", plant)
from PIL import Image
rgb = np.zeros((N, N, 3), "u1")
rock = (1 - np.maximum(sand, plant))
rgb[..., 0] = np.where(WATER, 30, 120 * rock + 200 * sand + 70 * plant)
rgb[..., 1] = np.where(WATER, 60, 110 * rock + 180 * sand + 140 * plant)
rgb[..., 2] = np.where(WATER, 140, 105 * rock + 120 * sand + 50 * plant)
Image.fromarray(rgb[::-1]).resize((512, 512), Image.NEAREST).save(os.path.join(odir, "paint_preview.png"))
print("ground paint: sand %.0f%% plant %.0f%% of land -> %s" % (100 * sand[~WATER].mean(), 100 * plant[~WATER].mean(), odir))
