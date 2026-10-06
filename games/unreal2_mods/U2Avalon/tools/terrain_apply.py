r"""Put an edited heightmap back into a copy of TutA with UnrealEd (through U2EdBridge / uedlib):

    py tools/terrain_apply.py <edited island1.bmp> [out map name=TutA_Liandri] [source map=TutA]

A TerrainInfo saves its built vertex arrays in the map, so swapping the heightmap texture alone changes
nothing in game, and SET TerrainInfo TerrainMap is class-wide (it re-pointed the SEA terrain too). What
works (uedlib.Ed.replace_actors): import the texture under its name, copy the TerrainInfo actors as T3D,
delete them, import that T3D again: a pasted TerrainInfo rebuilds from its texture.
"""
import os, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
from uedlib import Ed, session  # noqa

bmp = os.path.abspath(sys.argv[1])
name = sys.argv[2] if len(sys.argv) > 2 else "TutA_Liandri"
source = sys.argv[3] if len(sys.argv) > 3 else "TutA"


def apply(ed):
    ed.exec("!answer yes")
    ed.load(source)
    ed.import_texture(bmp, "island1", "MyLevel", "terrain_maps", MIPS=0)
    n = ed.replace_actors("TerrainInfo", None)
    print("re-imported", n, "TerrainInfo actors")
    for a in ed.actors("TerrainInfo"):
        print("  ", a["Name"], a.get("Location"), a["props"].get("TerrainMap"))
    ed.save(name)
    print("saved", ed.map_path(name))


session(apply)
