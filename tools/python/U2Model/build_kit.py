r"""Freeze the kit's pieces into static meshes (U2KitSM.<piece>), read one back from memory (!readmesh), and save
a test map with a courtyard building placed from the frozen pieces (StaticMeshActors: no CSG).

    py build_kit.py      -> <game>\StaticMeshes\U2KitSM.usx, <game>\Maps\U2KitTest.un2, kit_readback.t3d
"""
import os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "C", "U2EdBridge"))
import u2model as U  # noqa
import kit as K  # noqa
from uedlib import Ed, short_path  # noqa
import readmesh  # noqa

GAME = U.GAME
WORK = os.path.join(GAME, "U2ModelWork")
FLOOR = -1024
SLOT = 1400                 # pieces are built apart in the workshop, floating (nothing touches the room's floor)


def sp(p):
    if not os.path.exists(p):
        open(p, "a").close()
    return short_path(p)


def kit_t3d(plan, origin, prefix="Kit"):
    """placements -> StaticMeshActor T3D (yaw in degrees -> Unreal 65536 units: the same turn as Mesh.rotate)"""
    s = ""
    for k, (piece, (x, y, z), yaw) in enumerate(plan):
        s += ("Begin Actor Class=StaticMeshActor Name=%s%d\n    StaticMesh=StaticMesh'U2KitSM.%s'\n"
              "    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n    Rotation=(Pitch=0,Yaw=%d,Roll=0)\nEnd Actor\n"
              % (prefix, k, piece, origin[0] + x, origin[1] + y, origin[2] + z, int(round(yaw * 65536 / 360)) % 65536))
    return s


def main():
    os.makedirs(WORK, exist_ok=True)
    G = short_path(GAME)
    names = list(K.PIECES)
    slots = {nm: ((i % 4 - 1.5) * SLOT, (i // 4 - 1) * SLOT, FLOOR + 600) for i, nm in enumerate(names)}
    models = {nm: K.PIECES[nm]() for nm in names}
    with Ed.start() as ed:
        ed.exec("!answer yes")

        def run(c):
            rc, out = ed.exec_rc(c)
            last = out.strip().splitlines()[-1:] if out.strip() else []
            print("== %-80s rc=%d %s" % (c[:80], rc, last[0][:90] if last else ""))
            return out
        for c in U.Model([("sub", U.box(8192, 8192, 2048))]).editor_commands((0, 0, FLOOR), WORK, "room", sp):
            run(c)
        for nm in names:
            for c in models[nm].editor_commands(slots[nm], WORK, "kit_" + nm, sp):
                run(c)
        run("MAP REBUILD")
        polys_file = os.path.join(WORK, "kit_csg.t3d")
        run('MAP SAVEPOLYS FILE="%s" MERGE=1' % sp(polys_file))
        P = U.read_polylist_full(open(polys_file).read())
        for nm in names:
            lo, hi = models[nm].bounds()
            o = np.array(slots[nm], float)
            mine = [p for p in P if (p[0].min(axis=0) >= lo + o - 4).all() and (p[0].max(axis=0) <= hi + o + 4).all()]
            f = os.path.join(WORK, "kit_%s_frozen.t3d" % nm)
            open(f, "w").write(U.polylist_full(mine, -o))
            run('NEW StaticMeshFactory PACKAGE="U2KitSM" NAME="%s" FILE="%s"' % (nm, sp(f)))
            print("   %-12s %d polygons" % (nm, len(mine)))
        # the editor holds a loaded package's file open: save beside it, swap after the editor has closed
        run('OBJ SAVEPACKAGE PACKAGE="U2KitSM" FILE="%s"' % sp(os.path.join(WORK, "U2KitSM_new.usx")))
        # read one piece back out of memory: the round trip
        m = readmesh.grab(ed, "U2KitSM.wall_door", os.path.join(WORK, "wall_door.u2rm"))
        readmesh.to_t3d(m, os.path.join(HERE, "kit_readback.t3d"))
        print("readmesh: wall_door %d triangles, materials %s, box %s" % (len(m["tris"]), m["materials"], [round(x) for x in m["box"]]))
    swap_package()
    # the test map: a new editor (MAP NEW + imports is unsafe in one session), the courtyard from frozen pieces
    plan = K.building(["###", "#.#", "###"], doors={(1, 2, "s")}, windows={(0, 1, "w"), (2, 1, "e"), (1, 0, "n")})
    actors = os.path.join(WORK, "kit_actors.t3d")
    open(actors, "w").write("Begin Map\n" + kit_t3d(plan, (-512, -512, FLOOR)) +
                            "Begin Actor Class=ZoneInfo Name=KitZone\n    Location=(X=0,Y=0,Z=%d)\n    AmbientBrightness=48\nEnd Actor\n" % (FLOOR + 600) +
                            "Begin Actor Class=PlayerStart Name=KitStart\n    Location=(X=0,Y=-2600,Z=%d)\n    Rotation=(Pitch=0,Yaw=16384,Roll=0)\nEnd Actor\n" % (FLOOR + 100) +
                            "".join("Begin Actor Class=Light Name=KitLight%d\n    Location=(X=%d,Y=%d,Z=%d)\n    LightRadius=96\n    LightBrightness=220\nEnd Actor\n"
                                    % (k, x, y, FLOOR + 900) for k, (x, y) in enumerate([(-1600, -1600), (1600, -1600), (0, 0), (-1600, 1600), (1600, 1600)])) +
                            "End Map\n")
    with Ed.start() as ed:
        ed.exec("!answer yes")
        for c in ['OBJ LOAD FILE="%s\\StaticMeshes\\U2KitSM.usx"' % G] + \
                U.Model([("sub", U.box(8192, 8192, 2048))]).editor_commands((0, 0, FLOOR), WORK, "room", sp) + \
                ['MAP IMPORTADD FILE="%s"' % sp(actors), "MAP REBUILD", "LIGHT APPLY", 'MAP SAVE FILE="%s\\Maps\\U2KitTest.un2"' % G]:
            rc, out = ed.exec_rc(c)
            print("== %-80s rc=%d" % (c[:80], rc))
    print(len(plan), "pieces placed")


def swap_package():
    new = os.path.join(WORK, "U2KitSM_new.usx")
    if os.path.exists(new) and os.path.getsize(new) > 0:
        os.replace(new, os.path.join(GAME, "StaticMeshes", "U2KitSM.usx"))
        print("U2KitSM.usx updated")


if __name__ == "__main__":
    main()
