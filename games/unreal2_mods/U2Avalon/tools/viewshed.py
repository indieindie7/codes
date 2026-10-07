r"""What the player can see: a viewshed of the island from the map's playable area.

    py tools/viewshed.py <heightmap.bmp> <navpoints.json> <layout.json or -> <out_prefix> [eye=64] [window=300,34]

Film-set thinking (Anatomy of Decay, "build only what the camera sees"): Avalon's player only stands on
the tower's decks, balconies and stairs (U2Pilot playshots: the map's NavigationPoints), so the island is
a set seen from a few dozen fixed places. For every navigation point the terrain is ray-marched to every
cell (heightmap only; the tower's own walls are not known, so points on the enclosed command deck - the
PlayerStart's floor - only look through the window sector `window=yaw,half-angle`, the rest see all
round). Each cell gets
    seen  = how many points see it,
    score = sum over points of 1 / (1 + distance / 2000 u): near, often-seen ground scores high.
Writes <out_prefix>_vis.npz (seen, score), <out_prefix>_vis.png (the map, seen ground lit by score) and
<out_prefix>_vis.json (per building: points that see it, best distance, score). clutter.py vis=... uses
the npz as the detail budget: nothing where nobody looks, more where everybody does.
"""
import json, math, struct, sys

import numpy as np

src, nav_path, layout_path, prefix = sys.argv[1:5]
o = dict(a.split("=", 1) for a in sys.argv[5:] if "=" in a)
EYE = float(o.get("eye", 64))
WIN_YAW, WIN_HALF = (float(v) for v in o.get("window", "300,34").split(","))
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, N, SEA_Z = 512.0, 128, -4967.0

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * 0.5
Zs = np.maximum(Z, SEA_Z)                     # the sea surface hides nothing below it
J, I = np.mgrid[0:N, 0:N]
WX = LOC[0] + (I - N / 2) * CELL
WY = LOC[1] + (J - N / 2) * CELL


def bil(x, y):
    """terrain height at arrays of world positions (bilinear, clamped)"""
    fi = np.clip((x - LOC[0]) / CELL + N / 2, 0, N - 1.001)
    fj = np.clip((y - LOC[1]) / CELL + N / 2, 0, N - 1.001)
    i0, j0 = fi.astype(int), fj.astype(int)
    ti, tj = fi - i0, fj - j0
    return (Zs[j0, i0] * (1 - ti) * (1 - tj) + Zs[j0, i0 + 1] * ti * (1 - tj) + Zs[j0 + 1, i0] * (1 - ti) * tj
            + Zs[j0 + 1, i0 + 1] * ti * tj)


pts = json.load(open(nav_path))
start = next((p for p in pts if p["class"] == "PlayerStart"), pts[0])
sx, sy, sz = start["loc"]
seen = np.zeros((N, N))
score = np.zeros((N, N))
STEPS = 96
ts = np.linspace(0.02, 0.98, STEPS)[:, None, None]
for p in pts:
    x0, y0, z0 = p["loc"]
    ez = z0 + EYE
    dx, dy = WX - x0, WY - y0
    dist = np.hypot(dx, dy)
    target = Zs + 60                                   # a point 1.2 m over the ground counts as seen
    # ray-march: the terrain along the line must stay under the sight line
    xs, ys = x0 + dx[None] * ts, y0 + dy[None] * ts
    line = ez + (target - ez)[None] * ts
    vis = np.all(bil(xs, ys) <= line + 1.0, axis=0)
    # the enclosed command deck (the PlayerStart's floor, near it): only through the window
    if abs(z0 - sz) < 120 and math.hypot(x0 - sx, y0 - sy) < 2500:
        ang = np.degrees(np.arctan2(dy, dx))
        vis &= np.abs((ang - WIN_YAW + 180) % 360 - 180) <= WIN_HALF
    seen += vis
    score += vis / (1 + dist / 2000.0)
land = Z > SEA_Z
print("viewshed: %d points; land seen by >=1 point %.0f%%, by >=5 %.0f%%; sea seen %.0f%%" % (
    len(pts), 100 * (seen[land] > 0).mean(), 100 * (seen[land] >= 5).mean(), 100 * (seen[~land] > 0).mean()))
np.savez_compressed(prefix + "_vis.npz", seen=seen, score=score)

# per building: how much of the camera time it gets
if layout_path == "-":
    raise SystemExit(0)
L = json.load(open(layout_path))
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import binder  # noqa
_, sheets = binder.load()
rows = {}
for bid, b in L["buildings"].items():
    fi = int(np.clip(round((b["x"] - LOC[0]) / CELL + N / 2), 0, N - 1))
    fj = int(np.clip(round((b["y"] - LOC[1]) / CELL + N / 2), 0, N - 1))
    bd = min(math.hypot(b["x"] - p["loc"][0], b["y"] - p["loc"][1]) for p in pts)
    # a building counts as seen when its upper part is (a tall hall's roof shows over a ridge that hides its foot)
    hgt = sheets.get(bid, {}).get("size", (0, 0, 6))[2] * 50.0
    tz = max(float(bil(np.array([b["x"]]), np.array([b["y"]]))[0]), SEA_Z) + 0.7 * hgt
    n_seen = 0
    for p in pts:
        x0, y0, z0 = p["loc"]
        if abs(z0 - sz) < 120 and math.hypot(x0 - sx, y0 - sy) < 2500:
            ang = math.degrees(math.atan2(b["y"] - y0, b["x"] - x0))
            if abs((ang - WIN_YAW + 180) % 360 - 180) > WIN_HALF:
                continue
        t = np.linspace(0.02, 0.9, 64)
        xs, ys = x0 + (b["x"] - x0) * t, y0 + (b["y"] - y0) * t
        if np.all(bil(xs, ys) <= (z0 + EYE) + (tz - z0 - EYE) * t + 1.0):
            n_seen += 1
    rows[bid] = {"seen_by": n_seen, "score": round(float(score[fj, fi]), 2), "nearest_m": round(bd / 50)}
json.dump(rows, open(prefix + "_vis.json", "w"), indent=1)
hidden = sorted(b for b, r in rows.items() if r["seen_by"] == 0)
print("buildings seen from the playable area: %d of %d; never seen: %s" % (len(rows) - len(hidden), len(rows), ", ".join(hidden) or "-"))

from PIL import Image
gy, gx = np.gradient(Z, CELL)
lit = np.clip(0.55 + 1.2 * (-gx - gy), 0.15, 1.0)
s = np.clip(score / max(1e-6, np.percentile(score[score > 0], 95) if (score > 0).any() else 1), 0, 1)
rgb = np.zeros((N, N, 3))
rgb[..., 0] = np.where(land, 40 + 60 * lit + 155 * s, 20)
rgb[..., 1] = np.where(land, 40 + 60 * lit + 120 * s, 40 + 60 * (seen > 0))
rgb[..., 2] = np.where(land, 45 + 50 * lit, 90 + 60 * (seen > 0))
img = Image.fromarray(rgb[::-1].astype("u1")).resize((640, 640), Image.NEAREST)
from PIL import ImageDraw
d = ImageDraw.Draw(img)
for bid, b in L["buildings"].items():
    u = ((b["x"] - LOC[0]) / CELL + N / 2) * 5
    v = (N - ((b["y"] - LOC[1]) / CELL + N / 2)) * 5
    c = (255, 255, 255) if rows[bid]["seen_by"] else (255, 60, 60)
    d.rectangle([u - 2, v - 2, u + 2, v + 2], outline=c)
for p in pts:
    u = ((p["loc"][0] - LOC[0]) / CELL + N / 2) * 5
    v = (N - ((p["loc"][1] - LOC[1]) / CELL + N / 2)) * 5
    d.point((u, v), fill=(0, 255, 255))
d.text((6, 6), "viewshed from the playable area: bright = often and near seen; red boxes = never seen", fill=(230, 230, 230))
img.save(prefix + "_vis.png")
print("->", prefix + "_vis.png")
