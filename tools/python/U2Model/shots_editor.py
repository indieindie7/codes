r"""Pictures of the U2Model test map from UnrealEd's own perspective viewport (the game camera kept missing):
    py shots_editor.py   -> shots\u2model_*.png"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "C", "U2EdBridge"))
from uedlib import Ed, short_path  # noqa

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening"
OUT = os.path.join(HERE, "shots")
os.makedirs(OUT, exist_ok=True)
VIEWS = {  # name: x, y, z, pitch, yaw
    "front": (1100, -2600, -300, -1800, 16384),
    "back": (1100, 2600, -300, -1800, 49152),
    "live_close": (-900, -1500, -500, -1500, 10000),
    "frozen_close": (3100, -1500, -500, -1500, 22800),
}
with Ed.start() as ed:
    ed.exec("!answer yes")
    ed.ok('MAP LOAD FILE="%s"' % os.path.join(short_path(GAME), "Maps", "U2ModelTest.un2"))
    ed.hide_icons()
    for name, (x, y, z, p, yw) in VIEWS.items():
        ed.view(x, y, z, p, yw)
        print(ed.screenshot(os.path.join(OUT, "u2model_%s.png" % name)))
