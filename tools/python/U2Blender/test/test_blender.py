"""Headless test of the add-on with Blender's Python module (pip install bpy), no Blender UI:

    python test/test_blender.py [render.png]

Imports test/sample.t3d and checks it against the file: actor counts, every brush face's
normal (Blender's, after mirroring) against the T3D's Normal, positions and rotations of
actors. Then the way back: exported unchanged, every actor comes out the same (brushes: the
same faces and texture alignment, now in world space); edited (moved, rotated, a new brush and
light), the edits come out. With a path, also renders the imported map to that PNG."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))   # tools/python, for "import U2Blender"

import bpy
from mathutils import Vector
import U2Blender
from U2Blender import t3d

SAMPLE = os.path.join(HERE, "sample.t3d")
SCALE = 0.02
failures = []

def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        failures.append(what)

def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def test_import():
    fresh_scene()
    U2Blender.register()
    made, warnings = U2Blender.import_t3d(bpy.context, SAMPLE, scale=SCALE)
    umap = t3d.read(SAMPLE)
    check(made == len(umap.actors), "every actor imported (%d)" % made)
    by_name = {o["ue_name"]: o for o in bpy.data.objects if "ue_name" in o}
    # brush normals: Blender's face normal == the T3D's Normal, mirrored
    worst = 1.0
    for a in umap.actors:
        if a.polys is None:
            continue
        obj = by_name[a.name]
        wp = a.world_polys()
        for fi, poly in enumerate(obj.data.polygons):
            n = obj.matrix_world.to_3x3() @ poly.normal
            want = Vector(t3d.normalize(t3d.to_blender(wp[fi].normal, 1)))
            worst = min(worst, n.normalized().dot(want))
    check(worst > 0.999, "brush face normals match the T3D (worst dot %.4f)" % worst)
    # the rotated, scaled, pivoted add brush: its world vertices
    b2 = by_name["Brush2"]
    zs = sorted({round((b2.matrix_world @ v.co).z / SCALE, 2) for v in b2.data.vertices})
    check(zs == [64.0, 320.0], "Brush2 spans Z 64..320 after PrePivot and PostScale (%s)" % zs)
    # a light at its place, with the hue as colour
    light = by_name["Light0"]
    check((light.matrix_world.translation - Vector((-100 * SCALE, -200 * SCALE, 600 * SCALE))).length < 1e-5,
          "light at (-100, 200, 600) -> Blender (-2, -4, 12)")
    check(light.data.color.r > light.data.color.b, "light hue 30 (orange) is warm")
    # static mesh: Yaw 16384 turns Unreal's X to +Y, which is Blender's -Y; DrawScale 1.5 x (1, 2, 1)
    sm = by_name["StaticMeshActor0"]
    x_axis = (sm.matrix_world.to_3x3() @ Vector((1, 0, 0)))
    check((x_axis.normalized() - Vector((0, -1, 0))).length < 1e-5, "static mesh faces Unreal +Y (Blender -Y)")
    check(abs(x_axis.length - 1.5) < 1e-5 and abs((sm.matrix_world.to_3x3() @ Vector((0, 1, 0))).length - 3.0) < 1e-5,
          "static mesh scale 1.5 x (1, 2, 1)")
    check("Event=OpenDoor" in by_name["Trigger0"]["ue_t3d"], "the trigger keeps its own text")
    check(len(bpy.data.collections["UE Brushes Subtract"].objects) == 1 and len(bpy.data.collections["UE Brushes Add"].objects) == 1,
          "brushes sorted by CSG type")
    return by_name

def tex_coords(poly):
    """Texture coordinates at each vertex: what the alignment means, whatever its origin."""
    return [round(t3d.dot(t3d.sub(v, poly.origin), poly.texture_u) + poly.pan[0], 3) for v in poly.verts] + \
           [round(t3d.dot(t3d.sub(v, poly.origin), poly.texture_v) + poly.pan[1], 3) for v in poly.verts]

def same_brush(a, b):
    pa, pb = a.world_polys(), b.world_polys()
    if len(pa) != len(pb):
        return False
    for x, y in zip(pa, pb):
        if x.texture != y.texture or len(x.verts) != len(y.verts):
            return False
        if any(not all(abs(c - d) < 1e-3 for c, d in zip(u, v)) for u, v in zip(x.verts, y.verts)):
            return False
        if t3d.dot(x.normal, y.normal) < 0.9999:
            return False
        if any(abs(c - d) > 1e-2 for c, d in zip(tex_coords(x), tex_coords(y))):
            return False
    return True

def test_round_trip(tmp):
    path = os.path.join(tmp, "unchanged.t3d")
    U2Blender.export_t3d(bpy.context, path)
    a, b = t3d.read(SAMPLE), t3d.read(path)
    check([x.name for x in a.actors] == [x.name for x in b.actors], "unchanged export: same actors, same order")
    for x, y in zip(a.actors, b.actors):
        check([l.rstrip() for l in x.lines] == [l.rstrip() for l in y.lines], "unchanged export: %s text identical" % x.name)

    # edits: move the trigger 1 Blender unit (50 Unreal units) along X, turn the static mesh a
    # quarter more, add a new add-brush cube and a new light
    objs = {o["ue_name"]: o for o in bpy.data.objects if "ue_name" in o}
    objs["Trigger0"].location.x += 1.0
    objs["StaticMeshActor0"].rotation_euler.z -= math.pi / 2      # Blender -Z turn = Unreal +Yaw
    bpy.ops.mesh.primitive_cube_add(size=2, location=(4, 4, 1))
    cube = bpy.context.active_object
    for c in cube.users_collection:
        c.objects.unlink(cube)
    bpy.data.collections["UE Brushes Add"].objects.link(cube)
    light = bpy.data.objects.new("NewLight", bpy.data.lights.new("NewLight", "POINT"))
    light.location = (0, 2, 6)
    bpy.data.collections["UE Lights"].objects.link(light)
    bpy.context.view_layer.update()
    path = os.path.join(tmp, "edited.t3d")
    U2Blender.export_t3d(bpy.context, path)
    e = {x.name: x for x in t3d.read(path).actors}
    check(abs(e["Trigger0"].location[0] - 350) < 0.01, "moved trigger at X=350 (%s)" % (e["Trigger0"].location,))
    check("Event=OpenDoor" in "\n".join(e["Trigger0"].lines), "moved trigger keeps its event")
    yaw = e["StaticMeshActor0"].rotation[1] % 65536
    check(abs(yaw - 32768) <= 1, "turned static mesh has Yaw 32768 (%d)" % yaw)
    new = [x for x in e.values() if x.cls == "Brush" and x.name not in ("Brush0", "Brush1", "Brush2")]
    check(len(new) == 1 and new[0].props.get("CsgOper") == "CSG_Add" and len(new[0].polys) == 6,
          "new cube exported as an add brush with 6 faces")
    if new:
        wp = new[0].world_polys()
        out = all(t3d.dot(p.normal, t3d.sub(p.verts[0], (200, -200, 50))) > 0 for p in wp)
        check(out, "new brush's faces point outwards")
        zs = sorted({round(v[2], 2) for p in wp for v in p.verts})
        check(zs == [0.0, 100.0], "new brush spans Z 0..100 (%s)" % zs)
    lights = [x for x in e.values() if x.cls == "Light"]
    check(len(lights) == 2, "new light exported")

    # and the edited file imports again
    fresh_scene()
    made, _ = U2Blender.import_t3d(bpy.context, path, scale=SCALE)
    check(made == len(e), "edited export imports again (%d actors)" % made)

def render(path):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.render.resolution_x, scene.render.resolution_y = 640, 400
    world = bpy.data.worlds.new("w"); world.color = (0.05, 0.05, 0.07); scene.world = world
    # see the room from outside: the subtract brush's faces point out, so show it as wireframe
    for o in bpy.data.collections["UE Brushes Subtract"].objects:
        o.display_type = "WIRE"
        o.hide_render = True
    for o in bpy.data.collections["UE Brushes Other"].objects:
        o.hide_render = True
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    s = 512 * SCALE
    z = -256 * SCALE                         # the room's floor (subtract brush: Z -256..768)
    floor.data.from_pydata([(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z)], [], [(0, 1, 2, 3)])
    scene.collection.objects.link(floor)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3; sun.rotation_euler = (0.6, 0.3, 2.2)
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.location = (24, 20, 16)
    direction = Vector((0, 0, -2)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)

def test_real_map(tmp):
    """A real Unreal II map as UnrealEd exported it (HoverTest, from the PC test run), if the
    repo has it: imported and exported unchanged, it must come back line for line."""
    real = os.path.join(HERE, "..", "..", "..", "..", "test-results", "2026-10-01-pc", "11-blender-roundtrip", "HoverTest.t3d")
    if not os.path.isfile(real):
        print("skip  real map (test-results/2026-10-01-pc/11-blender-roundtrip/HoverTest.t3d not here)")
        return
    fresh_scene()
    made, _ = U2Blender.import_t3d(bpy.context, real, scale=SCALE)
    out = os.path.join(tmp, "HoverTest_rt.t3d")
    U2Blender.export_t3d(bpy.context, out)
    norm = lambda path: [l.rstrip() for l in open(path, encoding="latin-1").read().splitlines()]
    a, b = norm(real), norm(out)
    diff = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    check(diff == 0, "real map HoverTest (%d actors): exported unchanged, %d lines differ" % (made, diff))

if __name__ == "__main__":
    import tempfile
    test_import()
    with tempfile.TemporaryDirectory() as tmp:
        test_round_trip(tmp)
        test_real_map(tmp)
    if len(sys.argv) > 1:
        fresh_scene()
        U2Blender.import_t3d(bpy.context, SAMPLE, scale=SCALE)
        render(os.path.abspath(sys.argv[1]))
    print("FAILED: %d" % len(failures) if failures else "all passed")
    sys.exit(1 if failures else 0)
