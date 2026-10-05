"""Pictures of a map's walkable spaces from UnrealEd: loads each map, exports it as T3D to find the AI path
points and player starts, picks N of them spread as far apart as possible (farthest-point sampling), and at
each takes four pictures at eye height (north, east, south, west) with the perspective viewport.

    python ued_interiors.py <out_dir> MAP[:N] [MAP[:N] ...]      e.g. shots Atlantis:10 TutB:12

Path points come from %TEMP%\zones_<MAP>.log if it exists (an Unreal2.log with "hub zones" output), else
from MAP EXPORT (which writes nothing for some maps).

Starts UnrealEd (u2ed.Editor.start: moves System\\d3d8.dll aside while it runs) and stops it at the end; nothing
is saved. Camera control and the window grab are the ones in ued_tour.py / winshot.py (see README).
"""
import math, os, re, subprocess, sys, tempfile, time
from u2ed import Editor

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser("~/Documents/Tools/Hunyuan3D-2/venv/Scripts/python.exe")   # has Pillow
HIDE = ["Light", "Triggers", "Keypoint", "NavigationPoint", "AmbientSound", "Emitter"]   # never Info (crashes)
POINTS = re.compile(r"Begin Actor Class=(PathNode|PlayerStart|U2PathNode|InventorySpot|AlternatePath)\b.*?"
                    r"Location=\(X=([-\d.]+),Y=([-\d.]+),Z=([-\d.]+)\)", re.S)


def spread(pts, n):
    if len(pts) <= n:
        return pts
    out = [pts[0]]
    d = [math.dist(p, out[0]) for p in pts]
    while len(out) < n:
        i = max(range(len(pts)), key=lambda k: d[k])
        out.append(pts[i])
        d = [min(d[k], math.dist(pts[k], pts[i])) for k in range(len(pts))]
    return out


def grab(name, out):
    win = os.path.join(out, "_win.png")
    subprocess.run([PY, os.path.join(HERE, "winshot.py"), win], check=True, capture_output=True)
    subprocess.run([PY, "-c", "from PIL import Image; Image.open(r'%s').crop((79,576,1276,1018)).save(r'%s')"
                    % (win, os.path.join(out, name + ".png"))], check=True)


def main():
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    ed = Editor.start()
    try:
        for arg in sys.argv[2:]:
            m, _, n = arg.partition(":")
            n = int(n or 10)
            print(ed.exec(r"MAP LOAD FILE=..\Maps\%s.un2" % m)[-200:].strip().splitlines()[-1:])
            # path points: from a game log with "Zones: nav" lines (U2Pilot, console hub zones) when there is one
            # (MAP EXPORT silently writes nothing for some maps, e.g. Atlantis), else from a T3D export
            zlog = os.path.join(tempfile.gettempdir(), "zones_%s.log" % m)
            if os.path.exists(zlog):
                pts = [(float(a), float(b), float(c)) for a, b, c in
                       re.findall(r"Zones: nav \S+ (-?\d+) (-?\d+) (-?\d+)", open(zlog, encoding="latin1").read())]
            else:
                t3d = os.path.join(tempfile.gettempdir(), m + "_ued.t3d")
                ed.exec("MAP EXPORT FILE=" + t3d)
                text = open(t3d, encoding="latin1").read()
                os.remove(t3d)
                pts = [(float(x), float(y), float(z)) for _, x, y, z in POINTS.findall(text)]
            pick = spread(pts, n)
            print(m, len(pts), "path points ->", len(pick))
            for c in HIDE:
                ed.exec("SET %s bHiddenEd True" % c)
            for k, (x, y, z) in enumerate(pick):
                for yaw, side in ((16384, "n"), (0, "e"), (49152, "s"), (32768, "w")):
                    for c in ["SET PlayerStart bHiddenEd False", "SET PlayerStart Location (X=%d,Y=%d,Z=%d)" % (x, y, z + 40),
                              "ACTOR SELECT OFCLASS CLASS=PlayerStart", "CAMERA ALIGN", "ACTOR SELECT NONE",
                              "SET PlayerStart bHiddenEd True", "SET Camera Rotation (Pitch=-400,Yaw=%d,Roll=0)" % yaw,
                              "ACTOR SELECT OFCLASS CLASS=Brush", "ACTOR SELECT NONE"]:
                        ed.exec(c)
                    time.sleep(0.4)
                    grab("%s_%02d%s" % (m, k, side), out)
                print(" point", k, "done")
    finally:
        ed.stop()


if __name__ == "__main__":
    main()
