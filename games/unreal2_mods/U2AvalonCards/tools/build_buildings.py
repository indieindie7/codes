"""Liandri buildings as SCRIPTED geometry: primitives and flat materials, built in Blender from the ref
sheets' descriptions (the img2threejs / blender-kiln idea: reconstruction by code, not a generated blob).

    blender -b --python build_buildings.py -- <out_dir> [names=cooling_tower,storage_tank,...]

Writes <out_dir>/<name>_script.glb per building (metres; the layout scales them anyway). Materials:
concrete grey, orange panels, dark steel, rust, orange glow. Each builder is a few primitives; edit the
numbers to match the sheet, score with fidelity.py, repeat.
"""
import math, os, sys
import bpy

a = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(a[0])
o = dict(x.split("=", 1) for x in a[1:])
os.makedirs(out, exist_ok=True)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "U2Avalon", "tools"))
import palette  # noqa  (the Liandri palette measured from the Hunyuan models; old names are aliased)

MATS = {}
COLOURS = palette.COLOURS


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = palette.colour(name) + (1,)
        bsdf.inputs["Roughness"].default_value = 0.85 if name != "glow" else 0.4
        if name == "glow":
            bsdf.inputs["Emission Color"].default_value = COLOURS[name] + (1,)
            bsdf.inputs["Emission Strength"].default_value = 4
        MATS[name] = m
    return MATS[name]


def place(ob, x, y, z, m, rot=(0, 0, 0)):
    ob.location = (x, y, z)
    ob.rotation_euler = rot
    ob.data.materials.append(mat(m))
    return ob


def box(x, y, z, sx, sy, sz, m="concrete", rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.scale = (sx, sy, sz)
    return place(ob, x, y, z, m, rot)


def cyl(x, y, z, r, h, m="concrete", n=24, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r, radius2=r2, depth=h)
    return place(bpy.context.object, x, y, z, m, rot)


def sphere(x, y, z, r, m="concrete"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=24, ring_count=12)
    return place(bpy.context.object, x, y, z, m)


def ring_of(n, r, fn):
    for i in range(n):
        t = 2 * math.pi * i / n
        fn(r * math.cos(t), r * math.sin(t), t)


def doors(x, y, z, w, h, facing_y=True):
    """a dark doorway with an orange frame on a wall facing -Y (or -X)"""
    if facing_y:
        box(x, y - 0.02, z + h / 2, w + 0.3, 0.1, h + 0.3, "orange")
        box(x, y - 0.06, z + h / 2, w, 0.1, h, "dark")
    else:
        box(x - 0.02, y, z + h / 2, 0.1, w + 0.3, h + 0.3, "orange")
        box(x - 0.06, y, z + h / 2, 0.1, w, h, "dark")


def cooling_tower():
    cyl(0, 0, 2, 7, 4, "concrete", 32, 5.4)                    # flared base
    cyl(0, 0, 18, 5.2, 28, "concrete", 32)                     # shaft
    cyl(0, 0, 32.6, 5.6, 1.2, "pale", 32)                      # top rim
    cyl(0, 0, 33.4, 4.6, 0.6, "dark", 32)                      # vent mouth
    for sgn in (-1, 1):
        box(sgn * 3.6, -4.9, 16, 1.8, 0.4, 9, "orange")        # tall panels
        box(sgn * 3.6, -4.9, 26, 1.8, 0.4, 3, "orange")
    doors(0, -5.4, 0.2, 1.6, 2.6)
    ring_of(6, 5.4, lambda x, y, t: box(x, y, 2.2, 1.0, 1.0, 4.4, "pale", (0, 0, t)))   # base buttresses


def processing_hall():
    box(0, 0, 4, 30, 14, 8, "concrete")                        # hall
    for i in range(5):                                          # sawtooth roof
        x = -12 + i * 6
        box(x, 0, 9.0, 5.8, 14, 2, "pale", (0, math.radians(18), 0))
        box(x + 2.6, 0, 9.0, 0.3, 14, 2.6, "glow")             # the lit face of each tooth
    for i in range(4):
        doors(-10 + i * 6.5, -7, 0, 3, 4)
    box(-16, 0, 1.5, 4, 8, 3, "concrete")                      # loading bay
    box(16, 0, 1.5, 4, 8, 3, "concrete")
    ring_of(4, 0, lambda x, y, t: None)


def storage_tank():
    cyl(0, 0, 0.6, 6.5, 1.2, "dark", 32)                       # base ring
    cyl(0, 0, 5.5, 6, 8.6, "concrete", 32)                     # shell
    sphere(0, 0, 9.8, 6, "concrete")                           # dome (lower half inside the shell)
    for i in range(8):                                          # ribs
        t = 2 * math.pi * i / 8
        box(5.9 * math.cos(t), 5.9 * math.sin(t), 5.5, 0.5, 0.9, 8.6, "pale", (0, 0, t))
    box(0, -6.1, 5.5, 3.4, 0.3, 4, "orange")                    # panel
    cyl(0, 0, 13.2, 0.6, 1.6, "dark", 12)                      # valve stack
    box(2.2, -5.9, 2.5, 0.4, 0.5, 5, "dark")                    # ladder


def ore_tank():
    for i in range(4):                                          # legs
        t = math.pi / 4 + 2 * math.pi * i / 4
        box(3.2 * math.cos(t), 3.2 * math.sin(t), 2.5, 0.8, 0.8, 5, "dark", (0, 0, t))
    cyl(0, 0, 6.0, 4.4, 3.0, "dark", 8, 1.2)                   # hopper (cone)
    cyl(0, 0, 13.5, 4.6, 12, "rust", 8)                        # octagonal silo
    cyl(0, 0, 20.6, 4.8, 2.2, "rust", 8, 0.8)                  # roof cone
    cyl(0, 0, 22.0, 0.5, 1.2, "dark", 8)
    box(0, -4.7, 13.5, 1.6, 0.3, 1.6, "glow")                   # lit hatch
    box(0, -4.6, 9.0, 1.2, 0.3, 5, "dark")                      # ladder


def dock_crane():
    box(0, 0, 0.3, 24, 8, 0.6, "concrete")                      # dock slab
    for sgn in (-1, 1):
        box(sgn * 8.5, 0, 6.5, 5.5, 4.5, 13, "concrete")        # wall-like legs
        box(sgn * 8.5, -2.3, 6.5, 3.5, 0.2, 9, "orange")
    box(0, 0, 15.0, 23, 4.5, 4.0, "concrete")                   # thick beam
    box(0, -2.3, 15.0, 21, 0.2, 2.6, "orange")
    box(2, 0, 12.8, 3, 3, 1.6, "dark")                          # trolley
    cyl(2, 0, 7.5, 0.08, 9, "dark", 8)                          # cable
    box(2, 0, 2.6, 1.6, 1.4, 1.2, "dark")                       # hook block
    box(-6, 3, 2.0, 4, 2.4, 2.4, "rust")                        # containers
    box(-1, -3, 2.0, 4, 2.4, 2.4, "dark")


def rig(dead=False):
    body, trim = ("rust", "dark") if dead else ("concrete", "orange")
    for i in range(4):
        t = math.pi / 4 + 2 * math.pi * i / 4
        x, y = 9 * math.cos(t), 9 * math.sin(t)
        box(x, y, 9, 4.2, 4.2, 18, body, (0, 0, t))             # thick legs
        box(x, y, 0.8, 6, 6, 1.6, body)                         # feet
    box(0, 0, 21, 28, 26, 8, body)                              # deck (tall)
    box(0, 0, 25.3, 26, 24, 0.6, trim)
    box(-4, -3, 29.5, 16, 12, 8, body)                          # quarters block
    box(-4, -9.1, 29.5, 14, 0.2, 2.4, "glow" if not dead else "dark")
    box(8, 6, 30, 5, 5, 9, body)                                 # derrick block
    cyl(8, 6, 36.5, 0.7, 4, "dark", 8)
    box(13, -8, 27, 10, 1, 1, "dark", (0, math.radians(-25), 0))   # flare boom
    if not dead:
        sphere(17.5, -8, 29.2, 1.2, "glow")                     # the flare
    cyl(-10, 9, 25.6, 3.5, 0.5, trim, 12)                       # helipad


def drilling_rig(): rig(False)
def dead_rig(): rig(True)


def cargo_dropship():
    box(0, 0, 0.3, 18, 18, 0.6, "concrete")                     # pad
    box(0, 0, 0.7, 14, 14, 0.3, "dark")
    box(0, 0, 6, 16, 9, 9, "concrete")                          # hull (tall box)
    box(0, 0, 10.9, 12, 7, 1.6, "dark")                         # spine
    box(-8.1, 0, 5.5, 0.4, 7, 6, "orange")                      # open rear ramp face
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(sx * 5, sy * 6.0, 5.5, 1.5, 4.4, "dark", 16, rot=(0, math.radians(90), 0))   # engine pods
            cyl(sx * 7.3, sy * 6.0, 5.5, 1.1, 0.3, "glow", 16, rot=(0, math.radians(90), 0))
        box(0, sx * 5.4, 6.0, 8, 2.4, 0.8, "pale")              # stub wings
    box(6.5, 0, 8.0, 3, 5, 3.0, "dark")                         # cockpit


def pylon():
    box(0, 0, 10, 4.4, 2.6, 20, "concrete")                      # slab post
    box(0, -1.35, 12, 3.2, 0.2, 14, "dark")                      # recessed channel
    box(0, 0, 21.2, 5.2, 3.2, 2.4, "pale")                       # head
    for sgn in (-1, 1):
        box(sgn * 2.9, 0, 18.5, 1.4, 1.0, 1.4, "concrete")       # short arms
        cyl(sgn * 2.9, 0, 17.3, 0.25, 1.4, "dark", 8)            # insulators
    box(0, -1.4, 18.6, 2.4, 0.1, 1.2, "glow")                    # orange light
    box(0, 0, 0.5, 6, 4, 1, "concrete")                          # footing


def radio_mast():
    box(0, 0, 1.5, 6, 5, 3, "concrete")                          # hut
    doors(0, -2.5, 0, 1.4, 2.4)
    box(0, 0, 14, 4.2, 3.4, 22, "concrete")                      # blocky housing
    box(0, 0, 27, 5.5, 4.5, 4, "pale")                           # head box
    box(3.0, 0, 25, 1.2, 3.0, 2.0, "dark")                       # side pod
    cyl(0, -2.4, 26.5, 1.9, 0.6, "dark", 20, rot=(math.radians(90), 0, 0))   # dish
    sphere(0, -2.5, 26.5, 0.5, "glow")                           # dish eye
    sphere(0, 0, 29.6, 0.5, "glow")                              # beacon
    box(0, -1.75, 14, 1.0, 0.1, 10, "orange")


# --- round 2 (2026-10-07): the concept cards as geometry - the user found the 8-view cards read as flat
# billboards from the tower ("make geometric primitives in their place trying to imitate them"). Their own
# colours (blue + orange stripe huts, the beige crane temple) live in EXTRA: these go into their own package
# (AvalonSM2) with their own palette, so the shared 8-stripe Pal.tga is untouched.
EXTRA = {"blue": (0.020, 0.060, 0.330), "beige": (0.560, 0.470, 0.330), "domered": (0.420, 0.020, 0.015),
         "tin": (0.180, 0.185, 0.190), "sand": (0.360, 0.290, 0.200)}
_colour = palette.colour
palette.colour = lambda n: EXTRA[n] if n in EXTRA else _colour(n)


def frustum(x, y, z, w0, d0, w1, d1, h, m):
    """a battered block: a box whose top is w1 x d1 over a w0 x d0 base (Aztec/temple walls)"""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    me = ob.data
    for v in me.vertices:
        top = v.co.z > 0
        v.co.x *= (w1 if top else w0)
        v.co.y *= (d1 if top else d0)
        v.co.z = (v.co.z + 0.5) * h
    return place(ob, x, y, z, m)


def crane_tower():
    # the Liandri temple-tower on the mountain: a stepped, battered base (the Aztec read the user loves), a
    # tall setback tower, red domes, and a lattice crane leaning off one side with red buoys on cables
    z = 0
    for k, (w, h) in enumerate(((44, 6), (36, 6), (29, 6))):
        frustum(0, 0, z, w, w * 0.8, w - 4, (w - 4) * 0.8, h, "beige" if k % 2 == 0 else "sand")
        z += h
    for sgn in (-1, 1):                                         # a stair up the front of the steps
        box(sgn * 3, -16, 9, 1.0, 10, 18, "sand", (math.radians(-38), 0, 0))
    frustum(0, 0, z, 22, 18, 17, 14, 22, "beige")               # tower body
    z += 22
    for sgn in (-1, 1):
        box(sgn * 9.2, -6, z - 11, 0.6, 1.2, 16, "dark")        # tall slit windows
        box(sgn * 4, -7.6, z - 9, 2.2, 0.6, 5, "dark")
    doors(0, -9.5, 18, 4, 7)
    frustum(0, 0, z, 15, 12, 12, 10, 12, "sand")                # setback
    z += 12
    frustum(0, 0, z, 10, 8, 8, 7, 8, "beige")
    z += 8
    sphere(0, 0, z + 1.5, 5.5, "domered")                       # the red dome
    cyl(0, 0, z + 9, 0.35, 12, "dark", 8)                       # mast
    for sgn in (-1, 1):
        cyl(sgn * 9, 5, 30, 2.4, 8, "beige", 12)                # side turrets
        sphere(sgn * 9, 5, 35.5, 2.6, "domered")
    # the crane (the user: the thin jib read as "fishing poles"): a real lattice crane on the tower's flank -
    # a square truss boom with zigzag lacing, an A-frame, backstays to a counterweight, a cab, one hoist
    # cable with a heavy hook block
    def strut(x0, y0, z0, x1, y1, z1, t, m):
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        rot = (0, math.atan2(math.hypot(dx, dy), dz), math.atan2(dy, dx))
        bpy.ops.mesh.primitive_cube_add(size=1)
        ob = bpy.context.object
        ob.scale = (t, t, L)
        return place(ob, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, m, rot)
    bx, bz = 11.0, 34.0                                         # boom foot on the tower's flank
    box(bx - 1.5, 0, bz - 2.5, 7, 7, 5, "orange")               # the turntable / cab
    box(bx - 3.2, -3.6, bz - 1.8, 2.2, 0.1, 1.6, "glow")        # cab window
    box(bx - 6.5, 0, bz - 1.0, 5, 5.5, 4, "steel")              # counterweight block
    ang, L, w = math.radians(58), 60.0, 4.6                     # boom: 60 m at 58 degrees, chunky enough to read from the window
    ux, uz = math.cos(ang), math.sin(ang)
    chords = [(-w / 2, -w / 2), (-w / 2, w / 2), (w / 2, -w / 2), (w / 2, w / 2)]
    taper = lambda t: 1 - 0.45 * t                              # the truss narrows toward the tip
    def at(t, c):                                               # a chord point t along the boom
        nx, nz = -uz, ux                                        # boom-normal in the XZ plane
        return (bx + ux * L * t + nx * c[0] * taper(t), c[1] * taper(t), bz + uz * L * t + nz * c[0] * taper(t))
    for c in chords:
        p0, p1 = at(0, c), at(1, c)
        strut(*p0, *p1, 0.9, "orange")
    n = 14
    for k in range(n):                                          # zigzag lacing on all four faces
        t0, t1 = k / n, (k + 1) / n
        for a_, b_ in ((0, 1), (2, 3), (0, 2), (1, 3)):
            ca, cb = chords[a_], chords[b_]
            p0 = at(t0, ca if k % 2 == 0 else cb)
            p1 = at(t1, cb if k % 2 == 0 else ca)
            strut(*p0, *p1, 0.45, "steel")
    tip = at(1, (0, 0))
    box(tip[0], 0, tip[2], 3.4, 3.4, 3.4, "orange")             # the boom head sheave
    for sy in (-1.6, 1.6):                                      # A-frame over the cab
        strut(bx - 3, sy, bz, bx - 1, sy * 0.4, bz + 9, 0.4, "steel")
    ax, az = bx - 1, bz + 9
    strut(ax, 0, az, tip[0], 0, tip[2], 0.12, "dark")           # luffing cable to the tip
    strut(ax, 0, az, bx - 6.5, 0, bz + 1, 0.12, "dark")         # backstay to the counterweight
    hz = tip[2] * 0.42                                          # the hoist cable and the hook block
    strut(tip[0], 0, tip[2], tip[0], 0, hz + 2.2, 0.3, "dark")
    box(tip[0], 0, hz + 1.2, 1.8, 1.2, 2.0, "orange")
    cyl(tip[0], 0, hz - 0.2, 0.35, 1.2, "dark", 8)
    box(tip[0] + 0.5, 0, hz - 0.9, 1.2, 0.4, 0.4, "dark")       # the hook
    box(tip[0], 0, hz - 3.4, 3.0, 3.0, 3.0, "domered")          # a red cargo crate on the hook


def aframe_hut():
    # the Sana hut: a tall blue A-frame, the orange stripe along the ridge and down the gable edges
    H, W, D = 9.0, 7.0, 6.0
    for sgn in (-1, 1):
        a = math.atan2(W / 2, H)
        box(sgn * W / 4, 0, H / 2, 0.5, D, H / math.cos(a), "blue", (0, -sgn * a, 0))
    frustum(0, 0, 0, W - 0.6, D - 0.2, 0.6, D - 0.2, H - 0.2, "blue")      # the solid inside
    box(0, 0, H, 0.9, D + 0.2, 0.6, "orange")                    # ridge stripe (the orange top)
    for sgn in (-1, 1):
        a = math.atan2(W / 2, H)
        box(sgn * W / 4, -D / 2 - 0.05, H / 2, 0.35, 0.2, H / math.cos(a), "orange", (0, -sgn * a, 0))
    doors(0, -D / 2 - 0.1, 0, 1.4, 2.4)
    box(0, -D / 2 - 0.15, 5.5, 1.0, 0.2, 2.4, "glow")            # the lit sign panel


def dorm_pod():
    # a blue sleeping box with an orange slab roof, raised on a narrower blue pedestal
    box(0, 0, 2.5, 6, 6, 5, "blue")                              # pedestal
    doors(0, -3, 0, 1.4, 2.4)
    box(0, 0, 8, 12, 9, 6, "blue")                               # pod
    box(0, 0, 11.3, 12.6, 9.6, 0.6, "orange")                    # roof slab
    box(0, -4.55, 10.6, 12.2, 0.2, 0.5, "orange")                # stripe
    for sx in (-3.5, 0, 3.5):
        box(sx, -4.56, 8, 2.2, 0.1, 1.6, "glow")                 # window strip


def tin_shack():
    # a grey corrugated tin shed with a pitched roof
    box(0, 0, 1.6, 8, 5, 3.2, "tin")
    for sgn in (-1, 1):
        box(0, sgn * 1.4, 3.75, 8.6, 3.2, 0.25, "steel", (sgn * math.radians(-22), 0, 0))
    for k in range(-3, 4):
        box(k * 1.1, -2.52, 1.6, 0.15, 0.06, 3.0, "steel")       # corrugation ribs
    doors(-2, -2.55, 0, 1.2, 2.2)
    sphere(-2, -2.7, 2.5, 0.15, "glow")                           # the lamp over the door


def twin_towers():
    # the stilt huts: dark huts on a platform of thin legs over water, a gantry between them
    box(0, 0, 6, 16, 6, 0.6, "dark")                             # platform
    for x in (-7, -2.5, 2.5, 7):
        for y in (-2.5, 2.5):
            cyl(x, y, 3, 0.25, 6, "rust", 6)
    for sgn in (-1, 1):
        box(sgn * 5, 0, 8.5, 4.5, 4.5, 4.5, "rustred")           # huts
        cyl(sgn * 5, 0, 11.2, 3.0, 0.8, "dark", 16)              # flat hat roofs
        doors(sgn * 5, -2.25, 6.3, 1.0, 2.0)
    box(0, 0, 9, 6, 1.0, 0.3, "dark")                            # gantry


def water_tower():
    # a tall column, a flared tank, a red-cone roof
    cyl(0, 0, 9, 1.4, 18, "brown", 16, r2=1.0)
    cyl(0, 0, 18.8, 1.2, 1.6, "steel", 16, r2=3.2)
    cyl(0, 0, 21, 3.2, 3.0, "rustred", 20)
    box(0, -3.2, 21, 2.0, 0.2, 0.6, "orange")
    cyl(0, 0, 24.2, 3.6, 3.4, "sand", 20, r2=0.2)               # cone roof
    sphere(1.2, -2.6, 24, 0.5, "domered")


# --- factories, pipes, roads (the user's mark, 2026-10-08: "add some procedural roads and pipes please and make
# some more normal look factories and some factory districts in the plateau")
EXTRA.update({"brick": (0.230, 0.075, 0.045), "asphalt": (0.050, 0.050, 0.055), "paint": (0.700, 0.650, 0.300)})


def factory_hall():
    # a long brick hall with a sawtooth roof (north lights), two chimneys and a loading bay
    L, W, H = 40.0, 22.0, 9.0
    box(0, 0, H / 2, L, W, H, "brick")
    box(0, -W / 2 - 0.05, 1.2, L, 0.1, 2.4, "steel")            # dirty plinth
    n = 6
    for k in range(n):                                          # the sawtooth: a steep glazed face + a slope
        x = -L / 2 + (k + 0.5) * L / n
        box(x - L / n * 0.3, 0, H + 1.6, 0.4, W, 3.2, "glow" if k % 2 else "dark")
        box(x + L / n * 0.1, 0, H + 1.6, L / n * 0.85, W, 0.5, "steel", (0, math.radians(-21), 0))
    for cx, h in ((L / 2 - 4, 26), (L / 2 - 10, 20)):
        cyl(cx, W / 2 - 4, h / 2, 1.3, h, "brick", 12, r2=1.0)    # chimneys
        cyl(cx, W / 2 - 4, h + 0.3, 1.2, 0.6, "dark", 12)
    doors(-L / 2 + 6, -W / 2, 0, 5, 5)                          # loading doors
    doors(-L / 2 + 14, -W / 2, 0, 5, 5)
    for k in range(5):
        box(-L / 2 + 8 * k + 4, -W / 2 - 0.05, 6.2, 5, 0.1, 1.4, "glow" if k % 3 else "dark")   # window band


def factory_block():
    # a four-storey industrial block: concrete frame, window bands, a water tank and a stair tower on the roof
    W, D, S = 18.0, 12.0, 3.6
    box(0, 0, 2 * S, W, D, 4 * S, "steel")
    for k in range(4):
        box(0, -D / 2 - 0.05, S * k + 2.0, W - 1.0, 0.1, 1.2, "glow" if (k + 1) % 2 else "dark")
        box(0, D / 2 + 0.05, S * k + 2.0, W - 1.0, 0.1, 1.2, "dark")
    box(0, 0, 4 * S + 0.3, W + 0.4, D + 0.4, 0.6, "grey")
    box(W / 2 - 3, D / 2 - 3, 4 * S + 2.0, 4, 4, 3.4, "steel")   # stair tower
    cyl(-W / 2 + 3, 0, 4 * S + 2.5, 1.8, 3.0, "rustred", 16)    # roof tank
    doors(0, -D / 2, 0, 2.2, 3.0)


def chimney_stack():
    # a tall industrial stack with red/white bands and a service ring
    cyl(0, 0, 3, 4.5, 6, "steel", 20)
    cyl(0, 0, 26, 2.6, 44, "brick", 20, r2=1.8)
    for z in (40, 44):
        cyl(0, 0, z, 2.05, 1.6, "domered" if z == 44 else "paint", 20)
    cyl(0, 0, 35, 2.9, 0.4, "dark", 20)                         # service ring


def silo_cluster():
    # four grain/ore silos with a gallery on top and a conveyor housing
    for sx in (-4, 4):
        for sy in (-4, 4):
            cyl(sx, sy, 11, 3.6, 22, "grey", 20)
            cyl(sx, sy, 22.6, 3.6, 1.2, "steel", 20, r2=2.8)
    box(0, 0, 24.5, 16, 4, 3, "steel")                          # top gallery
    box(12, 0, 14, 14, 2.4, 2.4, "steel", (0, math.radians(40), 0))   # conveyor housing up to it


def pipe_rack():
    # a 20 m pipe rack segment along +X (tiles end to end): two big pipes, one small, T-supports every 10 m
    for x in (-5, 5):
        box(x, 0, 2.5, 0.5, 0.5, 5, "steel")
        box(x, 0, 5.1, 0.5, 3.6, 0.4, "steel")
    for y, r, m in ((-1.0, 0.55, "grey"), (0.4, 0.45, "rustred"), (1.4, 0.25, "paint")):
        cyl(0, y, 5.3 + r, r, 20.0, m, 12, rot=(0, math.radians(90), 0))


def road_segment():
    # a 20 m x 8 m asphalt road slab (tiles end to end along +X): kerbs and a dashed centre line
    box(0, 0, 0.15, 20, 8, 0.3, "asphalt")
    for y in (-4.1, 4.1):
        box(0, y, 0.2, 20, 0.3, 0.4, "grey")
    for x in (-7.5, -2.5, 2.5, 7.5):
        box(x, 0, 0.31, 3, 0.18, 0.02, "paint")


BUILDERS = {"factory_hall": factory_hall, "factory_block": factory_block, "chimney_stack": chimney_stack,
            "silo_cluster": silo_cluster, "pipe_rack": pipe_rack, "road_segment": road_segment,
            "crane_tower": crane_tower, "aframe_hut": aframe_hut, "dorm_pod": dorm_pod, "tin_shack": tin_shack,
            "twin_towers": twin_towers, "water_tower": water_tower,
            "cooling_tower": cooling_tower, "processing_hall": processing_hall, "storage_tank": storage_tank,
            "ore_tank": ore_tank, "dock_crane": dock_crane, "drilling_rig": drilling_rig, "dead_rig": dead_rig,
            "cargo_dropship": cargo_dropship, "pylon": pylon, "radio_mast": radio_mast}
names = o.get("names", ",".join(BUILDERS)).split(",")
for name in names:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    BUILDERS[name]()
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
    path = os.path.join(out, name + "_script.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True)
    print("BUILT", name, len(bpy.context.scene.objects), "parts ->", path)
