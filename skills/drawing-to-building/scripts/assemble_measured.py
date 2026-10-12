"""Blender (headless): place housePlan1 parts with sizes measured from the sketch's depth pass.
blender -b --factory-startup -P assemble_measured.py -- <out.glb> <B.glb> <F.glb> <A.glb> <measure.json>
measure.json "ratios_to_F_height": front_width, side_length, F_height, B_wall_height, roof_rise (+ awning_* below).
Gable wall faces -Y (turn_view front); long wall faces +X. Awnings wrap the near corner (-Y/+X): one along each wall.
Written 2026-10-11 from house\depth (scenefit house)."""
import sys, json, math, bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
out, pB, pF, pA, pm = a[:5]
r = json.load(open(pm))["ratios_to_F_height"]
bpy.ops.wm.read_factory_settings(use_empty=True)

def load(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in set(bpy.data.objects) - before - set(meshes): bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.name = name; return o

def box(o):
    p = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(q[i] for q in p) for i in range(3)]), Vector([max(q[i] for q in p) for i in range(3)])

def fit(o, sx, sy, sz, x, y, z):
    lo, hi = box(o); dd = hi - lo
    o.scale = (o.scale.x * sx / dd.x, o.scale.y * sy / dd.y, o.scale.z * sz / dd.z); bpy.context.view_layer.update()
    lo, hi = box(o); o.location += Vector((x - (lo.x + hi.x) / 2, y - (lo.y + hi.y) / 2, z - lo.z)); bpy.context.view_layer.update()

H = 3.0                                       # F storey = 3 m; everything else from the ratios
fw, sl = r["front_width"] * H, r["side_length"] * H   # gable wall along X, long wall along Y
F, B, A = load(pF, "ground_F"), load(pB, "upper_B"), load(pA, "awning_A")
fit(F, fw, sl, H, 0, 0, 0)
# B's GLB is built with its gable on the front view: X = gable width, Y = long side. Height = walls + roof (+ chimney in bbox).
lo, hi = box(B); bd = hi - lo
bh = (r["B_wall_height"] + r["roof_rise"]) * H * r.get("chimney_extra", 1.0)
fit(B, fw * 1.02, sl * 1.02, bh, 0, 0, H)
ah, ad = r.get("awning_height", 0.85) * H, r.get("awning_depth", 0.35) * H
fit(A, fw * 0.9, ad, ah, 0, -sl / 2 - ad / 2, 0)              # along the gable wall, sticking out to -Y
A2 = A.copy(); A2.data = A.data.copy(); bpy.context.collection.objects.link(A2); A2.name = "awning_A_side"
A2.rotation_euler.z = math.radians(-90); bpy.context.view_layer.update()   # its front now faces +X
bpy.ops.object.select_all(action="DESELECT"); A2.select_set(True); bpy.context.view_layer.objects.active = A2
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
fit(A2, ad, sl * r.get("awning_side_frac", 0.8), ah, fw / 2 + ad / 2, -sl * (1 - r.get("awning_side_frac", 0.8)) / 2, 0)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True)
print("MEASURED", out, "F", round(fw, 2), round(sl, 2), H, "B h", round(bh, 2))
