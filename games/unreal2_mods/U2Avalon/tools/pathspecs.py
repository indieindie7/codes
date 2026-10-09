r"""ReachSpecs computed in Python, so the editor never has to run PATHS DEFINE (research_notes/Lighter AI pathing for
UE2, Route A, tested 2026-10-09: ReachSpecs written inline in a PathNode's T3D import and survive a save; the map
loads once LevelInfo.PathsRebuiltStamp is set back to the last define's value).

    py tools/pathspecs.py <run folder> [nodes=<run>\isl_paths.t3d] [out=<run>\isl_paths_specs.t3d] [step=32]
                          [rise=35] [slope=1.0] [radius=60] [height=96] [prune=1.2] [max=1200]

For every ordered pair of nodes closer than `max` (the engine's own 1200 UU limit), walk the straight segment on the
graded heightmap (isl_ec.bmp) every `step` UU and keep the pair when:
  - no step rises more than `rise` UU (the AI's step height 35) beyond what the slope allows, and the ground's slope
    stays under `slope` (rise per run; ~45 degrees, the engine's walkable floor),
  - the segment never crosses a building's cells (isl_layout.json) or the sea,
  - both ends sit on land.
Then prune like the engine (FPathBuilder PrunePaths, factor 1.2): drop A->B when some C has A->C and C->B whose
summed length is <= prune x |AB|. Each kept spec is written as walk-only (reachFlags=1) at radius/height (60/96, the
size that fits Pawn's default 34/78 and every smaller NPC).

Writes the nodes again (same names, locations and tags) with their ReachSpec objects inline and PathList(n) entries.
Import it INSTEAD of the plain node T3D, then `!setprop LevelInfo0 PathsRebuiltStamp <n>` before saving (remake_build
stage=specs). Conservative on purpose: a missing spec only makes the AI walk around; a wrong one gets it stuck.
Not modelled: clutter collision (crates, fences), interiors (the shells), jumps and drops (walk only).
"""
import json, math, os, re, struct, sys
import numpy as np

LOC = (-14487.546875, 4835.837891, -131.845703)
SCALE = (512.0, 512.0, 128.0)
SEA_Z = -4967.0

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
RUN = args[0]
NODES = o.get("nodes", os.path.join(RUN, "isl_paths.t3d"))
OUT = o.get("out", os.path.join(RUN, "isl_paths_specs.t3d"))
STEP, RISE, SLOPE = float(o.get("step", 32)), float(o.get("rise", 35)), float(o.get("slope", 1.0))
RAD, HGT, PRUNE, MAXD = float(o.get("radius", 60)), float(o.get("height", 96)), float(o.get("prune", 1.2)), float(o.get("max", 1200))

raw = open(os.path.join(RUN, "isl_ec.bmp"), "rb").read()
off = struct.unpack_from("<I", raw, 10)[0]
w, h = struct.unpack_from("<ii", raw, 18)
H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(np.float64)
if h > 0:
    H = H[::-1]
Z = LOC[2] + (H - 32768) * SCALE[2] / 256
n = Z.shape[0]


def ground(x, y):
    fi, fj = (x - LOC[0]) / SCALE[0] + w / 2, (y - LOC[1]) / SCALE[1] + n / 2
    i0 = np.clip(np.floor(fi).astype(int), 0, w - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, n - 2)
    u, v = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    return (Z[j0, i0] * (1 - u) * (1 - v) + Z[j0, i0 + 1] * u * (1 - v) + Z[j0 + 1, i0] * (1 - u) * v
            + Z[j0 + 1, i0 + 1] * u * v)


L = json.load(open(os.path.join(RUN, "isl_layout.json")))
built = np.zeros((n, w), bool)
for b in L["buildings"].values():
    for i, j in b.get("cells", []):
        if 0 <= j < n and 0 <= i < w:
            built[j, i] = True


def cells(x, y):
    i = np.clip(np.round((x - LOC[0]) / SCALE[0] + w / 2).astype(int), 0, w - 1)
    j = np.clip(np.round((y - LOC[1]) / SCALE[1] + n / 2).astype(int), 0, n - 1)
    return i, j


txt = open(NODES, encoding="utf-8", errors="replace").read()
blocks = re.findall(r"Begin Actor Class=(\w+) Name=(\w+)(.*?)End Actor", txt, re.S)
nodes = []
for cls, name, body in blocks:
    m = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", body)
    if m:
        nodes.append({"cls": cls, "name": name, "body": body, "p": tuple(map(float, m.groups()))})
P = np.array([nd["p"] for nd in nodes])
N = len(nodes)


def walkable(a, b):
    d2 = math.hypot(b[0] - a[0], b[1] - a[1])
    k = max(2, int(d2 / STEP) + 1)
    t = np.linspace(0, 1, k)
    xs, ys = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    g = ground(xs, ys)
    if (g <= SEA_Z + 40).any():
        return False
    i, j = cells(xs, ys)
    if built[j, i][1:-1].any():
        return False
    dz = np.abs(np.diff(g))
    run = d2 / (k - 1)
    return bool((dz <= SLOPE * run + 0.0).all() and (dz <= RISE + SLOPE * run).all())


specs = {}
for a in range(N):
    d = np.linalg.norm(P - P[a], axis=1)
    for b in np.nonzero((d > 1) & (d < MAXD))[0]:
        if walkable(P[a], P[b]):
            specs[(a, int(b))] = float(d[b])
raw_n = len(specs)

# prune (one pass, like the engine: an indirect route at most PRUNE x as long makes the direct spec redundant)
out_of = {}
for (a, b), dist in specs.items():
    out_of.setdefault(a, {})[b] = dist
pruned = set()
for (a, b), dist in specs.items():
    for c, d_ac in out_of.get(a, {}).items():
        if c != b and (c, b) in specs and (a, c) not in pruned and (c, b) not in pruned and d_ac + specs[(c, b)] <= PRUNE * dist:
            pruned.add((a, b))
            break
kept = {k: v for k, v in specs.items() if k not in pruned}

lines = ["Begin Map"]
for a, nd in enumerate(nodes):
    lines.append("Begin Actor Class=%s Name=%s" % (nd["cls"], nd["name"]))
    body = nd["body"].strip("\n")
    lines += [l for l in body.splitlines() if l.strip() and not l.strip().startswith("PathList")]
    k = 0
    for (s, e), dist in sorted(kept.items()):
        if s != a:
            continue
        sn = "Spec_%s_%s" % (nd["name"], nodes[e]["name"])
        lines += ["    Begin Object Class=ReachSpec Name=%s" % sn,
                  "        Distance=%d" % round(dist),
                  "        Start=%s'MyLevel.%s'" % (nd["cls"], nd["name"]),
                  "        End=%s'MyLevel.%s'" % (nodes[e]["cls"], nodes[e]["name"]),
                  "        CollisionRadius=%d" % RAD,
                  "        CollisionHeight=%d" % HGT,
                  "        reachFlags=1",
                  "    End Object",
                  "    PathList(%d)=ReachSpec'MyLevel.%s'" % (k, sn)]
        k += 1
    lines.append("End Actor")
lines.append("End Map")
open(OUT, "w", newline="\r\n").write("\n".join(lines) + "\n")

deg = np.bincount([s for s, _ in kept], minlength=N)
iso = int((deg == 0).sum())
print("pathspecs: %d nodes, %d candidate pairs walkable -> %d after pruning (%.1f per node, %d with none) -> %s"
      % (N, raw_n, len(kept), len(kept) / max(N, 1), iso, OUT))
