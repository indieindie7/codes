r"""Motion for the command room's view: plumes, trucks and the staged reveal, written as U2AvalonCards.ini keys.

    py tools/motion.py <layout.json> [ini=<U2AvalonCards.ini>] [trucks=2] [reveal=1] [cards=auto|all|none]

The cinematography report (games/reports/Cinematography and concept art for the Avalon town.md): motion pulls
the eye and makes a still view read as a living place; a truck beside a hall tells its size. All of it runs in
the mutator (AvalonPlume / AvalonTruck / AvalonFlyer), so it can be tuned without rebuilding the map.
  * plumes from the building sheets' `motion:` key ("steam", "smoke" or "flare"): steam over the cooling
    towers, smoke over the generator, the rig's flare;
  * trucks shuttling the spine road (dock <-> mine), the ore run;
  * the reveal: the first time the player comes down off the command deck, a dropship makes one low pass
    from the dock over the town and past the tower.
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import binder  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
TOWER = (-349.0, 1388.0)
DECK_Z = 4238.0
TRUCK_MESH = "Terran_DecoM.Vehicles.crane_cab"

layout_path = [a for a in sys.argv[1:] if "=" not in a][0]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
INI = o.get("ini", os.path.join(GAME, "System", "U2AvalonCards.ini"))
L = json.load(open(layout_path))
_, sheets = binder.load()

# kind -> (width, rise) in world units
PLUME = {"smoke": (0, 520, 3000), "steam": (1, 1000, 3800), "flare": (2, 450, 400)}
plumes = []
for bid, b in L["buildings"].items():
    m = sheets.get(bid, {}).get("motion")
    if not m:
        continue
    kind = m.split()[0]
    frac = float(m.split()[1]) if len(m.split()) > 1 else 0.9    # where on the building (of its height)
    k, width, rise = PLUME[kind]
    card = sheets[bid].get("card")
    if card and len(card.split()) > 1:
        lift = frac * float(card.split()[1])     # a card: over the ground under it
    else:
        lift = 60.0                              # a mesh: the trace stops on its roof
    plumes.append("%.0f %.0f %.0f %d %.0f %.0f" % (b["x"], b["y"], lift, k, width, rise))

# the spine as a polyline every ~600 units
sp = L.get("spine") or []
path = []
for x, y in sp:
    if not path or math.hypot(x - path[-1][0], y - path[-1][1]) >= 600:
        path.append((x, y))
if sp and path[-1] != tuple(sp[-1]):
    path.append(tuple(sp[-1]))
paths = [" ".join("%.0f %.0f" % p for p in path)] if len(path) >= 2 else []
NT = int(o.get("trucks", 2))
trucks = ["%s 1.5 650 0 %.2f 0" % (TRUCK_MESH, (i + 0.5) / NT) for i in range(NT)] if paths else []

# the reveal: from out over the dock, low, past the tower's decks and on inland, climbing
dock = L["buildings"].get("dock") or L["buildings"].get("cargo_pad")
reveal = {}
if dock and o.get("reveal", "1") != "0":
    dx, dy = TOWER[0] - dock["x"], TOWER[1] - dock["y"]
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    side = 2500                                   # passes beside the tower, not through it
    start = min(d, 14000)                         # close enough to read as a ship within a few seconds
    fx, fy = TOWER[0] - ux * start - uy * side, TOWER[1] - uy * start + ux * side
    tx, ty = TOWER[0] + ux * 14000 - uy * side, TOWER[1] + uy * 14000 + ux * side
    reveal = {"RevealBelowZ": "%.0f" % (DECK_Z - 300), "RevealSpeed": "3200", "RevealScale": "1.0",
              "RevealFrom": "(X=%.0f,Y=%.0f,Z=%.0f)" % (fx, fy, DECK_Z - 1500),
              "RevealTo": "(X=%.0f,Y=%.0f,Z=%.0f)" % (tx, ty, DECK_Z + 2600),
              "RevealSound": "CinemaA.Dropship.Dropship_PassbyFast2"}

# the round-2 concept buildings as 8-view cards (Extras[], "Name X Y Yaw Size 8"), each facing the tower:
#  * the Liandri landmark - the crane temple-tower from the low-sun paint-over - on the highest ground in
#    the command room's window, sized so its top stands over the Authority's tower (the company looms
#    over the backwater post);
#  * a row of blue A-frame huts along the cliff edge in the window view (the Sana huts, staff housing);
#  * dorm pods by dorm C, Tin Row shacks round the Tin Bar
# cards=auto (default): an Extra is left out when the run has a real mesh for its sheet - the export placed a
#   StaticMeshActor for it (<run>\isl_actors.t3d, or hollow.json: the shells hold it) or the sheet's mesh:/model:
#   names a mesh (the hero's `model: PyramidTower`, Q83) - on a remake map the card would stand twice over the
#   building. cards=all writes every Extra (the old behaviour, TutA's own map with no meshes); cards=none writes no Extras.
CARDS = o.get("cards", "auto")
if CARDS not in ("auto", "all", "none"):
    raise SystemExit("cards=auto|all|none")
CARD_NAMES = ("CraneTower", "AFrameHut", "DormPod", "TinShack")
EXTRA_SHEET = {"CraneTower": None, "AFrameHut": "staff_houses", "DormPod": "dorm_c", "TinShack": "tin_bar"}   # None: the parti's hero


def placed_meshes(run):
    """(x, y) of every StaticMeshActor the export wrote for this run (isl_actors.t3d), or None when there is no T3D"""
    t3d = os.path.join(run, "isl_actors.t3d")
    if not os.path.exists(t3d):
        return None
    return [(float(x), float(y)) for x, y in re.findall(r"Class=StaticMeshActor[^E]*?Location=\(X=([-\d.]+),Y=([-\d.]+)", open(t3d).read())]


def has_mesh(bid, placed, hollow):
    """the run has a real mesh for the sheet: the export placed one within 6 m of its layout point (or of a counted
    copy: the block's half extent is added), the shells hold it, or its sheet names a mesh (not a card name, not none)"""
    b, sh = L["buildings"].get(bid), sheets.get(bid, {})
    if not b:
        return False
    if bid in hollow:
        return True
    if placed:
        w, d = (sh.get("size") or [0, 0, 0])[:2]
        n = max([int(v) for v in re.findall(r"\d+", sh.get("count", "1"))] + [1])
        rad = 300 + max(w, d) * 50.0 * 1.5 * (n - 1) / 2
        if any(math.hypot(px - b["x"], py - b["y"]) < rad for px, py in placed):
            return True
    m = (sh.get("mesh") or sh.get("model") or "").split()
    return bool(m) and m[0].lower() != "none" and m[0] not in CARD_NAMES


def extra_sheet(card):
    if EXTRA_SHEET[card] is not None:
        return EXTRA_SHEET[card]
    try:
        return json.load(open(os.path.join(os.path.dirname(HERE), "binder", "parti.json"))).get("hero") or "liandri_tower"
    except Exception:
        return "liandri_tower"


def keep_extra(card, placed, hollow, dropped):
    if CARDS == "all":
        return True
    if CARDS == "none":
        return False
    bid = extra_sheet(card)
    if has_mesh(bid, placed, hollow):
        dropped.setdefault(card, bid)
        return False
    return True


import numpy as np
import compose  # noqa  (the heightmap reader and the window frame)
Z = compose._heights(L["heightmap"])


def ground(x, y):
    return float(compose._bil(Z, np.array([x]), np.array([y]))[0])


def face(x, y):
    return math.degrees(math.atan2(TOWER[1] - y, TOWER[0] - x)) % 360


extras = []
dropped = {}
if o.get("extras", "1") != "0" and CARDS != "none":
    RUN_ = os.path.dirname(os.path.abspath(layout_path))
    placed = placed_meshes(RUN_)
    hollow = set()
    if os.path.exists(os.path.join(RUN_, "hollow.json")):
        hollow = set(json.load(open(os.path.join(RUN_, "hollow.json"))).get("hollow", []))
    best = None
    for r in range(15000, 46000, 250):         # beyond the town: the mountain behind it, not in front of the glass
        for a in range(int(compose.LOOK_YAW - 17), int(compose.LOOK_YAW - 8), 1):   # the left third (the hero cooling towers hold the right)
            x, y = TOWER[0] + r * math.cos(math.radians(a)), TOWER[1] + r * math.sin(math.radians(a))
            g = ground(x, y)
            if g > compose.SEA_Z + 50 and (best is None or g > best[0]):
                best = (g, x, y)
    if best and keep_extra("CraneTower", placed, hollow, dropped):
        g, x, y = best
        size = max(3500.0, (DECK_Z + 2600 - g) / 0.92)     # top ~50 m over the Authority's command deck
        extras.append("CraneTower %.0f %.0f %.0f %.0f 8" % (x, y, face(x, y), size))
    for a in (range(int(compose.LOOK_YAW - 26), int(compose.LOOK_YAW + 27), 6) if keep_extra("AFrameHut", placed, hollow, dropped) else ()):   # the cliff-edge row
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        r = 1500
        while r < 20000 and ground(TOWER[0] + r * ca, TOWER[1] + r * sa) > compose.SEA_Z + 30:
            r += 100
        r -= 700
        if r > 2000:
            x, y = TOWER[0] + r * ca, TOWER[1] + r * sa
            extras.append("AFrameHut %.0f %.0f %.0f 420 8" % (x, y, face(x, y)))
    for bid, card, size, n, rad in (("dorm_c", "DormPod", 380, 4, 1100), ("tin_bar", "TinShack", 260, 3, 700)):
        b = L["buildings"].get(bid)
        if not b or not keep_extra(card, placed, hollow, dropped):
            continue
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            x, y = b["x"] + rad * math.cos(a), b["y"] + rad * math.sin(a)
            extras.append("%s %.0f %.0f %.0f %d 8" % (card, x, y, face(x, y), size))

# the company loudspeakers (AvalonPA): over the plant office, the dorms, Tin Row and the dock
spots = ["%.0f %.0f 700" % (L["buildings"][b]["x"], L["buildings"][b]["y"])
         for b in ("plant_office", "dorm", "tin_bar", "dock") if b in L["buildings"]]

# the layout's own things go to the family's section (family=, from town.py); wind and the reveal stay global
import avalon_ini  # noqa
avalon_ini.edit(INI, o.get("family"), ("Plumes", "Trucks", "Paths", "PASpots", "Extras"),
                ["Plumes[%d]=%s" % (k, p) for k, p in enumerate(plumes[:16])]
                + ["Paths[%d]=%s" % (k, p) for k, p in enumerate(paths[:4])]
                + ["Trucks[%d]=%s" % (k, t) for k, t in enumerate(trucks[:8])]
                + ["PASpots[%d]=%s" % (k, p) for k, p in enumerate(spots[:6])]
                + ["Extras[%d]=%s" % (k, e) for k, e in enumerate(extras[:48])])
avalon_ini.edit(INI, None, ("Wind",) + tuple(reveal.keys()) if reveal else ("Wind",),
                ["Wind=(X=60,Y=-40,Z=0)"] + ["%s=%s" % kv for kv in reveal.items()])
print("%d plumes, %d trucks on a %d-point road, reveal %s -> %s" % (len(plumes), len(trucks), len(path), "on" if reveal else "off", INI))
for p in plumes:
    print("  plume", p)
for e in extras:
    print("  card", e)
for card, bid in dropped.items():
    print("  no %s cards: the run has a real mesh for %s (cards=%s)" % (card, bid, CARDS))
