r"""A designed island in TutA's terrain frame, formed by the Advent chat's terrain tool (tools/python/terrain:
sketch -> uplift -> stream power -> droplets -> thermal -> detail) instead of a noise blob:

    py tools/island_form.py <seed> <template island1.bmp> <out.bmp> [preset=hills|alpine] [relief=90] [land=0.40] [png=sketch.png]

The sketch is drawn at random per seed inside the frame: one or two ridges across the interior, a valley
from the border (a bay), peaks on the ridges, a flat pad on the plant's coastal plain (cells 96..106 x
33..46, the binder town's shore), the outlet on the whole border so the ground falls to the sea all round.
The formed heights (metres, 0 = lowest) get a sea level chosen so about `land` of the map is land while the
tower cell (92,57) and the plain stay dry, then map to TutA units: Z = -4967 + (h - sea) * 50, sea floor
at -5500. The cells round the command tower blend into the template's heights (the BSP tower base).
"""
import json, math, os, struct, sys

import numpy as np

CODES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(CODES, "tools", "python", "terrain"))
import terrain_form as tf_  # noqa

seed = int(sys.argv[1])
src, dst = sys.argv[2], sys.argv[3]
o = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)
PRESET = o.get("preset", "hills")
STYLE = o.get("style", "ridges")             # ridges | plateau (the Sana concept: volcano cone, cliff-edged plateau with the plant, long coast road)
                                             # | mix (plateau + Socotra spires + a La Fortaleza mesa + Waimea gorge and layered ledges)
                                             # | cinema (2026-10-08: the island designed from the command room's window and the
                                             #   approved parti - see the CINEMA block)
RELIEF = float(o.get("relief", 90))          # metres, highest point over the lowest formed cell
LAND = float(o.get("land", 0.40))
PNG = o.get("png")
LOC_Z, SCALE_Z, M = -131.845703, 128.0, 50.0
SEA_Z, FLOOR_Z = -4967.0, -5500.0
TOWER = (92, 57)
PLAIN = (96, 106, 33, 46)
N = 128
rng = np.random.default_rng(seed)

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
rows_up = h < 0
T = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if not rows_up:
    T = T[::-1]
TZ = LOC_Z + (T - 32768) * SCALE_Z / 256


def pt(x, y):
    return [round(float(x), 3), round(float(y), 3)]


# --- the sketch: x = i/N (right), y = j/N (row); j is the world-Y index of the heightmap ----------------------
px, py = (PLAIN[0] + PLAIN[1]) / 2 / N, (PLAIN[2] + PLAIN[3]) / 2 / N
tx, ty = TOWER[0] / N, TOWER[1] / N
items = []
cx, cy = rng.uniform(0.42, 0.58), rng.uniform(0.42, 0.58)         # the island's heart
n_ridges = int(rng.integers(1, 3))
for k in range(n_ridges):
    ang = rng.uniform(0, math.pi)
    L = rng.uniform(0.28, 0.42)
    off_ = (rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12)) if k else (0, 0)
    pts = []
    for t in np.linspace(-1, 1, 4):
        wob = rng.uniform(-0.05, 0.05)
        pts.append(pt(cx + off_[0] + t * L * math.cos(ang) - wob * math.sin(ang),
                      cy + off_[1] + t * L * math.sin(ang) + wob * math.cos(ang)))
    items.append({"type": "ridge", "points": pts, "width": float(rng.uniform(0.07, 0.11)), "strength": 1.0 if k == 0 else 0.7})
    items.append({"type": "peak", "at": pts[int(rng.integers(1, 3))], "height": 1.0 if k == 0 else 0.75, "radius": 0.025})
# a bay: a valley from a random border point toward the heart (the river mouth becomes an inlet)
side = rng.integers(4)
bx, by = [(rng.uniform(0.1, 0.9), 0.0), (rng.uniform(0.1, 0.9), 1.0), (0.0, rng.uniform(0.1, 0.9)), (1.0, rng.uniform(0.1, 0.9))][side]
items.append({"type": "valley", "points": [pt(bx, by), pt((bx + cx) / 2 + rng.uniform(-0.05, 0.05), (by + cy) / 2 + rng.uniform(-0.05, 0.05)), pt(cx, cy)],
              "width": 0.05, "depth": 0.85})
# the plant's plain: flat after erosion, and low uplift so it stays a coastal plain
items.append({"type": "basin", "polygon": [pt(px - 0.07, py - 0.07), pt(px + 0.07, py - 0.07), pt(px + 0.07, py + 0.07), pt(px - 0.07, py + 0.07)], "depth": 0.7, "edge": 0.04})
items.append({"type": "pad", "at": pt(px, py), "radius": 0.045})
if STYLE in ("plateau", "mix"):
    # the concept island: one volcanic cone in the heart, a flat-topped plateau on the plant's side ending in
    # cliffs, and a long road from the plant along the shore past the tower and on round the coast
    items = []
    items.append({"type": "peak", "at": pt(cx, cy), "height": 1.0, "radius": 0.07})
    items.append({"type": "ridge", "points": [pt(cx, cy), pt((cx + px) / 2, (cy + py) / 2 + 0.08)], "width": 0.08, "strength": 0.8})
    ang0 = rng.uniform(0, 2 * math.pi)
    poly = [pt(px + 0.17 * math.cos(a) * rng.uniform(0.85, 1.15), py + 0.15 * math.sin(a) * rng.uniform(0.85, 1.15))
            for a in np.linspace(ang0, ang0 + 2 * math.pi, 9)[:-1]]
    items.append({"type": "plateau", "polygon": poly, "strength": 0.22, "edge": 0.03, "resist": 0.6})
    items.append({"type": "pad", "at": pt(px, py), "radius": 0.045})
    # the road: plain -> tower -> on along the coast on the far side of the tower
    ex, ey = tx + (tx - px) * 1.6, ty + (ty - py) * 1.6
    ex, ey = min(max(ex, 0.08), 0.92), min(max(ey, 0.08), 0.92)
    items.append({"type": "road", "points": [pt(px, py), pt((px + tx) / 2 + 0.03, (py + ty) / 2 - 0.03), pt(tx, ty), pt(ex, ey)], "width": 0.012})
    RELIEF = max(RELIEF, 130.0)
MESA = GORGE = None
CINEMA = None
if STYLE == "cinema":
    # ONE generator for land and town (the user, 2026-10-08: "mix terrain generator and town generators into a single
    # generator while minding also cinematography research findings"). The island is sketched FROM the camera
    # (games/reports/Cinematography and concept art for the Avalon town.md) and the parti (binder/parti.json):
    #  * the window looks along yaw 300 (+-34 deg); the hero must land on a vertical third: u = 1/3 or 2/3 is
    #    12.7 deg off the axis -> the works plateau (the town's mass, the hero's stage) sits on that bearing,
    #    20-29 cells (200-300 m) out, LOW (sea + ~12 m): the company's tower keeps the high ground
    #  * three depth layers with air between them (rule 3): the plateau (midground), a sea inlet beyond it (the gap),
    #    a cliffed mesa ridge across the view near the map's edge (the background silhouette against the sky)
    #  * the parti's "the town lives in its smoke": a terraced slope DOWNWIND of the plateau (wind 0.83, -0.55) for
    #    the shanty, its ledges cut into strata (flat plots)
    #  * the hour: the low sun at az 136 is behind the town seen from the window (yaw 300): back light (rule 5)
    #  * behind the tower (out of the frame) the island's volcanic heart, for the silhouette from the sea
    items = []
    side_ = 1 if rng.random() < 0.5 else -1                       # the hero on the left or the right third
    look = math.radians(300.0)
    hero_b = look + side_ * math.radians(12.7 + rng.uniform(-3, 3))
    R1 = rng.uniform(21, 28)                                      # cells to the plateau's centre
    mx_, my_ = tx + R1 / N * math.cos(hero_b), ty + R1 / N * math.sin(hero_b)
    rp = rng.uniform(0.07, 0.09)                                  # plateau radius (of the map)
    ang0 = rng.uniform(0, 2 * math.pi)
    poly = [pt(mx_ + rp * math.cos(a_) * rng.uniform(0.88, 1.12), my_ + rp * 0.85 * math.sin(a_) * rng.uniform(0.88, 1.12))
            for a_ in np.linspace(ang0, ang0 + 2 * math.pi, 10)[:-1]]
    items.append({"type": "plateau", "polygon": poly, "strength": 0.18, "edge": 0.025, "resist": 0.7})
    items.append({"type": "pad", "at": pt(mx_, my_), "radius": 0.05})
    # the tower's high ground: a ridge from the tower down toward the plateau (the spine climbs it)
    items.append({"type": "ridge", "points": [pt(tx, ty), pt((tx + mx_) / 2, (ty + my_) / 2)], "width": 0.06, "strength": 0.55})
    # the shanty's terraced slope, downwind of the works
    wx_, wy_ = 0.83, -0.55
    sx_, sy_ = mx_ + wx_ * rng.uniform(0.09, 0.12), my_ + wy_ * rng.uniform(0.09, 0.12)
    items.append({"type": "ridge", "points": [pt(sx_ - 0.05 * wy_, sy_ + 0.05 * wx_), pt(sx_ + 0.05 * wy_, sy_ - 0.05 * wx_)],
                  "width": 0.07, "strength": 0.45})
    # the gap of air: a sea inlet beyond the plateau along the view, across it
    R2 = R1 + rng.uniform(13, 17)
    ix_, iy_ = tx + R2 / N * math.cos(look + side_ * 0.10), ty + R2 / N * math.sin(look + side_ * 0.10)
    nx_, ny_ = -math.sin(look), math.cos(look)                    # across the view
    w_in = rng.uniform(0.12, 0.17)
    items.append({"type": "basin", "polygon": [pt(ix_ - nx_ * w_in - 0.03 * math.cos(look), iy_ - ny_ * w_in - 0.03 * math.sin(look)),
                                                pt(ix_ + nx_ * w_in - 0.03 * math.cos(look), iy_ + ny_ * w_in - 0.03 * math.sin(look)),
                                                pt(ix_ + nx_ * w_in + 0.04 * math.cos(look), iy_ + ny_ * w_in + 0.04 * math.sin(look)),
                                                pt(ix_ - nx_ * w_in + 0.04 * math.cos(look), iy_ - ny_ * w_in + 0.04 * math.sin(look))],
                  "depth": 0.95, "edge": 0.03})
    # the background: a long cliffed mesa ridge across the view, as far as the map allows (~45-52 cells)
    R3 = min(rng.uniform(45, 52), 0.95 * min((N - 10 - TOWER[0]) / max(1e-3, math.cos(look)), (TOWER[1] - 10) / max(1e-3, -math.sin(look))))
    bx_, by_ = tx + R3 / N * math.cos(look), ty + R3 / N * math.sin(look)
    L3 = rng.uniform(0.16, 0.22)
    items.append({"type": "ridge", "points": [pt(bx_ - nx_ * L3, by_ - ny_ * L3), pt(bx_ + nx_ * L3 * 0.2, by_ + ny_ * L3 * 0.2 + 0.01),
                                               pt(bx_ + nx_ * L3, by_ + ny_ * L3)], "width": 0.05, "strength": 1.0})
    poly = [pt(bx_ + nx_ * L3 * 0.8 * math.cos(a_) + math.cos(look) * 0.035 * math.sin(a_),
               by_ + ny_ * L3 * 0.8 * math.cos(a_) + math.sin(look) * 0.035 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 10)[:-1]]
    items.append({"type": "plateau", "polygon": poly, "strength": 0.55, "edge": 0.012, "resist": 0.9})
    # the heart behind the tower (out of the window): the island's volcanic cone, for its silhouette from the sea
    hx_, hy_ = tx - 0.22 * math.cos(look), ty - 0.22 * math.sin(look)
    items.append({"type": "peak", "at": pt(min(max(hx_, 0.15), 0.85), min(max(hy_, 0.15), 0.85)), "height": 1.0, "radius": 0.08})
    CINEMA = {"plateau": (mx_ * N, my_ * N, rp * N), "shanty": (sx_ * N, sy_ * N), "inlet": (ix_ * N, iy_ * N), "mesa": (bx_ * N, by_ * N),
              "side": side_, "R": (R1, R2, R3)}
    px, py = mx_, my_
    PLAIN = (int(mx_ * N) - 5, int(mx_ * N) + 5, int(my_ * N) - 6, int(my_ * N) + 6)
    RELIEF = max(RELIEF, 120.0)
if STYLE == "mix":
    # the user's pick of the real-place refs (2026-10-07, design-refs/avalon_real_places/desert_islands):
    # Socotra - a cluster of granite spires in the heart instead of one smooth cone
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.015, 0.05)
        items.append({"type": "peak", "at": pt(cx + r * math.cos(a), cy + r * math.sin(a)), "height": float(rng.uniform(0.75, 1.05)),
                      "radius": float(rng.uniform(0.012, 0.022))})
    # La Fortaleza - a cliff-capped mesa standing apart, across the heart from the plant (seen from the tower)
    mx, my = cx + (cx - px) * 0.85, cy + (cy - py) * 0.85
    mx, my = min(max(mx, 0.18), 0.82), min(max(my, 0.18), 0.82)
    MESA = (mx, my, 0.065)
    poly = [pt(mx + 0.065 * math.cos(a) * rng.uniform(0.85, 1.15), my + 0.055 * math.sin(a) * rng.uniform(0.85, 1.15))
            for a in np.linspace(0, 2 * math.pi, 10)[:-1]]
    items.append({"type": "plateau", "polygon": poly, "strength": 0.6, "edge": 0.012, "resist": 0.9})
    # Waimea - a deep narrow gorge from the heart down to the sea, on the side away from the plant
    gx, gy = cx + (cx - px) * 2.0 + rng.uniform(-0.15, 0.15), cy - (cy - py) * 0.5 + rng.uniform(-0.15, 0.15)
    gx, gy = min(max(gx, 0.0), 1.0), min(max(gy, 0.0), 1.0)
    GORGE = [pt(cx, cy), pt((cx + gx) / 2 + rng.uniform(-0.04, 0.04), (cy + gy) / 2 + rng.uniform(-0.04, 0.04)), pt(gx, gy)]
    items.append({"type": "valley", "points": GORGE, "width": 0.022, "depth": 1.0})
# a big bay or sound on one random side: a basin polygon eating into the island (never over the tower/plain quarter)
sides = ["north", "south", "east", "west"]
bay_side = "-"
if STYLE == "cinema":
    pass                                                          # the designed island keeps its own water
else:

  bay_side = sides[int(rng.integers(0, 2))] if rng.random() < 0.5 else "west"     # x<0.6 half: keeps the plant's shore intact
  bx0, bx1 = (0.0, rng.uniform(0.25, 0.45)) if bay_side == "west" else (rng.uniform(0.1, 0.6), rng.uniform(0.7, 0.9))
  by0, by1 = (0.0, rng.uniform(0.25, 0.45)) if bay_side == "north" else ((rng.uniform(0.55, 0.75), 1.0) if bay_side == "south" else (rng.uniform(0.15, 0.4), rng.uniform(0.6, 0.85)))
  items.append({"type": "basin", "polygon": [pt(bx0, by0), pt(bx1, by0 + rng.uniform(-0.05, 0.05)), pt(bx1 + rng.uniform(-0.08, 0.08), by1), pt(bx0, by1)],
              "depth": float(rng.uniform(0.7, 0.95)), "edge": 0.06})
# two more bites at random corners away from the plant's quarter, so no two coasts look alike
for _ in range(0 if STYLE == "cinema" else 2):
    qx, qy = rng.uniform(0.0, 0.55), rng.uniform(0.0, 1.0)
    rr = rng.uniform(0.12, 0.22)
    poly = [pt(qx + rr * math.cos(a) * rng.uniform(0.7, 1.3), qy + rr * math.sin(a) * rng.uniform(0.7, 1.3)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]]
    items.append({"type": "basin", "polygon": poly, "depth": float(rng.uniform(0.6, 0.9)), "edge": 0.05})
outlet = "border"
sketch = {"size": N, "metres_per_cell": 10.24, "relief": RELIEF, "preset": PRESET, "outlet": outlet, "edge_fade": 0.18,
          "base": 0.5, "roughness": 0.25, "items": items}

out = tf_.form(sketch, seed=seed, size=N, log=None)
hm = np.asarray(out["h"], dtype=np.float64)              # metres, [row=j, col=i]
hm = hm - hm.min()
# sea level: `land` of the map dry, but the tower and the plain always dry
from collections import deque


def main_mass(Hm, sea_level):
    land = Hm > sea_level
    seen = np.zeros((N, N), bool)
    dq = deque([TOWER])
    while dq:
        i, j = dq.popleft()
        if not (0 <= i < N and 0 <= j < N) or seen[j, i] or not land[j, i]:
            continue
        seen[j, i] = True
        dq.extend([(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)])
    return seen


J, I = np.mgrid[0:N, 0:N]
sea = float(np.percentile(hm, 100 * (1 - LAND)))
while sea > 3.0 and main_mass(hm, sea + 3.0).mean() < 0.8 * LAND:
    sea -= 1.5                                                   # lower the sea until the tower's landmass carries the island
if STYLE == "cinema":
    # the works' table LOW (sea + 12 m: the company's tower holds the high ground), cliffs round it kept
    dpl = np.hypot(I - CINEMA["plateau"][0], J - CINEMA["plateau"][1])
    r_pl = CINEMA["plateau"][2]
    tcap = np.clip((dpl - r_pl) / (0.06 * N), 0, 1)
    hm = np.minimum(hm, sea + 12.0 + 140.0 * tcap * tcap * (3 - 2 * tcap))
    # the shanty's slope in strata: 6 m ledges (plots for shacks) round its centre
    ds = np.hypot(I - CINEMA["shanty"][0], J - CINEMA["shanty"][1])
    ws = np.clip((14 - ds) / 6, 0, 1) * (hm > sea + 3)
    B_ = 6.0
    base0 = np.floor(hm / B_) * B_
    hm = hm * (1 - ws) + (base0 + B_ * np.clip(((hm - base0) / B_ - 0.75) / 0.25, 0, 1)) * ws
if STYLE in ("plateau", "mix"):
    # the plateau's table sits at the tower's own level (TutA's tower base is ~22 m over the sea): cap the
    # formed heights round the plain, the cap rising smoothly away so the cliffs stay where the sketch put them
    PLAT_H = 26.0
    dpl = np.hypot(I - (PLAIN[0] + PLAIN[1]) / 2, J - (PLAIN[2] + PLAIN[3]) / 2)
    r_pl = 0.16 * N
    tcap = np.clip((dpl - r_pl) / (0.08 * N), 0, 1)
    cap = sea + PLAT_H + 120.0 * tcap * tcap * (3 - 2 * tcap)
    hm = np.minimum(hm, cap)
if STYLE == "mix":
    J, I = np.mgrid[0:N, 0:N]

    def value_noise(cells, amp):
        g = rng.random((cells + 2, cells + 2))
        u = I * cells / N
        v = J * cells / N
        i0, j0 = u.astype(int), v.astype(int)
        fu, fv = u - i0, v - j0
        fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
        return amp * (g[j0, i0] * (1 - fu) * (1 - fv) + g[j0, i0 + 1] * fu * (1 - fv) + g[j0 + 1, i0] * (1 - fu) * fv + g[j0 + 1, i0 + 1] * fu * fv)
    keep = np.clip((np.hypot(I - TOWER[0], J - TOWER[1]) - 10) / 6, 0, 1) * \
        np.clip((np.hypot(I - (PLAIN[0] + PLAIN[1]) / 2, J - (PLAIN[2] + PLAIN[3]) / 2) - 0.17 * N) / 8, 0, 1)
    up = np.clip((hm - sea - 25) / 40, 0, 1)
    # Socotra: jagged high ground (ridged noise: sharp crests, 10 m cells)
    rid = 1 - np.abs(2 * value_noise(24, 1.0) - 1)
    hm = hm + keep * up * (rid ** 3) * 14.0
    # La Fortaleza: the mesa's top cut flat (a table with cliffs all round)
    if MESA:
        mi, mj, mr = MESA[0] * N, MESA[1] * N, MESA[2] * N
        inside = np.hypot(I - mi, J - mj) < mr * 0.8
        top = float(np.percentile(hm[inside], 55)) if inside.any() else hm.max()
        dm = np.hypot(I - mi, J - mj)
        wm = np.clip((mr * 1.05 - dm) / (mr * 0.25), 0, 1)
        hm = np.where(wm > 0, np.minimum(hm, top + (1 - wm) * 200.0), hm)
    # Waimea: steep ground stepped into strata - flat ledges (grass, by the ground paint's slope rule) and
    # short risers, bands of 9 m; the town's plateau and the tower's surroundings are left alone
    gy_, gx_ = np.gradient(hm, 10.24)
    slope = np.hypot(gx_, gy_)
    B = 9.0
    base_ = np.floor(hm / B) * B
    fr = (hm - base_) / B
    stepped = base_ + B * np.clip((fr - 0.7) / 0.3, 0, 1) ** 1.5
    w_ = keep * np.clip((slope - 0.25) / 0.35, 0, 1) * (hm > sea + 4)
    hm = hm * (1 - w_) + stepped * w_
# the plain and the tower must be dry: lift them with smooth bumps rather than lowering the sea
J, I = np.mgrid[0:N, 0:N]
for (ci, cj, need, rad) in ((TOWER[0], TOWER[1], 7.0, 10.0), ((PLAIN[0] + PLAIN[1]) // 2, (PLAIN[2] + PLAIN[3]) // 2, 3.5, 9.0)):
    short = sea + need - hm[cj, ci]
    if short > 0:
        hm = hm + short * np.exp(-((I - ci) ** 2 + (J - cj) ** 2) / (2 * rad * rad))
    near = np.hypot(I - ci, J - cj) <= rad * 0.8
    hm = np.where(near, np.maximum(hm, sea + 1.5), hm)                 # no pits inside the plain or under the tower
Z = np.where(hm >= sea, SEA_Z + 60 + (hm - sea) * M, FLOOR_Z - 40 * np.clip((sea - hm) / 10.0, 0, 1))
# only the landmass with the tower is land: islets go under
land = Z > SEA_Z
seen = main_mass(hm, sea)
Z = np.where(land & ~seen, FLOOR_Z, Z)
# the tower blends into the template (the BSP base), the map edge stays the template's water
dt = np.hypot(I - TOWER[0], J - TOWER[1])
wt = np.clip((9 - dt) / 5.0, 0, 1)
Z = Z * (1 - wt) + TZ * wt
E = np.clip((np.minimum.reduce([I, J, N - 1 - I, N - 1 - J]) - 3) / 6.0, 0, 1)
Z = Z * E + TZ * (1 - E)
Hn = np.clip(np.round(32768 + (Z - LOC_Z) * 256 / SCALE_Z), 0, 65535).astype("<u2")
pix = (Hn if rows_up else Hn[::-1]).tobytes()
open(dst, "wb").write(raw[:off] + pix + raw[off + len(pix):])
if CINEMA:
    json.dump(CINEMA, open(os.path.splitext(dst)[0] + "_cinema.json", "w"), indent=1)
print(f"seed {seed} [{PRESET} {STYLE}]: {n_ridges} ridge(s), inlet from side {side}, bay {bay_side}, sea at {sea:.1f} m of {hm.max():.0f}, land {(Z > SEA_Z).mean():.0%}, "
      f"peak Z {Z.max():.0f}, plain Z {Z[(PLAIN[2] + PLAIN[3]) // 2, (PLAIN[0] + PLAIN[1]) // 2]:.0f} -> {dst}")
if PNG:
    import json
    json.dump(sketch, open(os.path.splitext(PNG)[0] + ".json", "w"), indent=1)
    from PIL import Image, ImageDraw
    S = 4
    t = np.clip((Z - SEA_Z) / (RELIEF * M), 0, 1)
    rgb = np.zeros((N, N, 3), "u1")
    sea_m = Z <= SEA_Z
    rgb[..., 0] = np.where(sea_m, 30, 80 + 150 * t)
    rgb[..., 1] = np.where(sea_m, 60, 120 + 100 * t)
    rgb[..., 2] = np.where(sea_m, 140, 60 + 150 * t)
    img = Image.fromarray(rgb[::-1]).resize((N * S, N * S), Image.NEAREST)
    dr = ImageDraw.Draw(img)
    for it in items:
        if it["type"] in ("ridge", "valley"):
            dr.line([(x * N * S, (1 - y) * N * S) for x, y in it["points"]], fill=(255, 255, 255) if it["type"] == "ridge" else (0, 200, 255), width=2)
    dr.ellipse([tx * N * S - 4, (1 - ty) * N * S - 4, tx * N * S + 4, (1 - ty) * N * S + 4], fill=(255, 0, 0))
    dr.ellipse([px * N * S - 4, (1 - py) * N * S - 4, px * N * S + 4, (1 - py) * N * S + 4], fill=(255, 255, 0))
    img.save(PNG)
