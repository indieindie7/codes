r"""The low sun: re-aim the map's baked sunlight and relight the island (UnrealEd through U2EdBridge / uedlib).

    py tools/lowsun.py <map> [out=<map>_Dusk] [az=136] [el=9] [hue=24] [sat=110] [bright=] [show=1]

The cinematography report: a low sun (5-20 degrees) raking the town from the side picks out every roof and
wall plane and throws long shadows; a high noon sun flattens it. TutA's sky already paints a low, warm sun
(seen from the decks at about yaw 136, just over the horizon), but the map's Sunlight was baked from much
higher, so the island under that sky looks lit at midday. This re-aims every LE_Sunlight light at the
painted sun (az = the sun's direction in the sky as Unreal yaw degrees, el = its height), warms its colour
(UE2 hue 0-255, saturation 255 = white), and relights only the terrain and the static meshes (LIGHT APPLY
SELECTED=1): a full LIGHT APPLY relit TutA's BSP and the tower came out dark and blotchy (2026-10-07).
show=1 only prints the sun lights.
"""
import os, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
from uedlib import Ed, session, t3d_actors, t3d_set, t3d_map  # noqa

args = [a for a in sys.argv[1:] if "=" not in a]
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
SRC = args[0] if args else "TutA_Town5"
OUT = o.get("out", SRC + "_Dusk")
AZ, EL = float(o.get("az", 136)), float(o.get("el", 9))
U = 65536 / 360.0


def is_sun(a):
    return "LE_Sunlight" in a["props"].get("LightEffect", "")


def job(ed):
    ed.exec("!answer yes")
    ed.load(SRC)
    lights = ed.actors("Light", subclasses=True)
    suns = [a for a in lights if is_sun(a)]
    print("%d lights, %d sun:" % (len(lights), len(suns)))
    for a in suns:
        print("  ", a["Class"], a["Name"], a.get("Location"), a.get("Rotation"),
              {k: a["props"].get(k) for k in ("LightBrightness", "LightHue", "LightSaturation", "LightRadius")})
    if o.get("show") == "1" or not suns:
        return

    def edit(t):
        out = []
        for a in t3d_actors(t):
            b = a["text"]
            if is_sun(a):
                # the light travels away from the sun: yaw + 180, pitched down by its height
                b = t3d_set(b, "Rotation", "(Pitch=%d,Yaw=%d,Roll=0)" % (int(-EL * U) % 65536, int((AZ + 180) * U) % 65536))
                b = t3d_set(b, "LightHue", o.get("hue", "24"))
                b = t3d_set(b, "LightSaturation", o.get("sat", "110"))
                if "bright" in o:
                    b = t3d_set(b, "LightBrightness", o["bright"])
            out.append(b)
        return t3d_map(out)
    ed.replace_actors("Light", edit, subclasses=True)
    ed.deselect()
    ed.ok("ACTOR SELECT OFCLASS CLASS=StaticMeshActor")
    ed.ok("ACTOR SELECT OFCLASS CLASS=TerrainInfo")
    ed.light(selected=True)
    ed.deselect()
    for a in ed.actors("Light", subclasses=True):
        if is_sun(a):
            print("  now", a["Name"], a.get("Rotation"), a["props"].get("LightHue"), a["props"].get("LightSaturation"))
    ed.save(OUT)
    print("saved", ed.map_path(OUT))


session(job)
