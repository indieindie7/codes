"""The story parts (drain culverts, the taps' poles/cables/drums, the hollow-shell interior kit), built in Blender by
build_parts.py:

    blender -b --python build_parts.py -- <out_dir> ids=kit            (every part in PARTS)
    blender -b --python build_parts.py -- <out_dir> ids=B_culvert,B_k_wall_door

Every part is authored in UNREAL'S local frame (X along / forward, Y right, Z up, metres) and turned into Blender's
(x_b = Y, y_b = -X) on export, so glb_to_ase's own turn (glTF -Y front -> Unreal +X) lands it back at yaw 0. The
pivot after glb_to_ase is the XY bounds centre and z = the model's 0 (import with zero=<name>): the authored origin
of every part is listed in Models/ase/kit_pivots.json as the (dx, dy) metres from that bounds centre so the emitters
can place by the authored origin (story_export.py / shells.py read it).

Collision: objects named MCDCX_* are convex hull pieces (the UT2003-era prefix that glb_to_ase hulls=1 writes as
extra GEOMOBJECTs; the claims test showed UnrealEd uses them as the player's collision). Door and window panels
carry one hull per pier and lintel, so the openings stay walkable; tubes carry floor/walls/roof hulls.

Sizes (UU = metres x 50) are in STORY_ASSETS.md.
"""
import json, math, os

import bpy

HULL_MAT = "charcoal"
_parts_built = {}
_box = _cyl = _mat = None       # build_parts' helpers, set by build_all()


def U(X, Y, Z):
    """Unreal local (X along, Y right, Z up) -> Blender (x, y, z)"""
    return (Y, -X, Z)


def ubox(X, Y, Z, sX, sY, sZ, m="steel", yaw=0.0, pitch=0.0, hull=False):
    """a box centred at (X, Y, Z) with sizes along the Unreal axes; yaw in degrees about Z (positive toward +Y),
    pitch about Y (positive = nose up). hull=True makes it a collision hull piece instead of a render box."""
    x, y, z = U(X, Y, Z)
    # Unreal +X is Blender -y and Unreal +Y is Blender +x, so Unreal yaw +t (X toward Y) is the Blender turn
    # (0,-1) -> (1,0) = +t about z; Unreal pitch +t (nose up, X toward Z) is -t about Blender x.
    ob = _box(x, y, z, sY, sX, sZ, HULL_MAT if hull else m, (math.radians(-pitch), 0, math.radians(yaw)))
    # sizes: Blender x = Unreal Y (sY), Blender y = Unreal X (sX)
    if hull:
        ob.name = "MCDCX_h"
    return ob


def hexa(P, m="steel", hull=False):
    """a hexahedron from 8 Unreal-frame points: P[0..3] = the start face (y-, y+, at z lo / hi) and P[4..7] the end
    face in the same order: [(x,y,zlo) y-, (x,y,zlo) y+, (x,y,zhi) y+, (x,y,zhi) y-]. Faces are oriented outward
    by the centroid test, so the author needn't mind the winding."""
    V = [U(*p) for p in P]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    cx = [sum(v[k] for v in V) / 8 for k in range(3)]
    faces = []
    for f in F:
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        u = [b[k] - a[k] for k in range(3)]
        w = [c[k] - a[k] for k in range(3)]
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        fc = [sum(V[i][k] for i in f) / 4 for k in range(3)]
        out = sum(n[k] * (fc[k] - cx[k]) for k in range(3))
        faces.append(tuple(f) if out > 0 else tuple(reversed(f)))
    me = bpy.data.meshes.new("hexa")
    me.from_pydata(V, [], faces)
    me.update()
    ob = bpy.data.objects.new("MCDCX_h" if hull else "hexa", me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(_mat(HULL_MAT if hull else m))
    return ob


def prism(x0, x1, y0, y1, z0, z1, m="steel", t0=0.0, t1=0.0, hull=False):
    """a box whose start face is mitred: x = x0 + y*t0, and end face x = x1 + y*t1 (t = tan of the mitre)"""
    P = [(x0 + y0 * t0, y0, z0), (x0 + y1 * t0, y1, z0), (x0 + y1 * t0, y1, z1), (x0 + y0 * t0, y0, z1),
         (x1 + y0 * t1, y0, z0), (x1 + y1 * t1, y1, z0), (x1 + y1 * t1, y1, z1), (x1 + y0 * t1, y0, z1)]
    return hexa(P, m, hull)


def both(fn, *a, **k):
    """a render piece and the same box as a hull"""
    fn(*a, **k)
    fn(*a, **dict(k, hull=True))


# --- the drain -------------------------------------------------------------------------------------------------
CW, CH = 7.68, 6.4            # culvert interior: 384 wide, 320 high (over the ledge)
WALL = 0.5                    # 25 UU walls, floor, roof
LEDGE, CHAN_D = 2.56, 0.5     # the dry ledge (128) on the +Y side, the channel 0.5 m (25 UU) below it
CLEN = 10.24                  # one heightmap cell = 512 UU
GAL = (30.72, 15.36, 8.96)    # the sluice gallery 1536 x 768 x 448
JUN = (15.36, 15.36, 8.96)    # the junction room 768 x 768 x 448


def tube(x0, x1, m_wall="steel", t0=0.0, t1=0.0, ledge=True, roof=True, floor=True, walls=True):
    """a culvert run from x0 to x1 (mitres t0/t1): the invert at z=0, the ledge at +CHAN_D on the +Y side, walls,
    the roof. Interior width CW; outer width CW + 2 WALL. Each slab is one render hexa plus one hull hexa."""
    hw = CW / 2
    if floor:
        both(prism, x0, x1, -hw - WALL, hw + WALL, -WALL, 0.0, "steel", t0, t1)        # the slab under the channel
        both(prism, x0, x1, -hw, -hw + 0.3, 0.0, 0.3, "brown", t0, t1)                 # silt bank on the far side
    if ledge:
        both(prism, x0, x1, hw - LEDGE, hw, 0.0, CHAN_D, "grey", t0, t1)
    if walls:
        for s in (-1, 1):
            y0, y1 = (hw, hw + WALL) if s > 0 else (-hw - WALL, -hw)
            both(prism, x0, x1, y0, y1, -WALL, CHAN_D + CH + WALL, m_wall, t0, t1)
            yi = hw if s > 0 else -hw                                                   # the tide line, 1 m over the ledge
            prism(x0, x1, yi - s * 0.02, yi + s * 0.01, CHAN_D + 0.8, CHAN_D + 1.2, "brown", t0, t1)
    if roof:
        both(prism, x0, x1, -hw - WALL, hw + WALL, CHAN_D + CH, CHAN_D + CH + WALL, "charcoal", t0, t1)


def part_culvert():
    tube(-CLEN / 2, CLEN / 2)
    # formwork joints every 2.56 m: thin grey lines on the walls
    for k in range(1, 4):
        x = -CLEN / 2 + k * 2.56
        for s in (-1, 1):
            ubox(x, s * (CW / 2 - 0.01), CHAN_D + CH / 2, 0.06, 0.02, CH, "grey")


def part_culvert_bend(sign):
    """a 22.5 degree elbow turning toward +Y (sign +1, Unreal yaw +22.5) or -Y; two 4 m arms meeting at the mitre.
    Authored origin = the entry face's bottom centre; exit = origin + A*(1,0) + A*(cos t, sin t)."""
    th = math.radians(22.5) * sign
    A = 4.0
    t = math.tan(th / 2)
    tube(0.0, A, t0=0.0, t1=-t)
    # arm 2: authored in its own frame then turned by th about the corner (A, 0)
    objs0 = set(bpy.context.scene.objects)
    tube(0.0, A, t0=t, t1=0.0)
    for ob in set(bpy.context.scene.objects) - objs0:
        # every tube piece is a hexa with its verts authored in place (location 0): turn it by the Unreal yaw th
        # (= +th about Blender z) and move it to the corner, Unreal (A, 0) = Blender (0, -A)
        ob.rotation_euler = (0, 0, th)
        ob.location = (0, -A, 0)
    return {"A": A, "deg": 22.5 * sign}


def part_culvert_drop():
    """the drop shaft: 2.56 m of upper floor, then a 2.56 m shaft with no floor and a ladder on the ledge wall; the
    far wall exists only above the upper invert, so the lower culvert (placed from x = 5.12 at its own invert)
    opens into the shaft. Walls reach down 3.6 m (the deepest drop, 180 UU). The shaft floor is B_shaft_slab."""
    hw = CW / 2
    L1, L2 = 2.56, 2.56
    tube(0.0, L1)
    tube(L1, L1 + L2, floor=False, ledge=False, roof=True, walls=False)
    for s in (-1, 1):
        y0, y1 = (hw, hw + WALL) if s > 0 else (-hw - WALL, -hw)
        both(prism, L1, L1 + L2, y0, y1, -3.6, CHAN_D + CH + WALL, "steel")
    both(prism, L1 + L2, L1 + L2 + WALL, -hw - WALL, hw + WALL, 0.0, CHAN_D + CH + WALL, "steel")   # the far wall, upper half
    # the ladder down the ledge wall, 0.6 wide, rungs every 0.3 m from +0.5 to -3.5
    for z in [CHAN_D + 0.5 - 0.3 * k for k in range(14)]:
        ubox(L1 + 1.0, hw - 0.12, z, 0.6, 0.05, 0.05, "grey")
    for dy in (-0.3, 0.3):
        ubox(L1 + 1.0 + dy, hw - 0.12, CHAN_D - 1.5, 0.05, 0.05, 4.4, "grey")
    ubox(L1 + 0.5, hw - 0.3, CHAN_D + 0.05, 1.0, 0.6, 0.08, "hazard")        # the hazard edge at the drop
    ubox(L1 + 0.5, -0.3, CHAN_D - 0.2, 1.0, 5.0, 0.08, "hazard")


def part_shaft_slab():
    """the drop shaft's floor at the LOWER invert: 2.56 x the outer width x 0.5, top at z = 0"""
    both(ubox, 0, 0, -0.25, 2.56, CW + 2 * WALL, 0.5, "steel")


def part_junction():
    """768 x 768 x 448 room, the floor at the invert (z = 0), openings 384 x 345 centred on the entry (-X) and the
    exit (+X) face, a 2 x 2 grate hole in the roof with a 3 m shaft above it (the street grate's light shaft)."""
    L, W, H = JUN
    hw = W / 2
    room_openings(L, W, H, ((0.0, True), (L, True)), floor_z=0.0, mat="steel")
    hole = 1.0
    ubox(L / 2, 0, H + 1.5, 2.0 + 2 * WALL, 2.0 + 2 * WALL, 3.0, "steel")
    ubox(L / 2, 0, H + 1.5, 2.0, 2.0, 3.2, "soot")                          # the shaft's dark inside
    ubox(L / 2, 0, H + 3.0, 2.2, 2.2, 0.12, "hazard")                       # the grate frame above (a rim)
    for k in range(5):
        ubox(L / 2, -0.8 + 0.4 * k, H + 3.0, 2.0, 0.08, 0.06, "charcoal")
    for s in (-1, 1):                                                       # pipes along one wall, a valve stand
        ubox(L * 0.6, s * (hw - 0.5), 2.2, L * 0.5, 0.3, 0.3, "brown")
    ubox(L * 0.3, hw - 0.9, 0.6, 1.2, 1.2, 1.2, "steel")
    ubox(L * 0.3, hw - 0.9, 1.3, 0.6, 0.6, 0.2, "hazard")                   # the valve wheel (a moving machine)


def room_openings(L, W, H, ends, floor_z=0.0, mat="steel", end_w=CW, end_h=CHAN_D + CH):
    """a hollow box room from x = 0..L, y = -W/2..W/2, floor at floor_z, interior height H; ends = ((x, open), ...)
    for the two end walls, open = a centred end_w x end_h opening with pier + lintel hulls"""
    hw = W / 2
    both(prism, 0, L, -hw - WALL, hw + WALL, floor_z - WALL, floor_z, "steel")
    both(prism, 0, L, -hw - WALL, hw + WALL, floor_z + H, floor_z + H + WALL, "charcoal")
    for s in (-1, 1):
        y0, y1 = (hw, hw + WALL) if s > 0 else (-hw - WALL, -hw)
        both(prism, 0, L, y0, y1, floor_z - WALL, floor_z + H + WALL, mat)
        prism(0, L, (hw if s > 0 else -hw) - s * 0.02, (hw if s > 0 else -hw) + s * 0.01, floor_z + 0.8, floor_z + 1.2, "brown")
    for x, is_open in ends:
        x0, x1 = (x, x + WALL) if x > 0 else (x - WALL, x)
        if not is_open:
            both(prism, x0, x1, -hw - WALL, hw + WALL, floor_z - WALL, floor_z + H + WALL, mat)
            continue
        ow = end_w / 2
        both(prism, x0, x1, -hw - WALL, -ow, floor_z - WALL, floor_z + H + WALL, mat)
        both(prism, x0, x1, ow, hw + WALL, floor_z - WALL, floor_z + H + WALL, mat)
        both(prism, x0, x1, -ow, ow, floor_z + end_h, floor_z + H + WALL, mat)
        prism(x0 - 0.05 if x > 0 else x1 - 0.1, x0 + 0.1 if x > 0 else x1 + 0.05, -ow - 0.2, ow + 0.2, floor_z + end_h, floor_z + end_h + 0.3, "hazard")   # the opening's head edge


def part_gallery():
    """the sluice gallery 1536 x 768 x 448: the floor at the invert, both ends open 384 x 345 (the grate mover at
    the entry and the sluice gate at the exit are the importer's), a raised dry walk of 2.56 m along the +Y wall, a
    hazard frame round the exit. Pillars are B_pillar (8, placed by story_export)."""
    L, W, H = GAL
    room_openings(L, W, H, ((0.0, True), (L, True)), mat="steel")
    both(prism, 0.3, L - 0.3, W / 2 - 2.56, W / 2, 0.0, CHAN_D, "grey")          # the dry walk, 25 UU up
    for k in range(6):                                                           # the six lamp brackets, +Y wall
        x = 3.0 + k * (L - 6.0) / 5
        ubox(x, W / 2 - 0.2, 5.0, 0.3, 0.4, 0.2, "grey")
        ubox(x, W / 2 - 0.35, 4.85, 0.5, 0.25, 0.12, "glow")
    for s in (-1, 1):                                                           # hazard stripes at the sluice end
        for k in range(4):
            ubox(L - 0.02, s * (CW / 2 + 0.35), CHAN_D + 0.5 + k * 1.5, 0.05, 0.5, 0.75, "hazard" if k % 2 else "charcoal")
    ubox(L - 0.3, 0, CHAN_D + CH + 0.9, 0.3, 1.0, 0.5, "rustred")                # the beacon housing over the gate


def part_pillar():
    """2 x 4 x 8.96 m chamfered pillar, the tide band at 1 m"""
    both(ubox, 0, 0, GAL[2] / 2, 4.0, 2.0, GAL[2], "steel")
    ubox(0, 0, GAL[2] / 2, 4.0 + 0.2, 2.0 - 0.6, GAL[2] - 0.6, "grey")
    ubox(0, 0, GAL[2] / 2, 4.0 - 0.6, 2.0 + 0.2, GAL[2] - 0.6, "grey")
    ubox(0, 0, 1.0, 4.04, 2.04, 0.4, "brown")


def part_outfall():
    """the mouth: 2.56 m of culvert, a headwall with 3 m wing walls at 45 degrees, a parapet, and a bar grate with
    three bars torn out on the ledge side (a 2.3 m gap: the way through)"""
    hw = CW / 2
    tube(-1.28, 1.28)
    top = CHAN_D + CH + WALL
    for s in (-1, 1):                                                           # wing walls
        both(ubox, 1.28 + 1.06, s * (hw + WALL + 1.06), top / 2 - WALL, 3.0, 0.5, top + 0.5, "steel", yaw=s * 45)
    both(ubox, 1.0, 0, top + 0.25, 0.56, CW + 2 * WALL + 1.0, 0.5, "grey")       # parapet
    n = 12
    for k in range(n):
        y = -hw + (k + 0.5) * CW / n
        if k >= n - 4 and k < n - 1:                                            # torn: bent bars lying in the channel
            ubox(1.28 + 0.8, y - 0.2, 0.4, 1.8, 0.12, 0.12, "brown", pitch=20)
            continue
        both(ubox, 1.28, y, CHAN_D / 2 + CH / 2, 0.12, 0.12, CHAN_D + CH, "charcoal")
    ubox(1.28, 0, CHAN_D + CH - 0.2, 0.14, CW, 0.14, "charcoal")
    ubox(1.28, 0, 2.0, 0.14, CW, 0.14, "charcoal")


def part_drain_stair(depth=7.4):
    """the dorm-square entrance: a stair down a walled trench to the culvert's invert. Authored origin = the bottom
    landing's centre at the culvert's entry face (z = 0 = the invert); the stair climbs toward -X. 17 risers of
    0.435 m (21.8 UU; still 35 UU at DrawScale3D Z 1.6 = 11.8 m deep), treads 0.6, 2.56 wide between 0.3 walls.
    NEEDS A TERRAIN HOLE: the trench's plan is x = -12.8..0, y = +-1.58 (see STORY_ASSETS.md)."""
    n = 17
    riser, tread = depth / n, 0.6
    w = 2.56
    both(ubox, -1.0, 0, -0.15, 2.0, w, 0.3, "grey")                              # the bottom landing
    for k in range(n):
        x = -2.0 - (k + 0.5) * tread
        z = (k + 1) * riser
        both(ubox, x, 0, z / 2, tread, w, z, "grey")
        ubox(x + tread / 2 - 0.05, 0, z - 0.02, 0.1, w, 0.04, "hazard")           # hazard nosing
    run = 2.0 + n * tread
    both(ubox, -run - 0.75, 0, depth - 0.15, 1.5, w, 0.3, "grey")                 # the top landing at ground
    for s in (-1, 1):                                                            # trench walls, full height
        both(ubox, -(run + 1.5) / 2, s * (w / 2 + 0.15), depth / 2 + 0.3, run + 1.5, 0.3, depth + 0.6, "steel")
    both(ubox, -run - 1.5 - 0.15, 0, depth / 2 + 0.3, 0.3, w + 0.6, depth + 0.6, "steel")   # the end wall
    ubox(-(run + 1.5) / 2, 0, depth + 0.5, run + 1.5, w + 0.6, 0.2, "grey")        # the kerb at ground level
    for z in (0.55, 1.1):                                                         # a rail on the right cheek
        ubox(-run / 2 - 1.0, w / 2 - 0.1, depth + z, run, 0.06, 0.06, "hazard")
    return {"run": run + 1.5, "depth": depth}


def part_drain_hatch(depth=7.4):
    """the alternative entrance: a 2.56 square ladder shaft from the invert up to the ground (DrawScale3D Z =
    depth / 7.4), a hatch collar on top. Needs the same terrain hole (2.56 + 0.6 square)."""
    w = 2.56
    for s in (-1, 1):
        both(ubox, 0, s * (w / 2 + 0.15), depth / 2, w + 0.6, 0.3, depth, "steel")
        both(ubox, s * (w / 2 + 0.15), 0, depth / 2, 0.3, w, depth, "steel")
    for z in [0.5 + 0.3 * k for k in range(int(depth / 0.3))]:
        ubox(-w / 2 + 0.15, 0, z, 0.05, 0.6, 0.05, "grey")
    ubox(0, 0, depth + 0.15, w + 0.9, w + 0.9, 0.3, "grey")
    ubox(0, 0, depth + 0.35, w, w, 0.1, "hazard")                                # the hatch rim


# --- the taps ----------------------------------------------------------------------------------------------------
def part_pole(variant):
    """crooked improvised poles, the hook point at 5.5 m (takes.POLE_H_M): a = scaffold tube leaning 6 deg with a
    crossarm, b = a timber on a drum foot, c = a dead lamp post with a broken head. ~4-6 m."""
    if variant == "a":
        lean = 6.0
        h = 5.6
        ubox(h / 2 * math.sin(math.radians(lean)), 0, h / 2, 0.12, 0.12, h, "grey", pitch=-lean)
        ubox(h * math.sin(math.radians(lean)), 0, 5.4, 0.08, 1.2, 0.08, "steel")
        ubox(0.6, 0, 0.9, 0.08, 0.08, 2.0, "grey", pitch=40)                     # a prop stick
        ubox(0, 0, 0.1, 0.5, 0.5, 0.2, "brown")
    elif variant == "b":
        _cyl_u(0, 0, 0.45, 0.3, 0.9, "rustred", 12)                              # the drum foot
        h = 4.9
        ubox(0, 0.1, 0.9 + h / 2 - 0.2, 0.18, 0.14, h, "brown", pitch=-3)
        ubox(0, 0, 5.45, 0.06, 0.9, 0.06, "steel")
        ubox(0, 0.4, 5.5, 0.12, 0.12, 0.3, "charcoal")                           # the insulator
    else:
        lean = -4.0
        h = 6.0
        ubox(h / 2 * math.sin(math.radians(lean)), 0, h / 2, 0.16, 0.16, h, "steel", pitch=-lean)
        ubox(h * math.sin(math.radians(lean)) + 0.4, 0, 6.0, 0.9, 0.14, 0.14, "steel", pitch=15)
        ubox(h * math.sin(math.radians(lean)) + 0.8, 0, 5.85, 0.3, 0.3, 0.25, "soot")       # the dead (burnt-out) head
        ubox(5.5 * math.sin(math.radians(lean)) + 0.1, 0, 5.5, 0.4, 0.08, 0.08, "hazard")     # the hook bracket
        ubox(0, 0, 0.2, 0.6, 0.6, 0.4, "grey")


def _cyl_u(X, Y, Z, r, h, m, n=12):
    x, y, z = U(X, Y, Z)
    return _cyl(x, y, z, r, h, m, n)


def part_sagcable(span=10.0, sag=0.6, n=16):
    """a sagging cable: unit span 10 m along +X from the origin, both ends at z = 0, a parabola 0.6 m deep at the
    middle; cross-section 0.08 x 0.04 so DrawScale3D (X = span / 10 m, Z = sag / 0.6) keeps it thin"""
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        z0, z1 = -4 * sag * t0 * (1 - t0), -4 * sag * t1 * (1 - t1)
        x0, x1 = t0 * span, t1 * span
        L = math.hypot(x1 - x0, z1 - z0)
        pitch = math.degrees(math.atan2(z1 - z0, x1 - x0))
        ubox((x0 + x1) / 2, 0, (z0 + z1) / 2, L + 0.02, 0.08, 0.04, "charcoal", pitch=pitch)


def part_drum():
    """an oil drum 0.6 dia x 0.9 with a hose coil on top; water store for the hose taps"""
    _cyl_u(0, 0, 0.45, 0.3, 0.9, "rustred", 12)
    _cyl_u(0, 0, 0.2, 0.31, 0.04, "grey", 12)
    _cyl_u(0, 0, 0.7, 0.31, 0.04, "grey", 12)
    _cyl_u(0, 0, 0.93, 0.22, 0.08, "charcoal", 10)
    ubox(0.3, 0.2, 0.2, 0.9, 0.08, 0.08, "charcoal", yaw=30)


def part_hose():
    """10 m of garden hose lying on the ground along +X (DrawScale3D X = length / 10 m), 0.1 dia, with a wobble"""
    pts = [(k * 1.0, 0.12 * math.sin(k * 1.3)) for k in range(11)]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        ubox((x0 + x1) / 2, (y0 + y1) / 2, 0.05, L + 0.04, 0.1, 0.1, "charcoal", yaw=math.degrees(math.atan2(y1 - y0, x1 - x0)))


# --- the hollow-shell kit ----------------------------------------------------------------------------------------
STOREY = 3.4
T = 0.3                       # wall and slab thickness, 15 UU
DOOR_P = (2.0, 2.8)           # personnel 100 x 140 UU (importer: >= 96 wide, >= 120 high)
DOOR_M = (2.56, 3.84)         # main / Skaarj 128 x 192
DOOR_R = (5.0, 5.0)           # roller 250 x 250


def panel(w, h, m="charcoal", band=True):
    """a wall panel w long (X), T thick (Y), h high, origin at the bottom centre; the outside is -Y (a dirt band
    at the foot and a grey trim at the top on that face)"""
    both(ubox, 0, 0, h / 2, w, T, h, m)
    if band:
        ubox(0, -T / 2 - 0.01, 0.5, w, 0.02, 1.0, "brown")
        ubox(0, -T / 2 - 0.01, h - 0.2, w, 0.02, 0.4, "grey")


def panel_door(w, h, dw, dh, m="charcoal"):
    """a panel with a centred dw x dh opening: hulls per pier and the lintel"""
    pw = (w - dw) / 2
    for s in (-1, 1):
        both(ubox, s * (dw / 2 + pw / 2), 0, h / 2, pw, T, h, m)
        ubox(s * (dw / 2 + pw / 2), -T / 2 - 0.01, 0.5, pw, 0.02, 1.0, "brown")
    both(ubox, 0, 0, dh + (h - dh) / 2, dw + 0.02, T, h - dh, m)
    ubox(0, -T / 2 - 0.01, h - 0.2, w, 0.02, 0.4, "grey")


def panel_window(w=4.0, h=STOREY, ww=3.2, z0=2.0, z1=2.9, m="charcoal"):
    """a panel with a window strip opening (ww x 0.9 at 2.0..2.9 m), two mullions and a sill"""
    pw = (w - ww) / 2
    for s in (-1, 1):
        both(ubox, s * (ww / 2 + pw / 2), 0, h / 2, pw, T, h, m)
    both(ubox, 0, 0, z0 / 2, ww + 0.02, T, z0, m)
    both(ubox, 0, 0, z1 + (h - z1) / 2, ww + 0.02, T, h - z1, m)
    ubox(0, -T / 2 - 0.01, 0.5, w, 0.02, 1.0, "brown")
    ubox(0, 0, z0 + 0.03, ww + 0.1, T + 0.08, 0.06, "grey")
    for x in (-ww / 6, ww / 6):
        ubox(x, 0, (z0 + z1) / 2, 0.08, T - 0.1, z1 - z0, "grey")


def part_frame(dw, dh, m="orange"):
    """a door frame round a dw x dh opening: 0.15 members, 0.4 deep, standing on the floor at the wall line.
    orange = the company's frame colour; slate = the Authority's, with its one cold (cyan) indicator strip over
    the lintel (artist s. 1.1: a single cyan window strip is the Authority's motif)"""
    for s in (-1, 1):
        ubox(s * (dw / 2 + 0.075), 0, dh / 2, 0.15, 0.4, dh, m)
    ubox(0, 0, dh + 0.075, dw + 0.3, 0.4, 0.15, m)
    ubox(0, -0.25, 0.02, dw, 0.1, 0.04, "grey")                                 # the threshold
    if m == "slate":
        ubox(0, -0.21, dh + 0.075, 0.6, 0.02, 0.08, "cyan")


def part_column():
    both(ubox, 0, 0, STOREY / 2, 0.4, 0.4, STOREY, "steel")
    ubox(0, 0, 0.2, 0.46, 0.46, 0.4, "brown")


def part_slab(th=T, m="grey", grating=False):
    """4 x 4 slab whose TOP is z = 0 (place at the floor level; thickness th below it)"""
    both(ubox, 0, 0, -th / 2, 4.0, 4.0, th, m)
    if grating:
        for k in range(10):
            ubox(0, -1.8 + k * 0.4, 0.01, 4.0, 0.12, 0.02, "charcoal")


def part_rail(L=4.0):
    """a rail L long along X on the line y = 0: posts 1.5 m, top rail 1.1 (55 UU), mid rail 0.55, toe board 0.15
    hazard; one thin hull so the player can't walk off"""
    for x in (-L / 2 + 0.05, 0, L / 2 - 0.05):
        ubox(x, 0, 0.55, 0.06, 0.06, 1.1, "steel")
    ubox(0, 0, 1.1, L, 0.06, 0.06, "hazard")
    ubox(0, 0, 0.55, L, 0.05, 0.05, "steel")
    ubox(0, 0, 0.075, L, 0.04, 0.15, "hazard")
    ubox(0, 0, 0.55, L, 0.06, 1.1, "steel", hull=True)


def part_catwalk(L=4.0, w=1.6):
    """grating L x w (top at z = 0.1, the pivot at the grating's underside... no: z = 0 is the WALK SURFACE, the
    grating 0.1 below) with rails on both sides"""
    both(ubox, 0, 0, -0.05, L, w, 0.1, "charcoal")
    for k in range(10):
        ubox(0, -w / 2 + (k + 0.5) * w / 10, 0.005, L, 0.05, 0.01, "grey")
    for s in (-1, 1):
        for x in (-L / 2 + 0.05, 0, L / 2 - 0.05):
            ubox(x, s * (w / 2 - 0.03), 0.55, 0.06, 0.06, 1.1, "steel")
        ubox(0, s * (w / 2 - 0.03), 1.1, L, 0.06, 0.06, "hazard")
        ubox(0, s * (w / 2 - 0.03), 0.55, L, 0.05, 0.05, "steel")
        ubox(0, s * (w / 2 - 0.03), 0.075, L, 0.04, 0.15, "hazard")
        ubox(0, s * (w / 2 - 0.03), 0.55, L, 0.06, 1.1, "steel", hull=True)


def part_step():
    """one stair step: tread 0.56 (X) x 1.6 wide (Y) x 0.68 high (34 UU) block, origin at its bottom back... the
    bottom centre; shells.py places N of them with DrawScale3D Z = riser / 0.68 and Y = width / 1.6"""
    both(ubox, 0, 0, 0.34, 0.56, 1.6, 0.68, "grey")
    ubox(-0.24, 0, 0.67, 0.08, 1.6, 0.03, "hazard")                            # the nosing


def part_ladder(h=STOREY):
    """0.6 wide ladder h tall (DrawScale3D Z), rungs every 0.3, a cage from 2.2 m up; decoration (no hull)"""
    for dy in (-0.3, 0.3):
        ubox(0, dy, h / 2, 0.05, 0.05, h, "grey")
    for z in [0.3 * k for k in range(1, int(h / 0.3))]:
        ubox(0, 0, z, 0.04, 0.6, 0.04, "grey")
    for z in (2.2, 2.8, 3.3):
        if z < h:
            ubox(0.35, 0, z, 0.7, 0.9, 0.04, "steel")
            ubox(0.7, 0, z + 0.1, 0.04, 0.9, 0.04, "steel")


def part_plinth():
    """4 m of battered plinth, 1.2 m high, 0.8 thick at the foot and 0.4 at the top; the TOP is z = 0 (place at the
    floor level, DrawScale3D Z for deeper ground); the outside is -Y"""
    P = [(-2.0, -0.8, -1.2), (-2.0, 0.0, -1.2), (-2.0, 0.0, 0.0), (-2.0, -0.4, 0.0),
         (2.0, -0.8, -1.2), (2.0, 0.0, -1.2), (2.0, 0.0, 0.0), (2.0, -0.4, 0.0)]
    hexa(P, "charcoal")
    hexa(P, hull=True)
    ubox(0, -0.42, -0.05, 4.0, 0.08, 0.1, "grey")


# --- the process parts the binder commit 10829b6 asked for (D7-D10) ---------------------------------------------
def part_headframe():
    """mine portal: an 8 x 8 arch (2 m piers, a 1.5 m lintel, the dark inside, hazard stripes, rails out) under a
    24 m A-frame headframe with the sheave wheel; footprint 8 x 8 (the legs straddle the portal)"""
    for s in (-1, 1):
        both(ubox, 0, s * 3.0, 4.0, 3.0, 2.0, 8.0, "steel")                         # piers
        for k in range(4):
            ubox(1.52, s * 3.0, 0.6 + k * 1.2, 0.05, 2.0, 0.6, "hazard" if k % 2 else "charcoal")
    both(ubox, 0, 0, 8.75, 3.0, 8.0, 1.5, "steel")                                   # lintel
    ubox(-1.4, 0, 4.0, 0.2, 4.0, 8.0, "soot")                                         # the dark inside
    ubox(-1.5, 0, 9.5, 2.6, 8.4, 0.3, "grey")
    for s in (-1, 1):                                                                # the A-frame legs, leaning in
        ubox(s * 1.6, 0, 12.0, 0.5, 0.5, 24.5, "charcoal", pitch=s * 8.0)
        ubox(0, s * 1.6, 12.0, 0.5, 0.5, 24.5, "charcoal", yaw=90, pitch=s * 8.0)
    for z in (6.0, 12.0, 18.0):
        ubox(0, 0, z, 3.4 - z * 0.1, 0.2, 0.2, "grey")
        ubox(0, 0, z, 0.2, 3.4 - z * 0.1, 0.2, "grey")
    ubox(0, 0, 23.0, 2.2, 2.2, 1.2, "grey")                                           # the head
    _cyl_u(0, 0, 24.2, 1.1, 0.3, "rustred", 16, )
    ubox(0, 0, 24.4, 0.3, 0.3, 0.4, "rustred")                                      # the aviation lamp stub
    for s in (-1, 1):                                                                # rails out of the portal
        ubox(5.0, s * 0.7, 0.08, 8.0, 0.12, 0.16, "grey")


def part_transfer_tower():
    """6 x 6 x 14 square transfer tower: corner columns, steel panels, an open top deck with rails, a head house,
    the chute out of the +X face sloping to the ground"""
    for sx in (-1, 1):
        for sy in (-1, 1):
            ubox(sx * 2.8, sy * 2.8, 7.0, 0.4, 0.4, 14.0, "charcoal")
    for s in (-1, 1):
        both(ubox, s * 2.85, 0, 6.0, 0.3, 6.0, 12.0, "steel")
        both(ubox, 0, s * 2.85, 6.0, 6.0, 0.3, 12.0, "steel")
        ubox(s * 3.01, 0, 0.5, 0.02, 6.0, 1.0, "brown")
    both(ubox, 0, 0, 11.85, 6.0, 6.0, 0.3, "grey")                                   # the deck at 12 m
    for s in (-1, 1):
        ubox(s * 2.9, 0, 12.55, 0.06, 6.0, 0.06, "hazard")
        ubox(0, s * 2.9, 12.55, 6.0, 0.06, 0.06, "hazard")
        ubox(s * 2.9, 0, 12.0, 0.06, 6.0, 1.1, "steel", hull=True)
        ubox(0, s * 2.9, 12.0, 6.0, 0.06, 1.1, "steel", hull=True)
    ubox(-1.0, 0, 13.0, 3.0, 3.0, 2.0, "rustred")                                     # the head house
    ubox(4.5, 0, 6.5, 6.5, 1.2, 1.0, "rustred", pitch=-50)                            # the chute, down the +X face
    ubox(3.4, 0, 1.5, 1.2, 1.2, 3.0, "soot")                                         # the chute mouth, sooted
    ubox(0, 0, 0.3, 6.6, 6.6, 0.6, "grey")                                           # the footing


def part_thickener():
    """thickener ring 16 m across, 4 m high: the wall, the slurry surface, the centre column, a rake bridge across
    the top with rails (walkable: a hull), the rake arms below"""
    _cyl_u(0, 0, 2.0, 8.0, 4.0, "grey", 24)
    _cyl_u(0, 0, 2.0, 7.6, 4.1, "charcoal", 24)
    _cyl_u(0, 0, 3.6, 7.5, 0.1, "brown", 24)
    _cyl_u(0, 0, 2.5, 0.5, 5.0, "steel", 12)
    both(ubox, 0, 0, 4.45, 17.0, 1.2, 0.3, "grey")                                    # the bridge, hull = walkable
    for s in (-1, 1):
        ubox(0, s * 0.55, 5.15, 17.0, 0.06, 0.06, "hazard")
        ubox(0, s * 0.55, 4.6, 17.0, 0.06, 1.1, "steel", hull=True)
    for k in range(8):                                                               # the wall as 8 hull pieces
        a = k * math.pi / 4
        ubox(7.8 * math.cos(a), 7.8 * math.sin(a), 2.0, 0.5, 6.3, 4.0, "grey", yaw=math.degrees(a) + 90, hull=True)
    ubox(0, 0, 1.5, 14.0, 0.4, 0.3, "steel")                                         # the rake arms
    ubox(0, 0, 1.5, 0.4, 14.0, 0.3, "steel")
    for s in (-1, 1):                                                                # the launder outlet, a pipe
        ubox(s * 8.3, 0, 3.5, 0.6, 0.6, 1.0, "rustred")


def part_shiploader():
    """pier 30 x 6 at 3 m on piles, a conveyor along it, a 12 m gantry at the sea end and a 25 m boom out over
    the water (pitch 10 deg); origin at the shore end, +X toward the sea"""
    both(ubox, 15.0, 0, 2.85, 30.0, 6.0, 0.3, "grey")
    for k in range(6):
        for s in (-1, 1):
            _cyl_u(2.5 + k * 5.0, s * 2.4, 1.4, 0.3, 2.9, "charcoal", 8)
    for s in (-1, 1):
        ubox(15.0, s * 2.9, 3.55, 30.0, 0.06, 0.06, "hazard")
        ubox(15.0, s * 2.9, 3.0, 30.0, 0.06, 1.1, "steel", hull=True)
    ubox(15.0, -1.5, 3.6, 30.0, 1.2, 0.5, "charcoal")                                 # the conveyor
    for s in (-1, 1):                                                                # the gantry at the sea end
        ubox(27.0, s * 2.5, 9.0, 0.6, 0.6, 12.0, "charcoal")
    ubox(27.0, 0, 15.0, 1.2, 6.0, 1.2, "charcoal")
    ubox(27.0 + 11.5, 0, 15.6 + 2.1, 25.0, 1.4, 1.2, "rustred", pitch=10)              # the boom
    ubox(27.0 + 24.0, 0, 15.6 + 4.2 - 1.5, 1.0, 1.0, 3.0, "charcoal")                 # the spout
    ubox(27.0, 0, 16.0, 1.0, 1.0, 0.8, "rustred")                                     # the aviation lamp


PARTS = {
    # the drain
    "B_culvert": part_culvert, "B_culvert_bendP": lambda: part_culvert_bend(+1), "B_culvert_bendN": lambda: part_culvert_bend(-1),
    "B_culvert_drop": part_culvert_drop, "B_shaft_slab": part_shaft_slab, "B_junction": part_junction,
    "B_gallery": part_gallery, "B_pillar": part_pillar, "B_outfall": part_outfall,
    "B_drain_stair": part_drain_stair, "B_drain_hatch": part_drain_hatch,
    # the taps
    "B_pole_a": lambda: part_pole("a"), "B_pole_b": lambda: part_pole("b"), "B_pole_c": lambda: part_pole("c"),
    "B_sagcable": part_sagcable, "B_drum": part_drum, "B_hose": part_hose,
    # the hollow-shell kit
    "B_k_wall": lambda: panel(4.0, STOREY), "B_k_wall_in": lambda: panel(4.0, STOREY, "steel", band=False),
    "B_k_wall_door": lambda: panel_door(4.0, STOREY, *DOOR_P), "B_k_wall_door_in": lambda: panel_door(4.0, STOREY, *DOOR_P, "steel"),
    "B_k_wall_main": lambda: panel_door(4.0, 4.4, *DOOR_M), "B_k_wall_roller": lambda: panel_door(6.0, 6.0, *DOOR_R),
    "B_k_wall_win": lambda: panel_window(), "B_k_column": part_column,
    "B_k_slab": lambda: part_slab(), "B_k_grating": lambda: part_slab(0.1, "charcoal", True),
    "B_k_rail": part_rail, "B_k_catwalk": part_catwalk, "B_k_step": part_step, "B_k_ladder": part_ladder,
    "B_k_frame_p": lambda: part_frame(*DOOR_P), "B_k_frame_m": lambda: part_frame(*DOOR_M),
    "B_k_frame_p_auth": lambda: part_frame(*DOOR_P, "slate"), "B_k_plinth": part_plinth,
    # the process parts (binder D7-D10)
    "B_headframe": part_headframe, "B_transfer_tower": part_transfer_tower, "B_thickener": part_thickener, "B_shiploader": part_shiploader,
}


def dump_tris(path):
    """every render mesh's triangles (Unreal frame, metres) + colour for the CPU contact sheet (kit_sheet.py)"""
    out = []
    bpy.context.view_layer.update()            # ob.scale / rotation set from Python reach matrix_world only after this
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob.name.startswith("MCDCX"):
            continue
        me = ob.data
        me.calc_loop_triangles()
        M = ob.matrix_world
        col = (0.5, 0.5, 0.5)
        if me.materials and me.materials[0]:
            n = me.materials[0].node_tree.nodes.get("Principled BSDF")
            if n:
                col = tuple(n.inputs["Base Color"].default_value[:3])
        for t in me.loop_triangles:
            vs = [tuple(M @ me.vertices[i].co) for i in t.vertices]
            out.append([[(-v[1], v[0], v[2]) for v in vs], col])      # Blender -> Unreal (X = -y_b, Y = x_b)
    json.dump(out, open(path, "w"))


def build_all(out, only, box, cyl, mat):
    global _box, _cyl, _mat
    _box, _cyl, _mat = box, cyl, mat
    piv_path = os.path.join(out, "kit_pivots.json")
    pivots = json.load(open(piv_path)) if os.path.exists(piv_path) else {}
    tri_dir = os.path.join(out, "kit_tris")
    os.makedirs(tri_dir, exist_ok=True)
    for name, fn in PARTS.items():
        if only and name not in only and "kit" not in only:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        # build_parts' MATS cache belongs to the old scene: clear it through mat()'s module
        import sys
        sys.modules["__main__"].MATS.clear()
        info = fn() or {}
        bpy.context.view_layer.update()
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("MCDCX")]
        lo = [min(min((o.matrix_world @ v.co)[k] for v in o.data.vertices) for o in meshes) for k in range(3)]
        hi = [max(max((o.matrix_world @ v.co)[k] for v in o.data.vertices) for o in meshes) for k in range(3)]
        cxb, cyb = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        # the authored origin's offset from the bounds centre, in Unreal metres: X = -y_b, Y = x_b
        # the bounds centre in Unreal metres is (-cyb, cxb); the authored origin seen from it is (cyb, -cxb)
        pivots[name] = dict(info, dx=round(cyb, 3), dy=round(-cxb, 3),
                            size=[round(hi[1] - lo[1], 3), round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3)],
                            zmin=round(lo[2], 3), zmax=round(hi[2], 3),
                            hulls=sum(1 for o in bpy.context.scene.objects if o.name.startswith("MCDCX")))
        dump_tris(os.path.join(tri_dir, name + ".json"))
        for ob in bpy.context.scene.objects:
            ob.select_set(ob.type == "MESH")
        bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), use_selection=True, export_format="GLB", export_apply=True)
        print("BUILT", name, "size", pivots[name]["size"], "hulls", pivots[name]["hulls"], "origin-from-centre", pivots[name]["dx"], pivots[name]["dy"])
    json.dump(pivots, open(piv_path, "w"), indent=1)
