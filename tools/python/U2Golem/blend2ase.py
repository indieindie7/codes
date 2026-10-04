"""Blender meshes -> ASE static mesh for Unreal II's StaticMeshFactory (UnrealEd import).

Run:  blender -b <scene.blend> --python blend2ase.py -- <out.ase> [scale=1] [name=Body] [objects=a,b] [recenter=0]

Rules learned on U2Hover (see memory u2hover-project):
- no MATERIAL_LIST: UnrealEd crashes building a static mesh from an ASE with one; the texture goes on
  the actor as Skins[0] instead, so all objects must share one UV atlas (true for UT3 vehicles);
- Unreal II's ASE importer mirrors X, so X is pre-mirrored and the face winding flipped;
- the scene is taken in Unreal coordinates (psk2blend.py loads .psk/.pskx without axis changes),
  rest pose (armature deformation ignored), all mesh objects unless objects= is given.
"""
import os, sys
import bpy, bmesh

args = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(args[0])
o = dict(a.split("=", 1) for a in args[1:])
scale = float(o.get("scale", 1))
name = o.get("name", os.path.splitext(os.path.basename(out))[0])
pick = set(o["objects"].split(",")) if o.get("objects") else None

verts, faces, tverts = [], [], []
for ob in bpy.data.objects:
    if ob.type != "MESH" or (pick and ob.name not in pick):
        continue
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.transform(ob.matrix_world)
    uv = bm.loops.layers.uv.active
    base = len(verts)
    verts += [(-v.co.x * scale, v.co.y * scale, v.co.z * scale) for v in bm.verts]
    for f in bm.faces:
        ls = f.loops[:]
        order = (0, 2, 1)                      # mirrored X -> flip winding to stay outward
        t0 = len(tverts)
        for j in order:
            u, w = ls[j][uv].uv if uv else (0.0, 0.0)
            tverts.append((u, w))
        faces.append(([base + ls[j].vert.index for j in order], (t0, t0 + 1, t0 + 2)))
    bm.free()

if o.get("recenter") == "1":
    xs, ys, zs = zip(*verts)
    c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    verts = [(x - c[0], y - c[1], z - c[2]) for x, y, z in verts]

L = ["*3DSMAX_ASCIIEXPORT\t200", '*COMMENT "blend2ase"', "*GEOMOBJECT {", f'\t*NODE_NAME "{name}"', "\t*MESH {",
     "\t\t*TIMEVALUE 0", f"\t\t*MESH_NUMVERTEX {len(verts)}", f"\t\t*MESH_NUMFACES {len(faces)}", "\t\t*MESH_VERTEX_LIST {"]
L += [f"\t\t\t*MESH_VERTEX {i}\t{x:.5f}\t{y:.5f}\t{z:.5f}" for i, (x, y, z) in enumerate(verts)]
L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
L += [f"\t\t\t*MESH_FACE {i}: A: {a} B: {b} C: {c} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0"
      for i, ((a, b, c), _) in enumerate(faces)]
L += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(tverts)}", "\t\t*MESH_TVERTLIST {"]
L += [f"\t\t\t*MESH_TVERT {i}\t{u:.6f}\t{w:.6f}\t0.0000" for i, (u, w) in enumerate(tverts)]
L += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(faces)}", "\t\t*MESH_TFACELIST {"]
L += [f"\t\t\t*MESH_TFACE {i}\t{a}\t{b}\t{c}" for i, (_, (a, b, c)) in enumerate(faces)]
L += ["\t\t}", "\t}", "}"]
open(out, "w").write("\n".join(L) + "\n")
xs, ys, zs = zip(*verts)
print(f"BLEND2ASE {out}: {len(verts)} verts, {len(faces)} faces, size "
      f"{max(xs) - min(xs):.0f} x {max(ys) - min(ys):.0f} x {max(zs) - min(zs):.0f}")
