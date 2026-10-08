r"""Read a static mesh straight out of UnrealEd's memory (the ops bridge's !readmesh: the mesh's own source triangles,
UVs, vertex colours, materials) and decode it.

    from readmesh import grab
    mesh = grab(ed, "U2ModelSM.Shapes.GuardPost")        # ed = a uedlib.Ed; injects the ops bridge if needed
    mesh["tris"][0] -> {"v": [(x,y,z)]*3, "uv": [(u,v)]*3, "rgba": [(r,g,b,a)]*3, "mat": 0, "smooth": 1, "flags": 0}
    py readmesh.py FILE.u2rm [out.t3d]                   decode a dump; write it back as a T3D static mesh
"""
import os, struct, sys

TRI = 0x104


def _str(b, o):
    n, = struct.unpack_from("<i", b, o)
    return b[o + 4:o + 4 + 2 * n].decode("utf-16-le"), o + 4 + 2 * n


def decode(path):
    b = open(path, "rb").read()
    if b[:4] != b"U2RM":
        raise ValueError("not a U2RM dump")
    ver, = struct.unpack_from("<i", b, 4)
    name, o = _str(b, 8)
    box = struct.unpack_from("<6f", b, o)
    o += 24
    nm, = struct.unpack_from("<i", b, o)
    o += 4
    mats = []
    for _ in range(nm):
        s, o = _str(b, o)
        mats.append(s)
    nt, = struct.unpack_from("<i", b, o)
    o += 4
    tris = []
    for k in range(nt):
        t = b[o + k * TRI:o + (k + 1) * TRI]
        v = [struct.unpack_from("<3f", t, 12 * i) for i in range(3)]
        uv = [struct.unpack_from("<2f", t, 0x24 + i * 0x40) for i in range(3)]
        col = [struct.unpack_from("<4B", t, 0xe4 + 4 * i) for i in range(3)]          # FColor = B, G, R, A
        mat, smooth, nuv = struct.unpack_from("<iIi", t, 0xf0)
        flags, = struct.unpack_from("<I", t, 0x100)
        tris.append({"v": v, "uv": uv, "rgba": [(c[2], c[1], c[0], c[3]) for c in col], "mat": mat, "smooth": smooth,
                     "nuv": nuv, "flags": flags})
    return {"name": name, "version": ver, "box": box, "materials": mats, "tris": tris}


def to_t3d(mesh, path):
    """back to the T3D static mesh text the editor imports (Version 2.0)"""
    L = ["Begin StaticMesh Name=%s" % mesh["name"].split(".")[-1],
         "Version=2.000000 BoundingBox.Min.X=%f BoundingBox.Min.Y=%f BoundingBox.Min.Z=%f BoundingBox.Max.X=%f BoundingBox.Max.Y=%f BoundingBox.Max.Z=%f" % mesh["box"]]
    for t in mesh["tris"]:
        tex = mesh["materials"][t["mat"]] if t["mat"] < len(mesh["materials"]) and mesh["materials"][t["mat"]] else "Engine.DefaultTexture"
        L += ["Begin Triangle", "Texture %s" % tex, "SmoothingMask %d" % t["smooth"], "PolyFlags %d" % t["flags"]]
        L += ["Vertex %d %.4f %.4f %.4f %.5f %.5f" % (i, *t["v"][i], *t["uv"][i]) for i in range(3)]
        L.append("End Triangle")
    L.append("End StaticMesh")
    open(path, "w").write("\n".join(L) + "\n")


def grab(ed, name, dump=None):
    """!readmesh through the ops bridge of a running uedlib.Ed"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "C", "U2EdBridge"))
    from uedlib import Ops
    dump = dump or os.path.join(os.environ.get("TEMP", "."), name.replace(".", "_") + ".u2rm")
    ops = Ops.attach_to(ed.pid)
    out = ops.exec("!readmesh %s %s" % (name, dump))
    if "readmesh:" not in out or "->" not in out:
        raise RuntimeError(out.strip())
    return decode(dump)


if __name__ == "__main__":
    m = decode(sys.argv[1])
    print("%s: %d triangles, materials %s, box %s" % (m["name"], len(m["tris"]), m["materials"], m["box"]))
    if len(sys.argv) > 2:
        to_t3d(m, sys.argv[2])
        print("->", sys.argv[2])
