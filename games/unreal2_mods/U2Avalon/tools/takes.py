r"""The informal taps (binder `takes:`, writer redesign 2026-10-09 s. 4.2): Tin Row has no legal supply, yet it has
power and water - cables hooked onto the nearest company line and hoses/drums from the nearest water main. The
player should SEE the theft, so each tap becomes geometry for the clutter and export passes:

  * power -> 'sag_cable': from the nearest point of a power line (systems.py connections, its pylons included), on
    improvised poles every <= POLE_M, sagging badly (SAG_K x span), to a 'spider' pole at the block's edge, then one
    drop cable to every shack of the block (the sheet's count:);
  * water -> 'hose_drums': a hose lying on the ground from the nearest point of a water main, with a drum (barrel)
    every DRUM_M along it and a cluster of drums at the block's edge.

    py tools/takes.py <run folder> [heightmap=isl_ec.bmp] [layout=isl_layout.json] [out=<run>\taps.json]
                      [png=<run>\isl_taps.png] [write=0]

As a library: taps(L, Z, sheets) -> list of tap dicts (L['taps'] in the pipeline); clutter_items(taps) -> props
(mesh, x, y, yaw, scale, lift) for clutter.py's actor(); conc_report(L) -> the slurry pipeline's hops and length
(the route itself is systems.py's process chain, 24a454b). Needs systems.py to have run (L['connections']).
"""
import json, math, os, sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import anchors  # noqa  (terrain helpers)

M = 50.0
POLE_M = 18.0            # improvised poles: scaffold tube, a timber, a dead lamp post
POLE_H_M = 5.5
PYLON_H_M = 10.0         # where the tap hooks onto a company pylon line
SAG_K = 0.06             # sag = SAG_K x span (a legal line sags ~2-3 %; these hang low)
DRUM_M = 25.0
POLE_MESH = "AvalonSM.Liandri.Pylon"           # at POLE_SCALE until a crooked-pole part exists (build_parts)
POLE_SCALE = 0.45
DRUM_MESH = "Terran_DecoM.Barrels.Metal_Barrel_01"


def instances(bid, P, sheet):
    """the block's shacks (as walks.instances): count 'AxC' / 'n along|across' around the building's point"""
    W, D = sheet["size"][0] * M, sheet["size"][1] * M
    gap = max(W, D) * 1.5
    spec = (sheet.get("count") or "1").split()
    pts = [(0, 0)]
    if "x" in spec[0].lower():
        na, nc = (int(v) for v in spec[0].lower().split("x"))
        pts = [((ka - (na - 1) / 2) * gap, (kc - (nc - 1) / 2) * gap) for kc in range(nc) for ka in range(na)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    a = math.radians(P["yaw"])
    return [(P["x"] + da * math.cos(a) - dc * math.sin(a), P["y"] + da * math.sin(a) + dc * math.cos(a)) for da, dc in pts]


def nearest_on(lines, p):
    """nearest point to p on a set of polylines: (dist, point, line index)"""
    best = None
    for li, pts in lines:
        for a, b in zip(pts[:-1], pts[1:]):
            ax, ay, bx, by = a[0], a[1], b[0], b[1]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
            q = (ax + dx * t, ay + dy * t)
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if best is None or d < best[0]:
                best = (d, q, li)
    return best


def sag_spans(Z, pts, h0_m, h_m=POLE_H_M):
    """poles at pts (the first at height h0_m, a hook on the company line), spans with their sag"""
    poles, spans = [], []
    for k, (x, y) in enumerate(pts):
        g = anchors.zat(Z, x, y)
        poles.append([round(x, 1), round(y, 1), round(g, 1), h0_m if k == 0 else h_m])
    for a, b in zip(poles[:-1], poles[1:]):
        span = math.hypot(b[0] - a[0], b[1] - a[1]) / M
        spans.append({"a": [a[0], a[1], round(a[2] + a[3] * M, 1)], "b": [b[0], b[1], round(b[2] + b[3] * M, 1)],
                      "span_m": round(span, 1), "sag_m": round(SAG_K * span + 0.3, 2)})
    return poles, spans


def taps(L, Z, sheets):
    B = L["buildings"]
    conns = L.get("connections", [])
    out = []
    for bid, sheet in sheets.items():
        res_list = sheet.get("takes") or []
        if bid not in B or not res_list or B[bid].get("abandoned"):
            continue
        P = B[bid]
        shacks = instances(bid, P, sheet)
        for res in res_list:
            lines = [(k, c["path"]) for k, c in enumerate(conns) if c["resource"] == res and c.get("path") and c["to"] != bid]
            # a provider with no line drawn yet still counts: its own walls
            provs = [(None, [[B[p]["x"], B[p]["y"]], [B[p]["x"], B[p]["y"]]]) for p in B
                     if p != bid and p in sheets and res in (sheets[p].get("provides") or "").split()]
            hit = nearest_on(lines + provs, (P["x"], P["y"]))
            if hit is None:
                out.append({"taker": bid, "resource": res, "ok": False, "why": "no %s line or provider to tap" % res})
                continue
            d, q, li = hit
            src = conns[li]["from"] if li is not None else None
            # the block's edge nearest the tap: the shack nearest q, pushed half a shack toward q
            near = min(shacks, key=lambda s: math.hypot(s[0] - q[0], s[1] - q[1]))
            ux, uy = q[0] - near[0], q[1] - near[1]
            r = max(1.0, math.hypot(ux, uy))
            edge = (near[0] + ux / r * min(r, 6 * M), near[1] + uy / r * min(r, 6 * M))
            run = math.hypot(edge[0] - q[0], edge[1] - q[1])
            tap = {"taker": bid, "resource": res, "ok": True, "from_line": li, "from": src, "hook": [round(q[0], 1), round(q[1], 1)],
                   "metres": round(run / M, 1), "shacks": len(shacks)}
            if res == "power":
                n = max(1, int(math.ceil(run / (POLE_M * M))))
                pts = [(q[0] + (edge[0] - q[0]) * k / n, q[1] + (edge[1] - q[1]) * k / n) for k in range(n + 1)]
                # a little drunk: poles stand where someone could dig, never on a line
                rng = np.random.default_rng(abs(hash((bid, res))) % (2 ** 32))
                pts = [pts[0]] + [(x + rng.normal(0, 1.2 * M), y + rng.normal(0, 1.2 * M)) for x, y in pts[1:-1]] + [pts[-1]]
                hook_h = PYLON_H_M if (li is not None and conns[li].get("relays")) else POLE_H_M + 1.0
                poles, spans = sag_spans(Z, pts, hook_h)
                drops = []
                ex, ey, eg, eh = poles[-1]
                for sx, sy in shacks:                        # the spider pole's drops, one per shack
                    g = anchors.zat(Z, sx, sy)
                    span = math.hypot(sx - ex, sy - ey) / M
                    drops.append({"a": [ex, ey, round(eg + eh * M, 1)], "b": [round(sx, 1), round(sy, 1), round(g + 3.0 * M, 1)],
                                  "span_m": round(span, 1), "sag_m": round(SAG_K * span + 0.2, 2)})
                tap.update(style="sag_cable", poles=poles, spans=spans, drops=drops)
            else:
                n = max(1, int(run / (5 * M)))
                hose = []
                for k in range(n + 1):
                    x, y = q[0] + (edge[0] - q[0]) * k / n, q[1] + (edge[1] - q[1]) * k / n
                    hose.append([round(x, 1), round(y, 1), round(anchors.zat(Z, x, y) + 5, 1)])
                drums = [[round(q[0] + (edge[0] - q[0]) * t, 1), round(q[1] + (edge[1] - q[1]) * t, 1)]
                         for t in np.arange(DRUM_M * M, run, DRUM_M * M) / max(run, 1)]
                ang = math.atan2(edge[1] - q[1], edge[0] - q[0])
                for k in range(4):                           # the drum store at the block's edge
                    drums.append([round(edge[0] + math.cos(ang + 1.6 + k * 0.9) * 90, 1), round(edge[1] + math.sin(ang + 1.6 + k * 0.9) * 90, 1)])
                tap.update(style="hose_drums", hose=hose, drums=drums)
            out.append(tap)
    return out


def clutter_items(tap_list):
    """props for clutter.py's actor(mesh, x, y, yaw, scale, lift): the poles and the drums. The cables and hoses
    themselves are lines (spans/drops/hose) for a cable mesh or a decal when one exists"""
    items = []
    for t in tap_list:
        if not t.get("ok"):
            continue
        if t["style"] == "sag_cable":
            for k, (x, y, _, h) in enumerate(t["poles"]):
                if k == 0:
                    continue                                  # the hook is on the company's own pylon/pole
                items.append((POLE_MESH, x, y, (hash((x, y)) % 360), POLE_SCALE, 0.0))
        else:
            for k, (x, y) in enumerate(t["drums"]):
                items.append((DRUM_MESH, x, y, (k * 47) % 360, 1.0, 0.0))
    return items


def conc_report(L):
    """the slurry pipeline as systems.py routed it: hops (from, to, metres, ok) and the total route length"""
    hops = [c for c in L.get("connections", []) if c.get("resource") == "conc"]
    total = sum(anchors.plen(c["path"]) / M for c in hops if c.get("path"))
    nxt = {c["from"]: c["to"] for c in hops}
    heads = [f for f in nxt if f not in {c["to"] for c in hops}]
    chain = heads[:1]
    while chain and chain[-1] in nxt and nxt[chain[-1]] not in chain:
        chain.append(nxt[chain[-1]])
    return {"hops": [(c["from"], c["to"], c["metres"], c["ok"]) for c in hops], "chain": chain, "route_m": round(total),
            "direct_m": sum(c["metres"] for c in hops), "all_ok": all(c["ok"] for c in hops)}


def overlay(Z, L, tap_list, png, S=6):
    from PIL import ImageDraw, Image
    anchors.overlay(Z, L, png, None, S)
    img = Image.open(png)
    dr = ImageDraw.Draw(img)

    def P(x, y):
        fi, fj = anchors.w2c(x, y)
        return (fi * S, (anchors.N - fj) * S)
    for c in L.get("connections", []):
        col = {"power": (255, 230, 0), "water": (0, 120, 255), "conc": (160, 60, 20)}.get(c["resource"])
        if col and c.get("path"):
            dr.line([P(*p[:2]) for p in c["path"]], fill=col, width=3 if c["resource"] == "conc" else 1)
    for t in tap_list:
        if not t.get("ok"):
            continue
        if t["style"] == "sag_cable":
            dr.line([P(*p[:2]) for p in t["poles"]], fill=(255, 0, 255), width=2)
            for dsp in t["drops"]:
                dr.line([P(*dsp["a"][:2]), P(*dsp["b"][:2])], fill=(255, 120, 255), width=1)
        else:
            dr.line([P(*p[:2]) for p in t["hose"]], fill=(0, 255, 200), width=2)
            for x, y in t["drums"]:
                cx, cy = P(x, y)
                dr.rectangle([cx - 1, cy - 1, cx + 1, cy + 1], fill=(0, 255, 200))
    dr.text((4, 4), "taps: magenta = sagging cables, cyan = hose + drums; brown = conc slurry line", fill=(255, 255, 255))
    img.save(png)


if __name__ == "__main__":
    import binder
    run = sys.argv[1]
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    hm = os.path.join(run, o.get("heightmap", "isl_ec.bmp"))
    if not os.path.exists(hm):
        hm = os.path.join(run, "isl_e.bmp")
    lp = os.path.join(run, o.get("layout", "isl_layout.json"))
    Z = anchors.load_heights(hm)
    L = json.load(open(lp))
    _, sheets = binder.load()
    T = taps(L, Z, sheets)
    C = conc_report(L)
    out = o.get("out", os.path.join(run, "taps.json"))
    json.dump({"heightmap": hm, "layout": lp, "taps": T, "conc": C, "clutter": clutter_items(T)}, open(out, "w"), indent=1)
    overlay(Z, L, T, o.get("png", os.path.join(run, "isl_taps.png")))
    if o.get("write") == "1":
        L["taps"] = T
        json.dump(L, open(lp, "w"), indent=0)
    for t in T:
        print("  %-9s takes %-6s %s" % (t["taker"], t["resource"], ("%s from %s's line, %.0f m, %d shacks%s" % (
            t["style"], t["from"], t["metres"], t["shacks"], (", %d poles" % (len(t["poles"]) - 1)) if t["style"] == "sag_cable" else ", %d drums" % len(t["drums"])))
            if t["ok"] else "NONE: " + t["why"]))
    print("taps: %d (%d ok), %d clutter props; conc: %s, route %d m" % (len(T), sum(t["ok"] for t in T), len(clutter_items(T)), C["hops"], C["route_m"]))
    print("->", out)
