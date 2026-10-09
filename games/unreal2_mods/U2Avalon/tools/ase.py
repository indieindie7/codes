"""ASE writer for Unreal II static meshes (copied from U2Hover/make_map.py: Blender has no PIL for that import)."""
def tri_facing(v, tri, want):
    """Order tri so that it faces WANT after import (see module docstring)."""
    a, b, c = (v[i] for i in tri)
    u = [b[k] - a[k] for k in range(3)]
    w = [c[k] - a[k] for k in range(3)]
    n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
    if sum(n[k] * want[k] for k in range(3)) > 0:
        return (tri[0], tri[2], tri[1])
    return tri


def write_ase(path, name, verts, uvs, tris, material=None, extras=()):
    """material= a texture name: a one-entry material list whose bitmap is <material>.tga, so UnrealEd's
    importer can bind the mesh to the texture of that name already loaded (AvalonSM2's palette).
    extras = [(name, verts, uvs, tris), ...]: more GEOMOBJECTs in the same file - the MCDCX_<name> collision
    hulls (one convex piece each) that the importer uses as the mesh's collision instead of its render polys"""
    L = ["*3DSMAX_ASCIIEXPORT 200"]
    if material:
        L += ["*MATERIAL_LIST {", "\t*MATERIAL_COUNT 1", "\t*MATERIAL 0 {", f'\t\t*MATERIAL_NAME "{material}"',
              '\t\t*MATERIAL_CLASS "Standard"', "\t\t*MAP_DIFFUSE {", f'\t\t\t*MAP_NAME "{material}"',
              f'\t\t\t*BITMAP "{material}.tga"', "\t\t}", "\t}", "}"]
    L += geomobject(name, verts, uvs, tris, material)
    for en, ev, eu, et in extras:
        L += geomobject(en, ev, eu, et, material)
    open(path, "w").write("\n".join(L) + "\n")


def geomobject(name, verts, uvs, tris, material=None):
    L = ["*GEOMOBJECT {", f'\t*NODE_NAME "{name}"', "\t*MESH {",
         f"\t\t*MESH_NUMVERTEX {len(verts)}", f"\t\t*MESH_NUMFACES {len(tris)}", "\t\t*MESH_VERTEX_LIST {"]
    L += [f"\t\t\t*MESH_VERTEX {k} {-v[0]:.3f} {v[1]:.3f} {v[2]:.3f}" for k, v in enumerate(verts)]
    L += ["\t\t}", "\t\t*MESH_FACE_LIST {"]
    L += [f"\t\t\t*MESH_FACE {k}: A: {t[0]} B: {t[1]} C: {t[2]} AB: 1 BC: 1 CA: 1 *MESH_SMOOTHING 1 *MESH_MTLID 0"
          for k, t in enumerate(tris)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVERTEX {len(uvs)}", "\t\t*MESH_TVERTLIST {"]
    L += [f"\t\t\t*MESH_TVERT {k} {t[0]:.5f} {t[1]:.5f} 0.0000" for k, t in enumerate(uvs)]
    L += ["\t\t}", f"\t\t*MESH_NUMTVFACES {len(tris)}", "\t\t*MESH_TFACELIST {"]
    L += [f"\t\t\t*MESH_TFACE {k} {t[0]} {t[1]} {t[2]}" for k, t in enumerate(tris)]
    L += ["\t\t}", "\t}"]
    if material:
        L += ["\t*MATERIAL_REF 0"]
    L += ["}"]
    return L


