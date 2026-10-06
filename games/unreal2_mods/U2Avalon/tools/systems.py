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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

M = 50.0
# resource -> (carrier, reach in metres, carrier kind)
RELAY_M = 120.0          # a pylon every 120 m carries power beyond the cable's own reach, up to RELAY_MAX
RELAY_MAX = 1400.0
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


def run(layout_path, out_path=None, report=True):
    L = json.load(open(layout_path))
    B = L["buildings"]
    citizens, sheets = binder.load()
    road_pts = [tuple(p) for r in L.get("roads", []) for p in r[::3]]
    specs = {bid: spec_of(bid, sheets[bid]) for bid in B if bid in sheets}
    conns, lines, unmet = [], [], []
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
            path = l_route(a, c, road_pts) if carrier in ("pipe", "cable", "conveyor") else [list(a), list(c)]
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
    core_unmet = [u for u in unmet if u[1] in CORE]
    score = 1 - len(unmet) / max(1, sum(len(n) for _, n in specs.values()))
    L["connections"] = conns
    L["systems"] = {"needs": sum(len(n) for _, n in specs.values()), "unmet": unmet, "score": round(score, 3),
                    "pipes_m": round(sum(c["metres"] for c in conns if c["carrier"] == "pipe")),
                    "cables_m": round(sum(c["metres"] for c in conns if c["carrier"] == "cable")),
                    "conveyors_m": round(sum(c["metres"] for c in conns if c["carrier"] == "conveyor")),
                    "pylons": sum(len(c["relays"]) for c in conns)}
    json.dump(L, open(out_path or layout_path, "w"), indent=0)
    if report:
        print("systems: %d needs, %d unmet (%d core), score %.2f; pipes %d m, cables %d m, conveyors %d m, %d pylons"
              % (L["systems"]["needs"], len(unmet), len(core_unmet), score, L["systems"]["pipes_m"], L["systems"]["cables_m"],
                 L["systems"]["conveyors_m"], L["systems"]["pylons"]))
        for l in lines:
            print(l)
    return L, core_unmet


if __name__ == "__main__":
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    L, core_unmet = run(sys.argv[1], o.get("out"), o.get("report", "1") != "0")
    sys.exit(1 if core_unmet else 0)
