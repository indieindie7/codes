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
STOCK = o.get("stock")              # stock=<the source map's own heightmap BMP>: re-seat the map's own static meshes


def _heights(bmp):
    import struct
    import numpy as np
    raw = open(bmp, "rb").read()
    off = struct.unpack_from("<I", raw, 10)[0]
    w, h = struct.unpack_from("<ii", raw, 18)
    H = np.frombuffer(raw[off:off + w * abs(h) * 2], dtype="<u2").reshape(abs(h), w).astype(float)
    return (H[::-1] if h > 0 else H)


LOC, CELL, SEA_Z = (-14487.546875, 4835.837891, -131.845703), 512.0, -4967.0


def _ground(H, x, y):
    import math
    fi, fj = (x - LOC[0]) / CELL + 64, (y - LOC[1]) / CELL + 64
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if not (0 <= i0 < 127 and 0 <= j0 < 127):
        return None
    ti, tj = fi - i0, fj - j0
    v = H[j0, i0] * (1 - ti) * (1 - tj) + H[j0, i0 + 1] * ti * (1 - tj) + H[j0 + 1, i0] * (1 - ti) * tj + H[j0 + 1, i0 + 1] * ti * tj
    return LOC[2] + (v - 32768) * 0.5


def reseat(t3d):
    """the source map's own rocks and props stood on ITS terrain: one that rested on the old ground (its
    origin from 8 m under to 12 m over it) moves by the change in ground height; one that would now be under
    the sea is dropped. Our own meshes (AvalonSM) are imported later and are not touched. Without this the
    stock island's boulders floated over the new, lower land (seen from the tower as black discs)."""
    import re
    Hs, Hn = _heights(STOCK), _heights(bmp)
    out, moved, dropped = [], 0, 0
    for m in re.finditer(r"Begin Actor.*?End Actor", t3d, re.S):
        blk = m.group(0)
        loc = re.search(r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", blk)
        if loc and "AvalonSM." not in blk:
            x, y, z = (float(v) for v in loc.groups())
            gs, gn = _ground(Hs, x, y), _ground(Hn, x, y)
            if gs is not None and gn is not None and -400 <= z - gs <= 600 and abs(gn - gs) > 30:
                if gn <= SEA_Z + 20:
                    dropped += 1
                    continue
                blk = blk.replace(loc.group(0), "Location=(X=%s,Y=%s,Z=%.3f)" % (loc.group(1), loc.group(2), z + gn - gs))
                moved += 1
        out.append(blk)
    print("re-seated %d of the map's own static meshes, dropped %d now under the sea" % (moved, dropped))
    return "Begin Map\n" + "\n".join(out) + "\nEnd Map\n"


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
    if STOCK:
        ed.replace_actors("StaticMeshActor", reseat)
    for a in ed.actors("TerrainInfo"):
        print("  ", a["Name"], a.get("Location"), a["props"].get("TerrainMap"))
    ed.save(name)
    print("saved", ed.map_path(name))


session(apply)
