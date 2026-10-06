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
INI = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("shift=") else os.path.join(GAME, "System", "U2AvalonCards.ini")
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
SHIFT = float(o.get("shift", -5300))
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
    if spec[0].lower() == "2x2":
        pts = [(-gap / 2, -gap / 2), (gap / 2, -gap / 2), (-gap / 2, gap / 2), (gap / 2, gap / 2)]
    elif len(spec) == 2:
        n = int(spec[0])
        pts = [((k - (n - 1) / 2) * gap, 0) if spec[1] == "along" else (0, (k - (n - 1) / 2) * gap) for k in range(n)]
    if along is None:
        a = math.radians(deg)
        return [(L["x"] + da * math.cos(a) - dc * math.sin(a), L["y"] + da * math.sin(a) + dc * math.cos(a), deg) for da, dc in pts]
    return [from_frame(along + SHIFT + da, across + dc) + (deg,) for da, dc in pts]


citizens, buildings = binder.load()
props, cards = [], []
for bid, b in buildings.items():
    if "at" not in b or bid == "tower":
        continue
    kind = b["kind"]
    for x, y, deg in instances(b):
        if b.get("card"):
            cw = b["card"].split()
            csize = float(cw[1]) if len(cw) > 1 else b["size"][2] * M / 0.92
            cards.append("AvalonSM.Cards.%s %.0f %.0f %.0f %.0f 8 0" % (cw[0], x, y, deg, csize))
            if kind in ("rig", "cooling"):
                continue
        if kind in ("wreck",):
            props.append("Mission_05M.debris_sheet_003.Crashed_Transport %.0f %.0f %.0f 2.6 -60 0 0 -74" % (x, y, deg))
            continue
        if kind == "dock":
            props.append("AvalonSM.Liandri.Quay %.0f %.0f %.0f 1.0 -80 0 0 0" % (x, y, deg))
            continue
        mesh = b.get("mesh") or (f"B_{bid}" if kind in ASSEMBLED else SCRIPTED.get(bid, SCRIPTED.get(kind)))
        if mesh is None:
            continue
        lift = -0.9 * M if kind == "barge" else 0
        props.append("AvalonSM.Liandri.%s %.0f %.0f %.0f 1.0 %.0f 0 0 0" % (mesh, x, y, deg, lift))

txt = open(INI, newline="").read().replace("\r\n", "\n")
txt = re.sub(r"(?m)^(Props|Blocks|Cards)\[\d+\]=.*\n", "", txt)
head = "[U2AvalonCards.AvalonCards]\n"
i = txt.index(head) + len(head)
txt = (txt[:i] + "".join("Props[%d]=%s\n" % (k, p) for k, p in enumerate(props[:64]))
       + "".join("Cards[%d]=%s\n" % (k, c) for k, c in enumerate(cards[:64])) + txt[i:])
open(INI, "w", newline="").write(txt.replace("\n", "\r\n"))
print(len(props), "props,", len(cards), "cards ->", INI, "(shift %.0f)" % SHIFT)
if len(props) > 64:
    print("WARNING: more than 64 props; raise Props[] in AvalonCards.uc")
