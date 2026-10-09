"""PathNodes for a generated Avalon town, from its GRADED heightmap (redesign plan s.7 Phase A step 5).

    py tools/pathnodes.py <town dir> [out=<dir>/isl_paths.t3d] [z=60] [slope=0.9] [reach=6] [layout=stagger|grid] [cover=0|1]

Reads <town dir>/isl_ec.bmp (the cut-and-fill ground that ships), isl_layout.json (building cells) and
isl_clutter.t3d (cover props). Places:
  - ground nodes: layout=stagger (default, 2026-10-09): a staggered lattice on the heightmap cells, rows 1024 UU apart,
    every 2nd cell, odd rows shifted one cell, so each node has ~6 neighbours at 1024-1145 UU (all under the engine's
    hard 1200 UU pair limit); a lattice cell that isn't walkable falls back to a walkable 4-neighbour. ~20x fewer node
    pairs for PATHS DEFINE than layout=grid (one node per 512 UU cell: TutA_Remake's define ran 45+ min and was
    stopped; research_notes/Lighter AI pathing for UE2/report.md);
    walkable = above the sea + 50, within `reach` cells of a building or road, not a building cell, steepest rise to a 4-neighbour <= slope * 512;
  - cover nodes (cover=1 only; off by default: U2's AI makes its own CoverSpots at runtime): two per cover prop (crates, barrels, walls, sheds, pipe racks, rocks), 140 UU out on each side
    across the prop's facing, when that spot is walkable;
  - high nodes: walkable cells that are the top of their 5x5 window (sniping/overlook spots, tagged in Tag=).
Nodes sit `z` UU over the ground (the player's CollisionHeight is 54: facts_measured.md).
Writes a T3D of PathNode actors (paste/import into the map AFTER the lighting build, then PATHS DEFINE: the Sanctuary
gotcha) and <out>.png, a top view: grey ground, red buildings, white nodes, yellow cover, cyan high spots.
"""
import math, os, re, struct, sys, json
import numpy as np

LOC = (-14487.546875, 4835.837891, -131.845703)     # TutA TerrainInfo0 (every generated town keeps it)
SCALE = (512.0, 512.0, 128.0)
SEA_Z = -4967.0
COVER_RE = re.compile(r"Crate|Barrel|B_wall|B_shed|PipeRack|Rock\d", re.I)

town = sys.argv[1]
o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
out = o.get("out", os.path.join(town, "isl_paths.t3d"))
ZUP, SLOPE = float(o.get("z", 60)), float(o.get("slope", 0.9))
LAYOUT = o.get("layout", "stagger")
COVER_ON = o.get("cover", "0") == "1"

raw = open(os.path.join(town, "isl_ec.bmp"), "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
assert struct.unpack_from("<H", raw, 28)[0] == 16
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * SCALE[2] / 256          # world Z per cell [j, i]
n = Z.shape[0]


def world(i, j):
    return LOC[0] + (i - w / 2) * SCALE[0], LOC[1] + (j - n / 2) * SCALE[1]


def cell(x, y):
    return (x - LOC[0]) / SCALE[0] + w / 2, (y - LOC[1]) / SCALE[1] + n / 2


def ground(x, y):
    fi, fj = cell(x, y)
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < w - 1 and 0 <= j0 < n - 1):
        return None
    ti, tj = fi - i0, fj - j0
    return (Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj)
            + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)


lay = json.load(open(os.path.join(town, "isl_layout.json")))
built = np.zeros_like(Z, dtype=bool)
for b in lay["buildings"].values():
    for i, j in b.get("cells", []):
        if 0 <= j < n and 0 <= i < w:
            built[j, i] = True

rise = np.zeros_like(Z)
for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    rise = np.maximum(rise, np.abs(np.roll(np.roll(Z, dj, 0), di, 1) - Z))
# the play area: within `reach` cells of a building or a road (the outer terrain is a flat plain nobody walks)
REACH = int(o.get("reach", 6))
town_ = built.copy()
for road in lay.get("roads", []):
    for x, y in road:
        fi, fj = cell(x, y)
        i, j = int(round(fi)), int(round(fj))
        if 0 <= i < w and 0 <= j < n:
            town_[j, i] = True
near = town_.copy()
for _ in range(REACH):
    g = near.copy()                     # grow by one cell, no wrap-around at the map edges
    g[1:] |= near[:-1]; g[:-1] |= near[1:]; g[:, 1:] |= near[:, :-1]; g[:, :-1] |= near[:, 1:]
    near = g
walk = (Z > SEA_Z + 50) & ~built & (rise <= SLOPE * SCALE[0]) & near
walk[[0, -1], :] = walk[:, [0, -1]] = False


def walkable(x, y):
    fi, fj = cell(x, y)
    i, j = int(round(fi)), int(round(fj))
    return 0 <= i < w and 0 <= j < n and walk[j, i]


nodes = []      # (x, y, z, tag)
taken = set()


def is_high(i, j):
    win = Z[max(0, j - 2):j + 3, max(0, i - 2):i + 3]
    return Z[j, i] >= win.max() and win.max() - win.min() > 150


def lattice(i, j):
    return j % 2 == 0 and i % 2 == (j // 2) % 2


for j in range(n):
    for i in range(w):
        if LAYOUT == "grid":
            pick = (i, j) if walk[j, i] else None
        elif is_high(i, j) and walk[j, i]:
            pick = (i, j)                    # the high spots stay, on or off the lattice
        elif lattice(i, j):
            pick = next(((a, b) for a, b in ((i, j), (i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1))
                         if 0 <= a < w and 0 <= b < n and walk[b, a] and (a, b) not in taken), None)
        else:
            pick = None
        if pick and pick not in taken:
            taken.add(pick)
            a, b = pick
            x, y = world(a, b)
            nodes.append((x, y, Z[b, a] + ZUP, "high" if is_high(a, b) else "ground"))

txt = open(os.path.join(town, "isl_clutter.t3d"), encoding="utf-8", errors="replace").read()
ncover = 0
for blk in re.findall(r"Begin Actor(.*?)End Actor", txt, re.S):
    m = re.search(r"StaticMesh=StaticMesh'([^']+)'", blk)
    if not COVER_ON or not m or not COVER_RE.search(m.group(1)):
        continue
    L = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", blk)
    yaw = re.search(r"Yaw=(-?\d+)", blk)
    x0, y0 = float(L.group(1)), float(L.group(2))
    a = (int(yaw.group(1)) if yaw else 0) * math.pi / 32768 + math.pi / 2       # across the prop's facing
    for s in (-1, 1):
        x, y = x0 + s * 140 * math.cos(a), y0 + s * 140 * math.sin(a)
        g = ground(x, y)
        if g is not None and walkable(x, y):
            nodes.append((x, y, g + ZUP, "cover"))
            ncover += 1

with open(out, "w", newline="\r\n") as f:
    f.write("Begin Map\n")
    for k, (x, y, z, tag) in enumerate(nodes):
        f.write("Begin Actor Class=PathNode Name=GenPath%d\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    Tag=Gen_%s\nEnd Actor\n"
                % (k, x, y, z, tag))
    f.write("End Map\n")

# connected parts of the walkable grid (4-neighbour): islands of nodes the AI can't reach
lab = np.zeros(Z.shape, int)
parts = []
for j in range(n):
    for i in range(w):
        if walk[j, i] and not lab[j, i]:
            parts.append(0)
            st = [(j, i)]
            lab[j, i] = len(parts)
            while st:
                cj, ci = st.pop()
                parts[-1] += 1
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q, p = cj + dj, ci + di
                    if 0 <= q < n and 0 <= p < w and walk[q, p] and not lab[q, p]:
                        lab[q, p] = len(parts)
                        st.append((q, p))
parts.sort(reverse=True)
tags = {t: sum(1 for v in nodes if v[3] == t) for t in ("ground", "cover", "high")}
print("nodes %d %s | walkable parts %d, largest %s | out %s" % (len(nodes), tags, len(parts), parts[:5], out))

try:
    from PIL import Image, ImageDraw
    S = 6
    land = Z > SEA_Z
    img = Image.new("RGB", (w * S, n * S), (20, 40, 70))
    d = ImageDraw.Draw(img)
    zl = Z[land]
    lo, hi = (zl.min(), zl.max()) if zl.size else (0, 1)
    for j in range(n):
        for i in range(w):
            if land[j, i]:
                v = int(60 + 140 * (Z[j, i] - lo) / max(1, hi - lo))
                col = (170, 40, 40) if built[j, i] else (v, v, v) if walk[j, i] else (v // 2, v // 3, v // 3)
                d.rectangle([i * S, (n - 1 - j) * S, i * S + S - 1, (n - 1 - j) * S + S - 1], fill=col)
    colr = {"ground": (255, 255, 255), "cover": (255, 220, 0), "high": (0, 230, 255)}
    for x, y, z, tag in nodes:
        fi, fj = cell(x, y)
        px, py = fi * S + S / 2, (n - 1 - fj) * S + S / 2
        r = 2 if tag == "ground" else 3
        d.ellipse([px - r, py - r, px + r, py + r], fill=colr[tag])
    img.save(os.path.splitext(out)[0] + ".png")
except ImportError:
    pass
