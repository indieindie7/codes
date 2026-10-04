"""Write ActorX .psa animation files for Advent Rising's skeletons (the engine imports them
with #exec ANIM IMPORT). The skeleton comes from one of our exported meshes (.psk from
tools/ukx_mesh.py); its reference pose has identity rotations, so a bone's local position
is its reference offset and its rotation is the clip's own.

Mesh space of the human skeletons: -Y up, +X the body's left, +Z forward.

    python tools/make_psa.py <out.psa> [mesh=marine]

Clips are functions of t (0..1) returning {bone: (axis, degrees)} plus a root offset; this
first one is a hand-made test (knees buckle, then a fall forward) to prove the import path.
"""
import glob
import json
import math
import os
import struct
import sys

ANIMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AdventMod", "Anims")
MESHES = os.path.join(os.path.expanduser("~"), "Documents", "AdventRising_meshes")


def read_skeleton(psk):
    d = open(psk, "rb").read()
    q = 0
    while q < len(d):
        cid, _, size, count = struct.unpack_from("<20sIii", d, q)
        q += 32
        if cid.rstrip(b"\0") == b"REFSKELT":
            out = []
            for i in range(count):
                r = struct.unpack_from("<64sIii4f3ff3f", d, q + 120 * i)
                out.append(dict(name=r[0].split(b"\0")[0].decode(), children=r[2], parent=r[3], pos=r[8:11]))
            return out
        q += size * count
    raise ValueError("no skeleton in " + psk)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def axis_angle(axis, deg):
    x, y, z = axis
    n = math.sqrt(x * x + y * y + z * z)
    s = math.sin(math.radians(deg) / 2) / n
    return (x * s, y * s, z * s, math.cos(math.radians(deg) / 2))


def ease(t, a, b):
    """0 before a, 1 after b, smooth in between"""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    u = (t - a) / (b - a)
    return u * u * (3 - 2 * u)


X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)


def clip_buckle(t):
    """knees give (onto them, shins back along the floor), then the body pitches forward.
    Signs, measured in game (ModReact pose log): about X, + swings a bone hanging down
    (a leg, an arm) forward and so leans a bone pointing up (the spine) back; a knee
    folds the shin back with -."""
    k = ease(t, 0.0, 0.45)        # buckle
    f = ease(t, 0.35, 1.0)        # fall forward
    rot = {
        "leftUpLeg": [(X, 15 * k)], "rightUpLeg": [(X, 15 * k)],
        "leftLeg": [(X, -115 * k)], "rightLeg": [(X, -115 * k)],
        "leftFoot": [(X, -40 * k)], "rightFoot": [(X, -40 * k)],
        "hips": [(X, -55 * f)],
        "spine1": [(X, -10 * k - 10 * f)], "Spine3": [(X, -8 * k - 8 * f)],
        "head": [(X, 10 * k - 20 * f)],
        # arms down from the T pose, then reaching forward as the body goes
        "leftArm": [(Z, 70 * k), (X, 40 * f)], "rightArm": [(Z, -70 * k), (X, 40 * f)],
        "leftForeArm": [(Y, 20 * f)], "rightForeArm": [(Y, -20 * f)],
    }
    # the hips drop a thigh's length as the knees fold (+Y is down)
    root = (0.0, 42 * k + 8 * f, 20 * f)
    return rot, root


CLIPS = [("ModDie_Buckle", clip_buckle, 1.6)]
FPS = 30
ROOT_TURN = (0.0, 0.0, 1.0, 0.0)


def chunk(fh, cid, size, recs):
    fh.write(struct.pack("<20sIii", cid.encode(), 1999801, size, len(recs)))
    for r in recs:
        fh.write(r)


def hand_frames(fn, length):
    """a clip function sampled into frames: (root offset, {bone: local quat})"""
    n = max(2, int(round(length * FPS)) + 1)
    frames = []
    for f in range(n):
        rot, root = fn(f / (n - 1))
        quats = {}
        for name, turns in rot.items():
            q = (0.0, 0.0, 0.0, 1.0)
            for axis, deg in turns:
                q = qmul(axis_angle(axis, deg), q)
            quats[name] = q
        frames.append((root, quats))
    return frames


def load_clips(folder):
    """retargeted clips (tools/kimodo_retarget.py): <name>.json, {fps, frames: [{root, rot}]}"""
    clips = []
    for fn in sorted(glob.glob(os.path.join(folder, "*.json"))):
        d = json.load(open(fn))
        frames = [(tuple(f["root"]), {k: tuple(v) for k, v in f["rot"].items()}) for f in d["frames"]]
        name = os.path.splitext(os.path.basename(fn))[0]
        clips.append((name, d["fps"], frames))
        META[name] = (d.get("zone", "any"), d.get("handoff", 0.9))
    return clips


def write_psa(path, bones, clips):
    """clips: (name, fps, frames); a frame is (root offset in mesh space, {bone: quat}).
    Quats are plain right-handed rotations in mesh space, local to the parent bone."""
    infos, keys = [], []
    names_known = {b["name"] for b in bones}
    for name, fps, frames in clips:
        n = len(frames)
        first = len(keys) // len(bones)
        for root, quats in frames:
            unknown = set(quats) - names_known
            if unknown:
                raise ValueError("%s: no bones %s" % (name, sorted(unknown)))
            for i, b in enumerate(bones):
                q = quats.get(b["name"], (0.0, 0.0, 0.0, 1.0))
                pos = b["pos"]
                if i == 0:
                    pos = tuple(p + o for p, o in zip(pos, root))
                    # the root's own space is the mesh's turned half round about the forward
                    # axis (see root_key): its position turns with it. Measured in game:
                    # unturned, the hips sat two hip-heights too low and moved mirrored.
                    pos = (-pos[0], -pos[1], pos[2])
                    q = root_key(q)
                else:
                    # ActorX stores every bone but the root conjugated
                    q = (-q[0], -q[1], -q[2], q[3])
                keys.append(struct.pack("<3f4ff", *pos, *q, 1.0))
        infos.append(struct.pack("<64s64siiiifffiii", name.encode(), b"None", len(bones), 0, 0,
                                 n * len(bones), 0.0, float(n), float(fps), 0, first, n))
    names = [struct.pack("<64sIii4f3ff3f", b["name"].encode(), 0, b["children"], b["parent"],
                         0, 0, 0, 1, *b["pos"], 0, 0, 0, 0) for b in bones]
    with open(path, "wb") as fh:
        chunk(fh, "ANIMHEAD", 0, [])
        chunk(fh, "BONENAMES", 120, names)
        chunk(fh, "ANIMINFO", 168, infos)
        chunk(fh, "ANIMKEYS", 32, keys)


def root_key(q):
    """the root's key. The game's root carries a half turn about the forward axis: with an
    identity root the body stands on its head (measured in game). MAKEPSA_ROOT picks the
    variant while the convention for a turned root is being measured."""
    mode = os.environ.get("MAKEPSA_ROOT", "turn*q")
    c = (-q[0], -q[1], -q[2], q[3])
    return {"turn*q": qmul(ROOT_TURN, q), "q*turn": qmul(q, ROOT_TURN),
            "turn*c": qmul(ROOT_TURN, c), "c*turn": qmul(c, ROOT_TURN)}[mode]


META = {"ModDie_Buckle": ("any", 0.9)}
UC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AdventMod", "Classes", "ModDeathClips.uc")
UC_TEMPLATE = """//=============================================================================
// ModDeathClips - the death clips in ModDeathAnims' animation set: which hit each one
// answers (Zone), when the body may go limp (Handoff, seconds in) and how long it runs
// (Length). Generated by
// tools/make_psa.py from AdventMod/Anims: don't edit by hand.
//=============================================================================
class ModDeathClips extends Object;

struct DeathClip
{
	var name Clip;
	var string Zone;
	var float Handoff;
	var float Length;
};
var array<DeathClip> Clips;

defaultproperties
{
%s
}
"""


def write_table(clips):
    rows = []
    for name, fps, frames in clips:
        if name.startswith("ModTest"):
            continue
        zone, handoff = META.get(name, ("any", 0.9))
        rows.append('     Clips(%d)=(Clip=%s,Zone="%s",Handoff=%.3f,Length=%.3f)'
                    % (len(rows), name, zone, handoff, len(frames) / float(fps)))
    open(UC, "w", newline="\r\n").write(UC_TEMPLATE % "\n".join(rows))


def main():
    out = sys.argv[1]
    mesh = sys.argv[2] if len(sys.argv) > 2 else "marine"
    bones = read_skeleton(os.path.join(MESHES, mesh + ".psk"))
    clips = [(name, FPS, hand_frames(fn, length)) for name, fn, length in CLIPS]
    clips += load_clips(ANIMS)
    write_psa(out, bones, clips)
    write_table(clips)
    print(out, ":", len(bones), "bones,", ", ".join("%s (%d frames)" % (c[0], len(c[2])) for c in clips))


if __name__ == "__main__":
    main()
