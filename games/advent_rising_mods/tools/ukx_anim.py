"""Advent Rising MeshAnimation (build 2226) reader: lists the sequences of an animation set,
expands its keyframe-reduced tracks to one key per frame and writes ActorX .psa files (for
Blender / tools/psa.py) or JSON (for numpy tools).

    py -I tools/ukx_anim.py <package.ukx>                           lists the animation sets
    py -I tools/ukx_anim.py <package.ukx> <set>                     lists its sequences
    py -I tools/ukx_anim.py <package.ukx> <set> <mesh.psk> <out dir> [seq ...]
                                                                    writes <out dir>/<seq>.psa + .json (all seqs if none named)
    py -I tools/ukx_anim.py <package.ukx> <set> <mesh.psk> check    poses frame 0 of each sequence and prints where the feet land

UMeshAnimation as this build serializes it (read off seekers.ukx 'Base'; nothing like UT2004's):
  - int32 0 (no tagged properties), int32 Version (5)
  - RefBones: int32 count, then 12 bytes each: int32 name, int32 flags, int32 parent
  - the key bulk: int32 byte size, then the bytes (every track's arrays back to back, in the
    order of the size table below)
  - Moves: int32 count, one chunk per sequence: FVector RootSpeed3D, float TrackTime (frames),
    int32 StartBone, int32 Flags, TArray<int32> BoneIndices, int32 0, int32 0, TArray<int32>
    Format (per bone), int32 0
  - the size table: int32 per bulk array, per sequence: the root track (3 ints, 0 0 0 here) then
    per bone: Format 1 (a static bone) 2 ints [quat 12 bytes = 3 floats x y z (w implied), pos 12
    bytes], Format 3 or 4 three ints [quats n*6 bytes: 3 x uint16, c = u/65535*2-1, w implied;
    positions m*12 bytes (m = n for 3, 1 for 4); key times n*2 bytes: uint16 frame numbers]
  - AnimSeqs: int32 count, then per sequence: float (blend-in?), int32, int32 name,
    TArray<int32> groups, int32 StartFrame, int32 NumFrames, TArray<{float time, int32 function,
    int32 notify object}>, float Rate
Quaternions are kept as ActorX stores them (children conjugated, the root as is): posing with
the children's quats conjugated puts the feet on the floor (y 0) and the head up (y -82), the
plain quats don't (the check mode shows both). JSON keys are therefore in .psa form too.
"""
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ukx import Package  # noqa: E402


class AnimError(Exception):
    pass


def read_anim(p, e):
    d = p.d
    r = e["off"]
    end = r + e["size"]
    i32 = lambda at: struct.unpack_from("<i", d, at)[0]
    if i32(r) != 0:
        raise AnimError("tagged properties present")
    version = i32(r + 4)
    nb = i32(r + 8)
    r += 12
    bones = []
    for _ in range(nb):
        nm, fl, par = struct.unpack_from("<iii", d, r)
        bones.append(dict(name=p.names[nm], flags=fl, parent=par))
        r += 12
    bulk_size = i32(r)
    bulk = d[r + 4:r + 4 + bulk_size]
    r += 4 + bulk_size
    nchunks = i32(r)
    r += 4
    chunks = []
    for _ in range(nchunks):
        rs = struct.unpack_from("<3f", d, r)
        tt, sb, fl = struct.unpack_from("<fii", d, r + 12)
        n = i32(r + 24)
        bi = struct.unpack_from("<%di" % n, d, r + 28)
        r += 28 + 4 * n
        z1, z2 = struct.unpack_from("<ii", d, r)
        n2 = i32(r + 8)
        fmt = struct.unpack_from("<%di" % n2, d, r + 12)
        r += 12 + 4 * n2
        z3 = i32(r)
        r += 4
        if (z1, z2, z3) != (0, 0, 0) or n2 != nb:
            raise AnimError("a motion chunk isn't laid out as expected (%d %d %d, %d formats for %d bones)" % (z1, z2, z3, n2, nb))
        chunks.append(dict(rootspeed=rs, tracktime=tt, startbone=sb, flags=fl, boneidx=bi, fmt=fmt))
    # the size table, laid out by the chunks' formats
    tracks = []     # per sequence: (root sizes, [per bone sizes])
    for c in chunks:
        root = struct.unpack_from("<3i", d, r)
        r += 12
        per = []
        for f in c["fmt"]:
            w = 2 if f == 1 else 3
            per.append(struct.unpack_from("<%di" % w, d, r))
            r += 4 * w
        tracks.append((root, per))
    nseq = i32(r)
    r += 4
    seqs = []
    for _ in range(nseq):
        a, b, nm = struct.unpack_from("<fii", d, r)
        r += 12
        ng = i32(r)
        groups = [p.names[g] for g in struct.unpack_from("<%di" % ng, d, r + 4)]
        r += 4 + 4 * ng
        sf, nf = struct.unpack_from("<ii", d, r)
        r += 8
        nn = i32(r)
        notes = [struct.unpack_from("<fii", d, r + 4 + 12 * k) for k in range(nn)]
        r += 4 + 12 * nn
        rate = struct.unpack_from("<f", d, r)[0]
        r += 4
        seqs.append(dict(name=p.names[nm], groups=groups, start=sf, frames=nf, rate=rate, blend=a, notifies=notes))
    if r != end:
        raise AnimError("parse ended at %d of %d" % (r - e["off"], e["size"]))
    if nseq != nchunks:
        raise AnimError("%d sequences for %d chunks" % (nseq, nchunks))
    return dict(name=e["name"], version=version, bones=bones, bulk=bulk, chunks=chunks, tracks=tracks, seqs=seqs)


def unpack_quat16(raw):
    u = struct.unpack("<3H", raw)
    x, y, z = [v / 65535.0 * 2 - 1 for v in u]
    w = math.sqrt(max(0.0, 1 - x * x - y * y - z * z))
    return (x, y, z, w)


def decode_tracks(anim, s):
    """per bone: (keys [(frame, quat, pos)]) with the keyframe-reduced keys as stored"""
    bulk = anim["bulk"]
    o = 0
    for k in range(s):
        root, per = anim["tracks"][k]
        o += sum(root) + sum(sum(x) for x in per)
    root, per = anim["tracks"][s]
    o += sum(root)
    out = []
    for b, sizes in enumerate(per):
        if len(sizes) == 2:
            qx, qy, qz = struct.unpack_from("<3f", bulk, o)
            w = math.sqrt(max(0.0, 1 - qx * qx - qy * qy - qz * qz))
            pos = struct.unpack_from("<3f", bulk, o + 12)
            out.append([(0, (qx, qy, qz, w), pos)])
            o += 24
        else:
            qs, ps, ts = sizes
            n = ts // 2 if ts else qs // 6        # no time array: one key per frame
            if qs != 6 * n or ps % 12 or (ps // 12 not in (1, n)):
                raise AnimError("track sizes %s don't fit %d keys" % (sizes, n))
            quats = [unpack_quat16(bulk[o + 6 * i:o + 6 * i + 6]) for i in range(n)]
            o += qs
            poss = [struct.unpack_from("<3f", bulk, o + 12 * i) for i in range(ps // 12)]
            o += ps
            times = struct.unpack_from("<%dH" % n, bulk, o) if ts else tuple(range(n))
            o += ts
            out.append([(times[i], quats[i], poss[i if len(poss) > 1 else 0]) for i in range(n)])
    return out


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b = tuple(-x for x in b)
        d = -d
    if d > 0.9995:
        q = tuple(x + t * (y - x) for x, y in zip(a, b))
    else:
        th = math.acos(d)
        s = math.sin(th)
        q = tuple((math.sin((1 - t) * th) * x + math.sin(t * th) * y) / s for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


def expand(anim, s):
    """every frame of sequence s: [frame][bone] -> (quat, pos), interpolated between keys"""
    seq = anim["seqs"][s]
    tracks = decode_tracks(anim, s)
    frames = []
    for f in range(seq["frames"]):
        row = []
        for keys in tracks:
            if len(keys) == 1 or f <= keys[0][0]:
                row.append((keys[0][1], keys[0][2]))
                continue
            if f >= keys[-1][0]:
                row.append((keys[-1][1], keys[-1][2]))
                continue
            for i in range(len(keys) - 1):
                if keys[i][0] <= f <= keys[i + 1][0]:
                    t0, q0, p0 = keys[i]
                    t1, q1, p1 = keys[i + 1]
                    t = (f - t0) / float(t1 - t0) if t1 > t0 else 0.0
                    row.append((slerp(q0, q1, t), tuple(a + t * (b - a) for a, b in zip(p0, p1))))
                    break
        frames.append(row)
    return frames


# ---------------------------------------------------------------- psk skeleton, posing, output

def read_psk_bones(path):
    d = open(path, "rb").read()
    o = 0
    while o + 32 <= len(d):
        cid = d[o:o + 20].split(b"\0")[0]
        size, count = struct.unpack_from("<ii", d, o + 24)
        o += 32
        if cid == b"REFSKELT":
            out = []
            for i in range(count):
                r = struct.unpack_from("<64sIii4f3ff3f", d, o + 120 * i)
                out.append(dict(name=r[0].split(b"\0")[0].decode("latin1"), children=r[2], parent=r[3], quat=r[4:8], pos=r[8:11]))
            return out
        o += size * count
    raise AnimError("no skeleton in " + path)


def quat_mat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, v):
    return tuple(sum(a[i][k] * v[k] for k in range(3)) for i in range(3))


def pose(bones, frame, conj_child=False, conj_root=False):
    """mesh-space (R, O) per bone from a frame's local (quat, pos): O = O_p + R_p pos, R = R_p L"""
    R, O = [], []
    for i, b in enumerate(bones):
        q, pos = frame[i]
        if (i == 0 and conj_root) or (i > 0 and conj_child):
            q = (-q[0], -q[1], -q[2], q[3])
        L = quat_mat(q)
        if i == 0:
            R.append(L)
            O.append(tuple(pos))
        else:
            par = b["parent"]
            R.append(mm(R[par], L))
            O.append(tuple(a + c for a, c in zip(O[par], mv(R[par], pos))))
    return R, O


def chunk(fh, cid, size, recs):
    fh.write(struct.pack("<20sIii", cid.encode(), 1999801, size, len(recs)))
    for r in recs:
        fh.write(r)


def write_psa(path, bones, name, rate, frames):
    """ActorX .psa, one sequence. The engine keeps the keys as ActorX stores them (children
    conjugated: the pose check proves it, feet on the floor only with the children's quats
    conjugated), so they go out untouched."""
    names = [struct.pack("<64sIii4f3ff3f", b["name"].encode(), 0, b["children"], b["parent"], 0, 0, 0, 1, *b["pos"], 0, 0, 0, 0) for b in bones]
    keys = []
    for row in frames:
        for i, (q, pos) in enumerate(row):
            keys.append(struct.pack("<3f4ff", *pos, *q, 1.0))
    info = struct.pack("<64s64siiiifffiii", name.encode(), b"None", len(bones), 0, 0, len(keys), 0.0, float(len(frames)), float(rate), 0, 0, len(frames))
    with open(path, "wb") as fh:
        chunk(fh, "ANIMHEAD", 0, [])
        chunk(fh, "BONENAMES", 120, names)
        chunk(fh, "ANIMINFO", 168, [info])
        chunk(fh, "ANIMKEYS", 32, keys)


def main():
    p = Package(sys.argv[1])
    anims = [e for e in p.exports if p.cls(e) == "MeshAnimation"]
    if len(sys.argv) < 3:
        for e in anims:
            print("%-32s %8d" % (e["name"], e["size"]))
        return
    want = sys.argv[2].lower()
    e = [e for e in anims if e["name"].lower() == want]
    if not e:
        sys.exit("no animation set %s" % want)
    anim = read_anim(p, e[0])
    if len(sys.argv) < 5:
        print("%s: version %d, %d bones, %d sequences" % (anim["name"], anim["version"], len(anim["bones"]), len(anim["seqs"])))
        for i, s in enumerate(anim["seqs"]):
            c = anim["chunks"][i]
            print("%3d %-28s frames %4d rate %5.1f (%.2fs) flags %d groups %s" % (i, s["name"], s["frames"], s["rate"], s["frames"] / max(s["rate"], 1e-6), c["flags"], ",".join(s["groups"])))
        return
    bones = read_psk_bones(sys.argv[3])
    if [b["name"].lower() for b in bones] != [b["name"].lower() for b in anim["bones"]]:
        sys.exit("the mesh's bones aren't the animation's (%d vs %d)" % (len(bones), len(anim["bones"])))
    if sys.argv[4] == "check":
        feet = [i for i, b in enumerate(bones) if "foot" in b["name"].lower() or "toe" in b["name"].lower()]
        head = [i for i, b in enumerate(bones) if b["name"].lower() == "head"]
        for s, seq in enumerate(anim["seqs"]):
            frames = expand(anim, s)
            line = []
            for cc in (False, True):
                R, O = pose(bones, frames[0], conj_child=cc)
                fy = [O[i][1] for i in feet]
                hy = O[head[0]][1] if head else 0
                line.append("child%s: feet y %s head y %.0f" % (" conj" if cc else " plain", " ".join("%.0f" % y for y in fy), hy))
            print("%-24s hips %s | %s" % (seq["name"], " ".join("%.0f" % v for v in frames[0][0][1]), " | ".join(line)))
        return
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)
    names = [n.lower() for n in sys.argv[5:]]
    for s, seq in enumerate(anim["seqs"]):
        if names and seq["name"].lower() not in names:
            continue
        frames = expand(anim, s)
        write_psa(os.path.join(out, seq["name"] + ".psa"), bones, seq["name"], seq["rate"], frames)
        json.dump(dict(name=seq["name"], set=anim["name"], rate=seq["rate"], frames=[[list(q) + list(pos) for q, pos in row] for row in frames],
                       bones=[b["name"] for b in bones], groups=seq["groups"]),
                  open(os.path.join(out, seq["name"] + ".json"), "w"))
        print("%s: %d frames at %.0f fps -> %s" % (seq["name"], len(frames), seq["rate"], os.path.join(out, seq["name"] + ".psa")))


if __name__ == "__main__":
    main()
