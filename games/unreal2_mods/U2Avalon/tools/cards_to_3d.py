r"""Swap a map family's round-2 imposter cards for the 3D buildings in AvalonSM2 (the user, 2026-10-07: cards
"became billboards"; the geometry versions read right). Run with the GAME CLOSED: the running game rewrites
U2AvalonCards.ini from its cache.

    py tools/cards_to_3d.py <Section> [<Section> ...] [ini=...]        e.g. TutA_Ridge5 TutA_Mix5

Extras lines (CraneTower/AFrameHut/DormPod/TinShack) and the TwinTowers / WaterTower cards become Props lines
(free slots from 64 up), each turned to face the command-room window, sized to the card's height, with the
palette skin ("-") and the footprint half size (the mod sets props on the lowest ground under the footprint).
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
BOUNDS = os.path.join(HERE, "..", "..", "U2AvalonCards", "Models", "round2_ase", "bounds.json")
WINDOW = (-349.0, 1388.0)
NAMES = {"CraneTower": "CraneTower", "AFrameHut": "AframeHut", "DormPod": "DormPod", "TinShack": "TinShack"}


def face(x, y):
    return int(math.degrees(math.atan2(WINDOW[1] - y, WINDOW[0] - x))) % 360


def convert(txt, section, B):
    m = re.search(r"(?msi)^\[%s\]\n(.*?)(?=^\[|\Z)" % re.escape(section), txt)
    if not m:
        print(section, ": no such section")
        return txt
    sec = m.group(1)
    get = lambda k: (re.search(r"(?m)^%s=(.*)$" % re.escape(k), sec) or [None, ""])[1]
    used = {int(i) for i, v in re.findall(r"(?m)^Props\[(\d+)\]=(.+)$", sec) if v.strip()}
    slots = (i for i in range(64, 128) if i not in used)
    lines = []
    for i in range(48):
        e = get("Extras[%d]" % i).split()
        if len(e) >= 5 and e[0] in NAMES:
            n = NAMES[e[0]]
            x, y, size = float(e[1]), float(e[2]), float(e[4])
            half = 260 if n == "CraneTower" else max(B[n]["w"], B[n]["d"]) / 2   # peaks: keep the tower up
            lines += ["Props[%d]=AvalonSM2.Liandri.%s %d %d %d %.3f 0 0 0 0 - %d" % (next(slots), n, x, y, face(x, y), size / B[n]["h"], half),
                      "Extras[%d]=" % i]
    for i in range(64):
        c = get("Cards[%d]" % i).split()
        if len(c) >= 5 and ("TwinTowersHY" in c[0] or "WaterTowerHY" in c[0]):
            n = "TwinTowers" if "Twin" in c[0] else "WaterTower"
            x, y = float(c[1]), float(c[2])
            sc = 1.3 if n == "TwinTowers" else float(c[4]) / B[n]["h"]
            lines += ["Props[%d]=AvalonSM2.Liandri.%s %d %d %d %.3f 0 0 0 0 - %d" % (next(slots), n, x, y, face(x, y), sc, max(B[n]["w"], B[n]["d"]) / 2),
                      "Cards[%d]=" % i]
    keys = {l.split("=")[0] for l in lines}
    body = "\n".join(l for l in sec.split("\n") if l.split("=")[0] not in keys)
    print("%s: %d cards -> 3D" % (section, len(lines) // 2))
    return txt.replace(sec, "\n".join(lines) + "\n" + body, 1)


if __name__ == "__main__":
    o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    ini = o.get("ini", os.path.join(GAME, "System", "U2AvalonCards.ini"))
    B = json.load(open(BOUNDS))
    txt = open(ini, newline="").read().replace("\r\n", "\n")
    for s in (a for a in sys.argv[1:] if "=" not in a):
        txt = convert(txt, s, B)
    open(ini, "w", newline="").write(txt.replace("\n", "\r\n"))
