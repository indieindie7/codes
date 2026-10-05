"""Ragdolls for Advent Rising: writes KarmaData\\Advent.ka, the Karma asset file the
PC release lacks (the engine loads ragdoll skeletons from KarmaData\\*.ka by the
name in a pawn's RagdollOverride; without them a body set to PHYS_KarmaRagdoll
freezes as posed).

    python make_ka.py <meshes dir> <out.ka>
    (meshes dir: the .psk files tools/ukx_mesh.py exported)

Each asset is built from a skeleton read out of a .psk: a capsule (sphyl) body per
chosen bone, from the bone to the next chosen bone down the chain, joined to its
parent body by a cone-and-twist ("skeletal") joint. Advent's reference skeletons
have identity bone rotations, so every bone frame is the mesh frame moved to the
bone: capsules, joint axes and part transforms come straight from bone positions.
Karma units are mesh units x SCALE. Mesh space: X to the side, -Y up, Z forward.
"""
import math, os, re, struct, sys

SCALE = 0.01

# per skeleton: the psk it comes from, and its bodies:
#   bone: (end bone or None, radius in mesh units, cone half angle, twist half angle, mass weight)
#   an end of None runs the capsule END_LEN units along its parent's direction
RIGS = {
    "humanMale2": ("marine", {
        "hips":         ("spine1", 13, 0, 0, 14),
        "spine1":       ("Spine3", 13, 0.35, 0.3, 12),
        "Spine3":       ("neck", 14, 0.35, 0.3, 14),
        "head":         (None, 10, 0.6, 0.6, 6),
        "leftArm":      ("leftForeArm", 6, 1.3, 0.8, 3),
        "leftForeArm":  ("lefthand", 5, 1.2, 0.5, 2),
        "rightArm":     ("rightForeArm", 6, 1.3, 0.8, 3),
        "rightForeArm": ("righthand", 5, 1.2, 0.5, 2),
        "leftUpLeg":    ("leftLeg", 9, 1.0, 0.4, 9),
        "leftLeg":      ("leftFoot", 7, 1.2, 0.2, 5),
        "rightUpLeg":   ("rightLeg", 9, 1.0, 0.4, 9),
        "rightLeg":     ("rightFoot", 7, 1.2, 0.2, 5),
    }),
    "seeker": ("seekerinfantry", {
        "hips":             ("spine1", 15, 0, 0, 16),
        "spine1":           ("spine2", 15, 0.35, 0.3, 14),
        "spine2":           ("neck", 17, 0.35, 0.3, 16),
        "head":             (None, 11, 0.6, 0.6, 6),
        "leftArm":          ("leftForeArm", 6, 1.3, 0.8, 3),
        "leftForeArm":      ("lefthand", 5, 1.2, 0.5, 2),
        "rightArm":         ("rightForeArm", 6, 1.3, 0.8, 3),
        "rightForeArm":     ("righthand", 5, 1.2, 0.5, 2),
        "LeftFrontArm":     ("LeftFrontElbow", 7, 1.2, 0.6, 4),
        "LeftFrontElbow":   ("LeftFrontWrist", 6, 1.2, 0.4, 3),
        "RightFrontArm":    ("RightFrontElbow", 7, 1.2, 0.6, 4),
        "RightFrontElbow":  ("RightFrontWrist", 6, 1.2, 0.4, 3),
        "leftUpLeg":        ("leftLeg", 11, 1.0, 0.4, 11),
        "leftLeg":          ("leftFoot", 8, 1.2, 0.2, 6),
        "leftFoot":         ("LeftToes", 6, 0.8, 0.2, 3),
        "rightUpLeg":       ("rightLeg", 11, 1.0, 0.4, 11),
        "rightLeg":         ("rightFoot", 8, 1.2, 0.2, 6),
        "rightFoot":        ("RightToes", 6, 0.8, 0.2, 3),
    }),
    "seekerhound": ("seekerhound", {
        "hips":             ("spine1", 13, 0, 0, 14),
        "spine1":           ("spine2", 13, 0.35, 0.3, 12),
        "spine2":           ("neck", 14, 0.35, 0.3, 12),
        "head":             (None, 10, 0.6, 0.6, 5),
        "LeftFrontArm":     ("LeftFrontElbow", 6, 1.2, 0.6, 3),
        "LeftFrontElbow":   ("LeftFrontWrist", 5, 1.2, 0.4, 2),
        "RightFrontArm":    ("RightFrontElbow", 6, 1.2, 0.6, 3),
        "RightFrontElbow":  ("RightFrontWrist", 5, 1.2, 0.4, 2),
        "leftUpLeg":        ("leftLeg", 9, 1.0, 0.4, 8),
        "leftLeg":          ("leftFoot", 7, 1.2, 0.2, 5),
        "leftFoot":         ("LeftToes", 5, 0.8, 0.2, 2),
        "rightUpLeg":       ("rightLeg", 9, 1.0, 0.4, 8),
        "rightLeg":         ("rightFoot", 7, 1.2, 0.2, 5),
        "rightFoot":        ("RightToes", 5, 0.8, 0.2, 2),
    }),
}
END_LEN = 20.0

# hinge joints (knees, elbows): instead of a cone, one axis with an asymmetric range, as in
# UT2004's Human.ka. Per rig: body -> (where the body's end goes when the joint bends,
# mesh space; low limit; high limit), radians. Mesh space: X to the side, -Y up, Z forward.
# The hinge axis is (bone direction x bend), so a positive angle bends toward "bend".
BACK, FORWARD = (0, 0, -1), (0, 0, 1)
HINGES = {
    "humanMale2": {
        "leftLeg": (BACK, -0.1, 1.9), "rightLeg": (BACK, -0.1, 1.9),          # knees
        "leftForeArm": (FORWARD, -0.1, 2.0), "rightForeArm": (FORWARD, -0.1, 2.0),   # elbows
    },
    "seeker": {
        "leftLeg": (BACK, -0.1, 1.9), "rightLeg": (BACK, -0.1, 1.9),
        "leftForeArm": (FORWARD, -0.1, 2.0), "rightForeArm": (FORWARD, -0.1, 2.0),
        "LeftFrontElbow": (BACK, -0.1, 1.5), "RightFrontElbow": (BACK, -0.1, 1.5),
    },
}
UC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AdventMod", "Classes", "ModRagdollBones.uc")
TOTAL_MASS = 1.0


UC_TEMPLATE = """//=============================================================================
// ModRagdollBones - the ragdoll skeletons in KarmaData\\Advent.ka and the bones each
// needs (Bones[First .. First+Count-1]), for ModGore.Limp. Generated by
// tools/make_ka.py: don't edit by hand.
//=============================================================================
class ModRagdollBones extends Object;

struct Skeleton
{
	var string Name;
	var int First, Count;
};
var array<Skeleton> Skeletons;
var array<name> Bones;

defaultproperties
{
%s
%s
}
"""


def read_bones(psk):
    d = open(psk, "rb").read()
    q = 0
    while q < len(d):
        cid, _, size, count = struct.unpack_from("<20sIii", d, q)
        q += 32
        if cid.rstrip(b"\0") == b"REFSKELT":
            bones = []
            for i in range(count):
                rec = struct.unpack_from("<64sIii4f3ff3f", d, q + 120 * i)
                bones.append((rec[0].split(b"\0")[0].decode(), rec[3], rec[8:11]))
            # world positions (identity rotations: positions add up)
            world = []
            for i, (name, parent, pos) in enumerate(bones):
                w = pos if i == 0 else tuple(a + b for a, b in zip(world[parent], pos))
                world.append(w)
            return {name: (i, parent, world[i]) for i, (name, parent, pos) in enumerate(bones)}, [b[0] for b in bones]
        q += size * count
    raise SystemExit("no skeleton in " + psk)


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, k): return tuple(x * k for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def length(a): return math.sqrt(dot(a, a))
def norm(a):
    l = length(a)
    return mul(a, 1 / l) if l > 1e-9 else (0.0, -1.0, 0.0)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def perp(d):
    p = cross(d, (1, 0, 0)) if abs(d[0]) < 0.9 else cross(d, (0, 0, 1))
    return norm(p)
def f(v): return ",".join("%.7g" % x for x in v)


def build(asset, psk, bodies, hinges=None):
    hinges = hinges or {}
    bones, order = read_bones(psk)
    for b, (end, *_rest) in bodies.items():
        if b not in bones or (end and end not in bones):
            raise SystemExit("%s: bone missing: %s/%s" % (asset, b, end))
    names = [b for b in order if b in bodies]          # skeleton order: parents first

    def part_parent(b):
        if bones[b][0] == 0:
            return None                                # the root (its parent index is itself)
        p = bones[b][1]
        while True:
            pn = order[p]
            if pn in bodies:
                return pn
            if p == 0:
                return None
            p = bones[pn][1]

    info = {}
    for b in names:
        end, radius, cone, twist, weight = bodies[b]
        o = bones[b][2]
        if end:
            e = bones[end][2]
        else:
            pp = part_parent(b)
            dirp = norm(sub(o, bones[pp][2])) if pp else (0, -1, 0)
            e = add(o, mul(dirp, END_LEN))
        seg = sub(e, o)
        if b == "hips":
            seg = sub(bones[bodies["hips"][0]][2], o)
        info[b] = dict(origin=o, seg=seg, radius=radius, cone=cone, twist=twist, weight=weight, parent=part_parent(b))
    wsum = sum(i["weight"] for i in info.values())

    out = ['\t<ASSET id="%s" graphic="%s.psk" scale="%g" mass_scale="1" length_scale="1">' % (asset, os.path.basename(psk)[:-4], SCALE)]
    # geometry: a capsule from the bone along its segment (Karma's sphyl runs along its Z)
    for b in names:
        i = info[b]
        L = length(i["seg"]) * SCALE
        r = i["radius"] * SCALE
        d = norm(i["seg"])
        x = perp(d)
        y = cross(d, x)
        mid = mul(i["seg"], 0.5 * SCALE)
        tm = list(x) + [0] + list(y) + [0] + list(d) + [0] + list(mid) + [1]
        out += ['\t\t<GEOMETRY id="%s">' % b,
                '\t\t\t<PRIMITIVE id="%s_1" type="sphyl">' % b,
                '\t\t\t\t<RADIUS>%.7g</RADIUS>' % r,
                '\t\t\t\t<HEIGHT>%.7g</HEIGHT>' % max(L - r, r),
                '\t\t\t\t<TM>%s</TM>' % f(tm),
                '\t\t\t</PRIMITIVE>',
                '\t\t</GEOMETRY>']
    # bodies: mass by weight, a solid cylinder's inertia turned onto the segment
    for b in names:
        i = info[b]
        m = TOTAL_MASS * i["weight"] / wsum
        L = length(i["seg"]) * SCALE
        r = i["radius"] * SCALE
        il = m * r * r / 2
        ip = m * (3 * r * r + L * L) / 12
        d = norm(i["seg"])
        I = [[ip * (1 if a == c else 0) + (il - ip) * d[a] * d[c] for c in range(3)] for a in range(3)]
        mid = mul(i["seg"], 0.5 * SCALE)
        out += ['\t\t<MODEL id="%s" type="dynamics_and_geometry" geometry="%s">' % (b, b),
                '\t\t\t<DYNAMICS>',
                '\t\t\t\t<MASS>%.7g</MASS>' % m,
                '\t\t\t\t<DENSITY>1</DENSITY>',
                '\t\t\t\t<MASS_OFFSET>%s</MASS_OFFSET>' % f(mid),
                '\t\t\t\t<INERTIA>%s</INERTIA>' % f((I[0][0], I[0][1], I[0][2], I[1][1], I[1][2], I[2][2])),
                '\t\t\t\t<LIN_DAMP>0.1</LIN_DAMP>',
                '\t\t\t\t<ANG_DAMP>0.3</ANG_DAMP>',
                '\t\t\t\t<FAST_SPIN>0,1,0</FAST_SPIN>',
                '\t\t\t\t<USE_FAST_SPIN>0</USE_FAST_SPIN>',
                '\t\t\t</DYNAMICS>',
                '\t\t</MODEL>']
    # parts: each body on its bone, placed where the bone is in the reference pose
    for b in names:
        i = info[b]
        # every part names a parent; the root's is a bone outside the asset (as in
        # UT2004's files, where the pelvis' parent is bip01): a part with none crashes
        par = ' parent="%s"' % (i["parent"] or "Root")
        tm = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0] + list(mul(i["origin"], SCALE)) + [1]
        out += ['\t\t<PART id="%s" model="%s"%s>' % (b, b, par), '\t\t\t<TM>%s</TM>' % f(tm), '\t\t</PART>']
    # bodies that touch at a joint don't collide (only those: pairs further apart, as
    # siblings or grandparents, crashed the engine's ragdoll setup)
    pairs = set()
    for b in names:
        p = info[b]["parent"]
        if p:
            pairs.add((b, p))
    for a, c in sorted(pairs):
        out.append('\t\t<NO_COLLISION part1="%s" part2="%s"></NO_COLLISION>' % (a, c))
    # joints: a cone around the body's segment, a twist about it
    for b in names:
        i = info[b]
        p = i["parent"]
        if not p:
            continue
        d = norm(i["seg"])
        o = perp(d)
        pos2 = mul(sub(i["origin"], info[p]["origin"]), SCALE)
        if b in hinges:
            bend, low, high = hinges[b]
            axis = norm(cross(d, bend))
            out += ['\t\t<JOINT id="%s" part1="%s" part2="%s" type="hinge">' % (b, b, p),
                    '\t\t\t<HIGH_LIMIT>%.7g</HIGH_LIMIT>' % high,
                    '\t\t\t<LOW_LIMIT>%.7g</LOW_LIMIT>' % low,
                    '\t\t\t<HIGH_STIFFNESS>1000</HIGH_STIFFNESS>',
                    '\t\t\t<LOW_STIFFNESS>1000</LOW_STIFFNESS>',
                    '\t\t\t<LIMITED>1</LIMITED>',
                    '\t\t\t<MOTORIZED>0</MOTORIZED>',
                    '\t\t\t<DES_VEL>1</DES_VEL>',
                    '\t\t\t<MAX_FORCE>1000</MAX_FORCE>',
                    '\t\t\t<POS1>0,0,0</POS1>',
                    '\t\t\t<POS2>%s</POS2>' % f(pos2),
                    '\t\t\t<PRIMARY_AXIS1>%s</PRIMARY_AXIS1>' % f(axis),
                    '\t\t\t<PRIMARY_AXIS2>%s</PRIMARY_AXIS2>' % f(axis),
                    '\t\t\t<ORTHOGONAL_AXIS1>%s</ORTHOGONAL_AXIS1>' % f(d),
                    '\t\t\t<ORTHOGONAL_AXIS2>%s</ORTHOGONAL_AXIS2>' % f(d),
                    '\t\t</JOINT>']
            continue
        out += ['\t\t<JOINT id="%s" part1="%s" part2="%s" type="skeletal">' % (b, b, p),
                '\t\t\t<CONE_TYPE>2</CONE_TYPE>',
                '\t\t\t<CONE_HALF_ANGLE_X>%.7g</CONE_HALF_ANGLE_X>' % i["cone"],
                '\t\t\t<CONE_HALF_ANGLE_Y>%.7g</CONE_HALF_ANGLE_Y>' % i["cone"],
                '\t\t\t<CONE_STIFFNESS>1000</CONE_STIFFNESS>',
                '\t\t\t<CONE_DAMPING>1</CONE_DAMPING>',
                '\t\t\t<TWIST_TYPE>2</TWIST_TYPE>',
                '\t\t\t<TWIST_HALF_ANGLE>%.7g</TWIST_HALF_ANGLE>' % i["twist"],
                '\t\t\t<TWIST_STIFFNESS>1000</TWIST_STIFFNESS>',
                '\t\t\t<TWIST_DAMPING>1</TWIST_DAMPING>',
                '\t\t\t<POS1>0,0,0</POS1>',
                '\t\t\t<POS2>%s</POS2>' % f(pos2),
                '\t\t\t<PRIMARY_AXIS1>%s</PRIMARY_AXIS1>' % f(d),
                '\t\t\t<PRIMARY_AXIS2>%s</PRIMARY_AXIS2>' % f(d),
                '\t\t\t<ORTHOGONAL_AXIS1>%s</ORTHOGONAL_AXIS1>' % f(o),
                '\t\t\t<ORTHOGONAL_AXIS2>%s</ORTHOGONAL_AXIS2>' % f(o),
                '\t\t</JOINT>']
    out.append('\t</ASSET>')
    # the engine matches part names against the mesh's bone names in lower case: a
    # part named with capitals (Spine3, leftUpLeg) finds no bone and crashes the game
    if os.environ.get("MAKEKA_CASE") != "keep":
        out = [re.sub(r'((?:id|model|geometry|parent|part1|part2)=")([^"]*)(")', lambda m: m.group(1) + m.group(2).lower() + m.group(3), l)
               if '<ASSET' not in l else l for l in out]
    return out, len(names)


def main():
    meshes, dst = sys.argv[1], sys.argv[2]
    lines = ['<?xml version="1.0"?>', '', '<KARMA ka_file_version="1.0">']
    only = os.environ.get("MAKEKA_ONLY")              # testing: "bone,bone" keeps just those bodies
    for asset, (mesh, bodies) in RIGS.items():
        if only:
            bodies = {k: v for k, v in bodies.items() if k in only.split(",")}
        if os.environ.get("MAKEKA_CONE"):                # testing: one cone/twist for every joint
            c, t = (float(x) for x in os.environ["MAKEKA_CONE"].split(","))
            bodies = {k: (v[0], v[1], c, t, v[4]) for k, v in bodies.items()}
        hinges = {} if os.environ.get("MAKEKA_NOHINGE") else HINGES.get(asset, {})   # testing: cones everywhere
        body, n = build(asset, os.path.join(meshes, mesh + ".psk"), bodies, hinges)
        lines += body
        print(asset, "from", mesh + ".psk:", n, "bodies")
    lines.append('</KARMA>')
    # the same skeletons for script: ModGore only ragdolls a body whose mesh has every
    # bone of the skeleton (a part with no bone crashes the game: Seeker hounds ask for
    # "seeker" but have no upper arms)
    sets, flat = [], []
    for k, (a, (m, bodies)) in enumerate(RIGS.items()):
        sets.append('     Skeletons(%d)=(Name="%s",First=%d,Count=%d)' % (k, a, len(flat), len(bodies)))
        flat += list(bodies)
    names = ["     Bones(%d)=%s" % (k, n) for k, n in enumerate(flat)]
    src = UC_TEMPLATE % ("\n".join(sets), "\n".join(names))
    open(UC, "w", newline="\r\n").write(src)
    print(UC)
    open(dst, "w", newline="\r\n").write("\n".join(lines) + "\n")
    print(dst)


if __name__ == "__main__":
    main()
