r"""Architectural drawings of the Liandri buildings, cut from the meshes the game uses (2026-10-08; the user: "now
regenerate some architectural plans for some buildings"). One sheet per building, orthographic, true scale:

    py tools/building_plans.py [out_dir] [names=CraneTower,FactoryHall,...] [cut=1.5]

  PLAN        a horizontal cut at cut= metres over the base (thick black: what the plane cuts), and in thin grey what
              lies below the cut seen from above
  ROOF PLAN   the top view, shaded by height
  ELEVATIONS  front (looking at the +X face, the side that faces the road) and side (the +Y face), flat-shaded by the
              low sun and tinted by each face's palette colour (Models/round2_ase/Pal2.tga)
  SECTION     a vertical cut through the middle, across the front (thick black), the far half drawn pale beyond it
Every view has a 1.8 m figure and a scale bar. The title block names the building's district and its part in the parti
(binder/parti.json). Meshes: Models/round2_ase/*.ase (50 units = 1 m, pivot at the base; CraneTower's pivot is the
top of its plinth, so its plinth hangs below 0).
"""
import json, math, os, re, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Models", "round2_ase")
a = [x for x in sys.argv[1:] if "=" not in x]
o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
OUT = a[0] if a else os.path.join(HERE, "..", "Models", "plans")
os.makedirs(OUT, exist_ok=True)
CUT = float(o.get("cut", 1.5))
M = 50.0
ROLE = {
    "CraneTower": ("T5 company", "HERO. The company's stepped temple-tower on the high ground, with its lattice crane. Seen from the whole walk; beat 4 (melancholy) is its catwalk. Battered walls, red domes; prospect without refuge."),
    "FactoryHall": ("T4 works", "The works' shed. Blank battered edges to the road (Building Edge inverted); bay doors face the yard; stacks feed the plume that drifts over the shanty."),
    "FactoryBlock": ("T4 works", "Plant block between the halls and the racks: no place to stay."),
    "DormPod": ("T3 housing", "Company prefab: blue with the orange top band. Rows with back yards and back lanes; the kit the shanty later transforms."),
    "TinShack": ("T2 shanty", "The shanty's unit: the company kit transformed by additions - lean-tos, laundry, cables. Party walls, small squares, refuge."),
    "AframeHut": ("T3 housing", "Blue hut with the orange roof edge on the slopes; faces downhill to the road."),
    "WaterTower": ("T4 works", "Rhythm: one of the vertical marks along the spine (pylons, lamps, rack bents, towers)."),
    "TwinTowers": ("T4 works", "Cooling pair: the second landmark after the tower; the plume's source."),
    "SiloCluster": ("T4 works", "Ore silos on the datum (the straight ore line)."),
    "ChimneyStack": ("T4 works", "A stack: the smoke the town lives in."),
    "PipeRack": ("T4 works", "Rack bents along shared utility trunks: rhythm along the road."),
}
NAMES = o.get("names", "CraneTower,FactoryHall,DormPod,TinShack,AframeHut,TwinTowers").split(",")


def font(sz, bold=False):
    try:
        return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", "arialbd.ttf" if bold else "arial.ttf"), sz)
    except OSError:
        return ImageFont.load_default()


F11, F13, F16, F22, F30 = font(11), font(13), font(16, True), font(22, True), font(30, True)
PAL = np.asarray(Image.open(os.path.join(SRC, "Pal2.tga")).convert("RGB")).astype(float)


def load(name):
    t = open(os.path.join(SRC, name + ".ase")).read()
    V = np.array([[float(v) for v in m] for m in re.findall(r"\*MESH_VERTEX\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)", t)])
    V[:, 0] = -V[:, 0]                                  # ase.py mirrored X on write
    F = np.array([[int(v) for v in m] for m in re.findall(r"\*MESH_FACE\s+\d+:\s+A:\s+(\d+)\s+B:\s+(\d+)\s+C:\s+(\d+)", t)])
    TV = np.array([[float(v) for v in m] for m in re.findall(r"\*MESH_TVERT\s+\d+\s+(\S+)\s+(\S+)", t)])
    TF = np.array([[int(v) for v in m] for m in re.findall(r"\*MESH_TFACE\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)", t)])
    col = np.full((len(F), 3), 200.0)
    if len(TV) and len(TF) == len(F):
        uv = TV[TF].mean(1)
        h, w = PAL.shape[:2]
        col = PAL[np.clip(((1 - uv[:, 1]) * h).astype(int), 0, h - 1), np.clip((uv[:, 0] * w).astype(int), 0, w - 1)]
    return V / M, F, col                                # metres


def feature_edges(V, F, crease=20.0):
    """per triangle, which of its 3 edges is a real edge (an outline or a crease over `crease` degrees) - the
    triangulation's diagonals across flat faces are not drawn"""
    P = V[F]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    key = lambda p: (round(p[0], 2), round(p[1], 2), round(p[2], 2))
    edges = {}
    for t, tri in enumerate(P):
        for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
            k = tuple(sorted((key(tri[i]), key(tri[j]))))
            edges.setdefault(k, []).append((t, e))
    feat = np.zeros((len(F), 3), bool)
    cosc = math.cos(math.radians(crease))
    for k, lst in edges.items():
        if len(lst) == 1:
            feat[lst[0][0], lst[0][1]] = True
            continue
        for a_ in range(len(lst)):
            for b_ in range(a_ + 1, len(lst)):
                if float(n[lst[a_][0]] @ n[lst[b_][0]]) < cosc:
                    feat[lst[a_][0], lst[a_][1]] = True
                    feat[lst[b_][0], lst[b_][1]] = True
    return feat


def shade(n, base):
    sun = np.array([math.cos(math.radians(136)), math.sin(math.radians(136)), 0.45])
    sun /= np.linalg.norm(sun)
    k = 0.55 + 0.45 * max(0.0, float(n @ sun))
    c = base * 0.35 + 255 * 0.65                        # pale: a drawing, not a render
    return tuple(int(min(255, v * k)) for v in c)


def view(dr, V, F, col, axes, depth_axis, depth_sign, ox, oy, s, mode="elev", zclip=None, feat=None):
    """orthographic: axes = (u index, u sign, v index, v sign) on the page; painter's order by depth"""
    ui, us, vi, vs = axes
    P = V[F]                                            # (n, 3, 3)
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    nl = np.linalg.norm(n, axis=1, keepdims=True)
    n = n / np.maximum(nl, 1e-9)
    d = P[:, :, depth_axis].mean(1) * depth_sign
    order = np.argsort(d)                               # far first
    for k in order:
        if nl[k] < 1e-9:
            continue
        if zclip is not None and P[k, :, 2].max() > zclip:
            continue
        if n[k, depth_axis] * depth_sign <= 0 and mode != "plan_below":
            continue                                    # back faces
        pts = [(ox + us * P[k, j, ui] * s, oy - vs * P[k, j, vi] * s) for j in range(3)]
        if mode == "plan_below":
            fill, ink = (250, 250, 250), (175, 175, 175)
        elif mode == "roof":
            z = P[k, :, 2].mean()
            g = int(250 - 60 * np.clip(z / max(1e-6, V[:, 2].max()), 0, 1))
            fill, ink = (g, g, g), (140, 140, 140)
        else:
            fill, ink = shade(n[k], col[k]), (70, 70, 70)
        dr.polygon(pts, fill=fill)
        for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
            if feat is None or feat[k, e]:
                dr.line([pts[i], pts[j]], fill=ink, width=1)


def cut(V, F, axis, value):
    """segments where the plane coord[axis] = value cuts the triangles"""
    segs = []
    P = V[F]
    for tri in P:
        dvals = tri[:, axis] - value
        if dvals.min() > 0 or dvals.max() < 0:
            continue
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (dvals[i] > 0) != (dvals[j] > 0):
                t = dvals[i] / (dvals[i] - dvals[j])
                pts.append(tri[i] + (tri[j] - tri[i]) * t)
        if len(pts) == 2:
            segs.append(pts)
    return segs


def figure(dr, x, y, s):
    """a 1.8 m person standing at (x, y) on the page (y = feet)"""
    c = (190, 40, 40)
    if s * 1.8 < 6:                                     # too small to draw a body: a tick
        dr.line([(x, y), (x, y - 1.8 * s - 2)], fill=c, width=1)
        return
    w_ = max(1, int(0.08 * s))
    for dx_ in (-0.12, 0.12):                           # legs
        dr.line([(x + dx_ * s, y), (x + dx_ * 0.6 * s, y - 0.9 * s)], fill=c, width=w_)
    dr.rectangle([x - 0.2 * s, y - 1.5 * s, x + 0.2 * s, y - 0.85 * s], fill=c)      # body
    for dx_ in (-1, 1):                                 # arms
        dr.line([(x + dx_ * 0.2 * s, y - 1.45 * s), (x + dx_ * 0.27 * s, y - 0.9 * s)], fill=c, width=w_)
    r = 0.12 * s
    dr.ellipse([x - r, y - 1.8 * s, x + r, y - 1.8 * s + 2 * r], fill=c)


def scalebar(dr, x, y, s, metres):
    dr.rectangle([x, y, x + metres * s, y + 5], outline=(0, 0, 0))
    dr.rectangle([x, y, x + metres * s / 2, y + 5], fill=(0, 0, 0))
    dr.text((x, y + 8), "0", font=F11, fill=(0, 0, 0))
    dr.text((x + metres * s - 22, y + 8), "%g m" % metres, font=F11, fill=(0, 0, 0))


def nice(m):
    for v in (1, 2, 5, 10, 20, 50, 100):
        if v >= m:
            return v
    return 100


SW, SH = 1700, 1200
for k_sheet, name in enumerate(NAMES):
    V, F, col = load(name)
    FEAT = feature_edges(V, F)
    lo, hi = V.min(0), V.max(0)
    W, D, H = hi[1] - lo[1], hi[0] - lo[0], hi[2] - lo[2]
    # one scale for every view on the sheet: the 2x2 grid of panels left of the title column
    PWd, PHt = 590, 520
    s = min((PWd - 60) / max(D, W), (PHt - 70) / max(H, D, W))
    img = Image.new("RGB", (SW, SH), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    dr.rectangle([10, 10, SW - 10, SH - 10], outline=(0, 0, 0), width=2)
    dr.text((30, 22), name.upper(), font=F30, fill=(0, 0, 0))
    panels = [(30, 70), (30 + PWd + 20, 70), (30, 70 + PHt + 20), (30 + PWd + 20, 70 + PHt + 20)]
    titles = ["PLAN  cut at %.1f m" % CUT, "FRONT ELEVATION  (+X, the road side)", "SIDE ELEVATION  (+Y)", "SECTION  through the middle, across the front"]
    for (px, py), tt in zip(panels, titles):
        dr.rectangle([px, py, px + PWd, py + PHt], outline=(0, 0, 0))
        dr.text((px + 8, py + 6), tt, font=F13, fill=(0, 0, 0))
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    # PLAN: page u = -Y (so the front, +X, is down... keep north = +Y up): u = X, v = Y
    px, py = panels[0]
    ox, oy = px + PWd / 2 - cx * s, py + PHt / 2 + 10 + cy * s
    view(dr, V, F, col, (0, 1, 1, 1), 2, 1, ox, oy, s, mode="plan_below", zclip=lo[2] + CUT, feat=FEAT)
    zc = lo[2] + CUT if name != "CraneTower" else CUT              # the tower: cut 1.5 m over its plinth top
    for (p, q) in cut(V, F, 2, zc):
        dr.line([(ox + p[0] * s, oy - p[1] * s), (ox + q[0] * s, oy - q[1] * s)], fill=(0, 0, 0), width=3)
    ax_ = ox + (hi[0] + 1.5) * s
    dr.polygon([(ax_, oy - cy * s), (ax_ + 12, oy - cy * s - 6), (ax_ + 12, oy - cy * s + 6)], fill=(190, 40, 40))
    dr.text((ax_ + 14, oy - cy * s - 7), "road", font=F11, fill=(190, 40, 40))
    # FRONT ELEVATION: viewer at +X looking -X: page u = -Y (left = +Y), v = Z
    px, py = panels[1]
    gy = py + PHt - 45
    ox, oy = px + PWd / 2 + cy * s, gy + lo[2] * s
    view(dr, V, F, col, (1, -1, 2, 1), 0, 1, ox, oy, s, feat=FEAT)
    dr.line([(px + 10, oy - 0 * s), (px + PWd - 10, oy)], fill=(0, 0, 0), width=2)
    figure(dr, ox - (hi[1] + 2) * s if ox - (hi[1] + 2) * s > px + 15 else px + 20, oy, s)
    # SIDE ELEVATION: viewer at +Y looking -Y: page u = X, v = Z
    px, py = panels[2]
    gy = py + PHt - 45
    ox, oy = px + PWd / 2 - cx * s, gy + lo[2] * s
    view(dr, V, F, col, (0, 1, 2, 1), 1, 1, ox, oy, s, feat=FEAT)
    dr.line([(px + 10, oy), (px + PWd - 10, oy)], fill=(0, 0, 0), width=2)
    figure(dr, ox + (hi[0] + 2) * s if ox + (hi[0] + 2) * s < px + PWd - 15 else px + PWd - 20, oy, s)
    # SECTION at Y = cy, viewed from -Y (the far half, y > cy, beyond): page u = X, v = Z
    px, py = panels[3]
    gy = py + PHt - 45
    ox, oy = px + PWd / 2 - cx * s, gy + lo[2] * s
    far = np.array([i for i, f in enumerate(F) if V[f, 1].mean() > cy])
    if len(far):
        P = V[F[far]]
        for t in far[np.argsort(-P[:, :, 1].mean(1))]:
            tri = V[F[t]]
            pts = [(ox + tri[j, 0] * s, oy - tri[j, 2] * s) for j in range(3)]
            dr.polygon(pts, fill=(242, 242, 242))
            for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 0))):
                if FEAT[t, e]:
                    dr.line([pts[i], pts[j]], fill=(195, 195, 195))
    for (p, q) in cut(V, F, 1, cy):
        dr.line([(ox + p[0] * s, oy - p[2] * s), (ox + q[0] * s, oy - q[2] * s)], fill=(0, 0, 0), width=3)
    dr.line([(px + 10, oy), (px + PWd - 10, oy)], fill=(0, 0, 0), width=2)
    figure(dr, ox + (hi[0] + 2) * s if ox + (hi[0] + 2) * s < px + PWd - 15 else px + PWd - 20, oy, s)
    # scale bars
    sb = nice(max(D, W, H) / 4)
    for (px, py) in panels:
        scalebar(dr, px + 12, py + PHt - 22, s, sb)
    # notes + title block
    tx = 30 + 2 * PWd + 50
    district, role = ROLE.get(name, ("-", "-"))
    y = 80
    dr.text((tx, y), "Dimensions", font=F16, fill=(0, 0, 0)); y += 24
    for line in ("width %.1f m" % W, "depth %.1f m (front to back)" % D, "height %.1f m" % H, "faces %d" % len(F)):
        dr.text((tx, y), line, font=F13, fill=(30, 30, 30)); y += 18
    y += 10
    dr.text((tx, y), "Role in the parti", font=F16, fill=(0, 0, 0)); y += 24
    words, line = role.split(), ""
    for wd in words:
        if len(line) + len(wd) > 44:
            dr.text((tx, y), line, font=F13, fill=(30, 30, 30)); y += 18; line = wd
        else:
            line = (line + " " + wd).strip()
    dr.text((tx, y), line, font=F13, fill=(30, 30, 30)); y += 28
    dr.text((tx, y), "Conventions", font=F16, fill=(0, 0, 0)); y += 24
    for line in ("Thick black: cut by the plane.", "Thin grey: below the cut / beyond.", "Elevations: palette colours, low sun",
                 "from az 136.", "Red figure: 1.8 m.  Red arrow: the road."):
        dr.text((tx, y), line, font=F13, fill=(30, 30, 30)); y += 18
    ty = SH - 250
    dr.rectangle([tx - 10, ty - 10, SW - 22, SH - 22], outline=(0, 0, 0), width=2)
    dr.text((tx, ty), "AVALON", font=F30, fill=(0, 0, 0))
    dr.text((tx, ty + 40), "Liandri mining colony - building", font=F13, fill=(0, 0, 0))
    dr.text((tx, ty + 60), "%s  -  %s" % (name, district), font=F13, fill=(80, 80, 80))
    dr.line([tx - 10, ty + 86, SW - 22, ty + 86], fill=(0, 0, 0))
    dr.text((tx, ty + 96), "plan, elevations, section", font=F13, fill=(0, 0, 0))
    dr.text((tx, ty + 116), "one scale on the sheet; see the bars", font=F11, fill=(80, 80, 80))
    dr.line([tx - 10, ty + 146, SW - 22, ty + 146], fill=(0, 0, 0))
    dr.text((tx, ty + 156), "SHEET", font=F11, fill=(80, 80, 80))
    dr.text((tx, ty + 172), "B-%03d" % (101 + k_sheet), font=F30, fill=(0, 0, 0))
    dr.text((tx + 190, ty + 156), "2026-10-08", font=F11, fill=(80, 80, 80))
    dr.text((tx + 190, ty + 180), "from the game meshes", font=F11, fill=(80, 80, 80))
    path = os.path.join(OUT, "B-%03d_%s.png" % (101 + k_sheet, name))
    img.save(path)
    print("sheet", path, "(%.1f x %.1f x %.1f m)" % (W, D, H))
