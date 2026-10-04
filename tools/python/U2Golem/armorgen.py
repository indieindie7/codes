"""Generate armour plates for a rigged character in Blender, from a spec of plate outlines.

Run:  blender -b <character.blend> --python armorgen.py -- <spec.json> <out.blend> [texture dir]

Every plate is built the same way, so a whole suit speaks one design language:
  1. its outline is given in a bone's cylindrical space: rows of (t along the bone, left angle,
     right angle) - angle 0 = the character's front, +90 = his left; a row with left == right
     makes a point;
  2. each grid point is projected onto the body from outside (outermost surface), then pushed
     out by "gap" - the plate hugs the body;
  3. it gets thickness (solidify) and a small bevel; the rim takes the trim colour;
  4. it is rigid on its bone, or blended ("weights": {bone: w}) - e.g. hip tassets 0.3 pelvis /
     0.7 thigh, so they follow the leg like real tassets;
  5. UVs span the plate, and every plate uses one generated texture (plate.tga): palette metal
     with a trim band and rivets along the edge (cloth plates use the cloth half).
Spec: {"palette": {"plate": [r,g,b], "trim": [..], "cloth": [..], "cloth_trim": [..]},
       "plates": [{"name", "bone", "rows": [[t, left, right], ...], "gap", "thickness",
                   "material": "plate"|"cloth", "weights": {...}, "mirror": true}, ...]}
"mirror": true also builds the mirror image on the other side (L <-> R bone, angles negated).
"""
import json, math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
spec = json.load(open(args[0]))
out_blend = os.path.abspath(args[1])
texdir = args[2] if len(args) > 2 else os.path.dirname(out_blend)

arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
body = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm][0]
pal = spec["palette"]


# ---- the shared plate texture: top half metal plate, bottom half cloth ------------------------
def make_texture(path, size=256):
    rng = np.random.default_rng(7)
    img = np.zeros((size, size, 3), np.float32)
    half = size // 2
    for y0, base, trim in ((0, pal["plate"], pal["trim"]), (half, pal["cloth"], pal["cloth_trim"])):
        yy, xx = np.mgrid[0:half, 0:size]
        u, v = xx / size, yy / half
        # brushed base, a little darker toward the edges
        grain = 0.92 + 0.08 * rng.random((half, size)).cumsum(1) % 1.0 * 0 + 0.06 * np.sin(yy * 0.9 + rng.random((half, 1)) * 6)
        edge = np.minimum.reduce([u, 1 - u, v, 1 - v])
        shade = 0.85 + 0.15 * np.clip(edge * 8, 0, 1)
        col = np.array(base)[None, None, :] * (grain * shade)[..., None]
        band = (edge > 0.045) & (edge < 0.10)            # trim band inside the edge
        groove = (edge >= 0.10) & (edge < 0.115)          # dark groove inside the trim
        col[band] = np.array(trim) * (0.9 + 0.2 * rng.random((band.sum(), 1)))
        col[groove] *= 0.45
        # rivets along the trim, every 1/8
        for i in range(1, 8):
            for (cu, cv) in ((i / 8, 0.072), (i / 8, 1 - 0.072), (0.072, i / 8), (1 - 0.072, i / 8)):
                d = np.hypot((u - cu) * 1.0, (v - cv) * 2.0)
                r = d < 0.018
                col[r] = np.array(trim) * 1.35
                col[(d >= 0.018) & (d < 0.024)] *= 0.6
        img[y0:y0 + half] = col
    im = bpy.data.images.new("plate_gen", size, size, alpha=False)
    rgba = np.ones((size, size, 4), np.float32)
    rgba[..., :3] = np.clip(img[::-1], 0, 1)        # Blender images start at the bottom row
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    im.file_format = "TARGA_RAW"
    im.save()
    return path


tex_path = make_texture(os.path.join(texdir, "plate.tga"))
mat = bpy.data.materials.new("ArmourPlate")
mat.use_nodes = True
tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
tn.image = bpy.data.images.load(tex_path)
bsdf = mat.node_tree.nodes["Principled BSDF"]
mat.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Metallic"].default_value = 0.6
bsdf.inputs["Roughness"].default_value = 0.35
mat["source_texture"] = tex_path

# ---- the body surface to project onto (rest pose) ---------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = BVHTree.FromBMesh(bm_body)


def bone_frame(name):
    b = arm.data.bones[name]
    head = arm.matrix_world @ b.head_local
    tail = arm.matrix_world @ b.tail_local
    a = (tail - head)
    length = a.length
    a.normalize()
    front = Vector((0, -1, 0))                       # the character faces -Y
    if abs(a.dot(front)) > 0.9:
        front = Vector((0, 0, 1))
    f = (front - a * a.dot(front)).normalized()
    left = a.cross(f) if a.z < 0 else f.cross(a)     # +X is his left, for up- and down-bones alike
    if left.x < 0:
        left = -left
    return head, a, length, f, left


def project(head, a, length, f, left, t, ang, gap):
    p = head + a * (t * length)
    d = (f * math.cos(math.radians(ang)) + left * math.sin(math.radians(ang))).normalized()
    far = p + d * 200
    hit = bvh.ray_cast(far, -d, 400)
    if hit[0] is None:
        return p + d * 12
    return hit[0] + d * gap


def build_plate(pl):
    head, a, length, f, left = bone_frame(pl["bone"])
    rows = pl["rows"]
    nu = pl.get("cols", 8)
    nv_per = pl.get("subdiv", 3)
    # densify rows
    R = []
    for i in range(len(rows) - 1):
        for k in range(nv_per):
            s = k / nv_per
            R.append([rows[i][j] * (1 - s) + rows[i + 1][j] * s for j in range(3)])
    R.append(rows[-1])
    gap = pl.get("gap", 1.2)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    grid = []
    for (t, l, r) in R:
        grid.append([bm.verts.new(project(head, a, length, f, left, t, l + (r - l) * u / nu, gap)) for u in range(nu + 1)])
    vhalf = 0.0 if pl.get("material", "plate") == "plate" else 0.5
    for j in range(len(R) - 1):
        for i in range(nu):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            if len(set(q)) < 4:
                continue
            try:
                face = bm.faces.new(q)
            except ValueError:
                continue
            for loop, (uu, vv) in zip(face.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv_layer].uv = (uu / nu, 1 - (vhalf + 0.5 * vv / (len(R) - 1)))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05)
    bm.normal_update()
    # outward normals: away from the bone axis
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    axis_pt = head + a * (a.dot(c - head))
    if sum(fc.normal.dot(fc.calc_center_median() - axis_pt) for fc in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(pl["name"])
    bm.to_mesh(me)
    obj = bpy.data.objects.new(pl["name"], me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(mat)
    for v in me.vertices:
        pass
    weights = pl.get("weights", {pl["bone"]: 1.0})
    for bone, w in weights.items():
        g = obj.vertex_groups.new(name=bone)
        g.add(list(range(len(me.vertices))), w, "REPLACE")
    sol = obj.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = pl.get("thickness", 1.5)
    sol.offset = 1.0
    sol.use_rim = True
    bev = obj.modifiers.new("bevel", "BEVEL")
    bev.width = pl.get("bevel", 0.35)
    bev.segments = 1
    bev.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    obj.parent = arm
    obj.modifiers.new("Armature", "ARMATURE").object = arm
    return obj


def mirrored(pl):
    m = json.loads(json.dumps(pl))
    swap = lambda n: n.replace(" L ", " #").replace(" R ", " L ").replace(" #", " R ")
    m["name"] = pl["name"] + "_mirror"
    m["bone"] = swap(pl["bone"])
    m["rows"] = [[t, -r, -l] for t, l, r in pl["rows"]]
    m["weights"] = {swap(b): w for b, w in pl.get("weights", {pl["bone"]: 1.0}).items()}
    return m


made = []
for pl in spec["plates"]:
    made.append(build_plate(pl))
    if pl.get("mirror"):
        made.append(build_plate(mirrored(pl)))

# one armour object
bpy.ops.object.select_all(action="DESELECT")
for o in made:
    o.select_set(True)
bpy.context.view_layer.objects.active = made[0]
bpy.ops.object.join()
made[0].name = "GeneratedArmour"
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("ARMORGEN", len(spec["plates"]), "plate specs ->", len(made[0].data.polygons), "faces ->", out_blend)
