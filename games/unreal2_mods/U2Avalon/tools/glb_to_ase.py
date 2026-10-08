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
SCALE = float(o.get("scale", 1))     # 50 = metres -> Unreal units, so the actors sit at DrawScale 1
MESH_UVS = o.get("uvs", "palette") == "mesh"   # mesh: keep the GLB's UVs (a baked texture per mesh) instead of palette swatches
VFLIP = o.get("vflip", "0") == "1"
# a package of its own (AvalonSM2, 2026-10-07) keeps its own palette: pal= the texture's name (and the ASE's
# material, so the importer binds it by name), stripes= 16 for up to 16 colours (4 px columns)
PAL = o.get("pal", "Pal")
STRIPES = int(o.get("stripes", 8))
ZERO = set(o.get("zero", "CraneTower").split(","))   # meshes whose pivot stays at the model's z=0 (CraneTower: its plinth, Q33)
MATERIAL = o.get("material", "0") == "1"            # 1 = write 1-V (if the ASE importer does not flip V itself)
palette = []          # list of (r,g,b)


def swatch(rgb):
    key = tuple(round(v, 3) for v in rgb[:3])
    if key not in palette:
        palette.append(key)
    i = palette.index(key)
    if i >= STRIPES:
        raise SystemExit("more than %d palette colours: stripes=16" % STRIPES)
    # 8 full-height column stripes on a 64px texture, so the TGA's row order (Blender writes bottom-up and
    # UnrealEd does not flip) cannot matter; UV = the stripe's middle
    return ((i + 0.5) / STRIPES, 0.5)


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
    stem = os.path.basename(f)[:-4]
    # scripted buildings: cooling_tower_script -> CoolingTower; binder buildings keep their id: B_hall_a
    name = "".join(w.capitalize() for w in stem[:-7].split("_")) if stem.endswith("_script") else stem
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    meshes = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    P = np.concatenate([[tuple(mm.matrix_world @ v.co) for v in mm.data.vertices] for mm in meshes])
    lo, hi = P.min(0), P.max(0)
    cx, cy, z0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]
    if name in ZERO:
        z0 = 0.0                                    # pivot at the model's z=0, not its bottom: a plinth below it sinks into the ground
    verts, uvs, tris = [], [], []
    for mm in meshes:
        me = mm.data
        me.calc_loop_triangles()
        M = mm.matrix_world
        R = M.to_3x3()
        uvl = me.uv_layers.active.data if (MESH_UVS and me.uv_layers.active) else None
        for t in me.loop_triangles:
            mat = me.materials[t.material_index] if me.materials and t.material_index < len(me.materials) else None
            uv = swatch(mat_colour(mat)) if not MESH_UVS else None
            n = R @ t.normal
            idx = []
            for li, vi in zip(t.loops, t.vertices):
                if uvl is not None:
                    u_, v_ = uvl[li].uv
                    uv = (u_, 1.0 - v_) if VFLIP else (u_, v_)   # Blender V up; vflip=1 if the ASE importer keeps V as-is
                x, y, z = M @ me.vertices[vi].co
                x, y = x - cx, y - cy
                # glTF front (-Y) -> Unreal +X: turn +90 degrees about Z; scale= bakes metres into units
                verts.append((-y * SCALE, x * SCALE, (z - z0) * SCALE))
                uvs.append(uv)
                idx.append(len(verts) - 1)
            want = (-n.y, n.x, n.z)
            tris.append(tri_facing(verts, tuple(idx), want))
    write_ase(os.path.join(out, name + ".ase"), name, verts, uvs, tris, material=PAL if MATERIAL else None)
    bounds[name] = {"w": float(hi[1] - lo[1]) * SCALE, "d": float(hi[0] - lo[0]) * SCALE, "h": float(hi[2] - lo[2]) * SCALE,
                    "texture": (stem if MESH_UVS else PAL)}
    print("ASE", name, len(tris), "tris", bounds[name])

# the palette texture (row 0 at the top = V 0)
if MESH_UVS and not palette:
    # the baked meshes carry textures, not swatches: still write the 8 stripes (make_avalon's own meshes,
    # tower/room/quay/fence/pipeline, pick their colours from palette.json)
    import palette as _pal
    palette = [tuple(round(v, 3) for v in c) for c in _pal.COLOURS.values()]
img = np.zeros((64, 64, 4), np.float32)
img[..., 3] = 1
sw = 64 // STRIPES
for i, c in enumerate(palette):
    img[:, i * sw:(i + 1) * sw, :3] = c
tex = bpy.data.images.new(PAL, 64, 64, alpha=True)
tex.pixels = img[::-1].ravel()
tex.filepath_raw = os.path.join(out, PAL + ".tga")
tex.file_format = "TARGA_RAW"   # UnrealEd rejects RLE-compressed TGA ("Bad image format")
tex.save()
json.dump(bounds, open(os.path.join(out, "bounds.json"), "w"), indent=1)
json.dump([list(c) for c in palette], open(os.path.join(out, "palette.json"), "w"))   # stripe i = colour i
print("PALETTE", len(palette), "colours;", len(bounds), "meshes ->", out)
