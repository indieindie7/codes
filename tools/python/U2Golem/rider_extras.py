"""Primitive-built parts for the rider test (U2Golem/rider): a stahlhelm-style helmet with a
flared skirt, two antennae, a skull mouth guard, a round belt buckle and a shoulder knob.
Each part is rigid on one bone and uses the armour material armorgen made (or a steel one).

Run:  blender -b rider.blend --python rider_extras.py -- <out.blend>
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector, Matrix

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
plate = bpy.data.materials.get("ArmourPlate")
steel = bpy.data.materials.new("Steel")
steel.use_nodes = True
b = steel.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.42, 0.43, 0.45, 1)
b.inputs["Metallic"].default_value = 0.9
b.inputs["Roughness"].default_value = 0.35
dark = bpy.data.materials.new("Dark")
dark.use_nodes = True
dark.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1)

parts = []


def finish(bm, name, mat, bone):
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    g = o.vertex_groups.new(name=bone)
    g.add(list(range(len(me.vertices))), 1.0, "REPLACE")
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    parts.append(o)
    return o


def bone_head(n):
    return arm.matrix_world @ arm.data.bones[n].head_local


head = bone_head("Merc Head")          # chin level; the skull centre is ~6 above

# ---- helmet: a dome with a flared skirt, open at the face ------------------------------------
c = head + Vector((0, 0.5, 6.5))
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=11.0)
for v in bm.verts:
    v.co = Vector((v.co.x * 1.0, v.co.y * 1.12, v.co.z * 0.95))
cut = [v for v in bm.verts if v.co.z < -6.0 or (v.co.y < -4.0 and v.co.z < 1.5)]
bmesh.ops.delete(bm, geom=cut, context="VERTS")
for v in bm.verts:
    if v.co.z < 1.0:                    # the skirt flares out, most at the back and sides
        flare = (1.0 - v.co.z) * 0.32 * (1.0 if v.co.y > -4 else 0.4)
        r = Vector((v.co.x, v.co.y, 0)).normalized()
        v.co += r * flare
bmesh.ops.translate(bm, verts=bm.verts, vec=c)
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=-0.9)
finish(bm, "helmet", plate, "Merc Head")

# ---- antennae: thin rods from the brow, splaying up and out ----------------------------------
for sx in (1, -1):
    bm = bmesh.new()
    p0 = c + Vector((sx * 3.0, -10.5, 4.5))
    p1 = c + Vector((sx * 7.0, -9.0, 32.0))
    d = p1 - p0
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.55, radius2=0.35, depth=d.length)
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=bm.verts)
    finish(bm, f"antenna_{'L' if sx > 0 else 'R'}", steel, "Merc Head")

# ---- skull mouth guard: a jaw plate with tooth slats -----------------------------------------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.scale(bm, vec=Vector((9.0, 3.0, 5.5)), verts=bm.verts)
bmesh.ops.translate(bm, verts=bm.verts, vec=head + Vector((0, -8.8, 1.5)))
for i in range(5):
    t = bmesh.new()
    bmesh.ops.create_cube(t, size=1.0)
    bmesh.ops.scale(t, vec=Vector((1.3, 1.2, 4.2)), verts=t.verts)
    bmesh.ops.translate(t, verts=t.verts, vec=head + Vector((-3.6 + i * 1.8, -10.6, 1.8)))
    me = bpy.data.meshes.new("tmp")
    t.to_mesh(me)
    bm.from_mesh(me)
finish(bm, "mouthguard", steel, "Merc Head")

# ---- belt buckle: a round plate with a raised ring -------------------------------------------
pel = bone_head("Merc Pelvis")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=5.5, radius2=5.0, depth=1.6)
ring = bmesh.new()
bmesh.ops.create_cone(ring, cap_ends=True, segments=24, radius1=3.0, radius2=2.6, depth=2.6)
me = bpy.data.meshes.new("tmp")
ring.to_mesh(me)
bm.from_mesh(me)
rot = Matrix.Rotation(math.radians(90), 4, "X")
bmesh.ops.transform(bm, matrix=Matrix.Translation(pel + Vector((0, -11.6, 10.0))) @ rot, verts=bm.verts)
finish(bm, "buckle", steel, "Merc Pelvis")

# ---- shoulder knob on the cap (the figure's one-sided pauldron) ------------------------------
sh = bone_head("Merc L UpperArm")
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=2.0, radius2=1.8, depth=3.0)
bmesh.ops.transform(bm, matrix=Matrix.Translation(sh + Vector((2.0, 1.0, 9.5))), verts=bm.verts)
finish(bm, "shoulder_knob", steel, "Merc L UpperArm")

bpy.ops.wm.save_as_mainfile(filepath=out)
print("EXTRAS", len(parts), "parts ->", out)
