"""Put the binder's island into the GAME's own Avalon level (TutA) through the U2AvalonCards mutator: writes
the Props[] / Cards[] lines of System\\U2AvalonCards.ini from the building sheets. The mutator stands every
prop on whatever TutA has under it (land or its sea surface) at map load; the original map is untouched.

    python tools/export_mutator.py [<U2AvalonCards.ini>] [shift=-5300]

shift = how far to move everything back along the look (the generated map pushed the plant 5300 units out
to suit its own lower tower; TutA's shore is nearer). Meshes come from StaticMeshes\\AvalonSM.usx (world
units, origin at the bottom centre: CX CY MinZ = 0), cards from AvalonSM.Cards.<Name>0..7.
"""
import math, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))
import binder  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
_pos = [a for a in sys.argv[1:] if "=" not in a]
INI = _pos[0] if _pos else os.path.join(GAME, "System", "U2AvalonCards.ini")
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
SHIFT = float(o.get("shift", -5300))
T3D = o.get("t3d")                 # also write the buildings as StaticMeshActors in a T3D for MAP IMPORTADD
HEIGHTMAP = o.get("heightmap")     # the map's final G16 BMP: ground Z for the T3D actors (TutA frame)
WRITE_PROPS = o.get("props", "1") != "0"   # props=0: only Cards[] go to the ini (the map holds the buildings)
STORY = o.get("story", "0") == "1"         # story=1: the drain culverts and the taps' poles/cables/drums (story_export.py) into the T3D
HOLLOW = set()                             # hollow=<hollow.json from shells.py>: buildings whose solid mesh the shells replace
if o.get("hollow"):
    import json as _json0
    HOLLOW = set(_json0.load(open(o["hollow"])).get("hollow", []))
LOOK = 300.0
M = 50.0
SCRIPTED = {"tank": "StorageTank", "silo": "OreTank", "cooling": "CoolingTower", "mast": "RadioMast",
            "new_rig": "DrillingRig", "dead_rig": "DeadRig"}
ASSEMBLED = ("hall", "office", "dorm", "house", "pump", "jetty", "pad", "barge")


def from_frame(along, across):
    a = math.radians(LOOK)
    return (along * math.cos(a) - across * math.sin(a), along * math.sin(a) + across * math.cos(a))


LAYOUT = None
if o.get("layout"):
    import json as _json
    LAYOUT = _json.load(open(o["layout"]))["buildings"]


def instances(b):
    along, across, deg = b["at"]
    if LAYOUT and b["id"] in LAYOUT:
        # layout.py placed it: world position + yaw, instance offsets turned with the yaw
        L = LAYOUT[b["id"]]
        along, across, deg = None, None, L["yaw"]
    w, d = b["size"][0] * M, b["size"][1] * M
    gap = max(w, d) * 1.5
    spec = b.get("count", "1").split()
    pts = [(0, 0)]
    if "x" in spec[0].lower():                      # "3x4": a block, 3 along by 4 across (2x2 as before)
        na, nc = (int(v) for v in spec[0].lower().split("x"))
        pts = [((ka - (na - 1) / 2) * gap, (kc - (nc - 1) / 2) * gap) for kc in range(nc) for ka in range(na)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    if along is None:
        a = math.radians(deg)
        return [(L["x"] + da * math.cos(a) - dc * math.sin(a), L["y"] + da * math.sin(a) + dc * math.cos(a), deg) for da, dc in pts]
    return [from_frame(along + SHIFT + da, across + dc) + (deg,) for da, dc in pts]


ground = None
if HEIGHTMAP:
    import struct
    import numpy as np
    raw = open(HEIGHTMAP, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w_, h_ = struct.unpack_from("<ii", raw, 18)
    H_ = np.frombuffer(raw[off:off + w_ * abs(h_) * 2], dtype="<u2").reshape(abs(h_), w_).astype(float)
    if h_ > 0:
        H_ = H_[::-1]
    LOC_ = (-14487.546875, 4835.837891, -131.845703)

    def ground(x, y):
        fi, fj = (x - LOC_[0]) / 512.0 + 64, (y - LOC_[1]) / 512.0 + 64
        i0, j0 = int(math.floor(fi)), int(math.floor(fj))
        if not (0 <= i0 < 127 and 0 <= j0 < 127):
            return -4967.0
        ti, tj = fi - i0, fj - j0
        hv = (H_[j0, i0] * (1 - ti) * (1 - tj) + H_[j0, i0 + 1] * ti * (1 - tj) + H_[j0 + 1, i0] * (1 - ti) * tj + H_[j0 + 1, i0 + 1] * ti * tj)
        return LOC_[2] + (hv - 32768) * 0.5

citizens, buildings = binder.load()
props, cards = [], []
actors = []


def actor(mesh, x, y, deg, scale=1.0, lift=0.0):
    z = (ground(x, y) if ground else -4967.0) + lift
    actors.append("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'%s'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n"
                  "    Rotation=(Yaw=%d)\n    DrawScale=%.3f\n    bStatic=True\nEnd Actor" % (mesh, x, y, z, int(deg * 65536 / 360) % 65536, scale))
for bid, b in buildings.items():
    if "at" not in b or bid == "tower":
        continue
    kind = b["kind"]
    for x, y, deg in instances(b):
        if b.get("card"):
            cw = b["card"].split()
            csize = float(cw[1]) if len(cw) > 1 else b["size"][2] * M / 0.92
            cards.append("AvalonSM.Cards.%s %.0f %.0f %.0f %.0f 8 0" % (cw[0], x, y, deg, csize))
            if kind in ("rig", "cooling", "islet") or b.get("mesh", "").lower() == "none":
                continue
        if kind in ("wreck",):
            props.append("Mission_05M.debris_sheet_003.Crashed_Transport %.0f %.0f %.0f 2.6 -60 0 0 -74" % (x, y, deg))
            actor("Mission_05M.debris_sheet_003.Crashed_Transport", x, y, deg, 2.6, -60)
            continue
        if kind == "dock":
            props.append("AvalonSM.Liandri.Quay %.0f %.0f %.0f 1.0 -80 0 0 0" % (x, y, deg))
            actor("AvalonSM.Liandri.Quay", x, y, deg, 1.0, -80)
            continue
        mesh = b.get("mesh") or (f"B_{bid}" if kind in ASSEMBLED else SCRIPTED.get(bid, SCRIPTED.get(kind)))
        if mesh is None or mesh.lower() == "none" or bid in HOLLOW:
            continue                      # mesh: none without a card = nothing to place; hollow = shells.py's T3D holds it
        lift = -0.9 * M if kind == "barge" else 0
        props.append("AvalonSM.Liandri.%s %.0f %.0f %.0f 1.0 %.0f 0 0 0" % (mesh, x, y, deg, lift))
        actor("AvalonSM.Liandri.%s" % mesh, x, y, deg, 1.0, lift)

# family=<map family> (town.py: the map name): the family's own [<family> AvalonSet] section, not the global one
import avalon_ini  # noqa
avalon_ini.edit(INI, o.get("family"), ("Props", "Blocks", "Cards"),
                ["Props[%d]=%s" % (k, p) for k, p in enumerate(props[:64] if WRITE_PROPS else [])]
                + ["Cards[%d]=%s" % (k, c) for k, c in enumerate(cards[:64])])
print(len(props) if WRITE_PROPS else 0, "props,", len(cards), "cards ->", INI, "(shift %.0f)" % SHIFT)
if LAYOUT:
    _L = _json.load(open(o["layout"]))
    npyl = 0
    nct = 0
    for c in _L.get("connections", []):
        if c["carrier"] == "conveyor":
            # the ore line: an A-frame tower at every relay and a 60 m cable span with buckets toward the next
            rel = c.get("relays", [])
            pts = [tuple(c["path"][0])] + [(r[0], r[1]) for r in rel] + [tuple(c["path"][-1])]
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                deg = math.degrees(math.atan2(y1 - y0, x1 - x0))
                actor("AvalonSM.Liandri.B_ctower", x0, y0, deg, 1.0, 0.0)
                span = math.hypot(x1 - x0, y1 - y0) / (60 * M)
                z0 = ground(x0, y0) if ground else -4967.0
                actors.append("Begin Actor Class=StaticMeshActor\n    StaticMesh=StaticMesh'AvalonSM.Liandri.B_cable'\n    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n"
                              "    Rotation=(Yaw=%d)\n    DrawScale3D=(X=%.3f,Y=1,Z=1)\n    bStatic=True\nEnd Actor"
                              % (x0, y0, z0, int(deg * 65536 / 360) % 65536, max(0.05, span)))
                nct += 1
            continue
        for x, y, deg in c.get("relays", []):
            actor("AvalonSM.Liandri.Pylon", x, y, deg, 1.0, 0.0)
            props.append("AvalonSM.Liandri.Pylon %.0f %.0f %.0f 1.0 0 0 0 0" % (x, y, deg))
            npyl += 1
    if nct:
        print(nct, "conveyor towers + cable spans")
    if npyl:
        print(npyl, "pylons along the power lines")
if T3D:
    open(T3D, "w").write("Begin Map\n" + "\n".join(actors) + "\nEnd Map\n")
    print(len(actors), "StaticMeshActors ->", T3D)
if WRITE_PROPS and len(props) > 64:
    print("WARNING: more than 64 props; raise Props[] in AvalonCards.uc")
