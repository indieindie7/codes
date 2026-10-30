"""SwatMinds-style squad brain for the DK1 gym (ideas from the SWAT 4 SwatMinds mod).

 CLEAR  (no anchor, no contact): coverage-paint grid; leader walks to the nearest unpainted open cell
        (frontier), or to the last suspect position seen earlier; followers trail it in a train.
 HUNT   (anchor = last contact, no contact now; no cheating: only contact positions are ever known): zone graph (rooms =
        4x4-cell blocks split into 4-connected parts); BFS from the anchor zone, each trooper takes a distinct unsearched zone
        in hop order and walks its checkpoints (centroid, +2 far cells for big zones, POIS); zone searched when checkpoints done
        or >=80% painted. Anchor on contact = contact trooper's zone, RELAY_TICKS later (trooper alive) the suspect's own zone.
        All zones within HUNT_HOPS searched -> anchor dropped -> CLEAR.
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
ZONE_CELLS = 4       # zone block = ZONE_CELLS x ZONE_CELLS paint cells (~ a room)
HUNT_HOPS = 3        # zone-graph hops from the anchor zone searched before giving up
RELAY_TICKS = 2      # ticks until the contact trooper's report upgrades the anchor to the suspect's exact zone
BIG_ZONE = 2.0       # zone bigger than this x median size takes 2 troopers + 2 extra checkpoints
SEARCHED_FRAC = 0.8  # zone also searched when this share of its cells is painted
POIS = []            # optional [(x, y)] points of interest; one in a hunt zone becomes a checkpoint there
TRAIL_MAX = 200      # leader trail samples kept (fallback when no route)

S = dict(ids=None, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={},
         grid=None, send=None, lpath=None, region=None, holding=set(),
         zones=[], zof={}, zadj={}, anchor=None, xact=False, relay=None, hunt=None)


def reset(ids):
    S.update(ids=ids, painted=set(), bad=set(), trail=[], goal=None, goal_age=0, seen=None, mode="CLEAR", pend={}, lpath=None, holding=set(),
             anchor=None, xact=False, relay=None, hunt=None)  # zones = map data, rebuilt by bind()


def bind(send, cgrid_lines=None, region=None):
    """send = dk1gym.send; cgrid_lines = the answer of the bridge `cgrid` (header 'G w h mapW mapH' + h rows)."""
    S["send"] = send
    S["region"] = region  # fn(x, y) -> open-region label (0 blocked); goals outside the leader's region would hang GeneratePath
    S["grid"] = None
    if cgrid_lines and cgrid_lines[0].startswith("G "):
        w, h, mw, mh = map(int, cgrid_lines[0].split()[1:5])
        S["grid"] = dict(w=w, h=h, mw=mw, mh=mh, rows=cgrid_lines[1:1 + h])
    _build_zones()


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


def _build_zones():
    """Zones = 4-connected open paint cells inside one ZONE_CELLS block; adjacency = 4-neighbour cells of different zones."""
    S.update(zones=[], zof={}, zadj={})
    if not S["grid"]:
        return
    x0, y0, x1, y1 = _bounds()
    op = {(i, j) for i in range(int(x0 // CELL), int(x1 // CELL)) for j in range(int(y0 // CELL), int(y1 // CELL)) if not blocked(*_ctr((i, j)))}
    zs, zof = S["zones"], S["zof"]
    for c0 in sorted(op):
        if c0 in zof:
            continue
        b = (c0[0] // ZONE_CELLS, c0[1] // ZONE_CELLS)
        mem, st = [], [c0]
        zof[c0] = len(zs)
        while st:
            c = st.pop(); mem.append(c)
            for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                if n in op and n not in zof and (n[0] // ZONE_CELLS, n[1] // ZONE_CELLS) == b:
                    zof[n] = len(zs); st.append(n)
        mx, my = sum(c[0] for c in mem) / len(mem), sum(c[1] for c in mem) / len(mem)
        zs.append(dict(cells=mem, size=len(mem), c=min(mem, key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)))
    S["zadj"] = {i: set() for i in range(len(zs))}
    for (i, j), a in zof.items():
        for n in ((i + 1, j), (i, j + 1)):
            b = zof.get(n)
            if b is not None and b != a:
                S["zadj"][a].add(b); S["zadj"][b].add(a)


def _zone_of(x, y):
    """Zone index at a point (nearest zone cell within 3 cells when the point is on a wall); None = none."""
    c = _cell(x, y)
    z = S["zof"].get(c)
    for r in range(1, 4):
        if z is not None:
            break
        near = [S["zof"][(c[0] + i, c[1] + j)] for i in range(-r, r + 1) for j in range(-r, r + 1) if (c[0] + i, c[1] + j) in S["zof"]]
        z = near[0] if near else None
    return z


def _order(a):
    """Zones within HUNT_HOPS of zone a: BFS hop order, ties by distance from a's centroid."""
    hop, q = {a: 0}, [a]
    for z in q:
        if hop[z] < HUNT_HOPS:
            for n in sorted(S["zadj"][z]):
                if n not in hop:
                    hop[n] = hop[z] + 1; q.append(n)
    ca = S["zones"][a]["c"]
    return sorted(hop, key=lambda z: (hop[z], math.hypot(S["zones"][z]["c"][0] - ca[0], S["zones"][z]["c"][1] - ca[1])))


def _big(z):
    sz = sorted(q["size"] for q in S["zones"])
    return S["zones"][z]["size"] > BIG_ZONE * sz[len(sz) // 2]


def _cps(z):
    """Checkpoint cells of zone z: centroid (+2 far-apart cells if big) + POIS inside."""
    zz = S["zones"][z]
    cp = [zz["c"]]
    if _big(z):
        d = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
        f1 = max(zz["cells"], key=lambda c: d(c, zz["c"]))
        f2 = max(zz["cells"], key=lambda c: min(d(c, zz["c"]), d(c, f1)))
        cp += [c for c in (f1, f2) if c not in cp]
    for p in POIS:
        c = _cell(*p)
        if S["zof"].get(c) == z and c not in cp:
            cp.append(c)
    return cp


def _anchor_contact(t, s):
    """Contact: anchor = contact trooper's zone now, the suspect's exact zone once RELAY_TICKS passed (or already exact)."""
    S["hunt"] = None
    if S["xact"]:
        z = _zone_of(s["x"], s["y"])
        if z is not None:
            S["anchor"] = z
    elif S["relay"] is None:
        z = _zone_of(t["x"], t["y"])
        if z is not None:
            S["anchor"] = z
        S["relay"] = dict(tid=t["id"], pos=(s["x"], s["y"]), left=RELAY_TICKS)
    else:
        S["relay"]["pos"] = (s["x"], s["y"])


def _relay_step(ids):
    r = S["relay"]
    if not r:
        return
    r["left"] -= 1
    if r["tid"] not in ids:
        S["relay"] = None  # reporter died: anchor stays at its zone
    elif r["left"] <= 0:
        z = _zone_of(*r["pos"])
        if z is not None and z != S["anchor"]:
            S["anchor"] = z; S["hunt"] = None
        S["xact"] = True; S["relay"] = None


def _hunt(troopers, want, force):
    """One HUNT tick; False = every zone within HUNT_HOPS is searched (caller drops the anchor)."""
    zs, a = S["zones"], S["anchor"]
    h = S["hunt"]
    if h is None or h["a"] != a:
        order = _order(a)
        h = S["hunt"] = dict(a=a, order=order, done=set(), asg={}, tgt={}, age={}, pend={z: _cps(z) for z in order})
    done, asg, tgt, age, pend = h["done"], h["asg"], h["tgt"], h["age"], h["pend"]
    for t in troopers:
        i = t["id"]
        if i not in tgt:
            continue
        z, c = tgt[i]
        age[i] = age.get(i, 0) + 1
        if z in done:
            del tgt[i]
        elif math.hypot(_ctr(c)[0] - t["x"], _ctr(c)[1] - t["y"]) < GOAL_REACHED:
            pend[z].remove(c); del tgt[i]
        elif age[i] > GOAL_PATIENCE and t["wps"] == 0:
            pend[z].remove(c); del tgt[i]  # unreachable
        elif t["wps"] == 0 and age[i] > 2:
            force.add(i)
    for z in h["order"]:
        if z not in done and (not pend[z] or sum(c in S["painted"] for c in zs[z]["cells"]) >= SEARCHED_FRAC * zs[z]["size"]):
            done.add(z)
    todo = [z for z in h["order"] if z not in done]
    if not todo:
        return False
    for i in [i for i, z in asg.items() if z in done]:
        del asg[i]
    cnt = lambda z: sum(1 for v in asg.values() if v == z)
    for slot in (1, 2):  # first pass: one trooper per zone; second: leftovers double up in big zones
        for z in todo:
            needy = [t for t in troopers if t["id"] not in asg]
            if not needy:
                break
            if cnt(z) < slot and (slot == 1 or _big(z)):
                cz = _ctr(zs[z]["c"])
                asg[min(needy, key=lambda t: math.hypot(cz[0] - t["x"], cz[1] - t["y"]))["id"]] = z
    for t in troopers:
        i = t["id"]
        z = asg.get(i)
        while z is not None and i not in tgt:
            taken = {c for k, (zz, c) in tgt.items() if zz == z}
            free = [c for c in pend[z] if c not in taken]
            if not free:
                break
            c = min(free, key=lambda c: math.hypot(_ctr(c)[0] - t["x"], _ctr(c)[1] - t["y"]))
            if _route(t, c) is None:
                pend[z].remove(c); continue
            tgt[i] = (z, c); age[i] = 0; force.add(i)
        if i in tgt:
            want[i] = _ctr(tgt[i][1])
    return True


def feedback(ids, answers):
    """ids = trooper ids of the last move batch (same order as answer lines); blacklist a goal that had no path."""
    h = S["hunt"]
    for i, a in zip(ids, answers):
        if h and a.startswith("ERR") and i in h["tgt"]:
            z, c = h["tgt"].pop(i)
            if c in h["pend"][z]:
                h["pend"][z].remove(c)
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
    _relay_step(set(ids))
    # contact? suspect in LOS within CONTACT_R, or very close
    contact = [(t, s) for t in troopers for s in suspects
               if (lambda d: d <= CLOSE_R or (d <= CONTACT_R and los(t["x"], t["y"], s["x"], s["y"])))(math.hypot(s["x"] - t["x"], s["y"] - t["y"]))]
    force, thr = set(), {}
    if contact:
        cx = sum(t["x"] for t in troopers) / len(troopers)
        cy = sum(t["y"] for t in troopers) / len(troopers)
        t0, s = min(contact, key=lambda ts: math.hypot(ts[1]["x"] - cx, ts[1]["y"] - cy))
        _anchor_contact(t0, s)
        S["seen"] = (s["x"], s["y"]); S["mode"] = "ENGAGE"
        S["goal"] = None; S["lpath"] = None
        _engage(troopers, s, want := {}, force)
        S["pend"] = dict(leader=None)
    elif S["anchor"] is not None and S["zones"] and _hunt(troopers, want := {}, force):
        S["mode"] = "HUNT"; S["holding"] = set(); S["goal"] = None; S["lpath"] = None
        S["pend"] = dict(leader=None)
    else:
        if S["anchor"] is not None:  # hunt finished: forget the anchor, sweep
            S.update(anchor=None, xact=False, relay=None, hunt=None, seen=None)
        S["mode"] = "CLEAR"; S["holding"] = set()
        leader = next((t for t in troopers if t["id"] == S["ids"][0]), None) or troopers[0]
        S["trail"].append((leader["x"], leader["y"])); del S["trail"][:-TRAIL_MAX]
        want = {}
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


if __name__ == "__main__":  # offline self-test: two rooms + corridor, anchor set, no suspects -> HUNT zone goals, then CLEAR
    OPEN = {(i, j) for i in range(1, 7) for j in range(1, 9)} | {(i, j) for i in range(7, 13) for j in (4, 5)} \
        | {(i, j) for i in range(13, 19) for j in range(1, 9)}
    rows = ["".join("." if (gx // 8, gy // 8) in OPEN else "#" for gx in range(160)) for gy in range(80)]
    bind(None, ["G 160 80 640 320"] + rows)
    PAINT_R = 40  # troopers paint only their own cell, so zones are searched by walking
    ids = [1, 2, 3]
    tr = [dict(id=i, x=_ctr((2, 2 + i))[0], y=_ctr((2, 2 + i))[1], wps=0) for i in ids]
    reset(ids)
    nz = len(S["zones"]); print("zones", nz, "adj", sum(len(v) for v in S["zadj"].values()) // 2)
    assert nz >= 6 and all(S["zadj"][z] for z in range(nz))
    S["anchor"] = _zone_of(tr[0]["x"], tr[0]["y"])
    last, first, hunted = {}, None, 0
    for tick in range(60):
        out = orders(tr, [], last)
        last.update(out)
        if S["mode"] == "HUNT":
            hunted += 1
            zg = [z for z, c in S["hunt"]["tgt"].values()]
            if first is None:
                first = zg
                assert len(zg) == 3 and len(set(zg)) == 3, zg  # distinct zone goals
            assert all(S["hunt"]["a"] == S["anchor"] for _ in [0])
        for t in tr:  # teleport to the ordered goal
            if t["id"] in last:
                t["x"], t["y"] = last[t["id"]]
        if S["mode"] == "CLEAR" and S["anchor"] is None:
            break
    assert hunted >= 2 and S["anchor"] is None and S["mode"] == "CLEAR", (hunted, S["mode"], S["anchor"])
    # relay: contact at room B by trooper 1 -> anchor = its zone, 2 ticks later = suspect's zone, alive check
    reset(ids); sx, sy = _ctr((16, 3)); tr[0]["x"], tr[0]["y"] = _ctr((15, 3))
    orders(tr, [dict(x=sx, y=sy)], {}); z0 = S["anchor"]; assert z0 == _zone_of(tr[0]["x"], tr[0]["y"])
    orders(tr, [], {}); orders(tr, [], {}); assert S["anchor"] == _zone_of(sx, sy) and S["xact"]
    print("selftest ok: hunted %d ticks, first zone goals %s, zones %d" % (hunted, first, nz))
