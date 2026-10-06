"""Hand-keyed blade swings, built on the animation principles (the generated motion-capture
style swings read small and polite): a readable WIND-UP (anticipation), a STRIKE over four
or five frames (snap), an OVERSHOOT past the end pose (follow-through), and a settle; poses
pushed past life (exaggeration), on arcs. The torso twists with the arm and the head leads.

Writes AdventMod/AnimsBlade/<Clip>.json in make_psa.py's clip format, so the build's
make_psa call packs them into ModBladeSwings.psa. ModMelee plays them from Spine3 up over the
game's own punch move (legs and footwork stay the game's).

Conventions (make_psa.py): mesh space -Y up, X the body's left, Z forward; a bone's rotation
is relative to the T pose (arms straight out sideways). Right arm points -X: about Y, + swings
it forward then across the chest; about Z, - lowers it. Left arm points +X: about Y, - swings
it forward; about Z, + lowers it. Spine about Y twists the shoulders (+ turns the chest to
the left), about X pitches (+ leans back).

    python tools/make_blade_clips.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_psa import X, Y, Z, qmul, axis_angle   # noqa: E402

OUT = os.path.join(HERE, "..", "AdventMod", "AnimsBlade")
FPS = 30


def smooth(u):
    return u * u * (3 - 2 * u)


def key(t, keys):
    """keys: [(time, value, easing)]; easing of the segment ending at that key:
    'out' (fast start, slow end: a wind-up settling), 'in' (slow start, fast end),
    'snap' (nearly linear, a strike), 'smooth' (ease both ways)"""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            if e == "out":
                u = 1 - (1 - u) ** 2.2
            elif e == "in":
                u = u ** 2.2
            elif e == "snap":
                u = u ** 0.85
            else:
                u = smooth(u)
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def slash_right(t):
    """a horizontal slash from the right across the chest to the left (1.0 s)"""
    arm_y = key(t, [(0, 0, "out"), (0.28, -95, "out"), (0.30, -100, "out"),     # wind-up: back and up, held a beat
                    (0.42, 150, "snap"),                                        # the strike: 220 degrees in 4 frames
                    (0.50, 172, "out"), (0.62, 158, "smooth"), (1.0, 0, "smooth")])   # overshoot, back, settle
    arm_z = key(t, [(0, -60, "out"), (0.28, -10, "out"), (0.42, -5, "snap"), (0.50, -12, "out"), (1.0, -60, "smooth")])
    fore = key(t, [(0, 0, "out"), (0.28, -75, "out"), (0.42, -10, "snap"), (0.50, -5, "out"), (1.0, -20, "smooth")])
    twist = key(t, [(0, 0, "out"), (0.28, -55, "out"), (0.42, 55, "snap"), (0.50, 65, "out"), (1.0, 0, "smooth")])
    lean = key(t, [(0, 0, "out"), (0.28, 8, "out"), (0.42, -14, "snap"), (0.50, -16, "out"), (1.0, 0, "smooth")])
    head = key(t, [(0, 0, "out"), (0.22, 25, "out"), (0.40, -30, "snap"), (0.5, -28, "out"), (1.0, 0, "smooth")])    # the head leads the turn
    off_y = key(t, [(0, 0, "out"), (0.28, -40, "out"), (0.42, 10, "snap"), (1.0, -40, "smooth")])      # the other arm counters
    rot = {
        "rightArm": [(Z, arm_z), (Y, arm_y)], "rightForeArm": [(Y, fore)], "righthand": [(Y, fore * 0.3)],
        "leftArm": [(Z, 60), (Y, off_y)], "leftForeArm": [(Y, 30)],
        "spine1": [(Y, twist * 0.35), (X, lean * 0.4)], "Spine3": [(Y, twist * 0.65), (X, lean * 0.6)],
        "neck": [(Y, head * 0.4)], "head": [(Y, head * 0.6)],
    }
    return rot, (0.0, 0.0, 0.0)


def slash_left(t):
    """the backhand: from the left back across to the right (0.95 s)"""
    arm_y = key(t, [(0, 0, "out"), (0.28, 150, "out"), (0.30, 155, "out"),
                    (0.42, -70, "snap"), (0.50, -92, "out"), (0.62, -78, "smooth"), (1.0, 0, "smooth")])
    arm_z = key(t, [(0, -60, "out"), (0.28, -8, "out"), (0.42, -12, "snap"), (0.50, -18, "out"), (1.0, -60, "smooth")])
    fore = key(t, [(0, 0, "out"), (0.28, -20, "out"), (0.42, -45, "snap"), (0.50, -30, "out"), (1.0, -20, "smooth")])
    twist = key(t, [(0, 0, "out"), (0.28, 60, "out"), (0.42, -55, "snap"), (0.50, -65, "out"), (1.0, 0, "smooth")])
    lean = key(t, [(0, 0, "out"), (0.28, 6, "out"), (0.42, -12, "snap"), (0.50, -14, "out"), (1.0, 0, "smooth")])
    head = key(t, [(0, 0, "out"), (0.22, -25, "out"), (0.40, 30, "snap"), (0.5, 28, "out"), (1.0, 0, "smooth")])
    rot = {
        "rightArm": [(Z, arm_z), (Y, arm_y)], "rightForeArm": [(Y, fore)], "righthand": [(Y, fore * 0.3)],
        "leftArm": [(Z, 55), (Y, -20)], "leftForeArm": [(Y, 30)],
        "spine1": [(Y, twist * 0.35), (X, lean * 0.4)], "Spine3": [(Y, twist * 0.65), (X, lean * 0.6)],
        "neck": [(Y, head * 0.4)], "head": [(Y, head * 0.6)],
    }
    return rot, (0.0, 0.0, 0.0)


def overhead(t):
    """raised high over the head, held, then chopped down past the knees (1.05 s)"""
    arm_z = key(t, [(0, -60, "out"), (0.30, 80, "out"), (0.33, 84, "out"),      # up over the head (Z + raises the right arm)
                    (0.45, -95, "snap"), (0.53, -110, "out"), (0.66, -98, "smooth"), (1.0, -60, "smooth")])
    arm_y = key(t, [(0, 0, "out"), (0.30, 30, "out"), (0.45, 60, "snap"), (0.53, 62, "out"), (1.0, 0, "smooth")])   # in front, not beside
    fore = key(t, [(0, 0, "out"), (0.30, -60, "out"), (0.45, -5, "snap"), (0.53, -2, "out"), (1.0, -20, "smooth")])
    lean = key(t, [(0, 0, "out"), (0.30, 22, "out"), (0.45, -40, "snap"), (0.53, -46, "out"), (1.0, 0, "smooth")])   # back, then folded forward
    head = key(t, [(0, 0, "out"), (0.25, 20, "out"), (0.43, -25, "snap"), (0.53, -20, "out"), (1.0, 0, "smooth")])
    drop = key(t, [(0, 0, "out"), (0.30, -4, "out"), (0.45, 10, "snap"), (0.53, 12, "out"), (1.0, 0, "smooth")])     # the body drops into it (+Y is down)
    rot = {
        "rightArm": [(Y, arm_y), (Z, arm_z)], "rightForeArm": [(Y, fore)], "righthand": [(X, -fore * 0.3)],
        "leftArm": [(Z, 50), (Y, -25)], "leftForeArm": [(Y, 35)],
        "spine1": [(X, lean * 0.4)], "Spine3": [(X, lean * 0.6)],
        "neck": [(X, head * 0.4)], "head": [(X, head * 0.6)],
    }
    return rot, (0.0, drop, 0.0)


def frames(fn, length):
    n = int(round(length * FPS)) + 1
    out = []
    for f in range(n):
        rot, root = fn(f / (n - 1))
        quats = {}
        for name, turns in rot.items():
            q = (0.0, 0.0, 0.0, 1.0)
            for axis, deg in turns:
                q = qmul(axis_angle(axis, deg), q)
            quats[name] = list(q)
        out.append({"root": list(root), "rot": quats})
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn, length in [("BladeSlashR", slash_right, 1.0), ("BladeSlashL", slash_left, 0.95), ("BladeOverhead", overhead, 1.05)]:
        fr = frames(fn, length)
        json.dump({"fps": FPS, "frames": fr}, open(os.path.join(OUT, name + ".json"), "w"))
        print(name, len(fr), "frames")


if __name__ == "__main__":
    main()
