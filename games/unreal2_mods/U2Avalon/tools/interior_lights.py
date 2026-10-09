r"""Interior lights for the walk-in buildings (the remake's hollow shells had none: dark inside).

    py tools/interior_lights.py <run folder> [out=<run>\remake_lights.t3d] [bright=96]

One Light per room of every hollow building copy (rooms.json, the same plans shells.py builds from), hung 0.5 m under
the room's ceiling at its centre. Radius from the room's size (UE2: world radius = 25 * (LightRadius + 1) UU), colour by
owner (artist: "every light has a fixture you can see"; the director's value ladder keeps them below the windows):
company = sodium orange, authority = cold white-blue, everyone else = warm tungsten. Stairs and lifts get one small
lamp; the rooms marked existing / shown_not_given get none. Import after the shells, then LIGHT APPLY.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import binder, shells  # noqa

M = 50.0
COLOUR = {"company": (28, 150), "authority": (150, 190)}      # (LightHue, LightSaturation); 255 sat = white
DEFAULT = (32, 200)


def lights(run, bright=96):
    R = json.load(open(os.path.join(run, "rooms.json")))
    L = json.load(open(os.path.join(run, "isl_layout.json")))
    hollow = json.load(open(os.path.join(run, "hollow.json")))["hollow"]
    _, sheets = binder.load()
    out = []
    for bid in hollow:
        if bid == "tower" or bid not in R or bid not in L["buildings"] or bid not in sheets:
            continue
        plan, sheet = R[bid], sheets[bid]
        hue, sat = COLOUR.get(sheet.get("owner"), DEFAULT)
        for inst in shells.instances(bid, L["buildings"][bid], sheet):
            sh = shells.Shell(plan, sheet, inst)
            for r in plan["rooms"]:
                if r.get("existing") or r.get("shown_not_given"):
                    continue
                small = r.get("lift") or r["id"].startswith("stair")
                h = r.get("h", shells.STOREY)
                x, y, z = sh.world_of(r["x"], r["y"], r["z"] + max(h - 0.5, 1.6))
                size = max(r.get("w", 4), r.get("d", 4)) * M
                rad = 8 if small else int(max(10, min(40, size * 0.6 / 25)))
                out.append("\n".join([
                    "Begin Actor Class=Light Name=GenLight_%s_%d" % (bid, len(out)),
                    "    Location=(X=%.1f,Y=%.1f,Z=%.1f)" % (x, y, z),
                    "    LightBrightness=%d" % (bright * (0.6 if small else 1)),
                    "    LightHue=%d" % hue,
                    "    LightSaturation=%d" % sat,
                    "    LightRadius=%d" % rad,
                    "End Actor"]))
    return out


if __name__ == "__main__":
    run = sys.argv[1]
    o = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    A = lights(run, float(o.get("bright", 96)))
    p = o.get("out", os.path.join(run, "remake_lights.t3d"))
    open(p, "w").write("Begin Map\n" + "\n".join(A) + "\nEnd Map\n")
    print(len(A), "interior lights ->", p)
