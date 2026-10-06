"""Build the Avalon assets and map in UnrealEd through U2EdBridge (see make_avalon.py).

    python build_avalon.py assets   static meshes + palette -> StaticMeshes/AvalonSM.usx, brushes/room.u3d
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

ASSETS = [
    r'NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="Ground" NAME="Ground%d%d" FILE="{A}\Models\ase\Ground%d%d.ase"'
    % (i, j, i, j) for i in range(TILES) for j in range(TILES)
] + [
    r'NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="Ground" NAME="Sea" FILE="{A}\Models\ase\Sea.ase"',
    r'NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="Tower" NAME="Tower" FILE="{A}\Models\ase\Tower.ase"',
] + [
    r'NEW StaticMeshFactory PACKAGE="AvalonSM" GROUP="Liandri" NAME="%s" FILE="{A}\Models\ase\%s.ase"' % (b, b)
    for b in BUILDINGS
] + [
    r'TEXTURE IMPORT FILE="{A}\Models\ase\Pal.tga" NAME="Pal" PACKAGE="AvalonSM" GROUP="Pal" MIPS=0',
    r'OBJ SAVEPACKAGE PACKAGE="AvalonSM" FILE="{SM}\AvalonSM.usx"',
    # the room: the 512 cube scaled to 61440 x 61440 x 32768
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'ACTOR SELECT ALL',
    r'BRUSH SCALE X=120 Y=120 Z=64',
    r'BRUSH SAVE FILE="{A}\brushes\room.u3d"',
]

MAP = [
    r'OBJ LOAD FILE="{SM}\AvalonSM.usx"',
    r'OBJ LOAD FILE="{SM}\HoverTestSM.usx"',
    r'OBJ LOAD FILE="{GAME}\Textures\Mission_10T.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\JungleT.utx"',
    r'BRUSH LOAD FILE="{A}\brushes\room.u3d"',
    r'BRUSH MOVETO X=0 Y=0 Z=0',
    r'BRUSH SUBTRACT',
    r'MAP REBUILD',
    r'POLY SELECT ALL',
    r'POLY SET SETFLAGS=%d' % PF_FAKEBACKDROP,
    r'POLY SELECT NONE',
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'BRUSH MOVETO X=0 Y=0 Z=14000',
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
        ok = go(ASSETS)
    elif step == "map":
        ok = go(MAP) and go(PATHS)
    else:
        ok = go(PATHS)
    sys.exit(0 if ok else 1)
