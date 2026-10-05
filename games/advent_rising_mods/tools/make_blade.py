"""Writes the energy blade (ModBlade): AdventMod/Meshes/blade.ase and its two textures in
AdventMod/Textures (blade_glow.tga, blade_hilt.tga). Our own geometry and pictures.

The blade lies along +X with the grip at the origin: a short eight-sided hilt, a guard, and a
long flat diamond-section blade that tapers to a point. Material 0 is the hilt, 1 the blade
(drawn unlit, so the glow texture is its light). Every triangle has both windings, so it shows
whichever way the importer mirrors.

    python tools/make_blade.py
"""
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
MESH = os.path.join(HERE, "..", "AdventMod", "Meshes", "blade.ase")
TEX = os.path.join(HERE, "..", "AdventMod", "Textures")


class Mesh:
    def __init__(self):
        self.v, self.uv, self.f = [], [], []          # faces: (a, b, c, material)

    def ring(self, x, ry, rz, n, u):
        first = len(self.v)
        for i in range(n):
            a = 2 * math.pi * i / n
            self.v.append((x, ry * math.cos(a), rz * math.sin(a)))
            self.uv.append((u, i / n))
        return first

    def join(self, a, b, n, mat):
        for i in range(n):
            j = (i + 1) % n
            self.f += [(a + i, b + i, a + j, mat), (a + j, b + i, b + j, mat)]

    def cap(self, ring, n, x, u, mat):
        c = len(self.v)
        self.v.append((x, 0.0, 0.0))
        self.uv.append((u, 0.5))
        for i in range(n):
            self.f.append((c, ring + i, ring + (i + 1) % n, mat))


def build():
    m = Mesh()
    # the hilt: a pommel, the grip, the guard
    r0 = m.ring(-9.0, 1.6, 1.6, 8, 0.0)
    m.cap(r0, 8, -10.0, 0.0, 0)
    r1 = m.ring(-8.0, 1.2, 1.2, 8, 0.1)
    r2 = m.ring(0.0, 1.3, 1.3, 8, 0.6)
    r3 = m.ring(0.5, 3.2, 1.6, 8, 0.8)
    r4 = m.ring(2.0, 3.2, 1.6, 8, 1.0)
    for a, b in ((r0, r1), (r1, r2), (r2, r3), (r3, r4)):
        m.join(a, b, 8, 0)
    m.cap(r4, 8, 2.0, 1.0, 0)
    # the blade: flat diamond section (4 sides), widest near the guard, to a point
    b0 = m.ring(2.0, 2.6, 0.55, 4, 0.0)
    b1 = m.ring(10.0, 2.9, 0.6, 4, 0.15)
    b2 = m.ring(48.0, 2.3, 0.5, 4, 0.8)
    b3 = m.ring(58.0, 1.2, 0.3, 4, 0.95)
    for a, b in ((b0, b1), (b1, b2), (b2, b3)):
        m.join(a, b, 4, 1)
    m.cap(b3, 4, 64.0, 1.0, 1)
    m.f += [(a, c, b, mat) for a, b, c, mat in m.f]
    return m


def write_ase(m):
    L = ['*3DSMAX_ASCIIEXPORT\t200', '*COMMENT "make_blade.py"', '*MATERIAL_LIST {', '\t*MATERIAL_COUNT 1',
         '\t*MATERIAL 0 {', '\t\t*MATERIAL_NAME "blade_mat"', '\t\t*MATERIAL_CLASS "Multi/Sub-Object"', '\t\t*NUMSUBMTLS 2']
    for i, name in enumerate(("hilt", "glow")):
        L += ['\t\t*SUBMATERIAL %d {' % i, '\t\t\t*MATERIAL_NAME "%s"' % name, '\t\t\t*MATERIAL_CLASS "Standard"',
              '\t\t\t*MAP_DIFFUSE {', '\t\t\t\t*MAP_NAME "%s"' % name, '\t\t\t\t*BITMAP "%s.bmp"' % name, '\t\t\t}', '\t\t}']
    L += ['\t}', '}', '*GEOMOBJECT {', '\t*NODE_NAME "blade"', '\t*MESH {', '\t\t*TIMEVALUE 0',
          '\t\t*MESH_NUMVERTEX %d' % len(m.v), '\t\t*MESH_NUMFACES %d' % len(m.f), '\t\t*MESH_VERTEX_LIST {']
    L += ['\t\t\t*MESH_VERTEX %d\t%.5f\t%.5f\t%.5f' % ((i,) + v) for i, v in enumerate(m.v)]
    L += ['\t\t}', '\t\t*MESH_FACE_LIST {']
    L += ['\t\t\t*MESH_FACE %d: A: %d B: %d C: %d AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID %d' % ((i,) + f)
          for i, f in enumerate(m.f)]
    L += ['\t\t}', '\t\t*MESH_NUMTVERTEX %d' % len(m.uv), '\t\t*MESH_TVERTLIST {']
    L += ['\t\t\t*MESH_TVERT %d\t%.6f\t%.6f\t0.0000' % ((i,) + uv) for i, uv in enumerate(m.uv)]
    L += ['\t\t}', '\t\t*MESH_NUMTVFACES %d' % len(m.f), '\t\t*MESH_TFACELIST {']
    L += ['\t\t\t*MESH_TFACE %d\t%d\t%d\t%d' % (i, f[0], f[1], f[2]) for i, f in enumerate(m.f)]
    L += ['\t\t}', '\t}', '\t*MATERIAL_REF 0', '}']
    os.makedirs(os.path.dirname(MESH), exist_ok=True)
    open(MESH, "w", newline="\r\n").write("\n".join(L) + "\n")
    print(MESH, len(m.v), "verts,", len(m.f), "faces")


def write_tga(name, size, pixel):
    px = bytearray()
    for y in range(size):
        for x in range(size):
            r, g, b = pixel(x / (size - 1), y / (size - 1))
            px += bytes([int(255 * min(max(c, 0), 1) + 0.5) for c in (b, g, r)] + [255])
    path = os.path.join(TEX, name + ".tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


def glow(u, v):
    # white-hot along the blade's middle (v is around the section), cyan at the edges,
    # brighter toward the guard
    edge = abs(math.sin(v * 2 * math.pi))
    core = 0.75 + 0.25 * (1 - u)
    return (core * (0.55 + 0.45 * (1 - edge)), core, core)


def hilt(u, v):
    band = 0.5 + 0.5 * math.sin(u * 60)                      # a ribbed grip
    k = 0.10 + 0.06 * band + (0.25 if u > 0.75 else 0)       # the guard a little brighter
    return (k, k * 1.02, k * 1.08)


if __name__ == "__main__":
    write_ase(build())
    write_tga("blade_glow", 64, glow)
    write_tga("blade_hilt", 64, hilt)
