"""SwatMinds-style squad brain for the DK1 gym (ideas from the SWAT 4 SwatMinds mod).

 CLEAR  (no live suspect in contact): coverage-paint grid; leader walks to the nearest unpainted open cell
        (frontier), or to the last suspect position seen earlier; followers trail it in a train.
 ENGAGE (a suspect in LOS within CONTACT_R, or any within CLOSE_R, of a trooper): whole team converges on the
        suspect nearest the team centre.
Walls / doors / props = the game's own collision grid (bridge `cgrid`, mask 0x10, 4 px cells; PORTS-HOOKS.md DK1 walls):
 - coverage paint: a 32 px cell is "seen" when it is within PAINT_R of a trooper AND the line trooper->cell has no
   blocked grid cell (own Bresenham on the dumped grid; the bridge `los` command is the game's TraceLineOfSight, same result)
 - frontier goals skip blocked cells; contact needs LOS
 - train: the leader's planned route (bridge `route`, the pathfinder's points) is kept as a polyline; follower k is sent to
   the point k*SPACING behind the leader's progress along it (clamped to the route start).
Unreachable goals: `route`/`move` answer "ERR no path" -> goal cell blacklisted. State is module-global (one match at a
time); reset() when the trooper id set changes (new match).
"""
import math

CELL = 32            # px paint cell
PAINT_R = 320        # px: cells within this of a trooper AND in LOS count as seen
CONTACT_R = 300      # px: suspect in LOS this close to any trooper -> ENGAGE
CLOSE_R = 90         # px: suspect this close = contact even without LOS (sound / adjacent room)
SPACING = 40         # px between train members along the leader's route
REPATH = 48          # px: re-order only if the target moved more than this (same rule as rush/pairs)
GOAL_REACHED = 70    # px: leader this close to its goal cell = goal done
GOAL_PATIENCE = 12   # ticks (~1 s each) before an unreached goal is blacklisted
BOUNDS = (0, 0, 1600, 1200)  # px: frontier window, shrunk to the map size when the grid is known
TRAIN_REPATH = 140   # px: a follower is re-ordered only if its train slot moved this far (every move resets its plan)
HOLD_R = 230         # px: ENGAGE shooters with LOS to the target inside this range hold position
PUSH_AFTER = 8       # ticks of CLEAR without contact before the team rushes the nearest suspect (omniscient gym fallback)
TRAIL_MAX = 200      # leader trail samples kept (fallback when no route)

S = dict(ids=None, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={},
         grid=None, send=None, lpath=None, region=None, clear_ticks=0, holding=set())


def reset(ids):
    S.update(ids=ids, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={}, lpath=None, clear_ticks=0, holding=set())


def bind(send, cgrid_lines=None, region=None):
    """send = dk1gym.send; cgrid_lines = the answer of the bridge `cgrid` (header 'G w h mapW mapH' + h rows)."""
    S["send"] = send
    S["region"] = region  # fn(x, y) -> open-region label (0 blocked); goals outside the leader's region would hang GeneratePath
    S["grid"] = None
    if cgrid_lines and cgrid_lines[0].startswith("G "):
        w, h, mw, mh = map(int, cgrid_lines[0].split()[1:5])
        S["grid"] = dict(w=w, h=h, mw=mw, mh=mh, rows=cgrid_lines[1:1 + h])


def _gc(x, y):
    g = S["grid"]
    cx = min(max(int(g["w"] * x / g["mw"] - 0.5), 0), g["w"] - 1)
    cy = min(max(int(g["h"] * y / g["mh"] - 0.5), 0), g["h"] - 1)
    return cx, cy


def blocked(x, y):
    g = S["grid"]
    if not g:
        return False
    cx, cy = _gc(x, y)
    return g["rows"][cy][cx] == "#"


def los(x0, y0, x1, y1):
    """True when no blocked collision cell lies between the two points (start / end cells ignored)."""
    g = S["grid"]
    if not g:
        return True
    ax, ay = _gc(x0, y0)
    bx, by = _gc(x1, y1)
    dx, dy = abs(bx - ax), abs(by - ay)
    sx, sy = (1 if bx > ax else -1), (1 if by > ay else -1)
    err, x, y = dx - dy, ax, ay
    rows = g["rows"]
    while (x, y) != (bx, by):
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x += sx
        if e2 < dx:
            err += dx; y += sy
        if (x, y) != (bx, by) and rows[y][x] == "#":
            return False
    return True


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
                if (i, j) not in S["painted"] and math.hypot(px - t["x"], py - t["y"]) <= PAINT_R \
                        and (blocked(px, py) or los(t["x"], t["y"], px, py)):
                    S["painted"].add((i, j))  # wall cells count as seen (nothing to clear there)


def _bounds():
    g = S["grid"]
    return (0, 0, g["mw"], g["mh"]) if g else BOUNDS


def _frontier(leader):
    best, bd = None, 1e9
    x0, y0, x1, y1 = _bounds()
    for i in range(int(x0 // CELL), int(x1 // CELL)):
        for j in range(int(y0 // CELL), int(y1 // CELL)):
            c = (i, j)
            if c in S["painted"] or c in S["bad"]:
                continue
            px, py = _ctr(c)
            if blocked(px, py) or (S["region"] and S["region"](px, py) != S["region"](leader["x"], leader["y"])):
                continue
            d = math.hypot(px - leader["x"], py - leader["y"])
            if d < bd:
                best, bd = c, d
    return best


def _route(leader, goal):
    """Pathfinder points leader -> goal cell (bridge `route`); None = no path."""
    gx, gy = _ctr(goal)
    if not S["send"]:
        return [(leader["x"], leader["y"]), (gx, gy)]
    a = S["send"]([f"route {leader['id']} {gx:.0f} {gy:.0f}"])[0].split()
    if a[0] != "R":
        return None
    n = int(a[1])
    pts = [(float(a[2 + 2 * i]), float(a[3 + 2 * i])) for i in range(n)]
    return [(leader["x"], leader["y"])] + pts


def _along(path, d):
    """Point at arc length d on the polyline (clamped)."""
    acc = 0.0
    for a, b in zip(path, path[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg and acc + seg >= d:
            f = (d - acc) / seg
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        acc += seg
    return path[-1]


def _progress(path, x, y):
    """Arc length of the polyline point nearest to (x, y)."""
    best, bd, acc = 0.0, 1e18, 0.0
    for a, b in zip(path, path[1:]):
        sx, sy = b[0] - a[0], b[1] - a[1]
        seg = math.hypot(sx, sy)
        f = 0.0 if not seg else max(0.0, min(1.0, ((x - a[0]) * sx + (y - a[1]) * sy) / (seg * seg)))
        d = math.hypot(a[0] + sx * f - x, a[1] + sy * f - y)
        if d < bd:
            bd, best = d, acc + seg * f
        acc += seg
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
            S["bad"].add(S["goal"]); S["goal"] = None; S["lpath"] = None


def _pick_goal(leader):
    """Next goal cell with a pathfinder route (tries a few; unreachable ones are blacklisted)."""
    for _ in range(6):
        g = None
        if S["seen"]:  # last known suspect position first
            sx, sy = S["seen"]
            S["seen"] = None
            g = _cell(sx, sy)
            if g in S["painted"] or g in S["bad"] or blocked(*_ctr(g)) or (S["region"] and S["region"](*_ctr(g)) != S["region"](leader["x"], leader["y"])):
                g = None
        if not g:
            g = _frontier(leader)
        if not g:
            return None
        r = _route(leader, g)
        if r is None:
            S["bad"].add(g)
            continue
        S["lpath"] = r
        return g
    return None


def orders(troopers, suspects, last):
    ids = sorted(t["id"] for t in troopers)
    if S["ids"] is None or not set(ids) <= set(S["ids"]):
        reset(ids)
    _paint(troopers)
    # contact? suspect in LOS within CONTACT_R, or very close
    contact = [s for t in troopers for s in suspects
               if (lambda d: d <= CLOSE_R or (d <= CONTACT_R and los(t["x"], t["y"], s["x"], s["y"])))(math.hypot(s["x"] - t["x"], s["y"] - t["y"]))]
    force, thr = set(), {}
    if contact:
        S["clear_ticks"] = 0
        cx = sum(t["x"] for t in troopers) / len(troopers)
        cy = sum(t["y"] for t in troopers) / len(troopers)
        s = min(contact, key=lambda s: math.hypot(s["x"] - cx, s["y"] - cy))
        S["seen"] = (s["x"], s["y"]); S["mode"] = "ENGAGE"
        S["goal"] = None; S["lpath"] = None
        _engage(troopers, s, want := {}, force)
        S["pend"] = dict(leader=None)
    else:
        S["mode"] = "CLEAR"; S["holding"] = set(); S["clear_ticks"] += 1
        leader = next((t for t in troopers if t["id"] == S["ids"][0]), None) or troopers[0]
        S["trail"].append((leader["x"], leader["y"])); del S["trail"][:-TRAIL_MAX]
        want = {}
        if S["clear_ticks"] > PUSH_AFTER and suspects:  # nothing found by sweeping: close in on the nearest suspect (pairs-style)
            s = min(suspects, key=lambda s: math.hypot(s["x"] - leader["x"], s["y"] - leader["y"]))
            want = {t["id"]: (s["x"], s["y"]) for t in troopers}
            S["goal"] = None; S["lpath"] = None
            S["pend"] = dict(leader=None)
            return {i: p for i, p in want.items() if i not in last or math.hypot(p[0] - last[i][0], p[1] - last[i][1]) > 80}
        g = S["goal"]
        if g:
            gx, gy = _ctr(g)
            S["goal_age"] += 1
            if g in S["painted"] or math.hypot(gx - leader["x"], gy - leader["y"]) < GOAL_REACHED:
                S["painted"].add(g); S["goal"] = None
            elif S["goal_age"] > GOAL_PATIENCE and leader["wps"] == 0:
                S["bad"].add(g); S["goal"] = None  # leader idle, goal unreachable
            elif leader["wps"] == 0 and S["goal_age"] > 2:
                force.add(leader["id"])  # route consumed / plan dropped before the goal: re-issue the same cached goal, no new pathing here
        if not S["goal"]:
            S["goal"] = _pick_goal(leader); S["goal_age"] = 0
            if S["goal"]:
                force.add(leader["id"])
        if S["goal"]:
            want[leader["id"]] = _ctr(S["goal"])
        # train: followers ordered by distance to leader, k-th goes k*SPACING behind the leader on the planned route
        fol = sorted((t for t in troopers if t is not leader), key=lambda t: math.hypot(t["x"] - leader["x"], t["y"] - leader["y"]))
        lp = S["lpath"]
        if lp and len(lp) > 1:
            p = _progress(lp, leader["x"], leader["y"])
            for k, t in enumerate(fol, 1):
                want[t["id"]] = _along(lp, max(0.0, p - k * SPACING))
        elif len(S["trail"]) > 1:
            for k, t in enumerate(fol, 1):
                want[t["id"]] = _trail_point(k * SPACING)
        for t in fol:
            thr[t["id"]] = TRAIN_REPATH
            if t["wps"] == 0 and t["id"] in want and math.hypot(want[t["id"]][0] - t["x"], want[t["id"]][1] - t["y"]) > 60:
                force.add(t["id"])  # idle follower far from its slot
        S["pend"] = dict(leader=leader["id"])
    return {i: p for i, p in want.items()
            if i in force or i not in last or math.hypot(p[0] - last[i][0], p[1] - last[i][1]) > thr.get(i, REPATH)}


def _engage(troopers, s, want, force):
    """Shooters (LOS to the target, within HOLD_R, at most half the team, the farthest from it) hold their lane: stop in place.
    Everyone else pushes to the target."""
    sd = lambda t: math.hypot(s["x"] - t["x"], s["y"] - t["y"])
    shooters = sorted((t for t in troopers if sd(t) <= HOLD_R and los(t["x"], t["y"], s["x"], s["y"])), key=sd, reverse=True)
    hold = {t["id"] for t in shooters[:max(1, len(troopers) // 2)]} if len(troopers) > 1 else set()
    for t in troopers:
        if t["id"] in hold:
            if t["wps"] > 0 or t["id"] not in S["holding"]:
                want[t["id"]] = (t["x"], t["y"]); force.add(t["id"])  # move-to-self = stop
        else:
            want[t["id"]] = (s["x"], s["y"])
    S["holding"] = hold
