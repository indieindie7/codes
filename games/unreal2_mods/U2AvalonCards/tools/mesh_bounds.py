"""Bounding boxes of the static meshes in stock UE2 packages (.usx), read straight from the file: each
StaticMesh export starts (after its property list) with UPrimitive's FBox BoundingBox.

    python mesh_bounds.py <out.txt> <pkg.usx> [<pkg.usx> ...] [groups=Grp1,Grp2]

Writes one line per mesh: Package.Group.Name minX minY minZ maxX maxY maxZ (CardGallery reads them).
"""
import struct, sys


def ci(d, p):
    b = d[p]; p += 1
    neg = b & 0x80; v = b & 0x3F
    if b & 0x40:
        sh = 6
        while True:
            b = d[p]; p += 1
            v |= (b & 0x7F) << sh; sh += 7
            if not b & 0x80:
                break
    return (-v if neg else v), p


def skip_props(d, p, names):
    while True:
        n, p = ci(d, p)
        if names[n] == "None":
            return p
        info = d[p]; p += 1
        t, sc, arr = info & 0x0F, (info >> 4) & 7, info & 0x80
        if t == 10:                      # struct: its name follows
            _, p = ci(d, p)
        size = {0: 1, 1: 2, 2: 4, 3: 12, 4: 16}.get(sc)
        if sc == 5:
            size = d[p]; p += 1
        elif sc == 6:
            size = struct.unpack_from("<H", d, p)[0]; p += 2
        elif sc == 7:
            size = struct.unpack_from("<I", d, p)[0]; p += 4
        if arr and t != 3:               # array index (not for bools)
            b = d[p]
            p += 1 if b < 0x80 else (2 if b < 0xC0 else 4)
        if t != 3:
            p += size


def read(path, groups):
    d = open(path, "rb").read()
    tag, ver, lic, flags, nn, no, en, eo, im, io = struct.unpack_from("<IHHIIIIIII", d, 0)
    names, p = [], no
    for _ in range(nn):
        l, p = ci(d, p)
        names.append(d[p:p + l - 1].decode("latin1")); p += l + 4
    imps, p = [], io
    for _ in range(im):
        cp, p = ci(d, p); cn, p = ci(d, p); pk = struct.unpack_from("<i", d, p)[0]; p += 4; on, p = ci(d, p)
        imps.append(names[on])
    exps, p = [], eo
    for _ in range(en):
        cl, p = ci(d, p); su, p = ci(d, p); pk = struct.unpack_from("<i", d, p)[0]; p += 4
        nm, p = ci(d, p); p += 4; sz, p = ci(d, p); off = 0
        if sz > 0:
            off, p = ci(d, p)
        exps.append((cl, pk, names[nm], sz, off))

    def full(i):
        cl, pk, nm, _, _ = exps[i]
        return (full(pk - 1) + "." if pk > 0 else "") + nm

    pkg = path.replace("\\", "/").split("/")[-1].split(".")[0]
    for i, (cl, pk, nm, sz, off) in enumerate(exps):
        cls = imps[-cl - 1] if cl < 0 else (exps[cl - 1][2] if cl > 0 else "Class")
        if cls != "StaticMesh" or sz <= 0:
            continue
        f = pkg + "." + full(i)
        if groups and f.split(".")[1].lower() not in groups:
            continue
        q = skip_props(d, off, names)
        box = struct.unpack_from("<6f", d, q)
        if not all(abs(v) < 1e6 for v in box) or any(box[k] > box[k + 3] for k in range(3)):
            print("odd bounds", f, box, file=sys.stderr)
            continue
        yield f, box


out = sys.argv[1]
args = [a for a in sys.argv[2:] if not a.startswith("groups=")]
groups = set()
for a in sys.argv[2:]:
    if a.startswith("groups="):
        groups = {g.lower() for g in a[7:].split(",")}
n = 0
with open(out, "w") as fo:
    for path in args:
        for f, b in read(path, groups):
            fo.write("%s %s\n" % (f, " ".join("%.0f" % v for v in b)))
            n += 1
print(n, "meshes ->", out)
