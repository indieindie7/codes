"""Writes the rubble pieces (ModRubble): AdventMod/Meshes/rubble0.ase and rubble1.ase, lumpy
angular chunks of about unit radius, and their texture AdventMod/Textures/dirt_rock.tga
(grey, mottled). Our own geometry and picture. Both windings on every triangle, so a piece
shows whichever way the importer mirrors.

    python tools/make_rubble.py
"""
import math
import os
import random
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
MESHES = os.path.join(HERE, "..", "AdventMod", "Meshes")
TEX = os.path.join(HERE, "..", "AdventMod", "Textures")
RINGS, SEGS = 4, 6


def chunk(seed, flat):
    rng = random.Random(seed)
    verts, uvs = [(0.0, 0.0, flat)], [(0.5, 0.0)]
    for r in range(1, RINGS):
        phi = math.pi * r / RINGS
        for s in range(SEGS):
            th = 2 * math.pi * (s + 0.5 * (r % 2)) / SEGS
            k = 1.0 + rng.uniform(-0.35, 0.25)                  # broken, not round
            verts.append((k * math.sin(phi) * math.cos(th), k * math.sin(phi) * math.sin(th), flat * k * math.cos(phi)))
            uvs.append((s / SEGS, r / RINGS))
    verts.append((0.0, 0.0, -flat))
    uvs.append((0.5, 1.0))
    last = len(verts) - 1
    faces = []
    for s in range(SEGS):
        a, b = 1 + s, 1 + (s + 1) % SEGS
        faces.append((0, a, b))
        for r in range(RINGS - 2):
            p, q = 1 + r * SEGS + s, 1 + r * SEGS + (s + 1) % SEGS
            faces += [(p, p + SEGS, q), (q, p + SEGS, q + SEGS)]
        a, b = 1 + (RINGS - 2) * SEGS + s, 1 + (RINGS - 2) * SEGS + (s + 1) % SEGS
        faces.append((a, last, b))
    faces += [(a, c, b) for a, b, c in faces]
    return verts, uvs, faces


def write_ase(name, verts, uvs, faces):
    L = ['*3DSMAX_ASCIIEXPORT\t200', '*COMMENT "make_rubble.py"', '*MATERIAL_LIST {', '\t*MATERIAL_COUNT 1',
         '\t*MATERIAL 0 {', '\t\t*MATERIAL_NAME "rock"', '\t\t*MATERIAL_CLASS "Standard"', '\t\t*MAP_DIFFUSE {',
         '\t\t\t*MAP_NAME "rock"', '\t\t\t*BITMAP "rock.bmp"', '\t\t}', '\t}', '}', '*GEOMOBJECT {',
         '\t*NODE_NAME "%s"' % name, '\t*MESH {', '\t\t*TIMEVALUE 0', '\t\t*MESH_NUMVERTEX %d' % len(verts),
         '\t\t*MESH_NUMFACES %d' % len(faces), '\t\t*MESH_VERTEX_LIST {']
    L += ['\t\t\t*MESH_VERTEX %d\t%.5f\t%.5f\t%.5f' % ((i,) + v) for i, v in enumerate(verts)]
    L += ['\t\t}', '\t\t*MESH_FACE_LIST {']
    L += ['\t\t\t*MESH_FACE %d: A: %d B: %d C: %d AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 0 *MESH_MTLID 0' % ((i,) + f)
          for i, f in enumerate(faces)]
    L += ['\t\t}', '\t\t*MESH_NUMTVERTEX %d' % len(uvs), '\t\t*MESH_TVERTLIST {']
    L += ['\t\t\t*MESH_TVERT %d\t%.6f\t%.6f\t0.0000' % ((i,) + uv) for i, uv in enumerate(uvs)]
    L += ['\t\t}', '\t\t*MESH_NUMTVFACES %d' % len(faces), '\t\t*MESH_TFACELIST {']
    L += ['\t\t\t*MESH_TFACE %d\t%d\t%d\t%d' % ((i,) + f) for i, f in enumerate(faces)]
    L += ['\t\t}', '\t}', '\t*MATERIAL_REF 0', '}']
    path = os.path.join(MESHES, name + ".ase")
    os.makedirs(MESHES, exist_ok=True)
    open(path, "w", newline="\r\n").write("\n".join(L) + "\n")
    print(path, len(verts), "verts,", len(faces), "faces")


def write_rock(size=64):
    rng = random.Random(77)
    cells = 9
    lat = [[rng.random() for _ in range(cells + 1)] for _ in range(cells + 1)]
    px = bytearray()
    for y in range(size):
        for x in range(size):
            fx, fy = x / size * cells, y / size * cells
            x0, y0 = int(fx), int(fy)
            tx, ty = fx - x0, fy - y0
            n = (lat[y0][x0] * (1 - tx) + lat[y0][x0 + 1] * tx) * (1 - ty) + (lat[y0 + 1][x0] * (1 - tx) + lat[y0 + 1][x0 + 1] * tx) * ty
            g = 0.30 + 0.28 * n + 0.06 * rng.random()
            px += bytes([int(255 * g * k) for k in (0.95, 0.98, 1.0)] + [255])
    path = os.path.join(TEX, "dirt_rock.tga")
    with open(path, "wb") as fh:
        fh.write(struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 8))
        fh.write(px)
    print(path)


if __name__ == "__main__":
    write_ase("rubble0", *chunk(11, 0.7))
    write_ase("rubble1", *chunk(23, 0.45))
    write_rock()
