"""SwatMinds-style squad brain for the DK1 gym (ideas from the SWAT 4 SwatMinds mod).

 CLEAR  (no live suspect within CONTACT_R of any trooper): coverage-paint grid; leader walks to the nearest
        unpainted cell (frontier), or to the last suspect position seen earlier; followers trail it in a train.
 ENGAGE (a suspect within CONTACT_R of any trooper): whole team converges on the suspect nearest the team centre.
Level walls are not in the level XML (<Walls/> empty, props are entities), so LOS = radius PAINT_R (fallback).
Unreachable goals: the bridge answers "ERR no path" -> feedback() blacklists the cell. State is module-global
(one match at a time); reset() is called when a trooper id set changes (new match).
"""
import math

CELL = 32            # px grid cell
PAINT_R = 200        # px: cells within this of a trooper count as seen (LOS fallback)
CONTACT_R = 260      # px: suspect this close to any trooper -> ENGAGE
SPACING = 40         # px between train members along the leader's trail
REPATH = 48          # px: re-order only if the target moved more than this (same rule as rush/pairs)
GOAL_REACHED = 40    # px: leader this close to its goal cell = goal done
GOAL_PATIENCE = 12   # ticks (~1 s each) before an unreached goal is blacklisted
BOUNDS = (0, 0, 1600, 1200)  # px: frontier search window (bad cells get blacklisted via ERR)
TRAIL_MAX = 200      # leader trail samples kept

S = dict(ids=None, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={})


def reset(ids):
    S.update(ids=ids, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={})


def _cell(x, y):
    return int(x // CELL), int(y // CELL)


def _ctr(c):
    return (c[0] + 0.5) * CELL, (c[1] + 0.5) * CELL


def _paint(troopers):
    r = int(PAINT_R // CELL) + 1
    for t in troopers:
        cx, cy = _cell(t["x"], t["y"])
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                px, py = _ctr((i, j))
                if math.hypot(px - t["x"], py - t["y"]) <= PAINT_R:
                    S["painted"].add((i, j))


def _frontier(leader):
    best, bd = None, 1e9
    x0, y0, x1, y1 = BOUNDS
    for i in range(x0 // CELL, x1 // CELL):
        for j in range(y0 // CELL, y1 // CELL):
            c = (i, j)
            if c in S["painted"] or c in S["bad"]:
                continue
            px, py = _ctr(c)
            d = math.hypot(px - leader["x"], py - leader["y"])
            if d < bd:
                best, bd = c, d
    return best


def _trail_point(back):
    """Point `back` px behind the leader along its recorded trail (newest last)."""
    tr = S["trail"]
    acc = 0.0
    for a, b in zip(reversed(tr[1:]), reversed(tr[:-1])):
        seg = math.hypot(a[0] - b[0], a[1] - b[1])
        if acc + seg >= back:
            f = (back - acc) / seg if seg else 0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        acc += seg
    return tr[0]


def feedback(ids, answers):
    """ids = trooper ids of the last move batch (same order as answer lines); blacklist a goal that had no path."""
    for i, a in zip(ids, answers):
        if a.startswith("ERR") and i == S["pend"].get("leader") and S["goal"]:
            S["bad"].add(S["goal"]); S["goal"] = None


def orders(troopers, suspects, last):
    ids = sorted(t["id"] for t in troopers)
    if S["ids"] is None or not set(ids) <= set(S["ids"]):
        reset(ids)
    _paint(troopers)
    # contact?
    contact = [s for t in troopers for s in suspects if math.hypot(s["x"] - t["x"], s["y"] - t["y"]) <= CONTACT_R]
    if contact:
        cx = sum(t["x"] for t in troopers) / len(troopers)
        cy = sum(t["y"] for t in troopers) / len(troopers)
        s = min(contact, key=lambda s: math.hypot(s["x"] - cx, s["y"] - cy))
        S["seen"] = (s["x"], s["y"]); S["mode"] = "ENGAGE"
        want = {t["id"]: (s["x"], s["y"]) for t in troopers}
        S["pend"] = dict(leader=None)
    else:
        S["mode"] = "CLEAR"
        # leader = trooper nearest the goal if any, else the first id (stable)
        leader = next((t for t in troopers if t["id"] == S["ids"][0]), None) or troopers[0]
        S["trail"].append((leader["x"], leader["y"])); del S["trail"][:-TRAIL_MAX]
        g = S["goal"]
        if g:
            gx, gy = _ctr(g)
            S["goal_age"] += 1
            if g in S["painted"] or math.hypot(gx - leader["x"], gy - leader["y"]) < GOAL_REACHED:
                S["painted"].add(g); S["goal"] = None
            elif S["goal_age"] > GOAL_PATIENCE and leader["wps"] == 0:
                S["bad"].add(g); S["goal"] = None  # leader idle, goal unreachable
        if not S["goal"]:
            if S["seen"]:  # last known suspect position first
                sx, sy = S["seen"]
                S["seen"] = None
                S["goal"] = _cell(sx, sy); S["goal_age"] = 0
                if S["goal"] in S["painted"]:
                    S["goal"] = None
            if not S["goal"]:
                S["goal"] = _frontier(leader); S["goal_age"] = 0
        want = {}
        if S["goal"]:
            want[leader["id"]] = _ctr(S["goal"])
        # train: followers ordered by distance to leader, k-th trails k*SPACING back along the leader trail
        fol = sorted((t for t in troopers if t is not leader), key=lambda t: math.hypot(t["x"] - leader["x"], t["y"] - leader["y"]))
        if len(S["trail"]) > 1:
            for k, t in enumerate(fol, 1):
                want[t["id"]] = _trail_point(k * SPACING)
        S["pend"] = dict(leader=leader["id"])
    return {i: p for i, p in want.items() if i not in last or math.hypot(p[0] - last[i][0], p[1] - last[i][1]) > REPATH}
