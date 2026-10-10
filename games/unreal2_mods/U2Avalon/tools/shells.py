r"""Hollow-shell interiors from rooms.json (rooms.py): per building, StaticMeshActors of the kit parts (kit_parts.py,
AvalonSM.Liandri.B_k_*) that replace the solid building mesh - walls with real door and window openings, floor and
roof slabs, partitions with doors, upper slabs, gratings with rails, stairs from single steps, ladders, door frames by
owner and the plinth. The hulls in the parts (MCDCX_) keep the doorways walkable. A plan with a "facade" (facade.py,
the floor-plan buildings) gets its outside walls bay by bay from it, plus its canopies and cornice.

    py tools/shells.py <run folder with rooms.json + isl_layout.json> [out=<run>\isl_shells.t3d] [only=hall_b,dorm]
                       [all=1] [pkg=AvalonSM.Liandri] [plinth_m=1.2] [shell=rooms|sheet]

Default set (plan.md s. 5 + the tower lobby): hall_b (processing hall, with the control room on its uphill gable),
pump_house, dorm, mess, and tower (the Authority tower's lobby: written to a SEPARATE isl_shells_tower.t3d because it
stands where TutA's own tower BSP is; the importer decides). all=1 shells every plan that has rooms.
Also writes <run>\hollow.json {"hollow": [ids]} for export_mutator.py hollow=<file>, which then skips those
buildings' solid meshes (every instance of a `count:` building is shelled).

Frames: rooms.json is in the building's local metres (x along the width, y along the depth, FRONT = -y, z up from
the ground floor); Unreal local = (X = -y, Y = x, Z = z) x 50, then the layout's yaw and world point. Slabs: B_k_slab
is 0.3 m (15 UU) thick with its TOP at the actor Z, so a floor at level z has its walk surface at z; the roof slab
sits at H + 15 UU (underside at H). Gratings: 0.1 m (5 UU), top at the actor Z. Walls: 0.3 m (15 UU) thick, on the
footprint line. Stairs: B_k_step per riser, DrawScale3D Z = riser / 34 UU (rooms.py keeps risers <= 35), Y = width /
1.6 m. Doors: personnel 100 x 140 UU, main 128 x 192, roller 250 x 250 (the panels' openings).
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa
import story_export as se  # noqa  (actor(), rot(), PIVOTS)

M = 50.0
STOREY = 3.4
PANEL = 4.0
DEFAULT = ["hall_b", "pump_house", "dorm", "mess", "tower"]
WINDOW_SIDES = {"dorm": ("front", "back"), "office": ("front", "left", "right"), "house": ("front", "left", "right"),
                "hall": ("front", "back")}          # halls: the top band only (the clerestory)
DOOR_PART = {"personnel": ("B_k_wall_door", PANEL, STOREY), "main": ("B_k_wall_main", PANEL, 4.4), "roller": ("B_k_wall_roller", 6.0, 6.0)}
FRAME = {"liandri": {"personnel": "B_k_frame_p", "main": "B_k_frame_m"}, "authority": {"personnel": "B_k_frame_p_auth", "main": "B_k_frame_p_auth"}}


class Shell:
    def __init__(self, plan, sheet, world, pkg=None, plinth_m=1.2):
        self.p, self.sheet, self.w, self.pkg = plan, sheet, world, pkg
        self.W, self.D, self.H = plan["shell_m"]
        self.yaw = math.radians(world["yaw"])
        self.A = []
        self.plinth_m = plinth_m
        self.seen = set()

    # --- frames ---
    def world_of(self, x, y, z):
        """room-local metres -> world UU"""
        X, Y = -y * M, x * M
        wx, wy, _ = se.rot((X, Y, 0.0), self.yaw)
        return self.w["x"] + wx, self.w["y"] + wy, self.w["z"] + z * M

    def put(self, part, x, y, z, yaw_local_deg, sx=1.0, sy=1.0, sz=1.0, pitch=0.0):
        """an actor by its authored origin at room-local (x, y, z) metres; yaw_local in Unreal-local degrees"""
        wx, wy, wz = self.world_of(x, y, z)
        self.A.append(se.actor(part, wx, wy, wz, self.yaw + math.radians(yaw_local_deg), pitch, sx, sy, sz, self.pkg))

    # --- a wall run: panels along a line, doors as features ---
    def wall_run(self, origin, along, yaw_deg, length, H, doors, windows, interior=False, z0=0.0):
        """origin = room-local (x, y) of the run's centre; along = unit vector (room frame) of the panel's +X;
        doors = [(t, kind)] at offsets t from the centre; windows = True for window panels on the full bands"""
        plain = "B_k_wall_in" if interior else "B_k_wall"
        dpart = {"personnel": "B_k_wall_door_in" if interior else "B_k_wall_door", "main": "B_k_wall_main", "roller": "B_k_wall_roller"}
        feats = sorted(doors, key=lambda d: d[0])
        cols = []
        t = -length / 2
        for td, kind in feats:
            part, pw, ph = DOOR_PART.get(kind, DOOR_PART["personnel"])
            pw = min(pw, length)                 # a short wall (>= 3.2 m, floorplan.py) takes the door panel scaled down
            a = max(t, min(td - pw / 2, length / 2 - pw))
            if a - t > 0.05:
                cols.append((t, a, None))
            cols.append((a, a + pw, (dpart[kind] if kind in dpart else part, pw, min(ph, H))))
            t = a + pw
        if length / 2 - t > 0.05:
            cols.append((t, length / 2, None))
        for a, b, door in cols:
            if door is None:
                n = max(1, int(math.ceil((b - a) / PANEL - 1e-6)))
                w = (b - a) / n
                for i in range(n):
                    tc = a + (i + 0.5) * w
                    self.bands(origin, along, yaw_deg, tc, w / PANEL, 0.0, H, plain, windows, z0)
            else:
                part, pw, ph = door
                tc = (a + b) / 2
                full = DOOR_PART.get(next((k for k, v in DOOR_PART.items() if v[0] == part), "personnel"), DOOR_PART["personnel"])[1]
                sx = 1.0 if pw >= full - 1e-6 else pw / full
                self.put(part, origin[0] + along[0] * tc, origin[1] + along[1] * tc, z0, yaw_deg, sx, 1.0, 1.0)
                self.bands(origin, along, yaw_deg, tc, pw / PANEL, ph, H, plain, windows, z0, door_over=True)
        return cols

    def bands(self, origin, along, yaw_deg, tc, sx, zlo, zhi, plain, windows, z0, door_over=False):
        """storey bands from zlo to zhi in one column: plain panels Z-scaled, window panels on full 3.4 bands"""
        edges = sorted({zlo, zhi} | {k * STOREY for k in range(1, int(zhi / STOREY) + 1) if zlo < k * STOREY < zhi})
        nb = len(edges) - 1
        fulls = [i for i in range(nb) if abs(edges[i + 1] - edges[i] - STOREY) < 0.05]
        for i in range(nb):
            a, b = edges[i], edges[i + 1]
            if b - a < 0.05:
                continue
            full = i in fulls
            win = windows and full and not (door_over and i == 0)
            if windows == "top":
                win = fulls and i == fulls[-1] and nb > 1        # the clerestory: the highest full band
            part = "B_k_wall_win" if win else plain
            self.put(part, origin[0] + along[0] * tc, origin[1] + along[1] * tc, z0 + a, yaw_deg, sx, 1.0, (b - a) / STOREY)

    # --- the exterior ---
    SIDES = {  # side: (centre (x, y), along (room unit vector = the panel's +X), Unreal-local yaw, along-of(door))
        "front": (lambda W, D: (0, -D / 2), (1, 0), 90, lambda d: d["x"]),
        "back": (lambda W, D: (0, D / 2), (-1, 0), -90, lambda d: -d["x"]),
        "left": (lambda W, D: (-W / 2, 0), (0, -1), 0, lambda d: -d["y"]),
        "right": (lambda W, D: (W / 2, 0), (0, 1), 180, lambda d: d["y"]),
    }

    def exterior(self):
        W, D, H = self.W, self.D, self.H
        kind = self.sheet.get("kind")
        owner = self.sheet.get("owner")
        wsides = self.p.get("window_sides") or WINDOW_SIDES.get(kind, ())   # floorplan.py: every side a living room touches
        for side, (centre, along, yaw, tof) in self.SIDES.items():
            length = W if side in ("front", "back") else D
            doors = [(tof(d), d["kind"]) for d in self.p["doors"] if d["side"] == side and d.get("z", 0) == 0]
            windows = ("top" if kind == "hall" else True) if side in wsides else False
            c = centre(W, D)
            if self.p.get("facade"):
                self.facade_side(side, c, along, yaw)
            else:
                self.wall_run(c, along, yaw, length, H, doors, windows)
            # door frames by owner (orange = company, steel = authority, none = nobody)
            for td, dk in doors:
                fp = FRAME.get(owner, {}).get(dk)
                if fp:
                    self.put(fp, c[0] + along[0] * td, c[1] + along[1] * td, 0.0, yaw)
            # the plinth under the wall, outside face out, the top at the floor
            n = max(1, int(math.ceil(length / PANEL - 1e-6)))
            w = length / n
            for i in range(n):
                tc = -length / 2 + (i + 0.5) * w
                self.put("B_k_plinth", c[0] + along[0] * tc, c[1] + along[1] * tc, 0.0, yaw, w / PANEL, 1.0, self.plinth_m / 1.2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.put("B_k_column", sx * (W / 2 - 0.2), sy * (D / 2 - 0.2), 0.0, 0, 1, 1, H / STOREY)
        for x in (self.p.get("facade") or {}).get("extras", []):   # canopies, the cornice
            c, along, yaw, _ = self.SIDES[x["side"]]
            c = c(W, D)
            self.put(x["part"], c[0] + along[0] * x["t"], c[1] + along[1] * x["t"], x["z"], yaw, x.get("sx", 1.0), 1.0, 1.0)
        self.slab(0, 0, W, D, 0.0)                               # the ground slab
        self.slab(0, 0, W + 0.3, D + 0.3, H + 0.3)               # the roof: underside at H
        for s in (-1, 1):                                        # a parapet
            self.wall_run((0, s * (D / 2 + 0.15)), (1, 0), 90 if s < 0 else -90, W + 0.3, 0.7, [], False, True, H + 0.3)
            self.wall_run((s * (W / 2 + 0.15), 0), (0, s), 180 if s > 0 else 0, D, 0.7, [], False, True, H + 0.3)

    def facade_side(self, side, c, along, yaw):
        """facade.py's elements for one side: each bay one part, X-scaled to the bay, Z-scaled to its band; a door
        keeps its height (Z-scaled down only if its band is lower) and its full width unless the bay is narrower"""
        for e in self.p["facade"]["elements"]:
            if e["side"] != side:
                continue
            x, y = c[0] + along[0] * e["t"], c[1] + along[1] * e["t"]
            door = next((v for v in DOOR_PART.values() if v[0] == e["part"]), None)
            if door:
                _, full, ph = door
                h = e["sz"] * STOREY
                self.put(e["part"], x, y, e["z"], yaw, min(1.0, e["w"] / full), 1.0, min(1.0, h / ph))
                if h - ph > 0.05:
                    self.put("B_k_wall", x, y, e["z"] + ph, yaw, e["w"] / PANEL, 1.0, (h - ph) / STOREY)
            else:
                self.put(e["part"], x, y, e["z"], yaw, e["w"] / PANEL, 1.0, e["sz"])

    def slab(self, x, y, w, d, z, part="B_k_slab"):
        # at yaw 0 the part's X runs along room -y (the depth) and its Y along room x (the width)
        self.put(part, x, y, z, 0, d / PANEL, w / PANEL, 1.0)

    # --- the interior ---
    def interior(self):
        W, D, H = self.W, self.D, self.H
        rooms = self.p["rooms"]
        by_id = {r["id"]: r for r in rooms}
        given = self.p.get("walls")              # floorplan.py: the exact partitions, a door where a wall carries one
        for r in rooms:
            if r.get("existing") or r.get("lift") or r.get("shown_not_given"):
                continue
            if r.get("on", "").startswith("gable stair tower"):
                self.control_room(r)
                continue
            z = r["z"]
            full_w = r["w"] >= W - 0.5 and abs(r["x"]) < 0.3
            full_d = r["d"] >= D - 0.5 and abs(r["y"]) < 0.3
            if r.get("grating"):
                self.slab(r["x"], r["y"], r["w"], r["d"], z, "B_k_grating")
                if r.get("rail") or z > 0.5:
                    self.rails(r)
                continue
            if r.get("cover") == "full":                           # a counter: a low solid block
                self.put("B_k_wall_in", r["x"], r["y"], z, 0, r["d"] / PANEL, r["w"] / 0.3, r["h"] / STOREY)
                continue
            if r["level"] >= 1 and not r["id"].startswith("stair"):
                self.slab(r["x"], r["y"], r["w"], r["d"], z)       # an upper floor piece
            if full_w and full_d:
                continue                                           # the shell itself
            if given:
                continue                                           # the partitions come from the plan (below)
            # partitions: the room's 4 sides, skipping the shell walls, a door on the side toward door_to (else
            # toward the shell's centre when the room is closed on all sides)
            target = by_id.get(r.get("door_to"))
            if r["id"].startswith(("corridor", "stair")):
                target = None
                door_side = None
            else:
                tx, ty = (target["x"], target["y"]) if target else (0.0, 0.0)
                dx, dy = tx - r["x"], ty - r["y"]
                door_side = ("right" if dx > 0 else "left") if abs(dx) * r["d"] > abs(dy) * r["w"] else ("back" if dy > 0 else "front")
            for side, (centre, along, yaw, _) in self.SIDES.items():
                cx, cy = centre(r["w"], r["d"])
                px, py = r["x"] + cx, r["y"] + cy
                on_shell = (side in ("front", "back") and abs(abs(py) - D / 2) < 0.4) or (side in ("left", "right") and abs(abs(px) - W / 2) < 0.4)
                if on_shell:
                    continue
                length = r["w"] if side in ("front", "back") else r["d"]
                key = (round(px, 1), round(py, 1), round(length, 1), side in ("front", "back"), round(z, 1))
                if key in self.seen:
                    continue
                self.seen.add(key)
                doors = [(0.0, "personnel")] if side == door_side else []
                if not doors and target is None and not r["id"].startswith(("corridor", "stair")) and side == "front":
                    doors = [(0.0, "personnel")]
                self.wall_run((px, py), along, yaw, length, min(r["h"], H - z), doors, False, True, z)
        for w in given or []:
            if w.get("open"):
                continue
            hz = abs(w["y0"] - w["y1"]) < 1e-6
            length = abs(w["x1"] - w["x0"]) if hz else abs(w["y1"] - w["y0"])
            centre = ((w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2)
            along, yaw = ((1, 0), 90) if hz else ((0, 1), 180)
            self.wall_run(centre, along, yaw, length, min(w["h"], H - w["z"]), [(d["t"], d["kind"]) for d in w["doors"]], False, True, w["z"])
        for st in self.p.get("stairs", []):
            self.stair(st)
        if self.sheet.get("kind") == "hall" and self.p["levels"] >= 2:
            top = max((r["z"] for r in rooms if r.get("grating")), default=STOREY)
            for s in (-1, 1):
                self.put("B_k_ladder", s * (W / 2 - 0.7), 0.0, 0.0, 90 if s < 0 else -90, 1, 1, top / STOREY)

    def rails(self, r):
        """B_k_rail along the grating's edges that are not against the shell"""
        W, D = self.W, self.D
        for side, (centre, along, yaw, _) in self.SIDES.items():
            cx, cy = centre(r["w"], r["d"])
            px, py = r["x"] + cx, r["y"] + cy
            on_shell = (side in ("front", "back") and abs(abs(py) - D / 2) < 0.6) or (side in ("left", "right") and abs(abs(px) - W / 2) < 0.6)
            if on_shell:
                continue
            length = r["w"] if side in ("front", "back") else r["d"]
            n = max(1, int(math.ceil(length / PANEL - 1e-6)))
            w = length / n
            # the rail stands 0.05 inside the edge (its line y = 0 is the edge; the panel's -Y is the outside)
            ix, iy = -along[1], along[0]
            for i in range(n):
                tc = -length / 2 + (i + 0.5) * w
                self.put("B_k_rail", px + along[0] * tc - ix * 0.0, py + along[1] * tc - iy * 0.0, r["z"], yaw, w / PANEL, 1, 1)

    def stair(self, st):
        """B_k_step per riser along +x from the stair's centre - run/2"""
        n = st["risers"]
        riser = (st["z1"] - st["z0"]) / n
        tread = st["tread_uu"] / M
        x0 = st["x"] - st["run_m"] / 2
        for i in range(n):
            self.put("B_k_step", x0 + (i + 0.5) * tread, st["y"], st["z0"] + i * riser, 90, 1.0, st["width"] / 1.6, riser / 0.68)
        # a landing slab at the top when the stair does not end on an upper room's slab
        top = st["z1"]
        if not any(abs(r["z"] - top) < 0.1 and abs(r["x"] - (x0 + st["run_m"] + 0.8)) < r["w"] / 2 and abs(r["y"] - st["y"]) < r["d"] / 2
                   for r in self.p["rooms"]):
            self.slab(x0 + st["run_m"] + 0.8, st["y"], 1.6, st["width"], top)

    def control_room(self, r):
        """the plant control room on the hall's gable (rooms.py control_room): a box on the roof, its +x wall of
        window panels (the sloped glass stays a note), floor + roof slabs. The gable stair tower is its stair entry."""
        w, d, h, z = r["w"], r["d"], r["h"], r["z"]
        self.slab(r["x"], r["y"], w, d, z + 0.3)                       # its floor over the hall roof
        self.slab(r["x"], r["y"], w + 0.3, d + 0.3, z + 0.3 + h + 0.3)
        for side, (centre, along, yaw, _) in self.SIDES.items():
            cx, cy = centre(w, d)
            length = w if side in ("front", "back") else d
            doors = [(0.0, "personnel")] if side == "left" else []       # the door toward the hall's catwalk bridge
            self.wall_run((r["x"] + cx, r["y"] + cy), along, yaw, length, h, doors, side == "right", False, z + 0.3)


def instances(bid, P, sheet):
    """the building's copies (count: 'AxC' / 'n along|across'), as export_mutator.instances / takes.instances"""
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
    return [dict(P, x=P["x"] + da * math.cos(a) - dc * math.sin(a), y=P["y"] + da * math.sin(a) + dc * math.cos(a)) for da, dc in pts]


def build(run, only=None, all_=False, pkg=None, plinth_m=1.2, shell="rooms"):
    R = json.load(open(os.path.join(run, "rooms.json")))
    L = json.load(open(os.path.join(run, "isl_layout.json")))
    _, sheets = binder.load()
    ids = only or (list(R) if all_ else DEFAULT)
    main, tower, hollow, report = [], [], [], []
    for bid in ids:
        plan = R.get(bid)
        if not plan or not plan.get("rooms") or bid not in L["buildings"] or bid not in sheets:
            report.append("%s: no plan / not placed" % bid)
            continue
        if bid == "drain":
            continue
        sheet = sheets[bid]
        if shell == "sheet" and "size" in sheet:
            plan = dict(plan, shell_m=list(sheet["size"]))
        if bid == "tower":
            # only the lobby is new build (the command room, deck and catwalk are TutA's own BSP): the shell is the lobby
            lobby = next((r for r in plan["rooms"] if r["id"] == "lobby"), None)
            if lobby:
                plan = dict(plan, shell_m=[lobby["w"], lobby["d"], lobby["h"]], levels=1,
                            rooms=[r for r in plan["rooms"] if r["id"] == "lobby"], stairs=[],
                            doors=[d for d in plan["doors"] if d["side"] in Shell.SIDES])
        n0 = 0
        for inst in instances(bid, L["buildings"][bid], sheet):
            sh = Shell(plan, sheet, inst, pkg, plinth_m)
            sh.exterior()
            sh.interior()
            (tower if bid == "tower" else main).extend(sh.A)
            n0 += len(sh.A)
        hollow.append(bid)
        report.append("%s: %s m, %d levels, %d rooms, %d stairs -> %d actors%s" % (
            bid, plan["shell_m"], plan["levels"], len(plan["rooms"]), len(plan.get("stairs", [])), n0,
            " (tower: separate T3D, overlaps TutA's own tower BSP)" if bid == "tower" else ""))
    return main, tower, hollow, report


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if "=" not in a]
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    if not pos:
        raise SystemExit(__doc__)
    run = pos[0]
    if run.endswith(".json"):
        run = os.path.dirname(os.path.abspath(run))
    main, tower, hollow, report = build(run, o["only"].split(",") if "only" in o else None, o.get("all") == "1", o.get("pkg"),
                                        float(o.get("plinth_m", 1.2)), o.get("shell", "rooms"))
    out = o.get("out", os.path.join(run, "isl_shells.t3d"))
    open(out, "w").write("Begin Map\n" + "\n".join(main) + "\nEnd Map\n")
    if tower:
        open(out[:-4] + "_tower.t3d", "w").write("Begin Map\n" + "\n".join(tower) + "\nEnd Map\n")
    json.dump({"hollow": hollow, "note": "export_mutator.py hollow=<this file> skips these buildings' solid meshes"},
              open(os.path.join(run, "hollow.json"), "w"), indent=1)
    for r in report:
        print(r)
    print(len(main), "shell actors ->", out, ("+ %d tower lobby actors -> %s" % (len(tower), out[:-4] + "_tower.t3d")) if tower else "",
          "; hollow:", hollow, "->", os.path.join(run, "hollow.json"))
