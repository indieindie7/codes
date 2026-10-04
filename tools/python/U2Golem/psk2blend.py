"""ActorX .psk (UT2004 / UC2 / our gem2psk output) -> Blender: armature, weighted mesh, UVs,
textured materials. Blender 5.2 ships no PSK importer, so this is ours.

Run with Blender:  blender -b --python psk2blend.py -- <out.blend> <a.psk>[=tex0,tex1,...] [<b.psk>...]
or import from another script:  import psk2blend; psk2blend.load(path, textures, name)

Several .psk files can go into one scene (each gets its own armature and mesh: handy as donors
for kitbashing). Textures: a list per mesh in material-slot order; if left out, the .tga files
next to the .psk (or in ../PlayerSkins/Texture) named after the mesh are used: <Mesh>Body*.tga
for slot 0, <Mesh>Head*.tga for slot 1.
ActorX stores child bone rotations inverted (conjugated); the root as is.
"""
import glob, os, struct, sys
import bpy
from mathutils import Matrix, Quaternion, Vector


def read_psk(path):
    d = open(path, "rb").read()
    o, ch = 0, {}
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        size, count = struct.unpack_from("<ii", d, o + 24)
        ch[cid] = (d[o + 32:o + 32 + size * count], size, count)
        o += 32 + size * count
    get = lambda cid: ch.get(cid, (b"", 0, 0))
    b, s, n = get("PNTS0000")
    pts = [struct.unpack_from("<3f", b, s * i) for i in range(n)]
    b, s, n = get("VTXW0000")
    wedges = [struct.unpack_from("<HHffB", b, s * i) for i in range(n)]
    b, s, n = get("FACE0000")
    faces = [struct.unpack_from("<HHHB", b, s * i) for i in range(n)]
    b, s, n = get("MATT0000")
    mats = [b[s * i:s * i + 64].split(b"\0")[0].decode("latin1") for i in range(n)]
    b, s, n = get("REFSKELT")
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        flags, kids, parent = struct.unpack_from("<Iii", b, s * i + 64)
        q = struct.unpack_from("<4f", b, s * i + 76)
        pos = struct.unpack_from("<3f", b, s * i + 92)
        bones.append((name, parent if i else -1, pos, q))
    b, s, n = get("RAWWEIGHTS")
    weights = [struct.unpack_from("<fii", b, s * i) for i in range(n)]
    return pts, wedges, faces, mats, bones, weights


def guess_textures(path, nmat):
    name = os.path.splitext(os.path.basename(path))[0]
    dirs = [os.path.dirname(path), os.path.join(os.path.dirname(path), "..", "..", "PlayerSkins", "Texture"),
            os.path.join(os.path.dirname(path), "..", "Texture")]
    pool = [f for d in dirs for f in glob.glob(os.path.join(d, "*.tga"))]
    out = []
    for i, key in enumerate(["body", "head"][:nmat]):
        hit = sorted(f for f in pool if os.path.basename(f).lower().startswith(name.lower()) and key in os.path.basename(f).lower())
        out.append(os.path.abspath(hit[0]) if hit else None)
    return out


def load(path, textures=None, name=None):
    pts, wedges, faces, mats, bones, weights = read_psk(path)
    name = name or os.path.splitext(os.path.basename(path))[0]
    textures = textures or guess_textures(path, len(mats))

    world = []
    for i, (bname, parent, pos, q) in enumerate(bones):
        quat = Quaternion((q[3], q[0], q[1], q[2]))
        if parent >= 0:
            quat = quat.conjugated()                     # ActorX child rotations are inverted
        local = Matrix.Translation(Vector(pos)) @ quat.to_matrix().to_4x4()
        world.append(local if parent < 0 else world[parent] @ local)
    arm_data = bpy.data.armatures.new(name + "Skeleton")
    arm = bpy.data.objects.new(name + "Skeleton", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = []
    for i, (bname, parent, pos, q) in enumerate(bones):
        b = arm_data.edit_bones.new(bname)
        head = world[i].to_translation()
        kids = [j for j, bb in enumerate(bones) if bb[1] == i]
        tail = world[kids[0]].to_translation() if len(kids) == 1 else None
        if tail is None or (tail - head).length < 0.5:
            tail = head + world[i].to_3x3() @ Vector((2.0, 0, 0))
        b.head, b.tail = head, tail
        if parent >= 0:
            b.parent = eb[parent]
        eb.append(b)
    bpy.ops.object.mode_set(mode="OBJECT")

    me = bpy.data.meshes.new(name)
    me.from_pydata(pts, [], [(wedges[a][0], wedges[b][0], wedges[c][0]) for a, b, c, m in faces])
    uvl = me.uv_layers.new(name="UVMap")
    for poly, (a, b, c, m) in zip(me.polygons, faces):
        poly.material_index = m
        poly.use_smooth = True
        for li, w in zip(poly.loop_indices, (a, b, c)):
            uvl.data[li].uv = (wedges[w][2], 1.0 - wedges[w][3])
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for i, slot in enumerate(mats):
        mat = bpy.data.materials.new(f"{name}_{slot or i}")
        mat.use_nodes = True
        tex = textures[i] if i < len(textures) else None
        if tex and os.path.isfile(tex):
            img = bpy.data.images.load(tex)
            img.alpha_mode = "NONE"
            tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
            tn.image = img
            mat.node_tree.links.new(tn.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        mat["source_texture"] = tex or ""
        me.materials.append(mat)
    groups = [obj.vertex_groups.new(name=b[0]) for b in bones]
    for w, p, bi in weights:
        groups[bi].add([p], w, "ADD")
    obj.parent = arm
    obj.modifiers.new("Armature", "ARMATURE").object = arm
    return arm, obj


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for a in args[1:]:
        path, _, tex = a.partition("=")
        arm, obj = load(path, tex.split(",") if tex else None)
        print("PSK2BLEND", path, len(obj.data.vertices), "points", len(obj.data.polygons), "faces")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]))
