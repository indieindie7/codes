"""Build the Prairie map in UnrealEd through U2EdBridge (see make_prairie.py)."""
import os, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "U2Hover"))
import u2ed
from build_editor import run as _run, PF_FAKEBACKDROP  # noqa

GAME = r"C:\PROGRA~2\Steam\STEAMA~1\common\UNREAL~2"
P = GAME + r"\U2Prairie"
H = GAME + r"\U2Hover"
SM = GAME + r"\StaticMeshes"
MAPS = GAME + r"\Maps"
TILES = 8

ASSETS = [
    r'NEW StaticMeshFactory PACKAGE="PrairieSM" GROUP="Ground" NAME="Ground%d%d" FILE="{P}\Models\ase\Ground%d%d.ase"'
    % (i, j, i, j) for i in range(TILES) for j in range(TILES)
] + [
    r'NEW StaticMeshFactory PACKAGE="PrairieSM" GROUP="Ground" NAME="Creek" FILE="{P}\Models\ase\Creek.ase"',
    r'OBJ SAVEPACKAGE PACKAGE="PrairieSM" FILE="{SM}\PrairieSM.usx"',
    # the room: the 512 cube scaled to 61440 x 61440 x 8192
    r'BRUSH LOAD FILE="{H}\brushes\Entry.u3d"',
    r'ACTOR SELECT ALL',
    r'BRUSH SCALE X=120 Y=120 Z=16',
    r'BRUSH SAVE FILE="{P}\brushes\bigroom.u3d"',
]

MAP = [
    r'OBJ LOAD FILE="{SM}\PrairieSM.usx"',
    r'OBJ LOAD FILE="{SM}\HoverTestSM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_05M.usx"',
    r'OBJ LOAD FILE="{SM}\CinemaM.usx"',
    r'OBJ LOAD FILE="{SM}\Terran_DecoM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_08M.usx"',
    r'OBJ LOAD FILE="{SM}\Flora_M.usx"',
    r'OBJ LOAD FILE="{SM}\MM_WaterfrontM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_SulferonM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_10M.usx"',
    r'OBJ LOAD FILE="{GAME}\Textures\ScottT.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\Mission_10T.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\JungleT.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\VertexT.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\TerranT.utx"',
    r'OBJ LOAD FILE="{GAME}\Textures\CinemaT.utx"',
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
    r'MAP IMPORTADD FILE="{P}\prairie_actors.t3d"',
    r'MAP REBUILD',
    r'LIGHT APPLY',
    r'MAP SAVE FILE="{MAPS}\Prairie.un2"',
]

SURVEY = [
    r'MAP LOAD FILE="{MAPS}\Prairie.un2"',
    r'OBJ LOAD FILE="{SM}\Mission_08M.usx"',
    r'OBJ LOAD FILE="{SM}\Flora_M.usx"',
    r'OBJ LOAD FILE="{SM}\MM_WaterfrontM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_SulferonM.usx"',
    r'OBJ LOAD FILE="{SM}\Mission_10M.usx"',
    r'MAP IMPORTADD FILE="{P}\survey_actors.t3d"',
    r'MAP SAVE FILE="{MAPS}\PrairieSurvey.un2"',
]

PATHS = [
    r'MAP LOAD FILE="{MAPS}\Prairie.un2"',
    r'PATHS DEFINE',
    r'MAP SAVE FILE="{MAPS}\Prairie.un2"',
]


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
            print("== %s  [rc=%d, %d lines]" % (c, rc, len(lines)))
            for l in lines[-2:]:
                print("     " + l)
        return True
    finally:
        ed.stop()


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "assets"
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "brushes"), exist_ok=True)
    if step == "assets":
        ok = run(ASSETS)
    elif step == "survey":
        ok = run(SURVEY)
    elif step == "map":
        ok = run(MAP) and run(PATHS)
    else:
        ok = run(PATHS)
    sys.exit(0 if ok else 1)
