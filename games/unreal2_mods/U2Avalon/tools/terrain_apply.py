"""Put an edited heightmap back into a copy of TutA with UnrealEd (through U2EdBridge):

    py tools/terrain_apply.py <edited island1.bmp> [out map name=TutA_Liandri]

A TerrainInfo saves its built vertex arrays in the map, so swapping the heightmap texture alone changes
nothing in game, and SET TerrainInfo TerrainMap is class-wide (it re-pointed the SEA terrain too). What
works: import the texture under its name, copy both TerrainInfo actors as T3D (ACTOR SELECT OFCLASS +
EDIT COPY -> clipboard), delete them, import that T3D again: a pasted TerrainInfo rebuilds from its texture.
"""
import os, subprocess, sys

sys.path.insert(0, r"C:\Users\john\Documents\github\codes\tools\C\U2EdBridge")
import u2ed  # noqa

GAME = r"C:\PROGRA~2\Steam\STEAMA~1\common\UNREAL~2"
bmp = os.path.abspath(sys.argv[1])
name = sys.argv[2] if len(sys.argv) > 2 else "TutA_Liandri"
t3d = os.path.join(os.path.dirname(bmp), "TerrainInfos_%s.t3d" % name)


def run(ed, cmd, show=3):
    rc, o = ed.exec_rc(cmd)
    print("==", cmd[:95], "rc", rc)
    for l in o.strip().splitlines()[-show:]:
        print("    ", l[:150])
    return rc, o


ed = u2ed.Editor.start()
try:
    ed.exec("!answer yes")
    run(ed, r'MAP LOAD FILE="%s\Maps\TutA.un2"' % GAME, 1)
    run(ed, r'TEXTURE IMPORT FILE="%s" NAME="island1" PACKAGE="MyLevel" GROUP="terrain_maps" MIPS=0' % bmp, 2)
    run(ed, r'ACTOR SELECT NONE', 0)
    run(ed, r'ACTOR SELECT OFCLASS CLASS=TerrainInfo', 1)
    run(ed, r'EDIT COPY', 0)
    clip = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"], capture_output=True, text=True).stdout
    if "Begin Actor Class=TerrainInfo" not in clip:
        raise SystemExit("the clipboard has no TerrainInfo actors")
    if "Begin Map" not in clip:
        clip = "Begin Map\n" + clip + "\nEnd Map\n"
    open(t3d, "w").write(clip)
    print("copied", clip.count("Begin Actor"), "terrain actors ->", t3d)
    run(ed, r'ACTOR DELETE', 1)
    run(ed, r'MAP IMPORTADD FILE="%s"' % t3d, 4)
    run(ed, r'MAP SAVE FILE="%s\Maps\%s.un2"' % (GAME, name), 1)
finally:
    ed.stop()
print("saved", os.path.join(GAME, "Maps", name + ".un2"))
