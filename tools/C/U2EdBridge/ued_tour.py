"""A camera tour of the loaded map in UnrealEd (start it first: python u2ed.py start, then
exec "MAP LOAD FILE=..\Maps\TutA.un2"): for each (name, x, y, z, pitch, yaw) the PlayerStart is moved
there (SET), the viewports are aligned on it, its icon is hidden and the perspective camera turned (SET Camera
Rotation); the perspective viewport is then saved as <UED_OUT or shots>/<name>.png (PrintWindow, see winshot.py).
The views below are for TutA (Avalon); edit PX/PY_/PZ and VIEWS for another map.
Before the tour, hide the editor's helper icons with SET <class> bHiddenEd True for Light, Triggers,
Keypoint, NavigationPoint, AmbientSound. NOT Info: SET Info bHiddenEd crashes UnrealEd (ZoneInfo PostEditChange).
Nothing is saved to the map (the editor is stopped without saving)."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.expanduser("~/Documents/github/codes/tools/C/U2EdBridge"))
from u2ed import Editor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("UED_OUT", os.path.join(HERE, "shots"))
PY = os.path.expanduser("~/Documents/Tools/Hunyuan3D-2/venv/Scripts/python.exe")
PX, PY_, PZ = -349, 1388, 4244          # where the player starts (the command room)
D, H = 9000, 2500
VIEWS = [
    # the room, from the player's start, four ways
    ("room_n", PX, PY_, PZ + 40, -600, 16384),
    ("room_e", PX, PY_, PZ + 40, -600, 0),
    ("room_s", PX, PY_, PZ + 40, -600, 49152),
    ("room_w", PX, PY_, PZ + 40, -600, 32768),
    # the tower from outside, four sides, looking back at it
    ("out_e", PX + D, PY_, PZ + H, -1800, 32768),
    ("out_w", PX - D, PY_, PZ + H, -1800, 0),
    ("out_n", PX, PY_ + D, PZ + H, -1800, 49152),
    ("out_s", PX, PY_ - D, PZ + H, -1800, 16384),
    # far and high: the whole site
    ("aerial_se", PX + D, PY_ - D, PZ + 2 * D, -6000, 24576),
    ("aerial_nw", PX - D, PY_ + D, PZ + 2 * D, -6000, 57344),
    # from the sea, looking up at the tower
    ("sea_up", PX + 5000, PY_ - 3000, -3000, 2500, 40000),
]
only = set(sys.argv[1:])
os.makedirs(OUT, exist_ok=True)
ed = Editor.attach()
for name, x, y, z, pitch, yaw in VIEWS:
    if only and name not in only:
        continue
    for c in ["SET PlayerStart bHiddenEd False", "SET PlayerStart Location (X=%d,Y=%d,Z=%d)" % (x, y, z),
              "ACTOR SELECT OFCLASS CLASS=PlayerStart", "CAMERA ALIGN", "ACTOR SELECT NONE",
              "SET PlayerStart bHiddenEd True", "SET Camera Rotation (Pitch=%d,Yaw=%d,Roll=0)" % (pitch, yaw),
              "ACTOR SELECT OFCLASS CLASS=SectorCommander", "ACTOR SELECT NONE"]:
        r = ed.exec(c)
        if "Can't" in r:
            print(name, c, r.strip())
    time.sleep(0.5)
    win = os.path.join(OUT, "win_" + name + ".png")
    subprocess.run([PY, os.path.join(HERE, "winshot.py"), win], check=True, capture_output=True)
    subprocess.run([PY, "-c", "from PIL import Image; Image.open(r'%s').crop((79,576,1276,1018)).save(r'%s')"
                    % (win, os.path.join(OUT, name + ".png"))], check=True)
    print("shot", name)
ed.close()
