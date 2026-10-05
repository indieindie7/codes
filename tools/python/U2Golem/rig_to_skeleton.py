"""Rig a generated T-pose game mesh onto an existing character's skeleton, by borrowing that character's weights.

Run:  blender -b <rigged_character.blend> --python rig_to_skeleton.py -- <out.blend> low=<mesh.glb>
      [test=1] [smooth=4] [cloth=0.85] [name=Body]
<rigged_character.blend>: an armature with its skinned body (gem2blend.py output, e.g. dalton\\PlayerGame.blend).
low: the new mesh (retopo_bake.py output), standing upright, facing -Y, arms out to the sides.

1. Fit: the new mesh is scaled so its arms are as high above its soles as the old body's, and centred on it.
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
arm_h = lambda e: (e["handL"][2] + e["handR"][2]) / 2 - e["sole"]
s = arm_h(D0) / arm_h(N0)
T = Matrix.Translation((D0["cx"], D0["cy"], D0["sole"])) @ Matrix.Scale(s, 4) @ Matrix.Translation(
    (-N0["cx"], -N0["cy"], -N0["sole"]))
new.data.transform(T)
P = np.array([tuple(v.co) for v in new.data.vertices])
N = ends(P)
print(f"RIG scale {s:.2f}; arm span old {D0['handL'][0] - D0['handR'][0]:.1f} new {N['handL'][0] - N['handR'][0]:.1f}; "
      f"height old {body_points()[:, 2].max() - D0['sole']:.1f} new {P[:, 2].max() - N['sole']:.1f}")

# ---- 2. pose the old skeleton onto the new mesh ------------------------------------------------
pb = arm.pose.bones


def swing(root, tip, delta):
    """rotate bone `root` about its head so that bone `tip`'s head moves by about `delta` (armature space)"""
    h = pb[root].head.copy()
    d0 = (pb[tip].head - h)
    d1 = d0 + Vector(delta)
    q = d0.rotation_difference(d1)
    pb[root].matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb[root].matrix
    bpy.context.view_layer.update()


for it in range(3):                                  # a few rounds: the ends are measured on the deformed body
    D = ends(body_points())
    for side in "LR":
        swing(f"Merc {side} UpperArm", f"Merc {side} Hand", N["hand" + side] - D["hand" + side])
        swing(f"Merc {side} Thigh", f"Merc {side} Foot", (N["foot" + side] - D["foot" + side]) * np.array((1, 1, 0)))
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
if "Merc Pelvis" in groups:
    gp = groups.index("Merc Pelvis")
    hip_z, knee_z = pb["Merc Spine"].head.z, pb["Merc L Calf"].head.z
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

    turn("Merc L UpperArm", "Y", 65)                 # arms down
    turn("Merc R UpperArm", "Y", -65)
    turn("Merc L Forearm", "X", -40)                 # elbow bent forward
    turn("Merc L Thigh", "X", 35)                    # a stride
    turn("Merc L Calf", "X", -45)
    turn("Merc R Thigh", "X", -25)
    turn("Merc Head", "Z", 30)                       # look to one side
    shots("pose")
print("RIGGED", out + ".blend")
