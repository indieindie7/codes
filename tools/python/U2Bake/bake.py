r"""U2Bake - scene-wide light bake for Unreal II levels, offline (no editor, no game).

    py bake.py [map.t3d] [--scene dump.u2mv] [--ase DIR ...] [--out bake.json] [--ply bake.ply]
               [--rays 64] [--bounces 1] [--threads 6] [--only PATTERN ...] [--changed PATTERN ... --radius 1500]
               [--u2bk bake.u2bk --mode add|replace --gain 1 --terms sky,bounce]
               [--calib] [--fill 24 --fill-t3d fill.t3d] [--zones zones.txt]

Geometry comes from
  --scene: the editor's own dump (bridge command `!meshverts * <file>`, U2EdBridge_ops.dll): every
           StaticMeshActor with the engine's render vertices (the order of its per-instance colour stream),
           triangles, LocalToWorld, current vertex colours, zone, and every light with its engine values.
           Stock meshes (Flora_M, Terran_DecoM, ...) are included - no ASE needed.
  T3D + --ase: MAP EXPORT / generator T3D and the ASE sources (actors not in the dump; old route).
For each sample (an engine vertex, or a welded ASE vertex) it computes, in ENGINE UNITS (1.0 = vertex colour
byte 255, see LIGHTING.md "Calibration"):
    direct  = sun + point lights, UE2's own formula (2*cos*smoothstep falloff), shadow rays where the engine
              traces them (receiver flag 0x268&0x10)
    sky     = cosine-weighted sky visibility * --sky
    bounce  = one diffuse bounce (hits: albedo * (direct + sky*skyhit) at the hit point)
with bake_kernel.dll (C, BVH, threads). BSP and terrain are not in the scene yet (they neither occlude nor
reflect), so engine shadows cast by BSP/terrain are missing from `direct`.

Write-back (LIGHTING.md, "Write-back"):
  --u2bk F     per-vertex colours for `!bakeload F` (engine-vertex actors only), mode add (the engine keeps
               its own direct light, we add --terms, default sky,bounce) or replace (ours entirely, default
               terms direct,sky,bounce)
  --calib      compare our `direct` with the engine's colours in the dump (needs --scene after a LIGHT APPLY)
  --fill N     fit N unshadowed-style fill lights to the indirect light; --fill-t3d writes them as Light
               actors for MAP IMPORTADD (then MAP REBUILD + LIGHT APPLY). Don't also add `bounce` with --u2bk.
  --zones F    per-zone AmbientBrightness/Hue/Saturation suggestions as `!setprop` lines
Output JSON: {"actors": {Name: {"mesh", "engine": bool, "verts": [[lx,ly,lz, dR,dG,dB, sR,sG,sB, bR,bG,bB]]}}}
Incremental: --changed PATTERN (+ --radius R) re-bakes changed actors and those within R.
"""
import argparse, array, ctypes, fnmatch, json, math, os, re, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LE_SUNLIGHT = 0x16

# ---------------------------------------------------------------------------------------------- engine maths
def fgethsv(h, s, v):
    """Engine.dll FGetHSV(H, S, V) (0x10465140): brightness curve, 3-sector hue, saturation 255 = white"""
    b = v * 1.4 / 255.0
    b = b * 0.7 / (0.01 + math.sqrt(b)) if b > 0 else 0.0
    b = min(1.0, max(0.0, b))
    if h < 86:
        hue = ((85 - h) / 85.0, h / 85.0, 0.0)
    elif h < 171:
        hue = (0.0, (170 - h) / 85.0, (h - 85) / 85.0)
    else:
        hue = ((h - 170) / 85.0, 0.0, (255 - h) / 84.0)
    f = s / 255.0
    return tuple(((1 - c) * f + c) * b for c in hue)


def light_colour(hue, sat, bright, level_brightness=1.0):
    """FDynamicLight::Update, LT_Steady: FGetHSV(Hue, Sat, 255) * 1.0 * LightBrightness/255 * Level.Brightness"""
    return tuple(c * bright / 255.0 * level_brightness for c in fgethsv(hue, sat, 255))


def world_light_radius(radius_byte):
    return 25.0 * (radius_byte + 1)            # AActor::WorldLightRadius (0x10301e60)


def fit_hsv(rgb, v_fixed=None):
    """(H, S, V, error) so that fgethsv(H,S,V) ~ rgb; with v_fixed, also the scale k: fgethsv(H,S,v_fixed)*k ~ rgb"""
    best = None
    for h in range(0, 256, 2):
        for s in range(0, 256, 5):
            u = fgethsv(h, s, 255)
            uu = sum(c * c for c in u)
            if uu <= 0:
                continue
            k = max(0.0, sum(a * b for a, b in zip(u, rgb)) / uu)
            err = sum((k * a - b) ** 2 for a, b in zip(u, rgb))
            if best is None or err < best[3]:
                best = (h, s, k, err)
    h, s, k, err = best
    if v_fixed is not None:
        return h, s, k, err
    # k is relative to V=255: find V with fgethsv brightness k * b(255)
    target = k * fgethsv(0, 255, 255)[0]
    v = min(range(256), key=lambda v: abs(fgethsv(0, 255, v)[0] - target))
    return h, s, v, err


def to_byte(x):
    return 0 if x <= 0 else 255 if x >= 1 else int(x * 255 + 0.5)

# ---------------------------------------------------------------------------------------------- T3D
_KV = re.compile(r"(\w+)=([-\d.eE+]+)")


def parse_t3d(text):
    actors = []
    for m in re.finditer(r"^\s*Begin Actor (.*?)$(.*?)^\s*End Actor", text, re.S | re.M):
        head, body = m.group(1), m.group(2)
        a = dict(re.findall(r"(\w+)=(\S+)", head))
        props = {}
        depth = 0
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("Begin "):
                depth += 1
            elif s.startswith("End "):
                depth -= 1
            elif depth == 0 and "=" in s:
                k, v = s.split("=", 1)
                props[k] = v
        a["props"] = props
        actors.append(a)
    return actors


def vec(s, keys=("X", "Y", "Z"), default=0.0):
    d = dict((k, float(v)) for k, v in _KV.findall(s or ""))
    return tuple(d.get(k, default) for k in keys)


def rot_axes(pitch, yaw, roll):
    """UE2 FRotationMatrix rows: the local X, Y, Z axes in world space (65536 units = 360 degrees)"""
    k = 2 * math.pi / 65536.0
    sp, cp = math.sin(pitch * k), math.cos(pitch * k)
    sy, cy = math.sin(yaw * k), math.cos(yaw * k)
    sr, cr = math.sin(roll * k), math.cos(roll * k)
    x = (cp * cy, cp * sy, sp)
    y = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    z = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return x, y, z


_BYTEENUM = {"LT_None": 0, "LT_Steady": 1, "LE_None": 0, "LE_Sunlight": LE_SUNLIGHT}


def tbyte(p, key, default):
    v = p.get(key)
    if v is None:
        return default
    if v in _BYTEENUM:
        return _BYTEENUM[v]
    try:
        return int(float(v))
    except ValueError:
        return default

# ---------------------------------------------------------------------------------------------- ASE
def load_ase(path):
    """engine-space mesh: verts (X negated back, see U2Avalon/tools/ase.py), tris, per-tri UV centre"""
    verts, tris, tv, tf = [], [], [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.split()
        if not s:
            continue
        if s[0] == "*MESH_VERTEX":
            verts.append((-float(s[2]), float(s[3]), float(s[4])))
        elif s[0] == "*MESH_FACE":
            tris.append((int(s[3]), int(s[5]), int(s[7])))
        elif s[0] == "*MESH_TVERT":
            tv.append((float(s[2]), float(s[3])))
        elif s[0] == "*MESH_TFACE":
            tf.append((int(s[2]), int(s[3]), int(s[4])))
    uvc = []
    if tv and len(tf) == len(tris):
        for f in tf:
            uvc.append((sum(tv[i][0] for i in f) / 3, sum(tv[i][1] for i in f) / 3))
    cx = [sum(v[k] for v in verts) / max(1, len(verts)) for k in range(3)]
    score = 0.0
    for a, b, c in tris:
        A, B, C = verts[a], verts[b], verts[c]
        n = cross(sub(B, A), sub(C, A))
        m = [(A[k] + B[k] + C[k]) / 3 - cx[k] for k in range(3)]
        score += dot(n, m)
    if score < 0:
        tris = [(a, c, b) for a, b, c in tris]
    return {"verts": verts, "tris": tris, "uvc": uvc, "engine": False}


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    l = math.sqrt(dot(a, a))
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 0.0, 1.0)


def weld(mesh):
    """ASE meshes: unique positions with area-weighted smooth normals. Engine meshes: their own vertices."""
    if mesh.get("engine"):
        return mesh["verts"], mesh["normals"]
    key, pos, acc, remap = {}, [], [], []
    for v in mesh["verts"]:
        k = (round(v[0], 2), round(v[1], 2), round(v[2], 2))
        if k not in key:
            key[k] = len(pos)
            pos.append(v)
            acc.append([0.0, 0.0, 0.0])
        remap.append(key[k])
    for a, b, c in mesh["tris"]:
        A, B, C = mesh["verts"][a], mesh["verts"][b], mesh["verts"][c]
        n = cross(sub(B, A), sub(C, A))
        for i in (a, b, c):
            w = acc[remap[i]]
            w[0] += n[0]; w[1] += n[1]; w[2] += n[2]
    return pos, [norm(n) for n in acc]

# ---------------------------------------------------------------------------------------------- bridge dump
def read_u2mv(path):
    """the `!meshverts` dump (format in U2EdBridge/src/editor_ops.c)"""
    d = open(path, "rb").read()
    o = [0]

    def take(fmt):
        v = struct.unpack_from("<" + fmt, d, o[0])
        o[0] += struct.calcsize("<" + fmt)
        return v

    def string():
        n, = take("i")
        s = d[o[0]:o[0] + 2 * n].decode("utf-16-le")
        o[0] += 2 * n
        return s
    if d[:4] != b"U2MV":
        raise SystemExit("%s is not a !meshverts dump" % path)
    o[0] = 4
    ver, lb = take("if")
    if ver != 1:
        raise SystemExit("unknown U2MV version %d" % ver)
    meshes = []
    for _ in range(take("i")[0]):
        name = string()
        nv, = take("i")
        f = array.array("f"); f.frombytes(d[o[0]:o[0] + 24 * nv]); o[0] += 24 * nv
        ni, = take("i")
        ix = array.array("H"); ix.frombytes(d[o[0]:o[0] + 2 * ni]); o[0] += 2 * ni
        if ni & 1:
            o[0] += 2
        verts = [(f[i * 6], f[i * 6 + 1], f[i * 6 + 2]) for i in range(nv)]
        normals = [norm((f[i * 6 + 3], f[i * 6 + 4], f[i * 6 + 5])) for i in range(nv)]
        tris = [(ix[i], ix[i + 1], ix[i + 2]) for i in range(0, ni - ni % 3, 3)]
        meshes.append({"name": name, "verts": verts, "normals": normals, "tris": tris, "uvc": [], "engine": True})
    actors = []
    for _ in range(take("i")[0]):
        name, cls = string(), string()
        mi, = take("i")
        m = take("16f")
        flags, = take("i")
        zone = string()
        amb, nc = take("Ii")
        cols = array.array("I"); cols.frombytes(d[o[0]:o[0] + 4 * nc]); o[0] += 4 * nc
        actors.append({"name": name, "class": cls, "mesh": mi, "m": m, "flags": flags, "zone": zone,
                       "ambient": amb, "colors": cols})
    lights = []
    for _ in range(take("i")[0]):
        name, cls = string(), string()
        loc = take("3f")
        rot = take("3i")
        typ, eff, br, hue, sat, rad, _, _ = take("8B")
        wr, flags = take("fi")
        zone = string()
        lights.append({"name": name, "class": cls, "loc": loc, "rot": rot, "type": typ, "effect": eff,
                       "bright": br, "hue": hue, "sat": sat, "radius": rad, "wradius": wr, "flags": flags, "zone": zone})
    return {"level_brightness": lb, "meshes": meshes, "actors": actors, "lights": lights}

# ---------------------------------------------------------------------------------------------- scene
class Placed:
    """a mesh placed by a 4x3 matrix: world = x*R0 + y*R1 + z*R2 + T (UE2 row-vector convention)"""

    def __init__(self, name, cls, mesh, meshname, rows, flags=8, zone="", dump=None):
        self.name, self.cls, self.mesh, self.meshname = name, cls, mesh, meshname
        self.r = rows                                   # ((R0), (R1), (R2), (T))
        self.flags, self.zone, self.dump = flags, zone, dump
        a = [[rows[i][j] for j in range(3)] for i in range(3)]
        det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
               + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
        self.flip = det < 0                             # mirrored placement flips the winding

    @staticmethod
    def from_t3d(a, mesh, meshname):
        p = a["props"]
        loc = vec(p.get("Location"))
        ax = rot_axes(*vec(p.get("Rotation"), ("Pitch", "Yaw", "Roll")))
        ds = float(p.get("DrawScale", 1.0))
        d3 = vec(p.get("DrawScale3D"), default=1.0) if "DrawScale3D" in p else (1.0, 1.0, 1.0)
        rows = tuple(tuple(c * ds * d3[i] for c in ax[i]) for i in range(3)) + (loc,)
        return Placed(a.get("Name"), a.get("Class"), mesh, meshname, rows)

    def world(self, v):
        r = self.r
        return tuple(v[0] * r[0][k] + v[1] * r[1][k] + v[2] * r[2][k] + r[3][k] for k in range(3))

    def wnormal(self, n):
        # inverse-transpose: solve M^T-style via the cofactor matrix (rows r0,r1,r2)
        r0, r1, r2 = self.r[0], self.r[1], self.r[2]
        c0, c1, c2 = cross(r1, r2), cross(r2, r0), cross(r0, r1)
        w = tuple(n[0] * c0[k] + n[1] * c1[k] + n[2] * c2[k] for k in range(3))
        w = norm(w)
        return (-w[0], -w[1], -w[2]) if self.flip else w

    def bounds(self):
        if not hasattr(self, "_b"):
            pts = [self.world(v) for v in self.mesh["verts"]] or [self.r[3]]
            self._b = (tuple(min(p[k] for p in pts) for k in range(3)), tuple(max(p[k] for p in pts) for k in range(3)))
        return self._b


def box_dist(a, b):
    d = 0.0
    for k in range(3):
        g = max(a[0][k] - b[1][k], b[0][k] - a[1][k], 0.0)
        d += g * g
    return math.sqrt(d)

# ---------------------------------------------------------------------------------------------- write-back
def write_u2bk(path, rows, mode):
    """rows: [(actor name, [packed 0xAARRGGBB ...])] in engine vertex order"""
    with open(path, "wb") as f:
        f.write(b"U2BK" + struct.pack("<iii", 1, 1 if mode == "replace" else 0, len(rows)))
        for name, cols in rows:
            nm = name.encode("utf-16-le")
            f.write(struct.pack("<i", len(name)) + nm + struct.pack("<i", len(cols)))
            f.write(array.array("I", cols).tobytes())


def unpack_bgra(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def calibrate(owners, out):
    """our direct (bytes) vs the engine's stored instance colours (lights only, no ambient)"""
    tot_e = tot_o = 0.0
    n = 0
    sq = 0.0
    per = []
    for pl, k0, cnt in owners:
        if not pl.dump or not (pl.dump["flags"] & 2) or len(pl.dump["colors"]) != cnt:
            continue
        ae = ao = 0.0
        for i in range(cnt):
            e = unpack_bgra(pl.dump["colors"][i])
            ours = [min(255.0, 255.0 * out[(k0 + i) * 9 + j]) for j in range(3)]
            for j in range(3):
                ae += e[j]; ao += ours[j]; sq += (e[j] - ours[j]) ** 2
            n += 3
        tot_e += ae; tot_o += ao
        per.append((pl.name, ae / (3 * cnt), ao / (3 * cnt)))
    if not n:
        print("calib: no actor with engine colours in the dump (LIGHT APPLY, then !meshverts again)")
        return
    print("calib: %d actors, mean engine %.1f vs ours %.1f (bytes), ratio engine/ours %.3f, RMS %.1f bytes"
          % (len(per), tot_e / n, tot_o / n, tot_e / max(tot_o, 1e-6), math.sqrt(sq / n)))
    per.sort(key=lambda r: -abs(r[1] - r[2]))
    for name, e, o in per[:10]:
        print("   %-28s engine %6.1f  ours %6.1f" % (name, e, o))


def fit_fill_lights(P, N, Y, RGB, k, level_brightness, seed=1):
    """N fill lights fitted to the indirect light at the samples (numpy). Returns [(loc, radius_byte,
    brightness, hue, sat, predicted_rgb_scale)]"""
    import numpy as np
    rng = np.random.default_rng(seed)
    w = np.maximum(Y, 1e-6)
    idx = rng.choice(len(P), size=min(k, len(P)), replace=False, p=w / w.sum())
    C = P[idx].copy()
    for _ in range(20):                                    # weighted k-means on position
        lab = np.empty(len(P), dtype=np.int32)
        for s in range(0, len(P), 20000):
            d = ((P[s:s + 20000, None, :] - C[None, :, :]) ** 2).sum(-1)
            lab[s:s + 20000] = d.argmin(1)
        for j in range(len(C)):
            m = lab == j
            if m.any():
                C[j] = (P[m] * w[m, None]).sum(0) / w[m].sum()
    lights = []
    for j in range(len(C)):
        m = lab == j
        if not m.any():
            continue
        wn = (N[m] * w[m, None]).sum(0)
        nl = np.linalg.norm(wn)
        nrm = wn / nl if nl > 1e-6 else np.array([0, 0, 1.0])
        ext = math.sqrt(float(((P[m] - C[j]) ** 2).sum(1).mean()))
        off = max(48.0, 0.5 * ext)
        loc = C[j] + nrm * off
        rb = int(min(255, max(0, round((2.5 * ext + off) / 25.0 - 1))))
        lights.append([loc, rb])
    # response of every sample to every light (engine falloff, no shadows), then non-negative least squares
    A = np.zeros((len(P), len(lights)), dtype=np.float32)
    for j, (loc, rb) in enumerate(lights):
        R = world_light_radius(rb)
        d = loc[None, :] - P
        dist = np.linalg.norm(d, axis=1)
        c = (d * N).sum(1) / np.maximum(dist, 1e-3)
        t = dist / R
        A[:, j] = np.where((dist < R) & (c > 0), 2 * c * (1 - 3 * t * t + 2 * t ** 3), 0)
    AtA = A.T.astype(np.float64) @ A
    AtY = A.T.astype(np.float64) @ Y
    x = np.zeros(len(lights))
    for _ in range(300):                                   # projected coordinate descent
        for j in range(len(lights)):
            if AtA[j, j] <= 0:
                continue
            x[j] = max(0.0, x[j] + (AtY[j] - AtA[j] @ x) / AtA[j, j])
    res = []
    for j, (loc, rb) in enumerate(lights):
        if x[j] <= 1e-4:
            continue
        m = A[:, j] > 0
        chroma = (RGB[m] * A[m, j:j + 1]).sum(0)
        chroma = chroma / max(chroma.mean(), 1e-9)          # mean channel 1
        target = tuple(float(c) * x[j] for c in chroma)     # colour that gives luminance x[j]
        h, s, kk, _ = fit_hsv(target, v_fixed=255)
        bright = 255.0 * kk / max(level_brightness, 1e-6)
        res.append((tuple(float(c) for c in loc), rb, bright, h, s))
    fitted = A @ x
    rel = float(np.abs(fitted - Y).mean() / max(Y.mean(), 1e-9))
    return res, rel


def write_fill_t3d(path, lights):
    with open(path, "w") as f:
        f.write("Begin Map\n")
        for i, (loc, rb, bright, h, s) in enumerate(lights):
            f.write("Begin Actor Class=Light Name=BakeFill%d\n" % i)
            f.write("    LightType=LT_Steady\n    LightBrightness=%d\n    LightHue=%d\n    LightSaturation=%d\n"
                    "    LightRadius=%d\n" % (min(255, int(round(bright))), h, s, rb))
            f.write("    Location=(X=%.1f,Y=%.1f,Z=%.1f)\n" % loc)
            f.write("    Group=\"BakeFill\"\n    Tag=\"BakeFill\"\n    Name=\"BakeFill%d\"\n" % i)
            f.write("End Actor\n")
        f.write("End Map\n")

# ---------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("t3d", nargs="?")
    ap.add_argument("--scene", help="!meshverts dump (engine geometry, colours, lights)")
    ap.add_argument("--ase", action="append", default=[], help="folder of <MeshName>.ase (repeatable)")
    ap.add_argument("--palette", help="palette.json for swatch albedo (default: <first --ase>/palette.json)")
    ap.add_argument("--albedo", type=float, default=0.45, help="albedo where no swatch is known")
    ap.add_argument("--out", default="bake.json", help="JSON of all terms ('' = none)")
    ap.add_argument("--ply")
    ap.add_argument("--ply-term", default="indirect", choices=("indirect", "direct", "total"))
    ap.add_argument("--rays", type=int, default=64)
    ap.add_argument("--bounces", type=int, default=1)
    ap.add_argument("--bounce2-rays", type=int, default=8)
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--sky", default="0.30,0.36,0.45", help="sky radiance RGB in engine units (1.0 = byte 255)")
    ap.add_argument("--skyhit", type=float, default=0.5, help="sky term assumed at bounce hit points")
    ap.add_argument("--level-brightness", type=float, help="LevelInfo.Brightness (default: the dump's, else 1)")
    ap.add_argument("--only", action="append", default=[], help="bake only actors matching (glob)")
    ap.add_argument("--changed", action="append", default=[], help="incremental: changed actors (glob)")
    ap.add_argument("--radius", type=float, default=1500.0, help="incremental: re-bake within this distance")
    ap.add_argument("--max-actors", type=int, default=0, help="debug: stop after N target actors")
    ap.add_argument("--u2bk", help="write per-vertex colours for the bridge's !bakeload")
    ap.add_argument("--mode", default="add", choices=("add", "replace"))
    ap.add_argument("--terms", help="terms in the U2BK colours (default add: sky,bounce; replace: direct,sky,bounce)")
    ap.add_argument("--gain", type=float, default=1.0, help="multiplier on the U2BK terms")
    ap.add_argument("--calib", action="store_true", help="compare our direct with the dump's engine colours")
    ap.add_argument("--fill", type=int, default=0, help="fit N fill lights to the indirect light")
    ap.add_argument("--fill-t3d", default="bake_fill.t3d")
    ap.add_argument("--fill-terms", default="bounce", help="what the fill lights stand in for (bounce or sky,bounce)")
    ap.add_argument("--zones", help="write per-zone ambient suggestions (!setprop lines) to this file")
    ap.add_argument("--zone-percentile", type=float, default=30.0)
    o = ap.parse_args()
    if not o.t3d and not o.scene:
        ap.error("give a T3D, a --scene dump, or both")

    t0 = time.time()
    actors = parse_t3d(open(o.t3d, encoding="utf-8", errors="replace").read()) if o.t3d else []
    dump = read_u2mv(o.scene) if o.scene else None
    lb = o.level_brightness or (dump["level_brightness"] if dump else 1.0)
    pal = None
    pal_path = o.palette or (os.path.join(o.ase[0], "palette.json") if o.ase else None)
    if pal_path and os.path.exists(pal_path):
        pal = json.load(open(pal_path))

    meshes, missing, placed = {}, {}, []
    lights, sun, unhandled = [], None, 0
    have = set()
    if dump:
        for da in dump["actors"]:
            m = dump["meshes"][da["mesh"]]
            r = da["m"]
            rows = ((r[0], r[1], r[2]), (r[4], r[5], r[6]), (r[8], r[9], r[10]), (r[12], r[13], r[14]))
            placed.append(Placed(da["name"], da["class"], m, m["name"].split(".")[-1], rows, da["flags"], da["zone"], da))
            have.add(da["name"].lower())
        for L in dump["lights"]:
            if not (L["flags"] & 1) or L["type"] == 0:
                continue                                        # dynamic lights are not baked by the engine
            col = light_colour(L["hue"], L["sat"], L["bright"], lb)
            if L["effect"] == LE_SUNLIGHT:
                sun = (rot_axes(*L["rot"])[0], col)
            else:
                if L["type"] != 1 or L["effect"] != 0:
                    unhandled += 1
                lights.append((L["loc"], L["wradius"] or world_light_radius(L["radius"]), col))
    for a in actors:
        cls, p = a.get("Class", ""), a["props"]
        if (a.get("Name") or "").lower() in have:
            continue
        if "StaticMesh" in p:
            ref = p["StaticMesh"].split("'")[1] if "'" in p["StaticMesh"] else p["StaticMesh"]
            mname = ref.split(".")[-1]
            if mname not in meshes:
                meshes[mname] = None
                for d in o.ase:
                    f = os.path.join(d, mname + ".ase")
                    if os.path.exists(f):
                        meshes[mname] = load_ase(f)
                        break
            if meshes[mname] is None:
                missing[ref] = missing.get(ref, 0) + 1
                continue
            placed.append(Placed.from_t3d(a, meshes[mname], mname))
        elif dump is None and "light" in cls.lower():
            if p.get("bStatic", "True").lower() == "false":
                continue
            col = light_colour(tbyte(p, "LightHue", 0), tbyte(p, "LightSaturation", 255), tbyte(p, "LightBrightness", 64), lb)
            if cls.lower() == "sunlight" or p.get("LightEffect") == "LE_Sunlight":
                sun = (rot_axes(*vec(p.get("Rotation"), ("Pitch", "Yaw", "Roll")))[0], col)
            else:
                if p.get("LightEffect", "LE_None") != "LE_None":
                    unhandled += 1
                lights.append((vec(p.get("Location")), world_light_radius(tbyte(p, "LightRadius", 64)), col))

    # albedo per mesh: palette swatches for AvalonSM B_* ASE meshes; engine meshes get the ASE's mean swatch
    ase_mean = {}
    if pal:
        for mname, m in meshes.items():
            if m and m["uvc"] and mname.startswith("B_"):
                cs = [pal[min(len(pal) - 1, max(0, int(u * 8)))][:3] for u, _ in m["uvc"]]
                ase_mean[mname] = tuple(sum(c[k] for c in cs) / len(cs) for k in range(3))
    tri, alb = array.array("f"), array.array("f")
    for pl in placed:
        m = pl.mesh
        wv = [pl.world(v) for v in m["verts"]]
        base = ase_mean.get(pl.meshname, (o.albedo,) * 3)
        for i, (a, b, c) in enumerate(m["tris"]):
            if pl.flip:
                b, c = c, b
            tri.extend(wv[a]); tri.extend(wv[b]); tri.extend(wv[c])
            col = base
            if pal and m["uvc"] and pl.meshname.startswith("B_"):
                u = m["uvc"][i][0]
                col = tuple(pal[min(len(pal) - 1, max(0, int(u * 8)))][:3])
            alb.extend(col)

    targets = [pl for pl in placed if not o.only or any(fnmatch.fnmatchcase(pl.name, g) for g in o.only)]
    if o.changed:
        ch = [pl for pl in placed if any(fnmatch.fnmatchcase(pl.name, g) for g in o.changed)]
        targets = [pl for pl in targets if pl in ch or any(box_dist(pl.bounds(), c.bounds()) <= o.radius for c in ch)]
    if o.max_actors:
        targets = targets[:o.max_actors]

    pos, nrm, sfl, owners = array.array("f"), array.array("f"), array.array("i"), []
    welded = {}
    for pl in targets:
        key = id(pl.mesh)
        if key not in welded:
            welded[key] = weld(pl.mesh)
        lp, ln = welded[key]
        k0 = len(pos) // 3
        for v, n in zip(lp, ln):
            pos.extend(pl.world(v)); nrm.extend(pl.wnormal(n))
            sfl.append(1 if pl.flags & 8 else 0)
        owners.append((pl, k0, len(lp)))
    ns = len(pos) // 3
    t1 = time.time()
    print("scene: %d T3D actors, %s, %d meshes placed (%d triangles), %d lights (+%d with effects treated as "
          "steady), sun=%s, level brightness %.2f; %d target actors, %d samples; %d mesh refs without geometry "
          "(%d actors) [%.1fs]" % (len(actors), "dump %d actors" % len(dump["actors"]) if dump else "no dump",
                                    len(placed), len(tri) // 9, len(lights), unhandled, "yes" if sun else "no", lb,
                                    len(targets), ns, len(missing), sum(missing.values()), t1 - t0))
    for ref, n in sorted(missing.items(), key=lambda x: -x[1])[:8]:
        print("   no geometry: %s x%d" % (ref, n))

    dll = ctypes.CDLL(os.path.join(HERE, "bake_kernel.dll"))

    def buf(arr, ty=ctypes.c_float):
        if not len(arr):
            arr = array.array(arr.typecode, [0])
        return (ty * len(arr)).from_buffer(arr)
    larr = array.array("f")
    for p, r, c in lights:
        larr.extend(p); larr.append(r); larr.extend(c)
    sarr = array.array("f", list(sun[0]) + list(sun[1]) + [1.0] if sun else [0, 0, -1, 0, 0, 0, 0])
    sky = array.array("f", [float(x) for x in o.sky.split(",")])
    opts = array.array("f", [2.0, o.skyhit, 400000.0])
    out = array.array("f", [0.0] * (9 * max(ns, 1)))
    dll.bake_ex.restype = ctypes.c_int
    rc = dll.bake_ex(len(tri) // 9, buf(tri), buf(alb), ns, buf(pos), buf(nrm), buf(sfl, ctypes.c_int), len(lights),
                     buf(larr), buf(sarr), buf(sky), o.rays, o.bounces, o.bounce2_rays, 12345, buf(opts), buf(out),
                     o.threads)
    t2 = time.time()
    if rc:
        sys.exit("bake kernel failed (%d)" % rc)
    print("bake: %d samples x %d rays, %d bounce(s), %d threads: %.1fs (%.0f samples/s)"
          % (ns, o.rays, o.bounces, o.threads, t2 - t1, ns / max(t2 - t1, 1e-6)))

    if o.out:
        res = {}
        for pl, k0, n in owners:
            lp, _ = welded[id(pl.mesh)]
            rows = [[round(x, 2) for x in lp[i]] + [round(x, 4) for x in out[(k0 + i) * 9:(k0 + i) * 9 + 9]]
                    for i in range(n)]
            res[pl.name] = {"mesh": pl.meshname, "class": pl.cls, "engine": bool(pl.mesh.get("engine")), "verts": rows}
        json.dump({"t3d": os.path.abspath(o.t3d) if o.t3d else None, "scene": o.scene, "rays": o.rays,
                   "bounces": o.bounces, "sky": list(sky), "units": "engine (1.0 = byte 255)", "actors": res},
                  open(o.out, "w"))
        print("wrote", o.out)

    if o.calib:
        calibrate(owners, out)

    if o.u2bk:
        terms = (o.terms or ("sky,bounce" if o.mode == "add" else "direct,sky,bounce")).split(",")
        sel = [{"direct": 0, "sky": 3, "bounce": 6}[t.strip()] for t in terms]
        rows, skipped = [], 0
        for pl, k0, n in owners:
            if not pl.mesh.get("engine"):
                skipped += 1
                continue
            cols = []
            for i in range(n):
                b = out[(k0 + i) * 9:(k0 + i) * 9 + 9]
                c = [o.gain * sum(b[s + j] for s in sel) for j in range(3)]
                cols.append(0xff000000 | to_byte(c[0]) << 16 | to_byte(c[1]) << 8 | to_byte(c[2]))
            rows.append((pl.name, cols))
        write_u2bk(o.u2bk, rows, o.mode)
        print("wrote %s: %d actors, mode %s, terms %s x %.2f%s" % (o.u2bk, len(rows), o.mode, "+".join(terms), o.gain,
              "; %d ASE-only actors left out (no engine vertex order: use --scene)" % skipped if skipped else ""))

    if o.fill or o.zones:
        import numpy as np
        P = np.frombuffer(pos, dtype=np.float32).reshape(-1, 3).astype(np.float64)
        N = np.frombuffer(nrm, dtype=np.float32).reshape(-1, 3).astype(np.float64)
        R = np.frombuffer(out, dtype=np.float32)[:ns * 9].reshape(-1, 9).astype(np.float64)
        if o.fill:
            fsel = [{"sky": 3, "bounce": 6}[t.strip()] for t in o.fill_terms.split(",")]
            RGB = sum(R[:, s:s + 3] for s in fsel)
            Y = RGB.mean(1)
            fl, rel = fit_fill_lights(P, N, Y, RGB, o.fill, lb)
            write_fill_t3d(o.fill_t3d, fl)
            over = sum(1 for f in fl if f[2] > 255)
            print("wrote %s: %d fill lights for %s (mean abs error %.0f %% of the mean)%s" % (
                o.fill_t3d, len(fl), "+".join(o.fill_terms.split(",")), 100 * rel,
                "; %d need LightBrightness > 255 (clamped): use more lights" % over if over else ""))
        if o.zones:
            IND = R[:, 3:6] + R[:, 6:9]
            zone_of = []
            for pl, k0, n in owners:
                zone_of += [pl.zone or "(level)"] * n
            zone_of = np.array(zone_of)
            with open(o.zones, "w") as f:
                f.write("# U2Bake zone ambient suggestions (percentile %.0f of sky+bounce); FGetHSV(Hue, Sat, "
                        "AmbientBrightness) is added to every vertex/texel/actor of the zone at render time\n" % o.zone_percentile)
                for z in sorted(set(zone_of)):
                    m = zone_of == z
                    lum = IND[m].mean(1)
                    cut = np.percentile(lum, o.zone_percentile)
                    pick = IND[m][lum <= cut + 1e-9]
                    rgb = tuple(float(c) for c in pick.mean(0))
                    h, s, v, _ = fit_hsv(rgb)
                    name = z if z != "(level)" else "LevelInfo0"
                    f.write("!setprop %s AmbientBrightness %d\n!setprop %s AmbientHue %d\n!setprop %s AmbientSaturation %d\n"
                            % (name, v, name, h, name, s))
                    print("zone %-16s %6d samples: ambient rgb %.3f %.3f %.3f -> Brightness %d Hue %d Saturation %d"
                          % (z, int(m.sum()), rgb[0], rgb[1], rgb[2], v, h, s))
            print("wrote", o.zones)

    if o.ply:
        with open(o.ply, "w") as f:
            f.write("ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
                    "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n" % ns)
            for i in range(ns):
                d, s, b = out[i * 9:i * 9 + 3], out[i * 9 + 3:i * 9 + 6], out[i * 9 + 6:i * 9 + 9]
                c = d if o.ply_term == "direct" else ([s[j] + b[j] for j in range(3)] if o.ply_term == "indirect"
                                                      else [d[j] + s[j] + b[j] for j in range(3)])
                c = [to_byte(x) for x in c]                    # engine units: straight to bytes
                f.write("%.1f %.1f %.1f %d %d %d\n" % (pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2], c[0], c[1], c[2]))
        print("wrote", o.ply)


if __name__ == "__main__":
    main()
