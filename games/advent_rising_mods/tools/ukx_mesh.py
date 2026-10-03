"""Advent Rising skeletal meshes -> ActorX .psk (points, wedges, faces, materials,
reference skeleton, weights), for tools that cut them up (gib parts) or view them.

    python ukx_mesh.py <package.ukx>                      lists the skeletal meshes
    python ukx_mesh.py <package.ukx> <mesh|*> <out dir>    writes <mesh>.psk (+ a .txt summary)

USkeletalMesh as Advent's build 2226 serializes it (found on humans.ukx 'marine'):
  - int32 0: no tagged properties ("None")
  - FBox as 6 floats (no IsValid byte), FSphere (4 floats)
  - ULodMesh: int32 version (4), int32 ModelVerts, TArray Verts (int32 count, empty for
    skeletal), TArray<UMaterial*> (int32 count + int32 object refs), Scale, Origin,
    RotOrigin (int32 x3), then LOD settings
  - the reference skeleton: int32 count, then 60-byte FMeshBone: int32 name, uint32 flags,
    quat (4 floats), position (3), length, size (3), int32 children, int32 parent
  - the main arrays are lazy arrays: int32 absolute file offset of the array's end, int32
    count, the items. Influences (8 bytes: float weight, uint16 point, uint16 bone),
    wedges (10 bytes: uint16 point, float U, float V), faces (8 bytes: uint16 wedge x3,
    uint16 material), points (12 bytes: FVector)
Arrays are found by structure (the skip offset has to land exactly where count x size
ends) rather than at fixed offsets, so each mesh is checked as it is read.
"""
import os, struct, sys
from collections import defaultdict
from ukx import Package, Reader


class MeshError(Exception):
    pass


def lazy_arrays(d, start, end):
    """every (pos of items, count, item size) whose skip offset matches exactly"""
    out = []
    q = start
    while q < end - 8:
        skip, count = struct.unpack_from("<ii", d, q)
        if q + 8 < skip <= end and 0 < count < 1000000:
            n = skip - (q + 8)
            if n % count == 0 and n // count in (2, 4, 8, 10, 12, 16, 20, 24, 32):
                out.append((q + 8, count, n // count))
                q = skip
                continue
        q += 1
    return out


def read_mesh(p, e):
    d = p.d
    base, end = e["off"], e["off"] + e["size"]
    r = Reader(d, base)
    if r.i32() != 0:
        raise MeshError("tagged properties present (not handled)")
    box = [r.f32() for _ in range(6)]
    r.p += 16
    version = r.i32()
    model_verts = r.i32()
    n = r.i32()
    r.p += 4 * n
    n = r.i32()
    materials = [p.objname(r.i32()) for _ in range(n)]
    # the skeleton: the first count + run of 60-byte bones that hangs together (names
    # valid, unit rotations, every parent earlier than its child, children adding up)
    bones = None
    for q in range(r.p, min(r.p + 4000, end)):
        c = struct.unpack_from("<i", d, q)[0]
        if not 2 <= c <= 256 or q + 4 + 60 * c > end:
            continue
        ok = True
        kids = 0
        bl = []
        for i in range(c):
            rec = struct.unpack_from("<iI4f3ff3fii", d, q + 4 + 60 * i)
            name, flags = rec[0], rec[1]
            nchild, parent = rec[13], rec[14]
            qlen = sum(x * x for x in rec[2:6])
            if not (0 <= name < len(p.names)) or not (0 <= parent <= max(i - 1, 0)) or not (0 <= nchild < c) or abs(qlen - 1) > 0.01:
                ok = False
                break
            kids += nchild
            bl.append(dict(name=p.names[name], flags=flags, quat=rec[2:6], pos=rec[6:9], length=rec[9], size=rec[10:13], children=nchild, parent=parent))
        if ok and kids == c - 1:
            bones = bl
            after_bones = q + 4 + 60 * c
            break
    if bones is None:
        raise MeshError("no skeleton found")
    arrays = lazy_arrays(d, after_bones, end)
    infl = wedges = faces = points = None
    for pos, count, size in arrays:
        if size == 12 and count == model_verts:
            # two arrays of this shape: the points are the one whose extents fit the box
            pts = [struct.unpack_from("<3f", d, pos + 12 * i) for i in range(count)]
            ext = [min(v[k] for v in pts) for k in range(3)] + [max(v[k] for v in pts) for k in range(3)]
            score = sum(abs(a - b) for a, b in zip(ext, box))
            if points is None or score < points_score:
                points, points_score = pts, score
        elif size == 8 and infl is None:
            recs = [struct.unpack_from("<fHH", d, pos + 8 * i) for i in range(count)]
            tot = defaultdict(float)
            for w, pt, b in recs:
                tot[pt] += w
            if len(tot) == model_verts and all(abs(v - 1) < 0.01 for v in tot.values()) and all(b < len(bones) for _, _, b in recs):
                infl = recs
        elif size == 10 and wedges is None:
            wedges = [struct.unpack_from("<Hff", d, pos + 10 * i) for i in range(count)]
        elif size == 8 and wedges is not None and faces is None:
            fs = [struct.unpack_from("<4H", d, pos + 8 * i) for i in range(count)]
            if all(max(f[:3]) < len(wedges) for f in fs):
                faces = fs
    for what, v in (("influences", infl), ("wedges", wedges), ("faces", faces), ("points", points)):
        if v is None:
            raise MeshError("no %s found (arrays: %s)" % (what, [(pos - base, c, s) for pos, c, s in arrays][:20]))
    if max(w[0] for w in wedges) >= len(points):
        raise MeshError("a wedge points past the points")
    return dict(name=e["name"], materials=materials, bones=bones, points=points, wedges=wedges, faces=faces, influences=infl, box=box, version=version)


def chunk(fh, cid, size, items):
    fh.write(struct.pack("<20sIii", cid.encode(), 1999801, size, len(items)))
    for it in items:
        fh.write(it)


def write_psk(m, path):
    nmat = max(1, len(m["materials"]))
    # each wedge takes the material of a face that uses it
    wmat = [0] * len(m["wedges"])
    for a, b, c, mat in m["faces"]:
        for w in (a, b, c):
            wmat[w] = min(mat, nmat - 1)
    with open(path, "wb") as fh:
        chunk(fh, "ACTRHEAD", 0, [])
        chunk(fh, "PNTS0000", 12, [struct.pack("<3f", *pt) for pt in m["points"]])
        chunk(fh, "VTXW0000", 16, [struct.pack("<HHffBBH", pt, 0, u, v, wmat[i], 0, 0) for i, (pt, u, v) in enumerate(m["wedges"])])
        chunk(fh, "FACE0000", 12, [struct.pack("<3HBBI", a, b, c, min(mat, nmat - 1), 0, 1) for a, b, c, mat in m["faces"]])
        mats = m["materials"] or ["default"]
        chunk(fh, "MATT0000", 88, [struct.pack("<64siIiIii", name.encode()[:63], i, 0, 0, 0, 0, 0) for i, name in enumerate(mats)])
        chunk(fh, "REFSKELT", 120, [struct.pack("<64sIii4f3ff3f", b["name"].encode()[:63], 0, b["children"], b["parent"], *b["quat"], *b["pos"], b["length"], *b["size"]) for b in m["bones"]])
        chunk(fh, "RAWWEIGHTS", 12, [struct.pack("<fii", w, pt, bone) for w, pt, bone in m["influences"]])


def summary(m):
    lines = ["mesh %s: %d points, %d wedges, %d faces, %d influences, %d bones" % (m["name"], len(m["points"]), len(m["wedges"]), len(m["faces"]), len(m["influences"]), len(m["bones"])),
             "materials: " + ", ".join(m["materials"]),
             "bounding box: %s" % [round(x, 1) for x in m["box"]],
             "bones (index name parent):"]
    lines += ["  %d %s %d" % (i, b["name"], b["parent"]) for i, b in enumerate(m["bones"])]
    return "\n".join(lines) + "\n"


def main():
    p = Package(sys.argv[1])
    meshes = [e for e in p.exports if p.cls(e) == "SkeletalMesh"]
    if len(sys.argv) < 4:
        for e in meshes:
            print("%-32s %8d" % (e["name"], e["size"]))
        return
    want, out = sys.argv[2].lower(), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    for e in meshes:
        if want != "*" and e["name"].lower() != want:
            continue
        try:
            m = read_mesh(p, e)
        except MeshError as err:
            print("%s: %s" % (e["name"], err))
            continue
        write_psk(m, os.path.join(out, m["name"] + ".psk"))
        open(os.path.join(out, m["name"] + ".txt"), "w").write(summary(m))
        print("%s: %d points, %d faces, %d bones, materials %s" % (m["name"], len(m["points"]), len(m["faces"]), len(m["bones"]), m["materials"]))


if __name__ == "__main__":
    main()
