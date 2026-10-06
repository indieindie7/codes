r"""A camera tour of a map in UnrealEd, saved as PNGs of the perspective viewport (no mouse, no PIL):

    py ued_tour.py [map=TutA] [view names...]        -> <UED_OUT or shots>/<name>.png

Runs its own hidden editor session (nothing is saved). For each (name, x, y, z, pitch, yaw) the camera is
moved there with uedlib.Ed.view() (the PlayerStart is parked there, CAMERA ALIGN, then SET Camera Rotation)
and the perspective viewport is captured with PrintWindow. Helper icons are hidden first (Light, Triggers,
Keypoint, NavigationPoint, AmbientSound, PlayerStart). The views below are for TutA (Avalon).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uedlib import Ed, session

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("UED_OUT", os.path.join(HERE, "shots"))
PX, PY_, PZ = -349, 1388, 4244          # where the player starts (the command room)
D, H = 9000, 2500
VIEWS = [
    ("room_n", PX, PY_, PZ + 40, -600, 16384),
    ("room_e", PX, PY_, PZ + 40, -600, 0),
    ("room_s", PX, PY_, PZ + 40, -600, 49152),
    ("room_w", PX, PY_, PZ + 40, -600, 32768),
    ("out_e", PX + D, PY_, PZ + H, -1800, 32768),
    ("out_w", PX - D, PY_, PZ + H, -1800, 0),
    ("out_n", PX, PY_ + D, PZ + H, -1800, 49152),
    ("out_s", PX, PY_ - D, PZ + H, -1800, 16384),
    ("aerial_se", PX + D, PY_ - D, PZ + 2 * D, -6000, 24576),
    ("aerial_nw", PX - D, PY_ + D, PZ + 2 * D, -6000, 57344),
    ("sea_up", PX + 5000, PY_ - 3000, -3000, 2500, 40000),
]
args = sys.argv[1:]
MAP = args[0] if args and (args[0].lower().endswith(".un2") or args[0] not in {v[0] for v in VIEWS}) else "TutA"
only = set(a for a in args if a != MAP)
os.makedirs(OUT, exist_ok=True)


def tour(ed):
    ed.load(MAP)
    ed.hide_icons()
    for name, x, y, z, pitch, yaw in VIEWS:
        if only and name not in only:
            continue
        ed.view(x, y, z, pitch, yaw)
        print("shot", name, ed.screenshot(os.path.join(OUT, name + ".png")))


session(tour)
