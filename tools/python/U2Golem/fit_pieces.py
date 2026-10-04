"""Fit AI-generated armour pieces (Hunyuan3D .glb, any scale) onto a rigged body as wearable parts.

Run:  blender -b <body.blend> --python fit_pieces.py -- <out.blend> <pieces.json>

pieces.json: {"pieces": [{"glb": "...", "name": "vest", "slot": "torso"|"cuirass"|"skirt"|"boot",
               "rot_z": 0, "inflate": 1.1, "faces": 3000, "color": [r,g,b], "metal": 0.0}, ...],
              "hide_body": true}
Each piece is scaled into a box built from the skeleton (neck, shoulders, pelvis, knees, feet) and
the body's own width/depth there; "boot" is placed on both feet (mirrored). Then:
  - vertices inside the body are pushed out to the skin plus a margin (no clipping at rest),
  - weights are copied from the nearest body surface (so the piece moves with what it covers),
  - the piece is decimated to "faces",
  - with hide_body, body faces fully covered by a piece are deleted (armour replaces, not stacks).
"""
import json, math, os, sys
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
cfg = json.load(open(args[1]))
base = os.path.dirname(os.path.abspath(args[1]))

arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
body = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm][0]
B = {b.name.lower(): b for b in arm.data.bones}


def bone(*keys):
    for b in arm.data.bones:
        n = b.name.lower()
        if all(k in n for k in keys):
            return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
    raise KeyError(keys)


neck = bone("neck")[0]
pelvis = bone("pelvis")[0]
clav_l = bone("l clavicle")[1]
thigh_l = bone("l thigh")
calf_l = bone("l calf")
foot_l = bone("l foot")
toe_l = bone("l toe0nub")[0] if any("toe0nub" in b.name.lower() for b in arm.data.bones) else bone("l toe")[1]

BP = [body.matrix_world @ v.co for v in body.data.vertices]


def body_extent(zlo, zhi, xmax):
    pts = [p for p in BP if zlo <= p.z <= zhi and abs(p.x) <= xmax]
    return (min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts))


def boxes(slot, inflate):
    """target (lo, hi) boxes for a slot; boot gives two (left, right)"""
    if slot in ("torso", "cuirass"):
        x0, x1, y0, y1 = body_extent(pelvis.z + 4, neck.z - 2, clav_l.x * 0.95)
        zlo = pelvis.z - 3 if slot == "torso" else pelvis.z + 6
        ztop = neck.z + 3
        half = clav_l.x * (1.05 if slot == "torso" else 1.3)
        cy, dy = (y0 + y1) / 2, (y1 - y0) / 2 * inflate
        return [(Vector((-half, cy - dy, zlo)), Vector((half, cy + dy, ztop)))]
    if slot == "skirt":
        x0, x1, y0, y1 = body_extent(thigh_l[0].z - 12, pelvis.z + 6, 999)
        cy, dy = (y0 + y1) / 2, (y1 - y0) / 2 * inflate * 1.15
        half = max(-x0, x1) * inflate * 1.1
        return [(Vector((-half, cy - dy, (thigh_l[0].z + thigh_l[1].z) / 2 - 6)), Vector((half, cy + dy, pelvis.z + 8)))]
    if slot == "boot":
        res = []
        for s in (1, -1):
            sole = min(p.z for p in BP if p.x * s > 0)
            top = calf_l[0].z - 4
            pts = [p for p in BP if p.x * s > 0 and p.z < top]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]
            cx, hx = (min(xs) + max(xs)) / 2, (max(xs) - min(xs)) / 2 * inflate
            y0, y1 = min(ys) - 0.8, max(ys) + 1.0
            res.append((Vector((cx - hx, y0, sole - 0.6)), Vector((cx + hx, y1, top))))
        return res
    raise ValueError(slot)


bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
# meshes imported from ActorX often have inward normals: probe from far outside to get the sign
_far = Vector((0, min(p.y for p in BP) - 100, (min(p.z for p in BP) + max(p.z for p in BP)) / 2))
_l, _n, _, _ = bvh.find_nearest(_far)
NSIGN = 1.0 if (_far - _l).dot(_n) > 0 else -1.0
print("BODY normals", "outward" if NSIGN > 0 else "inward (corrected)")


def load_piece(path, rot_z):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.parent = None
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    for e in new:
        if e != o:
            bpy.data.objects.remove(e, do_unlink=True)
    if rot_z:
        o.data.transform(Matrix.Rotation(math.radians(rot_z), 4, "Z"))
    o.data.materials.clear()
    return o


def fit_box(o, lo, hi, mirror=False):
    P = [v.co for v in o.data.vertices]
    a = Vector([min(p[k] for p in P) for k in range(3)])
    b = Vector([max(p[k] for p in P) for k in range(3)])
    for v in o.data.vertices:
        t = Vector([(v.co[k] - a[k]) / max(b[k] - a[k], 1e-6) for k in range(3)])
        if mirror:
            t.x = 1 - t.x
        v.co = Vector([lo[k] + t[k] * (hi[k] - lo[k]) for k in range(3)])
    if mirror:
        o.data.flip_normals()


def enclose(o, max_inside=0.04, step=1.04, limit=1.8):
    """grow the piece horizontally about its own centre until it wraps the body (few vertices inside)"""
    def frac():
        n = 0
        for v in o.data.vertices:
            loc, nn, _, d = bvh.find_nearest(v.co)
            if loc is not None and (v.co - loc).dot(nn) * NSIGN < 0:
                n += 1
        return n / max(len(o.data.vertices), 1)
    P = [v.co for v in o.data.vertices]
    c = Vector(((min(p.x for p in P) + max(p.x for p in P)) / 2, (min(p.y for p in P) + max(p.y for p in P)) / 2, 0))
    total = 1.0
    f = frac()
    while f > max_inside and total < limit:
        for v in o.data.vertices:
            v.co.x = c.x + (v.co.x - c.x) * step
            v.co.y = c.y + (v.co.y - c.y) * step
        total *= step
        f = frac()
    return round(total, 2), round(f, 3)


def region(slot, side):
    """which body points a slot wraps (arms are excluded in T-pose)"""
    if slot == "torso":
        return lambda p: abs(p.x) < clav_l.x * 0.85
    if slot == "cuirass":
        return lambda p: abs(p.x) < clav_l.x * 1.1
    if slot == "skirt":
        return lambda p: True
    return lambda p: p.x * side > 0


def slice_fit(o, inside, pad_abs, pad_rel, step=2.0):
    """map each horizontal slice of the piece onto the body's cross-section there (plus padding),
    so the piece takes the body's shape instead of its bounding box"""
    V = o.data.vertices
    z0 = min(v.co.z for v in V); z1 = max(v.co.z for v in V)
    nb = max(int((z1 - z0) / step) + 1, 2)
    rows = []
    for i in range(nb):
        a, b = z0 + i * step - step, z0 + (i + 1) * step + step
        pv = [v.co for v in V if a <= v.co.z <= b]
        bv = [p for p in BP if a <= p.z <= b and inside(p)]
        if len(pv) < 3 or len(bv) < 3:
            rows.append(None)
            continue
        rows.append([min(p.x for p in pv), max(p.x for p in pv), min(p.y for p in pv), max(p.y for p in pv),
                     min(p.x for p in bv), max(p.x for p in bv), min(p.y for p in bv), max(p.y for p in bv)])
    # fill gaps from neighbours, then smooth along z
    for i in range(nb):
        if rows[i] is None:
            near = [rows[j] for j in sorted(range(nb), key=lambda j: abs(j - i)) if rows[j] is not None]
            rows[i] = list(near[0]) if near else None
    if any(r is None for r in rows):
        return False
    # the piece's own extents are smoothed much more than the body's: ridges and lames are local
    # bumps on the piece's outline and must survive the remap, not be flattened slice by slice
    for it in range(12):
        rows = [[(rows[max(i - 1, 0)][k] + 2 * rows[i][k] + rows[min(i + 1, nb - 1)][k]) / 4
                 if (k < 4 or it < 3) else rows[i][k] for k in range(8)] for i in range(nb)]
    for v in V:
        f = (v.co.z - z0) / step
        i = min(int(f), nb - 2); t = min(max(f - i, 0), 1)
        r = [rows[i][k] * (1 - t) + rows[i + 1][k] * t for k in range(8)]
        px0, px1, py0, py1, bx0, bx1, by0, by1 = r
        cx, hx = (bx0 + bx1) / 2, (bx1 - bx0) / 2 * (1 + pad_rel) + pad_abs
        cy, hy = (by0 + by1) / 2, (by1 - by0) / 2 * (1 + pad_rel) + pad_abs
        u = (v.co.x - px0) / max(px1 - px0, 1e-3) * 2 - 1
        w = (v.co.y - py0) / max(py1 - py0, 1e-3) * 2 - 1
        v.co.x = cx + u * hx
        v.co.y = cy + w * hy
    return True


def decimate(o, faces):
    if len(o.data.polygons) > faces:
        m = o.modifiers.new("dec", "DECIMATE")
        m.ratio = faces / len(o.data.polygons)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)


def push_out(o, margin, cut=0.3):
    """delete the parts of the piece that sit inside the body (the inner shell of a solid AI mesh),
    push the parts just above the skin out to the margin"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    inside, moved = [], 0
    for v in bm.verts:
        loc, n, _, d = bvh.find_nearest(v.co)
        if loc is None:
            continue
        n = n * NSIGN
        s = (v.co - loc).dot(n)
        if s < -cut:
            inside.append(v)
        elif s < margin:
            v.co = loc + n * margin
            moved += 1
    bmesh.ops.delete(bm, geom=inside, context="VERTS")
    # drop tiny islands left behind
    seen, small = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        isl, stack = [], [f]
        seen.add(f.index)
        while stack:
            g = stack.pop(); isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); stack.append(h)
        if len(isl) < 40:
            small += isl
    bmesh.ops.delete(bm, geom=list(set(small)), context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data); bm.free()
    return moved, len(inside)


def copy_weights(o):
    for g in body.vertex_groups:
        o.vertex_groups.new(name=g.name)
    m = o.modifiers.new("wt", "DATA_TRANSFER")
    m.object = body
    m.use_vert_data = True
    m.data_types_verts = {"VGROUP_WEIGHTS"}
    m.vert_mapping = "POLYINTERP_NEAREST"
    m.layers_vgroup_select_src = "ALL"
    m.layers_vgroup_select_dst = "NAME"
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    # drop empty groups
    used = set(g.group for v in o.data.vertices for g in v.groups if g.weight > 0.001)
    for g in list(o.vertex_groups):
        if g.index not in used:
            o.vertex_groups.remove(g)


def material(name, color, metal):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = 0.35 if metal > 0.5 else 0.7
    m.diffuse_color = (*color, 1)
    return m


pieces = []
for spec in cfg["pieces"]:
    glb = spec["glb"] if os.path.isabs(spec["glb"]) else os.path.join(base, spec["glb"])
    tgt = boxes(spec["slot"], spec.get("inflate", 1.1))
    mat = material(spec["name"], spec.get("color", (0.5, 0.5, 0.5)), spec.get("metal", 0.0))
    for i, (lo, hi) in enumerate(tgt):
        o = load_piece(glb, spec.get("rot_z", 0))
        o.name = spec["name"] + ("_L" if len(tgt) > 1 and i == 0 else "_R" if len(tgt) > 1 else "")
        decimate(o, spec.get("faces", 3000))
        fit_box(o, lo, hi, mirror=(i == 1 and spec.get("mirror", True)))
        slice_fit(o, region(spec["slot"], 1 if i == 0 else -1), spec.get("pad", 1.5), spec.get("pad_rel", 0.06))
        g = enclose(o, spec.get("max_inside", 0.04), limit=spec.get("grow_limit", 1.15))
        n = push_out(o, spec.get("margin", 0.8))
        n = (*n, "grow", *g)
        o.data.materials.append(mat)
        for f in o.data.polygons:
            f.use_smooth = True
        copy_weights(o)
        o.parent = arm
        o.modifiers.new("Armature", "ARMATURE").object = arm
        pieces.append(o)
        print("PIECE", o.name, len(o.data.polygons), "faces, pushed/cut", n, "verts, box", tuple(round(x, 1) for x in lo), tuple(round(x, 1) for x in hi))

if cfg.get("hide_body", True):
    # a body face is hidden when a ray outward from each of its corners hits a piece within reach
    pv = []
    for o in pieces:
        bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
        pv.append(BVHTree.FromBMesh(bm)); bm.free()
    reach = cfg.get("hide_reach", 6.0)
    me = body.data
    covered = []
    for v in me.vertices:
        p = body.matrix_world @ v.co
        n = (body.matrix_world.to_3x3() @ v.normal).normalized() * NSIGN
        covered.append(any(t.ray_cast(p + n * 0.05, n, reach)[0] is not None for t in pv))
    bm = bmesh.new(); bm.from_mesh(me)
    kill = [f for f in bm.faces if all(covered[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me); bm.free()
    print("HIDDEN body faces", len(kill), "loose verts removed", len(loose))

bpy.ops.wm.save_as_mainfile(filepath=out)
print("FIT_PIECES", out, sum(len(o.data.polygons) for o in pieces), "piece faces,", len(body.data.polygons), "body faces")
