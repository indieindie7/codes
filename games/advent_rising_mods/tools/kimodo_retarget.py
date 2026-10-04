"""Retarget a Kimodo motion (NVIDIA's text-to-motion model, SOMA skeleton) onto Advent
Rising's human skeleton, as a clip for tools/make_psa.py.

    <kimodo venv python> tools/kimodo_retarget.py <motion.npz> <ClipName> [start_s [end_s]]

writes AdventMod/Anims/<ClipName>.json: {fps, frames: [{root: [x,y,z], rot: {bone: quat}}]}.

Both skeletons rest in a T pose with every joint's axes along the world's, so a bone
takes the world rotation of its SOMA joint. The spaces differ by a mirror:
SOMA is Y up, X to the body's left, Z forward (metres); Advent's mesh space is -Y up,
X left, Z forward (about centimetres). A rotation R becomes M R M with M = diag(1,-1,1).
"""
import json
import os
import sys

import numpy as np

# Advent bone -> SOMA joint (somaskel77 names). Bones not listed keep their parent's turn.
MAP = {
    "hips": "Hips", "spine": "Spine1", "spine1": "Spine2", "spine2": "Chest",
    "neck": "Neck1", "head": "Head",
    "leftShoulder": "LeftShoulder", "leftArm": "LeftArm", "leftForeArm": "LeftForeArm", "lefthand": "LeftHand",
    "rightShoulder": "RightShoulder", "rightArm": "RightArm", "rightForeArm": "RightForeArm", "righthand": "RightHand",
    "leftUpLeg": "LeftLeg", "leftLeg": "LeftShin", "leftFoot": "LeftFoot", "LeftToes": "LeftToeBase",
    "rightUpLeg": "RightLeg", "rightLeg": "RightShin", "rightFoot": "RightFoot", "RightToes": "RightToeBase",
}
# the Advent chain (bone, parent) for the bones above, parents first
PARENT = {
    "hips": None, "spine": "hips", "spine1": "spine", "spine2": "spine1",
    "neck": "spine2", "head": "neck",          # Spine3 sits between spine2 and neck, unturned
    "leftShoulder": "spine2", "leftArm": "leftShoulder", "leftForeArm": "leftArm", "lefthand": "leftForeArm",
    "rightShoulder": "spine2", "rightArm": "rightShoulder", "rightForeArm": "rightArm", "righthand": "rightForeArm",
    "leftUpLeg": "hips", "leftLeg": "leftUpLeg", "leftFoot": "leftLeg", "LeftToes": "leftFoot",
    "rightUpLeg": "hips", "rightLeg": "rightUpLeg", "rightFoot": "rightLeg", "RightToes": "rightFoot",
}
HIPS_HEIGHT = 103.6        # Advent's hips over the floor in its T pose (mesh units)
M = np.diag([1.0, -1.0, 1.0])
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AdventMod", "Anims")


def soma_names():
    """joint names of the 77-joint SOMA skeleton, in the NPZ's order (from Kimodo itself)"""
    from kimodo.skeleton import build_skeleton
    sk = build_skeleton(77)
    return [n for n in sk.bone_order_names]


def quat(R):
    """rotation matrix -> (x, y, z, w)"""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        q = ((R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s)
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k]) * 2
        v = [0.0, 0.0, 0.0]
        v[i] = 0.25 * s
        v[j] = (R[j, i] + R[i, j]) / s
        v[k] = (R[k, i] + R[i, k]) / s
        q = (v[0], v[1], v[2], (R[k, j] - R[j, k]) / s)
    return [round(float(x), 6) for x in q]


def retarget(npz, start=0.0, end=None, fps=30.0):
    d = np.load(npz)
    G = d["global_rot_mats"]                 # [T, J, 3, 3]
    pos = d["posed_joints"]                  # [T, J, 3]
    if G.ndim == 5:                          # a batch of one
        G, pos = G[0], pos[0]
    names = soma_names()
    assert len(names) == G.shape[1], (len(names), G.shape)
    idx = {n: i for i, n in enumerate(names)}
    if start < 0:                            # auto: just before the body first moves
        move = np.linalg.norm(pos[:, idx["Chest"]] - pos[0, idx["Chest"]], axis=1)
        moving = np.nonzero(move > 0.04)[0]
        start = max(0, (int(moving[0]) if len(moving) else 0) - 3) / fps
    a = int(round(start * fps))
    b = G.shape[0] if end is None else min(G.shape[0], int(round(end * fps)) + 1)
    hips = idx["Hips"]
    rest_h = float(pos[0, hips, 1])
    scale = HIPS_HEIGHT / rest_h if 0.7 < rest_h < 1.3 else HIPS_HEIGHT / 1.0
    # the clip starts facing mesh-forward (+Z), over the origin
    f0 = G[a, hips] @ np.array([0.0, 0.0, 1.0])
    yaw = np.arctan2(f0[0], f0[2])
    c, s = np.cos(-yaw), np.sin(-yaw)
    Y = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    origin = pos[a, hips] * np.array([1.0, 0.0, 1.0])
    frames = []
    for t in range(a, b):
        world = {bone: M @ (Y @ G[t, idx[j]]) @ M for bone, j in MAP.items()}
        rot = {}
        for bone, parent in PARENT.items():
            local = world[bone] if parent is None else world[parent].T @ world[bone]
            rot[bone] = quat(local)
        p = (Y @ (pos[t, hips] - origin)) * scale
        root = [round(float(p[0]), 3), round(float(HIPS_HEIGHT - p[1]), 3), round(float(p[2]), 3)]
        frames.append({"root": root, "rot": rot})
    # the body goes limp once it's truly falling: hips under 4/5 of their standing height
    # (a take that never falls: after half a second of its reaction)
    h = pos[a:b, hips, 1]
    low = np.nonzero(h < 0.8 * rest_h)[0]
    handoff = float(np.clip((int(low[0]) / fps if len(low) else 0.5), 0.35, len(h) / fps - 0.15))
    return {"fps": fps, "source": os.path.basename(npz), "handoff": round(handoff, 3), "frames": frames}


def expected(clip, frame, psk):
    """where the game should put the limbs for a frame, as ModReact's pose log prints it
    (vectors between bones in the body's frame: X forward, Y to its left, Z up)"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from make_psa import read_skeleton
    bones = read_skeleton(psk)
    f = clip["frames"][frame]
    W, P = {}, {}
    for i, b in enumerate(bones):
        q = f["rot"].get(b["name"], [0, 0, 0, 1])
        x, y, z, w = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        if i == 0:
            W[b["name"]], P[b["name"]] = R, np.array(b["pos"]) + np.array(f["root"])
        else:
            par = bones[b["parent"]]["name"]
            W[b["name"]] = W[par] @ R
            P[b["name"]] = P[par] + W[par] @ np.array(b["pos"])
    pairs = [("hips", "head"), ("hips", "leftUpLeg"), ("leftUpLeg", "leftLeg"), ("leftLeg", "leftFoot"),
             ("rightUpLeg", "rightLeg"), ("rightLeg", "rightFoot"), ("leftArm", "lefthand"), ("rightArm", "righthand")]
    out = []
    for a, b in pairs:
        v = P[b] - P[a]
        out.append("%s->%s %d,%d,%d" % (a, b, round(v[2]), round(v[0]), round(-v[1])))
    return " | ".join(out)


def main():
    npz, name = sys.argv[1], sys.argv[2]
    start = float(sys.argv[3]) if len(sys.argv) > 3 else -1.0
    end = float(sys.argv[4]) if len(sys.argv) > 4 else None
    clip = retarget(npz, start, end)
    hold = os.environ.get("RETARGET_HOLD")           # testing: one frame held for 2 s
    if hold:
        clip["frames"] = [clip["frames"][int(hold)]] * 60
        print("expected pose:", expected(clip, 0, os.path.join(os.path.expanduser("~"), "Documents", "AdventRising_meshes", "marine.psk")))
    # ModDie_<zone>_<take>: the zone picks the clip in game
    parts = name.split("_")
    clip["zone"] = parts[1].lower() if len(parts) > 2 and parts[0] == "ModDie" else "any"
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, name + ".json")
    json.dump(clip, open(out, "w"), separators=(",", ":"))
    print(out, len(clip["frames"]), "frames")


if __name__ == "__main__":
    main()
