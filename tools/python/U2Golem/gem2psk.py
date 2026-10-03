"""Unreal II Golem character (.gem) -> ActorX .psk, for Blender and the U2Golem importer.
Usage: py -3.13 gem2psk.py <in.gem> <out.psk>

Golem stores the mesh in model space, Y up, with the skeleton as parent-relative
position + quaternion. The .psk is written Z up (as UT2004's are) with ActorX's quaternion
convention (child bones conjugated, the root as is).
"""
import math, struct, sys
import numpy as np
from gem import Gem


def chunk(cid, size, recs):
    data = b"".join(recs)
    return struct.pack("<20siii", cid.encode(), 1999801, size, len(recs)) + data


def qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return (w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2)


# Y up -> Z up: rotate +90 degrees about X  (x, y, z) -> (x, -z, y)
UP = (math.sin(math.pi / 4), 0.0, 0.0, math.cos(math.pi / 4))


def zup(v):
    return (v[0], -v[2], v[1])


def convert(src, dst):
    g = Gem(src)
    names, pts, spans, weights, normals = g.bone_points()
    bones = g.bones()
    verts, uvs, tris, mats = g.vertices(), g.uvs(), g.triangles(), g.materials()
    nmat = max(t[3] for t in tris) + 1

    out = [struct.pack("<20siii", b"ACTRHEAD", 1999801, 0, 0)]
    out.append(chunk("PNTS0000", 12, [struct.pack("<3f", *zup(p)) for p in pts]))
    vmat = {}
    for a, b, c, m in tris:
        for v in (a, b, c):
            vmat[v] = m
    out.append(chunk("VTXW0000", 16, [struct.pack("<HHffBBH", p, 0, uvs[t][0], uvs[t][1], vmat.get(i, 0), 0, 0)
                                      for i, (p, n, t) in enumerate(verts)]))
    out.append(chunk("FACE0000", 12, [struct.pack("<HHHBBI", a, b, c, m, 0, 1) for a, b, c, m in tris]))
    out.append(chunk("MATT0000", 88, [struct.pack("<64siiiiii", (mats[i] if i < len(mats) else "Mat%d" % i).encode(), i, 0, 0, 0, 0, 0)
                                      for i in range(nmat)]))
    kids = [sum(1 for b in bones if b[1] == i) for i in range(len(bones))]
    recs = []
    for i, (name, parent, pos, q) in enumerate(bones):
        if parent < 0:
            q = qmul(UP, q)
            pos = zup(pos)
            parent = 0
        else:
            q = (-q[0], -q[1], -q[2], q[3])      # ActorX stores child rotations inverted
        recs.append(struct.pack("<64sIii" + "f" * 11, name.encode(), 0, kids[i], parent, *q, *pos, 0.0, 1.0, 1.0, 1.0))
    out.append(chunk("REFSKELT", 120, recs))
    bone_index = {n: i for i, n in enumerate(b[0] for b in bones)}
    wrecs = []
    for p, (cnt, first) in enumerate(spans):
        for k in range(cnt):
            bi, w = weights[first + k]
            # weight bone indices refer to the BonePoints bone list (names), map to the hierarchy
            wrecs.append(struct.pack("<fii", w, p, bone_index[names[bi]]))
    out.append(chunk("RAWWEIGHTS", 12, wrecs))
    open(dst, "wb").write(b"".join(out))
    print(f"{dst}: {len(pts)} points, {len(verts)} wedges, {len(tris)} faces, {nmat} materials {mats}, {len(bones)} bones, {len(wrecs)} weights")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
