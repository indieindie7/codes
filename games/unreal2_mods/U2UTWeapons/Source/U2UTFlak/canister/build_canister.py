"""GES Bio Rifle view model with a fuel canister slung under the barrel (two-handed
flamethrower look): writes Models/ase_can/BioV000-090.ase = UT's 91 frames + the canister.

The canister is built once in the idle frame's space (BioV022) and carried into every frame
by an affine transform fitted to the gun's vertices around the mount point, so it follows the
select/put-down squash as well as the recoil. Textured from BioAtlas (no new texture):
  body     the grey hazard panel (red stripe -> a band round the tank, vents -> rings)
  windows  the goo window patch, so bio_gun.hlsl draws them as see-through glowing goo
  caps     the round fitting; straps and pipe the dark hose
Run: py -3.13 build_canister.py   (then rebuild U2UTFlakSM.usx with make_import_script.py --canister)
"""
import math, os, re
import numpy as np
import ase

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Unreal II The Awakening\U2UTFlak"
SRC = os.path.join(GAME, "Models", "ase")
OUT = os.path.join(GAME, "Models", "ase_can")
BASE = 22                       # the idle frame the canister is placed in

# placement in the idle frame (gun units: barrel along +X, Z up, grip at x 25..50)
CX0, CX1 = -22.0, 52.0          # tank length along X
CY, CZ = 0.0, -44.0             # axis
RAD = 19.0
SIDES = 16
MOUNT = np.array([15.0, 0.0, -30.0])   # where the tank meets the gun (fit centre)

# atlas rectangles in image space (u, v from the top) -> ASE stores v flipped
PANEL = (0.07, 0.04, 0.44, 0.46)        # grey hazard panel
GOO = (0.52, 0.03, 0.66, 0.15)          # goo window patch (bio_gun.hlsl mask a)
CAP = (0.425, 0.935, 0.055)             # round fitting: centre u, v, radius
HOSE = (0.30, 0.62, 0.42, 0.70)         # dark hose


class Mesh:
    def __init__(self):
        self.v, self.f, self.uv = [], [], []      # uv per face corner (3 per face)

    def vert(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def tri(self, a, b, c, ua, ub, uc):
        self.f.append((a, b, c))
        self.uv += [ua, ub, uc]

    def quad(self, a, b, c, d, ua, ub, uc, ud):
        self.tri(a, b, c, ua, ub, uc)
        self.tri(a, c, d, ua, uc, ud)


def rect_uv(r, s, t):
    """point (s, t) in 0..1 of an atlas rectangle"""
    return (r[0] + (r[2] - r[0]) * s, r[1] + (r[3] - r[1]) * t)


def ring(m, x, radius):
    return [m.vert((x, CY + radius * math.cos(2 * math.pi * k / SIDES), CZ + radius * math.sin(2 * math.pi * k / SIDES)))
            for k in range(SIDES)]


def window(k):
    # two windows, on the left and right flanks of the tank
    return k in (3, 4, 11, 12)


def tube(m, x0, x1, radius, uvrect=None, windows=False):
    a, b = ring(m, x0, radius), ring(m, x1, radius)
    for k in range(SIDES):
        k1 = (k + 1) % SIDES
        if windows and window(k):
            r, s0, s1 = GOO, (k % 2) * 0.5, (k % 2) * 0.5 + 0.5
            uvs = [rect_uv(r, 0, s0), rect_uv(r, 1, s0), rect_uv(r, 1, s1), rect_uv(r, 0, s1)]
        else:
            r = uvrect or PANEL
            s0, s1 = k / SIDES, (k + 1) / SIDES
            # around the tank -> down the panel, along the tank -> across it (the red stripe
            # becomes a band, the vents become rings)
            uvs = [rect_uv(r, 0, s0), rect_uv(r, 1, s0), rect_uv(r, 1, s1), rect_uv(r, 0, s1)]
        # winding: outward normals
        m.quad(a[k], b[k], b[k1], a[k1], *uvs)
    return a, b


def cap(m, rim, x, outward, goo=False):
    c = m.vert((x + outward * 4.0, CY, CZ))     # slightly domed
    for k in range(SIDES):
        if goo:
            # a round glass gauge full of goo (the goo patch, so bio_gun.hlsl makes it liquid)
            g0, g1 = rect_uv(GOO, 0.5 + 0.5 * math.cos(2 * math.pi * k / SIDES), 0.5 + 0.5 * math.sin(2 * math.pi * k / SIDES)),                 rect_uv(GOO, 0.5 + 0.5 * math.cos(2 * math.pi * (k + 1) / SIDES), 0.5 + 0.5 * math.sin(2 * math.pi * (k + 1) / SIDES))
            gc = rect_uv(GOO, 0.5, 0.5)
            if outward > 0:
                m.tri(c, rim[k], rim[(k + 1) % SIDES], gc, g0, g1)
            else:
                m.tri(c, rim[(k + 1) % SIDES], rim[k], gc, g1, g0)
            continue
        k1 = (k + 1) % SIDES
        ang0, ang1 = 2 * math.pi * k / SIDES, 2 * math.pi * k1 / SIDES
        u0 = (CAP[0] + CAP[2] * math.cos(ang0), CAP[1] + CAP[2] * math.sin(ang0))
        u1 = (CAP[0] + CAP[2] * math.cos(ang1), CAP[1] + CAP[2] * math.sin(ang1))
        if outward > 0:
            m.tri(c, rim[k], rim[k1], (CAP[0], CAP[1]), u0, u1)
        else:
            m.tri(c, rim[k1], rim[k], (CAP[0], CAP[1]), u1, u0)


def box(m, lo, hi, r):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = [m.vert((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    # p index = xi*4 + yi*2 + zi
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    for a, b, c, d in faces:
        m.quad(p[a], p[b], p[c], p[d], rect_uv(r, 0, 0), rect_uv(r, 1, 0), rect_uv(r, 1, 1), rect_uv(r, 0, 1))


def canister():
    m = Mesh()
    a, b = tube(m, CX0, CX1, RAD, windows=True)
    cap(m, a, CX0, -1)
    cap(m, b, CX1, +1, goo=True)       # the end facing the player (+X points back)
    # clamp bands and the straps up to the gun
    for x in (CX0 + 8, CX1 - 8):
        tube(m, x - 2.5, x + 2.5, RAD + 1.5, uvrect=HOSE)
        box(m, (x - 3, -5, CZ + RAD - 1), (x + 3, 5, CZ + RAD + 26), HOSE)
    # feed pipe off the tank's left flank, up into the gun body (kept clear of the gauge)
    py = CY - RAD - 1
    box(m, (CX1 - 14, py - 5, CZ - 2.5), (CX1 - 9, py, CZ + 2.5), HOSE)
    box(m, (CX1 - 14, py - 5, CZ), (CX1 - 9, py, CZ + 40), HOSE)
    return m


def fit_affine(base, frame):
    """3x4 affine taking the idle frame to this frame, weighted toward the mount"""
    d = np.linalg.norm(base - MOUNT, axis=1)
    w = np.exp(-(d / 60.0) ** 2) + 1e-3
    X = np.hstack([base, np.ones((len(base), 1))]) * w[:, None]
    Y = frame * w[:, None]
    A, *_ = np.linalg.lstsq(X, Y, rcond=None)
    return A                                    # (4, 3): p' = [p, 1] @ A


def write(path, name, v, f, uv):
    out = ["*3DSMAX_ASCIIEXPORT\t200", '*COMMENT "ue1_to_ase + bio canister"', "*GEOMOBJECT {",
           f'\t*NODE_NAME "{name}"', "\t*MESH {", "\t\t*TIMEVALUE 0",
           f"\t\t*MESH_NUMVERTEX {len(v)}", f"\t\t*MESH_NUMFACES {len(f)}", "\t\t*MESH_VERTEX_LIST {"]
    out += [f"\t\t\t*MESH_VERTEX {i}\t{p[0]:.5f}\t{p[1]:.5f}\t{p[2]:.5f}" for i, p in enumerate(v)]
    out += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
    out += [f"\t\t\t*MESH_FACE {i}: A: {a} B: {b} C: {c} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0"
            for i, (a, b, c) in enumerate(f)]
    out += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(uv)}", "\t\t*MESH_TVERTLIST {"]
    out += [f"\t\t\t*MESH_TVERT {i}\t{u:.6f}\t{t:.6f}\t0.0000" for i, (u, t) in enumerate(uv)]
    out += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(f)}", "\t\t*MESH_TFACELIST {"]
    out += [f"\t\t\t*MESH_TFACE {i}\t{3 * i}\t{3 * i + 1}\t{3 * i + 2}" for i in range(len(f))]
    out += ["\t\t}", "\t}", "}", ""]
    open(path, "w").write("\n".join(out))


def main():
    os.makedirs(OUT, exist_ok=True)
    can = canister()
    cv = np.array(can.v)
    # atlas image space -> ASE (v flipped), as the original frames store it
    can_uv = [(u, 1.0 - t) for u, t in can.uv]
    base = np.array(ase.read(os.path.join(SRC, f"BioV{BASE:03d}.ase"))["v"])
    for i in range(91):
        g = ase.read(os.path.join(SRC, f"BioV{i:03d}.ase"))
        A = fit_affine(base, np.array(g["v"]))
        moved = np.hstack([cv, np.ones((len(cv), 1))]) @ A
        n = len(g["v"])
        v = list(g["v"]) + [tuple(p) for p in moved]
        f = list(g["f"]) + [(a + n, b + n, c + n) for a, b, c in can.f]
        tv = np.array(g["tv"])
        uv = []
        for tf in g["tf"]:
            uv += [tuple(tv[j][:2]) for j in tf]
        uv += can_uv
        write(os.path.join(OUT, f"BioV{i:03d}.ase"), f"BioV{i:03d}", v, f, uv)
    print(f"91 frames -> {OUT} (+{len(cv)} verts, +{len(can.f)} faces each)")


if __name__ == "__main__":
    main()
