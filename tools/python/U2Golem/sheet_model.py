"""Poly-model a character from its reference sheet: simple tubes per body section, refined in versions.

Run:  blender -b --python sheet_model.py -- <out_prefix> front=<cutout.png> guide=<mesh.glb> [level=2]
      [round=2.3]
front  the front view with alpha (img2shape_mv.py saves *_input_front.png).
guide  a mesh of the same character in the same pose (the Hunyuan high-poly). The drawing decides the
       outline; the guide is only asked how deep each section is front to back, which a front view
       cannot show. Its bounding box also sets the scale (front = -Y, up = +Z).

The method (after Noggi's "Japan's 3D modeling philosophy" and Aka's low-poly build):
  1. Sections: every pixel row of the drawing is cut into runs. The run on the centre line is the core
     (head / torso / legs), runs beside it are the arms. Crotch, armpit and neck are where runs split
     and merge. Each section is modelled on its own, so a loop added to an arm stays in the arm.
  2. Each section starts as a tube: a ring per chosen row, as wide as the drawing there and as deep as
     the guide. Rings are superellipses ("round": 2 = ellipse, higher = boxier armour).
  3. Rings are placed where the shape needs them: start with the two ends, then keep adding the ring
     whose absence changes the outline most. Armour steps (gauntlet edge, boot top, knee pad) therefore
     get a tight pair of loops and smooth stretches get few.
  4. Armour that overlaps another section is its own piece: shoulder balls are found as a bulge in the
     arm's outer outline and completed as round forms (see pauldron()).
  5. level = how far the refinement goes: 1 blockout (~500 tris), 2 (~1,100), 3 (~2,300), 4 (~3,600).
UVs: every tube is one rectangle with its seam on the hidden side, at true relative size, packed.
Writes <out>.blend and <out>.glb (mesh "Low", UVs, sharp edges by angle); paint it with project_views.py
and bake with retopo_bake.py low=<out>.glb.
"""
import math, os, sys
import bpy, bmesh
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.splitext(os.path.abspath(args[0]))[0]
o = dict(a.split("=", 1) for a in args[1:])
LEVEL = int(o.get("level", 2))
ROUND = float(o.get("round", 2.3))
#        sides: limb, torso, head     rings: arm, leg, torso, head
LEVELS = {1: ((6, 8, 8), (6, 7, 7, 5)),
          2: ((8, 10, 10), (10, 12, 11, 8)),
          3: ((10, 14, 14), (16, 20, 18, 12)),
          4: ((12, 16, 16), (22, 28, 24, 16))}
(S_LIMB, S_TORSO, S_HEAD), (R_ARM, R_LEG, R_TORSO, R_HEAD) = LEVELS[LEVEL]

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---- the drawing ----
img = bpy.data.images.load(o["front"])
iw, ih = img.size
alpha = np.array(img.pixels[:]).reshape(ih, iw, 4)[::-1, :, 3]          # row 0 = top
mask = alpha > 0.5
rows = np.where(mask.any(1))[0]
cols = np.where(mask.any(0))[0]
r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
hpx = r1 - r0

# ---- the guide ----
bpy.ops.import_scene.gltf(filepath=o["guide"])
gs = [x for x in bpy.context.scene.objects if x.type == "MESH"]
GV, GT = [], []
for g in gs:
    g.data.calc_loop_triangles()
    base = len(GV)
    GV += [tuple(g.matrix_world @ v.co) for v in g.data.vertices]
    GT += [tuple(base + i for i in t.vertices) for t in g.data.loop_triangles]
for x in list(bpy.data.objects):
    bpy.data.objects.remove(x, do_unlink=True)
GV, GT = np.array(GV), np.array(GT)
a, b, c = GV[GT[:, 0]], GV[GT[:, 1]], GV[GT[:, 2]]
area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
rng = np.random.default_rng(0)
f = rng.choice(len(GT), 500000, p=area / area.sum())
u, v = rng.random(len(f)), rng.random(len(f))
flip = u + v > 1
u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
GS = a[f] + (b[f] - a[f]) * u[:, None] + (c[f] - a[f]) * v[:, None]
glo, ghi = GV.min(0), GV.max(0)
H = float(ghi[2] - glo[2])
# drawing -> world: the silhouette's bounding box is the guide's bounding box (as project_views.py does)
col2x = lambda cc: glo[0] + (np.asarray(cc, float) - c0) / (c1 - c0) * (ghi[0] - glo[0])
row2z = lambda rr: ghi[2] - (np.asarray(rr, float) - r0) / (r1 - r0) * H
px = (ghi[0] - glo[0]) / (c1 - c0)                                      # world units per pixel
g_row = np.clip(np.round(r0 + (ghi[2] - GS[:, 2]) / H * (r1 - r0)).astype(int), r0, r1)
g_order = np.argsort(g_row, kind="stable")
g_bounds = np.searchsorted(g_row[g_order], np.arange(r0, r1 + 2))


def runs_of(r):
    m = mask[r]
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0] - 1
    res = []
    for s, e in zip(st, en):
        if res and s - res[-1][1] <= 3:                # close hairline gaps (ink lines)
            res[-1] = (res[-1][0], e)
        else:
            res.append((s, e))
    return [(s, e) for s, e in res if e - s >= 3]


RUNS = {r: runs_of(r) for r in range(r0, r1 + 1)}
cxc = float(np.median(np.where(mask)[1]))


def core(r):
    for s, e in RUNS[r]:
        if s <= cxc <= e:
            return (s, e)
    return None


# ---- landmarks (rows grow downward) ----
def core_w(r):
    c = core(r)
    return c[1] - c[0] if c else 0


def is_hip(r):
    """the centre run is the whole hip, not just the tip between the thighs: about as wide as it is a bit higher up"""
    above = [core_w(q) for q in range(r - int(0.05 * hpx), r - int(0.02 * hpx))]
    return core_w(r) > 0 and core_w(r) >= 0.8 * float(np.median(above))


crotch = next(r for r in range(int(r1 - 0.25 * hpx), r0, -1) if is_hip(r))
# armpit: top of the longest stretch of rows where an arm hangs free on both sides of the core
# (pauldron tops beside the neck are a shorter stretch higher up)
free = [r for r in range(crotch, int(r0 + 0.08 * hpx), -1)
        if core(r) and any(e < core(r)[0] for s, e in RUNS[r]) and any(s > core(r)[1] for s, e in RUNS[r])]
stretches, cur = [], [free[0]]
for r in free[1:]:
    if cur[-1] - r > 4:
        stretches.append(cur)
        cur = []
    cur.append(r)
stretches.append(cur)
armpit = max(stretches, key=len)[-1]
xl, xr = core(armpit)
kn_l, kn_r = {}, {}
for r in range(armpit, r1 + 1):
    c = core(r)
    ls = sorted(k for k in RUNS[r] if k[1] < (c[0] if c else cxc))
    rs = sorted(k for k in RUNS[r] if k[0] > (c[1] if c else cxc))
    if c is None or r > crotch:                        # legs apart: the innermost run each side is a leg
        ls = sorted(k for k in RUNS[r] if k[1] < cxc and k != c)[:-1]
        rs = sorted(k for k in RUNS[r] if k[0] > cxc and k != c)[1:]
    if ls:
        kn_l[r] = max(k[1] for k in ls) + 1.5
    if rs:
        kn_r[r] = min(k[0] for k in rs) - 1.5
for r in set(kn_l) ^ set(kn_r):                        # arm resting on the hip: borrow the other side, mirrored
    if r in kn_l:
        kn_r[r] = 2 * cxc - kn_l[r]
    else:
        kn_l[r] = 2 * cxc - kn_r[r]
in_l, in_r = {}, {}
for kn, arr in ((kn_l, in_l), (kn_r, in_r)):
    ks = sorted(kn)
    rr = np.arange(armpit, min(r1, ks[-1] + int(0.03 * hpx)) + 1)      # a little past the fingertips
    for r, val in zip(rr, np.interp(rr, ks, [kn[k] for k in ks])):
        arr[int(r)] = float(val)
neck = min(range(int(r0 + 0.05 * hpx), int(armpit - 0.03 * hpx)), key=lambda r: (core(r)[1] - core(r)[0]) if core(r) else 9e9)
print(f"SHEET rows {r0}-{r1}: neck {neck}, armpit {armpit}, crotch {crotch}; shoulder cuts cols {xl}-{xr}")


def section_spans():
    """per section: {row: (col_a, col_b)} from the drawing."""
    sec = {k: {} for k in ("head", "torso", "legL", "legR", "armL", "armR")}
    for r in range(r0, r1 + 1):
        rs = RUNS[r]
        if not rs:
            continue
        c = core(r)
        if r < neck:
            # runs wholly outside the shoulder cuts are pauldron tops; the rest is the head
            head = [k for k in rs if not (k[1] < xl or k[0] > xr)]
            if head:
                sec["head"][r] = (min(k[0] for k in head), max(k[1] for k in head))
            la = [k for k in rs if k[1] < xl]
            ra = [k for k in rs if k[0] > xr]
            if la:
                sec["armL"][r] = (min(k[0] for k in la), max(k[1] for k in la))
            if ra:
                sec["armR"][r] = (min(k[0] for k in ra), max(k[1] for k in ra))
        elif r <= armpit:
            if c:
                sec["torso"][r] = (max(c[0], xl), min(c[1], xr))
            lo_ = min(k[0] for k in rs)
            hi_ = max(k[1] for k in rs)
            if lo_ < xl:
                sec["armL"][r] = (lo_, min(xl, max(k[1] for k in rs if k[0] < xl)))
            if hi_ > xr:
                sec["armR"][r] = (max(xr, min(k[0] for k in rs if k[1] > xr)), hi_)
        else:
            il, ir = in_l.get(r, -1e9), in_r.get(r, 1e9)
            body = [(max(s, il), min(e, ir)) for s, e in rs if e > il and s < ir]
            la = [(s, min(e, il)) for s, e in rs if s < il]
            ra = [(max(s, ir), e) for s, e in rs if e > ir]
            if la:
                sec["armL"][r] = (min(k[0] for k in la), max(k[1] for k in la))
            if ra:
                sec["armR"][r] = (min(k[0] for k in ra), max(k[1] for k in ra))
            if not body:
                continue
            if r <= crotch:
                sec["torso"][r] = (min(k[0] for k in body), max(k[1] for k in body))
            else:
                L = [(s, min(e, cxc)) for s, e in body if s < cxc]
                R = [(max(s, cxc), e) for s, e in body if e > cxc]
                L, R = [k for k in L if k[1] - k[0] >= 3], [k for k in R if k[1] - k[0] >= 3]
                if L:
                    sec["legL"][r] = (min(k[0] for k in L), max(k[1] for k in L))
                if R:
                    sec["legR"][r] = (min(k[0] for k in R), max(k[1] for k in R))
    return sec


def profile(span, min_w=0.012, top_frac=0.0):
    """rows + [xa, xb, ya, yb] in world units for a section; depth from the guide inside the section's width."""
    rs = sorted(span)
    # one contiguous stretch, without hair-thin tips (antenna, finger ends)
    rs = [r for r in rs if (span[r][1] - span[r][0]) * px > min_w * H]
    if top_frac:                                       # head: start where the skull does, not at an antenna
        wmax = max(span[r][1] - span[r][0] for r in rs)
        first = next(r for r in rs if span[r][1] - span[r][0] >= top_frac * wmax)
        rs = [r for r in rs if r >= first]
    best, cur = [], []
    for r in rs:
        if cur and r - cur[-1] > 4:
            best, cur = (cur if len(cur) > len(best) else best), []
        cur.append(r)
    rs = cur if len(cur) > len(best) else best
    P = np.full((len(rs), 4), np.nan)
    for i, r in enumerate(rs):
        xa, xb = col2x(span[r][0] - 0.5), col2x(span[r][1] + 0.5)
        P[i, 0], P[i, 1] = xa, xb
        lo_i, hi_i = g_bounds[max(r - 2 - r0, 0)], g_bounds[min(r + 3 - r0, r1 - r0 + 1)]
        pts = GS[g_order[lo_i:hi_i]]
        pad = (xb - xa) * 0.05
        pts = pts[(pts[:, 0] > xa - pad) & (pts[:, 0] < xb + pad)]
        if len(pts) > 12:
            P[i, 2], P[i, 3] = np.quantile(pts[:, 1], 0.01), np.quantile(pts[:, 1], 0.99)
    idx = np.arange(len(rs))
    for k in (0, 1):                                   # single-row outliers in the drawing (ink specks)
        pad7 = np.pad(P[:, k], 3, mode="edge")
        P[:, k] = np.median(np.stack([pad7[j:j + len(rs)] for j in range(7)]), 0)
    for k in (2, 3):
        bad = np.isnan(P[:, k])
        if bad.all():
            P[:, k] = (-1) ** (k + 1) * (P[:, 1] - P[:, 0]) / 2
        elif bad.any():
            P[bad, k] = np.interp(idx[bad], idx[~bad], P[~bad, k])
        # the guide's depth is noisier than a drawn outline: median of 5 rows
        pad5 = np.pad(P[:, k], 2, mode="edge")
        P[:, k] = np.median(np.stack([pad5[j:j + len(rs)] for j in range(5)]), 0)
    if top_frac:
        # the dome: above the widest row the depth may not outgrow the drawn width (keeps the guide's
        # antenna and hair wisps out of the skull)
        w = P[:, 1] - P[:, 0]
        wide = int(np.argmax(w))
        yc, ratio = (P[wide, 2] + P[wide, 3]) / 2, (P[wide, 3] - P[wide, 2]) / w[wide]
        for i in range(wide):
            half = min((P[i, 3] - P[i, 2]) / 2, w[i] * ratio / 2)
            c_ = np.clip((P[i, 2] + P[i, 3]) / 2, yc - (w[wide] * ratio / 2 - half), yc + (w[wide] * ratio / 2 - half))
            P[i, 2], P[i, 3] = c_ - half, c_ + half
    return np.array(rs), P


def pick_rings(rs, P, n):
    """greedy: keep adding the row whose absence changes the outline most."""
    z = row2z(rs)
    keep = [0, len(rs) - 1]
    while len(keep) < n:
        keep.sort()
        best, bj = -1.0, None
        for i0, i1 in zip(keep[:-1], keep[1:]):
            if i1 - i0 < 2:
                continue
            js = np.arange(i0 + 1, i1)
            t = ((z[js] - z[i0]) / (z[i1] - z[i0]))[:, None]
            err = np.abs(P[js] - (P[i0] * (1 - t) + P[i1] * t)).max(1) + 0.03 * abs(z[i1] - z[i0])
            if err.max() > best:
                best, bj = err.max(), js[err.argmax()]
        if bj is None:
            break
        keep.append(int(bj))
    return sorted(keep)


bm = bmesh.new()
uv = bm.loops.layers.uv.verify()
island_x = [0.0]


def tube(name, prof, sides, nrings, seam_deg, rnd=ROUND):
    rs, P = prof
    keep = pick_rings(rs, P, nrings)
    z = row2z(rs[keep])
    Q = P[keep]
    ang = math.radians(seam_deg) + np.arange(sides) / sides * 2 * math.pi
    cs, sn = np.cos(ang), np.sin(ang)
    ex = 2.0 / rnd
    ux, uy = np.sign(cs) * np.abs(cs) ** ex, np.sign(sn) * np.abs(sn) ** ex
    ring = np.zeros((len(keep), sides, 3))
    for j in range(len(keep)):
        ring[j, :, 0] = (Q[j, 0] + Q[j, 1]) / 2 + (Q[j, 1] - Q[j, 0]) / 2 * ux
        ring[j, :, 1] = (Q[j, 2] + Q[j, 3]) / 2 + (Q[j, 3] - Q[j, 2]) / 2 * uy
        ring[j, :, 2] = z[j]
    bv = [[bm.verts.new(tuple(p)) for p in ring[j]] for j in range(len(keep))]
    girth = float(np.linalg.norm(np.roll(ring, -1, 1) - ring, axis=2).sum(1).mean())
    vlen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=2).mean(1))])
    x0 = island_x[0]
    for j in range(len(keep) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((bv[j][k], bv[j + 1][k], bv[j + 1][k2], bv[j][k2]))
            for lp, (ku, jv) in zip(f.loops, ((k, j), (k, j + 1), (k + 1, j + 1), (k + 1, j))):
                lp[uv].uv = (x0 + ku / sides * girth, -vlen[jv])
    x0 += girth * 1.05
    for end, j in ((0, 0), (1, len(keep) - 1)):
        cpt = ring[j].mean(0)
        cv = bm.verts.new(tuple(cpt))
        d = ring[j] - cpt
        rad = float(np.linalg.norm(d, axis=1).max())
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((bv[j][k], bv[j][k2], cv) if end == 0 else (bv[j][k2], bv[j][k], cv))
            pts = (d[k], d[k2], (0, 0, 0)) if end == 0 else (d[k2], d[k], (0, 0, 0))
            for lp, q in zip(f.loops, pts):
                lp[uv].uv = (x0 + rad + q[0], -rad - end * rad * 2.2 + q[1])
        x0 = x0 if end == 0 else x0 + rad * 2.2
    island_x[0] = x0
    print(f"TUBE {name}: {sides} sides x {len(keep)} rings")


def pauldron(side):
    """A shoulder ball is its own piece. The drawing shows its outer outline; the half that overlaps the
    chest is hidden, so it is completed as a round form: a body of revolution about a vertical axis one
    radius in from its outermost point (radius = half its height). Depth is scaled to the guide.
    Returns (profile, first arm row) or None when the shoulder has no bulge."""
    sgn = -1 if side == "L" else 1
    outer = {}
    for r in range(r0, min(r1, armpit + int(0.12 * hpx))):
        rs = [k for k in RUNS[r] if (k[1] < cxc if side == "L" else k[0] > cxc) or (neck <= r)]
        if r < neck:
            rs = [k for k in RUNS[r] if (k[1] < xl if side == "L" else k[0] > xr)]
        if rs:
            outer[r] = min(k[0] for k in rs) if side == "L" else max(k[1] for k in rs)
    if not outer:
        return None
    rows_ = sorted(outer)
    top_rows = [r for r in rows_ if r <= armpit]
    if not top_rows:
        return None
    peak = min(top_rows, key=lambda r: outer[r] * -sgn)          # outermost row of the shoulder
    # the pinch under the ball: where the outline comes furthest back in before the arm goes on
    below = [r for r in rows_ if peak < r <= armpit + 0.10 * hpx]
    if not below:
        return None
    bottom = max(below, key=lambda r: outer[r] * -sgn)
    bulge = (outer[bottom] - outer[peak]) * -sgn
    if bulge * px < 0.012 * H:
        print(f"PAULDRON {side}: no bulge ({bulge * px / H * 100:.1f}% of height)")
        return None
    top = rows_[0]
    rad = (bottom - top) / 2
    xc = outer[peak] - sgn * rad
    trim = int(0.05 * (bottom - top))
    rs = np.array([r for r in rows_ if top + trim <= r <= bottom - trim])
    rr = np.array([max(1.0, (xc - outer[r]) * -sgn) for r in rs])
    # round off the two ends so the piece closes (the outline is cut flat at the bottom by the arm)
    t = (rs - top) / max(1, bottom - top)
    rr = np.minimum(rr, rad * 2 * np.sqrt(np.clip(t * (1 - t), 0, None)) + 1.0)
    xw, rw = col2x(xc), rr * px
    sel = (GS[:, 2] < row2z(top)) & (GS[:, 2] > row2z(bottom)) & ((GS[:, 0] - xw) * sgn > 0.2 * rad * px)          # the outer side only: the inner side is chest
    if sel.sum() > 50:
        ya, yb = np.quantile(GS[sel, 1], 0.01), np.quantile(GS[sel, 1], 0.99)
    else:
        ya, yb = -rad * px, rad * px
    yc, ratio = (ya + yb) / 2, min(1.15, (yb - ya) / 2 / (rad * px) * 1.05)
    P = np.stack([xw - rw, xw + rw, yc - rw * ratio, yc + rw * ratio], 1)
    print(f"PAULDRON {side}: rows {top}-{bottom}, radius {rad * px:.3f}, depth ratio {ratio:.2f}")
    return (rs, P), int(bottom - 0.35 * (bottom - top))


sec = section_spans()
# seam angle: 0 deg = +X, 90 = +Y (back). Seams sit on the inner side of limbs and down the back.
for side, seam in (("L", 0), ("R", 180)):
    pd = pauldron(side)
    if pd:
        prof_p, arm_from = pd
        tube("pauldron" + side, prof_p, S_LIMB, max(5, R_ARM // 2 + 1), seam, 2.0)
        sec["arm" + side] = {r: v for r, v in sec["arm" + side].items() if r >= arm_from}
    tube("arm" + side, profile(sec["arm" + side]), S_LIMB, R_ARM, seam)
    tube("leg" + side, profile(sec["leg" + side]), S_LIMB, R_LEG, seam)
tube("torso", profile(sec["torso"]), S_TORSO, R_TORSO, 90, ROUND + 0.4)
tube("head", profile(sec["head"], top_frac=0.3), S_HEAD, R_HEAD, 90, 2.0)

me = bpy.data.meshes.new("Low")
bm.normal_update()
bm.to_mesh(me)
bm.free()
low = bpy.data.objects.new("Low", me)
bpy.context.scene.collection.objects.link(low)
bpy.context.view_layer.objects.active = low
low.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.uv.select_all(action="SELECT")
bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
bpy.ops.object.mode_set(mode="OBJECT")
for p in me.polygons:
    p.use_smooth = True
me.set_sharp_from_angle(angle=math.radians(50))
me.calc_loop_triangles()
bpy.ops.wm.save_as_mainfile(filepath=out + ".blend")
bpy.ops.export_scene.gltf(filepath=out + ".glb", use_selection=True)
print(f"SHEET_MODEL {out}.glb level {LEVEL}: {len(me.vertices)} verts, {len(me.loop_triangles)} tris")
