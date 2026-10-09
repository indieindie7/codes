r"""PathNodes for a generated town, in the pipeline (round 3, tools/HOOKS.md item 4): runs tools/pathnodes.py (another
chat's tool, read-only here) on a run folder and adds the STORY nodes it cannot see - a chain along the drain (on the
invert + Z_UP) and along the hero's truck road (ground + Z_UP) - so the AI can path through the culvert and up to the
temple. Reports the walkable parts pathnodes.py finds and which of them the story chains join.

    py tools/pathlinks.py <run folder> [out=<run>/isl_paths.t3d]

pathnodes.py needs <run>/isl_ec.bmp, isl_layout.json and isl_clutter.t3d; before the clutter step it is run in a temp
folder with an EMPTY clutter T3D (town.py runs it again after the clutter in a full build).
"""
import json, math, os, re, shutil, subprocess, sys, tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anchors  # noqa

Z_UP = 60.0                   # over the floor (pathnodes.py z=60: the player's CollisionHeight is 54)
DRAIN_STEP = 256.0            # UU between nodes in the culvert (its sections are 384 wide)
ROAD_STEP = 512.0             # ... and on the truck road (pathnodes' grid spacing)
LINK_M = 20.0                 # a story chain joins a walkable part when its end is within this of one of its cells


def _parts(run, L):
    """pathnodes.py's walkable mask and its 4-connected parts, recomputed (its labels are not exported):
    land + 50, within 6 cells of a building or a road, not a building cell, rise <= 0.9 x 512 to a 4-neighbour"""
    from scipy.ndimage import label, binary_dilation
    Z = anchors.load_heights(os.path.join(run, "isl_ec.bmp"))
    n = Z.shape[0]
    built = np.zeros_like(Z, bool)
    for b in L["buildings"].values():
        for i, j in b.get("cells", []):
            if 0 <= j < n and 0 <= i < n:
                built[j, i] = True
    rise = np.zeros_like(Z)
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rise = np.maximum(rise, np.abs(np.roll(np.roll(Z, dj, 0), di, 1) - Z))
    town = built.copy()
    for road in L.get("roads", []):
        for x, y in road:
            fi, fj = anchors.w2c(x, y)
            i, j = int(round(fi)), int(round(fj))
            if 0 <= i < n and 0 <= j < n:
                town[j, i] = True
    near = binary_dilation(town, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), iterations=6)
    walk = (Z > anchors.SEA_Z + 50) & ~built & (rise <= 0.9 * 512.0) & near
    walk[[0, -1], :] = walk[:, [0, -1]] = False
    lab, k = label(walk, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    return Z, lab, k


def _part_at(lab, x, y, within_m=LINK_M):
    """the part id of the walkable cell nearest (x, y) within within_m, else 0"""
    fi, fj = anchors.w2c(x, y)
    i0, j0 = int(round(fi)), int(round(fj))
    r = int(math.ceil(within_m / anchors.CELL_M)) + 1
    best = (1e9, 0)
    for j in range(max(0, j0 - r), min(lab.shape[0], j0 + r + 1)):
        for i in range(max(0, i0 - r), min(lab.shape[1], i0 + r + 1)):
            if lab[j, i]:
                wx, wy = anchors.c2w(i, j)
                d = math.hypot(wx - x, wy - y) / anchors.M
                if d <= within_m and d < best[0]:
                    best = (d, int(lab[j, i]))
    return best[1]


def story_nodes(L, Z):
    """[(x, y, z, tag)] along the drain (on its invert) and the hero's truck road (the branch ending at the hero)"""
    out = []
    dr = L.get("drain")
    if dr and dr.get("path"):
        acc = 0.0
        last = None
        for x, y, gz, iv in dr["path"]:
            if last is not None:
                acc += math.hypot(x - last[0], y - last[1])
            if last is None or acc >= DRAIN_STEP:
                out.append((x, y, iv + Z_UP, "drain"))
                acc = 0.0
            last = (x, y)
        if out and (out[-1][0], out[-1][1]) != tuple(dr["path"][-1][:2]):
            x, y, gz, iv = dr["path"][-1]
            out.append((x, y, iv + Z_UP, "drain"))
    hero = anchors.PARTI_HERO
    B = L["buildings"]
    if hero in B:
        hx, hy = B[hero]["x"], B[hero]["y"]
        roads = L.get("roads", [])
        cls = L.get("road_class") or ["spine"] + ["branch"] * (len(roads) - 1)
        cand = [(min(math.hypot(r[0][0] - hx, r[0][1] - hy), math.hypot(r[-1][0] - hx, r[-1][1] - hy)), k)
                for k, r in enumerate(roads) if cls[k] != "path" and len(r) > 1]
        if cand:
            d, k = min(cand)
            if d <= 60 * anchors.M:                       # the road ends at the plinth's foot
                r = roads[k]
                acc = 0.0
                last = None
                for x, y in r:
                    if last is not None:
                        acc += math.hypot(x - last[0], y - last[1])
                    if last is None or acc >= ROAD_STEP:
                        out.append((x, y, anchors.zat(Z, x, y) + Z_UP, "truckroad"))
                        acc = 0.0
                    last = (x, y)
                if (out[-1][0], out[-1][1]) != tuple(r[-1]):
                    out.append((r[-1][0], r[-1][1], anchors.zat(Z, *r[-1]) + Z_UP, "truckroad"))
    return out


def run(run_dir, out=None, clutter=None):
    """pathnodes.py on the run folder (+ the story chains). Returns the report dict (also written to <run>/paths.txt)"""
    out = out or os.path.join(run_dir, "isl_paths.t3d")
    L = json.load(open(os.path.join(run_dir, "isl_layout.json")))
    clutter = clutter or os.path.join(run_dir, "isl_clutter.t3d")
    tool = os.path.join(HERE, "pathnodes.py")
    tmp = None
    if os.path.exists(clutter):
        src = run_dir
    else:                                                 # before the clutter step: an empty clutter T3D in a temp folder
        tmp = tempfile.mkdtemp(prefix="paths_")
        for f in ("isl_ec.bmp", "isl_layout.json"):
            shutil.copy(os.path.join(run_dir, f), tmp)
        open(os.path.join(tmp, "isl_clutter.t3d"), "w").write("Begin Map\nEnd Map\n")
        src = tmp
    r = subprocess.run(["py", tool, src, "out=" + out], capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or [""])[-1]
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    m = re.search(r"nodes (\d+) (\{.*?\}) \| walkable parts (\d+), largest (\[.*?\])", line)
    rep = {"nodes": int(m.group(1)) if m else None, "parts": int(m.group(3)) if m else None,
           "largest": json.loads(m.group(4)) if m else None, "line": line or r.stderr.strip()[-300:],
           "clutter": "with the clutter" if not tmp else "before the clutter (empty T3D)"}
    # the story chains, appended to the T3D
    Z, lab, k = _parts(run_dir, L)
    nodes = story_nodes(L, Z)
    if nodes:
        txt = open(out, encoding="utf-8", errors="replace").read()
        body = "".join("Begin Actor Class=PathNode Name=GenStory%d\r\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\r\n    Tag=Gen_%s\r\nEnd Actor\r\n"
                       % (i, x, y, z, tag) for i, (x, y, z, tag) in enumerate(nodes))
        txt = txt.replace("End Map", body + "End Map", 1) if "End Map" in txt else txt + body
        open(out, "w", newline="").write(txt)
    rep["story_nodes"] = {t: sum(1 for v in nodes if v[3] == t) for t in ("drain", "truckroad")}
    # which parts do the chains join? (each chain's two ends -> the part they touch)
    joins = []
    for tag in ("drain", "truckroad"):
        ch = [v for v in nodes if v[3] == tag]
        if len(ch) < 2:
            continue
        a, b = _part_at(lab, ch[0][0], ch[0][1]), _part_at(lab, ch[-1][0], ch[-1][1])
        joins.append({"chain": tag, "ends_in_parts": [a, b], "joins": bool(a and b and a != b)})
    rep["parts_recomputed"] = int(k)
    merged = set()
    for j in joins:
        if j["joins"]:
            merged.add(tuple(sorted(j["ends_in_parts"])))
    rep["parts_after_links"] = int(k) - len(merged)
    rep["joins"] = joins
    rep["out"] = out
    open(os.path.join(run_dir, "paths.txt"), "w", encoding="utf-8").write(json.dumps(rep, indent=1))
    return rep


def summary(rep):
    return "pathnodes: %s nodes, %s walkable parts (largest %s), %s; story chains: %d drain + %d truck-road nodes, %s -> %s parts" % (
        rep["nodes"], rep["parts"], rep["largest"], rep["clutter"], rep["story_nodes"]["drain"], rep["story_nodes"]["truckroad"],
        ", ".join("%s %s parts %s" % (j["chain"], "joins" if j["joins"] else "stays in", "-".join(str(p) for p in j["ends_in_parts"])) for j in rep["joins"]) or "no chains",
        rep["parts_after_links"])


if __name__ == "__main__":
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    print(summary(run(sys.argv[1], o.get("out"))))
