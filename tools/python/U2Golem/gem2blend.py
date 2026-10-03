"""Unreal II Golem character (.gem) -> a Blender scene: rigged, weighted, UV-mapped and textured.
Run with Blender:  blender -b --python gem2blend.py -- <in.gem> <out.blend> [texture dir]

Builds the armature from Golem's bone hierarchy, the mesh from its points (vertex groups =
bone weights, UVs from the render vertices, one material per Golem material slot), and saves
the .blend. Golem is Y up; the scene is converted to Blender's Z up.
"""
import os, sys
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gem import Gem

args = sys.argv[sys.argv.index("--") + 1:]
src, dst = args[0], args[1]
texdir = args[2] if len(args) > 2 else os.path.dirname(src)
name = os.path.splitext(os.path.basename(src))[0]

g = Gem(src)
names, pts, spans, weights, normals = g.bone_points()
bones = g.bones()
verts, uvs, tris, mats = g.vertices(), g.uvs(), g.triangles(), g.materials()
UP = Matrix.Rotation(1.5707963, 4, "X")          # Y up -> Z up

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---- skeleton: world transforms from parent-relative position + quaternion -------------------
world = []
for bname, parent, pos, q in bones:
    local = Matrix.Translation(Vector(pos)) @ Quaternion((q[3], q[0], q[1], q[2])).to_matrix().to_4x4()
    world.append(local if parent < 0 else world[parent] @ local)
arm_data = bpy.data.armatures.new(name + "Skeleton")
arm = bpy.data.objects.new(name + "Skeleton", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = []
for i, (bname, parent, pos, q) in enumerate(bones):
    m = UP @ world[i]
    b = arm_data.edit_bones.new(bname)
    head = m.to_translation()
    kids = [j for j, bb in enumerate(bones) if bb[1] == i]
    if len(kids) == 1:
        tail = (UP @ world[kids[0]]).to_translation()
        if (tail - head).length < 0.5:
            tail = head + m.to_3x3() @ Vector((2.0, 0, 0))
    else:
        tail = head + m.to_3x3() @ Vector((2.0, 0, 0))   # Character Studio bones run along local X
    b.head, b.tail = head, tail
    if parent >= 0:
        b.parent = eb[parent]
    eb.append(b)
bpy.ops.object.mode_set(mode="OBJECT")

# ---- mesh ------------------------------------------------------------------------------------
me = bpy.data.meshes.new(name)
co = [UP @ Vector(p) for p in pts]
faces = [(verts[a][0], verts[b][0], verts[c][0]) for a, b, c, m in tris]
me.from_pydata([tuple(v) for v in co], [], faces)
uvl = me.uv_layers.new(name="UVMap")
for poly, (a, b, c, m) in zip(me.polygons, tris):
    poly.material_index = m
    poly.use_smooth = True
    for li, v in zip(poly.loop_indices, (a, b, c)):
        u, t = uvs[verts[v][2]]
        uvl.data[li].uv = (u, 1.0 - t)               # Golem/D3D v runs down
me.validate()
obj = bpy.data.objects.new(name, me)
bpy.context.scene.collection.objects.link(obj)

# materials: Golem slot names; textures guessed as <Character><Slot>_Default.tga in the folder
tex_files = [f for f in os.listdir(texdir) if f.lower().endswith(".tga")]
for slot in mats:
    mat = bpy.data.materials.new(slot)
    mat.use_nodes = True
    hit = [f for f in tex_files if slot.lower() in f.lower()]
    if hit:
        img = bpy.data.images.load(os.path.join(texdir, hit[0]))
        img.alpha_mode = "NONE"                      # Golem alpha is a gloss mask, not transparency
        tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tn.image = img
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        mat.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.append(mat)

# weights
groups = {b[0]: obj.vertex_groups.new(name=b[0]) for b in bones}
for p, (cnt, first) in enumerate(spans):
    for k in range(cnt):
        bi, w = weights[first + k]
        groups[names[bi]].add([p], w, "REPLACE")
obj.parent = arm
mod = obj.modifiers.new("Armature", "ARMATURE")
mod.object = arm

bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(dst))
print(f"GEM2BLEND {dst}: {len(pts)} points, {len(faces)} faces, {len(bones)} bones, materials {mats}")
