"""Save each stock map's builder brush (BRUSH SAVE / BRUSH EXPORT) to brushes/,
to find a plain cube to scale into the HoverTest room."""
import os, sys
from build_editor import u2ed, H, MAPS

maps = sys.argv[1:] or ["Entry", "CS_Titles", "PA_Hell", "PD_Hell", "PA_Sanctuary", "PD_Sanctuary",
                        "PA_Janus", "PD_NaKoja", "CS_Intro", "M09B"]
ed = u2ed.Editor.start()
try:
    for m in maps:
        for c in (r'MAP LOAD FILE="%s\%s.un2"' % (MAPS, m),
                  r'BRUSH EXPORT FILE="%s\brushes\%s.t3d"' % (H, m),
                  r'BRUSH SAVE FILE="%s\brushes\%s.u3d"' % (H, m)):
            try:
                ed.exec_rc(c)
            except u2ed.EditorCrashed as e:
                print("CRASH", c, e)
                raise SystemExit(1)
        t3d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brushes", m + ".t3d")
        n = open(t3d).read().count("Begin Polygon") if os.path.exists(t3d) else -1
        print("%-14s %d polygons" % (m, n))
finally:
    ed.stop()
