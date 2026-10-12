"""Level analysis for a layout.json (page-3 format): walks the path every 2 m and checks the level-design heuristics.
  py -3.13 analyze_level.py [folder]    -> prints a report, writes analysis.json + analysis_overlay.png
2D occlusion, plus a 3D check for A (A_3d: worst-case 8 m houses, the hill from layout.json): occluders = building rectangles + round C; mansion A and C are the landmarks.
Isovists are pysovist's exact 2D wedge sweep (max 60 m); sight to a landmark = a free line to any of 9 points on it.
"""
import json, math, os, sys
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely import affinity
from pysovist import isovist
from PIL import Image, ImageDraw

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(D, 'layout.json')))
S = L['scale_m_per_px']
M = lambda x, y: (x * S, -y * S)                    # preview px (y down) -> metres (y up)


def rect(cx, cy, w, h, a):
    p = Polygon([M(cx - w / 2, cy - h / 2), M(cx + w / 2, cy - h / 2), M(cx + w / 2, cy + h / 2), M(cx - w / 2, cy + h / 2)])
    return affinity.rotate(p, -a, origin=M(cx, cy))  # drawn angle is clockwise in y-down px


blds = [rect(*b) for b in L['buildings']]
cx, cy, r = L['round_C']
roundC = Point(M(cx, cy)).buffer(r * S, 24)
mans = rect(*L['mansion_A'])
occ = blds + [roundC]


def segs(polys):
    out = []
    for p in polys:
        c = list(p.exterior.coords)
        out += [[c[i], c[i + 1]] for i in range(len(c) - 1)]
    return np.array(out, float)


SEG_ALL = segs(occ + [mans])
LM = {'A': (mans, blds + [roundC]), 'C': (roundC, blds + [mans])}


def sees(o, target, blockers):
    pts = [target.centroid] + [Point(c) for c in target.exterior.coords[:-1:max(1, len(target.exterior.coords) // 8)]]
    for q in pts:
        ln = LineString([o, q])
        if not any(ln.crosses(b) or ln.within(b) for b in blockers if b.distance(ln) < 1e-6 and not b.equals(target)):
            return True
    return False


HT, HH, HR = L['hill']['top'], L['hill']['height_m'], L['hill']['radius_px'] * S
def hgt(x, y):                                       # same hill as build_level.py, metres in, metres out
    return HH * max(0.0, 1 - math.dist((x, y), M(*HT)) / HR) ** 2
TOP = 8.0                                            # worst-case house/C top above its ground (walls 5-8 m + roof)
def sees3(o, tgt_xy, tgt_z):
    """Eye 1.7 m over the ground at o to a 3D point; blocked by a building whose top is above the line or by the hill."""
    z0 = hgt(o.x, o.y) + 1.7; ln = LineString([o, tgt_xy]); dist = ln.length
    for b in occ:
        if b.distance(ln) > 1e-6: continue
        seg = ln.intersection(b)
        for c in getattr(seg, 'coords', []):
            t = math.dist((o.x, o.y), c) / dist
            if z0 + t * (tgt_z - z0) < hgt(*c) + TOP: return False
    for t in np.linspace(0.05, 0.95, 19):
        x, y = o.x + t * (tgt_xy[0] - o.x), o.y + t * (tgt_xy[1] - o.y)
        if z0 + t * (tgt_z - z0) < hgt(x, y): return False
    return True
AT = (mans.centroid.x, mans.centroid.y); AZ = hgt(*AT) + 12.0   # 3/4 up the 16 m mansion card

# --- path samples every 2 m
path = LineString([M(*p) for p in L['path']])
n = int(path.length // 2) + 1
samp = [path.interpolate(i * 2.0) for i in range(n)]
rows = []
for i, s in enumerate(samp):
    a, b = path.interpolate(max(0, i * 2 - 1)), path.interpolate(min(path.length, i * 2 + 1))
    hd = math.atan2(b.y - a.y, b.x - a.x)
    iso = isovist(SEG_ALL, (s.x, s.y), max_distance=60.0)
    m = iso.metrics
    row = {'i': i, 'd': round(i * 2.0, 1), 'x': round(s.x, 2), 'y': round(s.y, 2),
           'area': round(float(m['area']), 1), 'r_max': round(float(m['r_max']), 1), 'r_mean': round(float(m['r_mean']), 1),
           'clear': round(min(p.distance(s) for p in occ), 2)}
    for k, (t, bl) in LM.items():
        row['see_' + k] = sees(s, t, bl)
        tb = math.atan2(t.centroid.y - s.y, t.centroid.x - s.x)
        row['ang_' + k] = round(abs(math.degrees((tb - hd + math.pi) % (2 * math.pi) - math.pi)), 0)
    row['see3_A'] = sees3(s, AT, AZ)
    rows.append(row)

# --- report
P = L['path']
straight = math.dist(M(*P[0]), M(*P[-1]))
area = np.array([r['area'] for r in rows])
rep = {'path_m': round(path.length, 1), 'samples': n, 'winding_ratio': round(path.length / straight, 2)}
for k in LM:
    v = [r['see_' + k] for r in rows]
    first = next((r['d'] for r in rows if r['see_' + k]), None)
    lead = [r for r in rows if r['see_' + k] and r['ang_' + k] <= 45]
    rep[k] = {'visible_pct': round(100 * sum(v) / n), 'first_seen_m': first, 'seen_at_start': v[0],
              'ahead_within_45deg_pct': round(100 * len(lead) / n),
              'hidden_stretches_m': [], }
    run = None
    for r in rows:
        if not r['see_' + k] and run is None: run = r['d']
        if r['see_' + k] and run is not None: rep[k]['hidden_stretches_m'].append([run, r['d']]); run = None
    if run is not None: rep[k]['hidden_stretches_m'].append([run, rows[-1]['d']])
v3 = [r['see3_A'] for r in rows]
rep['A_3d'] = {'visible_pct': round(100 * sum(v3) / n), 'seen_at_start': v3[0],
               'first_seen_m': next((r['d'] for r in rows if r['see3_A']), None)}
rep['isovist_area_m2'] = {'min': float(area.min()), 'max': float(area.max()), 'mean': round(float(area.mean()), 1),
                          'cv': round(float(area.std() / area.mean()), 2)}
# compression/release: local minima then a jump of +50% within 10 m
rel = []
for i in range(1, n - 5):
    if area[i] <= area[i - 1] and area[i] <= area[i + 1] and area[i + 1:i + 6].max() > 1.5 * area[i]:
        rel.append(rows[i]['d'])
rep['release_points_m'] = rel
cl = [r['clear'] for r in rows]
rep['clearance_m'] = {'min': min(cl), 'at_m': rows[int(np.argmin(cl))]['d'], 'under_2m_samples': sum(c < 2.0 for c in cl)}
json.dump({'report': rep, 'samples': rows}, open(os.path.join(D, 'analysis.json'), 'w'), indent=1)
print(json.dumps(rep, indent=1))

# --- overlay on the map preview: path dots green = sees A, orange = sees only C, red = neither; size = isovist area
g = os.path.join(D, 'map_grid.png')
x0, y0, x1, y1 = L['map_box']
im = Image.open(g).convert('RGB').crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2))
dr = ImageDraw.Draw(im, 'RGBA')
px = lambda x, y: ((x / S - x0) * 2, (-y / S - y0) * 2)
for p in occ + [mans]:
    dr.polygon([px(*c) for c in p.exterior.coords], fill=(60, 60, 200, 60), outline=(40, 40, 160, 255))
amax = area.max()
for r in rows:
    c = (30, 170, 60) if r['see_A'] else (120, 200, 255) if r['see3_A'] else (240, 140, 20) if r['see_C'] else (220, 30, 30)
    rad = 3 + 9 * r['area'] / amax
    X, Y = px(r['x'], r['y'])
    dr.ellipse([X - rad, Y - rad, X + rad, Y + rad], fill=c + (200,), outline=(0, 0, 0, 255))
for d in rel:
    r = rows[int(d / 2)]; X, Y = px(r['x'], r['y'])
    dr.text((X + 10, Y - 6), 'release', fill=(0, 0, 0, 255))
dr.text((10, 10), 'green: A visible (2D)   blue: A over the roofs (3D)   orange: only C   red: neither   dot size = isovist area', fill=(0, 0, 0, 255))
im.save(os.path.join(D, 'analysis_overlay.png'))
