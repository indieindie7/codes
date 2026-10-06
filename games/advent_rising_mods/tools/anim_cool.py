"""The animation principles applied to a generated clip (the user: the first swings "failed
the rule of cool"): a motion-capture-like clip is realistic and small; an attack that reads
needs ANTICIPATION (a slow, visible wind-up), a SNAP (the strike over a few frames), FOLLOW-
THROUGH and OVERSHOOT (the body keeps going past the end pose and settles), and
EXAGGERATION (poses pushed further than life), on clean ARCS.

    python tools/anim_cool.py <in.json> <out.json> [exaggerate=1.5] [snap=0.35] [anticipation=1.6]

- finds the strike: the frame where the right hand moves fastest (forward kinematics over the
  marine skeleton, as make_psa.py does);
- re-times: the wind-up before it runs at 1/anticipation speed (longer, readable), the strike
  window (the 0.25 s around the peak) at 1/snap speed (faster), the rest as is;
- exaggerates: every bone's rotation is pushed away from the first frame's pose by
  `exaggerate` (slerp past 1), the arms and spine most, the legs less;
- overshoot: after the strike the pose overshoots its path by 12% and eases back over 0.2 s.
Writes the same JSON format (fps, frames: [{root, rot}]) for make_psa.py.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_psa import read_skeleton, qmul, MESHES   # noqa: E402

EXAG = {"spine": 1.0, "spine1": 1.0, "spine2": 1.0, "Spine3": 1.0, "neck": 0.7, "head": 0.7,
        "rightShoulder": 1.0, "rightArm": 1.0, "rightForeArm": 1.0, "righthand": 1.0,
        "leftShoulder": 0.8, "leftArm": 0.8, "leftForeArm": 0.8, "lefthand": 0.8,
        "hips": 0.6, "leftUpLeg": 0.4, "leftLeg": 0.4, "leftFoot": 0.3, "rightUpLeg": 0.4, "rightLeg": 0.4, "rightFoot": 0.3}


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qslerp(a, b, t):
    """slerp from a to b; t may run past 1 (extrapolation) or below 0"""
    a = qnorm(a); b = qnorm(b)
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b = tuple(-c for c in b); d = -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(max(-1.0, min(1.0, d)))
    s = math.sin(th)
    wa = math.sin((1 - t) * th) / s
    wb = math.sin(t * th) / s
    return qnorm(tuple(wa * x + wb * y for x, y in zip(a, b)))


def qrot(q, v):
    """rotate vector v by quaternion q (x, y, z, w)"""
    x, y, z, w = q
    vx, vy, vz = v
    # q * v * q^-1
    tx = 2 * (y * vz - z * vy); ty = 2 * (z * vx - x * vz); tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def hand_positions(bones, frames, bone="righthand"):
    """world position of a bone per frame by forward kinematics (local quats, reference offsets)"""
    index = {b["name"]: i for i, b in enumerate(bones)}
    chain = []
    i = index[bone]
    while True:
        chain.append(i)
        if bones[i]["parent"] == i and i == 0:
            break
        i = bones[i]["parent"]
        if i == 0:
            chain.append(0)
            break
    chain.reverse()
    out = []
    for root, rot in frames:
        pos = tuple(root)
        q = (0.0, 0.0, 0.0, 1.0)
        for k, i in enumerate(chain):
            b = bones[i]
            if k > 0:
                pos = tuple(p + d for p, d in zip(pos, qrot(q, b["pos"])))
            q = qmul(q, rot.get(b["name"], (0.0, 0.0, 0.0, 1.0)))
        out.append(pos)
    return out


def sample(frames, t):
    """frame at a fractional index, slerped"""
    n = len(frames)
    if t <= 0:
        return frames[0]
    if t >= n - 1:
        return frames[-1]
    i = int(t); f = t - i
    r0, q0 = frames[i]; r1, q1 = frames[i + 1]
    root = tuple(a + (b - a) * f for a, b in zip(r0, r1))
    rot = {k: qslerp(q0[k], q1.get(k, q0[k]), f) for k in q0}
    return (root, rot)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    exag = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    snap = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
    antic = float(sys.argv[5]) if len(sys.argv) > 5 else 1.6
    d = json.load(open(src))
    fps = float(d["fps"])
    frames = [(tuple(f["root"]), {k: tuple(v) for k, v in f["rot"].items()}) for f in d["frames"]]
    bones = read_skeleton(os.path.join(MESHES, "marine.psk"))
    hand = hand_positions(bones, frames)
    speed = [0.0] + [math.dist(hand[i], hand[i - 1]) * fps for i in range(1, len(hand))]
    peak = max(range(len(speed)), key=lambda i: speed[i])
    half = max(2, int(round(0.125 * fps)))
    s0, s1 = max(0, peak - half), min(len(frames) - 1, peak + half)
    # the time map: output time -> input frame index, piecewise
    seg = [(0, s0, antic), (s0, s1, snap), (s1, len(frames) - 1, 1.0)]     # (from, to, output duration factor)
    out_frames = []
    t_out = 0.0
    total_out = sum((b - a) * k for a, b, k in seg)
    n_out = int(round(total_out)) + 1
    for j in range(n_out):
        t = j
        src_t = 0.0
        for a, b, k in seg:
            length = (b - a) * k
            if t <= length or (a, b, k) == seg[-1]:
                src_t = a + (t / k if k > 0 else 0)
                break
            t -= length
        src_t = min(src_t, len(frames) - 1)
        root, rot = sample(frames, src_t)
        # exaggeration: push away from the first frame's pose
        root0, rot0 = frames[0]
        rot2 = {}
        for k, q in rot.items():
            e = 1 + (exag - 1) * EXAG.get(k, 0.6)
            rot2[k] = qslerp(rot0.get(k, (0, 0, 0, 1)), q, e)
        root2 = tuple(r0 + (r - r0) * (1 + (exag - 1) * 0.6) for r0, r in zip(root0, root))
        out_frames.append([root2, rot2])
    # overshoot after the strike: the pose runs 12% past itself for 0.2 s and eases back
    strike_out = int(round((s0) * antic + (s1 - s0) * snap))
    over = int(round(0.2 * fps))
    for j in range(strike_out, min(len(out_frames), strike_out + over)):
        w = 0.12 * (1 - (j - strike_out) / float(over))
        prev = out_frames[max(0, j - 2)]
        root, rot = out_frames[j]
        rot2 = {k: qslerp(prev[1].get(k, q), q, 1 + w) for k, q in rot.items()}
        out_frames[j] = [root, rot2]
    json.dump({"fps": fps, "frames": [{"root": list(r), "rot": {k: list(q) for k, q in rot.items()}} for r, rot in out_frames]}, open(dst, "w"))
    print("%s: %d frames -> %d; strike at frame %d (%.2f s, hand %.0f units/s), wind-up x%.2f, strike x%.2f, exaggerate %.2f"
          % (os.path.basename(dst), len(frames), len(out_frames), peak, peak / fps, speed[peak], antic, snap, exag))


if __name__ == "__main__":
    main()
