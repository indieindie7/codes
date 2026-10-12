"""Blender (headless): swap the house's Hunyuan/carved awnings for built porches (sloped roof on posts) and add the shed.
blender -b --factory-startup -P porch_shed.py -- <in.glb> <out.glb> <measure.json> [depth_x=2.0]
User 2026-10-12: "yes rebuild the house with the porches and shed". housePlan1 drawing: both awnings are porches
reaching well out with posts to the ground; the small box far left is a separate shed (own object "shed").
Frame as assemble_measured.py: ground storey 3 m, gable wall faces -Y, long wall faces +X, origin at the house centre."""
import sys, json, bpy, bmesh
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
pin, out, pm = a[:3]
opt = dict(s.split("=") for s in a[3:])
r = json.load(open(pm))["ratios_to_F_height"]
H = 3.0
fw, sl = r["front_width"] * H, r["side_length"] * H
D = r["awning_depth"] * H * float(opt.get("depth_x", 2.0))       # porch depth out from the wall
TOP = r["awning_height"] * H                                     # roof height at the wall
DROP = 0.35                                                      # roof falls this much to the outer edge
POST, ROOF_T = 0.09, 0.06

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=pin)
gone = [o for o in bpy.data.objects if "awning" in o.name.lower()]
print("removing", [o.name for o in gone])
for o in gone: bpy.data.objects.remove(o)

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1); return m
WOOD, ROOF, SHED = mat("porch_wood", (0.42, 0.32, 0.22)), mat("porch_roof", (0.25, 0.22, 0.2)), mat("shed", (0.5, 0.44, 0.36))

def solid(name, verts, m):
    """convex block from 8 corners (bottom 4 then top 4, same order)"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    v = [bm.verts.new(p) for p in verts]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); me.materials.append(m); return o

def post(name, x, y, h):
    s = POST / 2
    return solid(name, [(x - s, y - s, 0), (x + s, y - s, 0), (x + s, y + s, 0), (x - s, y + s, 0),
                        (x - s, y - s, h), (x + s, y - s, h), (x + s, y + s, h), (x - s, y + s, h)], WOOD)

def porch(name, u0, u1, wall, out_dir, along):
    """roof from the wall line out by D, between u0..u1 along the wall; posts at the outer corners (+ middle if long)"""
    def P(u, d, z):                                   # u along the wall, d out from it
        return tuple(Vector(along) * u + Vector(out_dir) * (wall + d) + Vector((0, 0, z)))
    lo, hi = TOP, TOP - DROP
    roof = solid(name + "_roof", [P(u0, 0, lo), P(u1, 0, lo), P(u1, D, hi), P(u0, D, hi),
                                  P(u0, 0, lo + ROOF_T), P(u1, 0, lo + ROOF_T), P(u1, D, hi + ROOF_T), P(u0, D, hi + ROOF_T)], ROOF)
    parts = [roof]
    n = 3 if (u1 - u0) > 1.8 else 2
    for k in range(n):
        u = u0 + POST + (u1 - u0 - 2 * POST) * k / (n - 1)
        x, y, _ = P(u, D - POST, 0); parts.append(post(f"{name}_post{k}", x, y, hi))
    for p in parts: p.name = name if p is roof else p.name
    return parts

# front porch on the gable wall (-Y), most of its width; side porch on the long wall (+X) from the near corner
porch("porch_front", -fw * 0.45, fw * 0.45, sl / 2, (0, -1, 0), (1, 0, 0))
porch("porch_side", -sl / 2, -sl / 2 + sl * r.get("awning_side_frac", 0.85), fw / 2, (1, 0, 0), (0, 1, 0))

# shed: far left in the drawing = -X side, a step ahead of the gable wall; mono-pitch top falling to the back
w, d, hf, hb = 1.0, 1.0, 2.0, 1.75
cx, cy = -fw / 2 - 0.35 - w / 2, -sl / 2 + d / 2 - 0.3
solid("shed", [(cx - w/2, cy - d/2, 0), (cx + w/2, cy - d/2, 0), (cx + w/2, cy + d/2, 0), (cx - w/2, cy + d/2, 0),
               (cx - w/2, cy - d/2, hf), (cx + w/2, cy - d/2, hf), (cx + w/2, cy + d/2, hb), (cx - w/2, cy + d/2, hb)], SHED)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True)
print("PORCHSHED", out, "porch depth", round(D, 2), "top", round(TOP, 2), "house", round(fw, 2), round(sl, 2))
