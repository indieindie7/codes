r"""The money shot: how a layout reads through the command room's window, scored like a cinematographer would.

    py tools/compose.py <heightmap.bmp> <layout.json> [png=frame.png]
    (as a library: score(heightmap, layout) -> dict)

The player starts in the tower's command room (TutA's PlayerStart) and looks out of one window that faces
yaw 300 +- 34 degrees. That view is projected here (a pinhole camera at eye height, 68 degrees wide, looking 9 degrees
down: the sea horizon on the upper third, the plant about 19 degrees below the eye on the lower third; it was 28 down,
which cut the horizon out of the frame - the director, redesign 2026-10-09 s. 0.2): every building that the terrain does not hide is placed on the frame
by the top of its silhouette. Rules from games/reports/Cinematography and concept art for the Avalon
town.md:
  * the hero (the cooling towers, else the tallest building in frame) on a vertical third, not centred;
  * the town spans 30-60 % of the frame width: smaller reads as specks, wider as clutter;
  * enough in frame to read as a town (12+ buildings), with depth (near, middle and far bands all used);
  * a leading line: the spine road's on-screen direction points at the hero.
score() returns the parts and a total in 0..1; town.py tries several layout seeds and keeps the best.
"""
import json, math, os, struct, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import binder  # noqa

try:
    PARTI = json.load(open(os.path.join(os.path.dirname(HERE), "binder", "parti.json")))
except (OSError, ValueError):
    PARTI = {}

LOC = (-14487.546875, 4835.837891, -131.845703)
CELL, N, SEA_Z = 512.0, 128, -4967.0
EYE = (-349.7, 1388.3, 4238.0 + 64)            # the command room's PlayerStart, eye height
LOOK_YAW, HALF_W, PITCH = 300.0, 34.0, -9.0    # the window: centre yaw, half width, the gaze tilt (horizon on the upper third)
HALF_H = 26.0                                   # half height of the view (degrees): -35 .. +17 with the tilt
# The map must match: the command room's PlayerStart should face Pitch -9 deg (= -1638 rotation units, 63898 as an
# unsigned word) so the first frame the player sees is this one; island_batch.pilot_script's window shots still turn
# to -18..-22 (they look at the plant, not at this frame).
PITCH_RU = int(round(PITCH * 65536 / 360.0)) % 65536


def _heights(bmp):
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    H = H[::-1] if h > 0 else H
    return np.maximum(LOC[2] + (H - 32768) * 0.5, SEA_Z)


def _bil(Z, x, y):
    fi = np.clip((x - LOC[0]) / CELL + N / 2, 0, N - 1.001)
    fj = np.clip((y - LOC[1]) / CELL + N / 2, 0, N - 1.001)
    i0, j0 = fi.astype(int), fj.astype(int)
    ti, tj = fi - i0, fj - j0
    return Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj


def project(x, y, z):
    """world point -> (u, v) on the window frame (0..1, v down), or None outside it"""
    dx, dy, dz = x - EYE[0], y - EYE[1], z - EYE[2]
    yaw = math.degrees(math.atan2(dy, dx))
    rel = (yaw - LOOK_YAW + 180) % 360 - 180
    if abs(rel) > HALF_W:
        return None
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy))) - PITCH
    u = 0.5 + 0.5 * math.tan(math.radians(rel)) / math.tan(math.radians(HALF_W))
    v = 0.5 - 0.5 * math.tan(math.radians(pitch)) / math.tan(math.radians(HALF_H))
    return (u, v) if 0 <= v <= 1 else None


def score(heightmap, layout_path, png=None):
    Z = _heights(heightmap)
    L = json.load(open(layout_path))
    _, sheets = binder.load()
    inframe = []
    for bid, b in L["buildings"].items():
        sz = sheets.get(bid, {}).get("size")
        if not sz or bid in ("tower", "far_islands"):
            continue
        hgt = sz[2] * 50.0
        if sheets[bid].get("card"):
            cw = sheets[bid]["card"].split()
            if len(cw) > 1:
                hgt = max(hgt, float(cw[1]))
        gz = max(float(_bil(Z, np.array([b["x"]]), np.array([b["y"]]))[0]), SEA_Z)
        top = gz + hgt
        p = project(b["x"], b["y"], top)
        if p is None:
            continue
        t = np.linspace(0.02, 0.95, 80)          # the terrain must not hide the silhouette's top
        xs, ys = EYE[0] + (b["x"] - EYE[0]) * t, EYE[1] + (b["y"] - EYE[1]) * t
        if not np.all(_bil(Z, xs, ys) <= EYE[2] + (top - EYE[2]) * t + 1.0):
            continue
        dist = math.hypot(b["x"] - EYE[0], b["y"] - EYE[1]) / 50.0
        inframe.append(dict(id=bid, u=p[0], v=p[1], hgt=hgt, dist=dist))
    out = {"in_frame": len(inframe), "ids": sorted(x["id"] for x in inframe)}
    if not inframe:
        out.update(total=0.0, hero=None)
        return out
    # the hero: the parti's (binder/parti.json, liandri_tower since binder 1940260) when it is in the window, else its
    # "second" (the cooling towers), else the tallest building in frame
    hero = (next((x for x in inframe if x["id"] == PARTI.get("hero")), None) or
            next((x for x in inframe if x["id"] == PARTI.get("second", "cooling_towers")), None) or max(inframe, key=lambda x: x["hgt"]))
    thirds = max(0.0, 1 - min(abs(hero["u"] - 1 / 3), abs(hero["u"] - 2 / 3)) / 0.17)
    us = [x["u"] for x in inframe]
    span = max(us) - min(us)
    cover = 1.0 if 0.3 <= span <= 0.6 else max(0.0, 1 - (0.3 - span) / 0.3 if span < 0.3 else 1 - (span - 0.6) / 0.4)
    count = min(1.0, len(inframe) / 12.0)
    bands = {0 if x["dist"] < 250 else (1 if x["dist"] < 500 else 2) for x in inframe}
    depth = len(bands) / 3.0
    lead = 0.5
    sp = L.get("spine") or []
    seg = [project(x, y, float(_bil(Z, np.array([x]), np.array([y]))[0])) for x, y in sp[::4]]
    seg = [s for s in seg if s]
    if len(seg) >= 2:
        (u0, v0), (u1, v1) = seg[0], seg[-1]
        d_line = (u1 - u0, v1 - v0)
        d_hero = (hero["u"] - u0, hero["v"] - v0)
        n1, n2 = math.hypot(*d_line), math.hypot(*d_hero)
        if n1 > 1e-3 and n2 > 1e-3:
            lead = 0.5 + 0.5 * abs(d_line[0] * d_hero[0] + d_line[1] * d_hero[1]) / (n1 * n2)
    total = 0.3 * thirds + 0.25 * cover + 0.2 * count + 0.15 * depth + 0.1 * lead
    out.update(hero=hero["id"], hero_u=round(hero["u"], 2), thirds=round(thirds, 2), span=round(span, 2), cover=round(cover, 2),
               count=round(count, 2), depth=round(depth, 2), lead=round(lead, 2), total=round(total, 3))
    if png:
        from PIL import Image, ImageDraw
        W, Hh = 680, 440
        im = Image.new("RGB", (W, Hh), (150, 180, 210))
        d = ImageDraw.Draw(im)
        hz = []                                   # the terrain's skyline across the frame
        for k in range(0, W, 4):
            rel = math.degrees(math.atan(((k / W) - 0.5) * 2 * math.tan(math.radians(HALF_W))))
            a = math.radians(LOOK_YAW + rel)
            best = 1.0
            for r in np.linspace(200, 60000, 220):
                x, y = EYE[0] + r * math.cos(a), EYE[1] + r * math.sin(a)
                z = float(_bil(Z, np.array([x]), np.array([y]))[0])
                pr = project(x, y, z)
                if pr:
                    best = min(best, pr[1])
            hz.append((k, best * Hh))
        d.polygon([(0, Hh)] + hz + [(W, Hh)], fill=(95, 120, 80))
        for x in (W / 3, 2 * W / 3):
            d.line([x, 0, x, Hh], fill=(255, 255, 255))
        for x in inframe:
            c = (255, 80, 60) if x is hero else (40, 40, 45)
            u, v = x["u"] * W, x["v"] * Hh
            d.rectangle([u - 4, v, u + 4, v + 10 + x["hgt"] / 150], fill=c)
        d.text((6, 6), "window frame: %d buildings, hero %s at u=%.2f, total %.2f" % (len(inframe), hero["id"], hero["u"], total), fill=(0, 0, 0))
        im.save(png)
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if "=" not in x]
    o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    print(json.dumps(score(a[0], a[1], o.get("png")), indent=1))
