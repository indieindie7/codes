"""Blender scene -> ActorX .psk (the way back after editing or generating in Blender).

Run:  blender -b <scene.blend> --python blend2psk.py -- <out.psk> [rename.json] [mesh object names...]

Writes every mesh parented to the armature (or the named ones), triangulated, in world space:
points, wedges (UV per corner), faces with material slots, the armature's bones (world rest
matrices -> parent-relative position + quaternion, child rotations conjugated as ActorX expects,
the convention psk2blend.py / kitbash.py read) and the vertex-group weights (max 4 per point).
rename.json maps Blender bone names to output names (e.g. MPFB "upperarm_l" -> "Bip01 L UpperArm");
bones mapped to "" are dropped and their weights go to the nearest kept parent.
Also writes <out>.json: material slot names and their image files (for kitbash/u2import).
"""
import json, os, struct, sys
import bpy, bmesh

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
rename = json.load(open(args[1])) if len(args) > 1 and args[1].endswith(".json") else {}
names = [a for a in args[1:] if not a.endswith(".json")]

arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and (o.name in names if names else o.parent == arm)]

# ---- bones ----------------------------------------------------------------------------------
bl = list(arm.data.bones)
def out_name(b):
    return rename.get(b.name, b.name) if rename else b.name
keep = [b for b in bl if out_name(b) != ""]
index = {b.name: i for i, b in enumerate(keep)}
def kept(b):
    while b is not None and b.name not in index:
        b = b.parent
    return b
recs = []
for i, b in enumerate(keep):
    p = kept(b.parent)
    M = arm.matrix_world @ b.matrix_local
    if p is None:
        L, parent = M, 0
    else:
        L = (arm.matrix_world @ p.matrix_local).inverted() @ M
        parent = index[p.name]
    q = L.to_quaternion()
    t = L.to_translation()
    if p is not None:
        q = q.conjugated()
    kids = sum(1 for c in keep if kept(c.parent) is b)
    recs.append(struct.pack("<64sIii" + "f" * 11, out_name(b).encode()[:63], 0, kids, parent,
                            q.x, q.y, q.z, q.w, t.x, t.y, t.z, 0.0, 1.0, 1.0, 1.0))

# ---- geometry -------------------------------------------------------------------------------
pts, wedges, faces, weights, mats, texs = [], [], [], [], [], []
mat_index = {}
dg = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)                      # rest shape (no armature deformation)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.transform(o.matrix_world)
    uv = bm.loops.layers.uv.active
    deform = bm.verts.layers.deform.active
    base = len(pts)
    groups = {g.index: g.name for g in o.vertex_groups}
    for v in bm.verts:
        pts.append(tuple(v.co))
        ws = []
        if deform is not None:
            for gi, w in v[deform].items():
                b = arm.data.bones.get(groups.get(gi, ""))
                kb = kept(b) if b else None
                if kb and w > 0.001:
                    ws.append((index[kb.name], w))
        merged = {}
        for bi, w in ws:
            merged[bi] = merged.get(bi, 0) + w
        top = sorted(merged.items(), key=lambda x: -x[1])[:4] or [(0, 1.0)]
        s = sum(w for _, w in top)
        for bi, w in top:
            weights.append((w / s, base + v.index, bi))
    for f in bm.faces:
        slot = o.material_slots[f.material_index].material if o.material_slots else None
        key = slot.name if slot else f"{o.name}_mat"
        if key not in mat_index:
            mat_index[key] = len(mats)
            mats.append(key)
            img = ""
            if slot and slot.use_nodes:
                for n in slot.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image:
                        img = bpy.path.abspath(n.image.filepath)
                        break
            texs.append(slot.get("source_texture", img) if slot else "")
        m = mat_index[key]
        tri = []
        for loop in f.loops:
            u, w = loop[uv].uv if uv else (0.0, 0.0)
            tri.append(len(wedges))
            wedges.append((base + loop.vert.index, u, 1.0 - w, m))
        faces.append((tri[0], tri[2], tri[1], m))   # ActorX winding is clockwise
    bm.free()


def chunk(cid, size, rs):
    return struct.pack("<20siii", cid.encode(), 1999801, size, len(rs)) + b"".join(rs)


big = len(wedges) > 65535
data = [struct.pack("<20siii", b"ACTRHEAD", 1999801, 0, 0)]
data.append(chunk("PNTS0000", 12, [struct.pack("<3f", *p) for p in pts]))
data.append(chunk("VTXW0000", 16, [struct.pack("<IffBBH" if big else "<HHffBBH", *((p, u, v, m, 0, 0) if big else (p, 0, u, v, m, 0, 0))) for p, u, v, m in wedges]))
data.append(chunk("FACE0000", 12, [struct.pack("<HHHBBI", a, b, c, m, 0, 1) for a, b, c, m in faces]))
data.append(chunk("MATT0000", 88, [struct.pack("<64siiiiii", n.encode()[:63], i, 0, 0, 0, 0, 0) for i, n in enumerate(mats)]))
data.append(chunk("REFSKELT", 120, recs))
data.append(chunk("RAWWEIGHTS", 12, [struct.pack("<fii", w, p, b) for w, p, b in weights]))
open(out, "wb").write(b"".join(data))
json.dump(dict(materials=mats, textures=texs), open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print(f"BLEND2PSK {out}: {len(pts)} points, {len(wedges)} wedges, {len(faces)} faces, {len(mats)} materials, {len(recs)} bones, {len(weights)} weights")
