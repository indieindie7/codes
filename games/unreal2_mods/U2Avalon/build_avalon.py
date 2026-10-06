"""Build the Avalon assets and map in UnrealEd through U2EdBridge (see make_avalon.py).

    python build_avalon.py assets   static meshes + palette -> StaticMeshes/AvalonSM.usx, brushes/room.u3d
    python build_avalon.py room     only the room brush
    python build_avalon.py map      -> Maps/Avalon.un2, then paths

Each step runs in a fresh editor (see U2Hover/build_editor.py for why).
"""
import os, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "U2Hover", "Source", "U2Hover"))
import u2ed  # noqa
from build_editor import run, PF_FAKEBACKDROP  # noqa

GAME = r"C:\PROGRA~2\Steam\STEAMA~1\common\UNREAL~2"   # 8.3: Unreal paths can't contain spaces
A = GAME + r"\U2Avalon"
H = GAME + r"\U2Hover"
SM = GAME + r"\StaticMeshes"
MAPS = GAME + r"\Maps"
TILES = 8
BUILDINGS = ["CoolingTower", "ProcessingHall", "StorageTank", "OreTank", "DockCrane", "DrillingRig", "DeadRig",
             "CargoDropship", "Pylon", "RadioMast"]

def manifest():
    """make_avalon.py's Models/ase/manifest.txt: 'name group texture' per mesh"""
    here = os.path.dirname(os.path.abspath(__file__))
    rows = []
    for line in open(os.path.join(here, "Models", "ase", "manifest.txt")):
        w = line.split(None, 2)
        if w:
            rows.append((w[0], w[1]))
    return rows


def bakes():
    """the 'name Bake <path>' rows of the manifest: baked textures to import into AvalonSM.Bake"""
    here = os.path.dirname(os.path.abspath(__file__))
    rows = []
    for line in open(os.path.join(here, "Models", "ase", "manifest.txt")):
        w = line.split(None, 2)
        if len(w) == 3 and w[1] == "Bake":
            rows.append(w[0])
    return rows


ASSETS = [
    r'NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="%s" NAME="%s" FILE="{A}\Models\ase\%s.ase"' % (g, n, n)
    for n, g in manifest() if g != "Bake"
] + [
    r'TEXTURE IMPORT FILE="{A}\Models\bake\%s.tga" NAME="%s" PACKAGE="AvalonSM" GROUP="Bake" MIPS=1' % (t, t)
    for t in bakes()
] + [
    r'TEXTURE IMPORT FILE="{A}\Models\ase\Pal.tga" NAME="Pal" PACKAGE="AvalonSM" GROUP="Pal" MIPS=0',
    r'OBJ SAVEPACKAGE PACKAGE="AvalonSM" FILE="{SM}\AvalonSM.usx"',
]

# the room: the 512 cube scaled to 61440 x 61440 x 16384 (Z +-8192, the Prairie's proportions; a 32768-tall
# room ended up as ONE zone with the sky room, and the SkyZoneInfo then governed the whole level: nothing lit)
ROOM = [
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'ACTOR SELECT ALL',
    r'BRUSH SCALE X=120 Y=120 Z=32',
    r'BRUSH SAVE FILE="{A}\brushes\room.u3d"',
]

MAP = [
    r'OBJ LOAD FILE="{SM}\AvalonSM.usx"',
    r'OBJ LOAD FILE="{SM}\HoverTestSM.usx"',
    r'OBJ LOAD FILE="{SM}\Flora_M.usx"',
    r'OBJ LOAD FILE="{SM}\Terran_DecoM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_SulferonM.usx"',
    r'OBJ LOAD FILE="{GAME}\Textures\Mission_10T.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\JungleT.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\ScottT.utx"',
    r'BRUSH LOAD FILE="{A}\brushes\room.u3d"',
    r'BRUSH MOVETO X=0 Y=0 Z=0',
    r'BRUSH SUBTRACT',
    r'MAP REBUILD',
    r'POLY SELECT ALL',
    r'POLY SET SETFLAGS=%d' % PF_FAKEBACKDROP,
    r'POLY SELECT NONE',
    # the sky room: the SAME big builder brush again, stacked above the main room (Z 11808..28192). Only the
    # first BRUSH LOAD of a session takes effect (measured: a second load is ignored), so a small Entry.u3d
    # cube here came out room-sized at Z 12000, overlapped the main room and merged the two zones; the
    # SkyZoneInfo then governed everything and nothing was lit. (The Prairie worked because its room was
    # only +-4096 tall, so the big "sky cube" at 12000 happened not to overlap.)
    r'BRUSH MOVETO X=0 Y=0 Z=20000',
    r'BRUSH SUBTRACT',
    r'MAP IMPORTADD FILE="{A}\avalon_actors.t3d"',
    r'MAP REBUILD',
    r'LIGHT APPLY',
    r'MAP SAVE FILE="{MAPS}\Avalon.un2"',
]

PATHS = [
    r'MAP LOAD FILE="{MAPS}\Avalon.un2"',
    r'PATHS DEFINE',
    r'MAP SAVE FILE="{MAPS}\Avalon.un2"',
]


def go(cmds):
    import build_editor
    build_editor.H = H
    return run([c.replace("{A}", A) for c in cmds])


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "assets"
    if step == "assets":
        ok = go(ASSETS) and go(ROOM)
    elif step == "room":
        ok = go(ROOM) and go(ROOM)
    elif step == "room":
        ok = go(ROOM)
    elif step == "map":
        ok = go(MAP) and go(PATHS)
    elif step == "map-dusk":
        # the brief's one frame, from avalon_actors_dusk.t3d (py make_avalon.py dusk) -> Maps/AvalonDusk.un2
        dusk = [c.replace("avalon_actors.t3d", "avalon_actors_dusk.t3d").replace("Avalon.un2", "AvalonDusk.un2") for c in MAP]
        paths = [c.replace("Avalon.un2", "AvalonDusk.un2") for c in PATHS]
        ok = go(dusk) and go(paths)
    else:
        ok = go(PATHS)
    sys.exit(0 if ok else 1)
