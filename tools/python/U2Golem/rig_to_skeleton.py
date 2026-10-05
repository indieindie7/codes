"""Rig a generated T-pose game mesh onto an existing character's skeleton, by borrowing that character's weights.

Run:  blender -b <rigged_character.blend> --python rig_to_skeleton.py -- <out.blend> low=<mesh.glb>
      [test=1] [smooth=4] [cloth=0.85] [slim=1.25] [name=Body]
<rigged_character.blend>: an armature with its skinned body (gem2blend.py output, e.g. dalton\\PlayerGame.blend).
low: the new mesh (retopo_bake.py output), standing upright, facing -Y, arms out to the sides.

1. Fit in sections to the skeleton's proportions (see the comment in the code): legs and torso are stretched
   to the shoulder joints' height, the head keeps its shape, the arms take the skeleton's arm length.
2. Match the pose: the old skeleton's arms and legs are rotated until the old body's hands and feet sit where
   the new mesh has its hands and feet (generated T-poses never have exactly the rest pose's angles).
3. Weights: every new vertex takes the bone weights of the nearest point on the old body's surface in that
   pose; weights are then smoothed over the new mesh, cut to 4 bones per vertex and normalised.
4. Un-pose: each new vertex is moved back through the inverse of its own skinning transform, so that with
   the skeleton at rest the new mesh is at rest too, and in the matched pose it is exactly as generated.
5. The old body is removed; the new mesh gets the Armature modifier.
test=1 also renders <out>_rest.png and <out>_pose.png (an arms-down walking pose) on the CPU.
Then: blender -b <out.blend> --python blend2psk.py -- <out.psk>
"""
import math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(a[0]))[0]
o = dict(x.split("=", 1) for x in a[1:])
SMOOTH, TEST, NAME = int(o.get("smooth", 4)), int(o.get("test", 0)), o.get("name", "Body")
SLIM = float(o.get("slim", 1.25))        # trunk no wider/deeper than this x the original body (0 = off)
CLOTH = float(o.get("cloth", 0.85))     # how far hanging cloth may go over to the pelvis (0 = off)

arm = [x for x in bpy.data.objects if x.type == "ARMATURE"][0]
body = [x for x in bpy.data.objects if x.type == "MESH" and x.parent == arm][0]
dg = bpy.context.evaluated_depsgraph_get


def body_points():
    ev = body.evaluated_get(dg())
    return np.array([tuple(ev.matrix_world @ v.co) for v in ev.data.vertices])


def ends(P):
    """hand and foot centres of an arms-out figure: the far ends in x, the soles on each side"""
    x0, x1, z0, H = P[:, 0].min(), P[:, 0].max(), P[:, 2].min(), P[:, 2].max() - P[:, 2].min()
    cx = (x0 + x1) / 2
    half = (x1 - x0) / 2
    r = {}
    r["handL"] = P[P[:, 0] > cx + 0.86 * half].mean(0)
    r["handR"] = P[P[:, 0] < cx - 0.86 * half].mean(0)
    low = P[P[:, 2] < z0 + 0.05 * H]
    r["footL"], r["footR"] = low[low[:, 0] > cx].mean(0), low[low[:, 0] < cx].mean(0)
    r["sole"], r["cx"], r["cy"] = z0, cx, float(np.median(P[np.abs(P[:, 2] - (z0 + 0.6 * H)) < 0.05 * H, 1]))
    return r


def bn(suffix):
    """bone by the end of its name, any prefix or case: Unreal II's "Merc L UpperArm" or UT2004's "Bip01 L UpperArm" """
    m = [b.name for b in arm.data.bones if b.name.lower().endswith(suffix.lower())]
    if not m:
        raise KeyError(suffix)
    return min(m, key=len)



def swing(root, tip, delta):
    """rotate bone `root` about its head so that bone `tip`'s head moves by about `delta` (armature space)"""
    h = pb[root].head.copy()
    d0 = (pb[tip].head - h)
    d1 = d0 + Vector(delta)
    q = d0.rotation_difference(d1)
    pb[root].matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb[root].matrix
    bpy.context.view_layer.update()


# ---- 1. load and fit the new mesh -------------------------------------------------------------
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=o["low"])
new = [x for x in bpy.data.objects if x not in before and x.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
new.select_set(True)
bpy.context.view_layer.objects.active = new
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
new.data.transform(new.matrix_world)
new.matrix_world = Matrix.Identity(4)
for x in [x for x in bpy.data.objects if x not in before and x != new]:
    bpy.data.objects.remove(x, do_unlink=True)
new.name = NAME
P = np.array([tuple(v.co) for v in new.data.vertices])
D0 = ends(body_points())
N0 = ends(P)
# The game's animations carry the skeleton's own bone lengths, so the mesh must take the skeleton's
# proportions, not the other way round. A generated figure is usually stockier (lower shoulders, bigger head).
# The fit is done in sections:
#   soles -> shoulders: stretched in height to the skeleton's shoulder joints (the new mesh is in a T-pose, so
#                       its hands are at shoulder height);
#   widths and depths : one scale, between the height stretch and a plain whole-height fit;
#   above the shoulders (neck, head, hat): that same scale in every direction, so the head is not distorted;
#   arms              : stretched along their length to the skeleton's arm length.
bone_w = lambda b: arm.matrix_world @ b.head_local
sh = [b for b in arm.data.bones if b.name.lower().endswith(" upperarm")]
shoulder_z = float(np.mean([bone_w(b).z for b in sh]))
shoulder_x = float(np.mean([abs(bone_w(b).x - D0["cx"]) for b in sh]))
n_arm_z = (N0["handL"][2] + N0["handR"][2]) / 2
s_z = (shoulder_z - D0["sole"]) / (n_arm_z - N0["sole"])
s_h = (body_points()[:, 2].max() - D0["sole"]) / (P[:, 2].max() - N0["sole"])
s = math.sqrt(s_z * s_h)
Q = np.empty_like(P)
Q[:, 0] = D0["cx"] + (P[:, 0] - N0["cx"]) * s
Q[:, 1] = D0["cy"] + (P[:, 1] - N0["cy"]) * s
low_part = P[:, 2] <= n_arm_z
Q[:, 2] = np.where(low_part, D0["sole"] + (P[:, 2] - N0["sole"]) * s_z, shoulder_z + (P[:, 2] - n_arm_z) * s)
# arm length: old = shoulder joint to the hand end (whatever the rest pose), new = shoulder line to the hand end
old_len = float(np.mean([np.linalg.norm(D0["hand" + sd] - np.array(bone_w(arm.data.bones[bn(f" {sd} UpperArm")]))) for sd in "LR"]))
dx = Q[:, 0] - D0["cx"]
new_len = float(np.mean([abs(Q[np.sign(dx) == sg][np.abs(dx[np.sign(dx) == sg]) > 0.86 * np.abs(dx[np.sign(dx) == sg]).max(), 0].mean() - D0["cx"]) for sg in (1, -1)])) - shoulder_x
k = old_len / new_len
out_x = np.abs(dx) > shoulder_x
Q[out_x, 0] = D0["cx"] + np.sign(dx[out_x]) * (shoulder_x + (np.abs(dx[out_x]) - shoulder_x) * k)
# Slim the trunk to the skeleton's own body. The game's poses put the hands where the ORIGINAL character's hips
# and thighs leave room; a generated outfit with a puffy skirt or coat is much wider there and swallows the
# hands and forearms. Between the knees and the armpits, each height is narrowed (width and depth separately)
# to at most SLIM x the original body's size there; arms are left alone.
if SLIM:
    OB = body_points()
    og = [g.name.lower() for g in body.vertex_groups]
    arm_ix = {i for i, n in enumerate(og) if any(k in n for k in ("upperarm", "forearm", "hand", "finger", "clavicle"))}
    not_arm = np.array([sum(g.weight for g in v.groups if g.group in arm_ix) < 0.5 for v in body.data.vertices])
    OB = OB[not_arm]
    knee_z = float(bone_w(arm.data.bones[bn(" L Calf")]).z)
    zs = np.linspace(knee_z, shoulder_z - 0.06 * (shoulder_z - D0["sole"]), 40)
    band = (zs[1] - zs[0]) * 0.6
    trunk = np.abs(Q[:, 0] - D0["cx"]) < shoulder_x * 1.6          # the T-pose arms are further out than this
    fx, fy = np.ones(len(zs)), np.ones(len(zs))
    for i, z in enumerate(zs):
        a_ = OB[np.abs(OB[:, 2] - z) < band]
        b_ = Q[trunk & (np.abs(Q[:, 2] - z) < band)]
        if len(a_) > 5 and len(b_) > 5:
            fx[i] = min(1.0, SLIM * np.abs(a_[:, 0] - D0["cx"]).max() / np.abs(b_[:, 0] - D0["cx"]).max())
            fy[i] = min(1.0, SLIM * (a_[:, 1].max() - a_[:, 1].min()) / (b_[:, 1].max() - b_[:, 1].min()))
    for f in (fx, fy):
        f[0] = f[-1] = 1.0                                         # fade in and out, no steps
        for _ in range(4):
            f[1:-1] = (f[:-2] + 2 * f[1:-1] + f[2:]) / 4
    sel = trunk & (Q[:, 2] > zs[0]) & (Q[:, 2] < zs[-1])
    cyq = float(np.median(Q[trunk, 1]))
    Q[sel, 0] = D0["cx"] + (Q[sel, 0] - D0["cx"]) * np.interp(Q[sel, 2], zs, fx)
    Q[sel, 1] = cyq + (Q[sel, 1] - cyq) * np.interp(Q[sel, 2], zs, fy)
    print(f"RIG slim: narrowest width factor {fx.min():.2f}, depth factor {fy.min():.2f}")
for v, q in zip(new.data.vertices, Q):
    v.co = q
P = Q
N = ends(P)
print(f"RIG fit: height x{s_z:.1f} below the shoulders, x{s:.1f} elsewhere (plain whole-height fit would be x{s_h:.1f}); "
      f"arms x{k:.2f} in length; height old {body_points()[:, 2].max() - D0['sole']:.0f} new {P[:, 2].max() - N['sole']:.0f}")

# ---- 2. pose the old skeleton onto the new mesh ------------------------------------------------
pb = arm.pose.bones


for it in range(3):                                  # a few rounds: the ends are measured on the deformed body
    D = ends(body_points())
    for side in "LR":
        swing(bn(f" {side} UpperArm"), bn(f" {side} Hand"), N["hand" + side] - D["hand" + side])
        swing(bn(f" {side} Thigh"), bn(f" {side} Foot"), (N["foot" + side] - D["foot" + side]) * np.array((1, 1, 0)))
D = ends(body_points())
print("RIG pose match, remaining offsets: " + ", ".join(
    f"{k} {np.linalg.norm(N[k] - D[k]):.1f}" for k in ("handL", "handR", "footL", "footR")))

# ---- 3. weights from the nearest point of the posed old body -----------------------------------
ev = body.evaluated_get(dg())
em = ev.data
em.calc_loop_triangles()
EV = np.array([tuple(ev.matrix_world @ v.co) for v in em.vertices])
tris = [tuple(t.vertices) for t in em.loop_triangles]
bvh = BVHTree.FromPolygons([tuple(p) for p in EV], tris)
groups = [g.name for g in body.vertex_groups]
W0 = np.zeros((len(body.data.vertices), len(groups)), np.float32)
for v in body.data.vertices:
    for g in v.groups:
        W0[v.index, g.group] = g.weight
W = np.zeros((len(P), len(groups)), np.float32)
dist = np.zeros(len(P))
for i, p in enumerate(P):
    loc, _, fi, _ = bvh.find_nearest(Vector(p))
    ia, ib, ic = tris[fi]
    pa, pb_, pc = EV[ia], EV[ib], EV[ic]
    v0, v1, v2 = pb_ - pa, pc - pa, np.array(loc) - pa
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    bv = (d11 * d20 - d01 * d21) / den if abs(den) > 1e-12 else 0.0
    bw = (d00 * d21 - d01 * d20) / den if abs(den) > 1e-12 else 0.0
    W[i] = W0[ia] * (1 - bv - bw) + W0[ib] * bv + W0[ic] * bw
    dist[i] = float(np.linalg.norm(np.array(loc) - p))
# Hanging cloth (skirt, tabard, coat tails): it is far from the skin and the nearest skin is one thigh or the
# other, so a stride would tear it down the middle. Between hip and knee, the further a vertex hangs off the
# body the more it follows the pelvis instead.
if bn(" Pelvis") in groups:
    gp = groups.index(bn(" Pelvis"))
    hip_z, knee_z = pb[bn(" Spine")].head.z, pb[bn(" L Calf")].head.z
    Hb = EV[:, 2].max() - EV[:, 2].min()
    for i in np.where((P[:, 2] < hip_z + 0.03 * Hb) & (P[:, 2] > knee_z - 0.06 * Hb))[0]:
        f = float(np.clip((dist[i] - 0.012 * Hb) / (0.045 * Hb), 0, CLOTH))
        if f > 0:
            W[i] *= 1 - f
            W[i, gp] += f
# The mesh file splits a vertex wherever UV islands meet. Copies of one point must get identical weights, or
# the skin tears along every UV seam as soon as a bone moves: weights are averaged and smoothed per POINT.
_, pid = np.unique(np.round(P / (1e-4 * (P.max() - P.min()))).astype(np.int64), axis=0, return_inverse=True)
pid = pid.ravel()
npnt = int(pid.max()) + 1
cnt = np.bincount(pid, minlength=npnt)[:, None]
Wp = np.zeros((npnt, W.shape[1]), np.float32)
np.add.at(Wp, pid, W)
Wp /= cnt
nbp = [set() for _ in range(npnt)]
for e in new.data.edges:
    x, y = pid[e.vertices[0]], pid[e.vertices[1]]
    if x != y:
        nbp[x].add(int(y))
        nbp[y].add(int(x))
nbp = [list(x) for x in nbp]
for _ in range(SMOOTH):
    Wp = np.array([(Wp[i] + Wp[nbp[i]].mean(0)) / 2 if nbp[i] else Wp[i] for i in range(npnt)])
W = Wp[pid]
print(f"RIG {len(P)} vertices are {npnt} points")
keep = np.argsort(-W, 1)[:, :4]
W4 = np.zeros_like(W)
np.put_along_axis(W4, keep, np.take_along_axis(W, keep, 1), 1)
W4[W4 < 0.02] = 0
W = W4 / np.maximum(W4.sum(1, keepdims=True), 1e-9)

# ---- 4. un-pose --------------------------------------------------------------------------------
bones = {b.name: b for b in arm.data.bones}
M = np.zeros((len(groups), 4, 4))
for gi, g in enumerate(groups):
    M[gi] = np.array(pb[g].matrix @ bones[g].matrix_local.inverted()) if g in bones else np.eye(4)
Ph = np.concatenate([P, np.ones((len(P), 1))], 1)
rest = np.empty_like(P)
for i in range(len(P)):
    Mi = np.tensordot(W[i], M, axes=1)
    rest[i] = (np.linalg.inv(Mi) @ Ph[i])[:3]
for v, r in zip(new.data.vertices, rest):
    v.co = r
for g in groups:
    new.vertex_groups.new(name=g)
for i in range(len(P)):
    for gi in np.nonzero(W[i])[0]:
        new.vertex_groups[int(gi)].add([i], float(W[i, gi]), "REPLACE")
used = int((W.sum(0) > 0).sum())
bpy.data.objects.remove(body, do_unlink=True)
new.parent = arm
md = new.modifiers.new("Armature", "ARMATURE")
md.object = arm
bpy.context.view_layer.update()
evn = new.evaluated_get(dg())
err = np.linalg.norm(np.array([tuple(v.co) for v in evn.data.vertices]) - P, axis=1).max()
print(f"RIG {len(P)} vertices on {used} bones; in the matched pose the mesh is back within {err:.3f} units of the original")
for b in pb:                                         # back to the rest pose
    b.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")

# ---- test renders ------------------------------------------------------------------------------
if TEST:
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 12
    sc.cycles.max_bounces = 1
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.52, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(55), 0, math.radians(30))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_end = 5000
    H = float(P[:, 2].max() - P[:, 2].min())
    cam.data.ortho_scale = H * 1.25
    sc.render.resolution_x = sc.render.resolution_y = 800
    cz = float(P[:, 2].min()) + H / 2

    def shots(tag):
        tiles = []
        for ang in (0, 60, 180):
            r = math.radians(ang)
            cam.location = (H * 4 * math.sin(r), -H * 4 * math.cos(r), cz)
            cam.rotation_euler = (math.radians(90), 0, r)
            sc.render.filepath = f"{out}_{tag}_{ang}.png"
            bpy.ops.render.render(write_still=True)
            tiles.append(np.array(bpy.data.images.load(sc.render.filepath).pixels[:]).reshape(800, 800, 4))
            os.remove(sc.render.filepath)
        img = bpy.data.images.new(tag, 2400, 800)
        img.pixels = np.concatenate(tiles, 1).ravel()
        img.filepath_raw = f"{out}_{tag}.png"
        img.file_format = "PNG"
        img.save()

    shots("rest")

    def turn(name, axis, deg):                       # rotate a bone about a world axis through its head
        h = pb[name].head.copy()
        pb[name].matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ pb[name].matrix
        bpy.context.view_layer.update()

    turn(bn(" L UpperArm"), "Y", 65)                 # arms down
    turn(bn(" R UpperArm"), "Y", -65)
    turn(bn(" L Forearm"), "X", -40)                 # elbow bent forward
    turn(bn(" L Thigh"), "X", 35)                    # a stride
    turn(bn(" L Calf"), "X", -45)
    turn(bn(" R Thigh"), "X", -25)
    turn(bn(" Head"), "Z", 30)                       # look to one side
    shots("pose")
print("RIGGED", out + ".blend")
