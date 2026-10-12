"""Blender: page-3 level map (layout.json) -> blockout scene + renders from the drawn C1 cameras and a top view.
blender -b --factory-startup -P build_level.py -- <page3 dir>"""
import bpy, bmesh, json, math, os, sys, random
D = sys.argv[sys.argv.index('--') + 1]; L = json.load(open(os.path.join(D, 'layout.json')))
S = L['scale_m_per_px']; random.seed(3)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
W = lambda x, y: (x * S, -y * S)
HT, HH, HR = L['hill']['top'], L['hill']['height_m'], L['hill']['radius_px']
def hgt(x, y):
    d = math.hypot(x - HT[0], y - HT[1]) / HR
    return HH * max(0.0, 1 - d) ** 2
def mat(name, col, img=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = 0.9
    if img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(D, img))
        nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
        b.inputs['Emission Color'].default_value = (1, 1, 1, 1); nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = 0.35
    return m
def obj(name, bm, m):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me)
    o.data.materials.append(m); sc.collection.objects.link(o); return o
# ground
bm = bmesh.new(); X0, Y0, X1, Y1 = L['map_box']; n = 80
bmesh.ops.create_grid(bm, x_segments=n, y_segments=n, size=1)
for v in bm.verts:
    px = X0 + (v.co.x + 1) / 2 * (X1 - X0); py = Y0 + (1 - (v.co.y + 1) / 2) * (Y1 - Y0)
    v.co = (*W(px, py), hgt(px, py))
obj('ground', bm, mat('grass', (0.16, 0.2, 0.1)))
# path strip
pts = L['path']; bm = bmesh.new(); prev = None
for i, (x, y) in enumerate(pts):
    a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
    dx, dy = b[0] - a[0], b[1] - a[1]; l = math.hypot(dx, dy) or 1; nx, ny = -dy / l * 12, dx / l * 12
    z = hgt(x, y) + 0.06
    vs = [bm.verts.new((*W(x + nx, y + ny), z)), bm.verts.new((*W(x - nx, y - ny), z))]
    if prev: bm.faces.new([prev[0], prev[1], vs[1], vs[0]])
    prev = vs
obj('path', bm, mat('dirt', (0.35, 0.27, 0.17)))
# buildings: leaning box + pyramid roof
wall, roof = mat('wall', (0.55, 0.5, 0.45)), mat('roof', (0.22, 0.12, 0.1))
for i, (x, y, w, d, ang) in enumerate(L['buildings']):
    hgtb = random.uniform(5, 8); z = hgt(x, y)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts: v.co = (v.co.x * w * S, v.co.y * d * S, (v.co.z + 0.5) * hgtb)
    o = obj(f'B{i}', bm, wall); o.location = (*W(x, y), z - 0.3)
    o.rotation_euler = (random.uniform(-.04, .04), random.uniform(-.04, .04), math.radians(-ang))
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.72, radius2=0, depth=1)
    for v in bm.verts: v.co = (v.co.x * w * S, v.co.y * d * S, (v.co.z + 0.5) * hgtb * 0.45)
    r = obj(f'B{i}_roof', bm, roof); r.parent = o; r.location = (0, 0, hgtb); r.rotation_euler = (0, 0, math.radians(45))
    r.scale = (0.75, 0.75, 1)
# round building C: drum + dome
x, y, rr = L['round_C']; z = hgt(x, y); r = rr * S * 0.55
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=6, location=(*W(x, y), z + 3)); bpy.context.object.data.materials.append(wall)
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r * 1.05, location=(*W(x, y), z + 6))
bpy.context.object.scale.z = 0.8; bpy.context.object.data.materials.append(roof)
# cards (drawn impostors)
def card(img, x, y, height, yaw, cross=False):
    im = bpy.data.images.load(os.path.join(D, img)); asp = im.size[0] / im.size[1]; m = mat(img, (1, 1, 1), img)
    for k in ([0, 90] if cross else [0]):
        bm = bmesh.new()
        vs = [bm.verts.new((sx * height * asp / 2, 0, sz * height)) for sx, sz in [(-1, 0), (1, 0), (1, 1), (-1, 1)]]
        f = bm.faces.new(vs); uv = bm.loops.layers.uv.new()
        for lp, c in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]): lp[uv].uv = c
        o = obj(img + str(k), bm, m); o.location = (*W(x, y), hgt(x, y) - 0.1); o.rotation_euler = (0, 0, math.radians(yaw + k))
for i, (x, y) in enumerate(L['trees']):
    card(f'card_tree{i % 3 + 1}.png', x, y, random.uniform(6, 9), random.uniform(0, 90), cross=True)
x, y, w, d, _ = L['mansion_A']; card('card_mansion.png', x, y + d / 2, 16, 0)
# light + world (dusk)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 2.5; sun.data.color = (1, .75, .55); sun.rotation_euler = (math.radians(70), 0, math.radians(-40))
wd = bpy.data.worlds.new('w'); wd.use_nodes = True; wd.node_tree.nodes['Background'].inputs[0].default_value = (.08, .1, .2, 1)
wd.node_tree.nodes['Background'].inputs[1].default_value = 1.2; sc.world = wd
for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = e; break
    except TypeError: pass
sc.render.resolution_x, sc.render.resolution_y = 1280, 720; sc.view_settings.view_transform = 'Standard'
def shoot(name, loc, rot, ortho=0):
    c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); sc.collection.objects.link(c)
    c.location, c.rotation_euler = loc, rot; c.data.lens = 22
    if ortho: c.data.type = 'ORTHO'; c.data.ortho_scale = ortho
    sc.camera = c; sc.render.filepath = os.path.join(D, 'renders', name + '.png'); bpy.ops.render.render(write_still=True)
for i, (x, y, dx, dy) in enumerate(L['cameras']):
    yaw = math.atan2(-dy, dx) - math.pi / 2
    n = math.hypot(dx, dy); ahead = 25 / S                  # aim at a point 25 m ahead, 2.5 m above the ground there
    tx, ty = x + dx / n * ahead, y + dy / n * ahead
    ch = hgt(x, y) + 1.7; pitch = math.pi / 2 + math.atan2(hgt(tx, ty) + 2.5 - ch, 25)
    shoot(f'cam{i + 1}', (*W(x, y), ch), (pitch, 0, yaw))
shoot('top', (X1 * S / 2, -Y1 * S / 2, 60), (0, 0, 0), ortho=X1 * S * 1.02)
shoot('overview', (W(425, 760)[0], W(425, 760)[1], 35), (math.radians(58), 0, 0))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, 'level_blockout.blend'))
