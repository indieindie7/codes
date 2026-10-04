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
                   "material": "plate"|"cloth", "weights": {...}, "mirror": true,
                   "ridges": n, "ridge_height": h (raised ribs across the plate),
                   "quilt": [across, down], "quilt_depth": d (padded pillows, stitched in a grid;
                   [0, n] = horizontal rolls, [n, 0] = vertical channels)}, ...]}
Angles: 0 = front; for a vertical (torso) bone +90 = his left; for an arm bone (T-pose) +90 = up,
180 = back; for leg bones +90 = outside of the left leg.
"tubes": [{"name", "points": [[bone, t, angle, out], ...], "radius", "count" (wire bundle),
            "spread", "material": "tube"|"plate"|"cloth", "mirror"}] - hoses/wires through points on
            the body, each vertex following its nearest anchor's bone.
"replace": true (default) - plates hug the body (thickness grows inward, small gap) and the body
faces hidden under them are deleted, so armour replaces skin instead of bulking it out.
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
def make_texture(path, size=256, plate=None, trim_c=None, cloth=None, cloth_trim=None):
    rng = np.random.default_rng(7)
    img = np.zeros((size, size, 3), np.float32)
    half = size // 2
    for y0, base, trim in ((0, plate or pal["plate"], trim_c or pal["trim"]), (half, cloth or pal["cloth"], cloth_trim or pal["cloth_trim"])):
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


tex_path = make_texture(os.path.join(texdir, "plate.tga"), spec.get("texture_size", 512))
# extra named materials: {"name": {"color": [..], "trim": [..], "kind": "plate"|"cloth"}}, each with
# its own generated texture (same layout: plate half on top, cloth half below)
named = {}
mat = bpy.data.materials.new("ArmourPlate")
mat.use_nodes = True
tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
tn.image = bpy.data.images.load(tex_path)
bsdf = mat.node_tree.nodes["Principled BSDF"]
mat.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Metallic"].default_value = 0.6
bsdf.inputs["Roughness"].default_value = 0.35
mat["source_texture"] = tex_path
mat.diffuse_color = tuple(pal["plate"]) + (1,)
cmat = mat.copy()                                  # same texture (its cloth half), own colour
cmat.name = "ArmourCloth"
cmat.diffuse_color = tuple(pal["cloth"]) + (1,)
bsdf_c = cmat.node_tree.nodes["Principled BSDF"]
bsdf_c.inputs["Metallic"].default_value = 0.0
bsdf_c.inputs["Roughness"].default_value = 0.9
for nm, md in spec.get("materials", {}).items():
    col, trim = md["color"], md.get("trim", [c * 0.7 for c in md["color"]])
    tp = make_texture(os.path.join(texdir, f"mat_{nm}.tga"), spec.get("texture_size", 512), col, trim, col, trim)
    m = bpy.data.materials.new(nm)
    m.use_nodes = True
    n = m.node_tree.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(tp)
    b = m.node_tree.nodes["Principled BSDF"]
    m.node_tree.links.new(n.outputs["Color"], b.inputs["Base Color"])
    cloth_kind = md.get("kind", "plate") == "cloth"
    b.inputs["Metallic"].default_value = 0.0 if cloth_kind else 0.5
    b.inputs["Roughness"].default_value = 0.9 if cloth_kind else 0.4
    m.diffuse_color = tuple(col) + (1,)
    m["source_texture"] = tp
    m["kind"] = md.get("kind", "plate")
    named[nm] = m


def material_of(name):
    if name in named:
        return named[name]
    return cmat if name == "cloth" else mat


def kind_of(name):
    return named[name]["kind"] if name in named else ("cloth" if name == "cloth" else "plate")

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


def project(head, a, length, f, left, t, ang, gap, reach):
    """outermost body surface within `reach` of the bone axis in that direction (casting from
    further out would hit other limbs first, e.g. the legs under a T-posed arm)"""
    p = head + a * (t * length)
    d = (f * math.cos(math.radians(ang)) + left * math.sin(math.radians(ang))).normalized()
    hit = bvh.ray_cast(p + d * reach, -d, reach)
    if hit[0] is None:
        return p + d * (reach * 0.5 + gap)
    return hit[0] + d * gap


def build_plate(pl):
    head, a, length, f, left = bone_frame(pl["bone"])
    rows = pl["rows"]
    qu, qv = pl.get("quilt", [0, 0])
    nu = max(pl.get("cols", 8), qu * 4)
    nv_per = pl.get("subdiv", 3) if not pl.get("ridges") else max(pl.get("subdiv", 3), 4 * pl["ridges"] // max(len(pl["rows"]) - 1, 1) + 1)
    # densify rows
    R = []
    for i in range(len(rows) - 1):
        for k in range(nv_per):
            s = k / nv_per
            R.append([rows[i][j] * (1 - s) + rows[i + 1][j] * s for j in range(3)])
    R.append(rows[-1])
    while qv and len(R) < qv * 4 + 1:             # quilting needs a few rows per pillow
        R2 = []
        for i in range(len(R) - 1):
            R2 += [R[i], [(R[i][k] + R[i + 1][k]) / 2 for k in range(3)]]
        R = R2 + [R[-1]]
    gap = pl.get("gap", 0.5 if spec.get("replace", True) else 1.2)
    reach = pl.get("reach", 22.0 if "Thigh" in pl["bone"] or "Calf" in pl["bone"] or "Arm" in pl["bone"] or "Forearm" in pl["bone"] else 40.0)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    grid = []
    ridges, rh = pl.get("ridges", 0), pl.get("ridge_height", 0.7)
    for j, (t, l, r) in enumerate(R):
        v = j / max(len(R) - 1, 1)
        g = gap + (rh * 0.5 * (1 - math.cos(2 * math.pi * ridges * v)) if ridges else 0.0)   # raised ribs across the plate
        qd = pl.get("quilt_depth", 0.9)
        row = []
        for u in range(nu + 1):
            puff = 0.0
            if qu or qv:
                su = abs(math.sin(math.pi * (u / nu) * qu)) if qu else 1.0
                sv = abs(math.sin(math.pi * v * qv)) if qv else 1.0
                puff = qd * (su * sv) ** 0.6         # pillows, pinched at the stitch lines
            row.append(bm.verts.new(project(head, a, length, f, left, t, l + (r - l) * u / nu, g + puff, reach)))
        grid.append(row)
    vhalf = 0.0 if kind_of(pl.get("material", "plate")) == "plate" else 0.5
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
    for fc in bm.faces:
        fc.smooth = True
    me = bpy.data.meshes.new(pl["name"])
    bm.to_mesh(me)
    obj = bpy.data.objects.new(pl["name"], me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(material_of(pl.get("material", "plate")))
    weights = pl.get("weights", {pl["bone"]: 1.0})
    for bone, w in weights.items():
        g = obj.vertex_groups.new(name=bone)
        g.add(list(range(len(me.vertices))), w, "REPLACE")
    sol = obj.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = pl.get("thickness", 1.5)
    sol.offset = -1.0 if spec.get("replace", True) else 1.0
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

# ---- tubes and wires: smooth hoses between points on bones ------------------------------------
def anchor(pt):
    bone, tt, ang, out = pt
    head, a, length, f, left = bone_frame(bone)
    p = project(head, a, length, f, left, tt, ang, out, 30.0)
    return Vector(p), bone


def build_tube(tb, idx):
    pts = [anchor(p) for p in tb["points"]]
    radius = tb.get("radius", 1.0)
    count = tb.get("count", 1)              # a bundle of wires side by side
    spread = tb.get("spread", radius * 2.2)
    objs = []
    for k in range(count):
        cu = bpy.data.curves.new(f"{tb['name']}_{k}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = radius
        cu.bevel_resolution = tb.get("bevel_resolution", 2)
        cu.resolution_u = tb.get("resolution", 6)
        cu.use_fill_caps = True
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        off = Vector((0, 0, (k - (count - 1) / 2) * spread))
        for i, (p, b) in enumerate(pts):
            sp.points[i].co = (*(p + off), 1.0)
        sp.order_u = min(4, len(pts))
        sp.use_endpoint_u = True
        o = bpy.data.objects.new(cu.name, cu)
        bpy.context.scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.convert(target="MESH")
        o = bpy.context.view_layer.objects.active
        o.select_set(False)
        o.data.materials.clear()
        o.data.materials.append(tmat if tb.get("material", "tube") == "tube" else material_of(tb["material"]))
        # each vertex follows the bone of its nearest anchor (blended between two)
        groups = {b: o.vertex_groups.get(b) or o.vertex_groups.new(name=b) for _, b in pts}
        for v in o.data.vertices:
            d = sorted(((v.co - p).length, b) for p, b in pts)
            (d0, b0), (d1, b1) = d[0], d[1] if len(d) > 1 else d[0]
            w0 = d1 / (d0 + d1 + 1e-6)
            groups[b0].add([v.index], w0, "ADD")
            if b1 != b0:
                groups[b1].add([v.index], 1 - w0, "ADD")
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
        objs.append(o)
    return objs


tmat = bpy.data.materials.new("Tube")
tmat.use_nodes = True
tcol = spec.get("palette", {}).get("tube", [0.12, 0.12, 0.12])
tmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*tcol, 1)
tmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
tmat.diffuse_color = (*tcol, 1)
for i, tb in enumerate(spec.get("tubes", [])):
    made += build_tube(tb, i)
    if tb.get("mirror"):
        m = json.loads(json.dumps(tb))
        swap = lambda n: n.replace(" L ", " #").replace(" R ", " L ").replace(" #", " R ")
        m["name"] += "_mirror"
        m["points"] = [[swap(b), tt, -ang, out] for b, tt, ang, out in tb["points"]]
        made += build_tube(m, i)

# ---- replace, don't stack: delete body faces hidden under armour --------------------------------
if spec.get("replace", True):
    dg = bpy.context.evaluated_depsgraph_get()
    plates_bm = bmesh.new()
    for o in made:
        if o.type == "MESH" and not o.name.startswith(tuple(t["name"] for t in spec.get("tubes", []))):
            tmp = o.data.copy()
            tmp.transform(o.matrix_world)
            plates_bm.from_mesh(tmp)
    cover = BVHTree.FromBMesh(plates_bm)
    depth = spec.get("cover_depth", 4.0)
    bmb = bmesh.new()
    bmb.from_mesh(body.data)
    gone = []
    for fc in bmb.faces:
        c = body.matrix_world @ fc.calc_center_median()
        n = (body.matrix_world.to_3x3() @ fc.normal).normalized()
        if all(cover.ray_cast(body.matrix_world @ v.co - n * 0.2, n, depth)[0] is not None for v in fc.verts):
            gone.append(fc)
    bmesh.ops.delete(bmb, geom=gone, context="FACES")
    bmb.to_mesh(body.data)
    body.data.update()
    print("REPLACED", len(gone), "body faces hidden under armour")

# one armour object
bpy.ops.object.select_all(action="DESELECT")
for o in made:
    o.select_set(True)
bpy.context.view_layer.objects.active = made[0]
bpy.ops.object.join()
made[0].name = "GeneratedArmour"
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("ARMORGEN", len(spec["plates"]), "plate specs ->", len(made[0].data.polygons), "faces ->", out_blend)
