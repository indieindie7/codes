# ResPlan statistics for a building-interiors skill: room sizes and shapes, connections,
# windows, depth from the entrance. Usage: python3 -I analyse.py ResPlan.pkl split.json out.json
import sys, json, math, statistics as st
from collections import Counter, defaultdict
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load
from shapely.ops import unary_union

ROOMS = ["living", "bedroom", "bathroom", "kitchen", "storage", "stair", "balcony"]

def parts(g):
    if g is None or g.is_empty:
        return []
    return [x for x in (g.geoms if hasattr(g, "geoms") else [g]) if x.area > 0]

def rect(g):
    r = g.minimum_rotated_rectangle
    c = list(r.exterior.coords)
    a, b = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    return min(a, b), max(a, b), r.area

def main(pkl, split, out):
    data = load(pkl)
    sp = json.load(open(split))
    keep = set(sp["train"]) | set(sp["val"]) | set(sp["test"])
    room_area = defaultdict(list); room_short = defaultdict(list); room_aspect = defaultdict(list)
    room_rectish = defaultdict(list); room_window = defaultdict(lambda: [0, 0]); window_w = defaultdict(list)
    door_pairs = Counter(); open_pairs = Counter(); wall_pairs = Counter(); entry = Counter()
    depth = defaultdict(list); ensuite = [0, 0]
    by_bed = defaultdict(lambda: defaultdict(list)); doors_w = []; front_w = []; wall_t = []
    plans = 0
    dropped = 0
    for p in data:
        if p.get("id") not in keep:
            continue
        geoms = [p[k] for k in ROOMS[:6] if k in p and p[k] is not None and not p[k].is_empty]
        ua = unary_union(geoms).area if geoms else 0
        if ua <= 0 or not p.get("net_area"):
            continue
        s = math.sqrt(float(p["net_area"]) / ua)          # metres per unit
        wd = float(p.get("wall_depth") or 4.0)
        # the listed area is sometimes wrong (sqft, gross, a typo): trust the scale only when the
        # plan's own doors come out at door size
        dws = sorted(rect(d)[1] * s for d in parts(p.get("door")))
        if len(dws) < 2 or not (0.7 <= dws[len(dws) // 2] <= 1.05):
            dropped += 1
            continue
        plans += 1
        wall_t.append(wd * s)
        rooms = []
        for k in ROOMS:
            for g in parts(p.get(k)):
                rooms.append((k, g))
        wins = parts(p.get("window"))
        for k, g in rooms:
            short, long_, ra = rect(g)
            room_area[k].append(g.area * s * s)
            room_short[k].append(short * s)
            room_aspect[k].append(long_ / max(short, 1e-6))
            room_rectish[k].append(g.area / max(ra, 1e-9))
            # a window in this room's own wall: its wall-thick strip overlaps the room's edge
            near = [w for w in wins if w.distance(g) < wd * 0.6 and w.buffer(wd * 0.7).intersection(g).area > 0.3 * rect(w)[1] * wd * 0.7]
            room_window[k][0] += 1
            if near:
                room_window[k][1] += 1
                for w in near:
                    window_w[k].append(rect(w)[1] * s)
        # connections
        n = len(rooms)
        adj = defaultdict(set)
        door_edge = set()
        for d in parts(p.get("door")):
            doors_w.append(rect(d)[1] * s)
            hit = [i for i, (_, g) in enumerate(rooms) if g.distance(d) < wd * 0.75]
            if len(hit) == 2:
                i, j = hit
                door_edge.add((min(i, j), max(i, j)))
        for i in range(n):
            for j in range(i + 1, n):
                gi, gj = rooms[i][1], rooms[j][1]
                dist = gi.distance(gj)
                if dist > wd * 1.6:
                    continue
                shared = gi.buffer(wd * 0.9).intersection(gj.buffer(wd * 0.9)).area / (wd * 1.8) * s
                if shared < 0.5:
                    continue
                pair = tuple(sorted((rooms[i][0], rooms[j][0])))
                if (i, j) in door_edge:
                    door_pairs[pair] += 1
                    adj[i].add(j); adj[j].add(i)
                elif dist < wd * 0.3:
                    open_pairs[pair] += 1                     # no wall between: open plan
                    adj[i].add(j); adj[j].add(i)
                else:
                    wall_pairs[pair] += 1
        # ensuite: a bathroom whose only door leads to a bedroom
        for i, (k, g) in enumerate(rooms):
            if k != "bathroom":
                continue
            ensuite[0] += 1
            nb = [rooms[j][0] for j in adj[i]]
            if nb and all(t == "bedroom" for t in nb):
                ensuite[1] += 1
        # entrance and depth (steps through doors and openings)
        fd = p.get("front_door")
        start = None
        if fd is not None and not fd.is_empty:
            cand = [(g.distance(fd), i) for i, (_, g) in enumerate(rooms) if g.distance(fd) < wd * 1.0]
            if cand:
                start = min(cand)[1]
                entry[rooms[start][0]] += 1
        if start is not None:
            dist = {start: 0}; q = [start]
            while q:
                c = q.pop(0)
                for nb in adj[c]:
                    if nb not in dist:
                        dist[nb] = dist[c] + 1; q.append(nb)
            for i, dd in dist.items():
                depth[rooms[i][0]].append(dd)
        nbed = sum(1 for k, _ in rooms if k == "bedroom")
        by_bed[nbed]["net_area"].append(float(p["net_area"]))
        by_bed[nbed]["bathrooms"].append(sum(1 for k, _ in rooms if k == "bathroom"))
        by_bed[nbed]["rooms"].append(len(rooms))
    def pct(a, qs=(10, 25, 50, 75, 90)):
        a = sorted(a)
        return {f"p{q}": round(a[min(len(a) - 1, int(len(a) * q / 100))], 2) for q in qs} if a else {}
    res = {"plans": plans, "dropped_bad_scale": dropped, "rooms": {}, "doors_m": pct(doors_w), "wall_thickness_m": pct(wall_t),
           "door_pairs": door_pairs.most_common(), "open_pairs": open_pairs.most_common(),
           "wall_pairs": wall_pairs.most_common(), "entry_room": entry.most_common(),
           "ensuite_share": round(ensuite[1] / max(ensuite[0], 1), 3), "by_bedrooms": {}}
    for k in ROOMS:
        if not room_area[k]:
            continue
        res["rooms"][k] = {"count": len(room_area[k]), "area_m2": pct(room_area[k]), "short_side_m": pct(room_short[k]),
                           "aspect": pct(room_aspect[k]), "rectangular_fill": pct(room_rectish[k]),
                           "window_share": round(room_window[k][1] / max(room_window[k][0], 1), 3),
                           "window_width_m": pct(window_w[k]),
                           "depth_from_entry": pct(depth[k]) if depth[k] else {},
                           "mean_depth": round(st.mean(depth[k]), 2) if depth[k] else None}
    for nb in sorted(by_bed):
        v = by_bed[nb]
        if len(v["net_area"]) < 30:
            continue
        res["by_bedrooms"][nb] = {"plans": len(v["net_area"]), "net_area_m2": pct(v["net_area"]),
                                  "bathrooms_median": st.median(v["bathrooms"]), "rooms_median": st.median(v["rooms"])}
    json.dump(res, open(out, "w"), indent=1, default=lambda o: list(o) if isinstance(o, tuple) else str(o))
    print("plans", plans)

if __name__ == "__main__":
    main(*sys.argv[1:4])
