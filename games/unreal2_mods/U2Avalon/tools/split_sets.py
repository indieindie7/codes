r"""One-off move to per-family dressing (2026-10-07): copy a family's arrays from an ini snapshot's global section
into [<family> AvalonSet] of the live ini (run with the game closed: it caches the ini and writes it back).

    py tools/split_sets.py <snapshot.ini> <family> [ini=<U2AvalonCards.ini>]
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import avalon_ini  # noqa

KEYS = ("Props", "Blocks", "Cards", "Extras", "Plumes", "Trucks", "Paths", "PASpots", "RadioSpot", "TowerSpot", "DecayLamp")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"


def global_lines(path):
    txt = open(path, newline="").read().replace("\r\n", "\n")
    head = "[%s]\n" % avalon_ini.GLOBAL
    i = txt.index(head) + len(head)
    m = re.search(r"(?m)^\[", txt[i:])
    body = txt[i:i + m.start()] if m else txt[i:]
    out = []
    for line in body.split("\n"):
        k = re.match(r"([A-Za-z_]\w*)", line)
        if k and k.group(1) in KEYS and not line.rstrip().endswith("="):
            out.append(line.rstrip())
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if "=" not in x]
    o = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    ini = o.get("ini", os.path.join(GAME, "System", "U2AvalonCards.ini"))
    lines = global_lines(a[0])
    avalon_ini.edit(ini, a[1], KEYS, lines)
    print("%s: %d lines -> [%s] in %s" % (a[1], len(lines), avalon_ini.section_name(a[1]), ini))
