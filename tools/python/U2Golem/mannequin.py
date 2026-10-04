"""A rigged base body from scratch, for armorgen tests: a stick skeleton -> Blender's Skin
modifier -> smoothed body mesh, an armature with the Unreal II biped's bone names (Merc ...),
automatic weights, and a dark cloth material.

Run:  blender -b --python mannequin.py -- <out.blend> [height]
The body faces -Y (like the decoded Unreal II characters), Z up, T-pose, feet at z = 0.
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
H = float(args[1]) if len(args) > 1 else 180.0
s = H / 180.0

bpy.ops.wm.read_factory_settings(use_empty=True)

# joints (x, y, z) for a slim 180-unit figure, and skin radii (side, front-back)
J = {
    "pelvis": ((0, 0, 96), (15, 10)), "spine": ((0, 0, 112), (13, 9)), "chest": ((0, 0, 130), (17, 11)),
    "neck": ((0, 0, 150), (5.5, 5.5)), "head": ((0, -1, 160), (8.5, 9.5)), "crown": ((0, -1, 175), (7, 7.5)),
}
for side, sx in (("L", 1), ("R", -1)):
    J.update({
        f"{side}clav": ((sx * 6, 0, 146), (6, 6)), f"{side}shoulder": ((sx * 19, 0, 143), (6.5, 6.5)),
        f"{side}elbow": ((sx * 46, 0, 141), (4.8, 4.8)), f"{side}wrist": ((sx * 70, 0, 140), (3.6, 3.0)),
        f"{side}hand": ((sx * 80, 0, 140), (4.2, 2.0)),
        f"{side}hip": ((sx * 10, 0, 92), (9, 9)), f"{side}knee": ((sx * 11, -1, 50), (6, 6)),
        f"{side}ankle": ((sx * 12, 2, 9), (4.2, 4.2)), f"{side}toe": ((sx * 12, -13, 3), (4, 3)),
    })
edges = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head"), ("head", "crown")]
for side in "LR":
    edges += [("chest", f"{side}clav"), (f"{side}clav", f"{side}shoulder"), (f"{side}shoulder", f"{side}elbow"),
              (f"{side}elbow", f"{side}wrist"), (f"{side}wrist", f"{side}hand"),
              ("pelvis", f"{side}hip"), (f"{side}hip", f"{side}knee"), (f"{side}knee", f"{side}ankle"),
              (f"{side}ankle", f"{side}toe")]

names = list(J)
me = bpy.data.meshes.new("Mannequin")
me.from_pydata([Vector(J[n][0]) * s for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
body = bpy.data.objects.new("Mannequin", me)
bpy.context.scene.collection.objects.link(body)
bpy.context.view_layer.objects.active = body
body.select_set(True)
skin = body.modifiers.new("skin", "SKIN")
skin.use_smooth_shade = True
for i, n in enumerate(names):
    rx, ry = J[n][1]
    me.skin_vertices[0].data[i].radius = (rx * s, ry * s)
me.skin_vertices[0].data[names.index("pelvis")].use_root = True
sub = body.modifiers.new("sub", "SUBSURF")
sub.levels = 2
bpy.ops.object.modifier_apply(modifier="skin")
bpy.ops.object.modifier_apply(modifier="sub")

# armature: Unreal II biped names, so armorgen specs work on it unchanged
bones = [("Merc Pelvis", "pelvis", "spine", None), ("Merc Spine1", "spine", "chest", "Merc Pelvis"),
         ("Merc Spine2", "chest", "neck", "Merc Spine1"), ("Merc Neck", "neck", "head", "Merc Spine2"),
         ("Merc Head", "head", "crown", "Merc Neck")]
for side in "LR":
    bones += [(f"Merc {side} Clavicle", f"{side}clav", f"{side}shoulder", "Merc Spine2"),
              (f"Merc {side} UpperArm", f"{side}shoulder", f"{side}elbow", f"Merc {side} Clavicle"),
              (f"Merc {side} Forearm", f"{side}elbow", f"{side}wrist", f"Merc {side} UpperArm"),
              (f"Merc {side} Hand", f"{side}wrist", f"{side}hand", f"Merc {side} Forearm"),
              (f"Merc {side} Thigh", f"{side}hip", f"{side}knee", "Merc Pelvis"),
              (f"Merc {side} Calf", f"{side}knee", f"{side}ankle", f"Merc {side} Thigh"),
              (f"Merc {side} Foot", f"{side}ankle", f"{side}toe", f"Merc {side} Calf")]
ad = bpy.data.armatures.new("MannequinSkeleton")
arm = bpy.data.objects.new("MannequinSkeleton", ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for name, a, b, parent in bones:
    eb = ad.edit_bones.new(name)
    eb.head, eb.tail = Vector(J[a][0]) * s, Vector(J[b][0]) * s
    if parent:
        eb.parent = ad.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

mat = bpy.data.materials.new("Cloth")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1)
bsdf.inputs["Roughness"].default_value = 0.95
body.data.materials.append(mat)

bpy.ops.wm.save_as_mainfile(filepath=out)
print("MANNEQUIN", len(body.data.polygons), "faces,", len(bones), "bones ->", out)
