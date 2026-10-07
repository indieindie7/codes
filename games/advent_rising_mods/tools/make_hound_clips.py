"""Hand-keyed clips for the Seeker hound (seekerhound skeleton, 40 bones): knockdowns, get-ups
and deaths. The game links the whole Seeker animation set to the hound too, so it "has"
Death_Impact and GetUp_back, but those are keyed for the upright Seekers and fold the hound
wrong; these are made for its own four-legged body. KIMODO only knows human bodies, so they
are keyed by hand on the animation principles (make_blade_clips.py's key()).

Writes AdventMod/AnimsHound/<Clip>.json; the build packs them into ModHound.psa with
make_psa.py (mesh seekerhound) and ModHoundAnims imports it.

The hound's reference pose is standing on all fours (not a T pose), all bone rotations
identity. Mesh space as for the humans: -Y up, +X the body's left, +Z forward; the hips are
the root (102 above the floor), and all four legs and the spine hang off them. Signs:
  hips about Z: + rolls the back over to the left (it lies on its left side), - to the right
  hips about X: + lifts the nose (rears up / goes over backwards), - dips it
  a bone hanging down (a leg), about X: + swings it forward, - back
  neck / head about Y: + turns the head to the body's left, about X: + lifts it
Root offsets are in mesh space: +Y is down.

    python tools/make_hound_clips.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_psa import X, Y, Z, qmul             # noqa: E402

HALF_Z = (0.0, 0.0, 1.0, 0.0)                    # a half turn about the forward axis
from make_blade_clips import key, frames, FPS   # noqa: E402

OUT = os.path.join(HERE, "..", "AdventMod", "AnimsHound")

SIDE_DROP = 72      # the hips lying on a side: 102 standing, about 30 lying
BELLY_DROP = 70     # lying on the belly, legs folded under
BACK_DROP = 70      # on its back
FLOOR = 2           # the reference pose's paws are at y = 0..2 (mesh space, +Y down)


def wobble(t, start, amp, freq, decay):
    """a decaying swing that starts at `start` (secondary motion: legs, head)"""
    if t < start:
        return 0.0
    u = t - start
    return amp * math.exp(-u * decay) * math.sin(u * freq * 2 * math.pi)


def legs_loose(t, start, amp, side):
    """limbs going slack once it lies on a side. The legs splay wide (the paws are 44 out from
    the middle), so the floor side's legs swing in under the body (else they go through the
    floor; the angles from a search on the skeleton, tools/clip_sheet.py), the upper side's
    droop toward the floor, and all of them swing out of phase and settle"""
    w = lambda ph, a=amp: wobble(t, start + ph, a, 2.2, 5.0)
    k = key(t, [(0, 0, "out"), (start * 0.7, 1, "out"), (1.0, 1, "smooth")])      # tucked as it goes over, not after
    low, high = ("Left", "left") if side > 0 else ("Right", "right")
    up, upl = ("Right", "right") if side > 0 else ("Left", "left")
    return {
        low + "FrontShoulder": [(Z, 30 * side * k)], low + "FrontArm": [(X, -20 * k + w(0.0))],
        low + "FrontElbow": [(X, -20 * k + w(0.03, amp * 0.6))],
        high + "UpLeg": [(Z, 20 * side * k), (X, -25 * k + w(0.05))], high + "Leg": [(X, 35 * k + w(0.08, amp * 0.5))],
        up + "FrontShoulder": [(Z, -15 * side * k)], up + "FrontArm": [(X, 15 * k + w(0.02))],
        up + "FrontElbow": [(X, -25 * k + w(0.06, amp * 0.6))],
        upl + "UpLeg": [(Z, -12 * side * k), (X, 18 * k + w(0.07))], upl + "Leg": [(X, -15 * k + w(0.1, amp * 0.5))],
    }


def merge(*parts):
    out = {}
    for p in parts:
        for k, v in p.items():
            out.setdefault(k, []).extend(v)
    return out


def knock(side):
    """thrown onto a side by a heavy hit and lying there dazed (1.1 s; the last frame is the
    lying pose the game holds). side +1: onto its left side (pushed to its left), -1: right"""
    def clip(t):
        # the hit shoves the hips sideways first, the legs on that side buckle, then it rolls over
        roll = key(t, [(0, 0, "out"), (0.12, 12, "out"), (0.45, 92, "in"), (0.55, 84, "out"), (0.70, 89, "smooth"), (1.0, 88, "smooth")])
        drop = key(t, [(0, 0, "out"), (0.12, 8, "out"), (0.45, SIDE_DROP + 4, "in"), (0.55, SIDE_DROP - 3, "out"), (1.0, SIDE_DROP, "smooth")])
        slide = key(t, [(0, 0, "out"), (0.45, 38, "out"), (1.0, 46, "smooth")])          # carried along by the shove
        twist = key(t, [(0, 0, "out"), (0.3, 18, "out"), (1.0, 10, "smooth")])           # the rear swings round a little
        head_up = key(t, [(0, 0, "out"), (0.1, 25, "snap"), (0.45, -5, "in"), (0.6, 12, "out"), (1.0, 18, "smooth")])   # a yelp, the head hits, lifts dazed
        head_side = key(t, [(0, 0, "out"), (0.45, 16, "in"), (0.55, 24, "out"), (1.0, 14, "smooth")])                   # toward the floor, lifted a little (dazed, alive)
        jaw = key(t, [(0, 0, "out"), (0.1, 28, "snap"), (0.35, 6, "smooth"), (1.0, 10, "smooth")])
        rot = merge(
            {"hips": [(Y, twist * side), (Z, roll * side)],
             "spine1": [(Z, 6 * side * key(t, [(0, 0, "out"), (0.45, 1, "in"), (1, 0.4, "smooth")]))],
             "neck": [(Y, head_side * 0.4 * side), (X, head_up * 0.4)],
             "Neck02": [(Y, head_side * 0.6 * side), (X, head_up * 0.6)],
             "jaw": [(X, -jaw)]},
            legs_loose(t, 0.45, 22, side),
        )
        return rot, (-slide * side, drop, 0.0)
    return clip


def getup(side):
    """up again from lying on a side (1.3 s): the head comes up first, the front legs push the
    chest up, the hind legs gather under, a pop up past standing and a shake"""
    def clip(t):
        roll = key(t, [(0, 88, "out"), (0.18, 84, "out"), (0.45, 35, "in"), (0.68, -8, "snap"), (0.78, 4, "out"), (1.0, 0, "smooth")])
        drop = key(t, [(0, SIDE_DROP, "out"), (0.45, 40, "in"), (0.68, -6, "snap"), (0.80, 3, "out"), (1.0, 0, "smooth")])
        slide = key(t, [(0, 46, "out"), (1.0, 46, "smooth")])
        pitch = key(t, [(0, 0, "out"), (0.4, 14, "out"), (0.62, -6, "in"), (0.8, 2, "out"), (1.0, 0, "smooth")])   # chest first, then the rear
        head_side = key(t, [(0, 14, "out"), (0.25, 0, "out"), (0.45, -12, "out"), (0.7, 0, "smooth"), (1.0, 0, "smooth")])
        head_up = key(t, [(0, 18, "out"), (0.25, 30, "out"), (0.7, 6, "smooth"), (1.0, 0, "smooth")])
        shake = wobble(t, 0.74, 14, 4.5, 6.0)
        # legs: tucked while lying, the front ones plant and straighten, the hind ones gather
        fr = key(t, [(0, 18, "out"), (0.2, 40, "out"), (0.45, 10, "in"), (0.68, -6, "snap"), (1.0, 0, "smooth")])
        fe = key(t, [(0, -25, "out"), (0.2, -60, "out"), (0.45, -10, "in"), (0.68, 4, "snap"), (1.0, 0, "smooth")])
        hu = key(t, [(0, 22, "out"), (0.35, 48, "out"), (0.6, 30, "in"), (0.75, -4, "snap"), (1.0, 0, "smooth")])
        hl = key(t, [(0, -18, "out"), (0.35, -50, "out"), (0.6, -30, "in"), (0.75, 3, "snap"), (1.0, 0, "smooth")])
        rot = {
            "hips": [(Y, 10 * side * (1 - t)), (X, pitch), (Z, roll * side + shake * 0.4)],
            "spine1": [(Z, -shake * 0.5)], "spine2": [(Z, -shake * 0.6)],
            "neck": [(Y, head_side * 0.4 * side + shake), (X, head_up * 0.4)],
            "Neck02": [(Y, head_side * 0.6 * side + shake * 0.8), (X, head_up * 0.6)],
            "RightFrontArm": [(X, fr)], "LeftFrontArm": [(X, fr * 0.9)],
            "RightFrontElbow": [(X, fe)], "LeftFrontElbow": [(X, fe * 0.9)],
            "rightUpLeg": [(X, hu)], "leftUpLeg": [(X, hu * 0.95)],
            "rightLeg": [(X, hl)], "leftLeg": [(X, hl * 0.95)],
        }
        # the lying legs (as the knockdown left them) let go over the first half
        lying = legs_loose(1.0, 0.0, 0.0, side)
        fade = 1 - key(t, [(0, 0, "out"), (0.4, 0, "out"), (0.7, 1, "smooth")])     # held until it is mostly upright
        for b, turns in lying.items():
            rot.setdefault(b, [])[:0] = [(a, v * fade) for a, v in turns]
        return rot, (-slide * side, drop, 0.0)
    return clip


def die_side(side):
    """shot dead, standing: a jolt, the legs fold, down onto a side and still (1.4 s)"""
    def clip(t):
        roll = key(t, [(0, 0, "out"), (0.15, -8, "out"), (0.32, 20, "in"), (0.55, 94, "in"), (0.64, 86, "out"), (0.8, 90, "smooth"), (1.0, 90, "smooth")])
        drop = key(t, [(0, 0, "out"), (0.15, -6, "out"), (0.35, 26, "in"), (0.55, SIDE_DROP + 5, "in"), (0.64, SIDE_DROP - 2, "out"), (1.0, SIDE_DROP + 1, "smooth")])
        slide = key(t, [(0, 0, "out"), (0.55, 24, "out"), (1.0, 26, "smooth")])
        head_up = key(t, [(0, 0, "out"), (0.12, 34, "snap"), (0.4, 10, "smooth"), (0.58, -18, "in"), (0.66, -10, "out"), (1.0, -14, "smooth")])
        head_side = key(t, [(0, 0, "out"), (0.4, 8, "smooth"), (0.6, 30, "in"), (0.68, 24, "out"), (1.0, 26, "smooth")])     # resting on the floor
        jaw = key(t, [(0, 0, "out"), (0.12, 35, "snap"), (0.5, 20, "smooth"), (1.0, 16, "smooth")])
        # the legs give before it falls (front first), then go slack; one last kick at 0.85
        buckle = key(t, [(0, 0, "out"), (0.3, 1, "in"), (1.0, 1, "smooth")])
        kick = wobble(t, 0.85, 16, 3.0, 9.0)
        rot = merge(
            {"hips": [(X, -10 * buckle), (Z, roll * side)],
             "neck": [(Y, head_side * 0.4 * side), (X, head_up * 0.4)],
             "Neck02": [(Y, head_side * 0.6 * side), (X, head_up * 0.6)],
             "jaw": [(X, -jaw)],
             "RightFrontElbow": [(X, -30 * buckle)], "LeftFrontElbow": [(X, -30 * buckle)],
             "rightLeg": [(X, -15 * buckle + kick)]},
            legs_loose(t, 0.55, 26, side),
        )
        return rot, (-slide * side, drop, 0.0)
    return clip


def die_front(t):
    """shot from the front while running: the front legs fold, the chest ploughs in, the rear
    goes on over a little and comes down, it ends on its belly tipped to one side (1.3 s)"""
    pitch = key(t, [(0, 0, "out"), (0.2, -22, "in"), (0.38, -34, "in"), (0.55, -8, "out"), (0.7, 2, "out"), (1.0, 0, "smooth")])   # nose down, rear up, back down
    drop = key(t, [(0, 0, "out"), (0.38, 48, "in"), (0.55, BELLY_DROP + 4, "in"), (0.65, BELLY_DROP - 2, "out"), (1.0, BELLY_DROP, "smooth")])
    slide = key(t, [(0, 0, "out"), (0.4, 40, "out"), (0.7, 58, "out"), (1.0, 60, "smooth")])     # carried on by its run
    tip = key(t, [(0, 0, "out"), (0.6, 0, "out"), (0.8, 24, "in"), (0.88, 20, "out"), (1.0, 22, "smooth")])
    head = key(t, [(0, 0, "out"), (0.2, -20, "in"), (0.4, -32, "in"), (0.55, -20, "out"), (1.0, -26, "smooth")])
    fold_f = key(t, [(0, 0, "out"), (0.25, 1, "in"), (1.0, 1, "smooth")])
    fold_h = key(t, [(0, 0, "out"), (0.3, 0.5, "out"), (0.5, 1, "smooth"), (1.0, 1, "smooth")])
    rot = {
        "hips": [(X, pitch), (Z, tip)],
        "neck": [(X, head * 0.4), (Y, tip * 0.6)], "Neck02": [(X, head * 0.6), (Y, tip * 0.8)],
        "jaw": [(X, -18 * fold_f)],
        # front legs splay back under the chest, hind legs fold forward under the belly
        # front legs reach forward along the floor (sphinx), hind legs tuck under (crouched);
        # the angles from a search on the skeleton for the lowest fold
        "RightFrontArm": [(X, 50 * fold_f)], "LeftFrontArm": [(X, 46 * fold_f)],
        "RightFrontElbow": [(X, 30 * fold_f)], "LeftFrontElbow": [(X, 34 * fold_f)],
        "RightFrontWrist": [(X, -45 * fold_f)], "LeftFrontWrist": [(X, -45 * fold_f)],
        "rightUpLeg": [(X, 110 * fold_h)], "leftUpLeg": [(X, 105 * fold_h)],
        "rightLeg": [(X, -80 * fold_h)], "leftLeg": [(X, -80 * fold_h)],
        "rightFoot": [(X, -140 * fold_h)], "leftFoot": [(X, -140 * fold_h)],
    }
    return rot, (0.0, drop, slide)


def die_blast(t):
    """thrown by a blast: up and over backwards, lands on its back, legs folded in the air,
    rolls part way back onto a side (1.6 s)"""
    flip = key(t, [(0, 0, "out"), (0.12, 30, "in"), (0.42, 170, "out"), (0.52, 190, "out"), (0.62, 178, "smooth"), (0.8, 182, "smooth"), (1.0, 180, "smooth")])
    roll = key(t, [(0, 0, "out"), (0.6, 0, "out"), (0.78, 35, "in"), (0.86, 28, "out"), (1.0, 32, "smooth")])
    lift = key(t, [(0, 0, "out"), (0.08, 6, "out"), (0.26, -70, "out"), (0.46, BACK_DROP + 6, "in"), (0.54, BACK_DROP - 8, "out"), (0.62, BACK_DROP + 2, "in"), (1.0, BACK_DROP, "smooth")])
    back = key(t, [(0, 0, "out"), (0.46, -90, "out"), (0.6, -110, "out"), (1.0, -112, "smooth")])     # thrown backwards along its body
    curl = key(t, [(0, 0, "out"), (0.2, 0.6, "out"), (0.5, 1, "out"), (1.0, 0.8, "smooth")])
    kick = wobble(t, 0.5, 20, 2.5, 5.0)
    head = key(t, [(0, 0, "out"), (0.15, 30, "snap"), (0.45, 40, "out"), (0.55, -10, "in"), (1.0, -30, "smooth")])   # lying on its back the head tips toward the chest, not into the floor
    rot = {
        "hips": [(Z, roll), (X, flip)],
        "neck": [(X, head * 0.4)], "Neck02": [(X, head * 0.6)], "jaw": [(X, -30 * curl)],
        "RightFrontArm": [(X, 30 * curl + kick)], "LeftFrontArm": [(X, 35 * curl - kick * 0.7)],
        "RightFrontElbow": [(X, -80 * curl)], "LeftFrontElbow": [(X, -70 * curl)],
        "rightUpLeg": [(X, 50 * curl - kick * 0.6)], "leftUpLeg": [(X, 45 * curl + kick)],
        "rightLeg": [(X, -60 * curl)], "leftLeg": [(X, -55 * curl)],
    }
    return rot, (0.0, lift, back)


CLIPS = [
    ("HoundKnock_L", knock(1), 1.1), ("HoundKnock_R", knock(-1), 1.1),
    ("HoundGetUp_L", getup(1), 1.3), ("HoundGetUp_R", getup(-1), 1.3),
    ("HoundDie_L", die_side(1), 1.4), ("HoundDie_R", die_side(-1), 1.4),
    ("HoundDie_Front", die_front, 1.3), ("HoundDie_Blast", die_blast, 1.6),
]


def floor_clamp(fr, bones):
    """lift the root wherever a bone would go through the floor; the lift is eased over the
    neighbouring frames so the body doesn't hop"""
    from clip_sheet import pose
    need = []
    for f in fr:
        wp = pose(bones, (f["root"], f["rot"]))
        need.append(max(0.0, max(p[1] for p in wp) - FLOOR))
    n = len(need)
    lift = [max(need[max(0, i - 1):i + 2]) for i in range(n)]
    lift = [sum(lift[max(0, i - 1):i + 2]) / len(lift[max(0, i - 1):i + 2]) for i in range(n)]
    for f, l in zip(fr, lift):
        f["root"][1] -= l
    return max(need)


def main():
    from make_psa import read_skeleton, MESHES
    bones = read_skeleton(os.path.join(MESHES, "seekerhound.psk"))
    os.makedirs(OUT, exist_ok=True)
    for name, fn, length in CLIPS:
        fr = frames(fn, length)
        print(name, "floor clamp lifted up to", round(floor_clamp(fr, bones)), end=": ")
        # measured in game (ModReact.HoundPoseLog against clip_sheet.pose): the hips come out as
        # keyed, but the spine chain points down where the clip has it up, as if the game's
        # skeleton carried a half turn about the forward axis at 'spine'. A half turn keyed on
        # 'spine' cancels it (its own key is otherwise unused).
        # The bones under it then turn in that turned frame: pitch and yaw come out reversed
        # (the head lifted where it should drop), roll as keyed, so theirs are mirrored too.
        for f in fr:
            for b in ("spine1", "spine2", "neck", "Neck02", "head", "jaw"):
                if b in f["rot"]:
                    x, y, z, w = f["rot"][b]
                    f["rot"][b] = [-x, -y, z, w]
            f["rot"]["spine"] = list(qmul(HALF_Z, tuple(f["rot"].get("spine", (0.0, 0.0, 0.0, 1.0)))))
        json.dump({"fps": FPS, "spine_half_turn": True, "frames": fr}, open(os.path.join(OUT, name + ".json"), "w"))
        print(name, len(fr), "frames")


if __name__ == "__main__":
    main()
