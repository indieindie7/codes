"""Read the Avalon binder (binder/citizens/*.md, binder/buildings/*.md) and check it.

    python tools/binder.py            check: prints problems and door-side suggestions, exit 1 if any rule breaks
    python tools/binder.py dump       the parsed sheets as JSON

As a library: load() -> (citizens, buildings) dicts of dicts; the header 'key: value' lines are the fields,
'at'/'size' are parsed to numbers, 'doors' to {side: type}, 'users'/'bays' to lists, 'routine' to
[(minutes, building_id)]. Everything below the first blank line is prose and ignored.
"""
import glob, json, math, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINDER = os.path.join(HERE, "binder")
SIDES = ("front", "back", "left", "right")
DOOR_TYPES = ("personnel", "roller", "airlock", "none")


def parse(path):
    d = {"_file": os.path.basename(path)}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            break
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        d[k.strip()] = v.strip()
    for k in ("users", "bays"):
        d[k] = d.get(k, "").split()
    if "at" in d:
        w = d["at"].split()
        d["at"] = (float(w[0]), float(w[1]), float(w[2]) if len(w) > 2 else 0.0)
    if "size" in d:
        d["size"] = tuple(float(v) for v in d["size"].split())
    if "doors" in d:
        doors = {}
        for item in d["doors"].split():
            side, _, typ = item.partition(":")
            doors[side] = typ or "personnel"
        d["doors"] = doors
    if "routine" in d:
        r = []
        for item in d["routine"].split(";"):
            w = item.split()
            if len(w) >= 2:
                r.append((int(w[0][:2]) * 60 + int(w[0][2:]), w[1]))
        d["routine"] = r
    d["wear"] = float(d.get("wear", 0) or 0)
    d["lit"] = d.get("lit", "yes").lower() == "yes"
    d["abandoned"] = d.get("abandoned", "no").lower() == "yes"
    return d


def load():
    citizens = {}
    for p in sorted(glob.glob(os.path.join(BINDER, "citizens", "*.md"))):
        c = parse(p)
        citizens[c["id"]] = c
    buildings = {}
    for p in sorted(glob.glob(os.path.join(BINDER, "buildings", "*.md"))):
        b = parse(p)
        buildings[b["id"]] = b
    return citizens, buildings


def side_toward(b, target):
    """which side of building b (front = its yaw) faces the point target=(along, across)"""
    ax, ay, yaw = b["at"]
    # the look frame is rotated 300 degrees from world; a front yaw in world terms -> in-frame direction
    ang = math.radians(yaw - 300.0)
    dx, dy = target[0] - ax, target[1] - ay
    f = dx * math.cos(ang) + dy * math.sin(ang)
    s = -dx * math.sin(ang) + dy * math.cos(ang)
    if abs(f) >= abs(s):
        return "front" if f > 0 else "back"
    return "left" if s > 0 else "right"


def check(citizens, buildings, verbose=True):
    problems, notes = [], []
    for c in citizens.values():
        for key in ("lives", "works"):
            if c.get(key) and c[key] not in buildings:
                problems.append(f"{c['id']}: {key} '{c[key]}' is not a building")
        for _, bid in c.get("routine", []):
            if bid not in buildings:
                problems.append(f"{c['id']}: routine goes to '{bid}', not a building")
    users = {bid: set() for bid in buildings}
    arrivals = {bid: [] for bid in buildings}        # (from building) for door-side suggestions
    for c in citizens.values():
        for key in ("lives", "works"):
            if c.get(key) in users:
                users[c[key]].add(c["id"])
        r = c.get("routine", [])
        for k, (_, bid) in enumerate(r):
            if bid in users:
                users[bid].add(c["id"])
                prev = r[k - 1][1] if k else None
                if prev and prev != bid and prev in buildings:
                    arrivals[bid].append(prev)
    for bid, b in buildings.items():
        declared = set(b["users"])
        if not b["abandoned"] and not (declared | users[bid]):
            problems.append(f"{bid}: nobody uses it and it is not marked abandoned")
        missing = users[bid] - declared
        if missing:
            notes.append(f"{bid}: used in routines by {sorted(missing)} but not in its users: line")
        if b["abandoned"] and (b["wear"] < 0.6 or b["lit"]):
            problems.append(f"{bid}: abandoned but wear {b['wear']} / lit {b['lit']}")
        doors = b.get("doors", {})
        for side in doors:
            if side not in SIDES:
                problems.append(f"{bid}: door side '{side}'")
        if arrivals[bid] and doors and "at" in b:
            want = set()
            for prev in arrivals[bid]:
                if "at" in buildings[prev]:
                    want.add(side_toward(b, buildings[prev]["at"][:2]))
            if want and not (want & set(doors)):
                problems.append(f"{bid}: people arrive from the {sorted(want)} side(s) but the doors are on {sorted(doors)}")
    # growth rings: a core building of a kind should be nearer the old pad than a boom one of the same kind
    core_pad = buildings.get("cargo_pad")
    if core_pad and "at" in core_pad:
        by_kind = {}
        for b in buildings.values():
            if "at" in b and b.get("layer") in ("core", "boom"):
                by_kind.setdefault(b.get("kind"), []).append(b)
        for kind, bs in by_kind.items():
            cores = [math.dist(b["at"][:2], core_pad["at"][:2]) for b in bs if b["layer"] == "core"]
            booms = [math.dist(b["at"][:2], core_pad["at"][:2]) for b in bs if b["layer"] == "boom"]
            if cores and booms and min(cores) > max(booms):
                notes.append(f"{kind}: every core one is farther from the pad than every boom one (rings reversed?)")
    # G.U.A.R.D.S. (Loot Goblin Marketplace): every settlement needs government, underworld, altar, resources,
    # defenses and a social hub, all on one theme; a missing one is a hole the player feels, an imbalance is a story
    FUNCTIONS = {"government": {"tower", "plant_office", "authority_pad"}, "underworld": {"boat_landing", "dead_rig", "old_camp"},
                 "altar": set(), "resources": {"dock", "cargo_pad", "fuel_depot", "silos"}, "defenses": {"checkpoint", "authority_pad"},
                 "social": set()}
    for bid, b in buildings.items():
        for f in b.get("function", "").split():
            FUNCTIONS.setdefault(f, set()).add(bid)
    for f, ids in FUNCTIONS.items():
        present = [i for i in ids if i in buildings and not buildings[i].get("abandoned")]
        if not present:
            problems.append(f"GUARDS: no {f} building (add one or tag a sheet with 'function: {f}')")
    if verbose:
        for p in problems:
            print("PROBLEM", p)
        for n in notes:
            print("note", n)
        print(f"{len(citizens)} citizens, {len(buildings)} buildings, {len(problems)} problems, {len(notes)} notes")
    return problems, notes


if __name__ == "__main__":
    citizens, buildings = load()
    if len(sys.argv) > 1 and sys.argv[1] == "dump":
        print(json.dumps({"citizens": citizens, "buildings": buildings}, indent=1, default=str))
    else:
        problems, _ = check(citizens, buildings)
        sys.exit(1 if problems else 0)
