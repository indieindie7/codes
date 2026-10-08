r"""U2Bake - scene-wide light bake for Unreal II levels, offline (no editor, no game).

    py bake.py <map.t3d> --ase DIR [--ase DIR2 ...] [--out bake.json] [--ply bake.ply]
               [--rays 64] [--bounces 1] [--threads 6] [--only PATTERN ...] [--changed PATTERN ... --radius 1500]

Reads a T3D (MAP EXPORT, or a generator's actor T3D) and the ASE sources of its static meshes, places
every mesh it can find, and for each welded vertex of the target actors computes
    direct  = sun + point lights with shadow rays (what UE2 bakes itself, for reference/calibration)
    sky     = cosine-weighted sky visibility * sky colour
    bounce  = one diffuse bounce (hits: albedo * (direct + sky*skyhit) at the hit point)
in linear float RGB, using bake_kernel.dll (C, BVH, multithreaded). The scene includes every placed mesh,
so neighbours and the ground occlude and reflect.

Output JSON: {"actors": {Name: {"mesh": ..., "verts": [[lx,ly,lz, dR,dG,dB, sR,sG,sB, bR,bG,bB], ...]}}}
with lx..lz in MESH space (the write-back matches the engine's own vertices by position).
--ply writes the target vertices as a coloured point cloud (sky+bounce, or --ply-term direct|total).

Incremental: --changed PATTERN selects actors that moved/changed; with --radius R every actor whose
bounds come within R of a changed actor is re-baked too (bounce reach), the rest is skipped.
Not handled yet (see codes/tools/C/U2EdBridge/LIGHTING.md): BSP brushes, TerrainInfo heightmaps,
stock meshes without ASE (Flora_M, Terran_DecoM...: they are reported, not placed), spot lights,
LightEffect variants, texture albedo (palette swatches only).
"""
import argparse, array, ctypes, fnmatch, json, math, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

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


def hsv(hue, sat, bright=1.0):
    """UE2 FGetHSV: hue 0-255, saturation 255 = white (lowsun.py's note), result * bright"""
    h = (hue % 256) / 256.0 * 6.0
    i, f = int(h), h - int(h)
    rgb = [(1, f, 0), (1 - f, 1, 0), (0, 1, f), (0, 1 - f, 1), (f, 0, 1), (1, 0, 1 - f)][i % 6]
    s = sat / 255.0
    return tuple((c * (1 - s) + s) * bright for c in rgb)


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
    # winding: pick the sign that makes normals point away from the mesh centre on average
    cx = [sum(v[k] for v in verts) / max(1, len(verts)) for k in range(3)]
    score = 0.0
    for a, b, c in tris:
        A, B, C = verts[a], verts[b], verts[c]
        n = cross(sub(B, A), sub(C, A))
        m = [(A[k] + B[k] + C[k]) / 3 - cx[k] for k in range(3)]
        score += dot(n, m)
    if score < 0:
        tris = [(a, c, b) for a, b, c in tris]
    return {"verts": verts, "tris": tris, "uvc": uvc}


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    l = math.sqrt(dot(a, a))
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 0.0, 1.0)


def weld(mesh):
    """unique positions with area-weighted smooth normals (the ASE writer puts every face in smoothing
    group 1, so UnrealEd's import smooths too)"""
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


# ---------------------------------------------------------------------------------------------- scene
class Placed:
    def __init__(self, a, mesh, meshname):
        p = a["props"]
        self.name, self.cls, self.mesh, self.meshname = a.get("Name"), a.get("Class"), mesh, meshname
        self.loc = vec(p.get("Location"))
        pr = vec(p.get("Rotation"), ("Pitch", "Yaw", "Roll"))
        self.ax = rot_axes(*pr)
        ds = float(p.get("DrawScale", 1.0))
        d3 = vec(p.get("DrawScale3D"), default=1.0) if "DrawScale3D" in p else (1.0, 1.0, 1.0)
        self.scale = (ds * d3[0], ds * d3[1], ds * d3[2])

    def world(self, v):
        x, y, z = v[0] * self.scale[0], v[1] * self.scale[1], v[2] * self.scale[2]
        X, Y, Z = self.ax
        return (self.loc[0] + x * X[0] + y * Y[0] + z * Z[0],
                self.loc[1] + x * X[1] + y * Y[1] + z * Z[1],
                self.loc[2] + x * X[2] + y * Y[2] + z * Z[2])

    def wnormal(self, n):
        # inverse-transpose for non-uniform scale
        x, y, z = n[0] / self.scale[0], n[1] / self.scale[1], n[2] / self.scale[2]
        X, Y, Z = self.ax
        return norm((x * X[0] + y * Y[0] + z * Z[0], x * X[1] + y * Y[1] + z * Z[1], x * X[2] + y * Y[2] + z * Z[2]))

    def bounds(self):
        if not hasattr(self, "_b"):
            pts = [self.world(v) for v in self.mesh["verts"]] or [self.loc]
            self._b = (tuple(min(p[k] for p in pts) for k in range(3)), tuple(max(p[k] for p in pts) for k in range(3)))
        return self._b


def box_dist(a, b):
    d = 0.0
    for k in range(3):
        g = max(a[0][k] - b[1][k], b[0][k] - a[1][k], 0.0)
        d += g * g
    return math.sqrt(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("t3d")
    ap.add_argument("--ase", action="append", default=[], help="folder of <MeshName>.ase (repeatable)")
    ap.add_argument("--palette", help="palette.json for swatch albedo (default: <first --ase>/palette.json)")
    ap.add_argument("--albedo", type=float, default=0.45, help="albedo where no swatch is known")
    ap.add_argument("--out", default="bake.json")
    ap.add_argument("--ply")
    ap.add_argument("--ply-term", default="indirect", choices=("indirect", "direct", "total"))
    ap.add_argument("--rays", type=int, default=64)
    ap.add_argument("--bounces", type=int, default=1)
    ap.add_argument("--bounce2-rays", type=int, default=8)
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--sky", default="0.30,0.36,0.45", help="sky radiance RGB (linear)")
    ap.add_argument("--skyhit", type=float, default=0.5, help="sky term assumed at bounce hit points")
    ap.add_argument("--light-scale", type=float, default=1.0 / 255.0, help="LightBrightness -> linear intensity")
    ap.add_argument("--only", action="append", default=[], help="bake only actors matching (glob)")
    ap.add_argument("--changed", action="append", default=[], help="incremental: changed actors (glob)")
    ap.add_argument("--radius", type=float, default=1500.0, help="incremental: re-bake within this distance")
    ap.add_argument("--max-actors", type=int, default=0, help="debug: stop after N target actors")
    o = ap.parse_args()

    t0 = time.time()
    actors = parse_t3d(open(o.t3d, encoding="utf-8", errors="replace").read())
    pal = None
    pal_path = o.palette or (os.path.join(o.ase[0], "palette.json") if o.ase else None)
    if pal_path and os.path.exists(pal_path):
        pal = json.load(open(pal_path))

    meshes, missing, placed = {}, {}, []
    lights, sun = [], None
    for a in actors:
        cls, p = a.get("Class", ""), a["props"]
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
            placed.append(Placed(a, meshes[mname], mname))
        elif cls.lower() == "sunlight":
            pr = vec(p.get("Rotation"), ("Pitch", "Yaw", "Roll"))
            d = rot_axes(*pr)[0]                         # FRotator::Vector = direction the light travels
            b = float(p.get("LightBrightness", 64)) * o.light_scale
            sun = (d, hsv(int(p.get("LightHue", 0)), int(p.get("LightSaturation", 255)), b))
        elif "light" in cls.lower():
            b = float(p.get("LightBrightness", 64)) * o.light_scale
            r = 25.0 * (float(p.get("LightRadius", 64)) + 1)        # UE WorldLightRadius
            lights.append((vec(p.get("Location")), r, hsv(int(p.get("LightHue", 0)), int(p.get("LightSaturation", 255)), b)))

    # world triangles + albedo
    tri, alb = array.array("f"), array.array("f")
    for pl in placed:
        m = pl.mesh
        wv = [pl.world(v) for v in m["verts"]]
        for i, (a, b, c) in enumerate(m["tris"]):
            tri.extend(wv[a]); tri.extend(wv[b]); tri.extend(wv[c])
            col = (o.albedo,) * 3
            if pal and m["uvc"] and pl.meshname.startswith("B_"):
                u = m["uvc"][i][0]
                col = tuple(pal[min(len(pal) - 1, max(0, int(u * 8)))][:3])
            alb.extend(col)

    # targets
    def wanted(pl):
        if o.only and not any(fnmatch.fnmatchcase(pl.name, g) for g in o.only):
            return False
        return True
    targets = [pl for pl in placed if wanted(pl)]
    if o.changed:
        ch = [pl for pl in placed if any(fnmatch.fnmatchcase(pl.name, g) for g in o.changed)]
        targets = [pl for pl in targets if pl in ch or any(box_dist(pl.bounds(), c.bounds()) <= o.radius for c in ch)]
    if o.max_actors:
        targets = targets[:o.max_actors]

    pos, nrm, owners = array.array("f"), array.array("f"), []
    welded = {}
    for pl in targets:
        if pl.meshname not in welded:
            welded[pl.meshname] = weld(pl.mesh)
        lp, ln = welded[pl.meshname]
        for v, n in zip(lp, ln):
            pos.extend(pl.world(v)); nrm.extend(pl.wnormal(n))
        owners.append((pl, len(lp)))
    ns = len(pos) // 3
    t1 = time.time()
    print("scene: %d actors in T3D, %d meshes placed (%d triangles), %d lights, sun=%s; %d target actors, %d samples; "
          "%d mesh refs without ASE (%d actors) [%.1fs]" % (len(actors), len(placed), len(tri) // 9, len(lights),
          "yes" if sun else "no", len(targets), ns, len(missing), sum(missing.values()), t1 - t0))
    for ref, n in sorted(missing.items(), key=lambda x: -x[1])[:8]:
        print("   no ASE: %s x%d" % (ref, n))

    dll = ctypes.CDLL(os.path.join(HERE, "bake_kernel.dll"))
    F = ctypes.POINTER(ctypes.c_float)

    def buf(arr):
        if not len(arr):
            arr = array.array("f", [0.0])
        return (ctypes.c_float * len(arr)).from_buffer(arr)
    larr = array.array("f")
    for p, r, c in lights:
        larr.extend(p); larr.append(r); larr.extend(c)
    sarr = array.array("f", list(sun[0]) + list(sun[1]) + [1.0] if sun else [0, 0, -1, 0, 0, 0, 0])
    sky = array.array("f", [float(x) for x in o.sky.split(",")])
    opts = array.array("f", [2.0, o.skyhit, 400000.0])
    out = array.array("f", [0.0] * (9 * max(ns, 1)))
    dll.bake.restype = ctypes.c_int
    rc = dll.bake(len(tri) // 9, buf(tri), buf(alb), ns, buf(pos), buf(nrm), len(lights), buf(larr), buf(sarr), buf(sky),
                  o.rays, o.bounces, o.bounce2_rays, 12345, buf(opts), buf(out), o.threads)
    t2 = time.time()
    if rc:
        sys.exit("bake kernel failed (%d)" % rc)
    print("bake: %d samples x %d rays, %d bounce(s), %d threads: %.1fs (%.0f samples/s)"
          % (ns, o.rays, o.bounces, o.threads, t2 - t1, ns / max(t2 - t1, 1e-6)))

    res, k = {}, 0
    for pl, n in owners:
        lp, _ = welded[pl.meshname]
        rows = []
        for i in range(n):
            rows.append([round(x, 2) for x in lp[i]] + [round(x, 4) for x in out[(k + i) * 9:(k + i) * 9 + 9]])
        res[pl.name] = {"mesh": pl.meshname, "class": pl.cls, "verts": rows}
        k += n
    json.dump({"t3d": os.path.abspath(o.t3d), "rays": o.rays, "bounces": o.bounces, "sky": list(sky),
               "actors": res}, open(o.out, "w"))
    print("wrote", o.out)

    if o.ply:
        with open(o.ply, "w") as f:
            f.write("ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
                    "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n" % ns)
            for i in range(ns):
                d, s, b = out[i * 9:i * 9 + 3], out[i * 9 + 3:i * 9 + 6], out[i * 9 + 6:i * 9 + 9]
                c = d if o.ply_term == "direct" else ([s[j] + b[j] for j in range(3)] if o.ply_term == "indirect"
                                                      else [d[j] + s[j] + b[j] for j in range(3)])
                c = [int(255 * min(1.0, (x / (1 + x)) ** (1 / 2.2))) for x in c]       # Reinhard + gamma, preview only
                f.write("%.1f %.1f %.1f %d %d %d\n" % (pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2], c[0], c[1], c[2]))
        print("wrote", o.ply)


if __name__ == "__main__":
    main()
