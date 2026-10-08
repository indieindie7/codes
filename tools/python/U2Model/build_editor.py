r"""Build a U2Model model in UnrealEd (live brushes), freeze the CSG result into a static mesh, and save a test map with
both side by side.

    py build_editor.py demo_post GuardPost        (module with model(), static mesh name)
      -> <game>\Maps\U2ModelTest.un2, <game>\StaticMeshes\U2ModelSM.usx (U2ModelSM.<Name>; the editor ignores GROUP=)

The freeze: the model is built inside a big subtracted room, MAP REBUILD runs the editor's own CSG, MAP SAVEPOLYS
writes the result's polygons; the ones inside the model's bounds are its surfaces (facing out into the air) and go
back in as a PolyList through StaticMeshFactory (PolyList -> UModel -> CreateStaticMeshFromBrush).
"""
import importlib, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "C", "U2EdBridge"))
import u2model as U  # noqa
import u2ed  # noqa
from uedlib import short_path  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
WORK = os.path.join(GAME, "U2ModelWork")
FLOOR = -1024
FROZEN_AT = (2200, 0)


def sp(p):
    if not os.path.exists(p):
        open(p, "a").close()
    return short_path(p)


def main(modname, name):
    os.makedirs(WORK, exist_ok=True)
    model = importlib.import_module(modname).model()
    bad = model.check()
    if bad:
        raise SystemExit("model problems: %s" % bad)
    lo, hi = model.bounds()
    origin = (0, 0, FLOOR)
    room = U.box(8192, 8192, 2048)
    G = short_path(GAME)
    ed = u2ed.Editor.start()

    def run(c):
        rc, out = ed.exec_rc(c)
        last = out.strip().splitlines()[-1:] if out.strip() else []
        print("== %-90s rc=%d %s" % (c[:90], rc, last[0][:100] if last else ""))
        return out
    try:
        ed.exec("!answer yes")
        for c in U.Model([("sub", room)]).editor_commands((0, 0, FLOOR), WORK, "room", sp):
            run(c)
        for c in model.editor_commands(origin, WORK, name, sp):
            run(c)
        run("MAP REBUILD")
        polys_file = os.path.join(WORK, name + "_csg.t3d")
        run('MAP SAVEPOLYS FILE="%s" MERGE=1' % sp(polys_file))
        P = U.read_polylist(open(polys_file).read())
        o = np.array(origin, float)
        def room_floor(p):          # the room's floor under and around the model (flat at the base, facing up)
            n = U.newell(p)
            return np.abs(p[:, 2] - o[2] - lo[2]).max() < 0.5 and n[2] > 0
        keep = [p - o for p in P if (p.min(axis=0) >= lo + o - 4).all() and (p.max(axis=0) <= hi + o + 4).all()
                and not room_floor(p)]
        print("CSG result: %d polygons, %d of them the model's" % (len(P), len(keep)))
        frozen = os.path.join(WORK, name + "_frozen.t3d")
        open(frozen, "w").write(U.polylist(keep))
        run('NEW StaticMeshFactory PACKAGE="U2ModelSM" NAME="%s" FILE="%s"' % (name, sp(frozen)))
        # the editor holds a loaded package's file open: save beside it, swap after the editor has closed
        run('OBJ SAVEPACKAGE PACKAGE="U2ModelSM" FILE="%s"' % sp(os.path.join(WORK, "U2ModelSM_new.usx")))
        actors = os.path.join(WORK, name + "_actors.t3d")
        open(actors, "w").write(
            "Begin Map\n"
            "Begin Actor Class=StaticMeshActor Name=%sFrozen\n    StaticMesh=StaticMesh'U2ModelSM.%s'\n"
            "    Location=(X=%d,Y=%d,Z=%d)\nEnd Actor\n" % (name, name, FROZEN_AT[0], FROZEN_AT[1], FLOOR) +
            "Begin Actor Class=ZoneInfo Name=ModelZone\n    Location=(X=0,Y=0,Z=%d)\n    AmbientBrightness=48\nEnd Actor\n" % (FLOOR + 600) +
            "Begin Actor Class=PlayerStart Name=ModelStart\n    Location=(X=1100,Y=-2500,Z=%d)\n    Rotation=(Pitch=0,Yaw=16384,Roll=0)\nEnd Actor\n" % (FLOOR + 100) +
            "".join("Begin Actor Class=Light Name=ModelLight%d\n    Location=(X=%d,Y=%d,Z=%d)\n    LightRadius=96\n"
                    "    LightBrightness=220\nEnd Actor\n" % (k, x, y, FLOOR + 900)
                    for k, (x, y) in enumerate([(-1200, -1600), (1200, -1600), (3400, -1600), (0, 1600), (2200, 1600)])) +
            "End Map\n")
        run('MAP IMPORTADD FILE="%s"' % sp(actors))
        run("MAP REBUILD")
        run("LIGHT APPLY")
        run('MAP SAVE FILE="%s\\Maps\\U2ModelTest.un2"' % G)
    finally:
        ed.stop()
    swap_package()


def swap_package():
    new = os.path.join(WORK, "U2ModelSM_new.usx")
    if os.path.exists(new) and os.path.getsize(new) > 0:
        os.replace(new, os.path.join(GAME, "StaticMeshes", "U2ModelSM.usx"))
        print("U2ModelSM.usx updated")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
