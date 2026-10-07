r"""Put an edited heightmap back into a copy of TutA with UnrealEd (through U2EdBridge / uedlib):

    py tools/terrain_apply.py <edited island1.bmp> [out map name=TutA_Liandri] [source map=TutA_Stock]

A TerrainInfo saves its built vertex arrays in the map, so swapping the heightmap texture alone changes
nothing in game, and SET TerrainInfo TerrainMap is class-wide (it re-pointed the SEA terrain too). What
works (uedlib.Ed.replace_actors): import the texture under its name, copy the TerrainInfo actors as T3D,
delete them, import that T3D again: a pasted TerrainInfo rebuilds from its texture.
"""
import os, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
from uedlib import Ed, session  # noqa

bmp = os.path.abspath([a for a in sys.argv[1:] if "=" not in a][0])
args = [a for a in sys.argv[1:] if "=" not in a]
name = args[1] if len(args) > 1 else "TutA_Liandri"
source = args[2] if len(args) > 2 else "TutA_Stock"   # a pristine copy of the shipped TutA (TutA itself may be a generated town now)
o = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
ALPHAS = o.get("alphas")            # alphas=<dir> with Layer1.bmp, Layer2_Beach.bmp, PlantLife1.bmp (groundpaint.py)


def apply(ed):
    ed.exec("!answer yes")
    ed.load(source)
    ed.import_texture(bmp, "island1", "MyLevel", "terrain_maps", MIPS=0)
    if ALPHAS:
        for layer in ("Layer1", "Layer2_Beach", "PlantLife1"):
            f = os.path.join(ALPHAS, layer + ".tga")
            if os.path.exists(f):
                ed.import_texture(f, layer, "MyLevel", "IslandTerrainLayers", MIPS=0, ALPHA=1)
        print("layer alphas imported from", ALPHAS)
    n = ed.replace_actors("TerrainInfo", None)
    print("re-imported", n, "TerrainInfo actors")
    for a in ed.actors("TerrainInfo"):
        print("  ", a["Name"], a.get("Location"), a["props"].get("TerrainMap"))
    ed.save(name)
    print("saved", ed.map_path(name))


session(apply)
