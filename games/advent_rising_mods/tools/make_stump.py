"""Writes the stump cap mesh (AdventMod/Meshes/stump.ase): a lumpy low-poly blob of unit
radius, drawn where a severed limb left the body (ModStump). Our own geometry. Every
triangle is written with both windings, so it shows whichever way the importer mirrors.

    python tools/make_stump.py
"""
import math
import os
import random

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AdventMod", "Meshes", "stump.ase")
RINGS, SEGS = 5, 8


def main():
    random.seed(4)
    verts, uvs = [(0.0, 0.0, 1.0)], [(0.5, 0.0)]
    for r in range(1, RINGS):
        phi = math.pi * r / RINGS
        for s in range(SEGS):
            th = 2 * math.pi * s / SEGS
            k = 1.0 + random.uniform(-0.18, 0.18)            # lumps
            verts.append((k * math.sin(phi) * math.cos(th), k * math.sin(phi) * math.sin(th), 0.7 * k * math.cos(phi)))
            uvs.append((s / SEGS, r / RINGS))
    verts.append((0.0, 0.0, -0.7))
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
    faces += [(a, c, b) for a, b, c in faces]                # both windings
    L = ['*3DSMAX_ASCIIEXPORT\t200', '*COMMENT "make_stump.py"', '*MATERIAL_LIST {', '\t*MATERIAL_COUNT 1',
         '\t*MATERIAL 0 {', '\t\t*MATERIAL_NAME "meat"', '\t\t*MATERIAL_CLASS "Standard"', '\t\t*MAP_DIFFUSE {',
         '\t\t\t*MAP_NAME "meat"', '\t\t\t*BITMAP "meat.bmp"', '\t\t}', '\t}', '}', '*GEOMOBJECT {',
         '\t*NODE_NAME "stump"', '\t*MESH {', '\t\t*TIMEVALUE 0', '\t\t*MESH_NUMVERTEX %d' % len(verts),
         '\t\t*MESH_NUMFACES %d' % len(faces), '\t\t*MESH_VERTEX_LIST {']
    L += ['\t\t\t*MESH_VERTEX %d\t%.5f\t%.5f\t%.5f' % ((i,) + v) for i, v in enumerate(verts)]
    L += ['\t\t}', '\t\t*MESH_FACE_LIST {']
    L += ['\t\t\t*MESH_FACE %d: A: %d B: %d C: %d AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0' % ((i,) + f)
          for i, f in enumerate(faces)]
    L += ['\t\t}', '\t\t*MESH_NUMTVERTEX %d' % len(uvs), '\t\t*MESH_TVERTLIST {']
    L += ['\t\t\t*MESH_TVERT %d\t%.6f\t%.6f\t0.0000' % ((i,) + uv) for i, uv in enumerate(uvs)]
    L += ['\t\t}', '\t\t*MESH_NUMTVFACES %d' % len(faces), '\t\t*MESH_TFACELIST {']
    L += ['\t\t\t*MESH_TFACE %d\t%d\t%d\t%d' % ((i,) + f) for i, f in enumerate(faces)]
    L += ['\t\t}', '\t}', '\t*MATERIAL_REF 0', '}']
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", newline="\r\n").write("\n".join(L) + "\n")
    print(OUT, len(verts), "verts,", len(faces), "faces")


if __name__ == "__main__":
    main()
