"""Run editor commands given on the command line (one per argument) in a fresh
UnrealEd and print every reply in full. {H} {SM} {MAPS} are expanded."""
import sys
from build_editor import u2ed, H, SM, MAPS, GAME

ed = u2ed.Editor.start()
try:
    for c in sys.argv[1:]:
        c = c.format(H=H, SM=SM, MAPS=MAPS, GAME=GAME)
        try:
            rc, out = ed.exec_rc(c)
        except u2ed.EditorCrashed as e:
            print("CRASH during", c, "\n", e)
            break
        keep = [l for l in out.splitlines() if "garbage" not in l.lower() and "Matched Viewport" not in l]
        print("== %s  [rc=%d]" % (c, rc))
        for l in keep[:40]:
            print("     " + l)
        if len(keep) > 40:
            print("     ... %d more lines" % (len(keep) - 40))
finally:
    ed.stop()
