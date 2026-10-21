"""Cross-map curriculum order from game trajectories (10-21, 3Blue1Brown cross-entropy lesson).

Each map's games become a bag of map-independent "situation" tokens (per officer per frame: distance to the nearest
live suspect, live suspects within 1500 uu, officer speed, mission phase; plus kill/arrest/officer-down events).
Q_A = smoothed token distribution of map A. Transfer cost A -> B = KL(P_B || Q_A) = cross-entropy H(P_B, Q_A) - H(P_B):
the extra bits per token a model of A wastes on B (the "language trees and zipping" trick, with counts not gzip).

Order: start from the maps already trained; repeatedly add the locked map with the lowest
z(KL from the trained mixture) + DIFF_W * z(difficulty), difficulty = - mean game score on that map.

CLI: py -3.13 -I tools/swat4_maporder.py [--active N] [--maps a,b,...]  -> prints KL matrix + order, writes OUT/maporder.json
"""
import argparse
import json
import math
from collections import Counter
from pathlib import Path

OUT = Path(r"C:/Users/john/Documents/SwatMindsGym/autogym")
MAX_GAMES = 30   # most recent traj files per map (active maps have 150+, locked ones ~10)
ALPHA = 0.5      # additive smoothing per token
DIFF_W = 1.0     # weight of difficulty vs similarity in the greedy pick


def bucket(v, edges):
    for i, e in enumerate(edges):
        if v < e:
            return i
    return len(edges)


def game_tokens(path):
    frames = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    frames = [f for f in frames if "pawns" in f]
    out, prev = [], None
    for f in frames:
        P = f["pawns"]
        E = {k: v for k, v in P.items() if k[0] == "E"}
        live = [v for v in E.values() if v[3] == "c"]
        phase = bucket(1 - len(live) / len(E), (0.01, 0.34, 0.67)) if E else 0
        dt = max(0.1, f["t"] - prev["t"]) if prev else 1.0
        for k, o in P.items():
            if k[0] != "O" or o[3] != "c":
                continue
            d = min((math.hypot(o[0] - e[0], o[1] - e[1]) for e in live), default=1e9)
            near = sum(1 for e in live if math.hypot(o[0] - e[0], o[1] - e[1]) < 1500)
            po = prev["pawns"].get(k) if prev else None
            sp = math.hypot(o[0] - po[0], o[1] - po[1]) / dt if po else 0.0
            out.append(f"d{bucket(d, (400, 800, 1500, 3000))}n{min(near, 3)}s{bucket(sp, (20, 150))}p{phase}")
        if prev:
            for k, v in P.items():
                pv = prev["pawns"].get(k)
                if pv and pv[3] == "c" and v[3] != "c":
                    out.append(f"ev{k[0]}{v[3]}")  # evEd suspect down, evEa arrested, evOd officer down, evHa ...
        prev = f
    return out


def map_counts(m):
    files = sorted((OUT / "engine" / m).glob("search_logs/*/*.traj.jsonl"), key=lambda p: p.stat().st_mtime)[-MAX_GAMES:]
    c = Counter()
    for p in files:
        c.update(game_tokens(p))
    return c, len(files)


def difficulty(m):
    f = OUT / "engine" / m / "data.jsonl"
    if not f.exists():
        return None
    sc = [r["score"] for r in (json.loads(l) for l in f.read_text().splitlines() if l.strip()) if r.get("score") is not None]
    return -sum(sc) / len(sc) if sc else None


def kl(p, q, vocab):
    """KL(P || Q) in bits per token, both smoothed over the shared vocab."""
    np_, nq = sum(p.values()) + ALPHA * len(vocab), sum(q.values()) + ALPHA * len(vocab)
    return sum(((p[t] + ALPHA) / np_) * math.log2(((p[t] + ALPHA) / np_) / ((q[t] + ALPHA) / nq)) for t in vocab)


def z(xs):
    mu = sum(xs) / len(xs)
    sd = (sum((x - mu) ** 2 for x in xs) / len(xs)) ** 0.5 or 1.0
    return [(x - mu) / sd for x in xs]


def order(maps, n_active, log=print):
    """returns (new order, info). The first n_active maps keep their place; the rest are re-ordered."""
    C = {m: map_counts(m) for m in maps}
    usable = [m for m in maps if C[m][1] > 0]
    vocab = set().union(*(C[m][0] for m in usable))
    done = list(maps[:n_active])
    rest = [m for m in maps[n_active:] if m in usable]
    tail = [m for m in maps[n_active:] if m not in usable]  # no games yet: keep hand order at the end
    D = {m: difficulty(m) for m in maps}
    picks = []
    while rest:
        mix = Counter()
        for m in done:  # each trained map weighs the same in the mixture, however many games it has
            tot = sum(C[m][0].values()) or 1
            mix.update({t: 1000.0 * v / tot for t, v in C[m][0].items()})
        ks = [kl(C[m][0], mix, vocab) for m in rest]
        ds = [D[m] if D[m] is not None else max(d for d in D.values() if d is not None) for m in rest]
        cost = [a + DIFF_W * b for a, b in zip(z(ks), z(ds))] if len(rest) > 1 else [0.0]
        i = min(range(len(rest)), key=cost.__getitem__)
        picks.append(dict(map=rest[i], kl=round(ks[i], 3), diff=round(ds[i], 2), cost=round(cost[i], 2)))
        done.append(rest.pop(i))
    new = done + tail
    info = dict(order=new, picks=picks, games={m: C[m][1] for m in maps},
                kl_matrix={a: {b: round(kl(C[b][0], C[a][0], vocab), 3) for b in usable} for a in usable})
    (OUT / "maporder.json").write_text(json.dumps(info, indent=1))
    return new, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", default=None, help="comma list; default = the autogym --maps order in curriculum.json")
    ap.add_argument("--active", type=int, default=None)
    a = ap.parse_args()
    cur = json.loads((OUT / "curriculum.json").read_text())
    maps = a.maps.split(",") if a.maps else cur["maps"]
    new, info = order(maps, a.active if a.active is not None else cur["active"])
    us = list(info["kl_matrix"])
    short = [m.replace("SP-", "")[:6] for m in us]
    print("KL(P_col || Q_row) bits/token, row = trained map\n" + " " * 8 + " ".join(f"{s:>6}" for s in short))
    for m, s in zip(us, short):
        print(f"{s:>7} " + " ".join(f"{info['kl_matrix'][m][b]:6.2f}" for b in us))
    print("\npicks:", *(f"{p['map']} kl={p['kl']} diff={p['diff']} cost={p['cost']}" for p in info["picks"]), sep="\n  ")
    print("order:", ",".join(new))
