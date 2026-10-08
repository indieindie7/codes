r"""Heatmaps of a U2AutoPlay run (testing plan step 6): one top-down picture of where a level is broken, plus
coverage numbers.

    py -3.13 heatmap.py RUN_DIR_or_LOG [out_prefix]

Reads the "AutoPlay:" lines of Unreal2.log:
  POS x y z health              the bot's track (every 2 s)
  EVT STUCK/FELL/DIED/NOPROGRESS x y z ...
  AUDIT NODE / EDGE             the path network ("autoplay audit"), the backdrop and the coverage base
  AUDIT NOREACH / ONEWAY / ITEM / TRIGGER x y z
Without NODE lines the backdrop falls back to runs/navpoints_<MAP>.json (playshots.py's cache), else none.

Writes out_prefix.png (default RUN_DIR/heatmap.png: a time-in-place heat layer, the network with
unreached / one-way nodes, the track, and the events) and out_prefix.md (coverage: 5 m cells, nodes and
links walked, reachable). Coverage counts a node as walked when the track (its 2 s samples joined by
straight lines) passed within 3 m of it at about its height.
"""
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NEAR, NEAR_Z, CELL = 150.0, 200.0, 256.0        # 3 m, 4 m, 5 m (Unreal units: 50 per metre)
EVENT_STYLE = {"STUCK": ("o", "#ff9f1c"), "FELL": ("v", "#e63946"), "DIED": ("X", "#e63946"),
               "NOPROGRESS": ("s", "#b5179e")}


def parse(text):
    r = {"map": "?", "pos": [], "events": [], "nodes": {}, "edges": [], "audit": []}
    for line in text.splitlines():
        m = re.search(r"LoadMap: ([^?\s]+)", line)
        if m and m.group(1).lower() != "entry":
            r["map"] = m.group(1)
        i = line.find("AutoPlay: ")
        if i < 0:
            continue
        f = line[i + 10:].split()
        if not f:
            continue
        try:
            if f[0] == "POS":
                r["pos"].append(tuple(float(v) for v in f[1:4]))
            elif f[0] == "EVT":
                r["events"].append((f[1], float(f[2]), float(f[3]), float(f[4]), " ".join(f[5:])))
            elif f[0] == "AUDIT" and f[1] == "NODE":
                # NODE i name x y z class fwd back
                r["nodes"][int(f[2])] = dict(name=f[3], loc=(float(f[4]), float(f[5]), float(f[6])), cls=f[7],
                                             fwd=f[8] == "1", back=f[9] == "1")
            elif f[0] == "AUDIT" and f[1] == "EDGE":
                a = int(f[2])
                r["edges"] += [(a, int(b)) for b in f[3:]]
            elif f[0] == "AUDIT" and f[1] in ("NOREACH", "ONEWAY", "ITEM", "TRIGGER"):
                r["audit"].append((f[1], f[2], float(f[3]), float(f[4]), float(f[5]), " ".join(f[6:])))
        except (ValueError, IndexError):
            continue
    return r


def fallback_nodes(mapname):
    p = os.path.join(HERE, "runs", "navpoints_%s.json" % mapname)
    if not os.path.exists(p):
        return {}
    return {i: dict(name=n["name"], loc=tuple(n["loc"]), cls=n["class"], fwd=None, back=None)
            for i, n in enumerate(json.load(open(p)))}


def densify(pos, step=64.0):
    """the 2 s samples joined by straight lines, a point every step units"""
    if len(pos) < 2:
        return np.array(pos, dtype=float).reshape(-1, 3)
    out = []
    for a, b in zip(pos, pos[1:]):
        a, b = np.array(a), np.array(b)
        d = np.linalg.norm(b - a)
        if d > 3000:                    # a teleport or a respawn: don't draw a line across the map
            out.append(a)
            continue
        n = max(1, int(d / step))
        out += [a + (b - a) * t / n for t in range(n)]
    out.append(np.array(pos[-1]))
    return np.array(out)


def coverage(r, track):
    cells = {(int(x // CELL), int(y // CELL), int(z // CELL)) for x, y, z in track}
    walked = set()
    if len(track) and r["nodes"]:
        for i, n in r["nodes"].items():
            x, y, z = n["loc"]
            d = np.hypot(track[:, 0] - x, track[:, 1] - y)
            if np.any((d < NEAR) & (np.abs(track[:, 2] - z) < NEAR_Z)):
                walked.add(i)
    edges = {tuple(sorted(e)) for e in r["edges"]}
    walked_edges = {e for e in edges if e[0] in walked and e[1] in walked}
    return cells, walked, edges, walked_edges


def draw(r, track, walked, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 12), dpi=110)
    ax.set_facecolor("#14161a")
    fig.patch.set_facecolor("#14161a")
    # frame on the track, the network and the events; items and triggers far outside it are pinned to the edge
    core = [n["loc"] for n in r["nodes"].values()] + [tuple(p) for p in track] + \
        [(e[1], e[2], e[3]) for e in r["events"]] + [(a[2], a[3], a[4]) for a in r["audit"] if a[0] not in ("ITEM", "TRIGGER")]
    if not core:
        core = [(a[2], a[3], a[4]) for a in r["audit"]]
    if not core:
        raise SystemExit("nothing to draw: no POS, EVT or AUDIT lines in the log")
    P = np.array(core)
    x0, x1, y0, y1 = P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()
    pad = max(x1 - x0, y1 - y0, 2000) * 0.05
    x0, x1, y0, y1 = x0 - pad, x1 + pad, y0 - pad, y1 + pad
    cx, cy, half = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0, 2000) / 2    # square, at least 40 m
    x0, x1, y0, y1 = cx - half, cx + half, cy - half, cy + half

    # time spent in each place: the 2 s samples binned (each = 2 s), as a heat layer
    if len(r["pos"]):
        S = np.array(r["pos"])
        bins = int(min(200, max(8, (x1 - x0) / 128)))          # 2.5 m bins, at most 200 across
        H, xe, ye = np.histogram2d(S[:, 0], S[:, 1], bins=bins, range=[[x0, x1], [y0, y1]])
        H = np.ma.masked_equal(H, 0)
        ax.imshow(np.log1p(H.T * 2), origin="lower", extent=(x0, x1, y0, y1), cmap="inferno", alpha=0.75,
                  interpolation="nearest", aspect="equal", zorder=1)

    N = r["nodes"]
    for a, b in {tuple(sorted(e)) for e in r["edges"]}:
        if a in N and b in N:
            (ax_, ay_, _), (bx, by, _) = N[a]["loc"], N[b]["loc"]
            ok = a in walked and b in walked
            ax.plot([ax_, bx], [ay_, by], color="#5fd35f" if ok else "#3a4250", lw=0.8 if ok else 0.5, zorder=2)
    if N:
        def group(sel):
            return np.array([N[i]["loc"] for i in N if sel(i, N[i])]).reshape(-1, 3)
        for sel, c, s, lab in (
                (lambda i, n: n["fwd"] is not False and i not in walked, "#7a8699", 6, "node"),
                (lambda i, n: i in walked, "#5fd35f", 8, "node walked"),
                (lambda i, n: n["fwd"] is True and n["back"] is False, "#ffd166", 22, "one-way (no path back)"),
                (lambda i, n: n["fwd"] is False and n["cls"] != "PlayerStart", "#e63946", 14, "unreachable")):
            g = group(sel)
            if len(g):
                ax.scatter(g[:, 0], g[:, 1], s=s, c=c, label=lab, zorder=3, linewidths=0)

    if len(track):
        ax.plot(track[:, 0], track[:, 1], color="#4cc9f0", lw=1.0, alpha=0.9, label="bot track", zorder=4)
        ax.scatter([track[0, 0]], [track[0, 1]], s=90, c="#4cc9f0", marker="*", zorder=6, label="start")

    if not any(n["fwd"] is not None for n in N.values()):      # no NODE lines: the audit's own reports
        for kind, c, s, lab in (("NOREACH", "#e63946", 14, "unreachable"), ("ONEWAY", "#ffd166", 22, "one-way (no path back)")):
            g = np.array([(a[2], a[3]) for a in r["audit"] if a[0] == kind]).reshape(-1, 2)
            if len(g):
                ax.scatter(g[:, 0], g[:, 1], s=s, c=c, label=lab, zorder=3, linewidths=0)
    off = 0
    for kind in ("ITEM", "TRIGGER"):
        g = np.array([(a[2], a[3]) for a in r["audit"] if a[0] == kind]).reshape(-1, 2)
        if len(g):
            off += int(((g[:, 0] < x0) | (g[:, 0] > x1) | (g[:, 1] < y0) | (g[:, 1] > y1)).sum())
            g = np.column_stack([np.clip(g[:, 0], x0, x1), np.clip(g[:, 1], y0, y1)])
            ax.scatter(g[:, 0], g[:, 1], s=40, marker="D" if kind == "ITEM" else "P", facecolors="none",
                       edgecolors="#f72585" if kind == "ITEM" else "#ff9f1c", linewidths=1.2, zorder=5,
                       label="%s far from / cut off the network" % kind.lower())
    for kind, (mk, c) in EVENT_STYLE.items():
        g = np.array([(e[1], e[2]) for e in r["events"] if e[0] == kind]).reshape(-1, 2)
        if len(g):
            ax.scatter(g[:, 0], g[:, 1], s=70, marker=mk, c=c, edgecolors="white", linewidths=0.6, zorder=7,
                       label="%s (%d)" % (kind, len(g)))

    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)            # Unreal's Y runs the other way on screen (top-down, X right, Y down)
    ax.set_aspect("equal")
    ax.tick_params(colors="#8a93a3", labelsize=7)
    for s in ax.spines.values():
        s.set_color("#3a4250")
    ax.set_title("%s - autoplay heatmap (Unreal units, 50 = 1 m)%s" % (
        r["map"], "\n%d items/triggers beyond the frame, pinned to its edge" % off if off else ""), color="#e6e9ef")
    leg = ax.legend(loc="upper right", fontsize=8, facecolor="#1e2228", edgecolor="#3a4250", labelcolor="#e6e9ef")
    leg.set_zorder(10)
    fig.tight_layout()
    fig.savefig(out_png, facecolor=fig.get_facecolor())
    plt.close(fig)


def report(r, cells, walked, edges, walked_edges):
    N = r["nodes"]
    reach = [i for i in N if N[i]["fwd"]]
    pct = lambda a, b: "%d%%" % round(100.0 * a / b) if b else "-"
    L = ["# Heatmap: %s" % r["map"], "",
         "| | |", "|---|---|",
         "| Track samples (2 s) | %d (%d s) |" % (len(r["pos"]), 2 * len(r["pos"])),
         "| 5 m cells visited | %d |" % len(cells)]
    if N:
        src = "the audit" if any(n["fwd"] is not None for n in N.values()) else "the navpoint cache (no audit in this run)"
        L += ["| Nodes walked | %d of %d (%s) |" % (len(walked), len(N), pct(len(walked), len(N)))]
        if reach:
            L += ["| Nodes walked of the reachable | %d of %d (%s) |" % (len(walked & set(reach)), len(reach),
                                                                         pct(len(walked & set(reach)), len(reach)))]
        if edges:
            L += ["| Links walked | %d of %d (%s) |" % (len(walked_edges), len(edges), pct(len(walked_edges), len(edges)))]
        L += ["", "Network from %s." % src]
    ev = {}
    for e in r["events"]:
        ev[e[0]] = ev.get(e[0], 0) + 1
    L += ["", "Events: " + (", ".join("%s %d" % kv for kv in sorted(ev.items())) or "none")]
    au = {}
    for a in r["audit"]:
        au[a[0]] = au.get(a[0], 0) + 1
    L += ["Audit: " + (", ".join("%s %d" % kv for kv in sorted(au.items())) or "none")]
    for e in r["events"]:
        L.append("- %s at %d %d %d %s" % (e[0], e[1], e[2], e[3], e[4]))
    return "\n".join(L) + "\n"


def heatmap(src, out=None):
    log = os.path.join(src, "Unreal2.log") if os.path.isdir(src) else src
    r = parse(open(log, "rb").read().decode("latin1", "replace"))
    if not r["nodes"]:
        r["nodes"] = fallback_nodes(r["map"])
    if out is None:
        out = os.path.join(os.path.dirname(log), "heatmap")
    track = densify(r["pos"])
    cells, walked, edges, walked_edges = coverage(r, track)
    draw(r, track, walked, out + ".png")
    md = report(r, cells, walked, edges, walked_edges)
    open(out + ".md", "w", encoding="utf-8").write(md)
    return out, md


def run_heatmap(run_dir, log=print):
    """after a pilot run: only when the bot or the audit ran (any AutoPlay POS/EVT/AUDIT line)"""
    try:
        text = open(os.path.join(run_dir, "Unreal2.log"), "rb").read().decode("latin1", "replace")
        if "AutoPlay: POS" not in text and "AutoPlay: AUDIT" not in text:
            return
        out, md = heatmap(run_dir)
        rows = [l.strip("| ").replace(" | ", ": ") for l in md.splitlines() if l.startswith("| ") and l.strip("| ")]
        log("heatmap: " + " / ".join(rows + [l for l in md.splitlines() if l.startswith("Events:")]) + " -> heatmap.png")
    except Exception as e:                      # never lose a run over its report
        log(f"heatmap failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out, md = heatmap(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(md)
    print("wrote %s.png and %s.md" % (out, out))
