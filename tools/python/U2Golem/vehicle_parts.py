"""Rigid-part rig for UT3 vehicles in Unreal II (no Golem): .psk + .psa -> part meshes + script data.

    python vehicle_parts.py <mesh.psk> <anims.psa> <out_dir> <Name> [--step 2] [--package U2HoverSM]

UT3 vehicles are rigidly skinned (each vertex on one bone), so the mesh splits into one static mesh per
bone. Unreal II then plays the vehicle's own animations by moving those parts (RigBike.uc composes the
bone chain each tick).

Writes:
  <out_dir>/ase/<Name>_<Bone>.ase   one part per bone that owns faces, vertices in that bone's REST space
                                    (X pre-mirrored for Unreal II's ASE importer, like blend2ase.py)
  <out_dir>/<Name>Bike.uc           a RigBike subclass whose defaultproperties hold the skeleton (parent +
                                    parent-relative rest transform per bone), the part list, the sequences
                                    and every sampled frame as parent-relative (location, rotator) keys
  <out_dir>/<Name>_parts.txt        part names, for the UnrealEd import
Units and axes are Unreal's (UT3 = UE3, same as Unreal II). The model is recentred: the bounding-box centre
of the rest mesh becomes the actor's origin (Unreal actors are centred on their collision cylinder).
"""
import argparse, math, os, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psa as psa_mod


def read_psk(path):
    d = open(path, "rb").read()
    o, ch = 0, {}
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0].decode("latin1")
        size, count = struct.unpack_from("<ii", d, o + 24)
        ch[cid] = (d[o + 32:o + 32 + size * count], size, count)
        o += 32 + size * count
    b, s, n = ch["PNTS0000"]
    pts = np.array([struct.unpack_from("<3f", b, s * i) for i in range(n)])
    b, s, n = ch["VTXW0000"]
    big = n > 65536
    wedges = [(struct.unpack_from("<I", b, s * i)[0] if big else struct.unpack_from("<H", b, s * i)[0],)
              + struct.unpack_from("<ff", b, s * i + 4) for i in range(n)]
    b, s, n = ch["FACE0000"]
    faces = [struct.unpack_from("<HHH", b, s * i) for i in range(n)]
    b, s, n = ch["REFSKELT"]
    bones = []
    for i in range(n):
        name = b[s * i:s * i + 64].split(b"\0")[0].decode("latin1")
        parent = struct.unpack_from("<i", b, s * i + 72)[0]
        q = struct.unpack_from("<4f", b, s * i + 76)
        p = struct.unpack_from("<3f", b, s * i + 92)
        bones.append((name, parent if i else -1, p, q))
    b, s, n = ch["RAWWEIGHTS"]
    weights = [struct.unpack_from("<fii", b, s * i) for i in range(n)]
    return pts, wedges, faces, bones, weights


def quat_mat(q, is_root):
    x, y, z, w = q
    if not is_root:                       # ActorX stores child rotations conjugated
        x, y, z = -x, -y, -z
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def xform(pos, q, is_root):
    m = np.eye(4)
    m[:3, :3] = quat_mat(q, is_root)
    m[:3, 3] = pos
    return m


# Unreal rotators: GetAxes(R) gives X=(cp*cy, cp*sy, sp), Y=(sr*sp*cy-cr*sy, sr*sp*sy+cr*cy, -sr*cp),
# Z=(-(cr*sp*cy+sr*sy), cy*sr-cr*sp*sy, cr*cp); the axes are the columns of our rotation matrices.
U = 65536 / (2 * math.pi)


def rotator(m):
    X, Y, Z = m[:3, 0], m[:3, 1], m[:3, 2]
    yaw = math.atan2(X[1], X[0])
    pitch = math.atan2(X[2], math.hypot(X[0], X[1]))
    roll = math.atan2(-Y[2], Z[2])
    return int(round(pitch * U)), int(round(yaw * U)), int(round(roll * U))


def axes(p, y, r):
    p, y, r = p / U, y / U, r / U
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    X = (cp * cy, cp * sy, sp)
    Y = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    Z = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return np.array([X, Y, Z]).T


def write_ase(path, name, verts, tris, uvs):
    """verts in part space; tris = vertex index triples; uvs = per-corner (u, v) bottom-up."""
    L = ["*3DSMAX_ASCIIEXPORT\t200", '*COMMENT "vehicle_parts"', "*GEOMOBJECT {", f'\t*NODE_NAME "{name}"', "\t*MESH {",
         "\t\t*TIMEVALUE 0", f"\t\t*MESH_NUMVERTEX {len(verts)}", f"\t\t*MESH_NUMFACES {len(tris)}", "\t\t*MESH_VERTEX_LIST {"]
    L += [f"\t\t\t*MESH_VERTEX {i}\t{-x:.5f}\t{y:.5f}\t{z:.5f}" for i, (x, y, z) in enumerate(verts)]
    L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
    L += [f"\t\t\t*MESH_FACE {i}: A: {a} B: {c} C: {b} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0"
          for i, (a, b, c) in enumerate(tris)]                      # X mirrored -> flip the winding
    L += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(tris) * 3}", "\t\t*MESH_TVERTLIST {"]
    k = 0
    for t in range(len(tris)):
        for j in (0, 2, 1):
            u, v = uvs[t][j]
            L.append(f"\t\t\t*MESH_TVERT {k}\t{u:.6f}\t{v:.6f}\t0.0000")
            k += 1
    L += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(tris)}", "\t\t*MESH_TFACELIST {"]
    L += [f"\t\t\t*MESH_TFACE {i}\t{3 * i}\t{3 * i + 1}\t{3 * i + 2}" for i in range(len(tris))]
    L += ["\t\t}", "\t}", "}"]
    open(path, "w").write("\n".join(L) + "\n")


def vec(v):
    return f"(X={v[0]:.3f},Y={v[1]:.3f},Z={v[2]:.3f})"


def rot(r):
    return f"(Pitch={r[0]},Yaw={r[1]},Roll={r[2]})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("psk"); ap.add_argument("psa"); ap.add_argument("out"); ap.add_argument("name")
    ap.add_argument("--step", type=int, default=2, help="keep every Nth animation frame")
    ap.add_argument("--package", default="U2HoverSM")
    ap.add_argument("--preview", action="append", default=[], help="SEQ:FRAME -> <out>/preview_SEQ_FRAME.obj, posed parts")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "ase"), exist_ok=True)
    pts, wedges, faces, bones, weights = read_psk(a.psk)
    nb = len(bones)
    local_rest = [xform(p, q, i == 0) for i, (_, par, p, q) in enumerate(bones)]
    world_rest = []
    for i, (_, par, _, _) in enumerate(bones):
        world_rest.append(local_rest[i] if par < 0 else world_rest[par] @ local_rest[i])

    # rigid assignment: the heaviest bone per point, then per face (majority of its corners)
    best = {}
    for w, p, b in weights:
        if w > best.get(p, (0, -1))[0]:
            best[p] = (w, b)
    pbone = np.array([best.get(i, (0, 0))[1] for i in range(len(pts))])
    centre = (pts.min(0) + pts.max(0)) / 2
    part_faces = {}
    for f in faces:
        vs = [wedges[k][0] for k in f]
        bs = [pbone[v] for v in vs]
        b = max(set(bs), key=bs.count)
        part_faces.setdefault(b, []).append(f)

    parts, part_of = [], [-1] * nb
    for b in sorted(part_faces):
        name = f"{a.name}_{bones[b][0]}"
        inv = np.linalg.inv(world_rest[b])
        vmap, verts, tris, uvs = {}, [], [], []
        for f in part_faces[b]:
            tri, uvt = [], []
            for k in f:
                pi, u, v = wedges[k]
                if pi not in vmap:
                    vmap[pi] = len(verts)
                    verts.append((inv @ np.append(pts[pi], 1))[:3])
                tri.append(vmap[pi])
                uvt.append((u, 1.0 - v))
            tris.append(tri)
            uvs.append(uvt)
        write_ase(os.path.join(a.out, "ase", name + ".ase"), name, verts, tris, uvs)
        part_of[b] = len(parts)
        parts.append((name, b, len(tris)))

    # animation keys: parent-relative; bones the .psa doesn't track keep their rest local transform
    P = psa_mod.read(a.psa)
    track = {bb["name"]: i for i, bb in enumerate(P["bones"])}
    seq_lines, key_lines, first = [], [], 0
    worst = 0.0
    for s in P["seqs"]:
        frames = list(range(0, s["frames"], a.step)) or [0]
        if s["frames"] > 1 and frames[-1] != s["frames"] - 1:
            frames.append(s["frames"] - 1)
        for f in frames:
            keys = psa_mod.frame(P, s, f)
            for i, (bname, par, _, _) in enumerate(bones):
                if bname in track:
                    pos, q = keys[track[bname]]
                    m = xform(pos, q, i == 0)
                else:
                    m = local_rest[i]
                if i == 0:
                    m = m.copy()
                    m[:3, 3] -= centre          # recentre on the root
                r = rotator(m)
                worst = max(worst, float(np.abs(axes(*r) - m[:3, :3]).max()))
                key_lines.append(f"\tKeys({len(key_lines)})=(L={vec(m[:3, 3])},R={rot(r)})")
        rate = s["rate"] / a.step if len(frames) > 1 else s["rate"]
        seq_lines.append(f'\tSeqs({len(seq_lines)})=(SeqName="{s["name"]}",First={first},Frames={len(frames)},Rate={rate:.3f})')
        first += len(frames)

    bone_lines = []
    for i, (bname, par, p, q) in enumerate(bones):
        m = local_rest[i].copy()
        if i == 0:
            m[:3, 3] -= centre
        bone_lines.append(f'\tBones({i})=(BoneName="{bname}",Parent={par},L={vec(m[:3, 3])},R={rot(rotator(m))},Part={part_of[i]})')
    part_lines = [f'\tPartMeshes({k})="{a.package}.{name}"' for k, (name, b, n) in enumerate(parts)]
    lo, hi = pts.min(0) - centre, pts.max(0) - centre

    uc = f"""//=============================================================================
// {a.name}Bike - UT3's {a.name} as a RigBike: generated by tools/python/U2Golem/vehicle_parts.py
// from {os.path.basename(a.psk)} + {os.path.basename(a.psa)}. Do not edit the data by hand; regenerate.
// {len(parts)} parts, {nb} bones, {len(P['seqs'])} sequences, {len(key_lines)} keys (every {a.step} frames).
//=============================================================================
class {a.name}Bike extends RigBike
\tplaceable;

defaultproperties
{{
\tBodySkin="{a.package}.{a.name}.{a.name}Skin"
\tCollisionRadius={max(hi[0] - lo[0], hi[1] - lo[1]) / 2 * 0.8:.1f}
\tCollisionHeight={(hi[2] - lo[2]) / 2 * 0.8:.1f}
""" + "\n".join(bone_lines + part_lines + seq_lines + key_lines) + "\n}\n"
    open(os.path.join(a.out, f"{a.name}Bike.uc"), "w").write(uc)
    open(os.path.join(a.out, f"{a.name}_parts.txt"), "w").write("\n".join(n for n, _, _ in parts) + "\n")
    print(f"VEHICLE_PARTS {a.name}: {len(parts)} parts ({sum(n for *_, n in parts)} tris), {nb} bones, "
          f"{len(seq_lines)} sequences, {len(key_lines)} keys; size {hi - lo}; rotator round-trip error {worst:.2e}")
    for name, b, n in parts:
        print(f"  part {name:32s} bone {bones[b][0]:20s} {n} tris")
    # posed previews, assembled from the parts exactly the way RigBike composes them
    for spec in a.preview:
        sn, fr = spec.split(":")
        s = next(x for x in P["seqs"] if x["name"] == sn)
        keys = psa_mod.frame(P, s, min(int(fr), s["frames"] - 1))
        world = []
        for i, (bname, par, _, _) in enumerate(bones):
            m = xform(*keys[track[bname]], i == 0) if bname in track else local_rest[i]
            world.append(m if par < 0 else world[par] @ m)
        out = [f"# {a.name} {sn} frame {fr}"]
        vbase = 1
        for name, b, n in parts:
            inv = np.linalg.inv(world_rest[b])
            vs = sorted({wedges[k][0] for f in part_faces[b] for k in f})
            idx = {v: j for j, v in enumerate(vs)}
            for v in vs:
                w = world[b] @ inv @ np.append(pts[v], 1)
                out.append(f"v {w[0]:.3f} {w[1]:.3f} {w[2]:.3f}")
            out += [f"f {vbase + idx[wedges[f[0]][0]]} {vbase + idx[wedges[f[1]][0]]} {vbase + idx[wedges[f[2]][0]]}" for f in part_faces[b]]
            vbase += len(vs)
        open(os.path.join(a.out, f"preview_{sn}_{fr}.obj"), "w").write(chr(10).join(out) + chr(10))
        print("  preview", sn, fr)
    # check: the .psa's Idle frame should reproduce the .psk rest pose
    idle = next((s for s in P["seqs"] if s["name"].lower() == "idle"), None)
    if idle:
        keys = psa_mod.frame(P, idle, 0)
        d = max(float(np.abs(xform(*keys[track[bn]], i == 0) - local_rest[i]).max())
                for i, (bn, *_) in enumerate(bones) if bn in track)
        print(f"  idle frame vs rest pose: max difference {d:.4f}")


if __name__ == "__main__":
    main()
