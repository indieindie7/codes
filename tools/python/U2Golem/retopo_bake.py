"""Game mesh from an AI high-poly character: shape-driven low-poly per body section, clean UVs, baked maps.

Run:  blender -b <painted_high.blend> --python retopo_bake.py -- <out_prefix> [method=tube|decimate]
      [size=2048] [detail=1.0] [tris=3000] [ao=0.85] [samples=32] [low=<lowpoly.glb>] [high=<textured.glb>] [cage=] [extra=Trust] [albedo=<png>] [cpu=1]
<painted_high.blend> is project_views.py output: one A-pose mesh (front = -Y, up = +Z) with the
"Col" vertex colour. Use the true high-poly (img2shape_mv.py faces=0), not a reduced one.

method=tube (the poly-modelling way: sections built from simple tubes, edges where the shape needs them)
  1. Sections: the surface is sliced by height; in each slice the piece around the centre line is the
     core (head / torso / legs) and the pieces beside it are the arms. Crotch, armpit and neck are read
     from where those pieces split and merge; the hand is cut off at the wrist (the arm's thinnest place).
  2. Each section becomes a tube: candidate rings along its axis are cast onto the high-poly from the
     outside in, then only the rings that matter are kept (greedy: add the ring whose absence changes the
     shape most), so loops land on armour steps and silhouette changes instead of at even spacing.
     Hands are too branched for a tube and are decimated instead.
  3. UVs are laid out analytically: every tube is one rectangle (around x along), seam on its hidden
     side, scaled to its real size, then packed.
method=decimate: Blender's Decimate (collapse) to `tris` + angle-based UVs. The "just decimate" baseline.
high=<glb>: use this textured mesh as the high-poly (no .blend needed); its texture is the colour source.
low=<glb>: no retopo; bake onto this finished low-poly and its UVs (sheet_model.py output, with the blend
  being its painted copy from project_views.py).

Bakes high -> low (Cycles, selected to active): tangent normal map, ambient occlusion, colour ("Col").
Writes <out>_albedo.png, <out>_ao.png, <out>_normal.png, <out>_diffuse.png (albedo x AO, the texture
for engines without normal maps), <out>.blend, <out>.glb and <out>.png (textured row + wireframe row).
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(args[0]))[0]
o = dict(a.split("=", 1) for a in args[1:])
METHOD = o.get("method", "tube")
SIZE = int(o.get("size", 2048))
DETAIL = float(o.get("detail", 1.0))
TRIS = int(o.get("tris", 3000))
AO_STRENGTH = float(o.get("ao", 0.85))
SAMPLES = int(o.get("samples", 32))

if o.get("high"):
    # a textured high-poly given as a file (Hunyuan3D-Paint output) instead of a painted .blend
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=o["high"])
    ms = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for ob in ms:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    ms[0].data.transform(ms[0].matrix_world)
    ms[0].matrix_world.identity()
    for ob in [x for x in bpy.context.scene.objects if x.type != "MESH"]:
        bpy.data.objects.remove(ob, do_unlink=True)
hi = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"][0]
hi.name = "High"
me = hi.data
me.calc_loop_triangles()
V = np.array([tuple(v.co) for v in me.vertices])
T = np.array([tuple(t.vertices) for t in me.loop_triangles])
lo3, hi3 = V.min(0), V.max(0)
H = float(hi3[2] - lo3[2])
print(f"HIGH {len(V)} verts {len(T)} tris, height {H:.3f}")


# --------------------------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------------------------
def surface_samples(n):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(0)
    f = rng.choice(len(T), n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    return a[f] + (b[f] - a[f]) * u[:, None] + (c[f] - a[f]) * v[:, None]


def find_sections():
    """Landmarks from slice clusters. Returns a function point -> label and the landmark dict."""
    S = surface_samples(600000)
    cx = float(np.median(S[:, 0]))
    NZ = 200
    dz = H / NZ
    gap = 0.012 * H
    zc = lo3[2] + (np.arange(NZ) + 0.5) * dz
    idx = np.clip(((S[:, 2] - lo3[2]) / dz).astype(int), 0, NZ - 1)
    order = np.argsort(idx, kind="stable")
    bounds = np.searchsorted(idx[order], np.arange(NZ + 1))
    clusters = []
    for i in range(NZ):
        xs = np.sort(S[order[bounds[i]:bounds[i + 1]], 0])
        if len(xs) < 8:
            clusters.append([])
            continue
        cut = np.where(np.diff(xs) > gap)[0]
        st = np.concatenate([[0], cut + 1])
        en = np.concatenate([cut, [len(xs) - 1]])
        clusters.append([(xs[a], xs[b]) for a, b in zip(st, en) if b - a >= 6])

    def core(i):
        for c in clusters[i]:
            if c[0] <= cx <= c[1]:
                return c
        return None

    # crotch: lowest slice (above the shins) whose core piece spans the centre line
    crotch_i = next(i for i in range(int(0.25 * NZ), NZ) if core(i) is not None)
    # armpit: highest slice above the crotch where the arms are still separate pieces beside the core
    armpit_i = crotch_i
    for i in range(crotch_i, int(0.92 * NZ)):
        c = core(i)
        if c is not None and any(k[1] < c[0] for k in clusters[i]) and any(k[0] > c[1] for k in clusters[i]):
            armpit_i = i
    c = core(armpit_i)
    xl, xr = c[0], c[1]                       # vertical shoulder cuts, used where the arm is fused on
    # inner edge of each arm per slice up to the armpit. Known where the arm (or hand) is its own piece;
    # where it touches the body (forearm on the hip) the edge is interpolated between the known slices.
    kn_l, kn_r = {}, {}
    for i in range(armpit_i + 1):
        c = core(i)
        ls = sorted(k for k in clusters[i] if k[1] < (c[0] if c else cx))
        rs = sorted(k for k in clusters[i] if k[0] > (c[1] if c else cx))
        if c is None:                         # legs apart: the innermost piece on each side is the leg
            ls, rs = ls[:-1], rs[1:]
        if ls:
            kn_l[i] = max(k[1] for k in ls) + gap / 2
        if rs:
            kn_r[i] = min(k[0] for k in rs) - gap / 2
    # a side that is fused on (arm resting on the hip) borrows the other side's edge, mirrored: A-poses are symmetric
    for i in set(kn_l) ^ set(kn_r):
        if i in kn_l:
            kn_r[i] = 2 * cx - kn_l[i]
        else:
            kn_l[i] = 2 * cx - kn_r[i]
    in_l, in_r = np.full(NZ, -1e9), np.full(NZ, 1e9)
    for kn, arr in ((kn_l, in_l), (kn_r, in_r)):
        ks = sorted(kn)
        if ks:
            ii = np.arange(ks[0], armpit_i + 1)
            arr[ii] = np.interp(ii, ks, [kn[k] for k in ks])
    # neck: between the armpit and the top, the slice where the column inside the shoulder cuts is
    # thinnest front to back
    depth = []
    for i in range(armpit_i + int(0.03 * NZ), int(0.95 * NZ)):
        seg = S[order[bounds[i]:bounds[i + 1]]]
        seg = seg[(seg[:, 0] > xl) & (seg[:, 0] < xr)]
        depth.append((seg[:, 1].max() - seg[:, 1].min() if len(seg) > 8 else 9e9, i))
    neck_i = min(depth)[1]
    # above the neck only pieces separate from the head (pauldron tops) stay with the arms
    core_lo, core_hi = np.full(NZ, -1e9), np.full(NZ, 1e9)
    for i in range(neck_i, NZ):
        c = core(i)
        if c:
            core_lo[i], core_hi[i] = c[0] - gap / 2, c[1] + gap / 2
    lm = dict(cx=cx, crotch=zc[crotch_i], armpit=zc[armpit_i], neck=zc[neck_i], xl=xl, xr=xr)
    print("SECTIONS " + " ".join(f"{k}={v:.3f}" for k, v in lm.items()))

    def label(P):
        i = np.clip(((P[:, 2] - lo3[2]) / dz).astype(int), 0, NZ - 1)
        lab = np.full(len(P), "torso", dtype=object)
        x = P[:, 0]
        arm_l = np.where(i <= armpit_i, x < in_l[i], np.where(i < neck_i, x < xl, x < core_lo[i]))
        arm_r = np.where(i <= armpit_i, x > in_r[i], np.where(i < neck_i, x > xr, x > core_hi[i]))
        core_m = ~(arm_l | arm_r)
        lab[core_m & (P[:, 2] > lm["neck"])] = "head"
        lab[core_m & (P[:, 2] < lm["crotch"]) & (x < cx)] = "legL"
        lab[core_m & (P[:, 2] < lm["crotch"]) & (x >= cx)] = "legR"
        lab[arm_l] = "armL"
        lab[arm_r] = "armR"
        return lab
    return label, lm


# --------------------------------------------------------------------------------------------
# tubes
# --------------------------------------------------------------------------------------------
def build_tube(bm, tris, axis, sides, rings, seam_dir, name, cand=96):
    """Ring-cast a tube onto the faces `tris` (index array into T). Returns the faces made + UV island info."""
    P = V[T[tris]].reshape(-1, 3)
    bvh = BVHTree.FromPolygons([tuple(p) for p in V], [tuple(t) for t in T[tris]])
    axis = axis / np.linalg.norm(axis)
    t = P @ axis
    t0, t1 = t.min(), t.max()
    span = t1 - t0
    ts = t0 + span * (0.004 + 0.992 * np.linspace(0, 1, cand))
    # centre line: centroid of the section in each slab, smoothed
    C = np.zeros((cand, 3))
    for j, tj in enumerate(ts):
        m = np.abs(t - tj) < span / cand * 1.5
        C[j] = P[m].mean(0) if m.sum() > 3 else np.nan
    for k in range(3):
        bad = np.isnan(C[:, k])
        C[bad, k] = np.interp(ts[bad], ts[~bad], C[~bad, k])
    for _ in range(3):
        C[1:-1] = (C[:-2] + 2 * C[1:-1] + C[2:]) / 4
    C = C - np.outer((C @ axis) - ts, axis)           # keep each centre on its slab
    # ring frame: angle 0 points at the seam (the hidden side)
    u = np.array(seam_dir, float)
    u = u - axis * (u @ axis)
    u /= np.linalg.norm(u)
    w = np.cross(axis, u)
    ang = np.arange(sides) / sides * 2 * math.pi
    D = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * w
    far = float(np.linalg.norm(P.max(0) - P.min(0)))
    R = np.full((cand, sides), np.nan)
    for j in range(cand):
        for k in range(sides):
            org = C[j] + D[k] * far
            hit = bvh.ray_cast(Vector(org), Vector(-D[k]), far)
            if hit[0] is not None:
                r = far - hit[3]
                if r > 0:
                    R[j, k] = r
    # fill misses around the ring, then along the tube
    for j in range(cand):
        row = R[j]
        if np.isnan(row).all():
            continue
        if np.isnan(row).any():
            good = np.where(~np.isnan(row))[0]
            R[j] = np.interp(np.arange(sides), np.concatenate([good - sides, good, good + sides]),
                             np.tile(row[good], 3))
    okrow = ~np.isnan(R).any(1)
    for k in range(sides):
        R[~okrow, k] = np.interp(ts[~okrow], ts[okrow], R[okrow, k])
    # the last slabs at each end sit on the cut to the next section and catch slivers of it (a collar under
    # the helmet, a hip plate over the thigh): there the ring may not flare past the ring just inside
    e = max(2, cand // 20)
    for j in range(e):
        R[j] = np.minimum(R[j], R[e] * 1.08)
        R[cand - 1 - j] = np.minimum(R[cand - 1 - j], R[cand - 1 - e] * 1.08)
    pts = C[:, None, :] + D[None, :, :] * R[:, :, None]        # cand x sides x 3
    # keep the rings that matter: greedy insertion by the worst linear-interpolation error
    keep = [0, cand - 1]
    while len(keep) < rings:
        keep.sort()
        best, bj = -1.0, None
        for a, b in zip(keep[:-1], keep[1:]):
            if b - a < 2:
                continue
            js = np.arange(a + 1, b)
            f = ((ts[js] - ts[a]) / (ts[b] - ts[a]))[:, None, None]
            err = np.linalg.norm(pts[js] - (pts[a] * (1 - f) + pts[b] * f), axis=2).max(1)
            # a long gap also counts a little, so flat stretches still get a loop for bending
            err = err + 0.02 * (ts[b] - ts[a])
            if err.max() > best:
                best, bj = err.max(), js[err.argmax()]
        if bj is None:
            break
        keep.append(int(bj))
    keep.sort()
    ring_pts = pts[keep]
    n = len(keep)
    bv = [[bm.verts.new(tuple(ring_pts[j, k])) for k in range(sides)] for j in range(n)]
    uv = bm.loops.layers.uv.verify()
    isl = bm.faces.layers.int.get("island") or bm.faces.layers.int.new("island")
    circ = np.linalg.norm(np.roll(ring_pts, -1, 1) - ring_pts, axis=2).sum(1)
    width = float(circ.mean())
    vlen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ring_pts, axis=0), axis=2).mean(1))])
    island = build_tube.next_island
    build_tube.next_island += 3
    for j in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((bv[j][k], bv[j][k2], bv[j + 1][k2], bv[j + 1][k]))
            f[isl] = island
            uvs = ((k, j), (k + 1, j), (k + 1, j + 1), (k, j + 1))
            for lp, (ku, jv) in zip(f.loops, uvs):
                lp[uv].uv = (ku / sides * width, vlen[jv])
    # caps: a fan to the ring centre (tiny disc islands)
    for end, j in ((0, 0), (1, n - 1)):
        cpt = ring_pts[j].mean(0)
        cv = bm.verts.new(tuple(cpt))
        rad = float(np.linalg.norm(ring_pts[j] - cpt, axis=1).mean())
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((bv[j][k2], bv[j][k], cv) if end == 0 else (bv[j][k], bv[j][k2], cv))
            f[isl] = island + 1 + end
            a0, a1 = ang[k], ang[k] + 2 * math.pi / sides
            cuv = [(math.cos(a1) * rad, math.sin(a1) * rad), (math.cos(a0) * rad, math.sin(a0) * rad), (0, 0)]
            if end == 1:
                cuv = [cuv[1], cuv[0], cuv[2]]
            off = (width * 1.2 + end * rad * 2.4, rad)
            for lp, c2 in zip(f.loops, cuv):
                lp[uv].uv = (c2[0] + off[0], c2[1] + off[1])
    print(f"TUBE {name}: {sides} sides x {n} rings, length {vlen[-1]:.3f}, girth {width:.3f}")


build_tube.next_island = 1


def pca_axis(P, toward):
    c = P.mean(0)
    w, v = np.linalg.eigh(np.cov((P - c).T))
    ax = v[:, -1]
    return ax if ax @ toward > 0 else -ax


def make_tube_mesh():
    label, lm = find_sections()
    cen = V[T].mean(1)
    lab = label(cen)
    # section map on the high-poly ("Sect" colour) for the <out>_sections.png check
    pal = dict(head=(1, .8, .2), torso=(.2, .5, 1), armL=(1, .3, .3), armR=(.9, .5, .1), legL=(.3, .8, .3), legR=(.1, .6, .6))
    sect = me.color_attributes.new("Sect", "FLOAT_COLOR", "POINT")
    vl = label(V)
    for i, k in enumerate(vl):
        sect.data[i].color = (*pal[k], 1)
    bm = bmesh.new()
    d = DETAIL
    up = np.array((0, 0, 1.0))
    back = (0, 1, 0)
    q = lambda x: max(6, int(round(x * d / 2)) * 2)
    r = lambda x: max(4, int(round(x * d)))
    hands = []
    for side, sgn in (("L", -1), ("R", 1)):
        arm = np.where(lab == "arm" + side)[0]
        P = V[T[arm]].reshape(-1, 3)
        ax = pca_axis(P, np.array((0, 0, -1.0)))                 # shoulder -> hand
        t = cen[arm] @ ax
        # wrist: thinnest slab in the far quarter of the arm
        tt = t.min() + (t.max() - t.min()) * np.linspace(0.74, 0.93, 30)
        girth = []
        for tj in tt:
            m = np.abs(t - tj) < (t.max() - t.min()) / 60
            pp = cen[arm][m]
            pp = pp - np.outer(pp @ ax, ax)
            girth.append(np.linalg.norm(pp - pp.mean(0), axis=1).mean() if m.sum() > 5 else 9e9)
        wrist = tt[int(np.argmin(girth))]
        hands.append(arm[t > wrist])
        build_tube(bm, arm[t <= wrist + 0.01 * H], ax, q(10), r(11), (-sgn, 0, 0), "arm" + side)
        leg = np.where(lab == "leg" + side)[0]
        build_tube(bm, leg, -up, q(12), r(15), (-sgn, 0, 0), "leg" + side)
    build_tube(bm, np.where(lab == "torso")[0], -up, q(18), r(14), back, "torso")
    build_tube(bm, np.where(lab == "head")[0], -up, q(16), r(11), back, "head")
    m2 = bpy.data.meshes.new("Low")
    bm.to_mesh(m2)
    bm.free()
    low = bpy.data.objects.new("Low", m2)
    bpy.context.scene.collection.objects.link(low)
    # hands: cut out of the high-poly and decimated (fingers are not a tube)
    for hf, side in zip(hands, "LR"):
        hm = bpy.data.meshes.new("Hand" + side)
        used = np.unique(T[hf])
        remap = {int(v): i for i, v in enumerate(used)}
        hm.from_pydata([tuple(V[v]) for v in used], [], [tuple(remap[int(v)] for v in tri) for tri in T[hf]])
        ho = bpy.data.objects.new("Hand" + side, hm)
        bpy.context.scene.collection.objects.link(ho)
        bpy.context.view_layer.objects.active = ho
        want = int(260 * d)
        if len(hf) > want:
            md = ho.modifiers.new("dec", "DECIMATE")
            md.ratio = want / len(hf)
            bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.ops.object.select_all(action="DESELECT")
        ho.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.02)
        bpy.ops.object.mode_set(mode="OBJECT")
        # smart UVs fill 0..1: scale them to the hand's real size so texel density matches the tubes
        s = math.sqrt(sum(p.area for p in ho.data.polygons))
        for l in ho.data.uv_layers[0].data:
            l.uv = (l.uv[0] * s + 50 + (10 if side == "R" else 0), l.uv[1] * s)
        print(f"HAND {side}: {len(ho.data.polygons)} faces")
        bpy.ops.object.select_all(action="DESELECT")
        ho.select_set(True)
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.join()
    # pack the islands (they are already at true relative size)
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
    return low


def make_decimate_mesh():
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    bpy.context.view_layer.objects.active = hi
    bpy.ops.object.duplicate()
    low = bpy.context.view_layer.objects.active
    low.name = "Low"
    md = low.modifiers.new("dec", "DECIMATE")
    md.ratio = TRIS / len(T)
    bpy.ops.object.modifier_apply(modifier=md.name)
    while low.data.color_attributes:
        low.data.color_attributes.remove(low.data.color_attributes[0])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
    return low


def load_given_low(path):
    """a finished low-poly with its own UVs (sheet_model.py); the blend's mesh is its painted, subdivided copy"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    low = [ob for ob in bpy.data.objects if ob not in before and ob.type == "MESH"][0]
    low.data.transform(low.matrix_world)
    low.matrix_world.identity()
    low.name = "Low"
    return low


GIVEN = o.get("low")
if GIVEN:
    METHOD = "given"
    low = load_given_low(GIVEN)
else:
    low = make_tube_mesh() if METHOD == "tube" else make_decimate_mesh()
if me.color_attributes.get("Sect"):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "VERTEX"
    me.color_attributes.active_color = me.color_attributes["Sect"]
    low.hide_render = True
    cam0 = bpy.data.objects.new("cam0", bpy.data.cameras.new("cam0"))
    sc.collection.objects.link(cam0)
    sc.camera = cam0
    cam0.data.type = "ORTHO"
    cam0.data.ortho_scale = H * 1.06
    cam0.location = ((lo3[0] + hi3[0]) / 2, lo3[1] - 3 * H, (lo3[2] + hi3[2]) / 2)
    cam0.rotation_euler = (math.radians(90), 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = 700, 900
    sc.render.filepath = out + "_sections.png"
    bpy.ops.render.render(write_still=True)
    low.hide_render = False
    me.color_attributes.active_color = me.color_attributes["Col"]
low.data.materials.clear()
if not GIVEN:
    for p in low.data.polygons:
        p.use_smooth = True
low.data.calc_loop_triangles()
ntris = len(low.data.loop_triangles)
print(f"LOW {METHOD}: {len(low.data.vertices)} verts, {ntris} tris")

# --------------------------------------------------------------------------------------------
# bakes
# --------------------------------------------------------------------------------------------
mh = bpy.data.materials.new("HighCol")
mh.use_nodes = True
nt = mh.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
# colour source on the high-poly: the "Col" vertex colour, or else its own texture
src_img = None
if not me.color_attributes.get("Col"):
    for m_ in me.materials:
        if m_ and m_.use_nodes:
            for n_ in m_.node_tree.nodes:
                if n_.type == "TEX_IMAGE" and n_.image:
                    src_img = n_.image
if src_img:
    vc = nt.nodes.new("ShaderNodeTexImage")
    vc.image = src_img
else:
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
em = nt.nodes.new("ShaderNodeEmission")
mo = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(vc.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], mo.inputs["Surface"])
me.materials.clear()
me.materials.append(mh)
for p in me.polygons:
    p.use_smooth = True

ml = bpy.data.materials.new("LowBake")
ml.use_nodes = True
low.data.materials.append(ml)
tn = ml.node_tree.nodes.new("ShaderNodeTexImage")
ml.node_tree.nodes.active = tn

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.render.bake.margin = 12
sc.render.bake.use_selected_to_active = True
# a given low-poly is the same surface as its painted copy: keep the rays short so they cannot reach a neighbour
# (cage=<fraction of height> overrides: use 0.02 when the given low-poly is a reduced version of the high-poly)
CAGE = float(o.get("cage", 0.003 if GIVEN else 0.02))
sc.render.bake.cage_extrusion = H * CAGE
sc.render.bake.max_ray_distance = H * CAGE * 3
bpy.ops.object.select_all(action="DESELECT")
hi.select_set(True)
low.select_set(True)
bpy.context.view_layer.objects.active = low
maps = {}
jobs = [("albedo", "EMIT", 4, "sRGB", None), ("ao", "AO", SAMPLES, "Non-Color", None),
        ("normal", "NORMAL", 4, "Non-Color", None)]
# extra=<attr>[,<attr>]: also bake these vertex-colour attributes of the high-poly (e.g. Trust) as data maps
for ex in [x for x in o.get("extra", "").split(",") if x]:
    if me.color_attributes.get(ex):
        jobs.append((ex.lower(), "EMIT", 4, "Non-Color", ex))
ALBEDO = o.get("albedo")          # albedo=<png>: use this (already in the low-poly's UVs) instead of baking colour
for name, btype, samples, colorspace, attr_name in jobs:
    if name == "albedo" and ALBEDO:
        img = bpy.data.images.load(os.path.abspath(ALBEDO))
        maps[name] = img
        continue
    if isinstance(vc, bpy.types.ShaderNodeVertexColor):
        vc.layer_name = attr_name or "Col"
    img = bpy.data.images.new(os.path.basename(out) + "_" + name, SIZE, SIZE, alpha=False)
    img.colorspace_settings.name = colorspace
    img.filepath_raw = f"{out}_{name}.png"
    img.file_format = "PNG"
    tn.image = img
    sc.cycles.samples = samples
    bpy.ops.object.bake(type=btype)
    img.save()
    maps[name] = img
    print("BAKED", img.filepath_raw)

# diffuse = albedo x AO (in display space: the look an unlit/vertex-lit engine shows)
alb = np.array(maps["albedo"].pixels[:]).reshape(SIZE, SIZE, -1)
if alb.shape[2] == 3:
    alb = np.concatenate([alb, np.ones((SIZE, SIZE, 1))], 2)
ao = np.array(maps["ao"].pixels[:]).reshape(SIZE, SIZE, 4)[:, :, :1]
dif = alb.copy()
dif[:, :, :3] = alb[:, :, :3] * (1 - AO_STRENGTH + AO_STRENGTH * ao)
dimg = bpy.data.images.new(os.path.basename(out) + "_diffuse", SIZE, SIZE, alpha=False)
dimg.pixels = dif.ravel()
dimg.filepath_raw = out + "_diffuse.png"
dimg.file_format = "PNG"
dimg.save()

# final material: diffuse + normal map
low.data.materials.clear()
fm = bpy.data.materials.new("Game")
fm.use_nodes = True
fn = fm.node_tree
bsdf = fn.nodes["Principled BSDF"]
ct = fn.nodes.new("ShaderNodeTexImage")
ct.image = dimg
nmt = fn.nodes.new("ShaderNodeTexImage")
nmt.image = maps["normal"]
nm = fn.nodes.new("ShaderNodeNormalMap")
fn.links.new(ct.outputs["Color"], bsdf.inputs["Base Color"])
fn.links.new(nmt.outputs["Color"], nm.inputs["Color"])
fn.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
bsdf.inputs["Roughness"].default_value = 0.5
low.data.materials.append(fm)
hi.hide_render = True
hi.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
bpy.context.view_layer.objects.active = low
bpy.ops.export_scene.gltf(filepath=out + ".glb", use_selection=True)

# --------------------------------------------------------------------------------------------
# preview: textured row (diffuse + normal map under a sun) and wireframe row
# --------------------------------------------------------------------------------------------
W, HH = 480, 860
P = np.array([tuple(v.co) for v in low.data.vertices])
c = (P.min(0) + P.max(0)) / 2
h = float(P[:, 2].max() - P[:, 2].min())
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = h * 1.06
sc.render.resolution_x, sc.render.resolution_y = W, HH
sc.render.film_transparent = False
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sc.collection.objects.link(sun)
amb = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
amb.data.energy = 1.2
sc.collection.objects.link(amb)


def shots(tag):
    files = []
    for angle in (0, 35, 270, 180):
        r = math.radians(angle)
        cam.location = (c[0] + h * 3 * math.sin(r), c[1] - h * 3 * math.cos(r), c[2])
        cam.rotation_euler = (math.radians(90), 0, r)
        sun.rotation_euler = (math.radians(55), 0, r + math.radians(35))
        amb.rotation_euler = (math.radians(70), 0, r - math.radians(60))
        f = f"{out}_{tag}_{angle}.png"
        sc.render.filepath = f
        bpy.ops.render.render(write_still=True)
        files.append(f)
    row = np.concatenate([np.array(bpy.data.images.load(f).pixels[:]).reshape(HH, W, 4) for f in files], 1)
    for f in files:
        os.remove(f)
    return row


CPU = int(o.get("cpu", 0))        # cpu=1: previews with Cycles on the CPU (no GPU use: safe while a game is running)
if CPU:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 12
    sc.cycles.max_bounces = 1
else:
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
tex_row = shots("tex")
if not CPU:
    sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.75, 0.75, 0.75)
sc.display.shading.show_cavity = False
for p in low.data.polygons:
    p.use_smooth = False
bpy.ops.object.select_all(action="DESELECT")
low.select_set(True)
bpy.context.view_layer.objects.active = low
bpy.ops.object.duplicate()
wire = bpy.context.view_layer.objects.active
wm = wire.modifiers.new("w", "WIREFRAME")
wm.thickness = h * 0.0022
wm.use_even_offset = False
wire.data.materials.clear()
if CPU:
    for ob_, col_ in ((low, (0.75, 0.75, 0.75, 1)), (wire, (0.02, 0.02, 0.02, 1))):
        m_ = bpy.data.materials.new("flat")
        m_.use_nodes = True
        m_.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col_
        ob_.data.materials.clear()
        ob_.data.materials.append(m_)
sc.display.shading.color_type = "OBJECT"
low.color = (0.75, 0.75, 0.75, 1)
wire.color = (0.02, 0.02, 0.02, 1)
wire_row = shots("wire")
bpy.data.objects.remove(wire, do_unlink=True)
sheet = bpy.data.images.new("sheet", W * 4, HH * 2)
sheet.pixels = np.concatenate([wire_row, tex_row], 0).ravel()   # image rows run bottom-up: textured on top
sheet.filepath_raw = out + ".png"
sheet.file_format = "PNG"
sheet.save()
print(f"RETOPO_BAKE {out}.glb method={METHOD} {ntris} tris, textures {SIZE}")
