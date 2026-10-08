"""Build Sanctuary Open in UnrealEd through U2EdBridge (see make_open.py). Forked from U2Prairie/build_prairie.py.

    py build_open.py assets    -> StaticMeshes\\SanctuaryOpenSM.usx + U2SanctuaryOpen\\brushes\\bigroom.u3d
    py build_open.py map       -> Maps\\PrairieSanctuary.un2 (+ PATHS DEFINE)
"""
import os, sys

GAMEDIR = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
sys.path.insert(0, os.path.join(GAMEDIR, "U2Hover"))
import u2ed
from build_editor import PF_FAKEBACKDROP  # noqa

GAME = r"C:\PROGRA~2\Steam\STEAMA~1\common\UNREAL~2"
P = GAME + r"\U2SanctuaryOpen"
H = GAME + r"\U2Hover"
SM = GAME + r"\StaticMeshes"
MAPS = GAME + r"\Maps"
TILES = 8
NAME = "PrairieSanctuary"

ASSETS = [
    r'NEW StaticMeshFactory PACKAGE="SanctuaryOpenSM" GROUP="Ground" NAME="Ground%d%d" FILE="{P}\Models\ase\Ground%d%d.ase"'
    % (i, j, i, j) for i in range(TILES) for j in range(TILES)
] + [
    r'NEW StaticMeshFactory PACKAGE="SanctuaryOpenSM" GROUP="Ground" NAME="Basin" FILE="{P}\Models\ase\Basin.ase"',
    r'OBJ SAVEPACKAGE PACKAGE="SanctuaryOpenSM" FILE="{SM}\SanctuaryOpenSM.usx"',
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'ACTOR SELECT ALL',
    r'BRUSH SCALE X=120 Y=120 Z=16',
    r'BRUSH SAVE FILE="{P}\brushes\bigroom.u3d"',
]

LOADS = ["SanctuaryOpenSM", "HoverTestSM", "Mission_05M", "Terran_DecoM", "Mission_08M", "JungleM", "Flora_M",
         "MM_WaterfrontM", "Mission_SulferonM", "Mission_10M"]
TEX = ["ScottT", "Mission_10T", "JungleT", "VertexT", "TerranT"]

MAP = [r'OBJ LOAD FILE="{SM}\%s.usx"' % p for p in LOADS] + [r'OBJ LOAD FILE="{GAME}\Textures\%s.utx"' % t for t in TEX] + [
    r'BRUSH LOAD FILE="{P}\brushes\bigroom.u3d"',
    r'BRUSH MOVETO X=0 Y=0 Z=0',
    r'BRUSH SUBTRACT',
    r'MAP REBUILD',
    r'POLY SELECT ALL',
    r'POLY SET SETFLAGS=%d' % PF_FAKEBACKDROP,
    r'POLY SELECT NONE',
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'BRUSH MOVETO X=0 Y=0 Z=12000',
    r'BRUSH SUBTRACT',
    r'MAP IMPORTADD FILE="{P}\open_actors.t3d"',
    r'MAP REBUILD',
    r'LIGHT APPLY',
    r'MAP SAVE FILE="{MAPS}\%s.un2"' % NAME,
]

PATHS = [r'MAP LOAD FILE="{MAPS}\%s.un2"' % NAME, r'PATHS DEFINE', r'MAP SAVE FILE="{MAPS}\%s.un2"' % NAME]


def run(cmds):
    ed = u2ed.Editor.start()
    try:
        ed.exec("!answer yes")
        for c in cmds:
            c = c.format(P=P, H=H, SM=SM, MAPS=MAPS, GAME=GAME)
            try:
                rc, out = ed.exec_rc(c)
            except u2ed.EditorCrashed as e:
                print("CRASH during", c, "\n", e)
                return False
            lines = out.strip().splitlines()
            print("== %s  [rc=%d, %d lines]" % (c[:110], rc, len(lines)))
            for l in lines[-2:]:
                print("     " + l[:160])
        return True
    finally:
        ed.stop()


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "assets"
    os.makedirs(os.path.join(GAMEDIR, "U2SanctuaryOpen", "brushes"), exist_ok=True)
    ok = run(ASSETS) if step == "assets" else (run(MAP) and run(PATHS)) if step == "map" else run(PATHS)
    sys.exit(0 if ok else 1)
