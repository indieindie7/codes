"""Scripted buildings (tools\build_buildings.py GLBs) -> Unreal II ASE static meshes + one palette texture.

    blender -b --python glb_to_ase.py -- <glb_dir> <out_dir> [pattern=*_script.glb]

Every GLB material's base colour becomes one 8x8 swatch of <out_dir>/Pal.tga (64x64, up to 64 colours),
and every triangle's UVs point at the middle of its material's swatch, so all the buildings share a
single flat-coloured texture (Skins(0) on the actor). Each mesh is recentred (XY = bounds centre,
Z = its bottom) and turned so the glTF front (-Y) faces Unreal's +X (yaw 0). Written with the
U2Hover ASE conventions (X negated for the importer's mirror, winding fixed from Blender's normals).
<out_dir>/bounds.json: name -> {"w","d","h"} in the GLB's units, for DrawScale.
"""
import glob, json, os, sys
import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ase import write_ase, tri_facing  # noqa

a = sys.argv[sys.argv.index("--") + 1:]
src, out = a[0], os.path.abspath(a[1])
o = dict(x.split("=", 1) for x in a[2:])
os.makedirs(out, exist_ok=True)
palette = []          # list of (r,g,b)


def swatch(rgb):
    key = tuple(round(v, 3) for v in rgb[:3])
    if key not in palette:
        palette.append(key)
    i = palette.index(key)
    # 8x8 grid of 8px cells on a 64px texture; UV of the cell middle (V down in Unreal)
    return ((i % 8 + 0.5) / 8.0, (i // 8 + 0.5) / 8.0)


def mat_colour(m):
    if m is None:
        return (0.6, 0.6, 0.6)
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                c = n.inputs["Base Color"].default_value[:3]
                e = n.inputs["Emission Color"].default_value[:3] if "Emission Color" in n.inputs else (0, 0, 0)
                s = n.inputs["Emission Strength"].default_value if "Emission Strength" in n.inputs else 0
                if s > 0.5 and max(e) > 0.2:
                    return tuple(min(1, 0.4 * c[k] + 0.9 * e[k]) for k in range(3))
                return tuple(c)
    return tuple(m.diffuse_color[:3])


bounds = {}
for f in sorted(glob.glob(os.path.join(src, o.get("pattern", "*_script.glb")))):
    name = "".join(w.capitalize() for w in os.path.basename(f).replace("_script.glb", "").split("_"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    P = np.concatenate([[tuple(mm.matrix_world @ v.co) for v in mm.data.vertices] for mm in meshes])
    lo, hi = P.min(0), P.max(0)
    cx, cy, z0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]
    verts, uvs, tris = [], [], []
    for mm in meshes:
        me = mm.data
        me.calc_loop_triangles()
        M = mm.matrix_world
        R = M.to_3x3()
        for t in me.loop_triangles:
            mat = me.materials[t.material_index] if me.materials and t.material_index < len(me.materials) else None
            uv = swatch(mat_colour(mat))
            n = R @ t.normal
            idx = []
            for vi in t.vertices:
                x, y, z = M @ me.vertices[vi].co
                x, y = x - cx, y - cy
                # glTF front (-Y) -> Unreal +X: turn +90 degrees about Z
                verts.append((-y, x, z - z0))
                uvs.append(uv)
                idx.append(len(verts) - 1)
            want = (-n.y, n.x, n.z)
            tris.append(tri_facing(verts, tuple(idx), want))
    write_ase(os.path.join(out, name + ".ase"), name, verts, uvs, tris)
    bounds[name] = {"w": float(hi[1] - lo[1]), "d": float(hi[0] - lo[0]), "h": float(hi[2] - lo[2])}
    print("ASE", name, len(tris), "tris", bounds[name])

# the palette texture (row 0 at the top = V 0)
img = np.zeros((64, 64, 4), np.float32)
img[..., 3] = 1
for i, c in enumerate(palette):
    r, cI = i // 8, i % 8
    img[r * 8:(r + 1) * 8, cI * 8:(cI + 1) * 8, :3] = c
tex = bpy.data.images.new("Pal", 64, 64, alpha=True)
tex.pixels = img[::-1].ravel()
tex.filepath_raw = os.path.join(out, "Pal.tga")
tex.file_format = "TARGA_RAW"   # UnrealEd rejects RLE-compressed TGA ("Bad image format")
tex.save()
json.dump(bounds, open(os.path.join(out, "bounds.json"), "w"), indent=1)
print("PALETTE", len(palette), "colours;", len(bounds), "meshes ->", out)
