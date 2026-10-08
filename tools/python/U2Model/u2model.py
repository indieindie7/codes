r"""U2Model: basic shapes for Unreal II's editor that you can move, turn, scale and combine (CSG add / subtract), as
editor brushes or frozen into one static mesh, with an offline preview picture for a quick mock-up.

    from u2model import *
    post = box(512, 512, 320) - box(448, 448, 300).move(0, 0, 10) - box(128, 64, 200).move(0, -240, 10)
    post += cylinder(40, 400, 12).move(300, 300, 0) + wedge(256, 192, 96).move(0, -420, 0)
    post.preview("post.png")                       # instant: no editor, no GPU
    cmds = post.editor_commands(origin=(0, 0, -1024), workdir=r"C:\...\U2Model")    # BRUSH IMPORT / MOVETO / ADD|SUBTRACT
    post.freeze_commands(...)                      # the CSG result as a static mesh (editor: rebuild, SAVEPOLYS, re-import)

What the editor accepts (checked 2026-10-08, games/research_notes/3D modelling for the UE2 editor):
  - closed CONCAVE brushes are fine; polygons up to 32 vertices; faces are kept convex here anyway (non-convex faces
    are triangulated) because concave faces were only checked for collision, not for rendering/lighting
  - brushes must go through the builder brush (BRUSH IMPORT FILE=<PolyList t3d> + MOVETO + ADD/SUBTRACT); Brush actors
    in a MAP IMPORTADD are not built
  - winding: a face's outward normal is (v1-v0) x (v2-v0) (the editor's own, as make_open.py's box_polys)
Shapes sit on their base at the origin (z from 0 up) unless said otherwise; units are Unreal units (a door ~ 128 x 256).
"""
import math, os

import numpy as np

TEX = "Engine.DefaultTexture"
MAXV = 32


# ------------------------------------------------------------------------------------------------ the mesh
class Mesh:
    """a closed polyhedron: verts (N,3) and faces (lists of vertex indices, outward winding)"""

    def __init__(self, verts, faces, name="shape"):
        self.v = np.asarray(verts, dtype=float).reshape(-1, 3)
        self.f = [list(f) for f in faces]
        self.name = name

    # --- transforms (all return new meshes)
    def move(self, x=0, y=0, z=0):
        return Mesh(self.v + [x, y, z], self.f, self.name)

    def scale(self, sx=1, sy=None, sz=None):
        sy = sx if sy is None else sy
        sz = sx if sz is None else sz
        m = Mesh(self.v * [sx, sy, sz], self.f, self.name)
        return m.flipped() if sx * sy * sz < 0 else m

    def rotate(self, yaw=0, pitch=0, roll=0):
        """degrees: yaw about z (x toward y), pitch about y, roll about x"""
        a, b, c = (math.radians(t) for t in (yaw, pitch, roll))
        Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
        Rx = np.array([[1, 0, 0], [0, math.cos(c), -math.sin(c)], [0, math.sin(c), math.cos(c)]])
        return Mesh(self.v @ (Rz @ Ry @ Rx).T, self.f, self.name)

    def mirror(self, axis="x"):
        s = {"x": (-1, 1, 1), "y": (1, -1, 1), "z": (1, 1, -1)}[axis]
        return self.scale(*s)

    def flipped(self):
        return Mesh(self.v, [list(reversed(f)) for f in self.f], self.name)

    def named(self, name):
        return Mesh(self.v, self.f, name)

    # --- combining: a Model is an ordered list of CSG steps
    def __add__(self, other):
        return Model([("add", self)]) + other

    def __sub__(self, other):
        return Model([("add", self)]) - other

    # --- facts
    def bounds(self):
        return self.v.min(axis=0), self.v.max(axis=0)

    def volume(self):
        vol = 0.0
        for f in self.f:
            a = self.v[f[0]]
            for i in range(1, len(f) - 1):
                vol += np.dot(a, np.cross(self.v[f[i]], self.v[f[i + 1]])) / 6
        return vol

    def polys(self):
        """the faces as vertex loops, each planar-convex and <= 32 vertices (others triangulated)"""
        out = []
        for f in self.f:
            P = self.v[f]
            if len(f) <= MAXV and convex_planar(P):
                out.append(P)
            else:
                out += [P[list(t)] for t in triangulate(P)]
        return out

    def check(self):
        """problems: open edges, inward winding, non-planar faces (returns a list of strings; empty = good)"""
        bad, edges = [], {}
        for f in self.f:
            for a, b in zip(f, f[1:] + f[:1]):
                edges[(a, b)] = edges.get((a, b), 0) + 1
        open_ = [e for e in edges if (e[1], e[0]) not in edges]
        if open_:
            bad.append("%s: %d open edges (not closed)" % (self.name, len(open_)))
        if self.volume() <= 0:
            bad.append("%s: inside out (volume %.0f)" % (self.name, self.volume()))
        for f in self.f:
            P = self.v[f]
            n = newell(P)
            if np.linalg.norm(n) < 1e-9:
                bad.append("%s: a degenerate face" % self.name)
                continue
            n = n / np.linalg.norm(n)
            if np.abs((P - P[0]) @ n).max() > 0.5:
                bad.append("%s: a non-planar face" % self.name)
        return bad


# ------------------------------------------------------------------------------------------------ geometry helpers
def newell(P):
    n = np.zeros(3)
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        n += [(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])]
    return n


def frame(P):
    """2D coordinates of a planar loop in its own plane (u, v) with the normal as the third axis"""
    n = newell(P)
    n = n / (np.linalg.norm(n) or 1)
    u = P[1] - P[0]
    u = u / (np.linalg.norm(u) or 1)
    v = np.cross(n, u)
    return np.stack([(P - P[0]) @ u, (P - P[0]) @ v], axis=1)


def convex_planar(P):
    n = newell(P)
    if np.linalg.norm(n) < 1e-9:
        return False
    n = n / np.linalg.norm(n)
    if np.abs((P - P[0]) @ n).max() > 0.5:
        return False
    for i in range(len(P)):
        a, b, c = P[i - 1], P[i], P[(i + 1) % len(P)]
        if np.dot(np.cross(b - a, c - b), n) < -1e-6:
            return False
    return True


def triangulate(P):
    """ear clipping on a simple planar loop (keeps the loop's winding)"""
    Q = frame(np.asarray(P, float))
    idx = list(range(len(Q)))
    area = sum(Q[i][0] * Q[(i + 1) % len(Q)][1] - Q[(i + 1) % len(Q)][0] * Q[i][1] for i in range(len(Q)))
    sgn = 1 if area > 0 else -1
    tris, guard = [], 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = Q[i0], Q[i1], Q[i2]
            cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cr * sgn <= 1e-9:
                continue
            if any(inside(Q[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def inside(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def ccw(outline):
    a = sum(outline[i][0] * outline[(i + 1) % len(outline)][1] - outline[(i + 1) % len(outline)][0] * outline[i][1]
            for i in range(len(outline)))
    return list(outline) if a > 0 else list(reversed(outline))


# ------------------------------------------------------------------------------------------------ shapes
def prism(outline, h, name="prism"):
    """a 2D outline (x, y) pushed up h: any simple polygon, concave too"""
    o = ccw(outline)
    n = len(o)
    v = [(x, y, 0) for x, y in o] + [(x, y, h) for x, y in o]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]           # bottom (down), top (up)
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return Mesh(v, faces, name)


def box(w, d, h):
    return prism([(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)], h, "box")


def ngon(r, sides):
    return [(r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]


def cylinder(r, h, sides=16):
    return prism(ngon(r, sides), h, "cylinder")


def cone(r, h, sides=16, r_top=0.0):
    """a cone, or a frustum with r_top > 0"""
    b = ngon(r, sides)
    if r_top <= 0:
        v = [(x, y, 0) for x, y in b] + [(0, 0, h)]
        faces = [list(range(sides - 1, -1, -1))] + [[i, (i + 1) % sides, sides] for i in range(sides)]
        return Mesh(v, faces, "cone")
    t = ngon(r_top, sides)
    v = [(x, y, 0) for x, y in b] + [(x, y, h) for x, y in t]
    faces = [list(range(sides - 1, -1, -1)), list(range(sides, 2 * sides))]
    faces += [[i, (i + 1) % sides, sides + (i + 1) % sides, sides + i] for i in range(sides)]
    return Mesh(v, faces, "frustum")


def pyramid(w, d, h):
    v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (0, 0, h)]
    return Mesh(v, [[3, 2, 1, 0], [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]], "pyramid")


def wedge(w, d, h):
    """a ramp: w long (x), d wide (y), rising to h at +x"""
    v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (w / 2, -d / 2, h), (w / 2, d / 2, h)]
    faces = [[3, 2, 1, 0], [1, 2, 5, 4], [0, 1, 4], [2, 3, 5], [0, 4, 5, 3]]
    return Mesh(v, faces, "wedge")


def sphere(r, segs=12, rings=8):
    """sits on the ground: z from 0 to 2r"""
    v = [(0, 0, 0)]
    for j in range(1, rings):
        t = math.pi * j / rings
        z, rr = r - r * math.cos(t), r * math.sin(t)
        v += [(rr * math.cos(2 * math.pi * k / segs), rr * math.sin(2 * math.pi * k / segs), z) for k in range(segs)]
    v.append((0, 0, 2 * r))
    top = len(v) - 1

    def ring(j, k):
        return 1 + (j - 1) * segs + k % segs
    faces = [[ring(1, k + 1), ring(1, k), 0] for k in range(segs)]
    for j in range(1, rings - 1):
        faces += [[ring(j, k), ring(j, k + 1), ring(j + 1, k + 1), ring(j + 1, k)] for k in range(segs)]
    faces += [[ring(rings - 1, k), ring(rings - 1, k + 1), top] for k in range(segs)]
    return Mesh(v, faces, "sphere")


def dome(r, segs=12, rings=4):
    """a half sphere on the ground (z from 0 to r)"""
    v = []
    for j in range(rings):
        t = (math.pi / 2) * j / rings
        z, rr = r * math.sin(t), r * math.cos(t)
        v += [(rr * math.cos(2 * math.pi * k / segs), rr * math.sin(2 * math.pi * k / segs), z) for k in range(segs)]
    v.append((0, 0, r))
    top = len(v) - 1

    def ring(j, k):
        return j * segs + k % segs
    faces = [list(range(segs - 1, -1, -1))]
    for j in range(rings - 1):
        faces += [[ring(j, k), ring(j, k + 1), ring(j + 1, k + 1), ring(j + 1, k)] for k in range(segs)]
    faces += [[ring(rings - 1, k), ring(rings - 1, k + 1), top] for k in range(segs)]
    return Mesh(v, faces, "dome")


def extrude_profile(profile, depth, name="profile"):
    """a side profile (x, z) - x along, z up - pushed through depth along y (centred)"""
    m = prism(profile, depth, name)
    # prism axes (x, y=z_profile, z=depth) -> world (x, y=depth-centred, z=profile z): a swap of two axes flips
    v = np.stack([m.v[:, 0], m.v[:, 2] - depth / 2, m.v[:, 1]], axis=1)
    return Mesh(v, m.f, name).flipped()


def stairs(w, steps, rise=16, run=32):
    """a solid flight going up toward +x, w wide; base at the origin, first step at x = 0"""
    p = [(0, 0), (steps * run, 0)]
    for k in range(steps, 0, -1):
        p += [(k * run, k * rise), ((k - 1) * run, k * rise)]
    return extrude_profile(p, w, "stairs")


def arch(w, h, depth, opening, spring, segs=8):
    """a wall w wide and h high with an arched opening (opening wide, straight sides up to spring, then a half circle)"""
    r = opening / 2
    p = [(-w / 2, 0), (-r, 0), (-r, spring)]
    p += [(-r * math.cos(math.pi * k / segs), spring + r * math.sin(math.pi * k / segs)) for k in range(1, segs)]
    p += [(r, spring), (r, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]
    return extrude_profile(p, depth, "arch")


def tube(r_out, r_in, h, sides=16):
    """a pipe section: a ring pushed up h"""
    o, i = ngon(r_out, sides), ngon(r_in, sides)
    v = [(x, y, 0) for x, y in o] + [(x, y, h) for x, y in o] + [(x, y, 0) for x, y in i] + [(x, y, h) for x, y in i]
    S = sides
    faces = []
    for k in range(S):
        a, b = k, (k + 1) % S
        faces.append([a, b, S + b, S + a])                       # outer wall
        faces.append([2 * S + b, 2 * S + a, 3 * S + a, 3 * S + b])   # inner wall (faces the axis)
        faces.append([S + a, S + b, 3 * S + b, 3 * S + a])       # top ring
        faces.append([b, a, 2 * S + a, 2 * S + b])               # bottom ring
    return Mesh(v, faces, "tube")


# ------------------------------------------------------------------------------------------------ combining
class Model:
    """ordered CSG steps [("add"|"sub", Mesh)] - the editor applies them in order, like stacking brushes"""

    def __init__(self, steps=None):
        self.steps = list(steps or [])

    def _other(self, other):
        return other.steps if isinstance(other, Model) else [("add", other)]

    def __add__(self, other):
        return Model(self.steps + self._other(other))

    def __sub__(self, other):
        if isinstance(other, Model):
            if any(op == "sub" for op, _ in other.steps):
                raise ValueError("subtracting a model that has its own holes: subtract its parts one by one")
            return Model(self.steps + [("sub", m) for _, m in other.steps])
        return Model(self.steps + [("sub", other)])

    def move(self, x=0, y=0, z=0):
        return Model([(op, m.move(x, y, z)) for op, m in self.steps])

    def rotate(self, yaw=0, pitch=0, roll=0):
        return Model([(op, m.rotate(yaw, pitch, roll)) for op, m in self.steps])

    def scale(self, sx=1, sy=None, sz=None):
        return Model([(op, m.scale(sx, sy, sz)) for op, m in self.steps])

    def mirror(self, axis="x"):
        return Model([(op, m.mirror(axis)) for op, m in self.steps])

    def bounds(self):
        b = [m.bounds() for op, m in self.steps if op == "add"] or [m.bounds() for _, m in self.steps]
        return np.min([x[0] for x in b], axis=0), np.max([x[1] for x in b], axis=0)

    def check(self):
        return [p for _, m in self.steps for p in m.check()]

    # --- editor output
    def write_brushes(self, workdir, tag="model"):
        os.makedirs(workdir, exist_ok=True)
        out = []
        for k, (op, m) in enumerate(self.steps):
            path = os.path.join(workdir, "%s_%02d_%s.t3d" % (tag, k, m.name))
            open(path, "w").write(polylist(m.polys()))
            out.append((path, op))
        return out

    def editor_commands(self, origin=(0, 0, 0), workdir=".", tag="model", short=None):
        """BRUSH IMPORT + MOVETO + ADD/SUBTRACT per step; SHORT maps a path to the editor's 8.3 form"""
        short = short or (lambda p: p)
        x, y, z = (int(round(c)) for c in origin)
        cmds = []
        for path, op in self.write_brushes(workdir, tag):
            cmds += ['BRUSH IMPORT FILE="%s"' % short(path), "BRUSH MOVETO X=%d Y=%d Z=%d" % (x, y, z),
                     "BRUSH ADD" if op == "add" else "BRUSH SUBTRACT"]
        return cmds

    def static_mesh_t3d(self, path, texture=TEX, uv_scale=1 / 256.0):
        """add-only models straight to a static mesh file (T3D 'Begin StaticMesh' 2.0): the added shapes' faces, no
        boolean (overlaps stay inside). Models with subtracts go through the editor's CSG (freeze_commands)."""
        if any(op == "sub" for op, _ in self.steps):
            raise ValueError("this model subtracts: freeze it through the editor (freeze_commands)")
        tris = [t for _, m in self.steps for P in m.polys() for t in fan(P)]
        write_static_mesh(path, tris, texture, uv_scale, os.path.splitext(os.path.basename(path))[0])
        return len(tris)

    # --- preview
    def preview(self, path, views=((35, -60), (25, 30)), title=None):
        """an offline picture: added shapes shaded, subtracted ones as red ghosts (a mock-up, not the CSG result)"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        lo, hi = self.bounds()
        span = (hi - lo).max() or 1
        mid = (hi + lo) / 2
        fig = plt.figure(figsize=(6 * len(views), 6), dpi=110)
        light = np.array([0.4, -0.5, 0.8])
        light /= np.linalg.norm(light)
        alpha = 0.55 if any(op == "sub" for op, _ in self.steps) else 1.0     # see the cuts through the walls
        for vi, (elev, azim) in enumerate(views):
            ax = fig.add_subplot(1, len(views), vi + 1, projection="3d")
            for op, m in self.steps:
                P = m.polys()
                if op == "add":
                    cols = []
                    for p in P:
                        n = newell(p)
                        n = n / (np.linalg.norm(n) or 1)
                        s = 0.35 + 0.6 * max(0.0, float(n @ light))
                        cols.append((0.62 * s, 0.6 * s, 0.55 * s, alpha))
                    ax.add_collection3d(Poly3DCollection(P, facecolors=cols, edgecolors=(0, 0, 0, 0.25), linewidths=0.4))
                else:
                    ax.add_collection3d(Poly3DCollection(P, facecolors=(0.9, 0.15, 0.1, 0.45), edgecolors=(0.75, 0.05, 0.05, 0.9), linewidths=0.8))
            for setter, c in ((ax.set_xlim, 0), (ax.set_ylim, 1), (ax.set_zlim, 2)):
                setter(mid[c] - span / 2, mid[c] + span / 2)
            ax.view_init(elev, azim)
            ax.set_box_aspect((1, 1, 1))
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_zlabel("z")
        if title:
            fig.suptitle(title)
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        return path


def fan(P):
    return [(P[0], P[i], P[i + 1]) for i in range(1, len(P) - 1)]


# ------------------------------------------------------------------------------------------------ file writers
def polylist(polys, texture=TEX):
    """a T3D PolyList (what BRUSH IMPORT reads)"""
    s = "Begin PolyList\n"
    for k, P in enumerate(polys):
        n = newell(P)
        n = n / (np.linalg.norm(n) or 1)
        tu = np.array([1.0, 0, 0]) if abs(n[2]) > 0.5 else np.array([-n[1], n[0], 0]) / (math.hypot(n[0], n[1]) or 1)
        tv = np.cross(n, tu)
        s += "   Begin Polygon Texture=%s Link=%d\n" % (texture, k)
        s += "      Origin   %+.6f,%+.6f,%+.6f\n" % tuple(P[0])
        s += "      Normal   %+.6f,%+.6f,%+.6f\n" % tuple(n)
        s += "      TextureU %+.6f,%+.6f,%+.6f\n" % tuple(tu)
        s += "      TextureV %+.6f,%+.6f,%+.6f\n" % tuple(tv)
        s += "".join("      Vertex   %+.6f,%+.6f,%+.6f\n" % tuple(v) for v in P)
        s += "   End Polygon\n"
    return s + "End PolyList\n"


def write_static_mesh(path, tris, texture=TEX, uv_scale=1 / 256.0, name="Mesh"):
    """the T3D static mesh text the editor's StaticMeshFactory reads (Version 2.0); planar UVs per triangle"""
    L = ["Begin StaticMesh Name=%s" % name,
         "Version=2.000000 BoundingBox.Min.X=0 BoundingBox.Min.Y=0 BoundingBox.Min.Z=0 BoundingBox.Max.X=0 BoundingBox.Max.Y=0 BoundingBox.Max.Z=0"]
    for a, b, c in tris:
        n = np.cross(b - a, c - a)
        n = n / (np.linalg.norm(n) or 1)
        tu = np.array([1.0, 0, 0]) if abs(n[2]) > 0.5 else np.array([-n[1], n[0], 0]) / (math.hypot(n[0], n[1]) or 1)
        tv = np.cross(n, tu)
        L += ["Begin Triangle", "Texture %s" % texture, "SmoothingMask 1", "PolyFlags 0"]
        L += ["Vertex %d %.4f %.4f %.4f %.5f %.5f" % (i, p[0], p[1], p[2], (p @ tu) * uv_scale, (p @ tv) * uv_scale)
              for i, p in enumerate((a, b, c))]
        L.append("End Triangle")
    L.append("End StaticMesh")
    open(path, "w").write("\n".join(L) + "\n")


def read_polylist(text):
    """the polygons of a T3D PolyList (MAP SAVEPOLYS output, brush files) as vertex arrays"""
    polys, cur = [], None
    for line in text.splitlines():
        t = line.strip()
        if t.startswith("Begin Polygon"):
            cur = []
        elif t.startswith("Vertex") and cur is not None:
            cur.append([float(x) for x in t.split(None, 1)[1].split(",")])
        elif t.startswith("End Polygon") and cur is not None:
            if len(cur) >= 3:
                polys.append(np.array(cur))
            cur = None
    return polys
