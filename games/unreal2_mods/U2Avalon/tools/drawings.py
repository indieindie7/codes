r"""The architect's two thinking drawings for a town run (Q36 lesson 5, 2026-10-08; games/research_notes/How
architects and designers design): a figure-ground plan and cut sections, at true scale, the same every run so runs
compare.

    py tools/drawings.py <final heightmap.bmp> <layout.json> <out prefix> [margin=60]

Writes:
  <prefix>_figureground.png  1 px = 1 m, north up: built mass black, everything else white; the coast a thin grey
                             line, roads/lanes/paths a pale grey hairline (orientation only); scale bar + north
  <prefix>_nolli.png         the Nolli variant: public interiors (social, clinic, store, altar, office) left white
                             inside a grey outline - the town's shared rooms read as part of its open space
  <prefix>_sections.png      three cuts, true scale (no vertical exaggeration), 1 px = 1 m:
                               A  the parti axis: from the sea off the dock, through the dock and the town, to the
                                  tower and 150 m past it
                               B  across the spine at its busiest junction (space syntax: edge betweenness), 400 m
                               C  the command room's view: from the tower along the window (yaw 300), 700 m
                             terrain cut solid, sea level, buildings cut by the line solid (to their pad height +
                             binder height), buildings within 40 m behind the line drawn as pale elevations, and a
                             1.8 m figure at the start with 25 m and 100 m marks (Gehl: faces / figures)
"""
import json, math, os, struct, sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

src, layout_path, prefix = sys.argv[1:4]
o = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)
MARGIN = float(o.get("margin", 60))
LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, M, SEA_Z = 512.0, 50.0, -4967.0
PUBLIC = ("social", "clinic", "store", "altar")
WINDOW_YAW = 300.0

raw = open(src, "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
Hm = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
if h > 0:
    Hm = Hm[::-1]
Z = LOC[2] + (Hm - 32768) * 0.5
N = Hm.shape[0]


def ground(x, y):
    fi, fj = (x - LOC[0]) / CELL + N / 2 - 0.5, (y - LOC[1]) / CELL + N / 2 - 0.5
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < N - 1 and 0 <= j0 < N - 1):
        return SEA_Z - 200
    tx, ty = fi - i0, fj - j0
    return (Z[j0, i0] * (1 - tx) * (1 - ty) + Z[j0, i0 + 1] * tx * (1 - ty) + Z[j0 + 1, i0] * (1 - tx) * ty
            + Z[j0 + 1, i0 + 1] * tx * ty)


L = json.load(open(layout_path))
B = L["buildings"]
_, sheets = binder.load()


def footprints():
    """every building instance as (bid, polygon [(x, y)] in world units, ground z, height m, public?)"""
    out = []
    for bid, P in B.items():
        b = sheets.get(bid)
        if b is None or "size" not in b:
            continue
        W, D = b["size"][0] * M, b["size"][1] * M        # local X (the front axis) spans D, local Y spans W
        Hm_ = b["size"][2] if len(b["size"]) > 2 else 6.0
        gap = max(W, D) * 1.5
        spec = b.get("count", "1").split()
        pts = [(0, 0)]
        if "x" in spec[0].lower():
            na_, nc_ = (int(v) for v in spec[0].lower().split("x"))
            pts = [((ka - (na_ - 1) / 2) * gap, (kc - (nc_ - 1) / 2) * gap) for kc in range(nc_) for ka in range(na_)]
        elif len(spec) == 2:
            n = int(spec[0])
            pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
        a = math.radians(P["yaw"])
        ca, sa = math.cos(a), math.sin(a)
        pub = b.get("function") in PUBLIC or b["kind"] == "office"
        for da, dc in pts:
            cx, cy = P["x"] + da * ca - dc * sa, P["y"] + da * sa + dc * ca
            poly = [(cx + lx * ca - ly * sa, cy + lx * sa + ly * ca) for lx, ly in
                    ((D / 2, W / 2), (D / 2, -W / 2), (-D / 2, -W / 2), (-D / 2, W / 2))]
            out.append((bid, poly, P.get("z", ground(cx, cy)), Hm_, pub, b["kind"]))
    return out


FP = footprints()
# the plan's extent: plots, buildings and roads near the town (not the far rigs and islets)
town = [(p["x"], p["y"]) for bid, p in B.items() if sheets.get(bid, {}).get("kind") not in ("rig", "islet", "wreck", "barge")]
xs, ys = [p[0] for p in town], [p[1] for p in town]
X0, X1 = min(xs) - MARGIN * M, max(xs) + MARGIN * M
Y0, Y1 = min(ys) - MARGIN * M, max(ys) + MARGIN * M
PW, PH = int((X1 - X0) / M), int((Y1 - Y0) / M)


def P(x, y):                                         # world -> plan pixel (1 px = 1 m, north = +Y up)
    return ((x - X0) / M, (Y1 - y) / M)


def scale_and_north(dr, wpx, hpx, ink=(0, 0, 0)):
    x0, y0 = 20, hpx - 30
    dr.rectangle([x0, y0, x0 + 100, y0 + 6], outline=ink)
    dr.rectangle([x0, y0, x0 + 50, y0 + 6], fill=ink)
    dr.text((x0, y0 - 14), "0      50     100 m", fill=ink)
    nx, ny = wpx - 30, 40
    dr.polygon([(nx, ny - 22), (nx - 8, ny), (nx + 8, ny)], fill=ink)
    dr.text((nx - 4, ny + 4), "N", fill=ink)


def plan(nolli):
    img = Image.new("RGB", (PW, PH), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    # the coast: a thin grey contour at sea level (marching on the coarse grid is enough at this scale)
    for j in range(N - 1):
        for i in range(N - 1):
            a, b_ = Z[j, i] > SEA_Z, Z[j, i + 1] > SEA_Z
            c = Z[j + 1, i] > SEA_Z
            wx, wy = LOC[0] + (i + 0.5 - N / 2) * CELL, LOC[1] + (j + 0.5 - N / 2) * CELL
            if a != b_:
                dr.line([P(wx + CELL / 2, wy - CELL / 2), P(wx + CELL / 2, wy + CELL / 2)], fill=(150, 150, 150))
            if a != c:
                dr.line([P(wx - CELL / 2, wy + CELL / 2), P(wx + CELL / 2, wy + CELL / 2)], fill=(150, 150, 150))
    for r in L.get("roads", []):
        dr.line([P(*p) for p in r], fill=(215, 215, 215), width=1)
    for bid, poly, z, hm, pub, kind in FP:
        if kind in ("pad", "dock", "jetty", "islet", "rig", "barge", "wreck"):
            dr.polygon([P(*p) for p in poly], outline=(120, 120, 120))       # ground works, not mass
            continue
        if nolli and pub:
            dr.polygon([P(*p) for p in poly], fill=(255, 255, 255), outline=(110, 110, 110))
        else:
            dr.polygon([P(*p) for p in poly], fill=(0, 0, 0))
    scale_and_north(dr, PW, PH)
    dr.text((20, 12), ("Nolli plan" if nolli else "figure-ground") + "  -  1 px = 1 m", fill=(0, 0, 0))
    return img


plan(False).save(prefix + "_figureground.png")
plan(True).save(prefix + "_nolli.png")


# ---- sections -------------------------------------------------------------------------------------------------
def inside(poly, x, y):
    c = False
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def busiest_junction():
    try:
        import metrics
        pos, edges, adj = metrics.road_graph(L)
        eb = metrics.edge_betweenness(adj, list(adj.keys()))
        load = {n: sum(eb.get((min(n, m), max(n, m)), 0.0) for m in adj[n]) for n in adj if len(adj[n]) >= 3}
        if load:
            n = max(load, key=load.get)
            return pos[n]
    except Exception as e:
        print("  (busiest junction: %s)" % e)
    sp = L["spine"]
    return tuple(sp[len(sp) // 2])


def spine_dir_at(p):
    sp = L["spine"]
    k = min(range(len(sp) - 1), key=lambda k: math.dist(sp[k], p))
    dx, dy = sp[k + 1][0] - sp[k][0], sp[k + 1][1] - sp[k][1]
    d = math.hypot(dx, dy) or 1
    return dx / d, dy / d


sites = L.get("sites", {})
dock = tuple(sites.get("dock", L["spine"][0]))
tower = tuple(sites.get("tower", (B["tower"]["x"], B["tower"]["y"]) if "tower" in B else L["spine"][-1]))
ax_, ay_ = tower[0] - dock[0], tower[1] - dock[1]
al = math.hypot(ax_, ay_) or 1
ux, uy = ax_ / al, ay_ / al
CUTS = [("A  the parti axis: sea - dock - town - tower", (dock[0] - ux * 80 * M, dock[1] - uy * 80 * M), (tower[0] + ux * 150 * M, tower[1] + uy * 150 * M))]
jx, jy = busiest_junction()
sx, sy = spine_dir_at((jx, jy))
CUTS.append(("B  across the spine at the busiest junction", (jx + sy * 200 * M, jy - sx * 200 * M), (jx - sy * 200 * M, jy + sx * 200 * M)))
wa = math.radians(WINDOW_YAW)
CUTS.append(("C  the command room's view (yaw 300)", tower, (tower[0] + math.cos(wa) * 700 * M, tower[1] + math.sin(wa) * 700 * M)))


def section(title, a, b):
    Lm = int(math.dist(a, b) / M)
    xs_ = np.arange(Lm + 1)
    dx, dy = (b[0] - a[0]) / max(Lm, 1), (b[1] - a[1]) / max(Lm, 1)
    zs = np.array([ground(a[0] + dx * t, a[1] + dy * t) for t in xs_]) / M          # metres
    cut, beyond = [], []
    nx, ny = -dy / M, dx / M                                                          # unit normal (world units / m)
    for bid, poly, z, hm, pub, kind in FP:
        hits = [t for t in xs_[::2] if inside(poly, a[0] + dx * t, a[1] + dy * t)]
        if hits:
            cut.append((min(hits), max(hits) + 2, z / M, hm, kind))
            continue
        cx = sum(p[0] for p in poly) / 4
        cy = sum(p[1] for p in poly) / 4
        rel = ((cx - a[0]) * dx + (cy - a[1]) * dy) / (M * M)                          # along the cut (m)
        off_ = ((cx - a[0]) * nx + (cy - a[1]) * ny) / M                               # metres to the left
        if 0 <= rel <= Lm and 0 < off_ < 40:                                         # just behind the cut plane
            half = max(math.dist(poly[0], poly[1]), math.dist(poly[1], poly[2])) / M / 2
            beyond.append((rel - half, rel + half, z / M, hm))
    zmin = min(zs.min(), SEA_Z / M) - 10
    zmax = max([zs.max()] + [c[2] + c[3] for c in cut] + [e[2] + e[3] for e in beyond]) + 15
    Hpx = int(zmax - zmin) + 40
    img = Image.new("RGB", (Lm + 80, Hpx), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    def S(t, zm):
        return (40 + t, Hpx - 20 - (zm - zmin))

    # sea level, then elevations beyond (pale), terrain cut (solid), buildings cut (black)
    dr.line([S(0, SEA_Z / M), S(Lm, SEA_Z / M)], fill=(120, 160, 220), width=1)
    for t0, t1, zb, hm in beyond:
        dr.rectangle([S(max(t0, 0), zb + hm), S(min(t1, Lm), zb)], outline=(170, 170, 170), fill=(232, 232, 232))
    dr.polygon([S(0, zmin)] + [S(t, z) for t, z in zip(xs_, zs)] + [S(Lm, zmin)], fill=(70, 70, 70))
    for t0, t1, zb, hm, kind in cut:
        dr.rectangle([S(t0, zb + hm), S(t1, zb)], fill=(0, 0, 0))
    # a 1.8 m figure at the start, Gehl marks at 25 m and 100 m
    z0 = zs[0] if zs[0] > SEA_Z / M else SEA_Z / M
    fx, fy = S(2, z0)
    dr.line([(fx, fy), (fx, fy - 1.8)], fill=(200, 40, 40), width=2)
    dr.ellipse([fx - 1, fy - 2.6, fx + 1, fy - 1.6], fill=(200, 40, 40))
    for mark in (25, 100):
        if mark <= Lm:
            mx, my = S(mark, zs[min(mark, Lm)])
            dr.line([(mx, my - 6), (mx, my - 18)], fill=(200, 40, 40))
            dr.text((mx + 2, my - 30), "%d m" % mark, fill=(200, 40, 40))
    dr.text((40, 6), "%s   (%d m, true scale, 1 px = 1 m)" % (title, Lm), fill=(0, 0, 0))
    return img


secs = [section(*c) for c in CUTS]
Wt = max(s.size[0] for s in secs)
sheet = Image.new("RGB", (Wt, sum(s.size[1] for s in secs) + 10 * len(secs)), (255, 255, 255))
yy = 0
for s_ in secs:
    sheet.paste(s_, (0, yy))
    yy += s_.size[1] + 10
sheet.save(prefix + "_sections.png")
print("drawings: figure-ground %dx%d m, Nolli, sections %s -> %s_*.png" % (PW, PH, ", ".join("%s %d m" % (c[0][0], math.dist(c[1], c[2]) / M) for c in CUTS), prefix))
