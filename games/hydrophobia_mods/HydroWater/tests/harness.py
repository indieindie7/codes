"""HydroWater test harness: the upgrade plan's first-milestone tests, baseline vs upgraded.

    python tests\harness.py [test ...]        (tests: rest, dam, crate, wading, tub; default all)

Needs numpy and Pillow (the kimodo venv has both). Writes PNG frames and a summary.txt per test
into tests\out\<test>\ and prints the numbers that matter. Units: dx = 20, g = 980 (think cm),
water density 1.
"""
import ctypes
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
DLL = os.path.join(os.path.dirname(HERE), "bin", "hydrowater.dll")
DX, G = 20.0, 980.0


class Opts(ctypes.Structure):
    _fields_ = [("displacement", ctypes.c_int), ("capped_stamp", ctypes.c_int),
                ("face_walls", ctypes.c_int), ("clamps", ctypes.c_int),
                ("alpha", ctypes.c_float), ("c_adapt", ctypes.c_float), ("edge_damp", ctypes.c_float),
                ("recon", ctypes.c_int)]


lib = ctypes.CDLL(DLL)
P = ctypes.c_void_p
F = ctypes.c_float
lib.hw_create.restype = P
lib.hw_create.argtypes = [ctypes.c_int, ctypes.c_int, F, F, F]
lib.hw_destroy.argtypes = [P]
lib.hw_set_opts.argtypes = [P, ctypes.POINTER(Opts)]
for name in ("hw_width", "hw_height", "hw_stride"):
    getattr(lib, name).restype = ctypes.c_int
    getattr(lib, name).argtypes = [P]
for name in ("hw_depth", "hw_hu", "hw_hv", "hw_u", "hw_v", "hw_bed", "hw_wall", "hw_body"):
    getattr(lib, name).restype = ctypes.POINTER(F)
    getattr(lib, name).argtypes = [P]
lib.hw_fill.argtypes = [P, F]
lib.hw_wall_rect.argtypes = [P, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lib.hw_wall_segment.argtypes = [P, F, F, F, F]
lib.hw_bodies_begin.argtypes = [P]
lib.hw_body_box.restype = F
lib.hw_body_box.argtypes = [P, F, F, F, F, F, F]
lib.hw_body_disc.restype = F
lib.hw_body_disc.argtypes = [P, F, F, F, F, F]
lib.hw_stamp.argtypes = [P, F, F, F, F, F, F, F, F, F]
lib.hw_probe.restype = ctypes.c_int
lib.hw_probe.argtypes = [P, F, F] + [ctypes.POINTER(F)] * 5
lib.hw_body_force.restype = F
lib.hw_body_force.argtypes = [P, ctypes.POINTER(F), ctypes.c_int, F, F, F, F, F, F, ctypes.POINTER(F), ctypes.POINTER(F)]
lib.hw_step.restype = ctypes.c_int
lib.hw_step.argtypes = [P, F]
lib.hw_volume.restype = ctypes.c_double
lib.hw_volume.argtypes = [P]
lib.hw_smax.restype = F
lib.hw_smax.argtypes = [P]


class Sheet:
    def __init__(self, w, h, upgraded, **kw):
        self.s = lib.hw_create(w, h, DX, G, 0.5)
        self.w, self.h = w, h
        self.stride = lib.hw_stride(self.s)
        o = Opts()
        if upgraded:
            o.displacement = o.capped_stamp = o.face_walls = o.clamps = o.recon = 1
        for k, v in kw.items():
            setattr(o, k, v)
        lib.hw_set_opts(self.s, ctypes.byref(o))
        self.steps = 0

    def plane(self, name):
        p = getattr(lib, name)(self.s)
        a = np.ctypeslib.as_array(p, shape=((self.h + 4) * self.stride,))
        return a.reshape(self.h + 4, self.stride)[2:-2, 2:-2]

    @property
    def depth(self): return self.plane("hw_depth")
    @property
    def bed(self): return self.plane("hw_bed")
    @property
    def u(self): return self.plane("hw_u")
    @property
    def v(self): return self.plane("hw_v")
    @property
    def eta(self): return self.bed + self.depth

    def fill(self, eta): lib.hw_fill(self.s, eta)
    def step(self, dt):
        n = lib.hw_step(self.s, dt)
        self.steps += n
        return n
    def volume(self): return lib.hw_volume(self.s)
    def bodies_begin(self): lib.hw_bodies_begin(self.s)
    def body_box(self, x0, z0, x1, z1, yb, yt): return lib.hw_body_box(self.s, x0, z0, x1, z1, yb, yt)
    def body_disc(self, x, z, r, yb, yt): return lib.hw_body_disc(self.s, x, z, r, yb, yt)
    def stamp(self, px, pz, x, z, r, yb, vx, vz, dt): lib.hw_stamp(self.s, px, pz, x, z, r, yb, vx, vz, dt)

    def probe(self, x, z):
        out = [F() for _ in range(5)]
        ok = lib.hw_probe(self.s, x, z, *[ctypes.byref(o) for o in out])
        return (ok,) + tuple(o.value for o in out)

    def body_force(self, probes, V, A, rho, ramp, cd, kdamp, vel):
        arr = (F * (6 * len(probes)))(*[c for p in probes for c in p])
        bv = (F * 3)(*vel)
        f = (F * 3)()
        ratio = lib.hw_body_force(self.s, arr, len(probes), V, A, rho, ramp, cd, kdamp, bv, f)
        return list(f), ratio

    def close(self): lib.hw_destroy(self.s); self.s = None


def png(path, field, lo, hi, scale=4):
    a = np.clip((field - lo) / (hi - lo), 0, 1)
    img = Image.fromarray((a * 255).astype(np.uint8))
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)


def outdir(name):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    return d


def report(name, lines):
    d = outdir(name)
    with open(os.path.join(d, "summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("== " + name)
    for l in lines:
        print("   " + l)


# ----------------------------------------------------------------------------- tests

def test_rest():
    """Lake at rest on an uneven bed: velocity must stay zero (well-balanced)."""
    lines = []
    for mode in ("baseline", "upgraded"):
        s = Sheet(40, 30, mode == "upgraded")
        bed = s.bed
        j, i = np.mgrid[0:30, 0:40]
        bed[:] = 8 * np.sin(i / 3.0) * np.cos(j / 2.5) + 10 * (i > 25) + (j % 4 == 0) * 6
        s.fill(40.0)
        v0 = s.volume()
        for _ in range(200):
            s.step(1 / 60)
        vmax = max(np.abs(s.u).max(), np.abs(s.v).max())
        lines.append("%s: %d sub-steps, max |u|,|v| = %.3e units/s, volume drift %.2e" % (
            mode, s.steps, vmax, (s.volume() - v0) / v0))
        png(os.path.join(outdir("rest"), mode + "_eta.png"), s.eta, 0, 60)
        s.close()
    report("rest", lines)


def test_dam():
    """Dam break onto dry stairs: one front, no negative depths, volume conserved."""
    lines = []
    for mode in ("baseline", "upgraded"):
        s = Sheet(80, 16, mode == "upgraded")
        bed = s.bed
        j, i = np.mgrid[0:16, 0:80]
        bed[:] = np.where(i >= 40, ((i - 40) // 5) * 4.0, 0.0)      # stairs rising to the right
        d = s.depth
        d[:, :30] = 40.0
        v0 = s.volume()
        od = outdir("dam")
        negs, fronts = 0, []
        t = 0.0
        for f in range(90):
            s.step(1 / 30)
            t += 1 / 30
            dep = s.depth
            negs += int((dep < 0).sum())
            wet = np.where(dep[8] > 0.05)[0]
            fronts.append((t, (wet.max() + 1) * DX if len(wet) else 0))
            if f % 15 == 0:
                png(os.path.join(od, "%s_%03d.png" % (mode, f)), s.eta, 0, 50)
        # a thin "racing film": cells wet below 0.5 units ahead of the main front
        film = int(((s.depth[8] > 0.001) & (s.depth[8] < 0.5)).sum())
        lines.append("%s: front at %.0f units after 3 s, negative cells %d, film cells %d, volume drift %.2e, sub-steps %d" % (
            mode, fronts[-1][1], negs, film, (s.volume() - v0) / v0, s.steps))
        s.close()
    report("dam", lines)


def test_crate():
    """Stage 1: a crate lowered into still water makes one ring that grows at sqrt(g h)."""
    lines = []
    h0 = 30.0
    for mode in ("baseline", "upgraded"):
        s = Sheet(80, 80, mode == "upgraded")
        s.fill(h0)
        v0 = s.volume()
        od = outdir("crate")
        cx = cz = 40 * DX
        half = 30.0
        t = 0.0
        radii = []
        for f in range(120):
            dt = 1 / 60
            t += dt
            # the crate sinks 15 units over the first 0.25 s, then sits
            depth = min(15.0, 60.0 * t)
            s.bodies_begin()
            s.body_box(cx - half, cz - half, cx + half, cz + half, h0 - depth, h0 + 30)
            s.step(dt)
            if f % 10 == 9:
                eta = s.eta
                dev = np.abs(eta - h0)
                dev[36:44, 36:44] = 0            # ignore the crate's own footprint
                j, i = np.mgrid[0:80, 0:80]
                r = np.sqrt(((i + 0.5) * DX - cx) ** 2 + ((j + 0.5) * DX - cz) ** 2)
                if dev.max() > 0.05:
                    # the ring: radius of the peak deviation (the crest travels at about sqrt(g h))
                    radii.append((t, float(r.flat[int(dev.argmax())]), float(dev.max())))
                png(os.path.join(od, "%s_%03d.png" % (mode, f)), eta, h0 - 4, h0 + 4)
        c = math.sqrt(G * h0)
        if radii:
            # front speed from a least-squares line through (t, r) while the ring is still inside
            inside = [(tt, rr) for tt, rr, _ in radii if rr < 36 * DX]
            if len(inside) >= 2:
                ts = np.array([a for a, _ in inside]); rs = np.array([b for _, b in inside])
                speed = float(np.polyfit(ts, rs, 1)[0])
            else:
                speed = 0.0
            t1, r1, a1 = radii[-1]
            lines.append("%s: ring crest at radius %.0f units at %.2f s, crest speed %.0f units/s vs sqrt(g h) = %.0f, peak |eta - h0| %.2f" % (
                mode, r1, t1, speed, c, max(a for _, _, a in radii)))
        else:
            lines.append("%s: no disturbance at all (expected for the baseline: it has no displacement)" % mode)
        lines.append("%s: volume drift %.2e, sub-steps %d" % (mode, (s.volume() - v0) / v0, s.steps))
        s.close()
    report("crate", lines)


def test_wading():
    """Stages 1 + 2: a character walking through a pool leaves a mound ahead and a wake behind."""
    lines = []
    h0 = 25.0
    for mode in ("baseline", "upgraded"):
        s = Sheet(120, 60, mode == "upgraded", c_adapt=0.2)
        s.fill(h0)
        v0 = s.volume()
        od = outdir("wading")
        r, speed = 15.0, 120.0
        x, z = 10 * DX, 30 * DX
        t = 0.0
        for f in range(150):
            dt = 1 / 60
            px = x
            x += speed * dt
            t += dt
            s.bodies_begin()
            s.body_disc(x, z, r, 0.0, h0 + 50)          # feet on the floor, body through the surface
            s.stamp(px, z, x, z, r, 0.0, speed, 0.0, dt)
            s.step(dt)
            if f % 30 == 29:
                png(os.path.join(od, "%s_%03d.png" % (mode, f)), s.eta, h0 - 3, h0 + 3)
        eta = s.eta
        ci = int(x / DX)
        ahead = eta[30, min(ci + 2, 119)] - h0
        behind = eta[30, max(ci - 3, 0)] - h0
        lines.append("%s: after %.1f s at x = %.0f: surface ahead %+.2f, behind %+.2f, max |u| %.0f units/s, volume drift %.2e, sub-steps %d" % (
            mode, t, x, ahead, behind, np.abs(s.u).max(), (s.volume() - v0) / v0, s.steps))
        s.close()
    report("wading", lines)


def test_tub():
    """Stage 3: a half-density box dropped into a tub settles without bobbing forever.
    Buoyancy is rho g times the displaced volume the rasteriser reports (exact for the box and
    continuous in height); "hard" has no drag or damping, "smooth" adds quadratic drag against
    the water's velocity and damping near critical for the buoyancy spring."""
    lines = []
    h0 = 40.0
    for mode in ("hard", "smooth"):
        s = Sheet(40, 40, True)
        s.fill(h0)
        od = outdir("tub")
        side = 30.0
        V = side ** 3
        rho_w, rho_b = 1.0, 0.5
        m = rho_b * V
        cx = cz = 20 * DX
        y, vy = h0 + 20.0, 0.0           # bottom face 20 units above the surface
        t = 0.0
        hist = []
        settle_t = None
        vdisp = 0.0
        for f in range(600):
            dt = 1 / 120
            t += dt
            pts = []
            for px, pz in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0)):
                pts.append((cx + px * side * 0.45, y, cz + pz * side * 0.45, 0.0, vy, 0.0))
            for px, pz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                pts.append((cx + px * side * 0.45, y + side * 0.5, cz + pz * side * 0.45, 0.0, vy, 0.0))
            if mode == "hard":
                f3 = [0.0, 0.0, 0.0]
            else:
                kd = 1.4 * math.sqrt(rho_w * G * side * side * m)   # 2 zeta sqrt(k m), zeta 0.7
                f3, ratio = s.body_force(pts, 0.0, side * side, rho_w, 0.0, 0.8, kd, (0.0, vy, 0.0))
            ay = (rho_w * G * vdisp + f3[1]) / m - G
            vy += ay * dt
            y += vy * dt
            if y < 0:
                y, vy = 0.0, 0.0
            s.bodies_begin()
            vdisp = s.body_box(cx - side / 2, cz - side / 2, cx + side / 2, cz + side / 2, y, y + side)
            s.step(dt)
            hist.append((t, y, vy))
            if settle_t is None and t > 0.5 and all(abs(v) < 2.0 for _, _, v in hist[-60:]):
                settle_t = t
            if f % 60 == 0:
                png(os.path.join(od, "%s_%03d.png" % (mode, f)), s.eta, h0 - 5, h0 + 5)
        eta_c = s.probe(cx + side * 0.6, cz)[1]
        sub = eta_c - y
        lines.append("%s: settled %s, final immersion %.1f of %.0f units (Archimedes: %.0f), box bottom y = %.1f, final |vy| %.2f, max |vy| after 1 s %.1f" % (
            mode, ("at %.2f s" % settle_t) if settle_t else "NOT within 5 s", sub, side, side * rho_b / rho_w, y, abs(hist[-1][2]),
            max(abs(v) for tt, _, v in hist if tt > 1.0)))
        with open(os.path.join(od, mode + "_y.csv"), "w") as fcsv:
            fcsv.write("t,y,vy\n")
            for row in hist:
                fcsv.write("%.4f,%.3f,%.3f\n" % row)
        s.close()
    report("tub", lines)


TESTS = {"rest": test_rest, "dam": test_dam, "crate": test_crate, "wading": test_wading, "tub": test_tub}

if __name__ == "__main__":
    names = sys.argv[1:] or list(TESTS)
    for n in names:
        TESTS[n]()
