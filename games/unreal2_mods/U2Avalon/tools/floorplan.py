r"""Floor plans for Avalon's small buildings, from real plans: houses, offices, the clinic, the checkpoint, the bar,
the store, the shanties. rooms.py calls it for those (BY_ID / BY_KIND); the halls, dorms, mess, pumps and the tower
keep their own programmes there.

    py tools/floorplan.py [only=directors_house,plant_office] [seed=1] [out=data\floorplans\floorplans.json]
                          [png=data\floorplans]          (one picture per building + a contact sheet)

Where the numbers come from (.claude/skills/building-interiors, read its limits):
  * room sizes: ResPlan's measured medians and spreads (8,061 real plans, CC BY 4.0), times GAME = 1.25 in length
    (Avalon's player is 108 UU = 2.16 m tall at 50 UU/m, a real person ~1.75 m), so 1.56 in area;
  * which rooms connect: the entrance opens into the common room; bedrooms, kitchen and baths open off it; about 3
    kitchens in 4 open to it with no wall; ~60% of baths are en-suite (behind their bedroom, never off the hall);
    bedrooms sit side by side behind walls; private rooms deep, public ones at the front (the intimacy gradient);
  * the player (redesign/2026-10-09/facts_measured.md): every room >= 1.6 m across (2 x 28 UU + margin);
  * the kit (shells.py): a door is a 4 m panel column, so a wall with a door is >= 4 m long and holds one door per
    4 m; storeys are 3.4 m; exterior windows go on whole sides (window_sides).

How: per building a programme (rooms with target areas, zones, who they open to), then a search over layouts (a
public band along the front with the common room and maybe the kitchen, the private rooms in slots behind it, an
en-suite bath behind its bedroom, a passage through the back band when there is a back door; offices: rows either
side of a corridor), each scored on area error, proportions, minimum widths, doors that fit, daylight, privacy and
the sheet's doors landing in the common space. The best is written in rooms.py's schema plus:
  walls        the interior partitions (level, z, ends, height, doors at offsets from the centre, open = no wall)
  window_sides the shell sides that get window panels (every side a living room touches)
  graph        rooms and their connections (door / open) and each room's steps from the entrance
  doors        the shell doors moved so each lands in the common space
  notes        what the plan couldn't meet, and the numbers behind it
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
STATS = os.path.join(REPO, ".claude", "skills", "building-interiors", "reference", "resplan_stats.json")

M = 50.0
GAME = 1.25                  # length scale, real -> Avalon
STOREY = 3.4
DOOR_COL = 3.2               # the shortest wall that takes a door: the kit's 4 m door panel scaled to 0.8 (shells.py),
                             # which keeps the opening at 80 UU (rooms.checks)
MIN_SIDE = 1.6               # 2 x 28 UU + 24 (rooms.checks)
CORRIDOR = 2.4               # the dorms' corridor
DOOR_P = (1.6, 2.8)          # rooms.DOOR_P
DOOR_R = (5.0, 5.0)

# real-plan medians (m2, narrow side m), overwritten from the skill's numbers when present
REAL = {"living": (33.45, 6.56), "bedroom": (14.62, 3.54), "bathroom": (3.85, 1.57), "kitchen": (8.21, 2.56),
        "storage": (2.66, 1.38)}
SPREAD = {k: (0.75, 1.3) for k in REAL}       # p25/p50, p75/p50 (overwritten too)
try:
    _S = json.load(open(STATS))
    for k in REAL:
        r = _S["rooms"][k]
        REAL[k] = (r["area_m2"]["p50"], r["short_side_m"]["p50"])
        SPREAD[k] = (r["area_m2"]["p25"] / r["area_m2"]["p50"], r["area_m2"]["p75"] / r["area_m2"]["p50"])
except (OSError, KeyError, ValueError):
    _S = None

# room types beyond the real-plan set: (area m2 real, narrow side m real) from building practice (rules.md)
RULES = {"office": (12.0, 3.0), "meeting": (20.0, 3.6), "reception": (20.0, 3.5), "wc_block": (8.0, 2.0),
         "treatment": (12.0, 3.0), "waiting": (12.0, 3.0), "guard": (12.0, 3.0), "lockers": (5.0, 1.6),
         "bar": (25.0, 4.0), "store": (6.0, 2.0), "shop": (25.0, 4.0), "study": (10.0, 2.8), "shack": (14.0, 3.0),
         "sleeping": (6.0, 2.0), "stair": (9.0, 2.4)}
HABITABLE = {"living", "bedroom", "kitchen", "office", "meeting", "reception", "treatment", "waiting", "guard", "bar",
             "shop", "study", "shack", "sleeping"}
MAX_ASPECT = {"living": 2.6, "bedroom": 1.8, "bathroom": 2.6, "kitchen": 2.4, "office": 2.0, "meeting": 2.0, "stair": 3.0,
              "storage": 3.0, "store": 3.0, "wc_block": 3.0, "lockers": 3.0, "passage": 99, "corridor": 99}


def target(kind):
    a, s = REAL.get(kind) or RULES.get(kind) or (10.0, 2.5)
    return a * GAME * GAME, max(MIN_SIDE, s * GAME * 0.85)


# ---- programmes -----------------------------------------------------------------------------------------------
def programme(bid, sheet, W, D):
    """[(id, kind, label, zone, opens_to)]: zone hub (the common space), front (in the public band) or back;
    opens_to: 'hub', a room id (en-suite), or 'open' (no wall to the hub)"""
    beds = int(sheet.get("beds") or 0)
    area = W * D
    P = []
    if bid in ("guest_house",):
        P.append(("lounge", "living", "guest lounge + kitchenette", "hub", None))
        for k in range(max(2, min(4, beds or 3))):
            P.append(("room_%d" % (k + 1), "bedroom", "guest room %d" % (k + 1), "back", "hub", 9 - 2 * k))
            P.append(("bath_%d" % (k + 1), "bathroom", "en-suite %d" % (k + 1), "back", "room_%d" % (k + 1), 8 - 2 * k))
        return P
    if bid in ("directors_house",) or (sheet.get("kind") == "house" and area >= 90):
        nb = max(2, min(3, (beds + 1) // 2 or 2))
        P += [("living", "living", "living + hall", "hub", None),
              ("kitchen", "kitchen", "kitchen", "front", "open" if random.random() < 0.75 else "hub")]
        P.append(("bedroom_1", "bedroom", "main bedroom", "back", "hub", 9))
        P.append(("ensuite", "bathroom", "en-suite", "back", "bedroom_1", 4))
        for k in range(2, nb + 1):
            P.append(("bedroom_%d" % k, "bedroom", "bedroom %d" % k, "back", "hub", 8 - k))
        P.append(("bath", "bathroom", "bathroom", "back", "hub", 7))
        if bid == "directors_house":
            P.append(("study", "study", "study (company papers)", "back", "hub", 3))
        return P
    if sheet.get("kind") == "office" or bid == "plant_office":
        return "office"
    if bid == "clinic":
        return [("waiting", "waiting", "waiting room", "hub", None), ("treatment", "treatment", "treatment room", "back", "hub")]
    if bid == "checkpoint":
        return [("guard", "guard", "guard room (window to the road)", "hub", None), ("lockers", "lockers", "lockers + WC", "back", "hub")]
    if bid == "tin_bar":
        return [("bar", "bar", "bar room (counter)", "hub", None), ("store", "store", "back store", "back", "hub")]
    if bid == "company_store":
        return [("shop", "shop", "shop floor (counter)", "hub", None), ("store", "store", "stock room", "back", "hub")]
    if bid.startswith("shanty"):
        return [("shack", "shack", "one room (cooking corner, bunks)", "hub", None),
                ("sleeping", "sleeping", "sleeping corner (curtain)", "back", "hub")]
    if bid == "staff_houses":
        return [("living", "living", "living + kitchenette", "hub", None), ("bedroom", "bedroom", "bedroom", "back", "hub", 9),
                ("bath", "bathroom", "shower room", "back", "living", 5)]
    if area < 20:
        return [("main", "living", "one room", "hub", None)]
    return [("living", "living", "living + hall", "hub", None), ("kitchen", "kitchen", "kitchen", "front", "open"),
            ("bedroom", "bedroom", "bedroom", "back", "hub"), ("bath", "bathroom", "bathroom", "back", "hub")]


# ---- geometry helpers ----------------------------------------------------------------------------------------
def rect(rid, kind, label, x0, y0, x1, y1, space=None):
    return {"id": rid, "kind": kind, "label": label, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "space": space or rid}


def shared(a, b):
    """the shared edge of two rects: (orientation, fixed coord, lo, hi) or None"""
    e = 1e-6
    if abs(a["x1"] - b["x0"]) < e or abs(b["x1"] - a["x0"]) < e:
        x = a["x1"] if abs(a["x1"] - b["x0"]) < e else a["x0"]
        lo, hi = max(a["y0"], b["y0"]), min(a["y1"], b["y1"])
        if hi - lo > 0.05:
            return ("v", x, lo, hi)
    if abs(a["y1"] - b["y0"]) < e or abs(b["y1"] - a["y0"]) < e:
        y = a["y1"] if abs(a["y1"] - b["y0"]) < e else a["y0"]
        lo, hi = max(a["x0"], b["x0"]), min(a["x1"], b["x1"])
        if hi - lo > 0.05:
            return ("h", y, lo, hi)
    return None


def dims(r):
    w, d = r["x1"] - r["x0"], r["y1"] - r["y0"]
    return w, d, w * d, min(w, d), max(w, d) / max(min(w, d), 1e-6)


def on_shell(r, W, D):
    return [s for s, c in (("front", r["y0"] <= -D / 2 + 1e-6), ("back", r["y1"] >= D / 2 - 1e-6),
                           ("left", r["x0"] <= -W / 2 + 1e-6), ("right", r["x1"] >= W / 2 - 1e-6)) if c]


# ---- the band layout (houses and small buildings) ---------------------------------------------------------------
def band_layout(prog, W, D, sheet, rng):
    """one candidate: public band (depth h) along the front, private slots behind it"""
    hub = next(p for p in prog if p[3] == "hub")
    front = [p for p in prog if p[3] == "front"]
    back = [p for p in prog if p[3] == "back"]
    tot_t = sum(target(p[1])[0] for p in prog)
    scale = W * D / max(tot_t, 1e-6)
    t = {p[0]: target(p[1])[0] * min(1.0, scale) for p in prog}
    # groups in the back band: a room and the en-suite behind it travel together
    groups, used = [], set()
    for p in back:
        if p[0] in used:
            continue
        g = [p]
        used.add(p[0])
        for q in back:
            if q[4] == p[0] and q[0] not in used:
                g.append(q)
                used.add(q[0])
        groups.append(g)
    rng.shuffle(groups)
    sd = sheet.get("doors") or {}
    has = lambda side: sd.get(side, "none") not in ("none", None)
    passages = set()
    if groups:
        if has("back"):
            passages.add(rng.randint(0, len(groups)))
        if has("left") and rng.random() < 0.6:
            passages.add(0)
        if has("right") and rng.random() < 0.6:
            passages.add(len(groups))
        if rng.random() < 0.4:
            passages.add(rng.randint(0, len(groups)))      # a hall reaching back: rooms open off its sides too
    h = rng.uniform(MIN_SIDE * 1.5, max(MIN_SIDE * 1.5, D - MIN_SIDE)) if groups else D
    b = D - h
    R = []
    # the public band: the common room, the kitchen at one end
    x0 = -W / 2
    kit = front[0] if front else None
    kw = 0.0
    if kit:
        kw = max(target(kit[1])[1], min(W * 0.45, t[kit[0]] / h * rng.uniform(0.85, 1.2)))
        if rng.random() < 0.5:
            R.append(rect(kit[0], kit[1], kit[2], -W / 2, -D / 2, -W / 2 + kw, -D / 2 + h))
            R.append(rect(hub[0], hub[1], hub[2], -W / 2 + kw, -D / 2, W / 2, -D / 2 + h))
        else:
            R.append(rect(hub[0], hub[1], hub[2], -W / 2, -D / 2, W / 2 - kw, -D / 2 + h))
            R.append(rect(kit[0], kit[1], kit[2], W / 2 - kw, -D / 2, W / 2, -D / 2 + h))
    else:
        R.append(rect(hub[0], hub[1], hub[2], -W / 2, -D / 2, W / 2, -D / 2 + h))
    if not groups:
        return R
    # the back band: slots by area (a passage slot is part of the common space)
    slots = []
    for k, g in enumerate(groups):
        if k in passages:
            slots.append(("passage", None))
        slots.append(("group", g))
    if len(groups) in passages:
        slots.append(("passage", None))
    pw = CORRIDOR * rng.uniform(0.8, 1.4)
    weights = [pw * b if s[0] == "passage" else sum(t[q[0]] for q in s[1]) * rng.uniform(0.7, 1.3) for s in slots]
    free = W
    xs = -W / 2
    tw = sum(weights)
    for k, (kind, g) in enumerate(slots):
        w = W * weights[k] / tw if k < len(slots) - 1 else W / 2 - xs
        x1 = xs + w
        if kind == "passage":
            R.append(rect(hub[0] + "_hall", "passage", "hall", xs, -D / 2 + h, x1, D / 2, space=hub[0]))
        else:
            main = g[0]
            if len(g) == 1:
                R.append(rect(main[0], main[1], main[2], xs, -D / 2 + h, x1, D / 2))
            else:
                # the en-suite deepest, behind its room (the intimacy gradient)
                bd = rng.uniform(MIN_SIDE, max(MIN_SIDE, b - MIN_SIDE))
                R.append(rect(main[0], main[1], main[2], xs, -D / 2 + h, x1, D / 2 - bd))
                R.append(rect(g[1][0], g[1][1], g[1][2], xs, D / 2 - bd, x1, D / 2))
        xs = x1
    return R


def connections(R, prog, rng_open):
    """edges: (a, b, 'door' | 'open'); a room opens to its programme target through its longest shared edge"""
    by = {r["id"]: r for r in R}
    want = {p[0]: p[4] for p in prog}
    hub = next(p[0] for p in prog if p[3] == "hub")
    space = {r["id"]: r["space"] for r in R}
    E = []
    for r in R:
        if r["space"] != r["id"] and r["space"] == hub:
            E.append((r["id"], hub, "open"))          # the passage is the hall
            continue
        if r["id"] == hub:
            continue
        w = want.get(r["id"])
        if w in (None,):
            continue
        tgt_space = hub if w in ("hub", "open") else w
        best = None
        for o in R:
            if space.get(o["id"]) != tgt_space and o["id"] != tgt_space:
                continue
            s = shared(r, o)
            if s and (best is None or s[3] - s[2] > best[1][3] - best[1][2]):
                best = (o["id"], s)
        if best is None:
            E.append((r["id"], tgt_space, "none"))
            continue
        E.append((r["id"], best[0], "open" if w == "open" else "door"))
    return E


def score(R, E, prog, W, D, sheet):
    s = 0.0
    notes = []
    want = {p[0]: p for p in prog}
    for r in R:
        w, d, a, short, asp = dims(r)
        if r["kind"] == "passage":
            if short < MIN_SIDE:
                s += 50
            continue
        p = want.get(r["id"])
        tA, tS = target(r["kind"])
        s += 3.0 * abs(a - tA) / tA * (0.4 if p and p[3] == "hub" else 1.0)
        if asp > MAX_ASPECT.get(r["kind"], 2.4):
            s += 4.0 * (asp - MAX_ASPECT.get(r["kind"], 2.4))
        if short < MIN_SIDE:
            s += 60
        elif short < tS:
            s += 6.0 * (tS - short) / tS
        if r["kind"] in HABITABLE and not on_shell(r, W, D):
            s += 8                                        # no daylight
        if r["kind"] == "bedroom" and "front" in on_shell(r, W, D):
            s += 3                                        # private rooms deep
    for a, b, k in E:
        if k == "none":
            s += 100
            continue
        if k == "door":
            sh = shared(next(r for r in R if r["id"] == a), next(r for r in R if r["id"] == b))
            if sh is None or sh[3] - sh[2] < DOOR_COL - 1e-6:
                s += 80                                   # the kit's door panel doesn't fit
    # the sheet's doors must land in the common space
    hub = next(p[0] for p in prog if p[3] == "hub")
    for side, kind in (sheet.get("doors") or {}).items():
        if kind in ("none", None):
            continue
        need = DOOR_R[0] + 0.5 if kind == "roller" else DOOR_COL
        span = sum((r["x1"] - r["x0"]) if side in ("front", "back") else (r["y1"] - r["y0"])
                   for r in R if r["space"] == hub and side in on_shell(r, W, D))
        if span < min(need, (W if side in ("front", "back") else D)) - 1e-6:
            s += 40
    return s


def hard(R, E, prog, W, D, sheet):
    """the rules a plan must not break: rooms the player fits through, doors the kit can build, every room reached"""
    out = []
    for r in R:
        if dims(r)[3] < MIN_SIDE - 1e-6:
            out.append("%s %.1f m across" % (r["id"], dims(r)[3]))
    for a, b, k in E:
        if k == "none":
            out.append("%s has no wall with %s" % (a, b))
        elif k == "door":
            sh = shared(next(r for r in R if r["id"] == a), next(r for r in R if r["id"] == b))
            if sh is None or sh[3] - sh[2] < DOOR_COL - 1e-6:
                out.append("%s-%s wall %.1f m" % (a, b, (sh[3] - sh[2]) if sh else 0))
    return out


def search(prog, W, D, sheet, rng, tries):
    best = None
    for _ in range(tries):
        R = band_layout(prog, W, D, sheet, rng)
        E = connections(R, prog, rng)
        sc = score(R, E, prog, W, D, sheet)
        if best is None or sc < best[0]:
            best = (sc, R, E)
    return best


def place_shell_doors(R, prog, W, D, sheet):
    hub = next(p[0] for p in prog if p[3] == "hub")
    out, notes = [], []
    for side, kind in (sheet.get("doors") or {}).items():
        if kind in ("none", None) or side not in ("front", "back", "left", "right"):
            continue
        cands = [r for r in R if r["space"] == hub and side in on_shell(r, W, D)]
        if not cands:
            cands = [r for r in R if side in on_shell(r, W, D)]
            notes.append("the %s door opens into %s, not the common space" % (side, cands[0]["id"] if cands else "?"))
        r = max(cands, key=lambda r: (r["x1"] - r["x0"]) if side in ("front", "back") else (r["y1"] - r["y0"]))
        x = (r["x0"] + r["x1"]) / 2 if side in ("front", "back") else (-W / 2 if side == "left" else W / 2)
        y = (r["y0"] + r["y1"]) / 2 if side in ("left", "right") else (-D / 2 if side == "front" else D / 2)
        w, hh = DOOR_R if kind == "roller" else DOOR_P
        out.append({"side": side, "kind": kind, "x": round(x, 2), "y": round(y, 2), "z": 0.0, "w": w, "h": hh,
                    "uu": [round(w * M), round(hh * M)], "to": r["id"]})
    return out, notes


# ---- offices: rows either side of a corridor, the same on every level ------------------------------------------
def office_layout(W, D, levels, rng):
    f = (D - CORRIDOR) / 2 * rng.uniform(0.85, 1.15)
    n = max(2, int(W // 4.4))
    widths = [W / n] * n
    lobby = n // 2
    plans = []
    for lv in range(levels):
        R = []
        y_c0, y_c1 = -D / 2 + f, -D / 2 + f + CORRIDOR
        R.append(rect("corridor_%d" % lv, "corridor", "corridor", -W / 2, y_c0, W / 2, y_c1))
        x = -W / 2
        for k, w in enumerate(widths):
            if lv == 0 and k == lobby:
                R.append(rect("lobby", "reception", "reception + lobby", x, -D / 2, x + w, y_c0, space="corridor_0"))
            else:
                kind = "meeting" if (lv > 0 and k == lobby) else "office"
                R.append(rect("office_%d_f%d" % (lv, k), kind, "meeting room" if kind == "meeting" else "office", x, -D / 2, x + w, y_c0))
            x += w
        x = -W / 2
        for k, w in enumerate(widths):
            if k == 0:
                R.append(rect("stair_%d" % lv, "stair", "stair", x, y_c1, x + w, D / 2))
            elif k == n - 1:
                R.append(rect("wc_%d" % lv, "wc_block", "WCs", x, y_c1, x + w, D / 2))
            else:
                R.append(rect("office_%d_b%d" % (lv, k), "office", "office", x, y_c1, x + w, D / 2))
            x += w
        plans.append(R)
    return plans


# ---- assembly ------------------------------------------------------------------------------------------------
def walls_of(R, E, level, z, h, W, D):
    """interior partitions: every shared edge between two rooms of different spaces, a door where an edge carries one"""
    by = {r["id"]: r for r in R}
    links = {}
    for a, b, k in E:
        links[frozenset((a, b))] = k
    out = []
    for i, a in enumerate(R):
        for b in R[i + 1:]:
            s = shared(a, b)
            if not s:
                continue
            k = links.get(frozenset((a["id"], b["id"])))
            same = a["space"] == b["space"]
            ori, c, lo, hi = s
            x0, y0, x1, y1 = (lo, c, hi, c) if ori == "h" else (c, lo, c, hi)
            wall = {"level": level, "z": z, "x0": round(x0, 2), "y0": round(y0, 2), "x1": round(x1, 2), "y1": round(y1, 2),
                    "h": round(h, 2), "between": [a["id"], b["id"]], "doors": [], "open": same or k == "open"}
            if k == "door" and not same:
                wall["doors"].append({"t": 0.0, "kind": "personnel", "w": DOOR_P[0], "h": DOOR_P[1]})
            out.append(wall)
    return out


def graph(R, E, entry):
    adj = {r["id"]: set() for r in R}
    for a, b, k in E:
        if k in ("door", "open"):
            adj[a].add(b)
            adj[b].add(a)
    dist, q = {entry: 0}, [entry]
    while q:
        c = q.pop(0)
        for n in adj[c]:
            if n not in dist:
                dist[n] = dist[c] + 1
                q.append(n)
    return {"edges": [[a, b, k] for a, b, k in E], "steps_from_entrance": dist,
            "unreached": sorted(r["id"] for r in R if r["id"] not in dist)}


def to_rooms(R, E, level, z, h):
    out = []
    door_to = {a: b for a, b, k in E if k == "door"}
    open_to = {}
    for a, b, k in E:
        if k == "open":
            open_to.setdefault(a, []).append(b)
    for r in R:
        w, d, a, short, asp = dims(r)
        rr = {"id": r["id"], "name": r["label"], "level": level, "x": round((r["x0"] + r["x1"]) / 2, 2), "y": round((r["y0"] + r["y1"]) / 2, 2),
              "z": round(z, 2), "w": round(w, 2), "d": round(d, 2), "h": round(h, 2), "uu": [round(w * M), round(d * M), round(h * M)],
              "kind": r["kind"], "area_m2": round(a, 1), "space": r["space"]}
        if r["id"] in door_to:
            rr["door_to"] = door_to[r["id"]]
        if r["id"] in open_to:
            rr["open_to"] = open_to[r["id"]]
        if r["kind"] in ("corridor", "passage") or r["space"] != r["id"]:
            rr["circulation"] = True
        out.append(rr)
    return out


def plan(bid, sheet, W, D, H, seed=1, tries=4000):
    """-> (levels, rooms, stairs, extra) for rooms.plan(); extra carries walls, window_sides, graph, doors, notes"""
    rng = random.Random("%s:%s" % (bid, seed))
    random.seed("%s:%s:prog" % (bid, seed))
    prog = programme(bid, sheet, W, D)
    levels = max(1, int(H // STOREY))
    notes = []
    if prog == "office":
        best = None
        for _ in range(60):
            L = office_layout(W, D, levels, rng)
            sc = sum(score(R, [], [], W, D, {}) if False else 0 for R in L)
            areas = [dims(r)[2] for R in L for r in R if r["kind"] == "office"]
            sc = sum(abs(a - target("office")[0]) / target("office")[0] for a in areas) + \
                 sum(60 for R in L for r in R if dims(r)[3] < MIN_SIDE)
            if best is None or sc < best[0]:
                best = (sc, L)
        L = best[1]
        rooms, walls, stairs, edges, steps = [], [], [], [], {}
        h = STOREY - 0.3
        for lv, R in enumerate(L):
            z = lv * STOREY
            corr = "corridor_%d" % lv
            E = [(r["id"], corr, "open" if r["space"] == corr else "door") for r in R if r["id"] != corr]
            rooms += to_rooms(R, E, lv, z, h)
            walls += walls_of(R, E, lv, z, h, W, D)
            edges += [[a, b, k] for a, b, k in E]
            st = next(r for r in R if r["kind"] == "stair")
            if lv:
                rise = STOREY * M
                n = max(1, math.ceil(rise / 35))
                stairs.append({"kind": "stair", "x": round((st["x0"] + st["x1"]) / 2, 2), "y": round((st["y0"] + st["y1"]) / 2, 2),
                               "z0": z - STOREY, "z1": z, "risers": n, "riser_uu": round(rise / n, 1), "tread_uu": 28,
                               "width": 1.6, "run_m": round(n * 28 / M, 2), "landings": 0})
        sides = ["front", "back", "left", "right"]
        sheet_doors = dict(sheet.get("doors") or {})
        doors = []
        for side, kind in sheet_doors.items():
            if kind in ("none", None):
                continue
            if side == "front":
                lob = next(r for r in rooms if r["id"] == "lobby")
                x, y = lob["x"], -D / 2
            elif side in ("left", "right"):
                x, y = (-W / 2 if side == "left" else W / 2), -D / 2 + (D - CORRIDOR) / 2 + CORRIDOR / 2
            else:
                x, y = 0.0, D / 2
                notes.append("a back door opens into a back-row room (offices have no back passage)")
            w, hh = DOOR_R if kind == "roller" else DOOR_P
            doors.append({"side": side, "kind": kind, "x": round(x, 2), "y": round(y, 2), "z": 0.0, "w": w, "h": hh,
                          "uu": [round(w * M), round(hh * M)]})
        notes.append("offices: %d per row of %.1f m, a %.1f m corridor, stair and WCs stacked on every level" % (
            sum(1 for r in rooms if r["kind"] == "office" and r["level"] == 0), W / max(2, int(W // 4.4)), CORRIDOR))
        extra = {"walls": walls, "window_sides": sides, "doors": doors, "notes": notes,
                 "graph": {"edges": edges}, "generator": "floorplan.py office rows"}
        return levels, rooms, stairs, extra
    # search; while the best breaks a hard rule, drop the least important room (its en-suite with it) and search again
    dropped = []
    while True:
        sc, R, E = search(prog, W, D, sheet, rng, tries)
        bad = hard(R, E, prog, W, D, sheet)
        cand = [p for p in prog if len(p) > 5]
        if not bad or not cand:
            break
        drop = min(cand, key=lambda p: p[5])
        gone = {drop[0]} | {p[0] for p in prog if p[4] == drop[0]}
        prog = [p for p in prog if p[0] not in gone]
        dropped.append((drop[2], bad[:2]))
    for name, why in dropped:
        notes.append("left out the %s: the footprint has no room for it (%s)" % (name, "; ".join(why)))
    h = (H if levels == 1 else STOREY) - 0.3
    hub = next(p[0] for p in prog if p[3] == "hub")
    rooms = to_rooms(R, E, 0, 0.0, h)
    walls = walls_of(R, E, 0, 0.0, h, W, D)
    doors, dn = place_shell_doors(R, prog, W, D, sheet)
    notes += dn
    G = graph(R, E, hub)
    sides = sorted({s for r in R if r["kind"] in HABITABLE for s in on_shell(r, W, D)})
    for r in R:
        w, d, a, short, asp = dims(r)
        if r["kind"] == "passage":
            continue
        tA, tS = target(r["kind"])
        if short < MIN_SIDE:
            notes.append("%s is %.1f m across, under the player's %.1f m" % (r["id"], short, MIN_SIDE))
        if r["kind"] in REAL:
            lo, hi = tA * SPREAD[r["kind"]][0], tA * SPREAD[r["kind"]][1]
            if not lo * 0.7 <= a <= hi * 1.3:
                notes.append("%s %.0f m2 is outside the real plans' usual range scaled to Avalon (%.0f-%.0f m2)" % (r["id"], a, lo, hi))
    for a, b, k in E:
        if k == "door":
            s = shared(next(r for r in R if r["id"] == a), next(r for r in R if r["id"] == b))
            if s and s[3] - s[2] < DOOR_COL - 1e-6:
                notes.append("%s-%s: the shared wall is %.1f m, under the kit's 4 m door column" % (a, b, s[3] - s[2]))
        if k == "none":
            notes.append("%s has no wall in common with %s: no door" % (a, b))
    if G["unreached"]:
        notes.append("not reachable from the entrance: " + ", ".join(G["unreached"]))
    # counters (a low solid block; shells.py draws cover: full as one)
    for r in rooms:
        if r["kind"] in ("bar", "shop"):
            rooms.append({"id": r["id"] + "_counter", "name": "counter", "level": 0, "x": r["x"], "y": round(r["y"] + r["d"] * 0.15, 2),
                          "z": 0.0, "w": round(min(r["w"] * 0.6, 4.0), 2), "d": 0.9, "h": 1.1, "uu": [round(min(r["w"] * 0.6, 4.0) * M), 45, 55],
                          "cover": "full", "kind": "counter"})
            break
    extra = {"walls": walls, "window_sides": sides, "doors": doors, "notes": notes, "graph": G, "score": round(sc, 2),
             "generator": "floorplan.py band layout (%d tried)" % tries}
    return levels, rooms, [], extra


# ---- pictures --------------------------------------------------------------------------------------------------
COLOURS = {"living": (230, 190, 120), "passage": (230, 190, 120), "kitchen": (240, 150, 90), "bedroom": (140, 180, 230),
           "bathroom": (120, 210, 210), "study": (170, 160, 230), "office": (170, 200, 160), "meeting": (200, 220, 140),
           "reception": (230, 190, 120), "corridor": (220, 200, 160), "stair": (180, 180, 180), "wc_block": (120, 210, 210),
           "waiting": (230, 190, 120), "treatment": (240, 170, 200), "guard": (230, 190, 120), "lockers": (180, 180, 200),
           "bar": (230, 170, 110), "store": (180, 170, 150), "shop": (230, 190, 120), "shack": (210, 180, 140),
           "sleeping": (150, 170, 210), "counter": (90, 70, 60)}


def draw(bid, p, path, scale=28):
    from PIL import Image, ImageDraw
    W, D, H = p["shell_m"]
    levels = p["levels"]
    pad = 40
    iw = int(W * scale) + pad * 2
    img = Image.new("RGB", (iw * levels, int(D * scale) + pad * 2 + 70), (250, 250, 247))
    dr = ImageDraw.Draw(img)
    for lv in range(levels):
        ox, oy = lv * iw + pad, pad + 30
        X = lambda x: ox + (x + W / 2) * scale
        Y = lambda y: oy + (D / 2 - y) * scale             # front (-y) at the bottom of the picture
        for r in p["rooms"]:
            if r["level"] != lv or r.get("kind") == "counter":
                continue
            c = COLOURS.get(r.get("kind"), (200, 200, 200))
            dr.rectangle([X(r["x"] - r["w"] / 2), Y(r["y"] + r["d"] / 2), X(r["x"] + r["w"] / 2), Y(r["y"] - r["d"] / 2)], fill=c)
        for r in p["rooms"]:
            if r["level"] == lv and r.get("kind") == "counter":
                dr.rectangle([X(r["x"] - r["w"] / 2), Y(r["y"] + r["d"] / 2), X(r["x"] + r["w"] / 2), Y(r["y"] - r["d"] / 2)], fill=COLOURS["counter"])
        for w in p.get("walls", []):
            if w["level"] != lv or w["open"]:
                continue
            dr.line([X(w["x0"]), Y(w["y0"]), X(w["x1"]), Y(w["y1"])], fill=(40, 40, 40), width=3)
            for d in w["doors"]:
                cx, cy = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
                hz = abs(w["y0"] - w["y1"]) < 1e-6
                half = d["w"] / 2
                a = (X(cx - half), Y(cy)) if hz else (X(cx), Y(cy - half))
                b = (X(cx + half), Y(cy)) if hz else (X(cx), Y(cy + half))
                dr.line([a, b], fill=(250, 250, 247), width=5)
                dr.line([a, b], fill=(60, 160, 60), width=1)
        dr.rectangle([X(-W / 2), Y(D / 2), X(W / 2), Y(-D / 2)], outline=(20, 20, 20), width=4)
        for s in p.get("window_sides", []):
            if lv >= levels:
                continue
            seg = {"front": (X(-W / 2), Y(-D / 2), X(W / 2), Y(-D / 2)), "back": (X(-W / 2), Y(D / 2), X(W / 2), Y(D / 2)),
                   "left": (X(-W / 2), Y(-D / 2), X(-W / 2), Y(D / 2)), "right": (X(W / 2), Y(-D / 2), X(W / 2), Y(D / 2))}[s]
            dr.line(seg, fill=(80, 140, 230), width=2)
        for d in p.get("doors", []):
            if d.get("z", 0) != lv * STOREY and not (lv == 0 and d.get("z", 0) == 0):
                continue
            if lv:
                continue
            hz = d["side"] in ("front", "back")
            half = d["w"] / 2
            a = (X(d["x"] - half), Y(d["y"])) if hz else (X(d["x"]), Y(d["y"] - half))
            b = (X(d["x"] + half), Y(d["y"])) if hz else (X(d["x"]), Y(d["y"] + half))
            dr.line([a, b], fill=(250, 250, 247), width=6)
            dr.line([a, b], fill=(220, 60, 60), width=2)
        for st in p.get("stairs", []):
            if abs(st["z1"] - lv * STOREY) < 0.01 or abs(st["z0"] - lv * STOREY) < 0.01:
                for i in range(st["risers"]):
                    xx = st["x"] - st["run_m"] / 2 + (i + 0.5) * st["run_m"] / st["risers"]
                    dr.line([X(xx), Y(st["y"] - st["width"] / 2), X(xx), Y(st["y"] + st["width"] / 2)], fill=(90, 90, 90), width=1)
        for r in p["rooms"]:
            if r["level"] != lv or r.get("kind") == "counter":
                continue
            label = "%s\n%.0f m2" % (r["name"].split(" (")[0], r["w"] * r["d"])
            dr.multiline_text((X(r["x"] - r["w"] / 2) + 4, Y(r["y"] + r["d"] / 2) + 4), label, fill=(20, 20, 20))
        dr.text((ox, oy - 24), "level %d" % lv, fill=(20, 20, 20))
        dr.text((ox, oy + D * scale + 8), "front (entrance side)", fill=(120, 120, 120))
    dr.text((pad, 8), "%s  %.0f x %.0f m (%d x %d UU)   red: shell doors, green: inner doors, blue: window sides, 1 m = %d px" % (
        bid, W, D, W * M, D * M, scale), fill=(20, 20, 20))
    img.save(path)
    return img


def contact_sheet(images, path, cols=3):
    from PIL import Image
    if not images:
        return
    cw = max(i.width for i in images)
    ch = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols, ch * rows), (250, 250, 247))
    for k, im in enumerate(images):
        sheet.paste(im, ((k % cols) * cw, (k // cols) * ch))
    sheet.save(path)


IDS = ["directors_house", "guest_house", "plant_office", "staff_houses", "clinic", "checkpoint", "tin_bar", "company_store",
       "shanty_a", "shanty_b", "shanty_c"]


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import binder  # noqa
    import rooms  # noqa
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    only = o["only"].split(",") if o.get("only") else IDS
    seed = o.get("seed", "1")
    _, sheets = binder.load()
    outdir = os.path.join(HERE, "data", "floorplans")
    os.makedirs(outdir, exist_ok=True)
    pngdir = o.get("png", outdir)
    plans, imgs = {}, []
    for bid in only:
        if bid not in sheets:
            print("  %s: no sheet" % bid)
            continue
        p = rooms.plan(bid, dict(sheets[bid], _seed=seed), {r: s for r, s in binder.load_rooms().items() if s.get("in") == bid})
        if p is None:
            continue
        plans[bid] = p
        imgs.append(draw(bid, p, os.path.join(pngdir, "%s.png" % bid)))
        print("  %-16s %s m, %d level(s), %2d rooms, %2d walls, %d door(s)%s" % (
            bid, p["shell_m"], p["levels"], len(p["rooms"]), len(p.get("walls", [])), len(p["doors"]),
            "".join("\n      - " + n for n in p.get("notes", []))))
    json.dump(plans, open(o.get("out", os.path.join(outdir, "floorplans.json")), "w"), indent=1)
    contact_sheet(imgs, os.path.join(pngdir, "all.png"))
    print("%d plans -> %s" % (len(plans), outdir))
