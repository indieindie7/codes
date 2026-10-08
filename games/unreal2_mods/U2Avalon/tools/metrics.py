r"""Believability metrics for a town layout (Q35, 2026-10-08; games/research_notes/Believable city simulation, s. 11):
two scores from the layout JSON alone, to compare a layout before and after each simulation pass.

    py tools/metrics.py <layout.json> [more layouts...]      -> prints IMP and HIER (+ their terms) per layout

IMP (imperfection, 0..1): real frontage is irregular - gap CV, party-wall share (gaps < 1 m), setback CV, yaw
    spread off the road normal, and that spread's lag-1 autocorrelation along a row (a coherent wobble, not noise).
HIER (hierarchy + time, 0..1): a few busy streets and many quiet ones (Gini of length-weighted edge betweenness),
    10-30 % dead ends, loops (E - V + C), street-bearing entropy in the organic band (Boeing 2019: ~3.0-3.6 nats),
    and an older core (Spearman of building age vs network distance from the dock, negative).
Targets are the report's proposals: tune them against real references.
"""
import json, math, os, sys
from collections import defaultdict, deque

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
M = 50.0                                   # units per metre
LAYER_AGE = {"core": 0, "boom": 1, "decline": 2}


def clip01(v):
    return float(min(max(v, 0.0), 1.0))


def band(v, lo, hi, soft=0.1):
    """1 inside [lo, hi], falling off linearly over soft*(hi-lo)... outside"""
    w = max(1e-6, (hi - lo) * 0.5 + soft)
    if lo <= v <= hi:
        return 1.0
    return clip01(1 - (lo - v if v < lo else v - hi) / w)


# ---- the road graph: polyline vertices as nodes (shared coordinates = junctions), segments as edges
def road_graph(L):
    key = {}
    pos = []
    edges = {}

    def node(p):
        k = (round(p[0] / 25), round(p[1] / 25))          # vertices within ~25 units are one node (branch roots)
        if k not in key:
            key[k] = len(pos)
            pos.append((float(p[0]), float(p[1])))
        return key[k]

    for r in L["roads"]:
        pts = r["pts"] if isinstance(r, dict) else r
        ids = [node(p) for p in pts]
        for a, b in zip(ids[:-1], ids[1:]):
            if a != b:
                edges[(min(a, b), max(a, b))] = math.dist(pos[a], pos[b])
    # a branch starting ON a spine segment (not at a vertex): split that segment at the branch root
    adj = defaultdict(dict)
    for (a, b), w in edges.items():
        adj[a][b] = w
        adj[b][a] = w
    for n in range(len(pos)):
        if len(adj[n]) == 1:                                # a road end: does it touch another road's segment?
            for (a, b), w in list(edges.items()):
                if n in (a, b):
                    continue
                pa, pb, p = np.array(pos[a]), np.array(pos[b]), np.array(pos[n])
                t = np.clip(np.dot(p - pa, pb - pa) / max(1e-6, np.dot(pb - pa, pb - pa)), 0, 1)
                if np.linalg.norm(pa + t * (pb - pa) - p) < 60:
                    del edges[(a, b)]
                    for c in (a, b):
                        edges[(min(c, n), max(c, n))] = math.dist(pos[c], pos[n])
                    break
    adj = defaultdict(dict)
    for (a, b), w in edges.items():
        adj[a][b] = w
        adj[b][a] = w
    return pos, edges, adj


def dijkstra(adj, src):
    import heapq
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18):
            continue
        for v, w in adj[u].items():
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def edge_betweenness(adj, nodes):
    """Brandes, weighted (Dijkstra), on our small graphs"""
    import heapq
    eb = defaultdict(float)
    for s in nodes:
        S, P, sigma, dist = [], defaultdict(list), defaultdict(float), {}
        sigma[s] = 1.0
        dist[s] = 0.0
        pq = [(0.0, s, s)]
        seen = {}
        while pq:
            d, pred, v = heapq.heappop(pq)
            if v in seen:
                continue
            seen[v] = d
            S.append(v)
            for w, l in adj[v].items():
                nd = d + l
                if w not in seen and (w not in dist or nd < dist[w] - 1e-9):
                    dist[w] = nd
                    sigma[w] = sigma[v]
                    P[w] = [v]
                    heapq.heappush(pq, (nd, v, w))
                elif w not in seen and abs(nd - dist[w]) < 1e-9:
                    sigma[w] += sigma[v]
                    P[w].append(v)
        delta = defaultdict(float)
        while S:
            w = S.pop()
            for v in P[w]:
                c = sigma[v] / max(sigma[w], 1e-12) * (1 + delta[w])
                eb[(min(v, w), max(v, w))] += c
                delta[v] += c
    return eb


def gini(x, w=None):
    x = np.asarray(x, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    if len(x) < 2 or x.sum() <= 0:
        return 0.0
    o = np.argsort(x)
    x, w = x[o], w[o]
    cw = np.cumsum(w) / w.sum()
    cxw = np.cumsum(x * w) / (x * w).sum()
    return float(1 - np.sum((cxw[1:] + cxw[:-1]) * np.diff(cw)) - cxw[0] * cw[0])


def spearman(a, b):
    if len(a) < 3:
        return 0.0
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


# ---- IMP: per road side, plots ordered along the road
def road_point(pts, s):
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        if acc + L >= s or b is pts[-1]:
            t = 0 if L == 0 else min(max((s - acc) / L, 0), 1)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / max(L, 1e-6), (b[1] - a[1]) / max(L, 1e-6))
        acc += L
    return pts[-1], (1.0, 0.0)


def imperfection(L):
    roads = {}
    names = ["spine"] + ["branch%d" % k for k in range(1, len(L["roads"]))]
    for k, r in enumerate(L["roads"]):
        nm = r.get("name", names[k]) if isinstance(r, dict) else names[k]
        roads[nm] = r["pts"] if isinstance(r, dict) else r
    rows = defaultdict(list)
    for p in L.get("plots", []):
        rows[(p["road"], p["side"])].append(p)
    gaps, setbacks, devs, acs = [], [], [], []
    for (rn, side), ps in rows.items():
        ps.sort(key=lambda p: p["s0"])
        pts = roads.get(rn)
        if not pts:
            continue
        g = [max(0.0, (b["s0"] - a["s1"]) / M) for a, b in zip(ps[:-1], ps[1:])]
        gaps += [v for v in g if v < 60]                 # neighbours (a long empty stretch is not a gap)
        d = []
        for p in ps:
            setbacks.append(p.get("setback", 4.0))
            b = L["buildings"].get(p["id"])
            if b is None:
                continue
            (_, _), (ux, uy) = road_point(pts, (p["s0"] + p["s1"]) / 2)
            nx, ny = (-uy, ux) if side > 0 else (uy, -ux)
            normal = math.degrees(math.atan2(-ny, -nx))
            d.append((b["yaw"] - normal + 180) % 360 - 180)
        devs += d
        if len(d) >= 3:
            dd = np.array(d) - np.mean(d)
            if dd[:-1].std() > 0.5 and dd[1:].std() > 0.5:          # degrees: the JSON rounds yaw to 0.1
                acs.append(float(np.corrcoef(dd[:-1], dd[1:])[0, 1]))
    gaps = np.array(gaps) if gaps else np.zeros(1)
    t = {
        "gap_cv": float(gaps.std() / max(gaps.mean(), 1e-6)),
        "party": float((gaps < 1.0).mean()),
        "setback_cv": float(np.std(setbacks) / max(np.mean(setbacks), 1e-6)) if setbacks else 0.0,
        "yaw_dev": float(np.std(devs)) if devs else 0.0,
        "yaw_ac": float(np.mean(acs)) if acs else 0.0,
    }
    imp = np.mean([clip01(t["gap_cv"] / 0.5), clip01(t["party"] / 0.25), clip01(t["setback_cv"] / 0.3),
                   clip01(t["yaw_dev"] / 5.0), clip01(t["yaw_ac"] / 0.4)])
    return float(imp), t


def hierarchy(L):
    pos, edges, adj = road_graph(L)
    nodes = list(adj.keys())
    V, E = len(nodes), len(edges)
    # components
    seen, C = set(), 0
    for n in nodes:
        if n in seen:
            continue
        C += 1
        q = deque([n])
        seen.add(n)
        while q:
            u = q.popleft()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
    loops = E - V + C
    # dead ends: degree-1 nodes among the "decision" nodes (ends + junctions; road-interior vertices don't count)
    deg = {n: len(adj[n]) for n in nodes}
    decision = [n for n in nodes if deg[n] != 2]
    dead_share = sum(1 for n in decision if deg[n] == 1) / max(1, len(decision))
    eb = edge_betweenness(adj, nodes)
    lens = np.array([edges[e] for e in edges])
    gini_choice = gini([eb.get(e, 0.0) for e in edges], lens)
    # bearing entropy (Boeing): both directions, 36 bins, length-weighted
    hist = np.zeros(36)
    for (a, b), w in edges.items():
        brg = math.degrees(math.atan2(pos[b][1] - pos[a][1], pos[b][0] - pos[a][0])) % 360
        for x in (brg, (brg + 180) % 360):
            hist[int(x // 10) % 36] += w
    p = hist / max(hist.sum(), 1e-9)
    entropy = float(-(p[p > 0] * np.log(p[p > 0])).sum())
    # age vs network distance from the dock
    age_rho = 0.0
    try:
        import binder
        _, B = binder.load()
        dock = L.get("sites", {}).get("dock")
        if dock is not None:
            dn = min(nodes, key=lambda n: math.dist(pos[n], dock))
            dist = dijkstra(adj, dn)
            ages, dd = [], []
            for bid, b in L["buildings"].items():
                lay = (b.get("layer") or B.get(bid, {}).get("layer"))
                if lay not in LAYER_AGE:
                    continue
                n = min(nodes, key=lambda n: math.dist(pos[n], (b["x"], b["y"])))
                if n in dist:
                    ages.append(b.get("age", LAYER_AGE[lay]))
                    dd.append(dist[n] + math.dist(pos[n], (b["x"], b["y"])))
            # older (age 0) near the dock: age rises with distance -> positive rho; we want "older = nearer", so the
            # report's "age_rho <= -0.4" is in terms of building AGE (years); our age is an epoch index (0 = oldest)
            age_rho = -spearman(ages, dd)
    except Exception as e:                                    # binder not loadable here: skip the term
        print("  (age term skipped: %s)" % e)
    t = {"gini_choice": gini_choice, "dead_share": dead_share, "loops": loops, "entropy": entropy, "age_rho": age_rho,
         "nodes": V, "edges": E}
    hier = np.mean([clip01(gini_choice / 0.5), band(dead_share, 0.1, 0.3), clip01(loops / 3.0), band(entropy, 3.0, 3.6),
                    clip01(-age_rho / 0.4)])
    return float(hier), t


def score(path):
    L = json.load(open(path))
    imp, ti = imperfection(L)
    hier, th = hierarchy(L)
    return {"IMP": imp, "HIER": hier, **{k: round(v, 3) if isinstance(v, float) else v for k, v in {**ti, **th}.items()}}


if __name__ == "__main__":
    for f in sys.argv[1:]:
        r = score(f)
        print("%s\n  IMP %.2f  (gap_cv %.2f, party %.2f, setback_cv %.2f, yaw_dev %.1f deg, yaw_ac %.2f)\n"
              "  HIER %.2f (gini_choice %.2f, dead_share %.2f, loops %d, entropy %.2f, age_rho %.2f; %d nodes %d edges)" % (
                  os.path.basename(f), r["IMP"], r["gap_cv"], r["party"], r["setback_cv"], r["yaw_dev"], r["yaw_ac"],
                  r["HIER"], r["gini_choice"], r["dead_share"], r["loops"], r["entropy"], r["age_rho"], r["nodes"], r["edges"]))
