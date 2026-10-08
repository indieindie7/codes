r"""The systems layer of the binder town: what each building provides and needs (ore, power, water, fuel,
workers, goods, comms), whether the layout satisfies it, and the connections that carry it (pipes, cables,
conveyors, roads). This is what makes a town read as a working place rather than a scatter of props: every
building exists because of the ones around it, and the lines between them are visible.

    py tools/systems.py <layout.json> [out=<layout_systems.json>] [report=1]

Reads the binder (sheet keys `provides:` / `needs:`, e.g. `needs: ore power water workers`, with defaults by
id/kind below) and the layout's positions; for each need finds the nearest provider within the resource's
reach, routes a connection (L-shaped for pipes/cables/conveyors, the road network for goods and workers) and
writes everything back into the layout JSON as "connections" plus a "systems" report. Exit code 1 if any
core need is unmet (so a batch can stop and re-roll).
"""
import json, math, os, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

M = 50.0
# resource -> (carrier, reach in metres, carrier kind)
RELAY_M = 120.0          # a pylon every 120 m carries power beyond the cable's own reach, up to RELAY_MAX
RELAY_MAX = 1400.0
CONVEYOR_M = 60.0        # a tower every 60 m along the ore line (Longyearbyen's cableway: 74 towers)
RES = {
    "ore":     ("conveyor", 220),
    "power":   ("cable", 350),
    "water":   ("pipe", 300),
    "fuel":    ("pipe", 180),
    "cooling": ("pipe", 160),
    "workers": ("road", 450),
    "goods":   ("road", 450),
    "comms":   ("line", 1500),
    "supply":  ("road", 500),
}
# defaults by id, then by kind; sheets may override with `provides:` / `needs:` lines
BY_ID = {
    "wellhead_a": ({"ore"}, {"power"}), "wellhead_b": ({"ore"}, {"power"}), "wellhead_old": (set(), set()),
    "new_rig": ({"ore"}, {"power", "supply"}), "dead_rig": (set(), set()),
    "hall_a": ({"goods"}, {"ore", "power", "water", "workers", "cooling"}),
    "hall_b": ({"goods"}, {"ore", "power", "water", "workers"}),
    "hall_c": ({"goods"}, {"ore", "power", "workers"}),
    "silos": ({"ore"}, {"ore"}), "tank_farm": ({"fuel"}, {"fuel"}), "fuel_depot": ({"fuel"}, {"supply"}),
    "generator_house": ({"power"}, {"fuel"}), "pump_house": ({"water"}, {"power"}),
    "pump_station": ({"water"}, {"power"}), "intake": ({"water"}, {"power"}), "water_tanks": ({"water"}, {"water"}),
    "cooling_towers": ({"cooling"}, {"water", "power"}),
    "dorm": ({"workers"}, {"water", "power"}), "old_camp": ({"workers"}, set()), "directors_house": ({"workers"}, {"power", "water"}),
    "plant_office": (set(), {"power", "comms", "workers"}), "company_mast": ({"comms"}, {"power"}), "beacon": ({"comms"}, {"power"}),
    "dock": ({"supply"}, {"goods"}), "cargo_pad": ({"supply"}, set()), "boat_landing": (set(), set()),
    "checkpoint": (set(), {"power"}), "shed_a": (set(), set()), "shed_b": (set(), set()),
    "tower": ({"comms"}, set()), "mess": ({"workers"}, {"power", "water"}), "memorial": (set(), set()),
    "water_tower": ({"water"}, {"water"}), "far_islands": (set(), set()), "authority_pad": ({"supply"}, set()), "barge": (set(), set()), "wreck": (set(), set()),
}
CORE = {"ore", "power", "water", "workers"}      # unmet core needs fail the layout


def spec_of(bid, b):
    prov, need = BY_ID.get(bid, (set(), set()))
    prov, need = set(prov), set(need)
    if b.get("provides"):
        prov = set(b["provides"].split())
    if b.get("needs"):
        need = set(b["needs"].split())
    if b.get("abandoned"):
        prov, need = set(), set()
    return prov, need


def l_route(a, b, roads):
    """an L-shaped line a -> corner -> b; the corner on the side nearer a road cell (service lines follow roads)"""
    c1, c2 = (b[0], a[1]), (a[0], b[1])
    if roads:
        def dr(p):
            return min(math.hypot(p[0] - r[0], p[1] - r[1]) for r in roads)
        c = c1 if dr(c1) <= dr(c2) else c2
    else:
        c = c1
    return [list(a), list(c), list(b)]


class Net:
    """Q35 pass 7 (games/research_notes/Believable city simulation s. 7): utilities as trees along the roads.
    A graph of road vertices (every ~20 m) plus each building tied to its nearest vertex; each pipe/cable is the
    least-cost path from its provider, where ground this resource already runs along costs REUSE of a new run -
    so the lines merge into shared trunks (a cheap Steiner tree), instead of one L-shaped line per pair"""
    REUSE = 0.15

    def __init__(self, L, B):
        from scipy.sparse import csr_matrix
        self.pts, self.idx = [], {}
        edges = []
        for r in L.get("roads", []):
            prev = None
            acc = 0.0
            for k, p in enumerate(r):
                if prev is not None:
                    acc += math.hypot(p[0] - r[k - 1][0], p[1] - r[k - 1][1])
                if prev is None or acc >= 20 * M or k == len(r) - 1:
                    n = self.node(p)
                    if prev is not None and n != prev:
                        edges.append((prev, n))
                    prev, acc = n, 0.0
        self.road_n = len(self.pts)
        self.bnode = {}
        for bid, b in B.items():
            if self.road_n == 0:
                break
            p = (b["x"], b["y"])
            near = min(range(self.road_n), key=lambda k: math.dist(self.pts[k], p))
            n = self.node(p)
            self.bnode[bid] = n
            edges.append((n, near))
        self.edges = edges
        self.used = {}                                   # resource -> set of edges (u, v) with u < v
        self.load = {}                                   # edge -> set of resources

    def node(self, p):
        k = (round(p[0] / 100), round(p[1] / 100))
        if k not in self.idx:
            self.idx[k] = len(self.pts)
            self.pts.append((float(p[0]), float(p[1])))
        return self.idx[k]

    def route(self, res, a_bid, b_bid):
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        if a_bid not in self.bnode or b_bid not in self.bnode:
            return None
        used = self.used.setdefault(res, set())
        rows, cols, w = [], [], []
        for u, v in self.edges:
            d = math.dist(self.pts[u], self.pts[v]) + 1.0
            e = (min(u, v), max(u, v))
            c = d * (self.REUSE if e in used else 1.0)
            rows += [u, v]; cols += [v, u]; w += [c, c]
        n = len(self.pts)
        G = csr_matrix((w, (rows, cols)), shape=(n, n))
        src, dst = self.bnode[a_bid], self.bnode[b_bid]
        dist, pred = dijkstra(G, indices=src, return_predecessors=True)
        if not np.isfinite(dist[dst]):
            return None
        path, k = [], dst
        while k != src and k >= 0:
            path.append(k)
            k = pred[k]
        path.append(src)
        path.reverse()
        new_m = 0.0
        for u, v in zip(path[:-1], path[1:]):
            e = (min(u, v), max(u, v))
            if e not in used:
                new_m += math.dist(self.pts[u], self.pts[v]) / M
            used.add(e)
            self.load.setdefault(e, set()).add(res)
        return [[round(self.pts[k][0]), round(self.pts[k][1])] for k in path], new_m

    def racks(self):
        """stretches carrying two or more resources: a pipe rack along the road"""
        return [[[round(c) for c in self.pts[u]], [round(c) for c in self.pts[v]], sorted(rs)]
                for (u, v), rs in self.load.items() if len(rs) >= 2]


def run(layout_path, out_path=None, report=True):
    L = json.load(open(layout_path))
    B = L["buildings"]
    citizens, sheets = binder.load()
    road_pts = [tuple(p) for r in L.get("roads", []) for p in r[::3]]
    specs = {bid: spec_of(bid, sheets[bid]) for bid in B if bid in sheets}
    conns, lines, unmet = [], [], []
    TREES = L.get("road_class") is not None and len(L.get("roads", [])) > 0     # the Q35 layouts: shared trunks
    net = Net(L, B) if TREES else None
    new_m = {}
    for bid, (prov, need) in specs.items():
        for res in sorted(need):
            carrier, reach = RES[res]
            best = None
            for pid, (pp, _) in specs.items():
                if pid == bid or res not in pp:
                    continue
                d = math.hypot(B[pid]["x"] - B[bid]["x"], B[pid]["y"] - B[bid]["y"]) / M
                if best is None or d < best[0]:
                    best = (d, pid)
            if best is None:
                unmet.append((bid, res, "no provider in the town"))
                lines.append("  %-16s needs %-7s : NO PROVIDER" % (bid, res))
                continue
            d, pid = best
            ok = d <= reach
            relays = []
            a, c = (B[pid]["x"], B[pid]["y"]), (B[bid]["x"], B[bid]["y"])
            # a conveyor runs STRAIGHT (the dominant line of a plant, towers every CONVEYOR_M); pipes and cables follow the roads
            path = l_route(a, c, road_pts) if carrier in ("pipe", "cable") else [list(a), list(c)]
            if net is not None and carrier in ("pipe", "cable"):
                rt = net.route(res, pid, bid)
                if rt is not None:
                    path, nm = rt
                    new_m[carrier] = new_m.get(carrier, 0.0) + nm
            if carrier == "conveyor":
                ok = ok or d <= 900
                seg = d
                n = int(seg // CONVEYOR_M)
                for k in range(1, n + 1):
                    t = k * CONVEYOR_M / seg
                    relays.append([round(a[0] + (c[0] - a[0]) * t), round(a[1] + (c[1] - a[1]) * t), round(math.degrees(math.atan2(c[1] - a[1], c[0] - a[0])))])
            if not ok and res == "power" and d <= RELAY_MAX:
                ok = True                                   # a pylon line: relays along the L path every RELAY_M
                for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
                    seg = math.hypot(x1 - x0, y1 - y0) / M
                    n = int(seg // RELAY_M)
                    for k in range(1, n + 1):
                        t = k * RELAY_M / seg
                        relays.append([round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), round(math.degrees(math.atan2(y1 - y0, x1 - x0)))])
            if not ok:
                unmet.append((bid, res, "%s is %.0f m away (reach %d)" % (pid, d, reach)))
            lines.append("  %-16s needs %-7s <- %-16s %4.0f m %s" % (bid, res, pid, d, ("via %d pylons" % len(relays)) if relays else ("" if ok else "TOO FAR")))
            conns.append({"from": pid, "to": bid, "resource": res, "carrier": carrier, "ok": ok, "metres": round(d),
                          "path": path, "relays": relays})
    if net is not None:                                   # one pylon where several power lines share a stretch
        seen = set()
        for cn in conns:
            keep = []
            for r in cn["relays"]:
                k = (round(r[0] / (15 * M)), round(r[1] / (15 * M)))
                if cn["carrier"] == "conveyor" or k not in seen:
                    keep.append(r)
                    seen.add(k)
            cn["relays"] = keep
    core_unmet = [u for u in unmet if u[1] in CORE]
    score = 1 - len(unmet) / max(1, sum(len(n) for _, n in specs.values()))
    L["connections"] = conns
    L["systems"] = {"needs": sum(len(n) for _, n in specs.values()), "unmet": unmet, "score": round(score, 3),
                    "pipes_m": round(sum(c["metres"] for c in conns if c["carrier"] == "pipe")),
                    "cables_m": round(sum(c["metres"] for c in conns if c["carrier"] == "cable")),
                    "conveyors_m": round(sum(c["metres"] for c in conns if c["carrier"] == "conveyor")),
                    "pylons": sum(len(c["relays"]) for c in conns)}
    if net is not None:                                   # the trees: new run length (shared trunks counted once) + racks
        L["systems"]["pipes_m"] = round(new_m.get("pipe", 0.0))
        L["systems"]["cables_m"] = round(new_m.get("cable", 0.0))
        L["racks"] = net.racks()
        L["systems"]["racks"] = len(L["racks"])
    json.dump(L, open(out_path or layout_path, "w"), indent=0)
    if report:
        print("systems: %d needs, %d unmet (%d core), score %.2f; pipes %d m, cables %d m, conveyors %d m, %d pylons%s"
              % (L["systems"]["needs"], len(unmet), len(core_unmet), score, L["systems"]["pipes_m"], L["systems"]["cables_m"],
                 L["systems"]["conveyors_m"], L["systems"]["pylons"],
                 (", %d rack stretches (shared trunks)" % L["systems"]["racks"]) if "racks" in L["systems"] else ""))
        for l in lines:
            print(l)
    return L, core_unmet


if __name__ == "__main__":
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    L, core_unmet = run(sys.argv[1], o.get("out"), o.get("report", "1") != "0")
    sys.exit(1 if core_unmet else 0)
