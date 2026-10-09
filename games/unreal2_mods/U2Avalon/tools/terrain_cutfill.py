"""Cut-and-fill TutA's terrain heightmap under the binder's buildings (the real-world way to build on a
slope: a level plinth cut into the bank, the spoil filling the low side, a benched blend back to the hill).

    py tools/terrain_cutfill.py <island1.bmp exported by UnrealEd> <out.bmp> [shift=-5300] [margin=256] [blend=400]
                                [layout=<isl_layout.json>] [max_step=400] [arenas=1]

The BMP is the 16-bit (G16) heightmap UnrealEd exports with OBJ EXPORT TYPE=Texture; the same bytes go
back with TEXTURE IMPORT. TutA's TerrainInfo0 (read in game with 'hub list TerrainInfo'):
    location (-14487.5, 4835.8, -131.8), scale (512, 512, 128), heightmap 128x128
UE2 maps pixel (i, j) -> world (Location.X + (i - 64) * 512, Location.Y + (j - 64) * 512) and a height
value h -> Z = Location.Z + (h - 32768) * ScaleZ / 256.

Round 4 (marks M1, 2026-10-09). The order is: the arenas' floors, the roads, the building pads, the dock cutting,
then every footprint forced level once more. A pad is the building's FOOTPRINT - the sheet's w x d rectangle turned
by the layout yaw, one per instance of a `count:` group, plus `margin` (half a cell) - flat at ONE level per
building, blended back over `blend` outside it. The level is the mean of the road-graded ground under the
footprint, so a plot sits at its street; where a footprint and a road share a cell the footprint wins (the kerb /
retaining wall clutter.py draws at every rim over 2.6 m). Neighbours whose pads touch and whose levels are within
`max_step` (4 m) share a terrace (the area-weighted mean; a terrace's members never span more than `max_span`, 6 m);
further apart they keep their own level and the step between them is a wall. Nothing else is terraced: the old version gave every sheet with an `at:` a disc of
0.6 x size + 600 UU (far_islands, an islet, got a 42600 UU disc that forced most of Town7's island to one level,
26 m under the director's house), merged overlapping discs into terraces up to 64 m across whatever their
heights, and let the roads re-grade the pads afterwards.
Skipped: kinds rig, barge, wreck, islet and culvert (at sea, underground), the stock `tower`, and - with layout= -
every sheet the layout did not place (its `at:` is a placeholder). The hero (the parti's tower) gets the same
footprint pad as everything else: a flat plinth terrace at its mean ground.
arenas=1 (default): the greybox arenas E1-E4 (anchors.arenas on the natural ground) get a level floor at their
stop's ground first, at the lowest priority (roads and pads override), land cells only.
"""
import math, os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa
import anchors  # noqa  (footprints: the same rectangles codirect's M1 reads; arenas)

src, dst = sys.argv[1], sys.argv[2]
o = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)   # shift= margin= blend= max_step= layout= arenas=
SHIFT = float(o.get("shift", -5300))
MARGIN = float(o.get("margin", 256))      # half a cell round the footprint: the check disc (codirect M1) + the mesh's eaves
BLEND = float(o.get("blend", 400))        # shorter blend = real terraces (walls at the rims); 700 made soft mounds
MAX_STEP = float(o.get("max_step", 400))  # height units (100 = 1 m): touching pads closer than this share one terrace
MAX_SPAN = float(o.get("max_span", 1.5 * MAX_STEP))   # ... and a terrace's members' own levels never span more than this
QUAY_M = float(o.get("quay_m", 2.0))      # a pad never sits lower than this over the sea (the quay deck: E23 wants 1.5-4 m)
LOOK, M = 300.0, 50.0
LOC = (-14487.546875, 4835.837891, -131.845703)
SCALE = (512.0, 512.0, 128.0)
SEA_H = 32768 + (-4967 - LOC[2]) * 256 / SCALE[2]      # the sea surface as a height value
HPM = 256 / SCALE[2] * M                              # height units per metre (100)
SKIP_KINDS = ("rig", "barge", "wreck", "islet", "culvert")


def from_frame(along, across):
    a = math.radians(LOOK)
    return (along * math.cos(a) - across * math.sin(a), along * math.sin(a) + across * math.cos(a))


LAYOUT = None
LAY = None
if o.get("layout"):
    import json as _json
    LAY = _json.load(open(o["layout"]))
    LAYOUT = LAY["buildings"]


def instances(b):
    """[(x, y, yaw)] world, one per instance of the sheet's `count:` (the group's offsets turned with the yaw)"""
    along, across, deg = b["at"]
    if LAYOUT and b["id"] in LAYOUT:
        L = LAYOUT[b["id"]]
        along, across, deg = None, None, L["yaw"]
    w, d = b["size"][0] * M, b["size"][1] * M
    gap = max(w, d) * 1.5
    spec = b.get("count", "1").split()
    pts = [(0, 0)]
    if "x" in spec[0].lower():                  # "3x4": a block (2x2 as before)
        na_, nc_ = (int(v) for v in spec[0].lower().split("x"))
        pts = [((ka_ - (na_ - 1) / 2) * gap, (kc_ - (nc_ - 1) / 2) * gap) for kc_ in range(nc_) for ka_ in range(na_)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    if along is None:
        a = math.radians(deg)
        return [(L["x"] + da * math.cos(a) - dc * math.sin(a), L["y"] + da * math.sin(a) + dc * math.cos(a), deg) for da, dc in pts]
    return [from_frame(along + SHIFT + da, across + dc) + (deg + LOOK,) for da, dc in pts]


raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
bpp = struct.unpack_from("<H", raw, 28)[0]
assert bpp == 16 and w == 128, (bpp, w, h)
rows_up = h < 0            # positive height = bottom-up rows in the file
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if not rows_up:
    H = H[::-1]
ORIG = H.copy()
NR = abs(h)

ix = (np.arange(w) - w / 2) * SCALE[0] + LOC[0]      # world X of each column
jy = (np.arange(NR) - NR / 2) * SCALE[1] + LOC[1]
X, Y = np.meshgrid(ix, jy)


def sample(G, x, y):
    """bilinear height at a world point on the grid G"""
    fi = (x - LOC[0]) / SCALE[0] + w / 2
    fj = (y - LOC[1]) / SCALE[1] + NR / 2
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < w - 1 and 0 <= j0 < NR - 1):
        return None
    ti, tj = fi - i0, fj - j0
    return (G[j0, i0] * (1 - ti) * (1 - tj) + G[j0, i0 + 1] * ti * (1 - tj)
            + G[j0 + 1, i0] * (1 - ti) * tj + G[j0 + 1, i0 + 1] * ti * tj)


def rect_dist(cx, cy, yaw, hw, hd):
    """distance (UU) of every cell centre outside the rectangle (hw, hd half sizes along / across the yaw); <= 0 inside"""
    a = math.radians(yaw)
    dx, dy = X - cx, Y - cy
    lx = dx * math.cos(a) + dy * math.sin(a)
    ly = -dx * math.sin(a) + dy * math.cos(a)
    ox, oy = np.abs(lx) - hw, np.abs(ly) - hd
    return np.where((ox <= 0) & (oy <= 0), np.maximum(ox, oy), np.hypot(np.maximum(ox, 0), np.maximum(oy, 0)))


def to_z(hv):
    return LOC[2] + (hv - 32768) * SCALE[2] / 256


citizens, buildings = binder.load()

# 0. the arenas' floors (anchors.arenas on the natural ground): the lowest priority, land only
n_arena = 0
if LAY and o.get("arenas", "1") != "0":
    try:
        Zw = to_z(ORIG)
        AR = anchors.arenas(Zw, LAY, buildings)
        for aid, ar in AR.items():
            if not ar.get("placed"):
                continue
            ox, oy = ar["origin"]
            W_, D_ = ar["size"]
            a = math.radians(ar["yaw"])
            dx, dy = X - ox, Y - oy
            lx = dx * math.cos(a) + dy * math.sin(a)
            ly = -dx * math.sin(a) + dy * math.cos(a)
            inside = (lx >= 0) & (lx <= W_) & (ly >= 0) & (ly <= D_) & (ORIG > SEA_H)
            if inside.any():
                hv = 32768 + (ar["z"] - LOC[2]) * 256 / SCALE[2]
                H[inside] = hv
                n_arena += 1
                print(f"  arena {aid} floor at z {ar['z']:.0f} ({int(inside.sum())} cells, was {ar['ground_range_m']:.1f} m of range)")
    except Exception as e:                      # the arenas never break the grading
        print("  arenas skipped:", e)

# 1. roads: graded into the ground FIRST (the pads then sit at their street). Each road polyline is sampled every half
# cell; the ground along it is replaced by a smoothed profile (moving average over ~7 samples, grade capped at
# MAX_GRADE) and the cells within ROAD_W/2 of the line take that height, blended over one cell beyond, so a road
# reads as a cut bench on a slope and a causeway over a dip instead of a line painted on bumps.
ROAD_W = float(o.get("road_w", 1.3))        # cells
MAX_GRADE = float(o.get("max_grade", 0.12))  # rise/run
if LAY:
    road_cut = 0.0
    _RW = LAY.get("road_w") or []                # per-road widths in cells (lanes narrower; Q35 pass 4)
    for _ri, r in enumerate(LAY.get("roads", [])):
        rw = _RW[_ri] if _ri < len(_RW) else ROAD_W
        pts = []
        for (ax, ay), (bx, by) in zip(r[:-1], r[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) / (SCALE[0] * 0.5)))
            for k in range(n):
                t = k / n
                pts.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        pts.append(tuple(r[-1]))
        if len(pts) < 3:
            continue
        hs = []
        for x, y in pts:
            fi, fj = (x - LOC[0]) / SCALE[0] + w / 2, (y - LOC[1]) / SCALE[1] + NR / 2
            i0, j0 = min(w - 2, max(0, int(fi))), min(NR - 2, max(0, int(fj)))
            hs.append(H[j0, i0])
        hs = np.array(hs, float)
        k = 7
        sm = np.convolve(np.pad(hs, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        step_max = MAX_GRADE * SCALE[0] * 0.5 * 256 / SCALE[2]
        for a in range(1, len(sm)):
            sm[a] = min(max(sm[a], sm[a - 1] - step_max), sm[a - 1] + step_max)
        for a in range(len(sm) - 2, -1, -1):
            sm[a] = min(max(sm[a], sm[a + 1] - step_max), sm[a + 1] + step_max)
        D = np.full(H.shape, np.inf)
        T = np.zeros(H.shape)
        for (x, y), hv in zip(pts, sm):
            d = np.hypot(X - x, Y - y) / SCALE[0]
            better = d < D
            D[better] = d[better]
            T[better] = hv
        wgt = np.clip(1 - (D - rw / 2) / 1.0, 0, 1)
        wgt = wgt * wgt * (3 - 2 * wgt)
        newH = H * (1 - wgt) + T * wgt
        road_cut += float(np.abs(newH - H).sum()) * SCALE[2] / 256 * SCALE[0] * SCALE[1]
        H = newH
    print(f"roads graded: {len(LAY.get('roads', []))} legs, earth moved {road_cut / 1e9:.2f} (1e9 units^3)")
ROADED = H.copy()

# 2. the pads: one footprint rectangle per instance, one level per building
pads = []      # {bid, rects: [(cx, cy, yaw, hw, hd)], hc, S: distance field}
hero = None
try:
    import json as _json2
    hero = _json2.load(open(os.path.join(HERE, "binder", "parti.json"))).get("hero")
except (OSError, ValueError):
    pass
for bid, b in buildings.items():
    if "at" not in b or b["kind"] in SKIP_KINDS or bid == "tower":
        continue
    if LAYOUT is not None and bid not in LAYOUT:
        continue                              # not placed: the sheet's `at:` is a placeholder, no pad
    hw, hd = b["size"][0] * M / 2, b["size"][1] * M / 2
    if LAYOUT is not None:
        rects = anchors.footprints(LAYOUT[bid], b)     # the same rectangles codirect's M1 reads
    else:
        rects = [(x, y, yaw, hw, hd) for x, y, yaw in instances(b)]
    S = np.minimum.reduce([rect_dist(*rc) - MARGIN for rc in rects])
    inside = S <= 0
    hs = [sample(ROADED, rc[0], rc[1]) for rc in rects]
    hs = [v for v in hs if v is not None]
    if inside.any():
        hc = float(ROADED[inside].mean())
    elif hs:
        hc = sum(hs) / len(hs)
    else:
        continue
    hc = max(hc, SEA_H + QUAY_M * HPM)        # never below the quay level over the sea
    pads.append({"bid": bid, "rects": rects, "hc": hc, "S": S, "n": int(inside.sum()), "hero": bid == hero})
# touching pads within MAX_STEP share one terrace (the area-weighted mean level); further apart they keep their own
# level and the step between them is a retaining wall
parent = list(range(len(pads)))
span = {i: (p["hc"], p["hc"]) for i, p in enumerate(pads)}     # a group's lowest / highest original level


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


pairs = sorted((abs(pads[i]["hc"] - pads[j]["hc"]), i, j) for i in range(len(pads)) for j in range(i + 1, len(pads))
               if abs(pads[i]["hc"] - pads[j]["hc"]) <= MAX_STEP and ((pads[i]["S"] <= 0) & (pads[j]["S"] <= 0)).any())
for _, i, j in pairs:                       # the closest levels first; a chain never drifts past MAX_STEP
    a, b_ = find(i), find(j)
    if a == b_:
        continue
    lo, hi = min(span[a][0], span[b_][0]), max(span[a][1], span[b_][1])
    if hi - lo <= MAX_SPAN:
        parent[a] = b_
        span[b_] = (lo, hi)
groups = {}
for i, p in enumerate(pads):
    groups.setdefault(find(i), []).append(i)
for g in groups.values():
    if len(g) > 1:
        wsum = sum(max(1, pads[i]["n"]) for i in g)
        lvl = sum(pads[i]["hc"] * max(1, pads[i]["n"]) for i in g) / wsum
        for i in g:
            pads[i]["hc"] = lvl
            pads[i]["terrace"] = "+".join(pads[k]["bid"] for k in g)
# apply: every cell belongs to its NEAREST pad (distance outside the footprint), flat inside it, blended (smoothstep)
# over BLEND outside it; neighbouring pads meet at a seam instead of cutting each other
cut = fill = 0.0
INSIDE = np.zeros(H.shape, bool)
LEVEL = np.zeros(H.shape)
if pads:
    S = np.full(H.shape, np.inf)
    T = np.zeros(H.shape)
    for p in pads:
        better = p["S"] < S
        S[better] = p["S"][better]
        T[better] = p["hc"]
    INSIDE = S <= 0
    LEVEL = T
    t = np.clip(S / BLEND, 0, 1)
    wgt = 1 - (t * t * (3 - 2 * t))               # 1 inside the pad, 0 beyond the blend
    new = H * (1 - wgt) + T * wgt
    dz = (new - H) * SCALE[2] / 256
    cut = float(-dz[dz < 0].sum()) * SCALE[0] * SCALE[1]
    fill = float(dz[dz > 0].sum()) * SCALE[0] * SCALE[1]
    H = new

# 3. the dock cutting (the approved parti's beat 1, "dock: dread - compression, tower hidden"; 2026-10-08): the tower
# stands on the high ground, ~35 m over the quay, so no building near the dock can hide it - the arrival climbs
# between raised, battered banks instead (retaining walls follow from clutter's rim walls), walling the tower off
# until the road leaves the cutting. dock_cut=<metres> (0 = none), over the spine's first dock_cut_len metres.
if LAY:
    import json as _j
    try:
        _P = _j.load(open(os.path.join(HERE, "binder", "parti.json")))
    except (OSError, ValueError):
        _P = {}
    _want = any(b.get("at") == "dock" and "hidden" in b.get("move", "") for b in _P.get("beats", []))
    CUT_M = float(o.get("dock_cut", 9.0 if _want else 0.0))
    CUT_LEN = float(o.get("dock_cut_len", 160.0))
    if CUT_M > 0 and LAY.get("roads"):
        sp = LAY["roads"][0]
        s_acc, pts_s = 0.0, []
        for (ax, ay), (bx, by) in zip(sp[:-1], sp[1:]):
            seg = math.hypot(bx - ax, by - ay)
            n = max(1, int(seg / (SCALE[0] * 0.25)))
            for k in range(n):
                t = k / n
                pts_s.append((ax + (bx - ax) * t, ay + (by - ay) * t, s_acc + seg * t))
            s_acc += seg
            if s_acc > CUT_LEN * 50:
                break
        Dc = np.full(H.shape, np.inf)
        Sc = np.zeros(H.shape)
        for x, y, sv in pts_s:
            d = np.hypot(X - x, Y - y) / SCALE[0]
            better = d < Dc
            Dc[better] = d[better]
            Sc[better] = sv / 50.0
        rw0 = (LAY.get("road_w") or [ROAD_W])[0]
        # lateral: flat road, then a bank rising over 0.6 cell (battered), its crest 1.6 cells wide, falling over 1 cell
        lat = np.clip((Dc - rw0 / 2 - 0.3) / 0.6, 0, 1) * np.clip((rw0 / 2 + 3.5 - Dc) / 1.0, 0, 1)
        along = np.clip((Sc - 15) / 25, 0, 1) * np.clip((CUT_LEN - Sc) / 40, 0, 1)
        # the pads' own cells (+1): the banks never bury a building
        pad_mask = INSIDE.copy()
        pad_mask[1:, :] |= INSIDE[:-1, :]
        pad_mask[:-1, :] |= INSIDE[1:, :]
        pad_mask[:, 1:] |= INSIDE[:, :-1]
        pad_mask[:, :-1] |= INSIDE[:, 1:]
        for bid_, bb in LAY.get("buildings", {}).items():
            for ci, cj in bb.get("cells", []):
                pad_mask[max(0, cj - 1):cj + 2, max(0, ci - 1):ci + 2] = True
        land = ORIG > SEA_H                       # banks on land only (never out of the sea)
        rise = CUT_M * 50 / (SCALE[2] / 256) * lat * along * (~pad_mask) * land
        rise = np.where(Dc < 6, rise, 0)
        if o.get("debug_cut"):
            band = (lat > 0) & (along > 0)
            print("  cutting debug: band %d, off pads %d, on land %d" % (band.sum(), (band & ~pad_mask).sum(), (band & ~pad_mask & land).sum()))
        H = np.maximum(H, H + rise)
        print(f"dock cutting: banks {CUT_M:.0f} m over the spine's first {CUT_LEN:.0f} m ({int((rise > 0).sum())} cells raised)")

# 4. every footprint level once more, whatever came after the pads
if pads:
    H[INSIDE] = LEVEL[INSIDE]
H = np.clip(np.round(H), 0, 65535).astype("<u2")
pix = (H if rows_up else H[::-1]).tobytes()
open(dst, "wb").write(raw[:off] + pix + raw[off + len(pix):])
changed = int((H.astype(float) != ORIG).sum())
print(f"{len(pads)} pads ({len(groups)} terraces), {n_arena} arena floors, {changed} of {w * NR} heightmap cells changed, "
      f"cut {cut / 1e9:.2f} fill {fill / 1e9:.2f} (1e9 units^3) -> {dst}")
# the self-check (codirect's M1): the graded ground's range over each footprint + half a cell
HF = H.astype(float)
bad = []
for p in pads:
    chk = np.minimum.reduce([rect_dist(*rc) - SCALE[0] * 0.5 for rc in p["rects"]]) <= 0
    if chk.any():
        rng = (HF[chk].max() - HF[chk].min()) / HPM
        if rng > 2.0:
            bad.append("%s %.1f m" % (p["bid"], rng))
    x, y = p["rects"][0][0], p["rects"][0][1]
    print(f"  {p['bid']:16s} at ({x:7.0f},{y:7.0f}) {len(p['rects'])} x {2 * p['rects'][0][3] / M:.0f}x{2 * p['rects'][0][4] / M:.0f} m "
          f"pad Z {to_z(p['hc']):7.0f} ({(p['hc'] - sample(ORIG, x, y)) / HPM if sample(ORIG, x, y) is not None else 0:+5.1f} m vs natural)"
          + (f"  terrace {p['terrace']}" if p.get("terrace") else ""))
print("  footprints over 2 m of ground range: " + (", ".join(bad) if bad else "none"))
